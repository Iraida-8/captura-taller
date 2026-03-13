import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import date, datetime
from auth import require_login, require_access

# =================================
# Page configuration
# =================================
st.set_page_config(
    page_title="Captura Pase de Taller",
    layout="wide"
)

# =================================
# Hide sidebar completely
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
require_access("pase_taller")

# =================================
# Top navigation
# =================================
if st.button("⬅ Volver al Dashboard"):
    st.switch_page("pages/dashboard.py")

st.divider()

# =================================
# SUPABASE CONFIGURATION
# =================================
@st.cache_resource
def get_supabase():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_SERVICE_KEY"]
    )

supabase = get_supabase()

# =================================
# SUPABASE TABLE MAP
# =================================
TABLE_MAP = {
    "IGLOO TRANSPORT": "IGLOO",
    "LINCOLN FREIGHT": "LINCOLN",
    "PICUS": "PICUS",
    "SET FREIGHT INTERNATIONAL": "SFI",
    "SET LOGIS PLUS": "SLP"
}

EMPRESAS = list(TABLE_MAP.keys())

# =================================
# Check duplicate unit in last 24h (SUPABASE)
# =================================
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

    data = response.data

    if not data:
        return None

    return data[0]["No. de Folio"]

# =================================
# Append Pase de Taller to Supabase
# =================================
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

    prefix = prefix_map.get(data["Empresa"])

    # ---- GET LAST FOLIO ----
    response = (
        supabase.table(table_name)
        .select('"No. de Folio"')
        .ilike('"No. de Folio"', f"{prefix}%")
        .order('"No. de Folio"', desc=True)
        .limit(1)
        .execute()
    )

    last = response.data

    if last:
        num = int(last[0]["No. de Folio"].replace(prefix, ""))
        next_num = num + 1
    else:
        next_num = 1

    folio = f"{prefix}{str(next_num).zfill(5)}"

    # ---- INSERT INTO SUPABASE ----
    payload = data.copy()
    payload["No. de Folio"] = folio

    payload = {
        k: None if (pd.isna(v) or v == "")
        else v.item() if hasattr(v, "item")
        else v
        for k, v in payload.items()
    }

    try:
        response = supabase.table(table_name).insert(payload).execute()
        return folio

    except Exception as e:
        st.error(f"Supabase error: {e.args}")
        raise

# =================================
# Google Sheets configuration
# =================================
TRACTORES_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1tKWFDWD13fH6hwq-mCmuoahWFyaFfdop"
    "/export?format=csv&gid=897787433"
)

# =================================
# REMOLQUES SHEETS BY COMPANY
# =================================
REMOLQUES_SHEETS = {

    "IGLOO TRANSPORT":
        "https://docs.google.com/spreadsheets/d/1tKWFDWD13fH6hwq-mCmuoahWFyaFfdop/export?format=csv&gid=1273480736",

    "LINCOLN FREIGHT":
        "https://docs.google.com/spreadsheets/d/1tKWFDWD13fH6hwq-mCmuoahWFyaFfdop/export?format=csv&gid=459473217",

    "PICUS":
        "https://docs.google.com/spreadsheets/d/1tKWFDWD13fH6hwq-mCmuoahWFyaFfdop/export?format=csv&gid=1784212246",

    "SET FREIGHT INTERNATIONAL":
        "https://docs.google.com/spreadsheets/d/1tKWFDWD13fH6hwq-mCmuoahWFyaFfdop/export?format=csv&gid=108462367",

    "SET LOGIS PLUS":
        "https://docs.google.com/spreadsheets/d/1tKWFDWD13fH6hwq-mCmuoahWFyaFfdop/export?format=csv&gid=820737312",
}

# =================================
# Load catalogs
# =================================
@st.cache_data(ttl=3600)
def cargar_tractores():

    df = pd.read_csv(TRACTORES_URL)
    df.columns = df.columns.str.strip()
    df = df.fillna("")

    df_normalized = pd.DataFrame()

    df_normalized["TRACTOR"] = df["TRACTOR"].astype(str).str.strip()
    df_normalized["MARCA"] = df.get("MARCA", "")
    df_normalized["MODELO"] = pd.to_numeric(df.get("MODELO", ""), errors="coerce").astype("Int64")
    df_normalized["SUCURSAL"] = df.get("SUCURSAL", "")
    df_normalized["EMPRESA"] = df.get("EMPRESA", "").astype(str).str.strip()

    # remove blank rows
    df_normalized = df_normalized[df_normalized["TRACTOR"] != ""]

    return df_normalized

