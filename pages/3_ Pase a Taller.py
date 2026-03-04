import streamlit as st
import pandas as pd
from datetime import date, datetime
from auth import require_login, require_access
import gspread
from google.oauth2.service_account import Credentials
import os

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
# Google Sheets credentials (LOCAL + CLOUD)
# =================================
def get_gsheets_credentials():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]

    # Streamlit Cloud
    if "gcp_service_account" in st.secrets:
        return Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=scopes
        )

    # Local
    if os.path.exists("google_service_account.json"):
        return Credentials.from_service_account_file(
            "google_service_account.json",
            scopes=scopes
        )

    raise RuntimeError("Google Sheets credentials not found")

# =================================
# Helpers
# =================================
def safe_value(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "Sí" if v else "No"
    return str(v)

# =================================
# Check duplicate unit in last 24h
# =================================
def buscar_unidad_reciente(empresa, no_unidad, no_unidad_externo):
    creds = get_gsheets_credentials()
    client = gspread.authorize(creds)

    SPREADSHEET_ID = "1ca46k4PCbvNMvZjsgU_2MHJULADRJS5fnghLopSWGDA"

    sheet_map = {
        "IGLOO TRANSPORT": "IGLOO",
        "LINCOLN FREIGHT": "LINCOLN",
        "PICUS": "PICUS",
        "SET FREIGHT INTERNATIONAL": "SFI",
        "SET LOGIS PLUS": "SLP",
    }

    hoja = sheet_map.get(empresa)
    if not hoja:
        return None

    ws = client.open_by_key(SPREADSHEET_ID).worksheet(hoja)
    data = ws.get_all_records()

    if not data:
        return None

    df = pd.DataFrame(data)
    df.columns = df.columns.str.strip()

    if "Fecha de Captura" not in df.columns:
        return None

    df["Fecha de Captura"] = pd.to_datetime(df["Fecha de Captura"], errors="coerce")

    limite = datetime.now() - pd.Timedelta(hours=24)

    #external trailer logic
    if no_unidad == "REMOLQUE EXTERNO":
        if "No. de Unidad Externo" not in df.columns:
            return None
        filtro = df["No. de Unidad Externo"].astype(str) == str(no_unidad_externo)
    else:
        if "No. de Unidad" not in df.columns:
            return None
        filtro = df["No. de Unidad"].astype(str) == str(no_unidad)

    recientes = df[
        filtro &
        (df["Fecha de Captura"] >= limite)
    ]

    if recientes.empty:
        return None

    return recientes.sort_values("Fecha de Captura", ascending=False).iloc[0]["No. de Folio"]

# =================================
# Append Pase de Taller to Sheet
# =================================
def append_pase_to_sheet(data: dict):
    creds = get_gsheets_credentials()
    client = gspread.authorize(creds)

    SPREADSHEET_ID = "1ca46k4PCbvNMvZjsgU_2MHJULADRJS5fnghLopSWGDA"

    sheet_map = {
        "IGLOO TRANSPORT": ("IGLOO", "IG"),
        "LINCOLN FREIGHT": ("LINCOLN", "LF"),
        "PICUS": ("PICUS", "PI"),
        "SET FREIGHT INTERNATIONAL": ("SFI", "SFI"),
        "SET LOGIS PLUS": ("SLP", "SLP"),
    }

    empresa = data["empresa"]
    sheet_name, prefix = sheet_map[empresa]

    sheet = client.open_by_key(SPREADSHEET_ID).worksheet(sheet_name)

    # ---- AUTO-INCREMENT FOLIO (COLUMN B) ----
    existing = sheet.col_values(2)[1:]  # skip header
    nums = []
    for f in existing:
        if f.startswith(prefix):
            try:
                nums.append(int(f.replace(prefix, "")))
            except:
                pass

    next_num = max(nums) + 1 if nums else 1
    folio = f"{prefix}{str(next_num).zfill(5)}"

    # ---- COLUMN ORDER MUST MATCH HEADER EXACTLY ----
    row = [
        safe_value(data["timestamp"]),
        safe_value(folio),
        safe_value(data["fecha_reporte"]),
        safe_value(data["tipo_proveedor"]),
        safe_value(data["estado"]),
        safe_value(data["capturo"]),
        safe_value(data["oste"]),
        safe_value(data["no_reporte"]),
        safe_value(data["empresa"]),
        safe_value(data["tipo_reporte"]),
        safe_value(data["tipo_unidad"]),
        safe_value(data["operador"]),
        safe_value(data["no_unidad"]),
        safe_value(data["marca"]),
        safe_value(data["modelo"]),
        safe_value(data["sucursal"]),
        safe_value(data["tipo_caja"]),
        safe_value(data["no_unidad_externo"]),
        safe_value(data["linea_externa"]),
        safe_value(data["aplica_cobro"]),
        safe_value(data["responsable"]),
        safe_value(data["descripcion"]),
        safe_value(data["genero_multa"]),
        safe_value(data["no_inspeccion"]),
        safe_value(data["reparacion_multa"]),
    ]

    sheet.append_row(row, value_input_option="USER_ENTERED")
    return folio   # authoritative folio returned

# =================================
# Google Sheets configuration
# =================================
CATALOGOS_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1qlIcKouGS2cxsCsCdNh5pMgLfWXj41dXfaeq5cyktZ8"
    "/export?format=csv&gid=0"
)

