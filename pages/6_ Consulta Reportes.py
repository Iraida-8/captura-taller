import streamlit as st
import pandas as pd

from datetime import datetime

fecha_mod = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


from auth import require_login, require_access

# =================================
# Page configuration (MUST BE FIRST)
# =================================
st.set_page_config(
    page_title="Consulta de Reportes",
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
require_access("consulta_reportes")

# =================================
# Top navigation
# =================================
if st.button("⬅ Volver al Dashboard"):
    st.switch_page("pages/dashboard.py")

st.divider()

# =================================
# Page title
# =================================
st.title("📋 Consulta de Reportes (WIP)")

# =================================
# Google Sheets configuration
# =================================
IGLOO_ARTICULOS_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "18tFOA4prD-PWhtbc35cqKXxYcyuqGOC7"
    "/export?format=csv&gid=410297659"
)

