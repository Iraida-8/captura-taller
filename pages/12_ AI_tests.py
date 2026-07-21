import streamlit as st
from auth import require_login, require_access
from pages.css import load_css

# =================================
# RELEASE CHANNEL
# =================================

#APP_CHANNEL = "BETA"
APP_CHANNEL = "RELEASE"

DASHBOARD_PAGE = (
    "pages/dashboard_beta.py"
    if APP_CHANNEL == "BETA"
    else "pages/dashboard.py"
)

# =================================
# Page configuration
# =================================
st.set_page_config(
    page_title="AI STOOF",
    layout="wide"
)

# -------------------------------
# PAGE STYLE
# -------------------------------
load_css()

# =================================
# Security gates
# =================================
require_login()
require_access("ai_testing")

# =================================
# Navigation
# =================================
st.write("")
if st.button("⬅ Volver al Dashboard"):
    st.switch_page(DASHBOARD_PAGE)

st.divider()

# =================================
# HEADER
# =================================

st.title("💳  AI Tester")