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

if "comprobacion_form_version" not in st.session_state:
    st.session_state.comprobacion_form_version = 0

COMP_VERSION = st.session_state.comprobacion_form_version

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

if "comprobacion_form_version" not in st.session_state:
    st.session_state.comprobacion_form_version = 0

COMP_VERSION = st.session_state.comprobacion_form_version

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
                    "CASETAS",
                    "GASOLINA",
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

            df_display.insert(0, "Eliminar", False)

            edited_df = st.data_editor(
            df_display,
            use_container_width=True,
            hide_index=True,
            disabled=[
                "Tipo",
                "Descripcion",
                "Monto"
            ],
            column_config={
                "Eliminar": st.column_config.CheckboxColumn(
                    "Eliminar",
                    width="small"
                )
            },
            key=f"editor_solicitud_{FORM_VERSION}"
        )

            if st.button(
                "🗑️ Eliminar Filas Seleccionadas",
                use_container_width=True,
                key=f"btn_eliminar_concepto_{FORM_VERSION}"
            ):

                filas_restantes = []

                for idx, row in edited_df.iterrows():

                    if not row["Eliminar"]:

                        filas_restantes.append(
                            st.session_state[conceptos_key][idx]
                        )

                st.session_state[conceptos_key] = filas_restantes

                st.rerun()

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
            f"{prefijo}-{consecutivo:06d}-SGV"
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

            "conceptos": st.session_state[conceptos_key],

            "total_estimado": float(total_estimado),

            "observaciones": observaciones,

            "estatus": "Pendiente"

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

# =================================
# LOAD SOLICITUDES
# =================================

solicitudes_data = (
    supabase
    .table("solicitud_viaje")
    .select("*")
    .order("folio_solicitud")
    .execute()
)

solicitudes = solicitudes_data.data if solicitudes_data.data else []

# =================================
# LOAD COMPROBACIONES EXISTENTES
# =================================

comprobaciones_data = (
    supabase
    .table("comprobacion_viaje")
    .select("folio_solicitud")
    .execute()
)

folios_ya_utilizados = set()

if comprobaciones_data.data:

    folios_ya_utilizados = {
        row["folio_solicitud"]
        for row in comprobaciones_data.data
    }

folios_solicitud = ["Selecciona folio"]

for row in solicitudes:

    folio = row["folio_solicitud"]

    estatus = row.get(
        "estatus",
        ""
    )

    if (
        folio not in folios_ya_utilizados
        and estatus == "Aprobado"
    ):

        folios_solicitud.append(folio)

