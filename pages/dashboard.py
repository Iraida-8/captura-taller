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
# HEADER
# -------------------------------
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
# 1. GENERACION DE PASES Y SOLICITUDES
# =============================
section_generacion = [
    "pase_taller",
    "solicitud_viaticos"
]

if has_access(section_generacion):

    st.subheader("🏭 Generación de Pases y Solicitudes")

    render_button_grid([
        {
            "access": "pase_taller",
            "label": "🏭  Generar nuevo Pase a Taller",
            "page": "pages/3_ Pase a Taller.py",
            "key": "btn_pase_taller"
        },
        {
            "access": "solicitud_viaticos",
            "label": "💳  Solicitud de Viáticos y Reembolsos",
            "page": "pages/9_ Viaticos.py",
            "key": "btn_viaticos"
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
    "consulta_reportes"
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
        },
        {
            "access": "bonos_operador",
            "label": "💰 Bono de Operadores",
            "page": "pages/13_ Formulario Bonos.py",
            "key": "btn_bonos_operador"
        }
    ])

    st.divider()

    # ==========================================
# BONO DE OPERADORES
# ==========================================

st.title("💰 Bono de Operadores")

# ------------------------------------------
# PARAMETROS TEMPORALES
# ------------------------------------------

PRECIO_DIESEL = 10.00

RENDIMIENTOS = {
    "TR-001": {"min": 2.8, "max": 3.2},
    "TR-002": {"min": 2.6, "max": 3.0},
    "TR-003": {"min": 3.0, "max": 3.4},
}

# ------------------------------------------
# FORMULARIO
# ------------------------------------------

st.subheader("📋 Datos del Viaje")

col1, col2 = st.columns(2)

with col1:
    unidad = st.selectbox(
        "Unidad",
        list(RENDIMIENTOS.keys())
    )

    operador = st.text_input("Operador")

    origen = st.text_input("Origen")

    destino = st.text_input("Destino")

with col2:
    tipo_ruta = st.selectbox(
        "Tipo de Ruta",
        ["Corta", "Larga"]
    )

    numero_trafico = st.text_input(
        "Número de Tráfico"
    )

    kilometros = st.number_input(
        "Kilómetros Recorridos",
        min_value=0.0,
        step=1.0
    )

    litros_cargados = st.number_input(
        "Litros Cargados",
        min_value=0.0,
        step=1.0
    )

st.divider()

# ------------------------------------------
# PARAMETROS
# ------------------------------------------

st.subheader("⚙️ Parámetros")

rend_min = RENDIMIENTOS[unidad]["min"]
rend_max = RENDIMIENTOS[unidad]["max"]

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Rendimiento Mínimo",
        f"{rend_min:.2f} km/l"
    )

with col2:
    st.metric(
        "Rendimiento Máximo",
        f"{rend_max:.2f} km/l"
    )

with col3:
    precio_diesel = st.number_input(
        "Precio Diesel ($)",
        value=PRECIO_DIESEL,
        step=0.5
    )

st.divider()

# ------------------------------------------
# CALCULO
# ------------------------------------------

if st.button(
    "🧮 Calcular Bono",
    use_container_width=True
):

    errores = []

    if kilometros <= 0:
        errores.append(
            "Los kilómetros recorridos deben ser mayores a cero."
        )

    if litros_cargados <= 0:
        errores.append(
            "Los litros cargados deben ser mayores a cero."
        )

    if kilometros > 5000:
        errores.append(
            "Kilometraje fuera de rango."
        )

    rendimiento_real = (
        kilometros / litros_cargados
        if litros_cargados > 0
        else 0
    )

    if rendimiento_real < 1:
        errores.append(
            f"Rendimiento ilógico ({rendimiento_real:.2f} km/l)."
        )

    if rendimiento_real > 8:
        errores.append(
            f"Rendimiento ilógico ({rendimiento_real:.2f} km/l)."
        )

    if errores:

        for error in errores:
            st.error(error)

    else:

        rendimiento_objetivo = (
            rend_min + rend_max
        ) / 2

        litros_esperados = (
            kilometros / rendimiento_objetivo
        )

        diferencia_litros = (
            litros_esperados - litros_cargados
        )

        monto = (
            diferencia_litros * precio_diesel
        )

        st.divider()

        st.subheader("📊 Resultado")

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Rendimiento Real",
            f"{rendimiento_real:.2f} km/l"
        )

        c2.metric(
            "Litros Esperados",
            f"{litros_esperados:.2f}"
        )

        c3.metric(
            "Litros Reales",
            f"{litros_cargados:.2f}"
        )

        c4.metric(
            "Diferencia",
            f"{diferencia_litros:.2f}"
        )

        if monto > 0:

            st.success(
                f"✅ BONO AL OPERADOR: ${monto:,.2f}"
            )

        elif monto < 0:

            st.error(
                f"❌ COBRO AL OPERADOR: ${abs(monto):,.2f}"
            )

        else:

            st.info(
                "Sin bono ni cobro."
            )