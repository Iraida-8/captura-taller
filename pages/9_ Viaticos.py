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

    # =========================
    # PART 1: DATOS GENERALES
    # =========================
    # Using a container instead of a form here so the radio button can trigger the UI update
    col1, col2 = st.columns([1, 2])

    with col1:
        fecha_solicitud = st.date_input("Fecha de Solicitud")

    with col2:
        empresa_servicio = st.text_input("Nombre de la Empresa que Brinda el Servicio")

    empleado = st.text_input("Nombre del Empleado que lo Solicita")

    motivo_viaje = st.text_area("Motivo del Viaje", height=90)

    col1, col2 = st.columns(2)
    with col1:
        lugar_viaje = st.text_input("Lugar a Donde se Realiza el Viaje")
    with col2:
        periodo_viaje = st.text_input("Periodo del Viaje")

    st.divider()

    # EMPRESA A CARGO
    st.markdown("### Empresa a Cargo para Gastos de este Viaje")
    empresa_cargo = st.selectbox(
        "Empresa a Cargo", 
        ["Seleccione una opción...", "SET FREIGHT", "LINCOLN", "PICUS", "IGLOO", "SET LOGIS PLUS"],
        index=0,
        label_visibility="collapsed"
    )

    # UNIDAD DE NEGOCIO
    st.markdown("### Unidad de Negocio")
    unidad_negocio = st.selectbox(
        "Unidad de Negocio", 
        ["Seleccione una opción...", "CARRIER", "LOGISTICA", "PLUS"],
        index=0,
        label_visibility="collapsed"
    )

    # =========================
    # SUCURSAL (REACTIVE SECTION)
    # =========================
    st.markdown("### Sucursal")
    sucursal = st.radio(
        "",
        ["NUEVO LAREDO", "DALLAS", "CHICAGO", "GUADALAJARA", "MONTERREY", "QUERETARO", "LEON", "TLAXCALA", "OTRO"],
        horizontal=True,
        label_visibility="collapsed"
    )

    if sucursal == "OTRO":
        suc_otro_texto = st.text_input("Especificar")
        sucursales_final = [suc_otro_texto] if suc_otro_texto else []
    else:
        st.text_input("Especificar", value="", disabled=True)
        sucursales_final = [sucursal]

    st.divider()

    # =========================
    # DATOS CONTABLES
    # =========================
    col_poliza1, col_poliza2 = st.columns(2)

    with col_poliza1:
        ref_poliza = st.text_input(
            "REF DE POLIZA CONTABLE"
        )

    with col_poliza2:
        ref_entrega_fondo = st.text_input(
            "REF DE ENTREGA DEL FONDO PARA GASTOS DE ESTE VIAJE"
        )

    st.divider()

    # =========================
    # PART 2: THE FORM
    # =========================
    with st.form("form_solicitud_gastos"):
        st.markdown("## Estimación de Gastos de Viaje a Incurrir")

        col_g1, col_g2 = st.columns(2)

        with col_g1:
            transporte = st.number_input("Transportación Terrestre", min_value=0.0, step=100.0)
            hospedaje = st.number_input("Hospedaje", min_value=0.0, step=100.0)
            alimentos = st.number_input("Alimentos", min_value=0.0, step=100.0)
            propinas = st.number_input("Propinas", min_value=0.0, step=100.0)
            taxis = st.number_input("Taxis", min_value=0.0, step=100.0)
            otros = st.number_input("Otros", min_value=0.0, step=100.0)

        total_estimado = transporte + hospedaje + alimentos + propinas + taxis + otros

        with col_g2:
            st.metric("Total Estimado", f"${total_estimado:,.2f}")
            anticipo = st.number_input("(-) Anticipo para Gastos de Viaje Entregado", min_value=0.0, step=100.0)
            diferencia = total_estimado - anticipo
            st.metric("Diferencia a Cargo (Favor)", f"${diferencia:,.2f}")

        st.divider()
        observaciones = st.text_area("Observaciones", height=150)
        st.divider()

        submitted = st.form_submit_button("💳 Enviar Solicitud", use_container_width=True)

        if submitted:
            # Here you would collect all variables (from outside and inside the form) and send to Supabase
            st.success(f"Solicitud para {sucursales_final} enviada correctamente.")

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
            fecha_comprobacion = st.date_input("Fecha de Comprobación", value=date.today())
        with col2:
            total_comprobado = st.number_input("Total Comprobado", min_value=0.0, step=100.0)
            obs_comp = st.text_area("Observaciones")

        submitted_comprobacion = st.form_submit_button("🧾 Guardar Comprobación", use_container_width=True)
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