# app.py
import re
import io
from typing import List, Dict, Any, Tuple

import pandas as pd
import pdfplumber
import streamlit as st


# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Lector Facturas PDF → Excel", layout="wide")

COLS = [
    "EMPRESA", "#FACTURA", "UUID", "FECHA FACTURA",
    "FECHA Y HR SERVICIO", "#UNIDAD",
    "ACTIVIDAD", "CANTIDAD", "SUBTOTAL", "IVA", "TOTAL"
]


# =========================
# HELPERS
# =========================
def extract_pages_text(pdf_bytes: bytes) -> List[str]:
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        return [(p.extract_text() or "") for p in pdf.pages]


def find_first(pattern: str, text: str, flags=0) -> str:
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else ""


def norm_money(s: str) -> float:
    s = (s or "").replace("$", "").replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return 0.0


def clean_k9_service_dt(raw: str) -> str:
    # "04-02-2026 HORA 10.31 AM" -> "04-02-2026 10:31 am"
    if not raw:
        return ""
    raw = re.sub(r"\bHORA\b", "", raw, flags=re.I).strip()
    raw = re.sub(r"(\d{1,2})\.(\d{2})", r"\1:\2", raw)  # 10.31 -> 10:31
    raw = re.sub(r"\s+", " ", raw).strip()
    raw = raw.replace("AM", "am").replace("PM", "pm")
    return raw


def autodetect_format(full_text: str) -> str:
    t = full_text.upper()

    # WASH N CROSS
    if "WASH N CROSS" in t or "SERIE Y FOLIO" in t and "FOLIO FISCAL (UUID" in t:
        return "WASH"

    # ROYAN
    if "ROYAN-" in t and "TIPO:" in t and "CLIENTE:" in t:
        return "ROYAN"

    # K9
    if "K9" in t and "COMENTARIOS:" in t and "UUID" in t:
        return "K9"

    # fallback heuristics
    if "ROYAN-" in t:
        return "ROYAN"
    if "WNC" in t or "FOLIO FISCAL (UUID" in t:
        return "WASH"
    return "K9"


def build_df(rows: List[Dict[str, Any]], iva_rate: float) -> pd.DataFrame:
    out = []
    for r in rows:
        subtotal = float(r.get("SUBTOTAL", 0) or 0)
        iva = round(subtotal * iva_rate, 2)
        total = round(subtotal + iva, 2)

        out.append({
            "EMPRESA": r.get("EMPRESA", ""),
            "#FACTURA": r.get("#FACTURA", ""),
            "UUID": r.get("UUID", ""),
            "FECHA FACTURA": r.get("FECHA FACTURA", ""),
            "FECHA Y HR SERVICIO": r.get("FECHA Y HR SERVICIO", ""),
            "#UNIDAD": r.get("#UNIDAD", ""),
            "ACTIVIDAD": r.get("ACTIVIDAD", ""),
            "CANTIDAD": r.get("CANTIDAD", 1),
            "SUBTOTAL": round(subtotal, 2),
            "IVA": iva,
            "TOTAL": total,
        })

    return pd.DataFrame(out, columns=COLS)


