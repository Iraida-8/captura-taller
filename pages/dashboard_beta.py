import streamlit as st
from datetime import datetime
from auth import require_login
from pathlib import Path
from PIL import Image
import json
import streamlit.components.v1 as components
from supabase import create_client
from pages.css import load_css

# -------------------------------
# Security gate
# -------------------------------
require_login()

# -------------------------------
# RELEASE GATE
# -------------------------------
REQUIRED_RELEASE = "beta"
#REQUIRED_RELEASE = "release"

# -------------------------------
# PAGE SUFFIX
# -------------------------------
PAGE_SUFFIX = " Beta" if REQUIRED_RELEASE.lower() == "beta" else ""

user = st.session_state.user
access = user.get("access", [])
role = (user.get("role") or "").lower()

if REQUIRED_RELEASE not in access:
    st.error("No tienes permisos para acceder a esta versión del sistema.")
    st.stop()

# -------------------------------
# TITLE
# -------------------------------
st.set_page_config(
    page_title=(
        "Dashboard - OMEGA BETA"
        if REQUIRED_RELEASE.lower() == "beta"
        else "Dashboard - OMEGA"
    ),
    layout="wide"
)

# -------------------------------
# PAGE STYLE
# -------------------------------
load_css()

@st.cache_resource
def get_supabase():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_SERVICE_KEY"]
    )

supabase = get_supabase()

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
logo_path = assets_dir / "color_pgl.png"

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

            background:#F4F6FB;
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

