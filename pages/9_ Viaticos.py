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
# FORM VERSION
# =================================

if "solicitud_form_version" not in st.session_state:
    st.session_state.solicitud_form_version = 0

FORM_VERSION = st.session_state.solicitud_form_version

# =================================
# GLOBAL USER DATA
# =================================

user = st.session_state.user

nombre_usuario = (
    user.get("name")
    or user.get("email")
    or ""
)

# =================================
# FORM RESET
# =================================

if "reset_form_viaticos" not in st.session_state:
    st.session_state.reset_form_viaticos = 0

# =================================
# Top navigation
# =================================
if st.button("⬅ Volver al Dashboard"):
    st.switch_page("pages/dashboard.py")

st.divider()

# =================================
# HEADER
# =================================

st.title("💳  Solicitud de Viáticos y Reembolsos")

# =================================
# TABS
# =================================
tab_solicitud, tab_comprobacion = st.tabs(
[
    "🧳 SOLICITUD GASTOS DE VIAJE",
    "🧾 COMPROBACION GASTOS DE VIAJE"
])

# =================================
# FORM VERSION
# =================================

if "solicitud_form_version" not in st.session_state:
    st.session_state.solicitud_form_version = 0

FORM_VERSION = st.session_state.solicitud_form_version

# =================================
# TAB 1 — SOLICITUD
# =================================
with tab_solicitud:

    st.subheader("🧳 Solicitud de Fondo para Gastos de Viaje")

    # =================================
    # INFORMACION GENERAL
    # =================================

    with st.container(border=True):

        st.markdown("## 📋 Informacion General")

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
                index=0,
                key=f"empresa_servicio_{FORM_VERSION}"
            )

        with col2:

            empleado = st.text_input(
                "Nombre del Empleado que Solicita",
                value=nombre_usuario,
                disabled=True,
                key=f"empleado_{FORM_VERSION}"
            )

        motivo_viaje = st.text_area(
            "Motivo del Viaje",
            height=100,
            key=f"motivo_viaje_{FORM_VERSION}"
        )

        col1, col2, col3 = st.columns(3)

        with col1:

            fecha_solicitud = st.date_input(
                "Fecha de Solicitud",
                value=date.today(),
                disabled=True,
                key=f"fecha_solicitud_{FORM_VERSION}"
            )

        with col2:

            fecha_inicio = st.date_input(
                "Fecha de Inicio",
                value=date.today(),
                key=f"fecha_inicio_{FORM_VERSION}"
            )

        with col3:

            fecha_fin = st.date_input(
                "Fecha de Fin",
                value=date.today() + pd.Timedelta(days=1),
                key=f"fecha_fin_{FORM_VERSION}"
            )

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
                index=0,
                key=f"empresa_cargo_{FORM_VERSION}"
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
                index=0,
                key=f"unidad_negocio_{FORM_VERSION}"
            )

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
            label_visibility="collapsed",
            key=f"sucursal_{FORM_VERSION}"
        )

        if sucursal == "OTRO":

            suc_otro_texto = st.text_input(
                "Especificar",
                key=f"suc_otro_texto_{FORM_VERSION}"
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
                disabled=True,
                key=f"suc_otro_disabled_{FORM_VERSION}"
            )

            sucursales_final = [sucursal]

    st.divider()

    col_poliza1, col_poliza2 = st.columns(2)

    with col_poliza1:

        ref_poliza = st.text_input(
            "REF DE POLIZA CONTABLE",
            key=f"ref_poliza_{FORM_VERSION}"
        )

    with col_poliza2:

        ref_entrega_fondo = st.text_input(
            "REF DE ENTREGA DEL FONDO PARA GASTOS DE ESTE VIAJE",
            key=f"ref_entrega_fondo_{FORM_VERSION}"
        )

    st.divider()

    with st.container(border=True):

        st.markdown("## 💰 Estimacion de Gastos de Viaje a Incurrir")

        conceptos_key = f"conceptos_gastos_{FORM_VERSION}"

        if conceptos_key not in st.session_state:
            st.session_state[conceptos_key] = []

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
                key=f"tipo_gasto_{FORM_VERSION}"
            )

        with col2:

            descripcion_otros = st.text_input(
                "Describir",
                key=f"descripcion_otros_{FORM_VERSION}"
            )

        with col3:

            monto_estimado = st.number_input(
                "Monto Estimado",
                min_value=0.0,
                step=100.0,
                key=f"monto_estimado_{FORM_VERSION}"
            )

        if st.button(
            "➕ Agregar Concepto",
            use_container_width=True,
            key=f"btn_agregar_concepto_{FORM_VERSION}"
        ):

            descripcion_final = descripcion_otros

            if tipo_gasto != "Selecciona un tipo" and monto_estimado > 0:

                st.session_state[conceptos_key].append({
                    "Tipo": tipo_gasto,
                    "Descripcion": descripcion_final,
                    "Monto": monto_estimado
                })

        st.markdown("<br>", unsafe_allow_html=True)

        if st.session_state[conceptos_key]:

            df_conceptos = pd.DataFrame(
                st.session_state[conceptos_key]
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

            total_estimado = df_conceptos["Monto"].sum()

        else:

            st.info("No hay conceptos agregados.")
            total_estimado = 0

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

        observaciones = st.text_area(
            "Observaciones",
            height=150,
            key=f"observaciones_{FORM_VERSION}"
        )

    st.divider()

    submitted = st.button(
        "💳 Enviar Solicitud",
        use_container_width=True,
        type="primary",
        key=f"submit_solicitud_{FORM_VERSION}"
    )

    if submitted:

        prefijos_sucursal = {
            "NUEVO LAREDO": "NL",
            "DALLAS": "DL",
            "CHICAGO": "CH",
            "GUADALAJARA": "GD",
            "MONTERREY": "MT",
            "QUERETARO": "QT",
            "LEON": "LN",
            "TLAXCALA": "TL",
            "OTRO": "OT"
        }

        prefijo = prefijos_sucursal.get(
            sucursal,
            "OT"
        )

        # =================================
        # GENERAR FOLIO
        # =================================

        existing = (
            supabase
            .table("solicitud_viaje")
            .select("id")
            .execute()
        )

        consecutivo = len(existing.data) + 1

        folio_solicitud = (
            f"{prefijo}-{consecutivo:06d}"
        )

        # =================================
        # SUCURSAL FINAL
        # =================================

        sucursal_especificar = ""

        if sucursal == "OTRO":
            sucursal_especificar = suc_otro_texto

        # =================================
        # GUARDAR EN SUPABASE
        # =================================

        supabase.table("solicitud_viaje").insert({

            "folio_solicitud": folio_solicitud,

            "empresa_brinda_servicio": empresa_servicio,

            "nombre_empleado_solicita": empleado,

            "motivo_viaje": motivo_viaje,

            "fecha_solicitud": str(fecha_solicitud),

            "fecha_inicio": str(fecha_inicio),

            "fecha_fin": str(fecha_fin),

            "empresa_cargo_gastos": empresa_cargo,

            "unidad_negocio": unidad_negocio,

            "sucursal": sucursal,

            "sucursal_especificar": sucursal_especificar,

            "ref_poliza_contable": ref_poliza,

            "ref_entrega_fondo": ref_entrega_fondo,

            "conceptos": st.session_state[conceptos_key],

            "total_estimado": float(total_estimado),

            "observaciones": observaciones

        }).execute()

        @st.dialog("✅ Solicitud Enviada")
        def mostrar_confirmacion():

            st.success(
                "Solicitud enviada correctamente."
            )

            st.markdown("### 📄 FOLIO DE SOLICITUD")

            st.code(
                folio_solicitud,
                language=None
            )

            if st.button(
                "Cerrar",
                use_container_width=True,
                key=f"cerrar_popup_{FORM_VERSION}"
            ):

                st.session_state.solicitud_form_version += 1
                st.rerun()

        mostrar_confirmacion()

# =================================
# TAB 2 — COMPROBACION
# =================================
with tab_comprobacion:

    st.subheader("🧾 Comprobacion de Gastos de Viaje")

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

            empresa_comp = st.selectbox(
                "Nombre de la Compañia",
                [
                    "Seleccione una opción...",
                    "SET FREIGHT",
                    "LINCOLN",
                    "PICUS",
                    "IGLOO",
                    "SET LOGIS PLUS"
                ],
                index=0,
                key="empresa_comp"
            )

        with col2:

            empleado_comp = st.text_input(
                "Nombre del Empleado que Solicita",
                value=nombre_usuario,
                disabled=True,
                key="empleado_comp"
            )

        # =========================
        # ROW 2
        # =========================

        motivo_comp = st.text_area(
            "Motivo del Viaje",
            height=100,
            key="motivo_comp"
        )

        # =========================
        # ROW 3
        # =========================

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

        # =========================
        # ROW 4
        # =========================

        col1, col2, col3 = st.columns(3)

        with col1:

            fecha_comprobacion = st.date_input(
                "Fecha de Solicitud",
                value=date.today(),
                key="fecha_comprobacion"
            )

        with col2:

            fecha_inicio_comp = st.date_input(
                "Fecha de Inicio",
                value=date.today(),
                key="fecha_inicio_comp"
            )

        with col3:

            fecha_fin_comp = st.date_input(
                "Fecha de Fin",
                value=date.today() + pd.Timedelta(days=1),
                key="fecha_fin_comp"
            )

        # =========================
        # ROW 5
        # =========================

        col1, col2 = st.columns(2)

        with col1:

            empresa_cargo_comp = st.selectbox(
                "Empresa a Cargo para Gastos de este Viaje",
                [
                    "Seleccione una opción...",
                    "SET FREIGHT",
                    "LINCOLN",
                    "PICUS",
                    "IGLOO",
                    "SET LOGIS PLUS"
                ],
                index=0,
                key="empresa_cargo_comp"
            )

        with col2:

            unidad_negocio_comp = st.selectbox(
                "Unidad de Negocio",
                [
                    "Seleccione una opción...",
                    "CARRIER",
                    "LOGISTICA",
                    "PLUS"
                ],
                index=0,
                key="unidad_negocio_comp"
            )

        # =========================
        # ROW 6
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
    # IMPORTE DE GASTOS
    # =========================

    with st.container(border=True):

        st.markdown("## 💰 IMPORTE DE GASTOS")

        gastos_comp_key = "gastos_comprobacion"

        if gastos_comp_key not in st.session_state:
            st.session_state[gastos_comp_key] = []

            # =========================
            # INPUTS
            # =========================

            col1, col2, col3 = st.columns(3)

            with col1:

                tipo_gasto_comp = st.selectbox(
                    "Tipo",
                    [
                        "Selecciona un tipo",
                        "TRANSPORTACION TERRESTRE",
                        "HOSPEDAJE",
                        "ALIMENTOS",
                        "PROPINAS",
                        "TAXIS",
                        "CASETAS",
                        "GASOLINA"
                    ],
                    key="tipo_gasto_comp"
                )

            with col2:

                monto_gasto = st.number_input(
                    "Monto",
                    min_value=0.0,
                    step=100.0,
                    key="monto_gasto"
                )

            with col3:

                tiene_comprobante = st.checkbox(
                    "Tiene Comprobante",
                    key="tiene_comprobante"
                )

            st.markdown("<br>", unsafe_allow_html=True)

            col4, col5 = st.columns(2)

            with col4:

                aplica_iva = st.checkbox(
                    "Aplica IVA",
                    key="aplica_iva"
                )

                iva_porcentaje = st.selectbox(
                    "IVA %",
                    [
                        8,
                        12,
                        16
                    ],
                    disabled=not aplica_iva,
                    key="iva_porcentaje"
                )

            with col5:

                aplica_retencion = st.checkbox(
                    "Aplica Retención ISR",
                    key="aplica_retencion"
                )

            # =========================
            # ADD BUTTON
            # =========================

            if st.button(
                "➕ Agregar Concepto",
                use_container_width=True,
                key="btn_agregar_comp"
            ):

                if (
                    tipo_gasto_comp != "Selecciona un tipo"
                    and monto_gasto > 0
                ):

                    # =========================
                    # COMPROBANTE SPLIT
                    # =========================

                    gastos_con_comp = 0
                    gastos_sin_comp = 0

                    if tiene_comprobante:
                        gastos_con_comp = monto_gasto
                    else:
                        gastos_sin_comp = monto_gasto

                    # =========================
                    # IVA
                    # =========================

                    impuesto_acreditable = 0

                    if tiene_comprobante and aplica_iva:

                        impuesto_acreditable = (
                            monto_gasto *
                            (iva_porcentaje / 100)
                        )

                    # =========================
                    # RETENCION ISR
                    # =========================

                    if (
                        tiene_comprobante
                        and aplica_retencion
                    ):

                        retencion_isr = (
                            monto_gasto * 0.0125
                        )

                        impuesto_acreditable -= (
                            retencion_isr
                        )

                    # =========================
                    # TOTAL
                    # =========================

                    total_comprobado = (
                        monto_gasto +
                        impuesto_acreditable
                    )

                    # =========================
                    # SAVE ROW
                    # =========================

                    st.session_state[gastos_comp_key].append({

                        "Tipo":
                            tipo_gasto_comp,

                        "Gastos con Comprobante":
                            gastos_con_comp,

                        "Gastos sin Comprobante":
                            gastos_sin_comp,

                        "IVA %":
                            (
                                iva_porcentaje
                                if aplica_iva
                                else 0
                            ),

                        "Retención ISR":
                            (
                                "Sí"
                                if aplica_retencion
                                else "No"
                            ),

                        "Impuesto Acreditable":
                            impuesto_acreditable,

                        "Total Comprobado":
                            total_comprobado
                    })

        # =========================
        # TABLE
        # =========================

        if st.session_state[gastos_comp_key]:

            df_gastos = pd.DataFrame(
                st.session_state[gastos_comp_key]
            )

            df_display = df_gastos.copy()

            money_cols = [
                "Gastos con Comprobante",
                "Gastos sin Comprobante",
                "Impuesto Acreditable",
                "Total Comprobado"
            ]

            for col in money_cols:

                df_display[col] = df_display[col].apply(
                    lambda x: f"$ {x:,.2f}"
                )

            st.dataframe(
                df_display,
                use_container_width=True,
                hide_index=True
            )

            total_general = (
                df_gastos["Total Comprobado"]
                .sum()
            )

        else:

            st.info("No hay conceptos agregados.")
            total_general = 0

        st.markdown("<br>", unsafe_allow_html=True)

        # =========================
        # TOTAL ROW
        # =========================

        col1, col2, col3 = st.columns(3)

        with col2:

            anticipo_viaje = st.number_input(
                "(-) Anticipo para gastos de viaje",
                min_value=0.0,
                step=100.0,
                key="anticipo_viaje"
            )

        diferencia_cargo = (
            anticipo_viaje - total_general
        )

        with col1:

            st.text_input(
                "TOTAL COMPROBADO",
                value=f"$ {total_general:,.2f}",
                disabled=True,
                key=f"total_comprobado_{total_general}"
            )

        with col3:

            st.text_input(
                "DIFERENCIA A CARGO (FAVOR)",
                value=f"$ {diferencia_cargo:,.2f}",
                disabled=True,
                key=f"diferencia_cargo_{diferencia_cargo}"
            )

        st.markdown("<br>", unsafe_allow_html=True)

        # =========================
        # OBSERVACIONES
        # =========================

        observaciones_comp = st.text_area(
            "Observaciones",
            height=150,
            key="observaciones_comp"
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