import re
import io
import unicodedata
from typing import List, Dict, Any, Tuple
import pandas as pd
import pdfplumber
import streamlit as st
from auth import require_login, require_access

# =================================
# Page configuration
# =================================
st.set_page_config(page_title="Lector Facturas PDF → Excel", layout="wide")

# =================================
# Hide sidebar
# =================================
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        display: none;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# =================================
# Security gates
# =================================
require_login()
require_access("lector_pdf")

# =================================
# Navigation
# =================================
if st.button("⬅ Volver al Dashboard"):
    st.switch_page("pages/dashboard.py")

st.divider()

COLS = [
    "EMPRESA", "#FACTURA", "UUID", "FECHA FACTURA",
    "FECHA Y HR SERVICIO", "#UNIDAD",
    "ACTIVIDAD", "CANTIDAD", "SUBTOTAL", "IVA", "TOTAL"
]

def strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s or "")
        if unicodedata.category(c) != "Mn"
    )

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
    # '04-02-2026 HORA 10.31 AM' -> '04-02-2026 10:31 am'
    if not raw:
        return ""
    raw = re.sub(r"\bHORA\b", "", raw, flags=re.I).strip()
    raw = re.sub(r"(\d{1,2})\.(\d{2})", r"\1:\2", raw)  # 10.31 -> 10:31
    raw = re.sub(r"\s+", " ", raw).strip()
    raw = raw.replace("AM", "am").replace("PM", "pm")
    return raw

def prettify_receiver_name(s: str) -> str:
    """
    En Ana Cecilia, el receptor a veces sale pegado: LINCOLNFREIGHTCOMPANYLLC
    Aquí lo arreglamos con un mapeo simple (puedes agregar más si salen nuevos).
    """
    if not s:
        return ""
    u = s.upper().replace(" ", "")
    if u == "LINCOLNFREIGHTCOMPANYLLC":
        return "LINCOLN FREIGHT COMPANY LLC"
    return s

def build_df(rows: List[Dict[str, Any]], iva_rate: float) -> pd.DataFrame:
    """
    - Si la fila ya trae IVA numérico (ANA CECILIA), se respeta.
    - Si no trae IVA, se calcula con iva_rate.
    """
    out = []
    for r in rows:
        subtotal = float(r.get("SUBTOTAL", 0) or 0)

        iva_in = r.get("IVA", None)
        if iva_in is None or iva_in == "":
            iva = round(subtotal * iva_rate, 2)
        else:
            try:
                iva = round(float(iva_in), 2)
            except Exception:
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

def autodetect_format(full_text: str) -> str:
    t = strip_accents(full_text).upper()

    # Detecta directo por RFC (sin depender de "RFC emisor:" / "RFCemisor:")
    if "LOGA8509108NA" in t:
        return "ANA_CECILIA"

    if "WNC070608P43" in t or "WASH N CROSS" in t:
        return "WASH"

    if "NAMA820330G3A" in t or "ROYAN-" in t:
        return "ROYAN"

    if "BAEM890616HW5" in t or "COMENTARIOS:" in t or "ORDEN K9" in t:
        return "K9"

    return "K9"

