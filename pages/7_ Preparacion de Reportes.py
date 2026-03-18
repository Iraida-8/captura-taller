import streamlit as st
import pandas as pd
from datetime import date, datetime
from auth import require_login, require_access
import gspread
from google.oauth2.service_account import Credentials
import os
import unicodedata

# =================================
# Page configuration
# =================================
st.set_page_config(
    page_title="Preparación de Reportes",
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
require_access("prepara_reportes")

# =================================
# Top navigation
# =================================
if st.button("⬅ Volver al Dashboard"):
    st.switch_page("pages/dashboard.py")

st.divider()

st.title("📊 Preparación de Reportes")

# =================================
# Company selector (LOCK)
# =================================
companies = [
    "SELECCIONA EMPRESA",
    "IGLOO",
    "LINCOLN FREIGHT",
    "PICUS",
    "SET FREIGHT INTERNATIONAL",
    "SET LOGIS PLUS"
]

empresa = st.selectbox("Selecciona la empresa:", companies)

if empresa == "SELECCIONA EMPRESA":
    st.warning("Debes seleccionar una empresa para continuar.")
    st.stop()

# =================================
# Reset uploaders when company changes
# =================================
prev_empresa = st.session_state.get("prev_empresa", None)

if prev_empresa is not None and prev_empresa != empresa:
    for key in ["ordenes", "ostes", "mantenimientos"]:
        st.session_state.pop(key, None)
    st.rerun()

st.session_state.prev_empresa = empresa

st.success(f"Empresa seleccionada: {empresa}")

# =================================
# Normalize text (remove accents + lowercase)
# =================================
def normalize_text(text):
    text = text.lower()
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c))

# =================================
# Validate filename
# =================================
def validate_filename(file, required_words):
    name = normalize_text(file.name)
    return all(word in name for word in required_words)

# =================================
# Helper: Read file safely
# =================================
def read_file(file):
    try:
        if file.name.endswith(".csv"):
            try:
                return pd.read_csv(file, encoding="utf-8")
            except:
                file.seek(0)
                return pd.read_csv(file, encoding="latin-1")
        elif file.name.endswith(".xlsx"):
            return pd.read_excel(file, engine="openpyxl")
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
        "Sube Buscar Ordenes SAC",
        type=["csv", "xlsx"],
        key="ordenes"
    )

with col2:
    st.subheader(f"2. Reporte Ostes ({empresa})")
    file_ostes = st.file_uploader(
        "Sube Reporte Ostes",
        type=["csv", "xlsx"],
        key="ostes"
    )

with col3:
    st.subheader(f"3. Reporte de Mantenimientos ({empresa})")
    file_mantenimientos = st.file_uploader(
        "Sube Reporte de Mantenimientos",
        type=["csv", "xlsx"],
        key="mantenimientos"
    )

st.divider()

# =================================
# Display tables with validation (COLLAPSIBLE)
# =================================

# ---- ORDENES ----
if file_ordenes:
    if not validate_filename(file_ordenes, ["buscar", "ordenes", "sac"]):
        st.error("El archivo debe contener: buscar + ordenes + sac en el nombre.")
    else:
        df_ordenes = read_file(file_ordenes)
        if df_ordenes is not None:
            with st.expander("📄 Buscar Ordenes SAC", expanded=False):
                st.dataframe(df_ordenes, use_container_width=True)

# ---- OSTES ----
if file_ostes:
    if not validate_filename(file_ostes, ["ostes"]):
        st.error("El archivo debe contener: ostes en el nombre.")
    else:
        df_ostes = read_file(file_ostes)
        if df_ostes is not None:
            with st.expander(f"📄 Reporte Ostes ({empresa})", expanded=False):
                st.dataframe(df_ostes, use_container_width=True)

# ---- MANTENIMIENTOS ----
if file_mantenimientos:
    if not validate_filename(file_mantenimientos, ["mantenimientos"]):
        st.error("El archivo debe contener: mantenimientos en el nombre.")
    else:
        df_mantenimientos = read_file(file_mantenimientos)
        if df_mantenimientos is not None:
            with st.expander(f"📄 Reporte de Mantenimientos ({empresa})", expanded=False):
                st.dataframe(df_mantenimientos, use_container_width=True)