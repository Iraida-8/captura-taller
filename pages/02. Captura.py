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

    empresas = (
        df["EMPRESA"]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )

    unidades = (
        df["CAJA"]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )

    return {
        "empresas": sorted(empresas),
        "unidades": sorted(unidades)
    }

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
        df_final["Precio MXP"]
        * (1 + df_final["Iva"])
        * df_final["Cantidad"]
    )

    return df_final

catalogos = cargar_catalogos()

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

empresa = st.selectbox("Empresa", catalogos["empresas"])
tipo_unidad = st.selectbox("Tipo de Unidad", ["Caja seca", "Termo frio"])
unidad = st.selectbox("Unidad", catalogos["unidades"])
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

# ---------------------------------
# Column filters
# ---------------------------------
f1, f2, f3, f4, f5, f6, f7, f8 = st.columns([1, 2, 3, 2, 2, 2, 2, 2])

with f1: filtro_sel = st.text_input(" ", placeholder="✔")
with f2: filtro_articulo = st.text_input(" ", placeholder="Artículo")
with f3: filtro_desc = st.text_input(" ", placeholder="Descripción")
with f4: filtro_tipo = st.text_input(" ", placeholder="Tipo")
with f5: filtro_precio = st.text_input(" ", placeholder="Precio")
with f6: filtro_iva = st.text_input(" ", placeholder="IVA")
with f7: filtro_cantidad = st.text_input(" ", placeholder="Cantidad")
with f8: filtro_mtto = st.text_input(" ", placeholder="Mtto")

# ---------------------------------
# Initialize session state
# ---------------------------------
if "articulos_df" not in st.session_state:
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

df_base = st.session_state.articulos_df

# ---------------------------------
# Filtering logic
# ---------------------------------
def match(value, filtro):
    return filtro.lower() in str(value).lower()

df_filtrado = df_base[
    df_base["Artículo"].apply(match, filtro=filtro_articulo)
    & df_base["Descripción"].apply(match, filtro=filtro_desc)
    & df_base["Tipo"].apply(match, filtro=filtro_tipo)
    & df_base["Precio MXP"].apply(match, filtro=filtro_precio)
    & df_base["Iva"].apply(match, filtro=filtro_iva)
    & df_base["Cantidad"].apply(match, filtro=filtro_cantidad)
    & df_base["Tipo Mtto"].apply(match, filtro=filtro_mtto)
] if not df_base.empty else df_base

# ---------------------------------
# Table editor
# ---------------------------------
edited_df = st.data_editor(
    df_filtrado,
    key="editor_articulos",
    hide_index=True,
    column_config={
        "Seleccionar": st.column_config.CheckboxColumn("✔", width="small"),
        "Artículo": st.column_config.TextColumn("Artículo"),
        "Descripción": st.column_config.TextColumn("Descripción"),
        "Tipo": st.column_config.TextColumn("Tipo"),
        "Precio MXP": st.column_config.NumberColumn("Precio MXP", format="$ %.2f"),
        "Iva": st.column_config.NumberColumn("IVA", format="%.2f"),
        "Cantidad": st.column_config.SelectboxColumn(
            "Cantidad",
            options=list(range(1, 21)),
            default=1
        ),
        "Total MXN": st.column_config.NumberColumn("Total MXN", format="$ %.2f"),
        "Tipo Mtto": st.column_config.TextColumn("Tipo Mtto")
    },
    disabled=[
        "Artículo",
        "Descripción",
        "Tipo",
        "Precio MXP",
        "Iva",
        "Tipo Mtto",
        "Total MXN"
    ]
)

# ---------------------------------
# Instant recalculation
# ---------------------------------
if not edited_df.empty:
    edited_df = edited_df.copy()
    edited_df["Total MXN"] = (
        edited_df["Precio MXP"]
        * (1 + edited_df["Iva"])
        * edited_df["Cantidad"]
    )

    st.session_state.articulos_df.update(edited_df)
