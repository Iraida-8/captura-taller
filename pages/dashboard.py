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
col_title, col_logout = st.columns([6, 1])

with col_title:
    st.title("📊 Dashboard")
    st.caption(f"{user['name'] or user['email']}  •  {user['role']}")

with col_logout:
    if st.button("Cerrar sesión", type="secondary", key="btn_logout_top"):
        st.session_state.logged_in = False
        st.session_state.user = None
        st.switch_page("Home.py")

# live date / time
clock_placeholder = st.empty()

clock_placeholder.caption(
    datetime.now().strftime("%A, %d %B %Y")
)

st.divider()

# -------------------------------
# Navigation
# -------------------------------

def has_access(keys):
    return any(k in access for k in keys)


# =============================
# 1. GESTION DE ORDENES DE TALLER
# =============================
section_ordenes = ["pase_taller", "autorizacion"]

if has_access(section_ordenes):
    st.subheader("🏭 Gestión y Captura de Órdenes de Taller")

    col1, col2 = st.columns(2)

    with col1:
        if "pase_taller" in access:
            if st.button("🏭  Pase a Taller", use_container_width=True, key="btn_pase_taller"):
                st.switch_page("pages/3_ Pase a Taller.py")

    with col2:
        if "autorizacion" in access:
            if st.button("✅  Autorización", use_container_width=True, key="btn_autorizacion"):
                st.switch_page("pages/4_ Autorizacion.py")

    st.divider()


# =============================
# 2. CONSULTAS
# =============================
section_consultas = ["consultar_reparacion", "consulta_reportes"]

if has_access(section_consultas):
    st.subheader("🔍 Consultas de Reparación y Reportes")

    col1, col2 = st.columns(2)

    with col1:
        if "consultar_reparacion" in access:
            if st.button("🔍  Consultar Reparación", use_container_width=True, key="btn_consultar_reparacion"):
                st.switch_page("pages/1_ Consultar Reparacion.py")

    with col2:
        if "consulta_reportes" in access:
            if st.button("📊  Consulta Reportes", use_container_width=True, key="btn_consulta_reportes"):
                st.switch_page("pages/6_ Consulta Reportes.py")

    st.divider()


# =============================
# 3. EXTRAS
# =============================
section_extras = ["ifuel", "lector_pdf"]

if has_access(section_extras):
    st.subheader("⚙️ Extras")

    col1, col2 = st.columns(2)

    with col1:
        if "ifuel" in access:
            if st.button("⛽  Reporte iFuel", use_container_width=True, key="btn_ifuel"):
                st.switch_page("pages/5_ Reporte iFuel.py")

    with col2:
        if "lector_pdf" in access:
            if st.button("📄  Lector PDF", use_container_width=True, key="btn_lector_pdf"):
                st.switch_page("pages/2_ Lector PDF.py")

    st.divider()


# =============================
# 4. AUDIT
# =============================
section_audit = ["prepara_reportes", "gestion_unidades"]

if has_access(section_audit):
    st.subheader("🧾 Audit")

    col1, col2 = st.columns(2)

    with col1:
        if "prepara_reportes" in access:
            if st.button("🛠️  Preparación de Reportes", use_container_width=True, key="btn_prepara_reportes"):
                st.switch_page("pages/7_ Preparacion de Reportes.py")

    with col2:
        if "gestion_unidades" in access:
            if st.button("🚚  Gestión de Unidades", use_container_width=True, key="btn_gestion_unidades"):
                st.switch_page("pages/8_ Gestion de Unidades.py")

    st.divider()