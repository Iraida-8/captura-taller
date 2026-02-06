import streamlit as st
import pandas as pd
from datetime import date

from auth import require_login, require_access

st.cache_data.clear()

# =================================
# Page configuration
# =================================
st.set_page_config(
    page_title="Consulta de Reparación",
    layout="wide"
)

# =================================
# Hide sidebar
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
# Security
# =================================
require_login()
require_access("consultar_reparacion")

# =================================
# Navigation
# =================================
if st.button("⬅ Volver al Dashboard"):
    st.switch_page("pages/dashboard.py")

st.divider()
st.title("📋 Consulta de Reparación")

# =================================
# EMPRESA DATA CONFIG (Test)
# =================================
EMPRESA_CONFIG = {
    "IGLOO TRANSPORT": {
        "ordenes": (
            "https://docs.google.com/spreadsheets/d/"
            "1OGYOp0ZqK7PQ93F4wdHJKEnB4oZbl5pU"
            "/export?format=csv&gid=770635060"
        ),
        "partes": (
            "https://docs.google.com/spreadsheets/d/"
            "18tFOA4prD-PWhtbc35cqKXxYcyuqGOC7"
            "/export?format=csv&gid=410297659"
        )
    },

    "LINCOLN FREIGHT": {
        "ordenes": (
            "https://docs.google.com/spreadsheets/d/"
            "1nqRT3LRixs45Wth5bXyrKSojv3uJfjbZ"
            "/export?format=csv&gid=332111886"
        ),
        "partes": (
            "https://docs.google.com/spreadsheets/d/"
            "1lcNr73nHrMpsqdYBNxtTQFqFmY1Ey9gp"
            "/export?format=csv&gid=41991257"
        )
    },

    "PICUS": {
        "ordenes": (
            "https://docs.google.com/spreadsheets/d/"
            "1DSFFir8vQGzkIZdPGZKakMFygUUjA6vg"
            "/export?format=csv&gid=1157416037"
        ),
        "partes": (
            "https://docs.google.com/spreadsheets/d/"
            "1tzt6tYG94oVt8YwK3u9gR-DHFcuadpNN"
            "/export?format=csv&gid=354598948"
        )
    },

    "SET FREIGHT INTERNATIONAL": {
        "ordenes": (
            "https://docs.google.com/spreadsheets/d/"
            "166RzQ6DxBiZ1c7xjMQzyPJk2uLJI_piO"
            "/export?format=csv&gid=1292870764"
        ),
        "partes": (
            "https://docs.google.com/spreadsheets/d/"
            "1Nqbhl8o5qaKhI4LNxreicPW5Ew8kqShS"
            "/export?format=csv&gid=849445619"
        )
    },

    "SET LOGIS PLUS": {
        "ordenes": (
            "https://docs.google.com/spreadsheets/d/"
            "11q580KXBn-kX5t-eHAbV0kp-kTqIQBR6"
            "/export?format=csv&gid=663362391"
        ),
        "partes": (
            "https://docs.google.com/spreadsheets/d/"
            "1yrzwm5ixsaYNKwkZpfmFpDdvZnohFH61"
            "/export?format=csv&gid=1837946138"
        )
    }
}


# =================================
# LOADERS
# =================================
@st.cache_data(ttl=600)
def cargar_ordenes(url):
    if not url or "<PUT_" in url:
        return pd.DataFrame()

    df = pd.read_csv(url)
    df.columns = df.columns.str.strip()

    if "FECHA H" in df.columns:
        df["FECHA H"] = pd.to_datetime(
            df["FECHA H"],
            errors="coerce",
            dayfirst=True
        )
        df = df[df["FECHA H"] >= pd.Timestamp("2025-01-01")]

    return df


@st.cache_data(ttl=600)
def cargar_partes(url):
    if not url or "<PUT_" in url:
        return pd.DataFrame()

    df = pd.read_csv(url)
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
    ["Selecciona empresa"] + list(EMPRESA_CONFIG.keys()),
    index=0
)

if empresa == "Selecciona empresa":
    st.info("Selecciona una empresa para consultar las órdenes.")
    st.stop()

config = EMPRESA_CONFIG[empresa]

df = cargar_ordenes(config["ordenes"])
df_partes = cargar_partes(config["partes"])

if df.empty:
    st.warning("No hay datos disponibles para esta empresa.")
    st.stop()