@st.cache_data(ttl=3600)
def cargar_remolques_empresa(empresa):

    url = REMOLQUES_SHEETS.get(empresa)

    if not url:
        return pd.DataFrame()

    df = pd.read_csv(url)
    df.columns = df.columns.str.strip()
    df = df.fillna("")

    # --- Column detection ---
    column_map = {}

    for col in df.columns:
        c = col.strip().upper()

        if c in ["CAJA", "REMOLQUE", "UNIDAD", "NO UNIDAD", "NO. UNIDAD"]:
            column_map["UNIDAD"] = col

        elif c == "MARCA":
            column_map["MARCA"] = col

        elif c == "MODELO":
            column_map["MODELO"] = col

        elif c in ["SUCURSAL", "BASE"]:
            column_map["SUCURSAL"] = col

        elif c == "TIPO DE REMOLQUE":
            column_map["TIPO_CAJA"] = col

    # --- Create normalized columns ---
    df_normalized = pd.DataFrame()

    df_normalized["UNIDAD"] = df[column_map["UNIDAD"]] if "UNIDAD" in column_map else ""
    df_normalized["MARCA"] = df[column_map["MARCA"]] if "MARCA" in column_map else ""
    df_normalized["MODELO"] = (
        pd.to_numeric(df[column_map["MODELO"]], errors="coerce").astype("Int64")
        if "MODELO" in column_map else pd.Series(dtype="Int64")
    )
    df_normalized["SUCURSAL"] = df[column_map["SUCURSAL"]] if "SUCURSAL" in column_map else ""
    df_normalized["TIPO_CAJA"] = df[column_map["TIPO_CAJA"]] if "TIPO_CAJA" in column_map else ""

    df_normalized["UNIDAD"] = df_normalized["UNIDAD"].astype(str).str.strip()
    df_normalized = df_normalized[df_normalized["UNIDAD"].str.strip() != ""]

    return df_normalized

tractores_df = cargar_tractores()

# =================================
# Session state
# =================================
if "folio_generado" not in st.session_state:
    st.session_state.folio_generado = ""

if "mostrar_confirmacion" not in st.session_state:
    st.session_state.mostrar_confirmacion = False

if "folio_duplicado" not in st.session_state:
    st.session_state.folio_duplicado = None

if "confirmar_guardado" not in st.session_state:
    st.session_state.confirmar_guardado = False

if "forzar_guardado" not in st.session_state:
    st.session_state.forzar_guardado = False

# =================================
# Page title
# =================================
st.title("🛠️ Captura Pase de Taller")

# =================================
# SECCIÓN 1 — DATOS DEL REPORTE
# =================================
st.divider()
st.subheader("Datos del Reporte")

fecha_reporte = st.date_input(
    "Fecha de Reporte",
    value=date.today()
)

tp1, tp2 = st.columns(2)
with tp1:
    tipo_proveedor = st.selectbox(
        "Tipo de Proveedor",
        ["----", "Interno", "Externo"]
    )
with tp2:
    estado = st.selectbox(
        "Estado",
        ["En Curso / Nuevo"],
        index=0,
        disabled=True
    )

st.text_input(
    "Capturó",
    value=st.session_state.user.get("name") or st.session_state.user.get("email"),
    disabled=True
)

folio_display = (
    st.session_state.folio_generado
    if st.session_state.folio_generado
    else "Folio generado al guardar"
)

c1, c2, c3 = st.columns(3)
with c1:
    oste = st.text_input("OSTE", value="", disabled=True)
with c2:
    no_reporte = st.text_input(
        "No. de Reporte",
        disabled=(tipo_proveedor != "Interno")
    )
with c3:
    st.text_input(
        "No. de Folio",
        value=folio_display,
        disabled=True
    )