# =========================
# PARSERS
# =========================
def parse_k9(pdf_bytes: bytes) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    pages = extract_pages_text(pdf_bytes)
    full = "\n".join(pages)

    # EMPRESA: NOMBRE COMERCIAL
    empresa = find_first(r"NOMBRE COMERCIAL:\s*(.+)", full)

    # UUID (debajo de "UUID")
    uuid = find_first(r"\bUUID\s*\n\s*([0-9a-fA-F-]{36})", full)

    # FECHA FACTURA (debajo de TEL)
    fecha_factura = find_first(
        r"\b(\d{2}/\d{2}/\d{4}\s+\d{1,2}:\d{2}\s*[ap]\.m\.)\b",
        full, flags=re.I
    )

    # Fallback: a veces viene como "Fecha Expedición"
    if not fecha_factura:
        fecha_factura = find_first(
            r"Fecha\s*Expedici[oó]n:?\s*\n?\s*(\d{2}/\d{2}/\d{4}\s+\d{1,2}:\d{2}\s*[ap]\.m\.)",
            full, flags=re.I
        )
    
    # Fallback final: cualquier fecha-hora con a.m./p.m.
    if not fecha_factura:
        fecha_factura = find_first(
            r"(\d{2}/\d{2}/\d{4}\s+\d{1,2}:\d{2}\s*[ap]\.m\.)",
            full, flags=re.I
        )

    comentarios = find_first(r"Comentarios:\s*(.+)", full)

    # #FACTURA: ORDEN K9 6738
    factura = find_first(r"\bORDEN\s+(K9\s*\d+)\b", comentarios, flags=re.I).upper().replace("  ", " ")

    # #UNIDAD: lo que va después de la primer palabra (CAJA / CAMIÓN / TRACTOR / etc.)
    # Ej: "CAJA SET-33 ORDEN..." -> SET-33
    unidad = ""
    m = re.search(r"^\s*([A-ZÁÉÍÓÚÑ]+)\s+([A-Z0-9\-]+)\b", comentarios.strip(), flags=re.I)
    if m:
        unidad = m.group(2).strip()

    # FECHA Y HR SERVICIO: después de "SERVICIO REALIZADO"
    servicio_raw = find_first(r"\bSERVICIO REALIZADO\s+(.+)$", comentarios, flags=re.I)
    servicio = clean_k9_service_dt(servicio_raw)

    header = {
        "EMPRESA": empresa,
        "#FACTURA": factura,
        "UUID": uuid,
        "FECHA FACTURA": fecha_factura,
        "FECHA Y HR SERVICIO": servicio,
        "#UNIDAD": unidad,
    }

    # === Tabla de conceptos (con soporte multilínea) ===
    # Estrategia:
    # - Si una línea termina con "... <precio> <importe>" la cerramos
    # - Si no, la acumulamos como continuación del texto hasta que llegue la línea que trae importe
    items: List[Dict[str, Any]] = []

    pending_desc = ""
    pending_qty = None
    pending_subtotal = None

    # patrón de línea completa:
    # 78181507 DESCRIPCION SERVICIO 1 450.00 450.00
    pat_full = re.compile(
        r"^(?P<clave>\d{8})\s+(?P<desc>.+?)\s+(?P<unidad>[A-ZÁÉÍÓÚÑ]+)\s+"
        r"(?P<cant>\d+)\s+(?P<precio>[\d,]+\.\d{2})\s+(?P<importe>[\d,]+\.\d{2})$",
        re.I
    )

    # patrón de “cierre” sin clave (cuando se partió):
    # "... SERVICIO 1 1200.00 1200.00"
    pat_close = re.compile(
        r"^(?P<desc2>.+?)\s+(?P<unidad>[A-ZÁÉÍÓÚÑ]+)\s+(?P<cant>\d+)\s+"
        r"(?P<precio>[\d,]+\.\d{2})\s+(?P<importe>[\d,]+\.\d{2})$",
        re.I
    )

    for line in full.splitlines():
        s = re.sub(r"\s+", " ", line.strip())
        if not s:
            continue

        m1 = pat_full.match(s)
        if m1:
            items.append({
                "ACTIVIDAD": m1.group("desc").strip(),
                "CANTIDAD": int(m1.group("cant")),
                "SUBTOTAL": norm_money(m1.group("importe"))
            })
            pending_desc = ""
            continue

        # Si empieza con clave pero NO trae importe completo: acumulamos
        if re.match(r"^\d{8}\s+", s):
            # guardamos lo que venga después de la clave
            pending_desc = re.sub(r"^\d{8}\s+", "", s).strip()
            continue

        # si estamos acumulando y llega la línea de cierre:
        if pending_desc:
            m2 = pat_close.match(s)
            if m2:
                full_desc = (pending_desc + " " + m2.group("desc2")).strip()
                items.append({
                    "ACTIVIDAD": full_desc,
                    "CANTIDAD": int(m2.group("cant")),
                    "SUBTOTAL": norm_money(m2.group("importe"))
                })
                pending_desc = ""
            else:
                # sigue siendo parte de la descripción
                pending_desc = (pending_desc + " " + s).strip()

    return header, items