# =================================
# ÚLTIMOS 10 REGISTROS (ÓRDENES)
# =================================
st.subheader("Últimos 10 Registros")

unidad_orden_sel = "Todas"

if "Unidad" in df.columns:
    unidad_orden_sel = st.selectbox(
        "Filtrar por Unidad",
        ["Todas"] + sorted(df["Unidad"].dropna().astype(str).unique()),
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

if unidad_orden_sel != "Todas":
    df_ultimos = df_ultimos[df_ultimos["Unidad"].astype(str) == unidad_orden_sel]

df_ultimos = (
    df_ultimos
    .sort_values("FECHA", ascending=False)
    .head(10)[columnas_disponibles]
)

st.dataframe(df_ultimos, hide_index=True, width="stretch")

# =================================
# ÚLTIMOS 10 REGISTROS (PARTES)
# =================================
st.subheader("Refacciones Recientes")

if not df_partes.empty and "Unidad" in df_partes.columns:
    unidad_partes_sel = st.selectbox(
        "Filtrar por Unidad",
        ["Todas"] + sorted(df_partes["Unidad"].dropna().astype(str).unique()),
        index=0
    )

    df_partes_filtrado = df_partes.copy()

    # Detect which total column exists (empresa-specific)
    total_col = None
    display_total_col = None

    if empresa == "IGLOO TRANSPORT":
        total_col = "TotalCorrecion"      # sheet column
        display_total_col = "Total Correccion"
    elif empresa == "LINCOLN FREIGHT":
        total_col = "Total USD"
        display_total_col = "Total USD"

    columnas_partes = [
        "FECHA H",
        "Unidad",
        "Parte",
        "TipoCompra",
        "PrecioParte",
        "Cantidad",
    ]

    if total_col and total_col in df_partes_filtrado.columns:
        columnas_partes.append(total_col)


    columnas_disponibles_partes = [
        c for c in columnas_partes if c in df_partes_filtrado.columns
    ]

    df_partes_ultimos = (
        df_partes_filtrado
        .sort_values("FECHA H", ascending=False)
        .head(10)[columnas_disponibles_partes]
    )

    # Rename total column for display (empresa-specific)
    if total_col and display_total_col and total_col != display_total_col:
        df_partes_ultimos = df_partes_ultimos.rename(
            columns={total_col: display_total_col}
        )

    if "Fecha" in df_partes_ultimos.columns:
        df_partes_ultimos["Fecha"] = df_partes_ultimos["Fecha"].dt.strftime("%Y-%m-%d")

    st.dataframe(df_partes_ultimos, hide_index=True, width="stretch")
else:
    st.info("No hay información de partes disponible para esta empresa.")

# =================================
# FILTROS
# =================================
st.divider()
st.subheader("Filtros")

c1, c2, c3 = st.columns(3)

# --- Fecha inicio ---
with c1:
    fecha_inicio = st.date_input(
        "Fecha inicio",
        value=date(2025, 1, 1),
        min_value=date(2025, 1, 1)
    )

# --- Fecha fin ---
with c2:
    fecha_fin = st.date_input(
        "Fecha fin",
        value=date.today()
    )

# --- Unidad ---
with c3:
    if "Unidad" in df.columns:
        unidad_sel = st.selectbox(
            "Unidad",
            ["Todas"] + sorted(df["Unidad"].dropna().astype(str).unique())
        )
    else:
        unidad_sel = "Todas"


# =================================
# APPLY FILTERS
# =================================
df_filtrado = df.copy()

if "FECHA" in df_filtrado.columns:
    df_filtrado["FECHA"] = pd.to_datetime(
        df_filtrado["FECHA"],
        errors="coerce",
        dayfirst=True
    )

    df_filtrado = df_filtrado[
        (df_filtrado["FECHA"] >= pd.Timestamp("2025-01-01")) &
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

columnas_ocultar = ["DIFERENCIA", "COMENTARIOS"]
columnas_mostrar = [c for c in df_filtrado.columns if c not in columnas_ocultar]

st.dataframe(
    df_filtrado[columnas_mostrar]
        .sort_values("FECHA", ascending=False),
    hide_index=True,
    width="stretch"
)

# =================================
# FOOTER
# =================================
st.caption(
    f"Mostrando {len(df_filtrado)} registros | "
    f"Desde {fecha_inicio} hasta {fecha_fin}"
)