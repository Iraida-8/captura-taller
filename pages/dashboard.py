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
    page_title="Dashboard - Pase de Taller",
    layout="wide"
)

# -------------------------------
# MODERN DASHBOARD CSS
# -------------------------------
st.markdown("""
<style>

/* -------------------------------------------------- */
/* PAGE */
/* -------------------------------------------------- */

[data-testid="stSidebar"]{
    display:none;
}

.stApp{
    background:#F4F6FB;
}

.block-container{
    padding-top:0rem;
    padding-left:2rem;
    padding-right:2rem;
    padding-bottom:2rem;
    max-width:100%;
}

/* hide streamlit header */

header{
    visibility:hidden;
}

footer{
    visibility:hidden;
}

/* -------------------------------------------------- */
/* NAVBAR */
/* -------------------------------------------------- */

.navbar{

    position:sticky;
    top:0;

    z-index:999;

    margin-left:-2rem;
    margin-right:-2rem;
    margin-top:-1rem;

    height:72px;

    background:#202A78;

    display:flex;

    align-items:center;

    justify-content:space-between;

    padding-left:30px;
    padding-right:30px;

    box-shadow:

        0 5px 18px rgba(0,0,0,.18);

}

/* logo */

.nav-left{

    display:flex;
    align-items:center;
    gap:40px;

}

.logo-title{

    color:white;

    font-size:28px;

    font-weight:700;

}

/* menus */

.nav-menu{

    display:flex;

    gap:10px;

    align-items:center;

}

.menu-item{

    color:white;

    padding:

        12px 18px;

    border-radius:12px;

    transition:.25s;

    cursor:pointer;

    font-size:17px;

    font-weight:500;

}

.menu-item:hover{

    background:rgba(255,255,255,.12);

}

/* user */

.user-panel{

    display:flex;

    align-items:center;

    gap:15px;

    color:white;

}

.user-name{

    font-weight:700;

    font-size:18px;

}

.user-role{

    font-size:13px;

    opacity:.8;

}

/* -------------------------------------------------- */
/* HERO */
/* -------------------------------------------------- */

.hero{

    margin-top:35px;

    border-radius:26px;

    background:

        linear-gradient(
        135deg,
        #24338C,
        #202A78);

    padding:45px;

    color:white;

    box-shadow:

        0 12px 40px rgba(25,35,90,.22);

}

.hero h1{

    color:white;

    margin-bottom:10px;

    font-size:48px;

}

.hero p{

    color:#D5DBFF;

    font-size:18px;

}

.badge{

    display:inline-block;

    margin-top:18px;

    background:white;

    color:#202A78;

    padding:

        8px 20px;

    border-radius:50px;

    font-weight:700;

    font-size:14px;

}

/* -------------------------------------------------- */
/* SECTION TITLES */
/* -------------------------------------------------- */

.section-title{

    margin-top:45px;

    margin-bottom:20px;

    color:#202A78;

    font-size:34px;

    font-weight:700;

}

/* -------------------------------------------------- */
/* BUTTONS */
/* -------------------------------------------------- */

div.stButton>button{

    height:82px;

    border-radius:18px;

    background:white;

    border:none;

    color:#202A78;

    font-size:18px !important;

    font-weight:700;

    box-shadow:

        0 8px 24px rgba(0,0,0,.08);

    transition:.25s;

}

div.stButton>button:hover{

    transform:

        translateY(-4px);

    box-shadow:

        0 18px 36px rgba(0,0,0,.15);

    border:none;

    color:#202A78;

}

/* logout */

button[kind="secondary"]{

    border-radius:10px;

    background:#D72638;

    color:white;

    border:none;

    font-weight:700;

}

button[kind="secondary"]:hover{

    background:#B31928;

    color:white;

}

</style>

""", unsafe_allow_html=True)

# -------------------------------
# USER / ACCESS
# -------------------------------
user = st.session_state.user
access = user.get("access", [])

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

# --------------------------------------------------------
# MODERN HEADER
# --------------------------------------------------------

assets_dir = Path(__file__).parent.parent / "assets"
logo_path = assets_dir / "white_pgl.png"

top_left, top_center, top_right = st.columns([2,8,2])

with top_left:

    if logo_path.exists():
        st.image(
            Image.open(logo_path),
            width=170
        )