# =================================
# SECCIÓN 2 — INFORMACIÓN DEL OPERADOR
# =================================
if tipo_proveedor in ["Interno", "Externo"]:

    st.divider()
    st.subheader(
        "Pase de Taller Interno"
        if tipo_proveedor == "Interno"
        else "Pase de Taller Externo"
    )

    empresa = st.selectbox(
        "Empresa",
        ["Selecciona Empresa"] + EMPRESAS
    )

    if empresa == "Selecciona Empresa":
        st.info("Selecciona una empresa para continuar con la captura del pase.")
        st.stop()

    tr1, tr2 = st.columns(2)
    with tr1:
        tipo_reporte = st.selectbox(
            "Tipo de Reporte",
            [
                "Selecciona tipo de reporte",
                "Orden Preventivo",
                "Orden Correctivo"
            ]
        )
    with tr2:
        tipo_unidad_operador = st.selectbox(
            "Tipo de Unidad",
            ["Seleccionar tipo de unidad", "Tractores", "Remolques"]
        )

    tractores_filtrados = tractores_df[
        tractores_df["EMPRESA"].astype(str).str.strip() == empresa
    ]

    remolques_df = cargar_remolques_empresa(empresa)

    operador = st.text_input("Operador")

    c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 3])

    if tipo_unidad_operador == "Tractores":
        unidades = ["Selecciona Unidad"] + sorted(
            tractores_filtrados["TRACTOR"]
            .astype(str)
            .str.strip()
            .replace("", pd.NA)
            .dropna()
            .unique()
            .tolist()
        )
    elif tipo_unidad_operador == "Remolques":

        if not remolques_df.empty:
            lista_remolques = sorted(
                remolques_df["UNIDAD"]
                .astype(str)
                .str.strip()
                .replace("", pd.NA)
                .dropna()
                .unique()
                .tolist()
            )
        else:
            lista_remolques = []

        unidades = ["Selecciona Unidad", "REMOLQUE EXTERNO"] + lista_remolques

    else:
        unidades = ["Selecciona Unidad"]

    with c1:
        no_unidad = st.selectbox(
            "No. de Unidad",
            unidades,
            disabled=tipo_unidad_operador == "Seleccionar tipo de unidad"
        )

    marca_valor = ""
    modelo_valor = ""
    sucursal_valor = ""
    tipo_caja_auto = ""

    if tipo_unidad_operador == "Tractores" and no_unidad != "Selecciona Unidad":
        fila_match = tractores_filtrados[
            tractores_filtrados["TRACTOR"].astype(str) == str(no_unidad)
        ]

        if not fila_match.empty:
            fila = fila_match.iloc[0]
        else:
            fila = {}
        marca_valor = fila["MARCA"]
        modelo_valor = fila["MODELO"]
        if pd.notna(modelo_valor):
            try:
                modelo_valor = int(float(modelo_valor))
            except:
                modelo_valor = None
        sucursal_valor = fila.get("SUCURSAL", "")

    elif tipo_unidad_operador == "Remolques":
        if no_unidad == "REMOLQUE EXTERNO":
            marca_valor = "EXTERNO"
            modelo_valor = "0000"
            sucursal_valor = "EXTERNO"
            tipo_caja_auto = ""

        elif no_unidad != "Selecciona Unidad":
            fila_match = remolques_df[
                remolques_df["UNIDAD"].astype(str) == str(no_unidad)
            ]

            if not fila_match.empty:
                fila = fila_match.iloc[0]
            else:
                fila = {}

            marca_valor = fila.get("MARCA", "")
            modelo_valor = fila.get("MODELO", "")
            sucursal_valor = fila.get("SUCURSAL", "")
            tipo_caja_auto = fila.get("TIPO_CAJA", "")

    with c2:
        st.text_input("Marca", value=marca_valor, disabled=True)

    with c3:
        st.text_input("Modelo", value=modelo_valor, disabled=True)

    with c4:
        st.text_input("Sucursal", value=sucursal_valor, disabled=True)

    with c5:

        opciones_caja = ["Selecciona Caja", "Caja seca", "Caja fria"]

        if tipo_unidad_operador == "Remolques":
            tipo_lower = str(tipo_caja_auto).lower()

            if "seca" in tipo_lower:
                index_default = 1
            elif "refriger" in tipo_lower or "fria" in tipo_lower or "frío" in tipo_lower:
                index_default = 2
            else:
                index_default = 0
        else:
            index_default = 0

        tipo_caja = st.selectbox(
            "Tipo de Caja",
            opciones_caja if tipo_unidad_operador == "Remolques" else ["Caja no aplicable"],
            index=index_default,
            disabled=tipo_unidad_operador != "Remolques"
        )


    e1, e2 = st.columns(2)
    with e1:
        no_unidad_externo = st.text_input(
            "No. de Unidad Externo",
            disabled=no_unidad != "REMOLQUE EXTERNO"
        )
    with e2:
        linea_externa = st.text_input(
            "Nombre Línea Externa",
            disabled=no_unidad != "REMOLQUE EXTERNO"
        )

    aplica_cobro = st.radio(
        "¿Aplica Cobro?",
        ["No", "Sí"],
        horizontal=True,
        index=0
    )

    responsable = st.text_input(
        "Responsable",
        disabled=aplica_cobro != "Sí"
    )

    descripcion_problema = st.text_area("Descripción del problema")

    genero_multa = st.checkbox("¿Generó multa?")

    no_inspeccion = st.text_input(
        "No. de Inspección",
        disabled=not genero_multa
    )

    reparacion_multa = st.text_area(
        "Reparación que generó multa",
        placeholder="Por favor introducir # de reporte aplicable",
        disabled=not genero_multa
    )

    st.divider()
    st.markdown("###")

    # =================================
    # GUARDAR
    # =================================
    if st.button("💾 Guardar Pase", type="primary", use_container_width=True):

        # make sure flags exist
        st.session_state.setdefault("forzar_guardado", False)
        st.session_state.setdefault("confirmar_guardado", False)
        st.session_state.setdefault("folio_duplicado", "")

        # ==========================================
        # DUPLICATE CHECK — LAST 24 HOURS
        # ==========================================
        unidad_a_buscar = (
            no_unidad_externo if no_unidad == "REMOLQUE EXTERNO" else no_unidad
        )

        folio_existente = buscar_unidad_reciente(
            empresa,
            no_unidad,
            no_unidad_externo
        )


        # If duplicate AND not forcing → ask confirmation
        if folio_existente and not st.session_state.forzar_guardado:
            st.session_state.folio_duplicado = folio_existente
            st.session_state.confirmar_guardado = True
            st.rerun()

        # ==========================================
        # NORMAL SAVE
        # ==========================================
        payload = {
            "Fecha de Captura": datetime.now().isoformat(),
            "Fecha de Reporte": str(fecha_reporte),
            "Tipo de Proveedor": tipo_proveedor,
            "Estado": "En Curso / Nuevo",
            "Capturo": st.session_state.user.get("name") or st.session_state.user.get("email"),
            "Oste": oste,
            "No. de Reporte": no_reporte,
            "Empresa": empresa,
            "Tipo de Reporte": tipo_reporte,
            "Tipo de Unidad": tipo_unidad_operador,
            "Operador": operador,
            "No. de Unidad": no_unidad,
            "Marca": marca_valor,
            "Modelo": modelo_valor,
            "Sucursal": sucursal_valor,
            "Tipo de Caja": tipo_caja,
            "No. de Unidad Externo": no_unidad_externo,
            "Nombre Linea Externa": linea_externa,
            "Cobro": str(aplica_cobro),
            "Responsable": responsable,
            "Descripcion Problema": descripcion_problema,
            "Multa": "Sí" if genero_multa else "No",
            "No. de Inspeccion": no_inspeccion,
            "Reparacion Multa": reparacion_multa,
        }

        folio_real = append_pase_to_sheet(payload)

        # 🔥 important → clear force flag after using it
        st.session_state.forzar_guardado = False

        st.session_state.folio_generado = folio_real
        st.session_state.mostrar_confirmacion = True
        st.rerun()

    # =================================
    # DUPLICATE CONFIRMATION DIALOG
    # =================================
    if st.session_state.get("confirmar_guardado", False):

        @st.dialog("Registro duplicado detectado")
        def confirmar():

            st.warning(
                f"Ya existe un pase para esta unidad en las últimas 24 horas.\n\n"
                f"**Folio existente:** {st.session_state.folio_duplicado}"
            )

            c1, c2 = st.columns(2)

            # YES → CREATE NEW
            with c1:
                if st.button("Sí, crear nuevo"):
                    st.session_state.forzar_guardado = True
                    st.session_state.confirmar_guardado = False
                    st.rerun()

            # NO → USE OLD
            with c2:
                if st.button("No, usar existente"):
                    st.session_state.folio_generado = st.session_state.folio_duplicado
                    st.session_state.confirmar_guardado = False
                    st.session_state.mostrar_confirmacion = True
                    st.rerun()

        confirmar()

    # =================================
    # SUCCESS DIALOG
    # =================================
    if st.session_state.mostrar_confirmacion:

        @st.dialog("Pase guardado")
        def confirmacion():
            st.success("Pase guardado con éxito")
            st.markdown(
                f"**No. de Folio:** `{st.session_state.folio_generado}`"
            )

            if st.button("Aceptar"):
                st.session_state.mostrar_confirmacion = False
                st.session_state.folio_generado = ""
                st.switch_page("pages/dashboard.py")

        confirmacion()