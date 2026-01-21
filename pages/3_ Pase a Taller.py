import streamlit as st
import pandas as pd
from datetime import date
import random

# =================================
# Page configuration
# =================================
st.set_page_config(
    page_title="Captura Pase de Taller",
    layout="wide"
)

# =================================
# Fake logged-in users (TEMP)
# =================================
USUARIOS_FAKE = [
    "Juan Pérez",
    "María González",
    "Carlos Ramírez",
    "Ana López",
    "Luis Hernández",
    "Fernanda Torres"
]

if "usuario_actual" not in st.session_state:
    st.session_state.usuario_actual = random.choice(USUARIOS_FAKE)

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
# Folio generator
# =================================
def generar_folio(empresa: str) -> str:
    prefijos = {
        "IGLOO TRANSPORT": "IG",
        "LINCOLN FREIGHT": "LF",
        "PICUS": "PI",
        "SET FREIGHT INTERNATIONAL": "SFI",
        "SET LOGIS PLUS": "SLP",
    }
    return f"{prefijos.get(empresa, 'XX')}{str(1).zfill(5)}"

# =================================
# State
# =================================
if "folio_generado" not in st.session_state:
    st.session_state.folio_generado = ""

if "mostrar_confirmacion" not in st.session_state:
    st.session_state.mostrar_confirmacion = False

# =================================
# HEADER
# =================================
st.title("🛠️ Captura Pase de Taller")

# =================================
# DATOS DEL REPORTE
# =================================
st.divider()
st.subheader("Datos del Reporte")

st.date_input("Fecha de reporte", value=date.today())

tipo_proveedor = st.selectbox(
    "Tipo de proveedor",
    ["----", "Interno", "Externo"]
)

st.text_input(
    "No. de Folio",
    value=st.session_state.folio_generado or "folio generado al guardar",
    disabled=True
)

c1, c2 = st.columns(2)
with c1:
    st.text_input("OSTE", disabled=True)
with c2:
    st.text_input("No. de Reporte", disabled=True)

st.text_input(
    "Capturó",
    st.session_state.usuario_actual,
    disabled=True
)

st.selectbox(
    "Estado",
    ["En Curso/Nuevo"],
    index=0,
    disabled=True
)

# =================================
# STOP UNTIL PROVEEDOR
# =================================
if tipo_proveedor == "----":
    st.info("Selecciona el tipo de proveedor para continuar.")
    st.stop()

# =========================================================
# ORDEN DE REPARACIÓN INTERNA
# =========================================================
if tipo_proveedor == "Interno":

    st.divider()
    st.subheader("Orden de Reparación Interna")

    empresa_i = st.selectbox(
        "Empresa",
        ["Selecciona Empresa"] + empresas,
        key="empresa_interna"
    )

    if empresa_i == "Selecciona Empresa":
        st.info("Selecciona una empresa para continuar.")
        st.stop()

    st.text_input(
        "Tipo de Reporte",
        value="Entrega de Material",
        disabled=True,
        key="tipo_reporte_interno"
    )

    tipo_unidad_i = st.selectbox(
        "Tipo de Unidad",
        ["Seleccionar tipo de unidad", "Tractores", "Remolques"],
        key="tipo_unidad_interno"
    )

    st.text_input("Operador", key="operador_interno")

    st.text_area("Descripción del problema", key="desc_interno")

    aplica_cobro_i = st.radio(
        "¿Aplica Cobro?",
        ["No", "Sí"],
        horizontal=True,
        key="cobro_interno"
    )

    st.text_input(
        "Responsable",
        disabled=aplica_cobro_i != "Sí",
        key="responsable_interno"
    )

# =========================================================
# ORDEN DE REPARACIÓN EXTERNA
# =========================================================
if tipo_proveedor == "Externo":

    st.divider()
    st.subheader("Orden de Reparación Externa")

    empresa_e = st.selectbox(
        "Empresa",
        ["Selecciona Empresa"] + empresas,
        key="empresa_externa"
    )

    if empresa_e == "Selecciona Empresa":
        st.info("Selecciona una empresa para continuar.")
        st.stop()

    st.selectbox(
        "Tipo de Reporte",
        ["-----", "Orden Preventivo", "Orden Correctivo"],
        index=0,
        key="tipo_reporte_externo"
    )

    tipo_unidad_e = st.selectbox(
        "Tipo de Unidad",
        ["Seleccionar tipo de unidad", "Tractores", "Remolques"],
        key="tipo_unidad_externo"
    )

    st.text_input("Operador", key="operador_externo")

    st.text_area("Descripción del problema", key="desc_externo")

    aplica_cobro_e = st.radio(
        "¿Aplica Cobro?",
        ["No", "Sí"],
        horizontal=True,
        key="cobro_externo"
    )

    st.text_input(
        "Responsable",
        disabled=aplica_cobro_e != "Sí",
        key="responsable_externo"
    )

# =================================
# GUARDAR
# =================================
st.divider()

if st.button("💾 Guardar Pase", type="primary", width="stretch"):
    st.session_state.folio_generado = generar_folio("XX")
    st.session_state.mostrar_confirmacion = True
    st.rerun()

if st.session_state.mostrar_confirmacion:

    @st.dialog("Pase guardado")
    def confirmacion():
        st.success("Pase guardado con éxito")
        st.markdown(f"**No. de Folio:** `{st.session_state.folio_generado}`")
        if st.button("Aceptar"):
            st.session_state.mostrar_confirmacion = False
            st.rerun()

    confirmacion()