with top_center:

    menu = st.columns(6)

    with menu[0]:
        st.button(
            "🏠 Principal",
            use_container_width=True,
            disabled=True
        )

    with menu[1]:
        with st.popover("🏭 Solicitudes"):

            if "pase_taller" in access:
                if st.button(
                    "Generar Pase",
                    use_container_width=True,
                    key="nav_pase"
                ):
                    st.switch_page("pages/3_ Pase a Taller.py")

            if "solicitud_viaticos_D" in access:
                if st.button(
                    "Solicitud Viáticos",
                    use_container_width=True,
                    key="nav_viaticos"
                ):
                    st.switch_page("pages/9_ Viaticos.py")

            if "bonos_operador" in access:
                if st.button(
                    "Bono Operadores",
                    use_container_width=True,
                    key="nav_bonos"
                ):
                    st.switch_page("pages/13_ Formulario Bonos.py")

    with menu[2]:
        with st.popover("📋 Gestión"):

            if "autorizacion" in access:
                if st.button(
                    "Autorización",
                    key="nav_auto",
                    use_container_width=True
                ):
                    st.switch_page("pages/4_ Autorizacion.py")

            if "gestion_viaticos" in access:
                if st.button(
                    "Gestión Viáticos",
                    key="nav_gestion",
                    use_container_width=True
                ):
                    st.switch_page("pages/10_ Gestion Viaticos.py")

    with menu[3]:
        with st.popover("🔍 Consultas"):

            if "consultar_reparacion" in access:
                if st.button(
                    "Historial Reparación",
                    key="nav_historial",
                    use_container_width=True
                ):
                    st.switch_page("pages/1_ Consultar Reparacion.py")

            if "consulta_reportes" in access:
                if st.button(
                    "Consulta Pases",
                    key="nav_reportes",
                    use_container_width=True
                ):
                    st.switch_page("pages/6_ Consulta Reportes.py")

    with menu[4]:
        with st.popover("⚙ Extras"):

            if "ifuel" in access:
                if st.button(
                    "Reporte iFuel",
                    key="nav_ifuel",
                    use_container_width=True
                ):
                    st.switch_page("pages/5_ Reporte iFuel.py")

            if "lector_pdf" in access:
                if st.button(
                    "Lector PDF",
                    key="nav_pdf",
                    use_container_width=True
                ):
                    st.switch_page("pages/2_ Lector PDF.py")

            if "gps_tracking" in access:
                if st.button(
                    "GPS",
                    key="nav_gps",
                    use_container_width=True
                ):
                    st.switch_page("pages/11_ api_pull.py")

    with menu[5]:
        with st.popover("🧾 Audit"):

            if "prepara_reportes" in access:
                if st.button(
                    "Preparación Reportes",
                    key="nav_prepara",
                    use_container_width=True
                ):
                    st.switch_page("pages/7_ Preparacion de Reportes.py")

            if "gestion_unidades" in access:
                if st.button(
                    "Gestión Unidades",
                    key="nav_unidades",
                    use_container_width=True
                ):
                    st.switch_page("pages/8_ Gestion de Unidades.py")

            if "ai_testing" in access:
                if st.button(
                    "Pruebas IA",
                    key="nav_ai",
                    use_container_width=True
                ):
                    st.switch_page("pages/12_ AI_tests.py")

with top_right:

    st.markdown(f"""
### 👤 {user["name"]}

<small>{datetime.now().strftime("%d/%m/%Y")}</small>
""", unsafe_allow_html=True)

    if st.button(
        "Cerrar sesión",
        use_container_width=True,
        type="secondary"
    ):
        st.session_state.logged_in=False
        st.session_state.user=None
        st.switch_page("Home.py")

# -------------------------------
# HELPERS
# -------------------------------

def has_access(keys):
    return any(k in access for k in keys)


def render_module_section(title, buttons, columns=3):
    """
    Modern dashboard card layout.
    Preserves all existing access control and navigation.
    """

    visible = [
        b for b in buttons
        if b["access"] in access
    ]

    if not visible:
        return

    st.markdown(
        f"<div class='section-title'>{title}</div>",
        unsafe_allow_html=True
    )

    rows = [
        visible[i:i + columns]
        for i in range(0, len(visible), columns)
    ]

    for row in rows:

        cols = st.columns(columns)

        for i, btn in enumerate(row):

            with cols[i]:

                if st.button(
                    btn["label"],
                    key=btn["key"],
                    use_container_width=True
                ):
                    st.switch_page(btn["page"])

        st.write("")

    st.divider()

