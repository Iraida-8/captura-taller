import streamlit as st
import pandas as pd
from datetime import date

# =================================
# Page configuration
# =================================
st.set_page_config(
    page_title="Captura Pase de Taller",
    layout="wide"
)

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

IGLOO_ARTICULOS_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "18tFOA4prD-PWhtbc35cqKXxYcyuqGOC7"
    "/export?format=csv&gid=410297659"
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

@st.cache_data(ttl=3600)
def cargar_articulos_igloo():
    df = pd.read_csv(IGLOO_ARTICULOS_URL)
    df.columns = df.columns.str.strip()

    def limpiar_numero(valor):
        return (
            str(valor)
            .replace("$", "")
            .replace(",", "")
            .strip()
        )

    precio = df["PU"].apply(limpiar_numero).astype(float)
    iva_raw = df["Tasaiva"].apply(limpiar_numero).astype(float)
    iva = iva_raw.apply(lambda x: x / 100 if x >= 1 else x)

    df_final = pd.DataFrame({
        "Seleccionar": False,
        "Artículo": df["TipoCompra"],
        "Descripción": df["Parte"],
        "Tipo": df["TipoCompra"],
        "Precio MXP": precio,
        "Iva": iva,
        "Cantidad": 1,
        "Total MXN": 0.0,
        "Tipo Mtto": df["Tipo de reparacion"]
    })

    df_final["Total MXN"] = (
        df_final["Precio MXP"] * (1 + df_final["Iva"]) * df_final["Cantidad"]
    )

    return df_final

catalogos_df, empresas = cargar_catalogos()
tractores_df = cargar_tractores()

# =================================
# Title
# =================================
st.title("🛠️ Captura Pase de Taller")

# =================================
# SECCIÓN 1 — DATOS DEL REPORTE
# =================================
st.subheader("Datos del Reporte")
st.divider()

fecha_reporte = st.date_input("Fecha de reporte", value=date.today())
numero_reporte = st.text_input("No. de reporte", placeholder="Ej. REP-2026-001")
capturo = st.text_input("Capturó", placeholder="Nombre del responsable")
estado = st.selectbox("Estado", ["EDICION"])

# =================================
# SECCIÓN 2 — INFORMACIÓN DEL OPERADOR
# =================================
st.subheader("Información del Operador")
st.divider()

empresa = st.selectbox(
    "Empresa",
    ["Selecciona Empresa"] + empresas,
    index=0
)

# -------- UNIDADES FILTRADAS POR EMPRESA --------
if empresa and empresa != "Selecciona Empresa":
    unidades_filtradas = (
        catalogos_df[
            catalogos_df["EMPRESA"].astype(str).str.strip() == empresa
        ]["CAJA"]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )
else:
    unidades_filtradas = []

# -------- TRACTORES FILTRADOS POR EMPRESA --------
if empresa and empresa != "Selecciona Empresa":
    tractores_filtrados_df = tractores_df[
        tractores_df["EMPRESA"].astype(str).str.strip() == empresa
    ]
    lista_tractores = (
        tractores_filtrados_df["TRACTOR"]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )
else:
    tractores_filtrados_df = pd.DataFrame()
    lista_tractores = []

# -------- TRACTOR | MARCA | MODELO (MISMA FILA) --------
c1, c2, c3 = st.columns(3)

with c1:
    tractor = st.selectbox(
        "Tractor",
        ["Selecciona Unidad"] + sorted(lista_tractores),
        index=0
    )

# -------- AUTOFILL MARCA / MODELO --------
if tractor and tractor != "Selecciona Unidad" and not tractores_filtrados_df.empty:
    fila_tractor = tractores_filtrados_df[
        tractores_filtrados_df["TRACTOR"].astype(str).str.strip() == tractor
    ].iloc[0]

    marca_valor = str(fila_tractor["MARCA"]).strip()
    modelo_valor = str(fila_tractor["MODELO"]).strip()
else:
    marca_valor = ""
    modelo_valor = ""

with c2:
    marca = st.text_input("Marca", value=marca_valor, disabled=True)

with c3:
    modelo = st.text_input("Modelo", value=modelo_valor, disabled=True)

tipo_unidad = st.selectbox(
    "Tipo de Caja",
    ["Selecciona Caja", "Caja seca", "Termo frio"],
    index=0
)

unidad = st.selectbox(
    "Numero de Caja",
    ["Selecciona Unidad"] + sorted(unidades_filtradas),
    index=0
)

operador = st.text_input("Operador", placeholder="Nombre del operador")
tipo_reporte = st.selectbox("Tipo de Reporte", ["Reporte de reparación"])

descripcion_problema = st.text_area("Descripción del problema", height=120)

col1, col2 = st.columns([2, 1])
with col1:
    numero_inspeccion = st.text_input("No. de Inspección")
with col2:
    genero_multa = st.checkbox("¿Generó multa?")

reparacion_multa = st.text_area(
    "Reparación que generó multa",
    height=100,
    disabled=not genero_multa
)

# =================================
# SECCIÓN 3 — ARTÍCULOS / ACTIVIDADES
# =================================
st.subheader("Artículos / Actividades")
st.divider()

if "empresa_prev" not in st.session_state:
    st.session_state.empresa_prev = empresa

if empresa != st.session_state.empresa_prev:
    if empresa == "IGLOO TRANSPORT":
        st.session_state.articulos_df = cargar_articulos_igloo()
    else:
        st.session_state.articulos_df = pd.DataFrame(columns=[
            "Seleccionar",
            "Artículo",
            "Descripción",
            "Tipo",
            "Precio MXP",
            "Iva",
            "Cantidad",
            "Total MXN",
            "Tipo Mtto"
        ])
    st.session_state.empresa_prev = empresa

df_base = st.session_state.get("articulos_df", pd.DataFrame())

edited_df = st.data_editor(
    df_base,
    key="editor_articulos",
    hide_index=True
)

# =================================
# TOTAL SELECCIONADO
# =================================
st.divider()

total_seleccionado = (
    edited_df.loc[edited_df["Seleccionar"] == True, "Total MXN"].sum()
    if not edited_df.empty else 0.0
)

st.metric("Total Seleccionado MXN", f"$ {total_seleccionado:,.2f}")