with tab_comprobacion:

    st.subheader("🧾 Comprobacion de Gastos de Viaje")

    st.divider()

    # =========================
    # DATOS CONTABLES
    # =========================

    folio_seleccionado = st.selectbox(
        "REF DE ENTREGA DEL FONDO PARA GASTOS DE ESTE VIAJE",
        folios_solicitud,
        index=0,
        key=f"folio_seleccionado_{COMP_VERSION}"
    )

    solicitud_data = {}

    folio_real = folio_seleccionado.split(" — ")[0]

    if folio_real != "Selecciona folio":

        solicitud_data = next(
            (
                row for row in solicitudes
                if row["folio_solicitud"] == folio_real
            ),
            {}
        )

    st.divider()

    # =================================
    # INFORMACION GENERAL
    # =================================

    with st.container(border=True):

        st.markdown("## 📋 Informacion General")

        empresas_lista = [
            "Seleccione una opción...",
            "SET FREIGHT",
            "LINCOLN",
            "PICUS",
            "IGLOO",
            "SET LOGIS PLUS"
        ]

        unidades_lista = [
            "Seleccione una opción...",
            "CARRIER",
            "LOGISTICA",
            "PLUS"
        ]

        sucursales_lista = [
            "NUEVO LAREDO",
            "DALLAS",
            "CHICAGO",
            "GUADALAJARA",
            "MONTERREY",
            "QUERETARO",
            "LEON",
            "TLAXCALA",
            "OTRO"
        ]

        dynamic_key = f"{COMP_VERSION}_{folio_seleccionado}"

        col1, col2 = st.columns(2)

        with col1:

            empresa_servicio_comp = st.selectbox(
                "Empresa que Brinda el Servicio",
                empresas_lista,
                index=empresas_lista.index(
                    solicitud_data.get(
                        "empresa_brinda_servicio",
                        "Seleccione una opción..."
                    )
                ),
                disabled=True,
                key=f"empresa_servicio_comp_{dynamic_key}"
            )

        with col2:

            empleado_comp = st.text_input(
                "Nombre del Empleado que Solicita",
                value=nombre_usuario,
                disabled=True,
                key=f"empleado_comp_{dynamic_key}"
            )

        motivo_viaje_comp = st.text_area(
            "Motivo del Viaje",
            value=solicitud_data.get(
                "motivo_viaje",
                ""
            ),
            height=100,
            disabled=True,
            key=f"motivo_viaje_comp_{dynamic_key}"
        )

        col1, col2, col3 = st.columns(3)

        with col1:

            fecha_solicitud_comp = st.date_input(
                "Fecha de Solicitud",
                value=pd.to_datetime(
                    solicitud_data.get(
                        "fecha_solicitud",
                        date.today()
                    )
                ).date(),
                disabled=True,
                key=f"fecha_solicitud_comp_{dynamic_key}"
            )

        with col2:

            fecha_inicio_comp = st.date_input(
                "Fecha de Inicio",
                value=pd.to_datetime(
                    solicitud_data.get(
                        "fecha_inicio",
                        date.today()
                    )
                ).date(),
                disabled=True,
                key=f"fecha_inicio_comp_{dynamic_key}"
            )

        with col3:

            fecha_fin_comp = st.date_input(
                "Fecha de Fin",
                value=pd.to_datetime(
                    solicitud_data.get(
                        "fecha_fin",
                        date.today()
                    )
                ).date(),
                disabled=True,
                key=f"fecha_fin_comp_{dynamic_key}"
            )

        col1, col2 = st.columns(2)

        with col1:

            empresa_cargo_comp = st.selectbox(
                "Empresa a Cargo para Gastos de este Viaje",
                empresas_lista,
                index=empresas_lista.index(
                    solicitud_data.get(
                        "empresa_cargo_gastos",
                        "Seleccione una opción..."
                    )
                ),
                disabled=True,
                key=f"empresa_cargo_comp_{dynamic_key}"
            )

        with col2:

            unidad_negocio_comp = st.selectbox(
                "Unidad de Negocio",
                unidades_lista,
                index=unidades_lista.index(
                    solicitud_data.get(
                        "unidad_negocio",
                        "Seleccione una opción..."
                    )
                ),
                disabled=True,
                key=f"unidad_negocio_comp_{dynamic_key}"
            )

        st.markdown("### Sucursal")

        sucursal_db = solicitud_data.get(
            "sucursal",
            "NUEVO LAREDO"
        )

        sucursal_especificar_db = solicitud_data.get(
            "sucursal_especificar",
            ""
        )

        if sucursal_db not in sucursales_lista:
            sucursal_db = "OTRO"

        radio_index = sucursales_lista.index(sucursal_db)

        sucursal_comp = st.radio(
            "",
            sucursales_lista,
            index=radio_index,
            horizontal=True,
            disabled=True,
            label_visibility="collapsed",
            key=f"sucursal_comp_{dynamic_key}"
        )

        if sucursal_db == "OTRO":

            st.text_input(
                "Especificar",
                value=sucursal_especificar_db,
                disabled=True,
                key=f"suc_otro_texto_comp_{dynamic_key}"
            )

        else:

            st.text_input(
                "Especificar",
                value="",
                disabled=True,
                key=f"suc_otro_disabled_comp_{dynamic_key}"
            )

    # =========================
    # IMPORTE DE GASTOS
    # =========================

    with st.container(border=True):

        st.markdown("## 💰 IMPORTE DE GASTOS")

        gastos_comp_key = f"gastos_comprobacion_{COMP_VERSION}"

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
                    "GASOLINA",
                    "OTROS"
                ],
                key=f"tipo_gasto_comp_{COMP_VERSION}"
            )

        with col2:

            gasto_con_comp = st.number_input(
                "Gastos con Comprobante",
                min_value=0.0,
                step=100.0,
                key=f"gasto_con_comp_{COMP_VERSION}"
            )

        with col3:

            gasto_sin_comp = st.number_input(
                "Gastos sin Comprobante",
                min_value=0.0,
                step=100.0,
                key=f"gasto_sin_comp_{COMP_VERSION}"
            )

        st.markdown("<br>", unsafe_allow_html=True)

        col4, col5, col6 = st.columns([1, 1.2, 1.4])

        with col4:

            aplica_iva = st.checkbox(
                "Aplica IVA",
                key=f"aplica_iva_{COMP_VERSION}"
            )

        with col5:

            iva_inline_col1, iva_inline_col2 = st.columns([0.18, 1])

            with iva_inline_col1:

                st.markdown(
                    """
                    <div style="
                        padding-top:8px;
                        font-weight:600;
                        color:white;
                    ">
                        IVA %
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            with iva_inline_col2:

                iva_porcentaje = st.selectbox(
                    "",
                    [
                        8,
                        12,
                        16
                    ],
                    disabled=not aplica_iva,
                    key=f"iva_porcentaje_{COMP_VERSION}",
                    label_visibility="collapsed"
                )

        with col6:

            aplica_retencion = st.checkbox(
                "Aplica Retención ISR",
                key=f"aplica_retencion_{COMP_VERSION}"
            )

        # =========================
        # ADD BUTTON
        # =========================

        if st.button(
            "➕ Agregar Concepto",
            use_container_width=True,
            key=f"btn_agregar_comp_{COMP_VERSION}"
        ):

            if (
                tipo_gasto_comp != "Selecciona un tipo"
            ):

                base_total = (
                    gasto_con_comp +
                    gasto_sin_comp
                )

                impuesto_acreditable = 0

                if (
                    gasto_con_comp > 0
                    and aplica_iva
                ):

                    impuesto_acreditable = (
                        gasto_con_comp *
                        (iva_porcentaje / 100)
                    )

                if (
                    gasto_con_comp > 0
                    and aplica_retencion
                ):

                    impuesto_acreditable -= (
                        gasto_con_comp * 0.0125
                    )

                total_comprobado = (
                    base_total +
                    impuesto_acreditable
                )

                st.session_state[gastos_comp_key].append({

                    "Tipo": tipo_gasto_comp,

                    "Gastos con Comprobante":
                        gasto_con_comp,

                    "Gastos sin Comprobante":
                        gasto_sin_comp,

                    "Impuesto Acreditable":
                        impuesto_acreditable,

                    "Total Comprobado":
                        total_comprobado
                })

        st.markdown("<br>", unsafe_allow_html=True)

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

            df_display.insert(0, "Eliminar", False)

            edited_df = st.data_editor(
                df_display,
                use_container_width=True,
                hide_index=True,
                disabled=[
                    "Tipo",
                    "Gastos con Comprobante",
                    "Gastos sin Comprobante",
                    "Impuesto Acreditable",
                    "Total Comprobado"
                ],
                column_config={
                    "Eliminar": st.column_config.CheckboxColumn(
                        "Eliminar",
                        width="small"
                    )
                },
                key=f"editor_comp_{COMP_VERSION}"
            )

            if st.button(
                "🗑️ Eliminar Filas Seleccionadas",
                use_container_width=True,
                key=f"btn_eliminar_comp_{COMP_VERSION}"
            ):

                filas_restantes = []

                for idx, row in edited_df.iterrows():

                    if not row["Eliminar"]:

                        filas_restantes.append(
                            st.session_state[gastos_comp_key][idx]
                        )

                st.session_state[gastos_comp_key] = filas_restantes

                st.rerun()

            total_general = (
                df_gastos["Total Comprobado"]
                .sum()
            )

        else:

            st.info("No hay conceptos agregados.")
            total_general = 0

        st.markdown("<br>", unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)

        with col2:

            anticipo_viaje = float(
                solicitud_data.get(
                    "total_estimado",
                    0
                ) or 0
            )

            st.text_input(
                "(-) Anticipo para gastos de viaje",
                value=f"$ {anticipo_viaje:,.2f}",
                disabled=True,
                key=f"anticipo_viaje_{dynamic_key}"
            )

        diferencia_cargo = (
            anticipo_viaje - total_general
        )

        with col1:

            st.text_input(
                "TOTAL COMPROBADO",
                value=f"$ {total_general:,.2f}",
                disabled=True,
                key=f"total_comprobado_{total_general}_{COMP_VERSION}"
            )

        with col3:

            st.text_input(
                "DIFERENCIA A CARGO (FAVOR)",
                value=f"$ {diferencia_cargo:,.2f}",
                disabled=True,
                key=f"diferencia_cargo_{diferencia_cargo}_{COMP_VERSION}"
            )

        st.markdown("<br>", unsafe_allow_html=True)

        observaciones_comp = st.text_area(
            "Observaciones",
            height=150,
            key=f"observaciones_comp_{COMP_VERSION}"
        )

    st.markdown("<br><br>", unsafe_allow_html=True)

    submitted_comp = st.button(
        "🧾 Guardar Comprobación",
        use_container_width=True,
        type="primary",
        key=f"submitted_comp_{COMP_VERSION}"
    )

    if submitted_comp:

        if folio_seleccionado == "Selecciona folio":

            st.error(
                "Debes seleccionar un folio."
            )

        else:

            # =================================
            # GENERAR FOLIO COMPROBACION
            # =================================

            existing = (
                supabase
                .table("comprobacion_viaje")
                .select("id")
                .execute()
            )

            consecutivo = len(existing.data) + 1

            folio_comprobacion = (
                f"CGV-{consecutivo:06d}"
            )

            # =================================
            # GUARDAR EN SUPABASE
            # =================================

            supabase.table(
                "comprobacion_viaje"
            ).insert({

                "folio_comprobacion":
                    folio_comprobacion,

                "folio_solicitud":
                    folio_seleccionado,

                "nombre_empleado_solicita":
                    nombre_usuario,

                "conceptos":
                    st.session_state[gastos_comp_key],

                "total_comprobado":
                    float(total_general),

                "anticipo_viaje":
                    float(anticipo_viaje),

                "diferencia_cargo_favor":
                    float(diferencia_cargo),

                "observaciones":
                    observaciones_comp,

                "estatus":
                    "Verificar"

            }).execute()

            @st.dialog("✅ Comprobación Actualizada")
            def mostrar_confirmacion_comp():

                st.success(
                    "Folio actualizado exitosamente."
                )

                st.markdown(
                    "### 📄 FOLIO ACTUALIZADO"
                )

                st.code(
                    folio_seleccionado,
                    language=None
                )

                if st.button(
                    "Cerrar",
                    use_container_width=True,
                    key=f"cerrar_popup_comp_{COMP_VERSION}"
                ):

                    st.session_state[gastos_comp_key] = []

                    st.session_state.comprobacion_form_version += 1

                    st.rerun()

            mostrar_confirmacion_comp()

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