TRACTORES_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1qlIcKouGS2cxsCsCdNh5pMgLfWXj41dXfaeq5cyktZ8"
    "/export?format=csv&gid=1152583226"
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
def cargar_catalogos():
    df = pd.read_csv(CATALOGOS_URL)
    df.columns = df.columns.str.strip()
    empresas = (
        df["EMPRESA"]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )
    return df, sorted(empresas)

@st.cache_data(ttl=3600)
def cargar_tractores():
    df = pd.read_csv(TRACTORES_URL)
    df.columns = df.columns.str.strip()
    return df

@st.cache_data(ttl=3600)
def cargar_remolques_empresa(empresa):

    url = REMOLQUES_SHEETS.get(empresa)

    if not url:
        return pd.DataFrame()

    df = pd.read_csv(url)
    df.columns = df.columns.str.strip()

    # --- Column detection ---
    column_map = {}

    for col in df.columns:
        c = col.strip().upper()

        if c in ["CAJA", "REMOLQUE", "UNIDAD", "NO UNIDAD", "NO. UNIDAD"]:
            column_map["UNIDAD"] = col

        elif c in ["MARCA"]:
            column_map["MARCA"] = col

        elif c in ["MODELO"]:
            column_map["MODELO"] = col

        elif c in ["SUCURSAL", "BASE"]:
            column_map["SUCURSAL"] = col

        elif c in ["TIPO DE REMOLQUE", "TIPO REMOLQUE", "TIPO DE CAJA"]:
            column_map["TIPO_CAJA"] = col

    # --- Create normalized columns ---
    df_normalized = pd.DataFrame()

    df_normalized["UNIDAD"] = df[column_map["UNIDAD"]] if "UNIDAD" in column_map else ""
    df_normalized["MARCA"] = df[column_map["MARCA"]] if "MARCA" in column_map else ""
    df_normalized["MODELO"] = df[column_map["MODELO"]] if "MODELO" in column_map else ""
    df_normalized["SUCURSAL"] = df[column_map["SUCURSAL"]] if "SUCURSAL" in column_map else ""
    df_normalized["TIPO_CAJA"] = df[column_map["TIPO_CAJA"]] if "TIPO_CAJA" in column_map else ""

    df_normalized["UNIDAD"] = df_normalized["UNIDAD"].astype(str).str.strip()
    return df_normalized

catalogos_df, empresas = cargar_catalogos()
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
        ["Selecciona Empresa"] + empresas
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

    catalogos_filtrados = catalogos_df[
        catalogos_df["EMPRESA"].astype(str).str.strip() == empresa
    ]

    tractores_filtrados = tractores_df[
        tractores_df["EMPRESA"].astype(str).str.strip() == empresa
    ]

    remolques_df = cargar_remolques_empresa(empresa)

    operador = st.text_input("Operador")

    c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 3])

    if tipo_unidad_operador == "Tractores":
        unidades = ["Selecciona Unidad"] + sorted(
            tractores_filtrados["TRACTOR"].dropna().astype(str)
        )
    elif tipo_unidad_operador == "Remolques":

        if not remolques_df.empty:
            lista_remolques = sorted(remolques_df["UNIDAD"].dropna().astype(str))
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
            elif "fria" in tipo_lower or "frío" in tipo_lower:
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
            "timestamp": datetime.now().isoformat(),
            "fecha_reporte": str(fecha_reporte),
            "tipo_proveedor": tipo_proveedor,
            "estado": "En Curso / Nuevo",
            "capturo": st.session_state.user.get("name") or st.session_state.user.get("email"),
            "oste": oste,
            "no_reporte": no_reporte,
            "empresa": empresa,
            "tipo_reporte": tipo_reporte,
            "tipo_unidad": tipo_unidad_operador,
            "operador": operador,
            "no_unidad": no_unidad,
            "marca": marca_valor,
            "modelo": modelo_valor,
            "sucursal": sucursal_valor,
            "tipo_caja": tipo_caja,
            "no_unidad_externo": no_unidad_externo,
            "linea_externa": linea_externa,
            "aplica_cobro": aplica_cobro,
            "responsable": responsable,
            "descripcion": descripcion_problema,
            "genero_multa": genero_multa,
            "no_inspeccion": no_inspeccion,
            "reparacion_multa": reparacion_multa,
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
                st.switch_page("pages/dashboard.py")

        confirmacion()