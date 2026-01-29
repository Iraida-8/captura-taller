import streamlit as st
import pandas as pd
from datetime import date

from auth import require_login

require_login()

st.title("Dashboard")

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

IGLOO_PARTES_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "18tFOA4prD-PWhtbc35cqKXxYcyuqGOC7"
    "/export?format=csv&gid=410297659"
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


@st.cache_data(ttl=600)
def cargar_partes_igloo():
    df = pd.read_csv(IGLOO_PARTES_URL)
    df.columns = df.columns.str.strip()

    if "Fecha" in df.columns:
        df["Fecha"] = pd.to_datetime(
            df["Fecha"],
            errors="coerce",
            dayfirst=True
        )
        df = df[df["Fecha"] >= pd.Timestamp("2025-01-01")]

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

if empresa == "Selecciona empresa":
    st.info("Selecciona una empresa para consultar las órdenes.")
    st.stop()

# =================================
# LOAD DATA (ONLY IGLOO FOR NOW)
# =================================
if empresa == "IGLOO TRANSPORT":
    df = cargar_ordenes_igloo()
    df_partes = cargar_partes_igloo()
else:
    df = pd.DataFrame()
    df_partes = pd.DataFrame()

if df.empty:
    st.warning("No hay datos disponibles para esta empresa.")
    st.stop()

# =================================
# ÚLTIMOS 10 REGISTROS (ÓRDENES)
# =================================
st.subheader("Últimos 10 Registros")

unidad_orden_sel = "Todas"

if "Unidad" in df.columns:
    unidades_orden = (
        df["Unidad"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    unidad_orden_sel = st.selectbox(
        "Filtrar por Unidad",
        ["Todas"] + sorted(unidades_orden),
        index=0
    )

columnas_resumen = [
    "Fecha Aceptado",
    "Fecha Iniciada",
    "Unidad",
    "Tipo Unidad",
    "Reporte",
    "Descripcion",
    "Razon Reparacion"
]

columnas_disponibles = [c for c in columnas_resumen if c in df.columns]

df_ultimos = df.copy()

if unidad_orden_sel != "Todas" and "Unidad" in df_ultimos.columns:
    df_ultimos = df_ultimos[
        df_ultimos["Unidad"].astype(str) == unidad_orden_sel
    ]

df_ultimos = (
    df_ultimos
    .sort_values("FECHA", ascending=False)
    .head(10)[columnas_disponibles]
)

st.dataframe(
    df_ultimos,
    width="stretch",
    hide_index=True
)

# =================================
# ÚLTIMOS 10 REGISTROS (PARTES)
# =================================
st.subheader("Refacciones Recientes")

unidad_partes_sel = None

if not df_partes.empty and "Unidad" in df_partes.columns:
    unidades_partes = (
        df_partes["Unidad"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    unidad_partes_sel = st.selectbox(
        "Filtrar por Unidad",
        ["Todas"] + sorted(unidades_partes),
        index=0
    )

columnas_partes = [
    "Fecha",
    "Unidad",
    "Parte",
    "TipoCompra",
    "PrecioParte",
    "Cantidad",
    "Total Correccion"
]

if not df_partes.empty:
    df_partes_filtrado = df_partes.copy()

    if (
        unidad_partes_sel
        and unidad_partes_sel != "Todas"
        and "Unidad" in df_partes_filtrado.columns
    ):
        df_partes_filtrado = df_partes_filtrado[
            df_partes_filtrado["Unidad"].astype(str) == unidad_partes_sel
        ]

    columnas_disponibles_partes = [
        c for c in columnas_partes if c in df_partes_filtrado.columns
    ]

    if "Fecha" in columnas_disponibles_partes:
        df_partes_ultimos = (
            df_partes_filtrado
            .sort_values("Fecha", ascending=False)
            .head(10)[columnas_disponibles_partes]
            .copy()
        )

        df_partes_ultimos["Fecha"] = df_partes_ultimos["Fecha"].dt.strftime("%y-%m-%d")

        st.dataframe(
            df_partes_ultimos,
            width="stretch",
            hide_index=True
        )
    else:
        st.info("La tabla de partes no contiene el campo Fecha.")
else:
    st.info("No hay información de partes disponible para esta empresa.")

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
        value=date.today()
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
# TABLA COMPLETA (REMOVE COLUMNS)
# =================================
st.divider()
st.subheader("Todas las Órdenes")

columnas_ocultar = ["DIFERENCIA", "COMENTARIOS"]
columnas_mostrar = [
    c for c in df_filtrado.columns if c not in columnas_ocultar
]

st.dataframe(
    df_filtrado[columnas_mostrar]
        .sort_values("FECHA", ascending=False),
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