def parse_royan(pdf_bytes: bytes) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    pages = extract_pages_text(pdf_bytes)
    full = "\n".join(pages)

    empresa = find_first(r"\nCliente:\s*\n?([A-Z0-9ÁÉÍÓÚÑ ]+)\n", full).strip()
    factura = find_first(r"\b(ROYAN-\d+)\b", full)
    uuid = find_first(r"\b([0-9a-f]{8}-[0-9a-f\-]{27})\b", full, flags=re.I)
    fecha = find_first(r"\b(\d{2}/\d{2}/\d{4})\b", full)

    # Caja: PI-183
    unidad = find_first(r"\bCaja:\s*([A-Z0-9\-]+)\b", full, flags=re.I)

    header = {
        "EMPRESA": empresa,             # quieres PICUS (sale del Cliente)
        "#FACTURA": factura,
        "UUID": uuid,
        "FECHA FACTURA": fecha,         # solo fecha
        "FECHA Y HR SERVICIO": "",      # no aplica
        "#UNIDAD": unidad,
    }

    # === Detalle (multilínea) ===
    # En detalle viene como:
    # 3,200.00 Actividad MANTENIMIENTO... Y PONER
    # 4 RETENES
    # ACT
    items: List[Dict[str, Any]] = []

    # línea de inicio de concepto con importe
    pat_start = re.compile(r"^(?P<importe>[\d,]+\.\d{2})\s+Actividad\s+(?P<desc>.+)$", re.I)
    # línea que indica fin (ACT al final o sola)
    pat_end_act = re.compile(r".*\bACT\b$", re.I)

    current_importe = None
    current_desc_parts: List[str] = []

    for page_text in pages:
        for raw in (page_text or "").splitlines():
            line = raw.strip()
            if not line:
                continue

            m = pat_start.match(line)
            if m:
                # si había uno abierto, lo cerramos
                if current_importe is not None and current_desc_parts:
                    desc = " ".join(current_desc_parts).strip()
                    items.append({"ACTIVIDAD": desc, "CANTIDAD": 1, "SUBTOTAL": norm_money(current_importe)})
                    current_desc_parts = []

                current_importe = m.group("importe")
                current_desc_parts = [m.group("desc").strip()]
                continue

            # si hay uno abierto, acumulamos descripción hasta detectar ACT
            if current_importe is not None:
                # si la línea es "ACT" o termina en ACT, quitamos ACT y cerramos
                if line.upper() == "ACT" or pat_end_act.match(line):
                    cleaned = re.sub(r"\bACT\b", "", line, flags=re.I).strip()
                    if cleaned:
                        current_desc_parts.append(cleaned)

                    desc = " ".join(current_desc_parts).strip()
                    items.append({"ACTIVIDAD": desc, "CANTIDAD": 1, "SUBTOTAL": norm_money(current_importe)})
                    current_importe = None
                    current_desc_parts = []
                else:
                    # continuación (segunda línea como "4 RETENES")
                    current_desc_parts.append(line)

    # cierre por si quedó abierto
    if current_importe is not None and current_desc_parts:
        desc = " ".join(current_desc_parts).strip()
        items.append({"ACTIVIDAD": desc, "CANTIDAD": 1, "SUBTOTAL": norm_money(current_importe)})

    return header, items


