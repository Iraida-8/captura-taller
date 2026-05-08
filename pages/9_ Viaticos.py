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
# SUPABASE CONFIGURATION
# =================================
@st.cache_resource
def get_supabase():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_SERVICE_KEY"]
    )

supabase = get_supabase()

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

    # =================================
    # USER DATA
    # =================================

    user = st.session_state.user

    nombre_usuario = (
        user.get("name")
        or user.get("email")
        or ""
    )

    # =================================
    # INFORMACION GENERAL
    # =================================

    with st.container(border=True):

        st.markdown("## 📋 Informacion General")

        # =========================
        # ROW 1
        # =========================

        col1, col2 = st.columns(2)

        with col1:

            empresa_servicio = st.selectbox(
                "Empresa que Brinda el Servicio",
                [
                    "Seleccione una opción...",
                    "SET FREIGHT",
                    "LINCOLN",
                    "PICUS",
                    "IGLOO",
                    "SET LOGIS PLUS"
                ],
                index=0
            )

        with col2:

            empleado = st.text_input(
                "Nombre del Empleado que Solicita",
                value=nombre_usuario,
                disabled=True
            )

        # =========================
        # ROW 2
        # =========================

        motivo_viaje = st.text_area(
            "Motivo del Viaje",
            height=100
        )

        # =========================
        # ROW 3
        # =========================

        col1, col2 = st.columns(2)

        with col1:

            fecha_solicitud = st.date_input(
                "Fecha de Solicitud",
                value=date.today(),
                disabled=True
            )

        with col2:

            st.empty()

        # =========================
        # ROW 4
        # =========================

        col1, col2 = st.columns(2)

        with col1:

            fecha_inicio = st.date_input(
                "Fecha de Inicio",
                value=date.today()
            )

        with col2:

            fecha_fin = st.date_input(
                "Fecha de Fin",
                value=date.today() + pd.Timedelta(days=1)
            )

        # =========================
        # ROW 5
        # =========================

        col1, col2 = st.columns(2)

        with col1:

            empresa_cargo = st.selectbox(
                "Empresa a Cargo para Gastos de este Viaje",
                [
                    "Seleccione una opción...",
                    "SET FREIGHT",
                    "LINCOLN",
                    "PICUS",
                    "IGLOO",
                    "SET LOGIS PLUS"
                ],
                index=0
            )

        with col2:

            unidad_negocio = st.selectbox(
                "Unidad de Negocio",
                [
                    "Seleccione una opción...",
                    "CARRIER",
                    "LOGISTICA",
                    "PLUS"
                ],
                index=0
            )

        # =========================
        # ROW 6
        # =========================

        st.markdown("### Sucursal")

        sucursal = st.radio(
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
            label_visibility="collapsed"
        )

        if sucursal == "OTRO":

            suc_otro_texto = st.text_input(
                "Especificar"
            )

            sucursales_final = (
                [suc_otro_texto]
                if suc_otro_texto
                else []
            )

        else:

            st.text_input(
                "Especificar",
                value="",
                disabled=True
            )

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

    # =========================
    # ESTIMACION DE GASTOS
    # =========================

    with st.container(border=True):

        st.markdown("## 💰 Estimacion de Gastos de Viaje a Incurrir")

        # =========================
        # SESSION STATE
        # =========================

        if "conceptos_gastos" not in st.session_state:
            st.session_state.conceptos_gastos = []

        # =========================
        # INPUTS
        # =========================

        col1, col2, col3 = st.columns([2, 3, 2])

        with col1:

            tipo_gasto = st.selectbox(
                "Tipo",
                [
                    "Selecciona un tipo",
                    "TRANSPORTACION TERRESTRE",
                    "HOSPEDAJE",
                    "ALIMENTOS",
                    "PROPINAS",
                    "TAXIS",
                    "OTROS"
                ],
                key="tipo_gasto"
            )

        with col2:

            descripcion_otros = st.text_input(
                "Describir (Otros)",
                disabled=tipo_gasto != "OTROS",
                key="descripcion_otros"
            )

        with col3:

            monto_estimado = st.number_input(
                "Monto Estimado",
                min_value=0.0,
                step=100.0,
                key="monto_estimado"
            )

        # =========================
        # ADD BUTTON
        # =========================

        if st.button(
            "➕ Agregar Concepto",
            use_container_width=True
        ):

            descripcion_final = ""

            if tipo_gasto == "OTROS":
                descripcion_final = descripcion_otros

            if tipo_gasto == "Selecciona un tipo":

                st.warning("Selecciona un tipo.")

            elif monto_estimado <= 0:

                st.warning("Ingresa un monto válido.")

            else:

                st.session_state.conceptos_gastos.append({
                    "Tipo": tipo_gasto,
                    "Descripcion": descripcion_final,
                    "Monto": monto_estimado
                })

                st.success("Concepto agregado correctamente.")

        st.markdown("<br>", unsafe_allow_html=True)

        # =========================
        # TABLE
        # =========================

        if st.session_state.conceptos_gastos:

            df_conceptos = pd.DataFrame(
                st.session_state.conceptos_gastos
            )

            df_display = df_conceptos.copy()

            df_display["Monto"] = df_display["Monto"].apply(
                lambda x: f"$ {x:,.2f}"
            )

            st.dataframe(
                df_display,
                use_container_width=True,
                hide_index=True
            )

            total_estimado = (
                df_conceptos["Monto"]
                .sum()
            )

        else:

            st.info(
                "No hay conceptos agregados."
            )

            total_estimado = 0

        st.markdown("<br>", unsafe_allow_html=True)

        # =========================
        # TOTAL
        # =========================

        st.markdown(
            f"""
            <div style="
                background:white;
                color:black;
                border:2px solid black;
                padding:14px;
                font-size:24px;
                font-weight:bold;
                text-align:right;
            ">
                TOTAL ESTIMADO: $ {total_estimado:,.2f}
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("<br>", unsafe_allow_html=True)

        # =========================
        # OBSERVACIONES
        # =========================

        observaciones = st.text_area(
            "Observaciones",
            height=150
        )

        st.markdown("<br>", unsafe_allow_html=True)

        # =========================
        # ANTICIPO
        # =========================

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
                background:white;
                color:black;
                border:2px solid black;
                padding:14px;
                font-size:24px;
                font-weight:bold;
                text-align:right;
                margin-top:15px;
            ">
                DIFERENCIA A CARGO (FAVOR): $ {diferencia:,.2f}
            </div>
            """,
            unsafe_allow_html=True
        )

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

    st.subheader("🧾 Comprobacion de Gastos de Viaje")

    # =========================
    # DATOS GENERALES
    # =========================

    col1, col2 = st.columns([1, 2])

    with col1:
        fecha_comprobacion = st.date_input(
            "Fecha de Comprobacion",
            key="fecha_comprobacion"
        )

    with col2:
        empresa_comp = st.text_input(
            "Nombre de la Compañia",
            key="empresa_comp"
        )

    empleado_comp = st.text_input(
        "Nombre del Empleado",
        key="empleado_comp"
    )

    motivo_comp = st.text_area(
        "Motivo del Viaje",
        height=90,
        key="motivo_comp"
    )

    col1, col2 = st.columns(2)

    with col1:
        lugar_comp = st.text_input(
            "Lugar a Donde se Realiza el Viaje",
            key="lugar_comp"
        )

    with col2:
        periodo_comp = st.text_input(
            "Periodo del Viaje",
            key="periodo_comp"
        )

    st.divider()

    # =========================
    # EMPRESA A CARGO
    # =========================

    st.markdown("### Empresa a Cargo para Gastos de este Viaje")

    empresa_cargo_comp = st.selectbox(
        "Empresa a Cargo",
        [
            "Seleccione una opción...",
            "SET FREIGHT",
            "LINCOLN",
            "PICUS",
            "IGLOO",
            "SET LOGIS PLUS"
        ],
        index=0,
        key="empresa_cargo_comp",
        label_visibility="collapsed"
    )

    # =========================
    # UNIDAD DE NEGOCIO
    # =========================

    st.markdown("### Unidad de Negocio")

    unidad_negocio_comp = st.selectbox(
        "Unidad de Negocio",
        [
            "Seleccione una opción...",
            "CARRIER",
            "LOGISTICA",
            "PLUS"
        ],
        index=0,
        key="unidad_negocio_comp",
        label_visibility="collapsed"
    )

    # =========================
    # SUCURSAL
    # =========================

    st.markdown("### Sucursal")

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
            "Especificar",
            key="sucursal_otro_comp"
        )

    else:

        st.text_input(
            "Especificar",
            value="",
            disabled=True,
            key="sucursal_otro_disabled_comp"
        )

    st.divider()

    # =========================
    # DATOS CONTABLES
    # =========================

    ref_entrega_comp = st.text_input(
        "REF DE ENTREGA DEL FONDO PARA GASTOS DE ESTE VIAJE",
        key="ref_entrega_comp"
    )

    st.divider()

    # =========================
    # TABLE STYLE
    # =========================

    st.markdown(
        """
        <style>

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

    total_general += fila_comp("TRANSPORTACION TERRESTRE", "comp_trans")
    total_general += fila_comp("HOSPEDAJE", "comp_hosp")
    total_general += fila_comp("ALIMENTOS", "comp_alim")
    total_general += fila_comp("PROPINAS", "comp_prop")
    total_general += fila_comp("TAXIS", "comp_taxi")
    total_general += fila_comp("CASETAS", "comp_case")
    total_general += fila_comp("GASOLINA", "comp_gaso")

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
            key="obs_comp",
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
        type="primary",
        key="submitted_comp"
    )

    if submitted_comp:
        st.success("Comprobación guardada correctamente.")

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