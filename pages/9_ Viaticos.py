import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime, date, timezone
from auth import require_login, require_access

# =================================
# Page configuration
# =================================
st.set_page_config(
    page_title="Solicitud de Viaticos y Reembolsos",
    layout="wide"
)
# =================================
# Security gates
# =================================
require_login()
require_access("solicitud_viaticos")

# =================================
# Top navigation
# =================================
if st.button("⬅ Volver al Dashboard"):
    st.switch_page("pages/dashboard.py")

st.divider()

# =================================
# TABS
# =================================
tab_solicitud, tab_comprobacion = st.tabs([
    "🧳 SOLICITUD GTOS DE VIAJE",
    "🧾 COMPROBACION GTOS VIAJE"
])

# =================================
# TAB 1 — SOLICITUD
# =================================
with tab_solicitud:

    st.subheader("🧳 Solicitud de Fondo para Gastos de Viaje")

    # =========================================
    # SUCURSAL (ONLY ONE SELECTABLE)
    # =========================================
    st.markdown("### Sucursal")

    if "selected_sucursal" not in st.session_state:
        st.session_state.selected_sucursal = None

    def set_sucursal(value):
        st.session_state.selected_sucursal = value

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.checkbox(
            "NUEVO LAREDO",
            value=st.session_state.selected_sucursal == "NUEVO LAREDO",
            on_change=set_sucursal,
            args=("NUEVO LAREDO",),
            key="chk_nuevo_laredo"
        )

    with col2:
        st.checkbox(
            "DALLAS",
            value=st.session_state.selected_sucursal == "DALLAS",
            on_change=set_sucursal,
            args=("DALLAS",),
            key="chk_dallas"
        )

    with col3:
        st.checkbox(
            "CHICAGO",
            value=st.session_state.selected_sucursal == "CHICAGO",
            on_change=set_sucursal,
            args=("CHICAGO",),
            key="chk_chicago"
        )

    with col4:
        st.checkbox(
            "GUADALAJARA",
            value=st.session_state.selected_sucursal == "GUADALAJARA",
            on_change=set_sucursal,
            args=("GUADALAJARA",),
            key="chk_guadalajara"
        )

    with col5:
        st.checkbox(
            "MONTERREY",
            value=st.session_state.selected_sucursal == "MONTERREY",
            on_change=set_sucursal,
            args=("MONTERREY",),
            key="chk_monterrey"
        )

    col6, col7, col8, col9, col10 = st.columns(5)

    with col6:
        st.checkbox(
            "QUERETARO",
            value=st.session_state.selected_sucursal == "QUERETARO",
            on_change=set_sucursal,
            args=("QUERETARO",),
            key="chk_queretaro"
        )

    with col7:
        st.checkbox(
            "LEON",
            value=st.session_state.selected_sucursal == "LEON",
            on_change=set_sucursal,
            args=("LEON",),
            key="chk_leon"
        )

    with col8:
        st.checkbox(
            "TLAXCALA",
            value=st.session_state.selected_sucursal == "TLAXCALA",
            on_change=set_sucursal,
            args=("TLAXCALA",),
            key="chk_tlaxcala"
        )

    with col9:
        st.checkbox(
            "OTRO",
            value=st.session_state.selected_sucursal == "OTRO",
            on_change=set_sucursal,
            args=("OTRO",),
            key="chk_otro"
        )

    with col10:
        suc_otro_texto = st.text_input(
            "Especificar",
            disabled=st.session_state.selected_sucursal != "OTRO",
            key="sucursal_otro_text"
        )

    # =========================================
    # SUCURSAL FINAL
    # =========================================
    if st.session_state.selected_sucursal == "OTRO":
        sucursales = [suc_otro_texto] if suc_otro_texto else []
    else:
        sucursales = (
            [st.session_state.selected_sucursal]
            if st.session_state.selected_sucursal
            else []
        )

    # =========================================
    # MAIN FORM
    # =========================================
    with st.form("form_solicitud_viaticos"):

        # =========================
        # DATOS GENERALES
        # =========================
        col1, col2 = st.columns([1, 2])

        with col1:
            fecha_solicitud = st.date_input("Fecha de Solicitud")

        with col2:
            empresa_servicio = st.text_input(
                "Nombre de la Empresa que Brinda el Servicio"
            )

        empleado = st.text_input(
            "Nombre del Empleado que lo Solicita"
        )

        motivo_viaje = st.text_area(
            "Motivo del Viaje",
            height=90
        )

        col1, col2 = st.columns(2)

        with col1:
            lugar_viaje = st.text_input(
                "Lugar a Donde se Realiza el Viaje"
            )

        with col2:
            periodo_viaje = st.text_input(
                "Periodo del Viaje"
            )

        st.divider()

        # =========================
        # EMPRESA A CARGO
        # =========================
        st.markdown("### Empresa a Cargo para Gastos de este Viaje")

        empresas = st.multiselect(
            "",
            [
                "SET FREIGHT",
                "LINCOLN",
                "PICUS",
                "IGLOO",
                "SET LOGIS PLUS"
            ]
        )

        # =========================
        # UNIDAD DE NEGOCIO
        # =========================
        st.markdown("### Unidad de Negocio")

        unidades = st.multiselect(
            "",
            [
                "CARRIER",
                "LOGISTICA",
                "PLUS"
            ]
        )

        st.divider()

        # =========================
        # ESTIMACION DE GASTOS
        # =========================
        st.markdown("## Estimación de Gastos de Viaje a Incurrir")

        col1, col2 = st.columns(2)

        with col1:

            transporte = st.number_input(
                "Transportación Terrestre",
                min_value=0.0,
                step=100.0
            )

            hospedaje = st.number_input(
                "Hospedaje",
                min_value=0.0,
                step=100.0
            )

            alimentos = st.number_input(
                "Alimentos",
                min_value=0.0,
                step=100.0
            )

            propinas = st.number_input(
                "Propinas",
                min_value=0.0,
                step=100.0
            )

            taxis = st.number_input(
                "Taxis",
                min_value=0.0,
                step=100.0
            )

            otros = st.number_input(
                "Otros",
                min_value=0.0,
                step=100.0
            )

        total_estimado = (
            transporte
            + hospedaje
            + alimentos
            + propinas
            + taxis
            + otros
        )

        with col2:

            st.metric(
                "Total Estimado",
                f"${total_estimado:,.2f}"
            )

            anticipo = st.number_input(
                "(-) Anticipo para Gastos de Viaje Entregado",
                min_value=0.0,
                step=100.0
            )

            diferencia = total_estimado - anticipo

            st.metric(
                "Diferencia a Cargo (Favor)",
                f"${diferencia:,.2f}"
            )

        st.divider()

        # =========================
        # OBSERVACIONES
        # =========================
        observaciones = st.text_area(
            "Observaciones",
            height=150
        )

        st.divider()

        submitted = st.form_submit_button(
            "💳 Enviar Solicitud",
            use_container_width=True
        )

        if submitted:
            st.success("Solicitud enviada correctamente.")

