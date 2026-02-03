import streamlit as st
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
    [data-testid="stSidebar"] {
        display: none;
    }

    /* Make buttons BIG */
    div.stButton > button {
        height: 90px;
        font-size: 1.1rem;
        font-weight: 600;
        border-radius: 14px;
        padding: 1.2rem;
        white-space: normal;
    }

    /* Slight hover effect */
    div.stButton > button:hover {
        transform: scale(1.02);
        transition: 0.15s ease-in-out;
    }
    </style>
    """,
    unsafe_allow_html=True
)

user = st.session_state.user
access = user.get("access", [])

# -------------------------------
# Header
# -------------------------------
st.title("Dashboard")
st.write(f"Bienvenido, **{user['name'] or user['email']}**")
st.write(f"Rol: `{user['role']}`")
st.divider()

# -------------------------------
# Navigation buttons
# -------------------------------
st.subheader("Módulos")

col1, col2, col3 = st.columns(3)

# 1️⃣ Consultar Reparación
with col1:
    if "consultar_reparacion" in access:
        if st.button("🔍  Consultar Reparación", use_container_width=True):
            st.switch_page("pages/1_ Consultar Reparacion.py")

# 2️⃣ Pase a Taller
with col2:
    if "pase_taller" in access:
        if st.button("🏭  Pase a Taller", use_container_width=True):
            st.switch_page("pages/3_ Pase a Taller.py")

# 3️⃣ Autorización
with col3:
    if "autorizacion" in access:
        if st.button("✅  Autorización", use_container_width=True):
            st.switch_page("pages/4_ Autorizacion.py")

col4, col5, col6 = st.columns(3)

# 4️⃣ Reporte iFuel
with col4:
    if "ifuel" in access:
        if st.button("⛽  Reporte iFuel", use_container_width=True):
            st.switch_page("pages/5_ Reporte iFuel.py")

# 5️⃣ Consulta Reportes
with col5:
    if "consulta_reportes" in access:
        if st.button("📊  Consulta Reportes", use_container_width=True):
            st.switch_page("pages/6_ Consulta Reportes.py")

# col6 intentionally left empty to preserve grid alignment

# -------------------------------
# Logout
# -------------------------------
st.divider()

if st.button("Cerrar sesión"):
    st.session_state.logged_in = False
    st.session_state.user = None
    st.switch_page("Home.py")