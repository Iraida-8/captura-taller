import streamlit as st
import pandas as pd

# =================================
# Page config
# =================================
st.set_page_config(
    page_title="Carga de Reportes",
    layout="wide"
)

st.title("📊 Carga de Reportes")

# =================================
# Company selector (LOCK)
# =================================
companies = [
    "Selecciona Empresa",
    "Igloo",
    "Lincoln Freight",
    "Picus",
    "Set Freight International",
    "Set Logis Plus"
]

empresa = st.selectbox("Selecciona la empresa:", companies)

if empresa == "Selecciona Empresa":
    st.warning("Debes seleccionar una empresa para continuar.")
    st.stop()

st.success(f"Empresa seleccionada: {empresa}")

# =================================
# Helper function to read files
# =================================
def read_file(file):
    try:
        if file.name.endswith(".csv"):
            return pd.read_csv(file)
        elif file.name.endswith(".xlsx"):
            return pd.read_excel(file)
        else:
            st.error("Formato no soportado. Usa CSV o XLSX.")
            return None
    except Exception as e:
        st.error(f"Error al leer archivo: {e}")
        return None

# =================================
# Uploaders
# =================================
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("1. Buscar Ordenes SAC")
    file_ordenes = st.file_uploader(
        "Sube el reporte",
        type=["csv", "xlsx"],
        key="ordenes"
    )

with col2:
    st.subheader(f"2. Reporte Ostes ({empresa})")
    file_ostes = st.file_uploader(
        "Sube el reporte",
        type=["csv", "xlsx"],
        key="ostes"
    )

with col3:
    st.subheader(f"3. Reporte de Mantenimientos ({empresa})")
    file_mantenimientos = st.file_uploader(
        "Sube el reporte",
        type=["csv", "xlsx"],
        key="mantenimientos"
    )

# =================================
# Display Tables
# =================================
st.divider()

if file_ordenes:
    df_ordenes = read_file(file_ordenes)
    if df_ordenes is not None:
        st.subheader("📄 Buscar Ordenes SAC")
        st.dataframe(df_ordenes, use_container_width=True)

if file_ostes:
    df_ostes = read_file(file_ostes)
    if df_ostes is not None:
        st.subheader(f"📄 Reporte Ostes ({empresa})")
        st.dataframe(df_ostes, use_container_width=True)

if file_mantenimientos:
    df_mantenimientos = read_file(file_mantenimientos)
    if df_mantenimientos is not None:
        st.subheader(f"📄 Reporte de Mantenimientos ({empresa})")
        st.dataframe(df_mantenimientos, use_container_width=True)