def parse_k9(pdf_bytes: bytes) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    pages = extract_pages_text(pdf_bytes)
    full = "\n".join(pages)

    empresa = find_first(r"NOMBRE COMERCIAL:\s*(.+)", full)
    uuid = find_first(r"\bUUID\s*\n\s*([0-9a-fA-F-]{36})", full, flags=re.I)

    # FECHA FACTURA debajo de TEL (robusto)
    fecha_factura = find_first(
        r"TEL\.?\s*\n\s*(\d{2}/\d{2}/\d{4}\s+\d{1,2}:\d{2}\s*[ap]\.m\.)",
        full, flags=re.I
    )
    if not fecha_factura:
        fecha_factura = find_first(
            r"Fecha\s*Expedici[oó]n:?\s*\n?\s*(\d{2}/\d{2}/\d{4}\s+\d{1,2}:\d{2}\s*[ap]\.m\.)",
            full, flags=re.I
        )
    if not fecha_factura:
        fecha_factura = find_first(
            r"(\d{2}/\d{2}/\d{4}\s+\d{1,2}:\d{2}\s*[ap]\.m\.)",
            full, flags=re.I
        )

    comentarios = find_first(r"Comentarios:\s*(.+)", full)

    factura = find_first(r"\bORDEN\s+(K9\s*\d+)\b", comentarios, flags=re.I).upper().replace("  ", " ")

    # #UNIDAD: token después de la primer palabra (CAJA/CAMION/TRACTOR/etc.)
    unidad = ""
    m = re.search(r"^\s*([A-ZÁÉÍÓÚÑ]+)\s+([A-Z0-9\-]+)\b", comentarios.strip(), flags=re.I)
    if m:
        unidad = m.group(2).strip()

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

    # conceptos multilínea
    items: List[Dict[str, Any]] = []

    pat_full = re.compile(
        r"^(?P<clave>\d{8})\s+(?P<desc>.+?)\s+(?P<unidad>[A-ZÁÉÍÓÚÑ]+)\s+"
        r"(?P<cant>\d+)\s+(?P<precio>[\d,]+\.\d{2})\s+(?P<importe>[\d,]+\.\d{2})$",
        re.I
    )
    pat_close = re.compile(
        r"^(?P<desc2>.+?)\s+(?P<unidad>[A-ZÁÉÍÓÚÑ]+)\s+(?P<cant>\d+)\s+"
        r"(?P<precio>[\d,]+\.\d{2})\s+(?P<importe>[\d,]+\.\d{2})$",
        re.I
    )

    pending_desc = ""

    for line in full.splitlines():
        s = re.sub(r"\s+", " ", line.strip())
        if not s:
            continue

        m1 = pat_full.match(s)
        if m1:
            items.append({
                "ACTIVIDAD": m1.group("desc").strip(),
                "CANTIDAD": int(m1.group("cant")),
                "SUBTOTAL": norm_money(m1.group("importe")),
            })
            pending_desc = ""
            continue

        if re.match(r"^\d{8}\s+", s):
            pending_desc = re.sub(r"^\d{8}\s+", "", s).strip()
            continue

        if pending_desc:
            m2 = pat_close.match(s)
            if m2:
                full_desc = (pending_desc + " " + m2.group("desc2")).strip()
                items.append({
                    "ACTIVIDAD": full_desc,
                    "CANTIDAD": int(m2.group("cant")),
                    "SUBTOTAL": norm_money(m2.group("importe")),
                })
                pending_desc = ""
            else:
                pending_desc = (pending_desc + " " + s).strip()

    return header, items

def parse_royan(pdf_bytes: bytes) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    pages = extract_pages_text(pdf_bytes)
    full = "\n".join(pages)

    empresa = find_first(r"\nCliente:\s*\n?([A-Z0-9ÁÉÍÓÚÑ ]+)\n", full).strip()
    factura = find_first(r"\b(ROYAN-\d+)\b", full)
    uuid = find_first(r"\b([0-9a-f]{8}-[0-9a-f\-]{27})\b", full, flags=re.I)
    fecha = find_first(r"\b(\d{2}/\d{2}/\d{4})\b", full)
    unidad = find_first(r"\bCaja:\s*([A-Z0-9\-]+)\b", full, flags=re.I)

    header = {
        "EMPRESA": empresa,
        "#FACTURA": factura,
        "UUID": uuid,
        "FECHA FACTURA": fecha,
        "FECHA Y HR SERVICIO": "",
        "#UNIDAD": unidad,
    }

    items: List[Dict[str, Any]] = []
    pat_start = re.compile(r"^(?P<importe>[\d,]+\.\d{2})\s+Actividad\s+(?P<desc>.+)$", re.I)
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
                if current_importe is not None and current_desc_parts:
                    desc = " ".join(current_desc_parts).strip()
                    items.append({"ACTIVIDAD": desc, "CANTIDAD": 1, "SUBTOTAL": norm_money(current_importe)})
                    current_desc_parts = []

                current_importe = m.group("importe")
                current_desc_parts = [m.group("desc").strip()]
                continue

            if current_importe is not None:
                if line.upper() == "ACT" or pat_end_act.match(line):
                    cleaned = re.sub(r"\bACT\b", "", line, flags=re.I).strip()
                    if cleaned:
                        current_desc_parts.append(cleaned)

                    desc = " ".join(current_desc_parts).strip()
                    items.append({"ACTIVIDAD": desc, "CANTIDAD": 1, "SUBTOTAL": norm_money(current_importe)})
                    current_importe = None
                    current_desc_parts = []
                else:
                    current_desc_parts.append(line)

    if current_importe is not None and current_desc_parts:
        desc = " ".join(current_desc_parts).strip()
        items.append({"ACTIVIDAD": desc, "CANTIDAD": 1, "SUBTOTAL": norm_money(current_importe)})

    return header, items

