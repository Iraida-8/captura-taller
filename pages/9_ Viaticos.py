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

        # =================================
        # EMPRESA A CARGO
        # =================================

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

        # =================================
        # RESET DEPENDENT FIELDS
        # =================================

        empresa_prev_key = f"empresa_prev_{FORM_VERSION}"

        if empresa_prev_key not in st.session_state:
            st.session_state[empresa_prev_key] = empresa_cargo

        if st.session_state[empresa_prev_key] != empresa_cargo:

            st.session_state[f"unidad_negocio_{FORM_VERSION}"] = (
                "Seleccione una opción..."
            )

            st.session_state[f"sucursal_{FORM_VERSION}"] = "OTRO"

            st.session_state[f"suc_otro_texto_{FORM_VERSION}"] = ""

            st.session_state[empresa_prev_key] = empresa_cargo

            st.rerun()

        # =================================
        # CONFIGURACIONES BASE
        # =================================

        unidad_options = [
            "Seleccione una opción...",
            "CARRIER",
            "LOGISTICA",
            "PLUS"
        ]

        sucursal_options_all = [
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

        unidad_disabled = False
        sucursal_disabled = False

        unidad_default = "Seleccione una opción..."
        sucursal_default = "OTRO"

        sucursal_options = sucursal_options_all.copy()

        # =================================
        # LINCOLN / SET LOGIS PLUS
        # =================================

        if empresa_cargo in ["LINCOLN", "SET LOGIS PLUS"]:

            unidad_disabled = True
            sucursal_disabled = True

            unidad_default = "Seleccione una opción..."
            sucursal_default = "OTRO"

        # =================================
        # IGLOO
        # =================================

        elif empresa_cargo == "IGLOO":

            unidad_disabled = False
            sucursal_disabled = True

            unidad_default = "Seleccione una opción..."
            sucursal_default = "OTRO"

        # =================================
        # SET FREIGHT
        # =================================

        elif empresa_cargo == "SET FREIGHT":

            unidad_disabled = True
            sucursal_disabled = False

            unidad_default = "Seleccione una opción..."
            sucursal_default = "NUEVO LAREDO"

            sucursal_options = [
                "NUEVO LAREDO",
                "DALLAS",
                "CHICAGO",
                "GUADALAJARA",
                "MONTERREY",
                "LEON",
                "QUERETARO",
                "LINCOLN LOGISTICS",
                "ROLANDO ALFARO",
                "OTRO"
            ]

        # =================================
        # PICUS
        # =================================

        elif empresa_cargo == "PICUS":

            unidad_disabled = False

        # =================================
        # ROW
        # =================================

        col1, col2, col3 = st.columns(3)

        # =================================
        # UNIDAD NEGOCIO
        # =================================

        with col1:

            unidad_negocio = st.selectbox(
                "Unidad de Negocio",
                unidad_options,
                index=unidad_options.index(unidad_default),
                disabled=unidad_disabled,
                key=f"unidad_negocio_{FORM_VERSION}"
            )

        # =================================
        # PICUS DEPENDENCIAS
        # =================================

        if empresa_cargo == "PICUS":

            if unidad_negocio == "PLUS":

                sucursal_options = [
                    "NUEVO LAREDO",
                    "QUERETARO",
                    "OTRO"
                ]

                sucursal_disabled = False
                sucursal_default = "NUEVO LAREDO"

            elif unidad_negocio in ["CARRIER", "LOGISTICA"]:

                sucursal_options = ["OTRO"]

                sucursal_disabled = True
                sucursal_default = "OTRO"

            else:

                sucursal_options = ["OTRO"]

                sucursal_disabled = True
                sucursal_default = "OTRO"

        # =================================
        # SUCURSAL
        # =================================

        with col2:

            sucursal = st.selectbox(
                "Sucursal",
                sucursal_options,
                index=sucursal_options.index(sucursal_default),
                disabled=sucursal_disabled,
                key=f"sucursal_{FORM_VERSION}"
            )

        # =================================
        # OTRO
        # =================================

        otro_enabled = sucursal == "OTRO"

        with col3:

            suc_otro_texto = st.text_input(
                "Otro",
                disabled=not otro_enabled,
                key=f"suc_otro_texto_{FORM_VERSION}"
            )

        # =================================
        # SUCURSAL FINAL
        # =================================

        if sucursal == "OTRO":

            sucursales_final = (
                [suc_otro_texto]
                if suc_otro_texto
                else []
            )

        else:

            sucursales_final = [sucursal]

    # =================================
    # GASTOS
    # =================================

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
            "LINCOLN LOGISTICS": "LL",
            "ROLANDO ALFARO": "RA",
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

        if sucursal == "OTRO":
            sucursal_especificar = suc_otro_texto
        else:
            sucursal_especificar = ""

        # =================================
        # GUARDAR
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

            "unidad_negocio": (
                ""
                if unidad_disabled
                else unidad_negocio
            ),

            "sucursal": (
                ""
                if sucursal_disabled and empresa_cargo in ["LINCOLN", "SET LOGIS PLUS"]
                else sucursal
            ),

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

folios_solicitud = [
    "Selecciona folio",
    "Solicitud sin Folio"
]

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
    # SELECT FOLIO
    # =========================

    folio_seleccionado = st.selectbox(
        "REF DE ENTREGA DEL FONDO PARA GASTOS DE ESTE VIAJE",
        folios_solicitud,
        index=0,
        key=f"folio_seleccionado_{COMP_VERSION}"
    )

    # =================================
    # RESET TABLE WHEN FOLIO CHANGES
    # =================================

    folio_tracker_key = (
        f"folio_tracker_{COMP_VERSION}"
    )

    current_folio_value = (
        folio_seleccionado
    )

    if (
        folio_tracker_key
        not in st.session_state
    ):

        st.session_state[
            folio_tracker_key
        ] = current_folio_value

    elif (
        st.session_state[
            folio_tracker_key
        ] != current_folio_value
    ):

        keys_to_clear = [

            f"gastos_comprobacion_{COMP_VERSION}",

            f"loaded_folio_{COMP_VERSION}",

            f"editor_comp_{COMP_VERSION}"
        ]

        for key in keys_to_clear:

            if key in st.session_state:
                del st.session_state[key]

        st.session_state[
            folio_tracker_key
        ] = current_folio_value

        st.rerun()

    solicitud_data = {}

    folio_real = folio_seleccionado.split(" — ")[0]

    if (
        folio_real != "Selecciona folio"
        and folio_real != "Solicitud sin Folio"
    ):

        solicitud_data = next(
            (
                row for row in solicitudes
                if row["folio_solicitud"] == folio_real
            ),
            {}
        )

    modo_sin_folio = (
        folio_seleccionado == "Solicitud sin Folio"
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
            "LINCOLN LOGISTICS",
            "ROLANDO ALFARO",
            "OTRO"
        ]

        dynamic_key = f"{COMP_VERSION}_{folio_seleccionado}"

        # =================================
        # ROW 1
        # =================================

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
                ) if not modo_sin_folio else 0,
                disabled=not modo_sin_folio,
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
            value=(
                solicitud_data.get(
                    "motivo_viaje",
                    ""
                )
                if not modo_sin_folio
                else ""
            ),
            height=100,
            disabled=not modo_sin_folio,
            key=f"motivo_viaje_comp_{dynamic_key}"
        )

        # =================================
        # FECHAS
        # =================================

        col1, col2, col3 = st.columns(3)

        with col1:

            fecha_solicitud_comp = st.date_input(
                "Fecha de Solicitud",
                value=(
                    pd.to_datetime(
                        solicitud_data.get(
                            "fecha_solicitud",
                            date.today()
                        )
                    ).date()
                    if not modo_sin_folio
                    else date.today()
                ),
                disabled=not modo_sin_folio,
                key=f"fecha_solicitud_comp_{dynamic_key}"
            )

        with col2:

            fecha_inicio_comp = st.date_input(
                "Fecha de Inicio",
                value=(
                    pd.to_datetime(
                        solicitud_data.get(
                            "fecha_inicio",
                            date.today()
                        )
                    ).date()
                    if not modo_sin_folio
                    else date.today()
                ),
                disabled=not modo_sin_folio,
                key=f"fecha_inicio_comp_{dynamic_key}"
            )

        with col3:

            fecha_fin_comp = st.date_input(
                "Fecha de Fin",
                value=(
                    pd.to_datetime(
                        solicitud_data.get(
                            "fecha_fin",
                            date.today()
                        )
                    ).date()
                    if not modo_sin_folio
                    else date.today()
                ),
                disabled=not modo_sin_folio,
                key=f"fecha_fin_comp_{dynamic_key}"
            )

        # =================================
        # EMPRESA A CARGO
        # =================================

        col1, col2 = st.columns(2)

        with col1:

            empresa_cargo_default = (
                solicitud_data.get(
                    "empresa_cargo_gastos",
                    "Seleccione una opción..."
                )
                if not modo_sin_folio
                else "Seleccione una opción..."
            )

            empresa_cargo_comp = st.selectbox(
                "Empresa a Cargo para Gastos de este Viaje",
                empresas_lista,
                index=empresas_lista.index(
                    empresa_cargo_default
                ),
                disabled=not modo_sin_folio,
                key=f"empresa_cargo_comp_{dynamic_key}"
            )

        # =================================
        # RESET
        # =================================

        empresa_prev_key_comp = (
            f"empresa_prev_comp_{dynamic_key}"
        )

        if empresa_prev_key_comp not in st.session_state:
            st.session_state[
                empresa_prev_key_comp
            ] = empresa_cargo_comp

        if (
            st.session_state[
                empresa_prev_key_comp
            ] != empresa_cargo_comp
            and modo_sin_folio
        ):

            st.session_state[
                f"unidad_negocio_comp_{dynamic_key}"
            ] = "Seleccione una opción..."

            st.session_state[
                f"sucursal_comp_{dynamic_key}"
            ] = "OTRO"

            st.session_state[
                f"suc_otro_texto_comp_{dynamic_key}"
            ] = ""

            st.session_state[
                empresa_prev_key_comp
            ] = empresa_cargo_comp

            st.rerun()

        # =================================
        # CONFIG
        # =================================

        unidad_disabled_comp = False
        sucursal_disabled_comp = False

        unidad_default_comp = (
            solicitud_data.get(
                "unidad_negocio",
                "Seleccione una opción..."
            )
            if not modo_sin_folio
            else "Seleccione una opción..."
        )

        sucursal_default_comp = (
            solicitud_data.get(
                "sucursal",
                "OTRO"
            )
            if not modo_sin_folio
            else "OTRO"
        )

        sucursal_options_comp = (
            sucursales_lista.copy()
        )

        # =================================
        # LINCOLN / SET LOGIS
        # =================================

        if empresa_cargo_comp in [
            "LINCOLN",
            "SET LOGIS PLUS"
        ]:

            unidad_disabled_comp = True
            sucursal_disabled_comp = True

            unidad_default_comp = (
                "Seleccione una opción..."
            )

            sucursal_default_comp = "OTRO"

        # =================================
        # IGLOO
        # =================================

        elif empresa_cargo_comp == "IGLOO":

            unidad_disabled_comp = False
            sucursal_disabled_comp = True

            sucursal_default_comp = "OTRO"

        # =================================
        # SET FREIGHT
        # =================================

        elif empresa_cargo_comp == "SET FREIGHT":

            unidad_disabled_comp = True
            sucursal_disabled_comp = False

            sucursal_default_comp = (
                "NUEVO LAREDO"
            )

            sucursal_options_comp = [
                "NUEVO LAREDO",
                "DALLAS",
                "CHICAGO",
                "GUADALAJARA",
                "MONTERREY",
                "LEON",
                "QUERETARO",
                "LINCOLN LOGISTICS",
                "ROLANDO ALFARO",
                "OTRO"
            ]

        # =================================
        # ROW
        # =================================

        col1, col2, col3 = st.columns(3)

        with col1:

            unidad_negocio_comp = st.selectbox(
                "Unidad de Negocio",
                unidades_lista,
                index=unidades_lista.index(
                    unidad_default_comp
                ),
                disabled=(
                    unidad_disabled_comp
                    or not modo_sin_folio
                ),
                key=f"unidad_negocio_comp_{dynamic_key}"
            )

        # =================================
        # PICUS
        # =================================

        if empresa_cargo_comp == "PICUS":

            if unidad_negocio_comp == "PLUS":

                sucursal_options_comp = [
                    "NUEVO LAREDO",
                    "QUERETARO",
                    "OTRO"
                ]

                sucursal_disabled_comp = False
                sucursal_default_comp = (
                    "NUEVO LAREDO"
                )

            elif unidad_negocio_comp in [
                "CARRIER",
                "LOGISTICA"
            ]:

                sucursal_options_comp = ["OTRO"]

                sucursal_disabled_comp = True
                sucursal_default_comp = "OTRO"

            else:

                sucursal_options_comp = ["OTRO"]

                sucursal_disabled_comp = True
                sucursal_default_comp = "OTRO"

        # =================================
        # VALIDATE
        # =================================

        if (
            sucursal_default_comp
            not in sucursal_options_comp
        ):
            sucursal_default_comp = "OTRO"

        # =================================
        # SUCURSAL
        # =================================

        with col2:

            sucursal_comp = st.selectbox(
                "Sucursal",
                sucursal_options_comp,
                index=sucursal_options_comp.index(
                    sucursal_default_comp
                ),
                disabled=(
                    sucursal_disabled_comp
                    or not modo_sin_folio
                ),
                key=f"sucursal_comp_{dynamic_key}"
            )

        # =================================
        # OTRO
        # =================================

        otro_enabled_comp = (
            sucursal_comp == "OTRO"
        )

        with col3:

            suc_otro_texto_comp = st.text_input(
                "Otro",
                value=(
                    solicitud_data.get(
                        "sucursal_especificar",
                        ""
                    )
                    if not modo_sin_folio
                    else ""
                ),
                disabled=(
                    not otro_enabled_comp
                    or not modo_sin_folio
                ),
                key=f"suc_otro_texto_comp_{dynamic_key}"
            )

    # =========================
    # IMPORTE DE GASTOS
    # =========================

    with st.container(border=True):

        st.markdown("## 💰 IMPORTE DE GASTOS")

        gastos_comp_key = (
            f"gastos_comprobacion_{COMP_VERSION}"
        )

        loaded_folio_key = (
            f"loaded_folio_{COMP_VERSION}"
        )

        tipos_gasto_lista = [
            "TRANSPORTACION TERRESTRE",
            "HOSPEDAJE",
            "ALIMENTOS",
            "PROPINAS",
            "TAXIS",
            "CASETAS",
            "GASOLINA",
            "OTROS"
        ]

        # =================================
        # INITIALIZE / LOAD DATA
        # =================================

        if gastos_comp_key not in st.session_state:

            st.session_state[
                gastos_comp_key
            ] = []

        if loaded_folio_key not in st.session_state:

            st.session_state[loaded_folio_key] = ""

        # =================================
        # LOAD FROM SOLICITUD
        # =================================

        if (
            not modo_sin_folio
            and folio_seleccionado
            != "Selecciona folio"
            and st.session_state[loaded_folio_key]
            != folio_seleccionado
        ):

            conceptos_solicitud = (
                solicitud_data.get(
                    "conceptos",
                    []
                ) or []
            )

            nuevos_conceptos = []

            for item in conceptos_solicitud:

                monto = float(
                    item.get(
                        "Monto",
                        0
                    ) or 0
                )

                nuevos_conceptos.append({

                    "Eliminar": False,

                    "Tipo":
                        item.get(
                            "Tipo",
                            "OTROS"
                        ),

                    "Descripcion":
                        item.get(
                            "Descripcion",
                            ""
                        ),

                    "Monto":
                        monto,

                    "Comprobante":
                        "No",

                    "Aplica IVA":
                        False,

                    "IVA %":
                        0,

                    "Aplica Retencion":
                        False,

                    "Impuesto Acreditable":
                        0.0,

                    "Total Comprobado":
                        monto
                })

            st.session_state[
                gastos_comp_key
            ] = nuevos_conceptos

            st.session_state[
                loaded_folio_key
            ] = folio_seleccionado

        # =================================
        # EMPTY FOR SIN FOLIO
        # =================================

        elif (
            modo_sin_folio
            and st.session_state[loaded_folio_key]
            != "Solicitud sin Folio"
        ):

            st.session_state[
                gastos_comp_key
            ] = []

            st.session_state[
                loaded_folio_key
            ] = "Solicitud sin Folio"

        # =================================
        # ADD NEW ROW
        # =================================

        if st.button(
            "➕ Agregar Concepto",
            use_container_width=True,
            key=f"btn_add_row_{COMP_VERSION}"
        ):

            st.session_state[
                gastos_comp_key
            ].append({

                "Eliminar": False,

                "Tipo": "OTROS",

                "Descripcion": "",

                "Monto": 0.0,

                "Comprobante": "No",

                "Aplica IVA": False,

                "IVA %": 0,

                "Aplica Retencion": False,

                "Impuesto Acreditable": 0.0,

                "Total Comprobado": 0.0
            })

            st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)

        # =================================
        # TABLE
        # =================================

        if st.session_state[gastos_comp_key]:

            df_gastos = pd.DataFrame(
                st.session_state[gastos_comp_key]
            )

            edited_df = st.data_editor(

                df_gastos,

                use_container_width=True,

                hide_index=True,

                num_rows="dynamic",

                column_config={

                    "Eliminar":
                        st.column_config.CheckboxColumn(
                            "Eliminar",
                            width="small"
                        ),

                    "Tipo":
                        st.column_config.SelectboxColumn(
                            "Tipo",
                            options=tipos_gasto_lista,
                            required=True
                        ),

                    "Descripcion":
                        st.column_config.TextColumn(
                            "Descripcion"
                        ),

                    "Monto":
                        st.column_config.NumberColumn(
                            "Monto",
                            format="$ %.2f"
                        ),

                    "Comprobante":
                        st.column_config.SelectboxColumn(
                            "Comprobante",
                            options=["Si", "No"]
                        ),

                    "Aplica IVA":
                        st.column_config.CheckboxColumn(
                            "IVA"
                        ),

                    "IVA %":
                        st.column_config.SelectboxColumn(
                            "IVA %",
                            options=[0, 8, 12, 16]
                        ),

                    "Aplica Retencion":
                        st.column_config.CheckboxColumn(
                            "Retencion ISR"
                        ),

                    "Impuesto Acreditable":
                        st.column_config.NumberColumn(
                            "Impuesto Acreditable",
                            format="$ %.2f",
                            disabled=True
                        ),

                    "Total Comprobado":
                        st.column_config.NumberColumn(
                            "Total Comprobado",
                            format="$ %.2f",
                            disabled=True
                        )
                },

                key=f"editor_comp_{COMP_VERSION}"
            )

            # =================================
            # SAVE USER EDITS FIRST
            # =================================

            st.session_state[
                gastos_comp_key
            ] = edited_df.to_dict(
                orient="records"
            )

            # =================================
            # RECALCULATE
            # =================================

            recalculated_rows = []

            for row in edited_df.to_dict(
                orient="records"
            ):

                monto = float(
                    row.get(
                        "Monto",
                        0
                    ) or 0
                )

                comprobante = row.get(
                    "Comprobante",
                    "No"
                )

                aplica_iva = bool(
                    row.get(
                        "Aplica IVA",
                        False
                    )
                )

                iva_pct = int(
                    row.get(
                        "IVA %",
                        0
                    ) or 0
                )

                aplica_ret = bool(
                    row.get(
                        "Aplica Retencion",
                        False
                    )
                )

                impuesto = 0.0

                if aplica_iva:

                    impuesto += (
                        monto *
                        (iva_pct / 100)
                    )

                if aplica_ret:

                    impuesto -= (
                        monto * 0.0125
                    )

                total_final = (
                    monto +
                    impuesto
                )

                recalculated_rows.append({

                    "Eliminar":
                        bool(
                            row.get(
                                "Eliminar",
                                False
                            )
                        ),

                    "Tipo":
                        row.get(
                            "Tipo",
                            "OTROS"
                        ),

                    "Descripcion":
                        row.get(
                            "Descripcion",
                            ""
                        ),

                    "Monto":
                        monto,

                    "Comprobante":
                        comprobante,

                    "Aplica IVA":
                        aplica_iva,

                    "IVA %":
                        iva_pct,

                    "Aplica Retencion":
                        aplica_ret,

                    "Impuesto Acreditable":
                        round(
                            impuesto,
                            2
                        ),

                    "Total Comprobado":
                        round(
                            total_final,
                            2
                        )
                })

            # =================================
            # SAVE FINAL RECALCULATED DATA
            # =================================

            st.session_state[
                gastos_comp_key
            ] = recalculated_rows

            # =================================
            # RECALCULATE TOTAL FROM FINAL STATE
            # =================================

            total_general = sum(

                float(
                    row.get(
                        "Total Comprobado",
                        0
                    ) or 0
                )

                for row in
                st.session_state[
                    gastos_comp_key
                ]
            )

            # =================================
            # DELETE
            # =================================

            if st.button(
                "🗑️ Eliminar Filas Seleccionadas",
                use_container_width=True,
                key=f"btn_delete_rows_{COMP_VERSION}"
            ):

                st.session_state[
                    gastos_comp_key
                ] = [

                    row

                    for row in
                    recalculated_rows

                    if not row["Eliminar"]
                ]

                st.rerun()

        else:

            st.info(
                "No hay conceptos agregados."
            )

            total_general = 0

        # =================================
        # TOTALES
        # =================================

        st.markdown("<br>", unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)

        with col2:

            if modo_sin_folio:

                anticipo_viaje = 0.00

            else:

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
            total_general -
            anticipo_viaje
        )

        with col1:

            st.text_input(
                "TOTAL COMPROBADO",
                value=f"$ {total_general:,.2f}",
                disabled=True
            )

        with col3:

            st.text_input(
                "DIFERENCIA A CARGO (FAVOR)",
                value=f"$ {diferencia_cargo:,.2f}",
                disabled=True
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
            # MODO SIN FOLIO
            # =================================

            if modo_sin_folio:

                # =============================
                # GENERAR FOLIO SOLICITUD
                # =============================

                existing_sf = (
                    supabase
                    .table("solicitud_viaje")
                    .select("id")
                    .execute()
                )

                consecutivo_sf = (
                    len(existing_sf.data) + 1
                )

                folio_solicitud_sf = (
                    f"SF-{consecutivo_sf:06d}-SF"
                )

                # =============================
                # SUCURSAL ESPECIFICAR
                # =============================

                if sucursal_comp == "OTRO":

                    sucursal_especificar_sf = (
                        suc_otro_texto_comp
                    )

                else:

                    sucursal_especificar_sf = ""

                # =============================
                # INSERT SOLICITUD_VIAJE
                # =============================

                supabase.table(
                    "solicitud_viaje"
                ).insert({

                    "folio_solicitud":
                        folio_solicitud_sf,

                    "empresa_brinda_servicio":
                        empresa_servicio_comp,

                    "nombre_empleado_solicita":
                        nombre_usuario,

                    "motivo_viaje":
                        "Operacion/Solicitud sin Folio",

                    "fecha_solicitud":
                        str(fecha_solicitud_comp),

                    "fecha_inicio":
                        str(fecha_inicio_comp),

                    "fecha_fin":
                        str(fecha_fin_comp),

                    "empresa_cargo_gastos":
                        empresa_cargo_comp,

                    "unidad_negocio": (
                        ""
                        if unidad_disabled_comp
                        else unidad_negocio_comp
                    ),

                    "sucursal": (
                        ""
                        if (
                            sucursal_disabled_comp
                            and empresa_cargo_comp
                            in [
                                "LINCOLN",
                                "SET LOGIS PLUS"
                            ]
                        )
                        else sucursal_comp
                    ),

                    "sucursal_especificar":
                        sucursal_especificar_sf,

                    "conceptos": [
                        {
                            "Tipo": "OTROS",
                            "Descripcion":
                                "Operacion sin Solicitud",
                            "Monto": 0.00
                        }
                    ],

                    "total_estimado":
                        0.00,

                    "observaciones":
                        "Operacion/Solicitud sin Folio",

                    "estatus":
                        "Verificar"

                }).execute()

                folio_solicitud_final = (
                    folio_solicitud_sf
                )

                anticipo_viaje = 0.00

            else:

                folio_solicitud_final = (
                    folio_seleccionado
                )

            # =================================
            # INSERT COMPROBACION
            # =================================

            supabase.table(
                "comprobacion_viaje"
            ).insert({

                "folio_comprobacion":
                    folio_comprobacion,

                "folio_solicitud":
                    folio_solicitud_final,

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
                    folio_comprobacion,
                    language=None
                )

                if modo_sin_folio:

                    st.markdown(
                        "### 📄 FOLIO SOLICITUD GENERADO"
                    )

                    st.code(
                        folio_solicitud_final,
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