import streamlit as st
from datetime import datetime
from auth import require_login

# -------------------------------
# Security gate
# -------------------------------
require_login()

st.set_page_config(
    page_title="Dashboard",
    layout="wide"
)

# -------------------------------
# Hide sidebar + BIG BUTTON STYLES
# -------------------------------
st.markdown(
    """
    <style>
    /* Hide sidebar */
    [data-testid="stSidebar"] { display: none; }

    /* App background */
    .stApp {
        background-color: #0e1117;
    }

    /* Give page breathing room */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    /* =========================
       HEADER STYLE
       ========================= */
    h1 {
        font-size: 1.9rem;
        margin-bottom: 0.2rem;
    }

    /* =========================
       BIG MODULE BUTTONS
       ========================= */
    div.stButton > button {
        height: 95px;
        font-size: 1.05rem;
        font-weight: 600;
        border-radius: 16px;
        padding: 1.2rem;
        white-space: normal;

        background-color: #161b22;
        border: 1px solid #2d333b;
    }

    /* Hover */
    div.stButton > button:hover {
        transform: translateY(-2px);
        transition: 0.15s ease-in-out;
        border-color: #58a6ff;
    }

    /* =========================
       LOGOUT BUTTON
       ========================= */
    button[kind="secondary"] {
        display: block;
        margin-left: auto;
        margin-right: auto;
        border-radius: 12px;
    }

    /* Subheaders */
    h2, h3 {
        margin-top: 0.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)
# -------------------------------
user = st.session_state.user
access = user.get("access", [])

# -------------------------------
# Header
# -------------------------------
st.title("📊 Dashboard")
st.caption(f"{user['name'] or user['email']}  •  {user['role']}")

# live date / time
clock_placeholder = st.empty()

clock_placeholder.caption(
    datetime.now().strftime("%A, %d %B %Y")
)

st.divider()

# -------------------------------
# Navigation buttons
# -------------------------------
st.subheader("Módulos")

col1, col2, col3 = st.columns(3)

# 1 Consultar Reparación
with col1:
    if "consultar_reparacion" in access:
        if st.button("🔍  Consultar Reparación", use_container_width=True):
            st.switch_page("pages/1_ Consultar Reparacion.py")

# 2 Pase a Taller
with col2:
    if "pase_taller" in access:
        if st.button("🏭  Pase a Taller", use_container_width=True):
            st.switch_page("pages/3_ Pase a Taller.py")

# 3 Autorización
with col3:
    if "autorizacion" in access:
        if st.button("✅  Autorización", use_container_width=True):
            st.switch_page("pages/4_ Autorizacion.py")

col4, col5, col6 = st.columns(3)

# 4 Reporte iFuel
with col4:
    if "ifuel" in access:
        if st.button("⛽  Reporte iFuel", use_container_width=True):
            st.switch_page("pages/5_ Reporte iFuel.py")

# 5 Lector PDF
with col5:
    if "lector_pdf" in access:
        if st.button("📄  Lector PDF", use_container_width=True):
            st.switch_page("pages/2_ Lector PDF.py")

# 6 Consulta Reportes
with col6:
    if "consulta_reportes" in access:
        if st.button("📊  Consulta Reportes", use_container_width=True):
            st.switch_page("pages/6_ Consulta Reportes.py")

col7, col8, col9 = st.columns(3)

# 7 Preparación de Reportes
with col7:
    if "prepara_reportes" in access:
        if st.button("�  Preparación de Reportes", use_container_width=True):
            st.switch_page("pages/7_ Preparacion de Reportes.py")

# 8 Preparación de Reportes
with col7:
    if "gestiona_unidades" in access:
        if st.button("�  Gestion de Unidades", use_container_width=True):
            st.switch_page("pages/8_ Gestion de Unidades.py")

# -------------------------------
# Logout
# -------------------------------
st.divider()

if st.button("Cerrar sesión", type="secondary"):
    st.session_state.logged_in = False
    st.session_state.user = None
    st.switch_page("Home.py")