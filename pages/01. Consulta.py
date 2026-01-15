import streamlit as st
import pandas as pd
from datetime import date

# =================================
# Page configuration
# =================================
st.set_page_config(
    page_title="Consulta de Orden",
    layout="wide"
)

st.title("📋 Consulta de Orden")

# =================================
# DATA SOURCES
# =================================
IGLOO_ORDENES_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1OGYOp0ZqK7PQ93F4wdHJKEnB4oZbl5pU"
    "/export?format=csv&gid=770635060"
)

# =================================
# LOADERS
# =================================
@st.cache_data(ttl=600)
def cargar_ordenes_igloo():
    df = pd.read_csv(IGLOO_ORDENES_URL)
    df.columns = df.columns.str.strip()

    if "FECHA" in df.columns:
        df["FECHA"] = pd.to_datetime(
            df["FECHA"],
            errors="coerce",
            dayfirst=True
        )

        df = df[df["FECHA"] >= pd.Timestamp("2025-01-01")]

    return df

# =================================
# EMPRESA SELECTION
# =================================
st.subheader("Selección de Empresa")

empresa = st.selectbox(
    "Empresa",
    [
        "Selecciona empresa",
        "IGLOO TRANSPORT",
        "LINCOLN FREIGHT",
        "PICUS",
        "SET FREIGHT INTERNATIONAL",
        "SET LOGIS PLUS"
    ],
    index=0
)

# Stop execution until a company is selected
if empresa == "Selecciona empresa":
    st.info("Selecciona una empresa para consultar las órdenes.")
    st.stop()

# =================================
# LOAD DATA (ONLY IGLOO FOR NOW)
# =================================
if empresa == "IGLOO TRANSPORT":
    df = cargar_ordenes_igloo()
else:
    df = pd.DataFrame()

if df.empty:
    st.warning("No hay datos disponibles para esta empresa.")
    st.stop()

# =================================
# ÚLTIMOS 10 REGISTROS
# =================================
st.subheader("Últimos 10 Registros")

df_ultimos = (
    df.sort_values("FECHA", ascending=False)
      .head(10)
)

st.dataframe(
    df_ultimos,
    width="stretch",
    hide_index=True
)

# =================================
# FILTROS
# =================================
st.divider()
st.subheader("Filtros")

c1, c2, c3 = st.columns(3)

with c1:
    fecha_inicio = st.date_input(
        "Fecha inicio",
        value=df["FECHA"].min().date()
    )

with c2:
    fecha_fin = st.date_input(
        "Fecha fin",
        value=df["FECHA"].max().date()
    )

with c3:
    unidad_options = ["Todas"]
    if "Unidad" in df.columns:
        unidad_options += sorted(
            df["Unidad"].dropna().astype(str).unique().tolist()
        )

    unidad_sel = st.selectbox(
        "Unidad",
        unidad_options
    )

# =================================
# APPLY FILTERS
# =================================
df_filtrado = df.copy()

df_filtrado = df_filtrado[
    (df_filtrado["FECHA"] >= pd.to_datetime(fecha_inicio)) &
    (df_filtrado["FECHA"] <= pd.to_datetime(fecha_fin))
]

if unidad_sel != "Todas" and "Unidad" in df_filtrado.columns:
    df_filtrado = df_filtrado[
        df_filtrado["Unidad"].astype(str) == unidad_sel
    ]

# =================================
# TABLA COMPLETA
# =================================
st.divider()
st.subheader("Todas las Órdenes")

st.dataframe(
    df_filtrado.sort_values("FECHA", ascending=False),
    width="stretch",
    hide_index=True
)

# =================================
# FOOTER
# =================================
st.caption(
    f"Mostrando {len(df_filtrado)} registros | "
    f"Desde {fecha_inicio} hasta {fecha_fin}"
)