# ============================================================
# SOLICITUDES
# ============================================================

section_generacion = [
    "pase_taller",
    "solicitud_viaticos_D",
    "bonos_operador"
]

if has_access(section_generacion):

    render_module_section(
        "🏭 Solicitudes",
        [
            {
                "access": "pase_taller",
                "label": "🏭\nGenerar Pase a Taller",
                "page": "pages/3_ Pase a Taller.py",
                "key": "btn_pase_taller"
            },
            {
                "access": "solicitud_viaticos_D",
                "label": "💳\nViáticos y Reembolsos",
                "page": "pages/9_ Viaticos.py",
                "key": "btn_viaticos"
            },
            {
                "access": "bonos_operador",
                "label": "💰\nBono Operadores",
                "page": "pages/13_ Formulario Bonos.py",
                "key": "btn_bonos"
            }
        ]
    )


# ============================================================
# GESTIÓN
# ============================================================

section_gestion = [
    "autorizacion",
    "gestion_viaticos"
]

if has_access(section_gestion):

    render_module_section(
        "📋 Gestión",
        [
            {
                "access": "autorizacion",
                "label": "✅\nAutorización",
                "page": "pages/4_ Autorizacion.py",
                "key": "btn_autorizacion"
            },
            {
                "access": "gestion_viaticos",
                "label": "💼\nGestión Viáticos",
                "page": "pages/10_ Gestion Viaticos.py",
                "key": "btn_gestion_viaticos"
            }
        ]
    )


# ============================================================
# CONSULTAS
# ============================================================

section_consultas = [
    "consultar_reparacion",
    "consulta_reportes",
    "consulta_bonos_operador"
]

if has_access(section_consultas):

    render_module_section(
        "🔍 Consultas",
        [
            {
                "access": "consultar_reparacion",
                "label": "🔍\nHistorial Reparación",
                "page": "pages/1_ Consultar Reparacion.py",
                "key": "btn_consultar_reparacion"
            },
            {
                "access": "consulta_reportes",
                "label": "📊\nConsulta Pases",
                "page": "pages/6_ Consulta Reportes.py",
                "key": "btn_consulta_reportes"
            },
            {
                "access": "consulta_bonos_operador",
                "label": "💰\nConsulta Bonos",
                "page": "pages/14_ Consulta Bonos.py",
                "key": "btn_consulta_bonos"
            }
        ]
    )


# ============================================================
# EXTRAS
# ============================================================

section_extras = [
    "ifuel",
    "lector_pdf",
    "gps_tracking"
]

if has_access(section_extras):

    render_module_section(
        "⚙ Extras",
        [
            {
                "access": "ifuel",
                "label": "⛽\niFuel",
                "page": "pages/5_ Reporte iFuel.py",
                "key": "btn_ifuel"
            },
            {
                "access": "lector_pdf",
                "label": "📄\nLector PDF",
                "page": "pages/2_ Lector PDF.py",
                "key": "btn_pdf"
            },
            {
                "access": "gps_tracking",
                "label": "🛰️\nGPS",
                "page": "pages/11_ api_pull.py",
                "key": "btn_gps"
            }
        ]
    )


# ============================================================
# AUDIT
# ============================================================

section_audit = [
    "prepara_reportes",
    "gestion_unidades",
    "ai_testing"
]

if has_access(section_audit):

    render_module_section(
        "🧾 Audit",
        [
            {
                "access": "prepara_reportes",
                "label": "🛠️\nPreparación Reportes",
                "page": "pages/7_ Preparacion de Reportes.py",
                "key": "btn_prepara"
            },
            {
                "access": "gestion_unidades",
                "label": "🚚\nGestión Unidades",
                "page": "pages/8_ Gestion de Unidades.py",
                "key": "btn_unidades"
            },
            {
                "access": "ai_testing",
                "label": "🤖\nPruebas IA",
                "page": "pages/12_ AI_tests.py",
                "key": "btn_ai"
            }
        ]
    )