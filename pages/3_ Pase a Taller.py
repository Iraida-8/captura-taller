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

    prefijo = prefijos.get(empresa, "XX")
    return f"{prefijo}{str(1).zfill(5)}"

# =================================
# Session state
# =================================
if "folio_generado" not in st.session_state:
    st.session_state.folio_generado = ""

if "mostrar_confirmacion" not in st.session_state:
    st.session_state.mostrar_confirmacion = False

# =================================
# Title
# =================================
st.title("🛠️ Captura Pase de Taller")

# =================================
# SECCIÓN 1 — DATOS DEL REPORTE
# =================================
st.divider()
st.subheader("Datos del Reporte")

fecha_reporte = st.date_input("Fecha de reporte", value=date.today())

tipo_proveedor = st.selectbox(
    "Tipo de proveedor",
    ["----", "Interno", "Externo"]
)

folio_display = (
    st.session_state.folio_generado
    if st.session_state.folio_generado
    else "folio generado al guardar"
)

st.text_input("No. de Folio", value=folio_display, disabled=True)

# 🔹 OSTE + NO. DE REPORTE
o1, o2 = st.columns(2)

with o1:
    st.text_input("OSTE", disabled=True)

with o2:
    st.text_input("No. de Reporte", disabled=True)

st.text_input(
    "Capturó",
    value=st.session_state.usuario_actual,
    disabled=True
)

st.selectbox(
    "Estado",
    ["En Curso/Nuevo"],
    index=0,
    disabled=True
)

# =================================
# SECCIÓN 2 — INFORMACIÓN DEL OPERADOR
# =================================
st.divider()
st.subheader("Información del Operador")

empresa = st.selectbox(
    "Empresa",
    ["Selecciona Empresa"] + empresas
)

if empresa == "Selecciona Empresa":
    st.info("Selecciona una empresa para continuar con la captura del pase.")
    st.stop()

# =================================
# CONTENIDO POST-EMPRESA
# =================================
tipo_reporte = st.selectbox(
    "Tipo de Reporte",
    [
        "Selecciona tipo de reporte",
        "Orden Preventivo",
        "Orden Correctivo"
    ]
)

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

c1, c2, c3, c4 = st.columns([2, 2, 2, 3])

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

if tipo_unidad_operador == "Tractores" and no_unidad != "Selecciona Unidad":
    fila = tractores_filtrados[
        tractores_filtrados["TRACTOR"].astype(str) == no_unidad
    ].iloc[0]
    marca_valor = fila["MARCA"]
    modelo_valor = fila["MODELO"]

elif tipo_unidad_operador == "Remolques":
    if no_unidad == "REMOLQUE EXTERNO":
        marca_valor = "EXTERNO"
        modelo_valor = "0000"
    elif no_unidad != "Selecciona Unidad":
        fila = catalogos_filtrados[
            catalogos_filtrados["CAJA"].astype(str) == no_unidad
        ].iloc[0]
        marca_valor = fila.get("MARCA", "")
        modelo_valor = fila.get("MODELO", "")

with c2:
    st.text_input("Marca", value=marca_valor, disabled=True)
with c3:
    st.text_input("Modelo", value=modelo_valor, disabled=True)
with c4:
    tipo_caja = st.selectbox(
        "Tipo de Caja",
        ["Selecciona Caja", "Caja seca", "Caja fria"]
        if tipo_unidad_operador == "Remolques"
        else ["Caja no aplicable"],
        disabled=tipo_unidad_operador != "Remolques"
    )

e1, e2 = st.columns(2)

with e1:
    st.text_input(
        "No. de Unidad Externo",
        disabled=no_unidad != "REMOLQUE EXTERNO"
    )

with e2:
    st.text_input(
        "Nombre Línea Externa",
        disabled=no_unidad != "REMOLQUE EXTERNO"
    )

# =================================
# COBRO
# =================================
aplica_cobro = st.radio(
    "¿Aplica Cobro?",
    ["No", "Sí"],
    horizontal=True,
    index=0
)

st.text_input(
    "Responsable",
    disabled=aplica_cobro != "Sí"
)

# =================================
# DESCRIPCIÓN / MULTA
# =================================
descripcion_problema = st.text_area("Descripción del problema")

genero_multa = st.checkbox("¿Generó multa?")

st.text_input(
    "No. de Inspección",
    disabled=not genero_multa
)

st.text_area(
    "Reparación que generó multa",
    placeholder="Por favor introducir # de reporte aplicable",
    disabled=not genero_multa
)

# =================================
# GUARDAR PASE
# =================================
st.divider()
st.markdown("###")

if st.button("💾 Guardar Pase", type="primary", width="stretch"):
    st.session_state.folio_generado = generar_folio(empresa)
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