def parse_wash(pdf_bytes: bytes) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    pages = extract_pages_text(pdf_bytes)
    full = "\n".join(pages)

    empresa = find_first(r"\n(PICUS)\n", full)  # en tus ejemplos es literal
    factura = find_first(r"SERIE Y FOLIO\s+([A-Z0-9\-]+)", full)
    uuid = find_first(r"FOLIO FISCAL \(UUID\)\s*\n([0-9A-F-]{36})", full, flags=re.I)

    # FECHA FACTURA exacta: 05/01/2026 10:10:32
    fecha = find_first(r"FECHA DE EMISION\s+(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2})", full)

    header = {
        "EMPRESA": empresa,
        "#FACTURA": factura,
        "UUID": uuid,
        "FECHA FACTURA": fecha,
    }

    # conceptos: tomamos REF.PAGO -> #UNIDAD, OBS -> FECHA Y HR SERVICIO
    items: List[Dict[str, Any]] = []

    # Ej línea (texto lineal): "1 ... 78181500 ENTREGA ... 244973 PI-55 RL 2025-12-29 225.00 225.00"
    pat = re.compile(
        r"^(?P<cant>\d+)\s+.+?\s+\d{8}\s+(?P<desc>.+?)\s+\d+\s+"
        r"(?P<ref>[A-Z0-9\- ]+)\s+(?P<obs>\d{4}-\d{2}-\d{2})\s+"
        r"[\d,]+\.\d{2}\s+(?P<importe>[\d,]+\.\d{2})$",
        re.I
    )

    for line in full.splitlines():
        s = re.sub(r"\s+", " ", line.strip())
        if not s:
            continue
        m = pat.match(s)
        if m:
            items.append({
                "EMPRESA": header["EMPRESA"],
                "#FACTURA": header["#FACTURA"],
                "UUID": header["UUID"],
                "FECHA FACTURA": header["FECHA FACTURA"],
                "FECHA Y HR SERVICIO": m.group("obs").strip(),  # OBS
                "#UNIDAD": m.group("ref").strip(),             # REF.PAGO
                "ACTIVIDAD": m.group("desc").strip(),
                "CANTIDAD": int(m.group("cant")),
                "SUBTOTAL": norm_money(m.group("importe")),
            })

    return header, items


# =========================
# STREAMLIT UI
# =========================
st.title("📄 Lector de Facturas PDF → Excel")
st.caption("Sube 1 o varios PDFs. El formato se autodetecta (K9 / ROYAN / WASH N CROSS).")

files = st.file_uploader("Sube tus facturas PDF", type=["pdf"], accept_multiple_files=True)

col1, col2 = st.columns(2)
with col1:
    do_autodetect = st.checkbox("Autodetectar formato", value=True)
with col2:
    show_debug = st.checkbox("Ver formato detectado por archivo", value=False)

if st.button("Procesar") and files:
    all_dfs: List[pd.DataFrame] = []
    debug_rows = []

    for f in files:
        pdf_bytes = f.read()
        pages = extract_pages_text(pdf_bytes)
        full = "\n".join(pages)

        fmt = autodetect_format(full) if do_autodetect else "K9"

        if fmt == "K9":
            header, items = parse_k9(pdf_bytes)
            rows = [{**header, **it} for it in items]
            df = build_df(rows, iva_rate=0.08)

        elif fmt == "ROYAN":
            header, items = parse_royan(pdf_bytes)
            rows = [{**header, **it} for it in items]
            df = build_df(rows, iva_rate=0.16)

        else:  # WASH
            header, items = parse_wash(pdf_bytes)
            df = build_df(items, iva_rate=0.08)  # items ya vienen “por fila”

        all_dfs.append(df)

        debug_rows.append({
            "archivo": f.name,
            "formato_detectado": fmt,
            "filas_generadas": len(df)
        })

    final_df = pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame(columns=COLS)

    st.success(f"Listo: {len(final_df)} registros (de {len(files)} archivos).")
    st.dataframe(final_df, use_container_width=True)

    if show_debug:
        st.subheader("Debug")
        st.dataframe(pd.DataFrame(debug_rows), use_container_width=True)

    # export único
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        final_df.to_excel(writer, index=False, sheet_name="FACTURAS")

    st.download_button(
        "⬇️ Descargar Excel (con todo)",
        data=output.getvalue(),
        file_name="FACTURAS_CONSOLIDADO.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
