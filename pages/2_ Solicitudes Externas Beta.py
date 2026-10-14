import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime, date, timezone
from html import escape
import resend  #type: ignore
from pages.css import load_css

APP_CHANNEL = "BETA"
#APP_CHANNEL = "RELEASE"

st.set_page_config(
    page_title="Captura Pase de Taller BETA" if APP_CHANNEL == "BETA" else "Captura Pase de Taller",
    layout="wide",
)
load_css()
# Mobile-first sizing: full-width controls, comfortable touch targets, and stacked fields on phones.
st.markdown("""
<style>
  .block-container { padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1050px; }
  div[data-testid="stTabs"] button[role="tab"] { min-height: 3.2rem; padding: .75rem 1rem; font-size: 1.05rem; font-weight: 650; }
  div[data-testid="stWidgetLabel"] p { font-size: 1.02rem; font-weight: 600; }
  div[data-baseweb="select"] > div, div[data-baseweb="input"] > div { min-height: 3.15rem; }
  div[data-baseweb="select"] input, div[data-baseweb="input"] input { font-size: 1.05rem; }
  textarea { font-size: 1.05rem !important; }
  div.stButton > button { min-height: 3.4rem; font-size: 1.08rem; font-weight: 700; border-radius: .65rem; }
  @media (max-width: 640px) {
    .block-container { padding-left: .85rem; padding-right: .85rem; }
    div[data-testid="stTabs"] button[role="tab"] { font-size: .88rem; padding: .6rem .35rem; min-height: 3.5rem; }
    h1 { font-size: 1.65rem !important; }
    h2, h3 { font-size: 1.25rem !important; }
  }
</style>
""", unsafe_allow_html=True)
@st.cache_resource
def get_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_SERVICE_KEY"])
supabase = get_supabase()
EMAIL_EMPRESA_MAP = {
    "IGLOO TRANSPORT": "IGLOO",
    "LINCOLN FREIGHT": "LINCOLN",
    "PICUS": "PICUS",
    "SET FREIGHT INTERNATIONAL": "SET FREIGHT",
    "SET LOGIS PLUS": "SET LOGIS PLUS",
}
def enviar_correo_nuevo_pase(folio: str, datos: dict) -> list[str]:
    """Send new-pass notifications to every recipient configured for CONTROL."""
    respuesta = (
        supabase.table("lista_correo_viaticos")
        .select("email")
        .eq("empresa", "CONTROL")
        .execute()
    )
    destinatarios = sorted({
        str(fila.get("email") or "").strip()
        for fila in (respuesta.data or [])
        if str(fila.get("email") or "").strip()
    }, key=str.lower)
    if not destinatarios:
        raise ValueError(
            "No se encontraron destinatarios en lista_correo_viaticos con empresa CONTROL."
        )
    resend.api_key = st.secrets["RESEND_API_KEY"]
    def valor(campo):
        contenido = datos.get(campo)
        return escape(str(contenido).strip()) if contenido not in (None, "") else "—"
    campos = [
        ("Empresa a cobrar", "Empresa"),
        ("Fecha de captura", "Fecha de Captura"),
        ("Estado", "Estado"),
        ("No. de Unidad", "No. de Unidad"),
        ("Tipo de Unidad", "Tipo de Unidad"),
        ("Tipo de Caja", "Tipo de Caja"),
        ("No. de Unidad Externo", "No. de Unidad Externo"),
        ("Nombre Línea Externa", "Nombre Linea Externa"),
    ]
    filas_html = "".join(
        f"<tr><td style='padding:8px;border-bottom:1px solid #e5e7eb;color:#555;width:38%'><b>{escape(etiqueta)}</b></td>"
        f"<td style='padding:8px;border-bottom:1px solid #e5e7eb'>{valor(campo)}</td></tr>"
        for etiqueta, campo in campos
    )
    observaciones = valor("Descripcion Problema").replace("\\n", "<br>")
    correo_html = f"""
    <div style="font-family:Arial,sans-serif;color:#202124;max-width:680px;margin:auto">
      <div style="background:#151F6D;color:white;padding:22px 26px;border-radius:12px 12px 0 0">
        <div style="font-size:13px;opacity:.9">CAPTURA PASE DE TALLER</div>
        <h1 style="font-size:24px;margin:8px 0 0">Nuevo pase registrado</h1>
      </div>
      <div style="border:1px solid #e5e7eb;border-top:0;padding:24px;border-radius:0 0 12px 12px">
        <p>Se generó un nuevo folio al guardar un Pase de Taller.</p>
        <div style="background:#f3f5ff;border:1px solid #dbe2ff;border-radius:8px;padding:16px;margin:16px 0">
          <div style="font-size:12px;color:#555">NO. DE FOLIO</div>
          <div style="font-size:25px;font-weight:800;color:#151F6D;margin-top:4px">{escape(folio)}</div>
        </div>
        <table style="width:100%;border-collapse:collapse">{filas_html}</table>
        <h3 style="color:#151F6D;margin:22px 0 8px">Observaciones y comentarios</h3>
        <div style="background:#f8f9fa;border-radius:8px;padding:14px;white-space:normal">{observaciones}</div>
      </div>
    </div>
    """
    resend.Emails.send({
        "from": "PG Data Analyst <notificaciones@pgdataanalyst.com>",
        "to": destinatarios,
        "subject": f"Nuevo Pase de Taller: {folio}",
        "html": correo_html,
    })
    return destinatarios
@st.cache_data(ttl=3600)
def cargar_todas_unidades_supabase():
    """Fetch the full vehicle catalog; unit choice is not filtered by company."""
    response = supabase.table("vehicle_units").select("*").execute()
    df = pd.DataFrame(response.data or [])
    if df.empty:
        return df
    for col in ("unidad", "tipo_unidad", "empresa"):
        if col not in df:
            df[col] = ""
    df["unidad"] = df["unidad"].fillna("").astype(str).str.strip()
    df["tipo_unidad"] = df["tipo_unidad"].fillna("").astype(str).str.upper().str.strip()
    df["empresa"] = df["empresa"].fillna("").astype(str).str.upper().str.strip()
    return df[df["unidad"].ne("")].drop_duplicates(subset=["unidad"], keep="first")
TABLE_MAP = {
    "IGLOO TRANSPORT": "IGLOO",
    "LINCOLN FREIGHT": "LINCOLN",
    "PICUS": "PICUS",
    "SET FREIGHT INTERNATIONAL": "SFI",
    "SET LOGIS PLUS": "SLP",
}
EMPRESA_CODIGOS = {
    "IGLOO TRANSPORT": "IGT",
    "LINCOLN FREIGHT": "LIN",
    "PICUS": "PIC",
    "SET FREIGHT INTERNATIONAL": "SET",
    "SET LOGIS PLUS": "SLP",
}
EMPRESAS = list(TABLE_MAP.keys())
def buscar_unidad_reciente(empresa, no_unidad, no_unidad_externo):
    table_name = TABLE_MAP[empresa]
    unidad = no_unidad_externo if no_unidad == "REMOLQUE EXTERNO" else no_unidad
    limite = (datetime.now() - pd.Timedelta(hours=24)).isoformat()
    response = (
        supabase.table(table_name)
        .select('"No. de Folio", "Fecha de Captura"')
        .eq('"No. de Unidad"', unidad)
        .gte('"Fecha de Captura"', limite)
        .order('"Fecha de Captura"', desc=True)
        .limit(1)
        .execute()
    )
    data = response.data or []
    return data[0].get("No. de Folio") if data else None
def append_pase_to_sheet(data: dict):
    empresa = data["Empresa"]
    table_name = TABLE_MAP[empresa]
    prefix_map = {
        "IGLOO TRANSPORT": "IG",
        "LINCOLN FREIGHT": "LF",
        "PICUS": "PI",
        "SET FREIGHT INTERNATIONAL": "SFI",
        "SET LOGIS PLUS": "SLP",
    }
    prefix = prefix_map[empresa]
    response = (
        supabase.table(table_name)
        .select('"No. de Folio"')
        .ilike('"No. de Folio"', f"{prefix}%")
        .order('"No. de Folio"', desc=True)
        .limit(1)
        .execute()
    )
    last = response.data or []
    next_num = int(last[0]["No. de Folio"].replace(prefix, "")) + 1 if last else 1
    folio = f"{prefix}{str(next_num).zfill(5)}"
    payload = data.copy()
    payload["No. de Folio"] = folio
    payload = {
        key: None if (pd.isna(value) or value == "")
        else value.item() if hasattr(value, "item")
        else value
        for key, value in payload.items()
    }
    try:
        supabase.table(table_name).insert(payload).execute()
        return folio
    except Exception as exc:
        st.error(f"Error de Supabase al guardar: {exc}")
        raise
def buscar_folio_en_todas_empresas(folio: str):
    """Search an exact folio across each company's destination table."""
    folio = str(folio or "").strip()
    if not folio:
        return []
    resultados = []
    errores = []
    for empresa_nombre, table_name in TABLE_MAP.items():
        try:
            response = (
                supabase.table(table_name)
                .select("*")
                .eq('"No. de Folio"', folio)
                .limit(2)
                .execute()
            )
            for registro in (response.data or []):
                resultados.append({"empresa_tabla": empresa_nombre, "tabla": table_name, "registro": registro})
        except Exception as exc:
            errores.append(f"{table_name}: {exc}")
    if errores and not resultados:
        raise RuntimeError("No se pudo consultar Supabase. " + " | ".join(errores))
    return resultados
def crear_pdf_pase(registro: dict, empresa_tabla: str) -> bytes:
    """Create a simple, styled PDF using only Python's standard library."""
    import textwrap
    PAGE_W, PAGE_H = 612, 792  # US Letter, points
    NAVY = (21 / 255, 31 / 255, 109 / 255)
    LIGHT = (0.95, 0.96, 0.985)
    GREY = (0.35, 0.37, 0.42)
    MARGIN = 48
    def clean(value):
        if value is None or str(value).strip().lower() in ("", "none", "nan"):
            return "—"
        return str(value).replace("\r", "").strip()
    # Content is stored as WinAnsi-compatible hex strings to preserve accents safely.
    def pdf_text(value):
        encoded = str(value).encode("cp1252", errors="replace")
        return encoded.hex().upper()
    # Each entry: (kind, text, optional label/value pair)
    lines = [
        ("title", "PASE DE TALLER"),
        ("subtitle", f"Solicitud registrada · {empresa_tabla}"),
        ("folio", f"NO. DE FOLIO:  {clean(registro.get('No. de Folio'))}"),
        ("section", "DATOS DEL PASE"),
    ]
    def field(label, key):
        value = clean(registro.get(key))
        lines.append(("field", f"{label}:  {value}"))
    for label, key in [
        ("Fecha de captura", "Fecha de Captura"),
        ("Fecha de reporte", "Fecha de Reporte"),
        ("Estado", "Estado"),
        ("Empresa", "Empresa"),
        ("Tipo de reporte", "Tipo de Reporte"),
        ("Tipo de proveedor", "Tipo de Proveedor"),
    ]:
        field(label, key)
    lines.append(("section", "DATOS DE LA UNIDAD"))
    for label, key in [
        ("No. de Unidad", "No. de Unidad"),
        ("Tipo de unidad", "Tipo de Unidad"),
        ("Tipo de caja", "Tipo de Caja"),
        ("No. de Unidad Externo", "No. de Unidad Externo"),
        ("Nombre Línea Externa", "Nombre Linea Externa"),
        ("Operador", "Operador"),
        ("Marca", "Marca"),
        ("Modelo", "Modelo"),
        ("Sucursal", "Sucursal"),
    ]:
        field(label, key)
    lines.append(("section", "OBSERVACIONES Y COMENTARIOS"))
    comments = clean(registro.get("Descripcion Problema"))
    for para in comments.splitlines() or ["—"]:
        wrapped = textwrap.wrap(para, width=82, break_long_words=True, replace_whitespace=False) or [" "]
        for chunk in wrapped:
            lines.append(("comment", chunk))
    lines.append(("section", "SEGUIMIENTO Y COBRO"))
    for label, key in [
        ("No. de Reporte", "No. de Reporte"),
        ("No. de Inspección", "No. de Inspeccion"),
        ("Proveedor", "Proveedor"),
        ("Razones", "Razones"),
        ("Cobro", "Cobro"),
        ("Multa", "Multa"),
        ("Reparación de multa", "Reparacion Multa"),
        ("Capturó", "Capturo"),
        ("Responsable", "Responsable"),
        ("Oste", "Oste"),
    ]:
        field(label, key)
    # Keep a small footer on every page and split naturally across pages.
    pages, current, used = [], [], 0
    heights = {"title": 32, "subtitle": 24, "folio": 38, "section": 25, "field": 22, "comment": 17}
    available = PAGE_H - 120
    for item in lines:
        h = heights[item[0]]
        if current and used + h > available:
            pages.append(current)
            current, used = [], 0
        current.append(item)
        used += h
    if current:
        pages.append(current)
    objects = [None]  # PDF objects are 1-indexed
    def add_obj(content):
        objects.append(content if isinstance(content, bytes) else content.encode("latin-1"))
        return len(objects) - 1
    catalog_id = add_obj(b"")
    pages_id = add_obj(b"")
    font_regular_id = add_obj(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    font_bold_id = add_obj(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")
    page_ids = []
    for page_no, page_lines in enumerate(pages, start=1):
        ops = []
        # Header band on the first page; continuation pages start on white background.
        if page_no == 1:
            ops.append(f"{NAVY[0]:.3f} {NAVY[1]:.3f} {NAVY[2]:.3f} rg 0 {PAGE_H-92} {PAGE_W} 92 re f")
            y = PAGE_H - 49
        else:
            y = PAGE_H - 50
        for kind, text in page_lines:
            if kind == "title":
                ops.append("1 1 1 rg")
                ops.append(f"BT /F2 20 Tf 1 0 0 1 {MARGIN} {y} Tm <{pdf_text(text)}> Tj ET")
                y -= heights[kind]
            elif kind == "subtitle":
                ops.append("0.92 0.93 0.98 rg")
                ops.append(f"BT /F1 9 Tf 1 0 0 1 {MARGIN} {y} Tm <{pdf_text(text)}> Tj ET")
                y -= heights[kind]
            elif kind == "folio":
                y -= 2
                ops.append(f"{LIGHT[0]:.3f} {LIGHT[1]:.3f} {LIGHT[2]:.3f} rg {MARGIN} {y-12} {PAGE_W-2*MARGIN} 32 re f")
                ops.append(f"{NAVY[0]:.3f} {NAVY[1]:.3f} {NAVY[2]:.3f} RG 0.8 w {MARGIN} {y-12} {PAGE_W-2*MARGIN} 32 re S")
                ops.append(f"{NAVY[0]:.3f} {NAVY[1]:.3f} {NAVY[2]:.3f} rg BT /F2 12 Tf 1 0 0 1 {MARGIN+12} {y+1} Tm <{pdf_text(text)}> Tj ET")
                y -= heights[kind]
            elif kind == "section":
                y -= 3
                ops.append(f"{NAVY[0]:.3f} {NAVY[1]:.3f} {NAVY[2]:.3f} rg {MARGIN} {y-5} {PAGE_W-2*MARGIN} 18 re f")
                ops.append(f"1 1 1 rg BT /F2 9 Tf 1 0 0 1 {MARGIN+8} {y} Tm <{pdf_text(text)}> Tj ET")
                y -= heights[kind]
            else:
                if kind == "field":
                    label, sep, val = text.partition(":  ")
                    ops.append(f"{GREY[0]:.3f} {GREY[1]:.3f} {GREY[2]:.3f} rg BT /F2 8.5 Tf 1 0 0 1 {MARGIN+5} {y} Tm <{pdf_text(label + ':')}> Tj ET")
                    val_x = MARGIN + 160
                    value_chunks = textwrap.wrap(val if sep else "", width=65, break_long_words=True) or ["—"]
                    ops.append(f"0.10 0.11 0.15 rg BT /F1 9 Tf 1 0 0 1 {val_x} {y} Tm <{pdf_text(value_chunks[0])}> Tj ET")
                    for extra in value_chunks[1:]:
                        y -= 13
                        ops.append(f"0.10 0.11 0.15 rg BT /F1 9 Tf 1 0 0 1 {val_x} {y} Tm <{pdf_text(extra)}> Tj ET")
                else:
                    ops.append(f"0.10 0.11 0.15 rg BT /F1 9 Tf 1 0 0 1 {MARGIN+8} {y} Tm <{pdf_text(text)}> Tj ET")
                y -= heights[kind]
        ops.append(f"0.55 0.56 0.60 rg BT /F1 8 Tf 1 0 0 1 {MARGIN} 28 Tm <{pdf_text('Captura Pase de Taller  |  Página ' + str(page_no) + ' de ' + str(len(pages)))}> Tj ET")
        stream = ("\n".join(ops)).encode("ascii")
        stream_id = add_obj(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")
        page_id = add_obj(
            f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 {PAGE_W} {PAGE_H}] "
            f"/Resources << /Font << /F1 {font_regular_id} 0 R /F2 {font_bold_id} 0 R >> >> "
            f"/Contents {stream_id} 0 R >>"
        )
        page_ids.append(page_id)
    objects[catalog_id] = f"<< /Type /Catalog /Pages {pages_id} 0 R >>".encode("ascii")
    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    objects[pages_id] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode("ascii")
    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for obj in objects[1:]:
        offsets.append(len(output))
        output.extend(f"{len(offsets) - 1} 0 obj\n".encode("ascii"))
        output.extend(obj)
        output.extend(b"\nendobj\n")
    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects)}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(
        f"trailer\n<< /Size {len(objects)} /Root {catalog_id} 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode("ascii")
    )
    return bytes(output)
# Preserve duplicate-check and confirmation flow across Streamlit reruns.
for key, default in {
    "folio_generado": "",
    "mostrar_confirmacion": False,
    "folio_duplicado": None,
    "confirmar_guardado": False,
    "forzar_guardado": False,
    "folio_consulta_resultados": None,
    "folio_consulta_busqueda": "",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default
# Reset widget values at the start of a rerun, before Streamlit creates those widgets.
if st.session_state.pop("limpiar_captura_pendiente", False):
    for key in (
        "captura_no_unidad",
        "tipo_caja_externo",
        "tipo_caja_display",
        "tipo_unidad_display",
        "no_unidad_externo",
        "linea_externa",
        "empresa_cobrar",
        "observaciones_comentarios",
        "_unidad_anterior_empresa",
        "forzar_guardado",
        "confirmar_guardado",
        "folio_duplicado",
    ):
        st.session_state.pop(key, None)
st.title("🛠️ Captura Pase de Taller")
tab_captura, tab_consulta = st.tabs(["🛠️ Captura Pase de Taller", "🔎 Consultar Pase de Taller"])
with tab_consulta:
    st.markdown("### Consulta de pases registrados")
    st.caption("Busca por No. de Folio. La consulta revisa las tablas de todas las empresas y muestra el registro encontrado.")
    with st.form("form_buscar_folio", clear_on_submit=False):
        col_search, col_button = st.columns([4, 1], vertical_alignment="bottom")
        with col_search:
            folio_busqueda = st.text_input(
                "No. de Folio",
                placeholder="Ej. IG00001, LF00025, PI00012",
                key="folio_consulta_input",
            )
        with col_button:
            buscar_folio = st.form_submit_button("🔎 Buscar", type="primary", use_container_width=True)
    if buscar_folio:
        if not folio_busqueda.strip():
            st.warning("Escribe un No. de Folio para buscar.")
            st.session_state.folio_consulta_resultados = None
        else:
            try:
                with st.spinner("Buscando folio en las tablas de empresas..."):
                    resultados = buscar_folio_en_todas_empresas(folio_busqueda.strip())
                st.session_state.folio_consulta_resultados = resultados
                st.session_state.folio_consulta_busqueda = folio_busqueda.strip()
            except Exception as exc:
                st.session_state.folio_consulta_resultados = None
                st.error(f"No se pudo completar la búsqueda en Supabase: {exc}")
    resultados = st.session_state.get("folio_consulta_resultados")
    if resultados is not None:
        if not resultados:
            st.warning(f"No se encontró el folio **{st.session_state.get('folio_consulta_busqueda', '')}** en las tablas de empresas.")
        elif len(resultados) > 1:
            st.warning("El folio aparece en más de una tabla. Revisa los registros encontrados.")
        for idx, resultado in enumerate(resultados or []):
            registro = resultado["registro"]
            empresa_tabla = resultado["empresa_tabla"]
            folio = str(registro.get("No. de Folio") or st.session_state.get("folio_consulta_busqueda", "pase")).strip()
            estado = str(registro.get("Estado") or "Sin estado")
            st.markdown(
                f"<div style='border:1px solid #d9deea;border-radius:14px;padding:18px 20px;margin:12px 0 8px;background:linear-gradient(135deg,#f8f9fd,#ffffff)'>"
                f"<div style='font-size:0.82rem;color:#666'>PASE DE TALLER · {escape(empresa_tabla)}</div>"
                f"<div style='font-size:1.45rem;font-weight:800;color:#151F6D;margin:4px 0 10px'>{escape(folio)}</div>"
                f"<span style='display:inline-block;background:#e7ecf9;color:#151F6D;padding:5px 10px;border-radius:999px;font-size:.85rem;font-weight:700'>{escape(estado)}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
            # Highlight the common fields first, then make the full stored row available.
            left, right = st.columns(2)
            with left:
                st.markdown("**Unidad**")
                st.write(registro.get("No. de Unidad") or "—")
                st.markdown("**Tipo de unidad / caja**")
                st.write(" · ".join(str(registro.get(k)) for k in ("Tipo de Unidad", "Tipo de Caja") if registro.get(k)) or "—")
                st.markdown("**No. de Unidad Externo**")
                st.write(registro.get("No. de Unidad Externo") or "—")
                st.markdown("**Nombre Línea Externa**")
                st.write(registro.get("Nombre Linea Externa") or "—")
            with right:
                st.markdown("**Empresa a cobrar**")
                st.write(registro.get("Empresa") or empresa_tabla)
                st.markdown("**Fecha de captura**")
                st.write(registro.get("Fecha de Captura") or "—")
                st.markdown("**Fecha de reporte**")
                st.write(registro.get("Fecha de Reporte") or "—")
                st.markdown("**Estado**")
                st.write(estado)
            st.markdown("**Observaciones y comentarios**")
            st.write(registro.get("Descripcion Problema") or "Sin observaciones registradas.")
            with st.expander("Ver todos los campos guardados"):
                detalle = pd.DataFrame(
                    [{"Campo": str(k), "Valor": "—" if v is None or str(v).strip() == "" else str(v)} for k, v in registro.items()]
                )
                st.dataframe(detalle, hide_index=True, use_container_width=True)
            try:
                pdf_bytes = crear_pdf_pase(registro, empresa_tabla)
                st.download_button(
                    "🖨️ Imprimir / Guardar solicitud (PDF)",
                    data=pdf_bytes,
                    file_name=f"Pase_de_Taller_{folio}.pdf",
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True,
                    key=f"descargar_pdf_{idx}_{folio}",
                    help="Descarga un PDF listo para imprimir o guardar.",
                )
            except Exception as exc:
                st.error(f"No se pudo generar el PDF: {exc}")
            if idx < len(resultados) - 1:
                st.divider()
with tab_captura:
    st.caption("Capture los datos esenciales del pase. Los demás campos del registro se guardan vacíos o como null.")
    unidades_df = cargar_todas_unidades_supabase()
    if unidades_df.empty:
        st.warning("No fue posible cargar el catálogo de unidades. Verifica la tabla vehicle_units.")
        st.stop()
    unidad_options = ["Selecciona Unidad", "REMOLQUE EXTERNO"] + sorted(
        u for u in unidades_df["unidad"].dropna().unique().tolist()
        if u and u.upper() != "REMOLQUE EXTERNO"
    )
    no_unidad = st.selectbox(
        "No. de Unidad",
        unidad_options,
        index=0,
        help="Busca la unidad en el catálogo. La lista incluye todas las empresas.",
        key="captura_no_unidad",
    )
    fila = pd.Series(dtype=object)
    if no_unidad not in ("Selecciona Unidad", "REMOLQUE EXTERNO"):
        match = unidades_df[unidades_df["unidad"].astype(str).eq(str(no_unidad))]
        if not match.empty:
            fila = match.iloc[0]
    raw_tipo_unidad = str(fila.get("tipo_unidad", "") or "").strip().upper()
    tipo_unidad_auto = "Tractores" if raw_tipo_unidad == "TRACTOR" else (
        "Remolques" if raw_tipo_unidad in ("CAJA SECA", "CAJA REFRIGERADA") else ""
    )
    tipo_caja_auto = "Caja Seca" if "SECA" in raw_tipo_unidad else (
        "Caja Refrigerada" if "REFRIGERADA" in raw_tipo_unidad or "REFRIGER" in raw_tipo_unidad else ""
    )
    if no_unidad == "REMOLQUE EXTERNO":
        tipo_unidad_auto = "Remolques"
        tipo_caja_auto = ""
    es_externo = no_unidad == "REMOLQUE EXTERNO"
    # Keep catalog-derived values synchronized with the selected unit.
    st.session_state["tipo_unidad_display"] = tipo_unidad_auto
    # External trailers have no catalog type, so let the operator choose the box type.
    if es_externo:
        if "tipo_caja_externo" not in st.session_state:
            st.session_state["tipo_caja_externo"] = "Caja Seca"
        tipo_caja = st.selectbox(
            "Tipo de Caja",
            ["Caja Seca", "Caja Refrigerada"],
            key="tipo_caja_externo",
        )
    else:
        st.session_state["tipo_caja_display"] = tipo_caja_auto
        st.text_input("Tipo de Caja", disabled=True, key="tipo_caja_display")
        tipo_caja = tipo_caja_auto
    # Suggest the charge company from the selected catalog unit, but allow manual override.
    # Only reset the selectbox when the unit selection itself changes.
    empresa_por_codigo = {
        "IGT": "IGLOO TRANSPORT",
        "LIN": "LINCOLN FREIGHT",
        "PIC": "PICUS",
        "SET": "SET FREIGHT INTERNATIONAL",
        "SLP": "SET LOGIS PLUS",
    }
    empresa_por_catalogo = {
        **{name: name for name in EMPRESAS},
        **empresa_por_codigo,
    }
    unidad_anterior = st.session_state.get("_unidad_anterior_empresa")
    if no_unidad != unidad_anterior:
        empresa_sugerida = empresa_por_catalogo.get(
            str(fila.get("empresa", "") or "").strip().upper()
        )
        if empresa_sugerida in EMPRESAS:
            st.session_state["empresa_cobrar"] = empresa_sugerida
        elif "empresa_cobrar" not in st.session_state:
            st.session_state["empresa_cobrar"] = EMPRESAS[0]
        st.session_state["_unidad_anterior_empresa"] = no_unidad
    if not es_externo:
        # Avoid retaining stale external-unit details when switching back to a catalog unit.
        st.session_state["no_unidad_externo"] = ""
        st.session_state["linea_externa"] = ""
    no_unidad_externo = st.text_input(
        "No. de Unidad Externo",
        disabled=not es_externo,
        placeholder="Escribe el número externo",
        key="no_unidad_externo",
    )
    linea_externa = st.text_input(
        "Nombre Línea Externa",
        disabled=not es_externo,
        placeholder="Escribe el nombre de la línea",
        key="linea_externa",
    )
    st.text_input("Tipo de Unidad", disabled=True, key="tipo_unidad_display")
    empresa = st.selectbox(
        "Empresa a Cobrar",
        EMPRESAS,
        key="empresa_cobrar",
    )
    descripcion_problema = st.text_area(
        "Observaciones y Comentarios",
        placeholder="Describe brevemente el problema o los comentarios relevantes",
        height=150,
        key="observaciones_comentarios",
    )
    st.divider()
    guardar = st.button("💾 Guardar Pase de Taller", type="primary", use_container_width=True, key="guardar_pase_simplificado")
    if guardar:
        if no_unidad == "Selecciona Unidad":
            st.error("Debes seleccionar un No. de Unidad válido antes de guardar.")
            st.stop()
        if es_externo and not no_unidad_externo.strip():
            st.error("Debes capturar el No. de Unidad Externo.")
            st.stop()
        st.session_state.setdefault("forzar_guardado", False)
        st.session_state.setdefault("confirmar_guardado", False)
        folio_existente = buscar_unidad_reciente(empresa, no_unidad, no_unidad_externo)
        if folio_existente and not st.session_state.forzar_guardado:
            st.session_state.folio_duplicado = folio_existente
            st.session_state.confirmar_guardado = True
            st.rerun()
        payload = {
            "Fecha de Captura": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "Fecha de Reporte": str(date.today()),
            "Tipo de Proveedor": None,
            "Proveedor": None,
            "Razones": None,
            "Estado": "Por Completar",
            "Capturo": None,
            "Oste": None,
            "No. de Reporte": None,
            "Empresa": empresa,
            "Tipo de Reporte": None,
            "Tipo de Unidad": tipo_unidad_auto or None,
            "Operador": None,
            "No. de Unidad": no_unidad,
            "Marca": None,
            "Modelo": None,
            "Sucursal": None,
            "Tipo de Caja": tipo_caja or None,
            "No. de Unidad Externo": no_unidad_externo if es_externo else None,
            "Nombre Linea Externa": linea_externa if es_externo else None,
            "Cobro": None,
            "Responsable": None,
            "Descripcion Problema": descripcion_problema,
            "Multa": None,
            "No. de Inspeccion": None,
            "Reparacion Multa": None,
        }
        folio_real = append_pase_to_sheet(payload)
        st.session_state.forzar_guardado = False
        st.session_state.folio_generado = folio_real
        try:
            destinatarios_email = enviar_correo_nuevo_pase(folio_real, payload)
            st.session_state.email_pase_estado = "enviado"
            st.session_state.email_pase_destinatarios = destinatarios_email
            st.session_state.pop("email_pase_error", None)
        except Exception as email_exc:
            # The pass is already saved; an email failure must not undo the save.
            st.session_state.email_pase_estado = "error"
            st.session_state.email_pase_error = str(email_exc)
            st.session_state.pop("email_pase_destinatarios", None)
        st.session_state.mostrar_confirmacion = True
        st.rerun()
if st.session_state.get("confirmar_guardado", False):
    @st.dialog("Registro duplicado detectado")
    def confirmar():
        st.warning(
            "Ya existe un pase para esta unidad en las últimas 24 horas.\n\n"
            f"**Folio existente:** {st.session_state.folio_duplicado}"
        )
        col_yes, col_no = st.columns(2, gap="large")
        with col_yes:
            if st.button("Sí, crear nuevo", use_container_width=True):
                st.session_state.forzar_guardado = True
                st.session_state.confirmar_guardado = False
                st.rerun()
        with col_no:
            if st.button("No, usar existente", use_container_width=True):
                st.session_state.folio_generado = st.session_state.folio_duplicado
                st.session_state.confirmar_guardado = False
                st.session_state.mostrar_confirmacion = True
                st.rerun()
    confirmar()
if st.session_state.get("mostrar_confirmacion", False):
    @st.dialog("Pase guardado")
    def confirmacion():
        st.success("Pase guardado con éxito")
        st.markdown(f"**No. de Folio:** \`{st.session_state.folio_generado}\`")
        if st.session_state.get("email_pase_estado") == "enviado":
            total_destinatarios = len(st.session_state.get("email_pase_destinatarios", []))
            st.caption(f"Notificación enviada por correo a {total_destinatarios} destinatario(s).")
        elif st.session_state.get("email_pase_estado") == "error":
            st.warning(f"El pase sí se guardó, pero no se pudo enviar el correo: {st.session_state.get('email_pase_error', 'Error desconocido')}")
        if st.button("Aceptar", use_container_width=True):
            st.session_state.mostrar_confirmacion = False
            st.session_state.folio_generado = ""
            # Defer widget cleanup until the next run, before widgets are instantiated.
            st.session_state["limpiar_captura_pendiente"] = True
            for key in ("email_pase_estado", "email_pase_destinatarios", "email_pase_error"):
                st.session_state.pop(key, None)
            st.rerun()
    confirmacion()
