import streamlit as st
from datetime import datetime
from auth import require_login
from pathlib import Path
from PIL import Image
import json
#heregoesbackup
# -------------------------------
# Security gate
# -------------------------------
require_login()

st.set_page_config(
    page_title="Dashboard - BETA",
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
        border-radius: 16px;
        padding: 1.2rem;
    }

    div.stButton > button p,
    div.stButton > button span {
        font-size: 1.4rem !important;
        font-weight: 700 !important;
    }

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
# USER / ACCESS
# -------------------------------
user = st.session_state.user
access = user.get("access", [])
role = (user.get("role") or "").lower()

# -------------------------------
# CHANGELOG
# -------------------------------
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
# ASSETS
# -------------------------------
assets_dir = Path(__file__).parent.parent / "assets"
logo_path = assets_dir / "white_pgl.png"

# =============================
# FIELD USER VIEW
# =============================
if role == "field_user":
    # -------------------------------
    # HEADER
    # -------------------------------

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
        st.markdown(
            "<div style='margin-top: 35px;'></div>",
            unsafe_allow_html=True
        )

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

else:

    # -------------------------------
    # HEADER
    # -------------------------------
    col_logo, col_spacer, col_logout = st.columns([3, 7, 1.4])

    with col_logo:

        st.markdown(
            "<div style='margin-top:35px;'></div>",
            unsafe_allow_html=True
        )

        if logo_path.exists():
            img = Image.open(logo_path)

            st.image(
                img,
                width=220
            )

    with col_logout:

        st.markdown(
            """
            <style>

            div.stButton > button[kind="secondary"]{
                width:100%;
                height:48px;

                background:#BFA75F;
                color:white !important;

                border:none;
                border-radius:10px !important;

                font-weight:700;
                font-size:16px;

                display:flex;
                align-items:center;
                justify-content:center;

                text-align:center;

                box-shadow:0 4px 12px rgba(0,0,0,.18);
            }

            div.stButton > button[kind="secondary"]:hover{
                background:#D0B56C;
                color:white !important;
            }

            </style>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            "<div style='margin-top:28px;'></div>",
            unsafe_allow_html=True
        )

        if st.button(
            "Cerrar sesión",
            type="secondary",
            key="btn_logout_admin"
        ):
            st.session_state.logged_in = False
            st.session_state.user = None
            st.switch_page("Home.py")

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

#User Card

    st.markdown("""
    <style>

    .hero-card{
        background: linear-gradient(90deg,#232C7A 0%,#2F378E 100%);
        border-radius:24px;
        padding:45px 55px;
        border-left:8px solid #E23B2F;
        margin-top:10px;
        margin-bottom:10px;
        position:relative;
    }

    .hero-date{
        position:absolute;
        top:45px;
        right:55px;

        color:#AAB2D5;
        font-size:18px;
        font-weight:500;
    }

    .hero-welcome{
        color:#AAB2D5;
        font-size:20px;
        font-weight:600;
        margin-bottom:12px;
    }
    
    .hero-top{
        display:flex;
        justify-content:space-between;
        align-items:center;
        margin-bottom:12px;
    }

    .hero-date{
        color:#AAB2D5;
        font-size:18px;
        font-weight:500;
    }

    .hero-name{
        color:white;
        font-size:54px;
        font-weight:800;
        line-height:1.1;
        margin-bottom:20px;
    }

    .hero-role{
        display:inline-block;
        background:#EEF0FF;
        color:#1F2876;
        padding:8px 22px;
        border-radius:999px;
        font-size:18px;
        font-weight:700;
        margin-bottom:24px;
    }

    .hero-footer{
        color:#AAB2D5;
        font-size:20px;
    }

    </style>
    """, unsafe_allow_html=True)

    current_date = datetime.now().strftime("%d %B %Y")

    display_name = user["name"] or user["email"]

    display_role = (
        role.replace("_", " ").upper()
        if role else "USER"
    )

    st.markdown(
        f"""
<div class="hero-card">

<div class="hero-welcome">
    Bienvenid@
</div>

<div class="hero-date">
    {current_date}
</div>

<div class="hero-name">
{display_name}
</div>

<div class="hero-role">
{display_role}
</div>

<div class="hero-footer">
OMEGA · SYS. VER {latest_version}
</div>

</div>
        """,
        unsafe_allow_html=True,
    )
    
# -------------------------------
# HELPERS
# -------------------------------
def has_access(keys):
    return any(k in access for k in keys)

def render_button_grid(buttons, columns_per_row=2):

    visible_buttons = [
        b for b in buttons
        if b["access"] in access
    ]

    for i in range(0, len(visible_buttons), columns_per_row):

        row_buttons = visible_buttons[i:i + columns_per_row]

        cols = st.columns(columns_per_row)

        for idx, btn in enumerate(row_buttons):

            with cols[idx]:

                if st.button(
                    btn["label"],
                    use_container_width=True,
                    key=btn["key"]
                ):
                    st.switch_page(btn["page"])


# =============================
# FIELD USER VIEW
# =============================
if role == "field_user":
    # =============================
    # 1. GENERACION DE PASES Y SOLICITUDES
    # =============================
    section_generacion = [
        "pase_taller",
        "solicitud_viaticos",
        "bonos_operador"
    ]

    if has_access(section_generacion):

        st.subheader("🏭 Generación de Pases y Solicitudes")

        render_button_grid([
            {
                "access": "pase_taller",
                "label": "🏭  Generar nuevo Pase a Taller",
                "page": "pages/3_ Pase a Taller Beta.py",
                "key": "btn_pase_taller"
            },
            {
                "access": "solicitud_viaticos_D",
                "label": "💳  Solicitud de Viáticos y Reembolsos",
                "page": "pages/9_ Viaticos.py",
                "key": "btn_viaticos"
            },
            {
                "access": "bonos_operador",
                "label": "💰  Bono de Operadores",
                "page": "pages/13_ Formulario Bonos.py",
                "key": "btn_bonos_operador"
            }
        ])

        st.divider()

    # =============================
    # 2. GESTION DE ORDENES Y PASES
    # =============================
    section_gestion = [
        "autorizacion",
        "gestion_viaticos"
    ]

    if has_access(section_gestion):

        st.subheader("📋 Gestión de Órdenes y Pases")

        render_button_grid([
            {
                "access": "autorizacion",
                "label": "✅  Autorización y Gestión de Pases de Taller",
                "page": "pages/4_ Autorizacion.py",
                "key": "btn_autorizacion"
            },
            {
                "access": "gestion_viaticos",
                "label": "💼  Gestión de Viáticos",
                "page": "pages/10_ Gestion Viaticos.py",
                "key": "btn_gestion_viaticos"
            }
        ])

        st.divider()

    # =============================
    # 3. CONSULTAS
    # =============================
    section_consultas = [
        "consultar_reparacion",
        "consulta_reportes",
        "consulta_bonos_operador"
    ]

    if has_access(section_consultas):

        st.subheader("🔍 Consultas de Reparación y Reportes")

        render_button_grid([
            {
                "access": "consultar_reparacion",
                "label": "🔍  Consultar Historial de Reparación",
                "page": "pages/1_ Consultar Reparacion.py",
                "key": "btn_consultar_reparacion"
            },
            {
                "access": "consulta_reportes",
                "label": "📊  Consulta de Pases de Taller",
                "page": "pages/6_ Consulta Reportes.py",
                "key": "btn_consulta_reportes"
            },
            {
                "access": "consulta_bonos_operador",
                "label": "💰 Consultas y Reportes para Bono de Operadores",
                "page": "pages/14_ Consulta Bonos.py",
                "key": "btn_consulta_bonos_operador",
            }
        ])

        st.divider()

    # =============================
    # 4. EXTRAS
    # =============================
    section_extras = [
        "ifuel",
        "lector_pdf",
        "gps_tracking"
    ]

    if has_access(section_extras):

        st.subheader("⚙️ Extras")

        render_button_grid([
            {
                "access": "ifuel",
                "label": "⛽  Reporte iFuel",
                "page": "pages/5_ Reporte iFuel.py",
                "key": "btn_ifuel"
            },
            {
                "access": "lector_pdf",
                "label": "📄  Lector PDF",
                "page": "pages/2_ Lector PDF.py",
                "key": "btn_lector_pdf"
            },
            {
                "access": "gps_tracking",
                "label": "🛰️  Rastreador y Seguimiento GPS de Unidades",
                "page": "pages/11_ api_pull.py",
                "key": "btn_gps_tracking"
            }
        ])

        st.divider()

    # =============================
    # 5. AUDIT
    # =============================
    section_audit = [
        "prepara_reportes",
        "gestion_unidades"
    ]

    if has_access(section_audit):

        st.subheader("🧾 Audit")

        render_button_grid([
            {
                "access": "prepara_reportes",
                "label": "🛠️  Preparación de Reportes",
                "page": "pages/7_ Preparacion de Reportes.py",
                "key": "btn_prepara_reportes"
            },
            {
                "access": "gestion_unidades",
                "label": "🚚  Gestión de Unidades",
                "page": "pages/8_ Gestion de Unidades.py",
                "key": "btn_gestion_unidades"
            },
            {
                "access": "ai_testing",
                "label": "🚚  Pruebas de IA",
                "page": "pages/12_ AI_tests.py",
                "key": "btn_ai_testing"
            }
        ])

        st.divider()

else:

    st.markdown("## 📊 Resumen General")

    modules = [
        {
            "access": "pase_taller",
            "name": "Pase a Taller",
            "total": 0,
        },
        {
            "access": "solicitud_viaticos",
            "name": "Solicitud de Viáticos",
            "total": 0,
        },
        {
            "access": "bonos_operador",
            "name": "Bono de Operadores",
            "total": 0,
        },
    ]

    visible_modules = [
        m for m in modules
        if m["access"] in access
    ]

    CARDS_PER_ROW = 3

    for i in range(0, len(visible_modules), CARDS_PER_ROW):

        cols = st.columns(CARDS_PER_ROW)

        for col, module in zip(cols, visible_modules[i:i + CARDS_PER_ROW]):

            with col:

                with st.container(border=True):

                    st.caption("Total registros para")

                    st.markdown(f"#### {module['name']}")

                    st.write("")

                    st.markdown(
                        f"<h1 style='text-align:center;'>{module['total']}</h1>",
                        unsafe_allow_html=True
                    )

        st.write("")