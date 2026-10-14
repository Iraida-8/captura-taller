import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime, date, timezone
from pages.css import load_css

APP_CHANNEL = "BETA"
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

# Preserve duplicate-check and confirmation flow across Streamlit reruns.
for key, default in {
    "folio_generado": "",
    "mostrar_confirmacion": False,
    "folio_duplicado": None,
    "confirmar_guardado": False,
    "forzar_guardado": False,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

st.title("🛠️ Captura Pase de Taller")
tab_captura, tab_consulta = st.tabs(["🛠️ Captura Pase de Taller", "🔎 Consultar Pase de Taller"])

with tab_consulta:
    st.info("Coming soon")

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

    # Refresh dependent, read-only values before their widgets are instantiated.
    # This ensures changing the unit updates both displayed fields on Streamlit reruns.
    st.session_state["tipo_caja_display"] = tipo_caja_auto
    st.session_state["tipo_unidad_display"] = tipo_unidad_auto

    # Read-only controls clearly communicate catalog-derived values.
    st.text_input("Tipo de Caja", disabled=True, key="tipo_caja_display")

    es_externo = no_unidad == "REMOLQUE EXTERNO"
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

    # Company selection is independent from the unit dropdown.
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

        # Keep all original destination columns; values no longer captured are intentionally blank/null.
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
            "Tipo de Caja": tipo_caja_auto or None,
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
        st.markdown(f"**No. de Folio:** `{st.session_state.folio_generado}`")
        if st.button("Aceptar", use_container_width=True):
            st.session_state.mostrar_confirmacion = False
            st.session_state.folio_generado = ""
            st.rerun()
    confirmacion()