def parse_wash(pdf_bytes: bytes) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    pages = extract_pages_text(pdf_bytes)
    full = "\n".join(pages)

    empresa = find_first(r"\n(PICUS)\n", full)  # en tus ejemplos
    factura = find_first(r"SERIE Y FOLIO\s+([A-Z0-9\-]+)", full)
    uuid = find_first(r"FOLIO FISCAL \(UUID\)\s*\n([0-9A-F-]{36})", full, flags=re.I)
    fecha = find_first(r"FECHA DE EMISION\s+(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2})", full)

    header = {
        "EMPRESA": empresa,
        "#FACTURA": factura,
        "UUID": uuid,
        "FECHA FACTURA": fecha,
    }

    items: List[Dict[str, Any]] = []

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
                "FECHA Y HR SERVICIO": m.group("obs").strip(),
                "#UNIDAD": m.group("ref").strip(),
                "ACTIVIDAD": m.group("desc").strip(),
                "CANTIDAD": int(m.group("cant")),
                "SUBTOTAL": norm_money(m.group("importe")),
            })

    return header, items

def parse_ana_cecilia(pdf_bytes: bytes) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    pages = extract_pages_text(pdf_bytes)
    full = "\n".join(pages)

    # Normalizamos: sin acentos, y espacios “estándar”
    t = strip_accents(full)
    t1 = re.sub(r"\s+", " ", t).strip()   # una sola línea “limpia” para regex con DOTALL

    # ===== Encabezado =====
    empresa_raw = find_first(r"Nombre\s*receptor:\s*([A-Z0-9 ]+)", t, flags=re.I)
    empresa = prettify_receiver_name(empresa_raw)

    factura = find_first(r"Folio:\s*(\d+)", t, flags=re.I)
    uuid = find_first(r"Folio\s*fiscal:\s*([0-9A-F-]{36})", t, flags=re.I)

    # En tu PDF viene pegado: 882902026-02-0518:35:12
    mdt = re.search(
        r"Codigo\s*postal,?fechayhorade.*?(\d{5})\s*(\d{4}-\d{2}-\d{2})\s*(\d{2}:\d{2}:\d{2})",
        t1, flags=re.I
    )
    fecha_factura = f"{mdt.group(2)} {mdt.group(3)}" if mdt else ""

    header = {
        "EMPRESA": empresa,
        "#FACTURA": factura,
        "UUID": uuid,
        "FECHA FACTURA": fecha_factura,
        "FECHA Y HR SERVICIO": "",
        "#UNIDAD": "",
    }

    # ===== Conceptos =====
    # Estructura real (según el texto extraído):
    # 78181500 1.00 E48 Unidaddeservicio 300 300.000000 Siobjetodeimpuesto.
    # ...
    # Descripcion <TEXTO>
    # IVA Traslado <BASE> Tasa 8.00% <IMPORTE_IVA>
    # Numerodepedimento ...
    #
    # Vamos a capturar por cada bloque:
    # - cantidad: 1.00 -> 1
    # - actividad: lo que siga a "Descripcion" (puede cortarse en varias líneas)
    # - subtotal: "Base" (sale dentro del bloque de IVA como número)
    # - IVA: el último número después de "Tasa 8.00%"
    items: List[Dict[str, Any]] = []

    concept_pat = re.compile(
        r"(?P<clave>\d{8})\s+"
        r"(?P<cant>\d+\.\d+)\s+E48\s+Unidaddeservicio\s+"
        r"(?P<valor_unit>\d+)\s+(?P<imp_concepto>\d+\.\d+)\s+Siobjetodeimpuesto\.\s+"
        r".*?Descripcion\s+(?P<desc>.+?)\s+"
        r"IVA\s+Traslado\s+(?P<base>\d+\.\d+)\s+Tasa\s+(?P<tasa>\d+\.\d+)%\s+(?P<iva>\d+\.\d+)\s+"
        r"Numerodepedimento",
        flags=re.I | re.S
    )

    for m in concept_pat.finditer(t1):
        cant = int(float(m.group("cant")))
        desc = m.group("desc")

        # Limpieza básica
        desc = re.sub(r"\bFactor\b", " ", desc, flags=re.I)
        desc = re.sub(r"\bCuota\b", " ", desc, flags=re.I)

        # Recupera espacios típicos que pdfplumber pega
        desc = desc.replace("PARA", " PARA ")
        desc = desc.replace("EN", " EN ")
        desc = desc.replace("DE", " DE ")
        desc = desc.replace("LA", " LA ")
        desc = desc.replace("AL", " AL ")
        desc = desc.replace("A", " A ")
        desc = re.sub(r"\s+", " ", desc).strip()

        # --- #UNIDAD: lo que va después del ":" (PI59, PI123, etc.)
        unidad = ""
        mu = re.search(r":\s*([A-Z]{2}\d+)\b", desc.upper())
        if mu:
            unidad = mu.group(1).strip()

        # Si en algún caso viene "CAJA: PI-55" con guión, acepta también:
        if not unidad:
            mu2 = re.search(r":\s*([A-Z0-9\-]+)\b", desc.upper())
            if mu2:
                unidad = mu2.group(1).strip()

        base = norm_money(m.group("base"))
        iva = norm_money(m.group("iva"))

        items.append({
            **header,
            "#UNIDAD": unidad,     # <-- aquí ya se llena
            "ACTIVIDAD": desc,
            "CANTIDAD": cant,
            "SUBTOTAL": base,
            "IVA": iva,
        })

    return header, items

st.title("📄 Lector de Facturas PDF → Excel")
st.caption("Sube 1 o varios PDFs. Formatos: K9 / ROYAN / WASH N CROSS / ANA CECILIA.")

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

        elif fmt == "WASH":
            header, items = parse_wash(pdf_bytes)
            df = build_df(items, iva_rate=0.08)

        else:  # ANA_CECILIA
            header, items = parse_ana_cecilia(pdf_bytes)
            df = build_df(items, iva_rate=0.08)  # no importa la tasa, se respeta IVA

        all_dfs.append(df)
        debug_rows.append({"archivo": f.name, "formato_detectado": fmt, "filas_generadas": len(df)})

    final_df = pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame(columns=COLS)

    st.success(f"Listo: {len(final_df)} registros (de {len(files)} archivos).")
    st.dataframe(final_df, use_container_width=True)

    if show_debug:
        st.subheader("Debug")
        st.dataframe(pd.DataFrame(debug_rows), use_container_width=True)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        final_df.to_excel(writer, index=False, sheet_name="FACTURAS")

    st.download_button(
        "⬇️ Descargar Excel (con todo)",
        data=output.getvalue(),
        file_name="FACTURAS_CONSOLIDADO.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )