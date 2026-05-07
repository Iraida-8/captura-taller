import streamlit as st
from pathlib import Path
from PIL import Image
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
# HEADER
# =================================

assets_dir = Path(__file__).parent / "assets"
logo_path = assets_dir / "pg_brand.png"

# =================================
# HEADER
# =================================

col_logo, col_title, col_spacer = st.columns([1, 6, 1])

with col_logo:

    if logo_path.exists():

        img = Image.open(logo_path)

        st.image(
            img,
            width=95
        )

with col_title:

    st.markdown(
        """
        <div style="
            text-align:center;
            border:3px solid #151F6D;
            padding:14px;
            margin-top:18px;
            background:white;
            color:#151F6D;
            font-size:38px;
            font-weight:bold;
            letter-spacing:1px;
        ">
            SOLICITUD DE VIATICOS Y REEMBOLSOS
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown("<br>", unsafe_allow_html=True)

# =================================
# TABS
# =================================
tab_solicitud, tab_comprobacion = st.tabs([
    "🧳 SOLICITUD GASTOS DE VIAJE",
    "🧾 COMPROBACION GASTOS DE VIAJE"
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

    st.markdown(
        """
        <style>

        .table-header {
            background: white;
            color: black;
            border: 2px solid black;
            padding: 14px;
            font-size: 24px;
            font-weight: bold;
        }

        .table-cell {
            background: white;
            color: black;
            border-left: 2px solid black;
            border-right: 2px solid black;
            border-bottom: 1px dotted black;
            padding: 12px;
            font-size: 18px;
            min-height: 58px;
            display: flex;
            align-items: center;
        }

        .table-total {
            background: white;
            color: black;
            border: 2px solid black;
            padding: 14px;
            font-size: 20px;
            font-weight: bold;
            min-height: 58px;
            display: flex;
            align-items: center;
        }

        .obs-header {
            background: #9f9f9f;
            color: black;
            border: 2px solid black;
            text-align: center;
            letter-spacing: 8px;
            font-size: 24px;
            font-weight: bold;
            padding: 12px;
            margin-bottom: 0px;
        }

        div[data-testid="stNumberInput"] input {
            text-align: left;
            font-size: 18px;
        }

        </style>
        """,
        unsafe_allow_html=True
    )

    # =========================
    # HEADER
    # =========================

    col_h1, col_h2 = st.columns([7, 3], gap="small")

    with col_h1:
        st.markdown(
            '<div class="table-header">ESTIMACION DE GASTOS DE VIAJE A INCURRIR</div>',
            unsafe_allow_html=True
        )

    with col_h2:
        st.markdown(
            '<div class="table-header" style="text-align:center; justify-content:center; display:flex;">TOTAL ESTIMADO</div>',
            unsafe_allow_html=True
        )

    # =========================
    # ROW BUILDER
    # =========================

    def fila_gasto(nombre, key):

        c1, c2 = st.columns([7, 3], gap="small")

        with c1:
            st.markdown(
                f'<div class="table-cell">{nombre}</div>',
                unsafe_allow_html=True
            )

        with c2:
            valor = st.number_input(
                label=nombre,
                min_value=0.0,
                step=100.0,
                key=key,
                label_visibility="collapsed"
            )

        return valor

    # =========================
    # INPUT ROWS
    # =========================

    transporte = fila_gasto(
        "TRANSPORTACION TERRESTRE",
        "transporte"
    )

    hospedaje = fila_gasto(
        "HOSPEDAJE",
        "hospedaje"
    )

    alimentos = fila_gasto(
        "ALIMENTOS",
        "alimentos"
    )

    propinas = fila_gasto(
        "PROPINAS",
        "propinas"
    )

    taxis = fila_gasto(
        "TAXIS",
        "taxis"
    )

    otros = fila_gasto(
        "OTROS (Describir)",
        "otros"
    )

    # =========================
    # TOTALS
    # =========================

    total_estimado = (
        transporte
        + hospedaje
        + alimentos
        + propinas
        + taxis
        + otros
    )

    c_total1, c_total2 = st.columns([7, 3], gap="small")

    with c_total1:
        st.markdown(
            '<div class="table-total" style="justify-content:flex-end;">Importe estimado de gastos de viaje</div>',
            unsafe_allow_html=True
        )

    with c_total2:
        st.markdown(
            f'<div class="table-total">$ {total_estimado:,.2f}</div>',
            unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # =========================
    # LOWER SECTION
    # =========================

    col_obs, col_tot = st.columns([1.2, 1])

    with col_obs:

        st.markdown(
            '<div class="obs-header">OBSERVACIONES</div>',
            unsafe_allow_html=True
        )

        observaciones = st.text_area(
            "",
            height=170,
            label_visibility="collapsed"
        )

    with col_tot:

        anticipo = st.number_input(
            "(-) Anticipo para gastos de viaje entregado",
            min_value=0.0,
            step=100.0,
            key="anticipo"
        )

        diferencia = total_estimado - anticipo

        st.markdown(
            f"""
            <div style="
                color:white;
                font-size:24px;
                font-weight:bold;
                margin-top:40px;
                margin-bottom:15px;
            ">
                Diferencia a cargo (favor)
            </div>

            <div style="
                background:white;
                color:black;
                border:2px solid black;
                padding:12px;
                font-size:24px;
                font-weight:bold;
            ">
                $ {diferencia:,.2f}
            </div>
            """,
            unsafe_allow_html=True
        )

    st.divider()

    submitted = st.button(
        "💳 Enviar Solicitud",
        use_container_width=True,
        type="primary"
    )

    if submitted:
        st.success(
            f"Solicitud para {sucursales_final} enviada correctamente."
        )

# =================================
# TAB 2 — COMPROBACION
# =================================
with tab_comprobacion:

    st.markdown(
        """
        <style>

        .comp-header {
            background:white;
            color:#151F6D;
            border:3px solid #151F6D;
            padding:12px;
            text-align:center;
            font-size:34px;
            font-weight:bold;
            margin-bottom:40px;
        }

        .comp-label {
            color:white;
            font-size:18px;
            font-weight:bold;
            margin-top:14px;
        }

        .comp-table-header {
            background:white;
            color:black;
            border:2px solid black;
            padding:10px;
            font-size:18px;
            font-weight:bold;
            text-align:center;
        }

        .comp-table-cell {
            background:white;
            color:black;
            border-left:2px solid black;
            border-right:2px solid black;
            border-bottom:1px dotted black;
            padding:10px;
            min-height:55px;
            display:flex;
            align-items:center;
            font-size:17px;
            font-weight:bold;
        }

        .comp-total-box {
            background:white;
            color:black;
            border:2px solid black;
            padding:12px;
            font-size:22px;
            font-weight:bold;
            min-height:58px;
            display:flex;
            align-items:center;
        }

        .obs-header {
            background:#9f9f9f;
            color:black;
            border:2px solid black;
            text-align:center;
            letter-spacing:8px;
            font-size:24px;
            font-weight:bold;
            padding:12px;
            margin-bottom:0px;
        }

        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="comp-header">COMPROBACION DE GASTOS DE VIAJE</div>',
        unsafe_allow_html=True
    )

    # =========================
    # DATOS GENERALES
    # =========================

    c1, c2 = st.columns([1, 2])

    with c1:
        st.markdown(
            '<div class="comp-label">FECHA DE COMPROBACION</div>',
            unsafe_allow_html=True
        )

    with c2:
        fecha_comprobacion = st.date_input(
            "",
            value=date.today(),
            label_visibility="collapsed"
        )

    c1, c2 = st.columns([1, 2])

    with c1:
        st.markdown(
            '<div class="comp-label">NOMBRE DE LA COMPAÑIA</div>',
            unsafe_allow_html=True
        )

    with c2:
        empresa_comp = st.text_input(
            "",
            key="empresa_comp",
            label_visibility="collapsed"
        )

    c1, c2 = st.columns([1, 2])

    with c1:
        st.markdown(
            '<div class="comp-label">NOMBRE DEL EMPLEADO</div>',
            unsafe_allow_html=True
        )

    with c2:
        empleado_comp = st.text_input(
            "",
            key="empleado_comp",
            label_visibility="collapsed"
        )

    c1, c2 = st.columns([1, 2])

    with c1:
        st.markdown(
            '<div class="comp-label">MOTIVO DEL VIAJE</div>',
            unsafe_allow_html=True
        )

    with c2:
        motivo_comp = st.text_input(
            "",
            key="motivo_comp",
            label_visibility="collapsed"
        )

    c1, c2 = st.columns([1, 2])

    with c1:
        st.markdown(
            '<div class="comp-label">LUGAR A DONDE SE REALIZA EL VIAJE</div>',
            unsafe_allow_html=True
        )

    with c2:
        lugar_comp = st.text_input(
            "",
            key="lugar_comp",
            label_visibility="collapsed"
        )

    c1, c2 = st.columns([1, 2])

    with c1:
        st.markdown(
            '<div class="comp-label">PERIODO DEL VIAJE</div>',
            unsafe_allow_html=True
        )

    with c2:
        periodo_comp = st.text_input(
            "",
            key="periodo_comp",
            label_visibility="collapsed"
        )

    st.divider()

    # =========================
    # EMPRESA A CARGO
    # =========================

    st.markdown(
        '<div class="comp-label">EMPRESA A CARGO PARA GASTOS DE ESTE VIAJE</div>',
        unsafe_allow_html=True
    )

    empresa_cargo_comp = st.radio(
        "",
        ["SET FREIGHT", "LINCOLN", "PICUS", "IGLOO", "SET LOGIS PLUS"],
        horizontal=True,
        key="empresa_cargo_comp",
        label_visibility="collapsed"
    )

    # =========================
    # UNIDAD DE NEGOCIO
    # =========================

    st.markdown(
        '<div class="comp-label">UNIDAD DE NEGOCIO</div>',
        unsafe_allow_html=True
    )

    unidad_negocio_comp = st.radio(
        "",
        ["CARRIER", "LOGISTICA", "PLUS"],
        horizontal=True,
        key="unidad_negocio_comp",
        label_visibility="collapsed"
    )

    # =========================
    # SUCURSAL
    # =========================

    st.markdown(
        '<div class="comp-label">SUCURSAL</div>',
        unsafe_allow_html=True
    )

    sucursal_comp = st.radio(
        "",
        [
            "NUEVO LAREDO",
            "DALLAS",
            "CHICAGO",
            "GUADALAJARA",
            "MONTERREY",
            "QUERETARO",
            "LEON",
            "TLAXCALA",
            "OTRO"
        ],
        horizontal=True,
        key="sucursal_comp",
        label_visibility="collapsed"
    )

    if sucursal_comp == "OTRO":

        sucursal_otro_comp = st.text_input(
            "Especificar Sucursal",
            key="sucursal_otro_comp"
        )

    else:

        st.text_input(
            "Especificar Sucursal",
            value="",
            disabled=True,
            key="sucursal_otro_disabled_comp"
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # =========================
    # REF POLIZA
    # =========================

    ref_poliza_comp = st.text_input(
        "REF DE POLIZA CONTABLE DE ENTREGA DEL FONDO PARA GASTOS DE ESTE VIAJE",
        key="ref_poliza_comp"
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # =========================
    # TABLE HEADER
    # =========================

    h1, h2, h3, h4, h5 = st.columns([5, 2, 2, 2, 2])

    with h1:
        st.markdown(
            '<div class="comp-table-header"></div>',
            unsafe_allow_html=True
        )

    with h2:
        st.markdown(
            '<div class="comp-table-header">IMPORTE DE GASTOS CON</div>',
            unsafe_allow_html=True
        )

    with h3:
        st.markdown(
            '<div class="comp-table-header">IMPORTE DE GASTOS SIN</div>',
            unsafe_allow_html=True
        )

    with h4:
        st.markdown(
            '<div class="comp-table-header">IMPUESTO ACREDITABLE</div>',
            unsafe_allow_html=True
        )

    with h5:
        st.markdown(
            '<div class="comp-table-header">TOTAL COMPROBADO</div>',
            unsafe_allow_html=True
        )

    # =========================
    # ROW BUILDER
    # =========================

    def fila_comp(nombre, key):

        c1, c2, c3, c4, c5 = st.columns([5, 2, 2, 2, 2])

        with c1:
            st.markdown(
                f'<div class="comp-table-cell">{nombre}</div>',
                unsafe_allow_html=True
            )

        with c2:
            con_iva = st.number_input(
                "",
                min_value=0.0,
                step=100.0,
                key=f"{key}_con",
                label_visibility="collapsed"
            )

        with c3:
            sin_iva = st.number_input(
                "",
                min_value=0.0,
                step=100.0,
                key=f"{key}_sin",
                label_visibility="collapsed"
            )

        with c4:
            impuesto = st.number_input(
                "",
                min_value=0.0,
                step=100.0,
                key=f"{key}_imp",
                label_visibility="collapsed"
            )

        total = con_iva + sin_iva + impuesto

        with c5:
            st.markdown(
                f'<div class="comp-total-box">$ {total:,.2f}</div>',
                unsafe_allow_html=True
            )

        return total

    total_general = 0

    total_general += fila_comp("TRANSPORTACION TERRESTRE", "trans")
    total_general += fila_comp("HOSPEDAJE", "hosp")
    total_general += fila_comp("ALIMENTOS", "alim")
    total_general += fila_comp("PROPINAS", "prop")
    total_general += fila_comp("TAXIS", "taxi")
    total_general += fila_comp("CASETAS", "case")
    total_general += fila_comp("GASOLINA", "gaso")

    st.markdown("<br>", unsafe_allow_html=True)

    # =========================
    # LOWER SECTION
    # =========================

    col_obs, col_tot = st.columns([1.5, 1])

    with col_obs:

        st.markdown(
            '<div class="obs-header">OBSERVACIONES</div>',
            unsafe_allow_html=True
        )

        obs_comp = st.text_area(
            "",
            height=160,
            label_visibility="collapsed"
        )

    with col_tot:

        st.markdown(
            """
            <div style="
                color:white;
                font-size:22px;
                font-weight:bold;
                margin-bottom:12px;
            ">
                (-) Anticipo para gastos de viaje
            </div>
            """,
            unsafe_allow_html=True
        )

        anticipo_comp = st.number_input(
            "",
            min_value=0.0,
            step=100.0,
            key="anticipo_comp",
            label_visibility="collapsed"
        )

        diferencia_comp = total_general - anticipo_comp

        st.markdown(
            f'''
            <div style="
                color:white;
                font-size:24px;
                font-weight:bold;
                margin-top:40px;
                margin-bottom:15px;
            ">
                Diferencia a cargo (favor)
            </div>

            <div class="comp-total-box">
                $ {diferencia_comp:,.2f}
            </div>
            ''',
            unsafe_allow_html=True
        )

    st.markdown("<br><br>", unsafe_allow_html=True)

    submitted_comp = st.button(
        "🧾 Guardar Comprobación",
        use_container_width=True,
        type="primary"
    )

    if submitted_comp:
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