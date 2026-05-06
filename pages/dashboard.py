import streamlit as st
from datetime import datetime
from auth import require_login
from pathlib import Path
from PIL import Image
import json

# -------------------------------
# Security gate
# -------------------------------
require_login()

st.set_page_config(
    page_title="Dashboard - Pase de Taller",
    layout="wide"
)

# -------------------------------
# CSS
# -------------------------------
st.markdown(
    """
    <style>
    /* Hide sidebar */
    [data-testid="stSidebar"] {
        display: none;
    }

    /* App background */
    .stApp {
        background-color: #151F6D;
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
        color: #FFFFFF;
    }

    h2, h3 {
        margin-top: 0.5rem;
        color: #BFA75F;
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

        background-color: #1B267A;
        color: #FFFFFF;
        border: 1px solid rgba(191, 167, 95, 0.25);
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.12);
        transition: all 0.2s ease-in-out;
    }

    /* Hover */
    div.stButton > button:hover {
        transform: translateY(-2px);
        background-color: #24338C;
        border-color: #BFA75F;
        color: #BFA75F;
    }

    /* =========================
       LOGOUT BUTTON
       ========================= */
    button[kind="secondary"] {
        display: block;
        margin-left: auto;
        margin-right: auto;
        border-radius: 12px;
        background-color: transparent;
        color: #BFA75F;
        border: 1px solid #BFA75F;
        font-weight: 600;
    }

    button[kind="secondary"]:hover {
        background-color: #BFA75F;
        color: #151F6D;
    }

    /* Text */
    p, label, span {
        color: #F5F5F5;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# -------------------------------
user = st.session_state.user
access = user.get("access", [])

changelog_path = Path(__file__).parent.parent / "Changelog.json"

if changelog_path.exists():
    with open(changelog_path, "r", encoding="utf-8") as f:
        changelog_data = json.load(f)
else:
    changelog_data = []

latest_version = (
    changelog_data[0].get("version", "0.00.00.00")
    if changelog_data
    else "0.00.00.00"
)

# -------------------------------
# Header
# -------------------------------

from pathlib import Path
from PIL import Image

assets_dir = Path(__file__).parent.parent / "assets"
logo_path = assets_dir / "white_pgl.png"

col_info, col_logo, col_logout = st.columns([5, 3, 1])

with col_info:
    st.title("📊 Menu Principal")

    st.caption(f"SYS. VER {latest_version}")

    st.caption(
        f"{user['name'] or user['email']}"
    )

    # live date / time
    clock_placeholder = st.empty()
    clock_placeholder.caption(
        datetime.now().strftime("%A, %d %B %Y")
    )

with col_logo:
    st.markdown("<div style='margin-top: 35px;'></div>", unsafe_allow_html=True)

    if logo_path.exists():
        img = Image.open(logo_path)
        st.image(
            img,
            width=300
        )

with col_logout:
    if st.button(
        "Cerrar sesión",
        type="secondary",
        key="btn_logout_top"
    ):
        st.session_state.logged_in = False
        st.session_state.user = None
        st.switch_page("Home.py")

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
            if st.button("🏭  Generar nuevo Pase a Taller", use_container_width=True, key="btn_pase_taller"):
                st.switch_page("pages/3_ Pase a Taller.py")

    with col2:
        if "autorizacion" in access:
            if st.button("✅  Autorización y Gestión de Pases de Taller", use_container_width=True, key="btn_autorizacion"):
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
            if st.button("🔍  Consultar Historial de Reparación", use_container_width=True, key="btn_consultar_reparacion"):
                st.switch_page("pages/1_ Consultar Reparacion.py")

    with col2:
        if "consulta_reportes" in access:
            if st.button("📊  Consulta de Pases de Taller", use_container_width=True, key="btn_consulta_reportes"):
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
section_audit = ["prepara_reportes", "gestion_unidades", "solicitud_viaticos"]

if has_access(section_audit):
    st.subheader("🧾 Audit")

    # ROW 1
    col1, col2 = st.columns(2)

    with col1:
        if "prepara_reportes" in access:
            if st.button(
                "🛠️  Preparación de Reportes",
                use_container_width=True,
                key="btn_prepara_reportes"
            ):
                st.switch_page("pages/7_ Preparacion de Reportes.py")

    with col2:
        if "gestion_unidades" in access:
            if st.button(
                "🚚  Gestión de Unidades",
                use_container_width=True,
                key="btn_gestion_unidades"
            ):
                st.switch_page("pages/8_ Gestion de Unidades.py")

    # ROW 2
    col3, col4 = st.columns(2)

    with col3:
        if "solicitud_viaticos" in access:
            if st.button(
                "💳  Solicitud de Viáticos y Reembolsos",
                use_container_width=True,
                key="btn_viaticos"
            ):
                st.switch_page("pages/9_ Viaticos.py")

    st.divider()