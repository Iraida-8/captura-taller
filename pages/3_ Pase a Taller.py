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

catalogos_df, empresas = cargar_catalogos()
tractores_df = cargar_tractores()

# =================================
# Session state
# =================================
if "folio_generado" not in st.session_state:
    st.session_state.folio_generado = ""

if "mostrar_confirmacion" not in st.session_state:
    st.session_state.mostrar_confirmacion = False

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

    operador = st.text_input("Operador")

    c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 3])

    if tipo_unidad_operador == "Tractores":
        unidades = ["Selecciona Unidad"] + sorted(
            tractores_filtrados["TRACTOR"].dropna().astype(str)
        )
    elif tipo_unidad_operador == "Remolques":
        unidades = (
            ["Selecciona Unidad", "REMOLQUE EXTERNO"]
            + sorted(catalogos_filtrados["CAJA"].dropna().astype(str))
        )
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

    if tipo_unidad_operador == "Tractores" and no_unidad != "Selecciona Unidad":
        fila = tractores_filtrados[
            tractores_filtrados["TRACTOR"].astype(str) == no_unidad
        ].iloc[0]
        marca_valor = fila["MARCA"]
        modelo_valor = fila["MODELO"]
        sucursal_valor = fila.get("SUCURSAL", "")

    elif tipo_unidad_operador == "Remolques":
        if no_unidad == "REMOLQUE EXTERNO":
            marca_valor = "EXTERNO"
            modelo_valor = "0000"
            sucursal_valor = "EXTERNO"
        elif no_unidad != "Selecciona Unidad":
            fila = catalogos_filtrados[
                catalogos_filtrados["CAJA"].astype(str) == no_unidad
            ].iloc[0]
            marca_valor = fila.get("MARCA", "")
            modelo_valor = fila.get("MODELO", "")
            sucursal_valor = fila.get("SUCURSAL", "")

    with c2:
        st.text_input("Marca", value=marca_valor, disabled=True)

    with c3:
        st.text_input("Modelo", value=modelo_valor, disabled=True)

    with c4:
        st.text_input("Sucursal", value=sucursal_valor, disabled=True)

    with c5:
        tipo_caja = st.selectbox(
            "Tipo de Caja",
            ["Selecciona Caja", "Caja seca", "Caja fria"]
            if tipo_unidad_operador == "Remolques"
            else ["Caja no aplicable"],
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

        # USE THE REAL FOLIO RETURNED BY GOOGLE SHEETS
        folio_real = append_pase_to_sheet(payload)
        st.session_state.folio_generado = folio_real

        st.session_state.mostrar_confirmacion = True
        st.rerun()

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