def render_dashboard_cards(buttons, columns_per_row=3):

    visible_buttons = [
        b for b in buttons
        if b["access"] in access
    ]

    for i in range(0, len(visible_buttons), columns_per_row):

        cols = st.columns(columns_per_row)

        for col, btn in zip(cols, visible_buttons[i:i + columns_per_row]):

            with col:

                if st.button(
                    btn["label"],
                    key=f"dashboard_{btn['key']}",
                    use_container_width=True,
                ):
                    st.switch_page(btn["page"])

        st.markdown(
            "<div style='height:6px'></div>",
            unsafe_allow_html=True
        )

    # =============================
    # 1. GENERACION DE PASES Y SOLICITUDES
    # =============================
    section_generacion = [
        "pase_taller",
        "bonos_operador"
    ]

    if has_access(section_generacion):

        st.subheader("🏭 Generación de Pases y Solicitudes")

        render_button_grid([
            {
                "access": "pase_taller",
                "label": "🏭  Generar nuevo Pase a Taller",
                "page": f"pages/3_ Solicitudes y Pases{PAGE_SUFFIX}.py",
                "key": "btn_pase_taller"
            },
            {
                "access": "bonos_operador",
                "label": "💰  Bono de Operadores",
                "page": f"pages/13_ Formulario Bonos{PAGE_SUFFIX}.py",
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

    st.subheader("📋 Gestión de Órdenes y Pases")

    render_button_grid([
        {
            "access": "autorizacion",
            "label": "✅  Autorización y Gestión de Pases de Taller",
            "page": f"pages/4_ Autorizacion{PAGE_SUFFIX}.py",
            "key": "btn_autorizacion"
        },
        {
            "access": "gestion_viaticos",
            "label": "💼  Gestión de Viáticos",
            "page": f"pages/10_ Gestion Viaticos{PAGE_SUFFIX}.py",
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
                "page": f"pages/1_ Consultar Reparacion{PAGE_SUFFIX}.py",
                "key": "btn_consultar_reparacion"
            },
            {
                "access": "consulta_reportes",
                "label": "📊  Consulta de Pases de Taller",
                "page": f"pages/6_ Consulta Reportes{PAGE_SUFFIX}.py",
                "key": "btn_consulta_reportes"
            },
            {
                "access": "consulta_bonos_operador",
                "label": "💰 Consulta Bonos de Operadores",
                "page": f"pages/14_ Consulta Bonos{PAGE_SUFFIX}.py",
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
                "page": f"pages/5_ Reporte iFuel{PAGE_SUFFIX}.py",
                "key": "btn_ifuel"
            },
            {
                "access": "lector_pdf",
                "label": "📄  Lector PDF",
                "page": f"pages/2_ Lector PDF{PAGE_SUFFIX}.py",
                "key": "btn_lector_pdf"
            },
            {
                "access": "gps_tracking",
                "label": "🛰️  Rastreador y Seguimiento GPS de Unidades",
                "page": f"pages/11_ api_pull{PAGE_SUFFIX}.py",
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
                "page": f"pages/7_ Preparacion de Reportes{PAGE_SUFFIX}.py",
                "key": "btn_prepara_reportes"
            },
            {
                "access": "gestion_unidades",
                "label": "🚚  Gestión de Unidades",
                "page": f"pages/8_ Gestion de Unidades{PAGE_SUFFIX}.py",
                "key": "btn_gestion_unidades"
            },
            {
                "access": "ai_testing",
                "label": "🚚  Pruebas de IA",
                "page": f"pages/12_ AI_tests{PAGE_SUFFIX}.py",
                "key": "btn_ai_testing"
            }
        ])

        st.divider()

    # =============================
    # ADMIN, MANAGER, REGULAR USER VIEW
    # =============================
    else:


        show_kpis = role in ["admin", "manager"]

        if show_kpis:

            st.markdown("## 📊 Resumen General")

            # =====================================================
            # KPI TOTALS
            # =====================================================

            total_viaticos = (
                supabase.table("solicitud_viaje")
                .select("*", count="exact", head=True)
                .execute()
                .count
            )

            total_bonos = (
                supabase.table("bonos_operadores")
                .select("*", count="exact", head=True)
                .execute()
                .count
            )

            ACCESS_TABLE_MAP = {
                "igloo": "IGLOO",
                "lincoln": "LINCOLN",
                "picus": "PICUS",
                "setlogis": "SLP",
                "setfreight": "SFI",
            }

            pase_tables = [
                tabla
                for permiso, tabla in ACCESS_TABLE_MAP.items()
                if permiso in access
            ]

            total_pases = 0

            for table in pase_tables:

                response = (
                    supabase.table(table)
                    .select("*", count="exact", head=True)
                    .execute()
                )

                total_pases += response.count or 0

            # =====================================================
            # MODULES
            # =====================================================

            modules = [
                {
                    "access": "pase_taller",
                    "name": "Pase a Taller",
                    "total": total_pases,
                },
                {
                    "access": "solicitud_viaticos",
                    "name": "Solicitud de Viáticos",
                    "total": total_viaticos,
                },
                {
                    "access": "bonos_operador",
                    "name": "Bono de Operadores",
                    "total": total_bonos,
                },
            ]

            visible_modules = [
                m for m in modules
                if m["access"] in access
            ]

            cols = st.columns(3)

            for i, module in enumerate(visible_modules):

                with cols[i % 3]:

                    html = f"""
                    <div style="padding:6px 6px 18px 6px;">
                        <div style="
                            background:#FFF7D6;
                            padding:20px;
                            border-radius:18px;
                            box-shadow:0 4px 10px rgba(0,0,0,.10);
                            min-height:185px;
                            color:#111;
                            font-family:sans-serif;
                        ">

                            <div style="
                                color:#666666;
                                font-size:15px;
                                font-weight:600;
                            ">
                                Total registros para
                            </div>

                            <div style="
                                color:#111111;
                                font-size:28px;
                                font-weight:700;
                                margin-top:18px;
                                line-height:1.25;
                            ">
                                {module['name']}
                            </div>

                            <div style="
                                text-align:center;
                                color:#111111;
                                font-size:58px;
                                font-weight:800;
                                margin-top:42px;
                            ">
                                {module['total']:,}
                            </div>

                        </div>
                    </div>
                    """

                    components.html(html, height=255)

            st.write("")

            st.divider()

        # =================================
        #  ROW 1 OPERACIÓN / GESTIÓN
        # =================================
        show_operacion = has_access([
            "pase_taller",
            "bonos_operador",
        ])

        show_gestion = has_access([
            "autorizacion",
            "gestion_viaticos",
        ])

        if show_operacion and show_gestion:
            col1, col2 = st.columns(2)

        elif show_operacion:
            col1 = st.container()

        elif show_gestion:
            col2 = st.container()

        # =============================
        # 1. OPERACIÓN
        # =============================
        if show_operacion:

            with col1:

                section_operacion = [
                    "pase_taller",
                    "bonos_operador",
                ]

                with st.container(border=True):

                    st.markdown("## 🏭 SOLICITUDES Y PASES")

                    st.divider()

                    st.markdown("""
        **Módulos incluidos**

        - 🛠️ Captura de Pases de Taller
        - 💰 Bono de Operadores

        Permite registrar solicitudes de taller, generar Bonos de Operadores y administrar la captura inicial de la operación.
        """)

                    if st.button(
                        "Abrir módulo",
                        key="btn_operacion",
                        use_container_width=True,
                    ):
                        st.switch_page(
                            f"pages/3_ Solicitudes y Pases{PAGE_SUFFIX}.py"
                        )

        # =============================
        # 2. GESTIÓN
        # =============================
        if show_gestion:

            with col2:

                section_gestion = [
                    "autorizacion",
                    "gestion_viaticos",
                ]

                if has_access(section_gestion):

                    with st.container(border=True):

                        st.markdown("## 📋 GESTIÓN DE ÓRDENES Y PASES")

                        st.divider()

                        st.markdown("""
            **Módulos incluidos**

            - ✅ Autorización y Gestión de Pases de Taller
            - 💼 Gestión de Viáticos

            Permite autorizar, actualizar y dar seguimiento a Pases de Taller, así como gestionar Solicitudes de Viáticos y Reembolsos desde una única interfaz operativa.
            """)

                        if st.button(
                            "Abrir módulo",
                            key="btn_gestion_operacion",
                            use_container_width=True,
                        ):
                            st.switch_page(
                                f"pages/4_ Autorizacion{PAGE_SUFFIX}.py"
                            )

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

            render_dashboard_cards([
                {
                    "access": "consultar_reparacion",
                    "label": "🔍  Consultar Historial de Reparación",
                    "page": f"pages/1_ Consultar Reparacion{PAGE_SUFFIX}.py",
                    "key": "btn_consultar_reparacion"
                },
                {
                    "access": "consulta_reportes",
                    "label": "📊  Consulta de Pases de Taller",
                    "page": f"pages/6_ Consulta Reportes{PAGE_SUFFIX}.py",
                    "key": "btn_consulta_reportes"
                },
                {
                    "access": "consulta_bonos_operador",
                    "label": "💰 Consulta Bonos de Operadores",
                    "page": f"pages/14_ Consulta Bonos{PAGE_SUFFIX}.py",
                    "key": "btn_consulta_bonos_operador",
                }
            ])

            st.divider()

        # =================================
        # ROW 4 EXTRAS / GPS
        # =================================
        show_extras = has_access([
            "ifuel",
            "lector_pdf",
        ])

        show_gps = has_access([
            "gps_tracking",
        ])

        if show_extras and show_gps:
            col1, col2 = st.columns(2)

        elif show_extras:
            col1 = st.container()

        elif show_gps:
            col2 = st.container()

        # =============================
        # 1. EXTRAS
        # =============================
        if show_extras:

            with col1:

                section_extras = [
                    "ifuel",
                    "lector_pdf",
                ]

                with st.container(border=True):

                    st.markdown("## ⚙️ EXTRAS")

                    st.divider()

                    st.markdown("""
        **Módulos incluidos**

        - 📄 Lector PDF
        - ⛽ Reporte iFuel

        Permite consultar archivos PDF de reparación y generar reportes operativos de iFuel desde una única interfaz.
        """)

                    if st.button(
                        "Abrir módulo",
                        key="btn_extras",
                        use_container_width=True,
                    ):
                        st.switch_page(
                            f"pages/5_ Extras{PAGE_SUFFIX}.py"
                        )

        # =============================
        # 2. GPS
        # =============================
        if show_gps:

            with col2:

                section_gps = [
                    "gps_tracking",
                ]

                if has_access(section_gps):

                    with st.container(border=True):

                        st.markdown("## 🛰️ RASTREADOR Y SEGUIMIENTO GPS")

                        st.divider()

                        st.markdown("""
        **Módulo incluido**

        - 🛰️ Rastreador y Seguimiento GPS de Unidades

        Permite visualizar la ubicación en tiempo real de las unidades, consultar indicadores operativos y dar seguimiento a la flota.
        """)

                        if st.button(
                            "Abrir módulo",
                            key="btn_gps_tracking",
                            use_container_width=True,
                        ):
                            st.switch_page(
                                f"pages/11_ api_pull{PAGE_SUFFIX}.py"
                            )

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

            render_dashboard_cards([
                {
                    "access": "prepara_reportes",
                    "label": "🛠️  Preparación de Reportes",
                    "page": f"pages/7_ Preparacion de Reportes{PAGE_SUFFIX}.py",
                    "key": "btn_prepara_reportes"
                },
                {
                    "access": "gestion_unidades",
                    "label": "🚚  Gestión de Unidades",
                    "page": f"pages/8_ Gestion de Unidades{PAGE_SUFFIX}.py",
                    "key": "btn_gestion_unidades"
                },
                {
                    "access": "ai_testing",
                    "label": "🚚  Pruebas de IA",
                    "page": f"pages/12_ AI_tests{PAGE_SUFFIX}.py",
                    "key": "btn_ai_testing"
                }
            ])

            st.divider()   