# =================================
# TAB 2 — COMPROBACION
# =================================
with tab_comprobacion:

    st.subheader("🧾 Comprobación de Gastos de Viaje")

    with st.form("form_comprobacion_viaticos"):

        col1, col2 = st.columns(2)

        with col1:
            folio = st.text_input("Folio")
            empleado_comp = st.text_input("Empleado")
            fecha_comprobacion = st.date_input(
                "Fecha de Comprobación",
                value=date.today()
            )

        with col2:
            total_comprobado = st.number_input(
                "Total Comprobado",
                min_value=0.0,
                step=100.0
            )

            observaciones = st.text_area("Observaciones")

        submitted_comprobacion = st.form_submit_button(
            "🧾 Guardar Comprobación",
            use_container_width=True
        )

        if submitted_comprobacion:
            st.success("Comprobación guardada correctamente.")

# =================================
# SUPABASE CONFIGURATION
# =================================
@st.cache_resource
def get_supabase():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_SERVICE_KEY"]
    )

supabase = get_supabase()

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
        TABS
        ========================= */

        /* Container holding tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0;
            width: 100%;
        }

        /* Each tab */
        .stTabs [data-baseweb="tab"] {
            flex: 1;
            justify-content: center;

            height: 70px;
            font-size: 1.05rem;
            font-weight: 700;

            background-color: #1B267A;
            color: #FFFFFF;

            border-radius: 14px 14px 0 0;
            border: 1px solid rgba(191, 167, 95, 0.25);

            margin-right: 4px;
        }

        /* Selected tab */
        .stTabs [aria-selected="true"] {
            background-color: #24338C;
            color: #BFA75F;
            border-color: #BFA75F;
        }

        /* Hover */
        .stTabs [data-baseweb="tab"]:hover {
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