import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from supabase import create_client
from datetime import datetime, timezone
from auth import require_login, require_access
import resend # type: ignore
from io import BytesIO
from pages.css import load_css

# =================================
# RELEASE CHANNEL
# =================================

APP_CHANNEL = "BETA"
# APP_CHANNEL = "RELEASE"

DASHBOARD_PAGE = (
    "pages/dashboard_beta.py"
    if APP_CHANNEL == "BETA"
    else "pages/dashboard.py"
)

# =================================
# Page configuration
# =================================
st.set_page_config(
    page_title="Gestión de Viáticos",
    layout="wide"
)

# -------------------------------
# PAGE STYLE
# -------------------------------
load_css()

# =================================
# Security gates
# =================================
require_login()
require_access("gestion_viaticos")

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
# RESEND CONFIG
# =================================

resend.api_key = (
    st.secrets["RESEND_API_KEY"]
)

# =================================
# USER DATA
# =================================
user = st.session_state.user

nombre_usuario = (
    user.get("name")
    or user.get("email")
    or ""
)

email_usuario = (
    user.get("email")
    or ""
)

# =================================
# EMAIL CONFIG
# =================================

EMAILS_FIJOS = [

    "Maria.garcia@palosgarza.com",

    "cristobal.ochoa@set-freight.com",

    "practicas.auditoria@palosgarzalogistics.com"
]

EMAILS_EMPRESA = {

    "SET FREIGHT": [

        "karina.colina@palosgarza.com",

        "cindy.gonzalez@palosgarza.com"
    ],

    "LINCOLN": [

        "karina.colina@palosgarza.com",

        "corina@palosgarza.com",

        "ivonne.hernandez@palosgarza.com"
    ],

    "PICUS": [

        "argelia.salinas@palosgarza.com"
    ],

    "IGLOO": [

        "agustin.rodriguez@palosgarza.com"
    ],

    "SET LOGIS PLUS": [

        "juan.santos@palosgarza.com"
    ]
}

# =================================
# GET EMAIL FROM PROFILE
# =================================

def obtener_email_usuario(nombre_completo):

    try:

        response = (
            supabase
            .table("profiles")
            .select("email")
            .eq(
                "full_name",
                nombre_completo
            )
            .limit(1)
            .execute()
        )

        if (
            response.data
            and len(response.data) > 0
        ):

            return (
                response
                .data[0]
                .get("email")
            )

    except Exception as e:

        st.warning(
            f"Error obteniendo email: {e}"
        )

    return None

# =================================
# EMAIL TEST MODE
# =================================

EMAIL_TEST_MODE = True
EMAIL_TEST_RECIPIENT = (
    "aldo.sanchez@palosgarzalogistics.com"
)

def construir_destinatarios(
    empresa,
    email_usuario_actual,
    correo_creador=None
):

    if EMAIL_TEST_MODE:
        return [EMAIL_TEST_RECIPIENT]

    destinatarios = []


    # =================================
    # LOGGED USER
    # =================================

    if (
        email_usuario_actual
        and email_usuario_actual not in destinatarios
    ):

        destinatarios.append(
            email_usuario_actual
        )

    # =================================
    # CREATOR EMAIL
    # =================================

    if (
        correo_creador
        and correo_creador not in destinatarios
    ):

        destinatarios.append(
            correo_creador
        )

    # =================================
    # FIXED EMAILS
    # =================================

    for correo in EMAILS_FIJOS:

        if correo not in destinatarios:

            destinatarios.append(correo)

    # =================================
    # CONDITIONAL EMAILS
    # =================================

    empresa = str(
        empresa or ""
    ).strip().upper()

    correos_empresa = (
        EMAILS_EMPRESA.get(
            empresa,
            []
        )
    )

    for correo in correos_empresa:

        if correo not in destinatarios:

            destinatarios.append(correo)

    return destinatarios

# =================================
# EMAIL APROBACION / RECHAZO
# =================================

def enviar_correo_estatus_solicitud(

    destinatarios,
    folio,
    estatus,
    fecha_inicio,
    fecha_fin,
    motivo_viaje,
    observaciones,
    conceptos

):

    total_aprobado = 0.0

    conceptos_html = ""

    for item in conceptos:

        tipo = item.get("Tipo", "")

        descripcion = item.get(
            "Descripcion",
            ""
        )

        monto = float(
            item.get(
                "Monto",
                0
            ) or 0
        )

        moneda = item.get(
            "Moneda",
            "MXN"
        )

        aprobado = str(
            item.get(
                "Aprobado",
                "Si"
            )
        )

        razon = item.get(
            "Razon",
            ""
        )

        aprobado_texto = (
            "🟢 APROBADO"
            if aprobado in [
                "Si",
                "🟢 Si"
            ]
            else "🔴 RECHAZADO"
        )

        if aprobado in [
            "Si",
            "🟢 Si"
        ]:

            total_aprobado += monto

        conceptos_html += f"""

        <tr>

            <td style="
                border:1px solid #ccc;
                padding:8px;
            ">
                {tipo}
            </td>

            <td style="
                border:1px solid #ccc;
                padding:8px;
            ">
                {descripcion}
            </td>

            <td style="
                border:1px solid #ccc;
                padding:8px;
            ">
                {moneda}
            </td>

            <td style="
                border:1px solid #ccc;
                padding:8px;
            ">
                ${monto:,.2f}
            </td>

            <td style="
                border:1px solid #ccc;
                padding:8px;
                font-weight:700;
            ">
                {aprobado_texto}
            </td>

            <td style="
                border:1px solid #ccc;
                padding:8px;
            ">
                {razon}
            </td>

        </tr>
        """

    if estatus in ["Aprobado", "Concluido"]:

        color_estatus = "#10B981"

    elif estatus == "Rechazado":

        color_estatus = "#EF4444"

    else:

        color_estatus = "#38BDF8"

    html = f"""

    <div style="
        font-family:Arial;
        max-width:900px;
        margin:auto;
    ">

        <h2 style="
            color:#151F6D;
        ">
            Actualización de Solicitud
        </h2>

        <h2 style="
            color:{color_estatus};
        ">
            {estatus}
        </h2>

        <hr>

        <p>
            <b>Folio:</b>
            {folio}
        </p>

        <p>
            <b>Fecha Inicio:</b>
            {fecha_inicio}
        </p>

        <p>
            <b>Fecha Fin:</b>
            {fecha_fin}
        </p>

        <p>
            <b>Motivo del Viaje:</b>
            {motivo_viaje}
        </p>

        <hr>

        <h3>
            Conceptos
        </h3>

        <table style="
            width:100%;
            border-collapse:collapse;
        ">

            <tr style="
                background:#151F6D;
                color:white;
            ">

                <th style="padding:10px;">
                    Tipo
                </th>

                <th style="padding:10px;">
                    Descripción
                </th>

                <th style="padding:10px;">
                    Moneda
                </th>

                <th style="padding:10px;">
                    Monto
                </th>

                <th style="padding:10px;">
                    Estatus
                </th>

                <th style="padding:10px;">
                    Razón
                </th>

            </tr>

            {conceptos_html}

        </table>

        <h2 style="
            margin-top:30px;
            color:#BFA75F;
        ">
            TOTAL APROBADO:
            ${total_aprobado:,.2f}
        </h2>

    </div>
    """

    resend.Emails.send({

        "from":
            "onboarding@resend.dev",

        "to":
            destinatarios,

        "subject":
            folio,

        "html":
            html
    })

# =================================
# LOAD DATA
# =================================

@st.cache_data(ttl=30)
def cargar_solicitudes():

    all_rows = []

    page_size = 1000
    start = 0

    while True:

        response = (
            supabase
            .table("solicitud_viaje")
            .select("*")
            .order("created_at", desc=True)
            .range(
                start,
                start + page_size - 1
            )
            .execute()
        )

        data = response.data or []

        if len(data) == 0:
            break

        all_rows.extend(data)

        if len(data) < page_size:
            break

        start += page_size

    return pd.DataFrame(all_rows)


@st.cache_data(ttl=30)
def cargar_comprobaciones():

    all_rows = []

    page_size = 1000
    start = 0

    while True:

        response = (
            supabase
            .table("comprobacion_viaje")
            .select("*")
            .order("created_at", desc=True)
            .range(
                start,
                start + page_size - 1
            )
            .execute()
        )

        data = response.data or []

        if len(data) == 0:
            break

        all_rows.extend(data)

        if len(data) < page_size:
            break

        start += page_size

    return pd.DataFrame(all_rows)


df_solicitudes = cargar_solicitudes()
df_comprobaciones = cargar_comprobaciones()

# =================================
# EMPTY DATAFRAME SAFETY
# =================================

if df_solicitudes.empty:

    df_solicitudes = pd.DataFrame(columns=[

        "folio_solicitud",
        "estatus",
        "nombre_empleado_solicita",
        "fecha_solicitud",
        "total_estimado",
        "created_at"
    ])

if df_comprobaciones.empty:

    df_comprobaciones = pd.DataFrame(columns=[

        "folio_solicitud",
        "folio_comprobacion",
        "estatus",
        "nombre_empleado_solicita",
        "conceptos",
        "observaciones",
        "total_comprobado",
        "anticipo_viaje",
        "diferencia_cargo_favor",
        "created_at"
    ])

# =================================
# GLOBAL TOAST
# =================================

if "toast_actualizado" in st.session_state:

    st.toast(
        st.session_state.toast_actualizado
    )

    del st.session_state[
        "toast_actualizado"
    ]

# =================================
# Navigation
# =================================
st.write("")
if st.button("⬅ Volver al Dashboard"):
    st.switch_page(DASHBOARD_PAGE)

st.divider()

# =================================
# KPI VALUES
# =================================
if "estatus" not in df_solicitudes.columns:
    df_solicitudes["estatus"] = "Pendiente"

df_solicitudes["estatus"] = (
    df_solicitudes["estatus"]
    .fillna("Pendiente")
    .astype(str)
    .str.strip()
)

if "estatus" not in df_comprobaciones.columns:
    df_comprobaciones["estatus"] = "Pendiente"

df_comprobaciones["estatus"] = (
    df_comprobaciones["estatus"]
    .fillna("Pendiente")
    .astype(str)
    .str.strip()
)

# =================================
# KPI COUNTS
# =================================
total_registros = (
    df_solicitudes["folio_solicitud"]
    .astype(str)
    .str.strip()
    .nunique()
)

# PENDIENTES
pendientes = len(
    df_solicitudes[
        df_solicitudes["estatus"] == "Pendiente"
    ]
)

# AUTORIZADAS
autorizados = len(
    df_solicitudes[
        df_solicitudes["estatus"] == "Aprobado"
    ]
)

# VERIFICANDO
verificando = len(
    df_solicitudes[
        df_solicitudes["estatus"] == "Verificar"
    ]
)

# RECHAZADAS
rechazados = len(
    df_solicitudes[
        df_solicitudes["estatus"] == "Rechazado"
    ]
)

# =================================
# CONCLUIDOS
# =================================
concluidos = len(
    df_solicitudes[
        df_solicitudes["estatus"] == "Concluido"
    ]
)

# =================================
# HEADER
# =================================
st.title("⚙ Gestión de Viáticos")

# =================================
# KPI CARDS
# =================================
kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)

import streamlit.components.v1 as components

def render_kpi_card(
    title,
    value,
    emoji,
    color,
):

    html = f"""
    <div style="padding:6px;">
        <div style="
            background:#FFF7D6;
            padding:20px;
            border-radius:18px;
            box-shadow:0 4px 10px rgba(0,0,0,.10);
            min-height:170px;
            color:#111;
            font-family:sans-serif;
        ">

            <div style="
                color:#666666;
                font-size:15px;
                font-weight:600;
            ">
                {emoji} {title}
            </div>

            <div style="
                text-align:center;
                color:{color};
                font-size:58px;
                font-weight:800;
                margin-top:40px;
            ">
                {value}
            </div>

        </div>
    </div>
    """

    components.html(html, height=240)

with kpi1:

    render_kpi_card(
        "Total",
        total_registros,
        "📊",
        "#BFA75F"
    )

with kpi2:

    render_kpi_card(
        "Pendientes",
        pendientes,
        "⏳",
        "#F59E0B"
    )

with kpi3:

    render_kpi_card(
        "Autorizadas",
        autorizados,
        "✅",
        "#10B981"
    )

with kpi4:

    render_kpi_card(
        "Verificando",
        verificando,
        "🔎",
        "#38BDF8"
    )

with kpi5:

    render_kpi_card(
        "Rechazadas",
        rechazados,
        "❌",
        "#EF4444"
    )

with kpi6:

    render_kpi_card(
        "Concluidos",
        concluidos,
        "🏁",
        "#8B5CF6"
    )

st.markdown("<br><br>", unsafe_allow_html=True)

# =================================
# PENDIENTES SECTION
# =================================
st.header("📋 Solicitudes Pendientes")

# Only pendientes
df_pendientes = df_solicitudes[
    df_solicitudes["estatus"] == "Pendiente"
].copy()

# Sort newest first
if "created_at" in df_pendientes.columns:

    df_pendientes = df_pendientes.sort_values(
        by="created_at",
        ascending=False
    )

# =================================
# PAGINATION
# =================================

ENTRADAS_POR_PAGINA = 5

total_entries = len(df_pendientes)

total_paginas = max(
    1,
    (total_entries + ENTRADAS_POR_PAGINA - 1)
    // ENTRADAS_POR_PAGINA
)

if "pagina_viaticos" not in st.session_state:
    st.session_state.pagina_viaticos = 1

pagina_actual = st.session_state.pagina_viaticos

inicio = (
    (pagina_actual - 1)
    * ENTRADAS_POR_PAGINA
)

fin = inicio + ENTRADAS_POR_PAGINA

df_pagina = df_pendientes.iloc[inicio:fin]

# =================================
# MODAL
# =================================
@st.dialog("Detalle de Solicitud")

def modal_ver_solicitud(row):

    st.markdown(
        "<h2 style='color:#151F6D;'>📋 Información General</h2>",
        unsafe_allow_html=True
    )

    col1, col2 = st.columns(2)

    with col1:

        st.markdown(
            f"<span style='color:black;'><b>Folio:</b> {row.get('folio_solicitud', '')}</span>",
            unsafe_allow_html=True
        )

        st.markdown(
            f"<span style='color:black;'><b>Estatus:</b> {row.get('estatus', '')}</span>",
            unsafe_allow_html=True
        )

        st.markdown(
            f"<span style='color:black;'><b>Empresa Brinda Servicio:</b> {row.get('empresa_brinda_servicio', '')}</span>",
            unsafe_allow_html=True
        )

        st.markdown(
            f"<span style='color:black;'><b>Empleado Solicita:</b> {row.get('nombre_empleado_solicita', '')}</span>",
            unsafe_allow_html=True
        )

        st.markdown(
            f"<span style='color:black;'><b>Fecha Solicitud:</b> {row.get('fecha_solicitud', '')}</span>",
            unsafe_allow_html=True
        )

        st.markdown(
            f"<span style='color:black;'><b>Fecha Inicio:</b> {row.get('fecha_inicio', '')}</span>",
            unsafe_allow_html=True
        )

        st.markdown(
            f"<span style='color:black;'><b>Fecha Fin:</b> {row.get('fecha_fin', '')}</span>",
            unsafe_allow_html=True
        )

    with col2:

        st.markdown(
            f"<span style='color:black;'><b>Empresa Cargo Gastos:</b> {row.get('empresa_cargo_gastos', '')}</span>",
            unsafe_allow_html=True
        )

        st.markdown(
            f"<span style='color:black;'><b>Unidad Negocio:</b> {row.get('unidad_negocio', '')}</span>",
            unsafe_allow_html=True
        )

        st.markdown(
            f"<span style='color:black;'><b>Sucursal:</b> {row.get('sucursal', '')}</span>",
            unsafe_allow_html=True
        )

        st.markdown(
            f"<span style='color:black;'><b>Sucursal Especificar:</b> {row.get('sucursal_especificar', '')}</span>",
            unsafe_allow_html=True
        )

        label_cliente = (
            "Motivo del Viaje"
            if str(
                row.get(
                    "motivo_viaje",
                    ""
                )
            ).strip().upper() == "OTROS"
            else "Nombre del Cliente"
        )

        st.markdown(
            f"<span style='color:black;'><b>{label_cliente}:</b> {row.get('nombre_cliente', '')}</span>",
            unsafe_allow_html=True
        )

        st.markdown(
            f"<span style='color:black;'><b>Registro SAC Ventas?:</b> {row.get('folio_sac', '')}</span>",
            unsafe_allow_html=True
        )

    # =================================
    # MOTIVO VIAJE
    # =================================
    st.markdown("---")

    st.markdown("## ✈️ Motivo del Viaje")

    st.markdown(
        f"""
        <div style='
            background-color:#F3F4F6;
            padding:16px;
            border-radius:12px;
            border:1px solid rgba(191,167,95,0.25);
            margin-bottom:20px;
            white-space:pre-wrap;
        '>
            {row.get('motivo_viaje', '')}
        </div>
        """,
        unsafe_allow_html=True
    )

    # =================================
    # OBSERVACIONES
    # =================================

    st.markdown(
        "<h2 style='color:#151F6D;'>📝 Observaciones</h2>",
        unsafe_allow_html=True
    )

    observaciones_edit = st.text_area(
        label="",
        value=row.get(
            "observaciones",
            ""
        ),
        height=150,
        key=f"obs_edit_{row.get('id')}",
        label_visibility="collapsed"
    )

    # =================================
    # CONCEPTOS
    # =================================

    st.markdown("---")

    st.markdown("## 💰 Conceptos")

    total_value = row.get(
        "total_estimado",
        0
    )

    try:
        total_value = float(total_value)
    except:
        total_value = 0

    st.markdown(
        f"""
        <div style='
            font-size:24px;
            font-weight:700;
            color:#BFA75F;
            margin-bottom:15px;
        '>
            Total Estimado: ${total_value:,.2f}
        </div>
        """,
        unsafe_allow_html=True
    )

    conceptos = row.get(
        "conceptos",
        []
    )

    if conceptos:

        try:

            conceptos_final = []

            for concepto in conceptos:

                conceptos_final.append({

                    "Tipo":
                        concepto.get(
                            "Tipo",
                            ""
                        ),

                    "Descripcion":
                        concepto.get(
                            "Descripcion",
                            ""
                        ),

                    "Monto":
                        concepto.get(
                            "Monto",
                            0
                        ),
                    
                    "Tipo Cambio":
                        concepto.get(
                            "Tipo Cambio",
                            ""
                        ),

                    "Aprobado":
                        "🟢 Si"
                        if concepto.get(
                            "Aprobado",
                            "Si"
                        ) in ["Si", "🟢 Si"]
                        else "🔴 No",

                    "Razon":
                        concepto.get(
                            "Razon",
                            ""
                        )
                })

            df_conceptos = pd.DataFrame(
                conceptos_final
            )

            edited_df = st.data_editor(

                df_conceptos,

                use_container_width=True,

                hide_index=True,

                num_rows="fixed",

                column_config={

                    "Tipo":
                        st.column_config.TextColumn(
                            "Tipo",
                            disabled=True
                        ),

                    "Descripcion":
                        st.column_config.TextColumn(
                            "Descripcion",
                            disabled=True
                        ),

                    "Monto":
                        st.column_config.NumberColumn(
                            "Monto",
                            disabled=True,
                            format="$ %.2f"
                        ),

                    "Aprobado":
                        st.column_config.SelectboxColumn(
                            "Aprobado",
                            options=[
                                "🟢 Si",
                                "🔴 No"
                            ],
                            required=True
                        ),

                    "Razon":
                        st.column_config.TextColumn(
                            "Razon"
                        )
                },

                key=f"editor_conceptos_{row.get('id')}"
            )

            st.markdown("<br>", unsafe_allow_html=True)

            if st.button(
                "💾 Actualizar Solicitud",
                use_container_width=True,
                key=f"actualizar_sol_{row.get('id')}"
            ):

                conceptos_actualizados = (
                    edited_df.to_dict(
                        orient="records"
                    )
                )

                # =================================
                # RECALCULAR TOTAL ESTIMADO
                # =================================

                nuevo_total_estimado = 0.0

                for item in conceptos_actualizados:

                    aprobado = str(
                        item.get(
                            "Aprobado",
                            "🟢 Si"
                        )
                    ).strip()

                    if aprobado in [
                        "Si",
                        "🟢 Si"
                    ]:

                        try:

                            nuevo_total_estimado += float(
                                item.get(
                                    "Monto",
                                    0
                                ) or 0
                            )

                        except:

                            pass

                supabase.table(
                    "solicitud_viaje"
                ).update(
                    {
                        "observaciones":
                            observaciones_edit,

                        "conceptos":
                            conceptos_actualizados,

                        "total_estimado":
                            float(
                                nuevo_total_estimado
                            ),

                        "fecha_actualizacion":
                            datetime.now(
                                timezone.utc
                            ).isoformat()
                    }
                ).eq(
                    "id",
                    row["id"]
                ).execute()

                st.cache_data.clear()

                st.session_state.toast_actualizado = (
                    f"Folio "
                    f"{row.get('folio_solicitud', '')} "
                    f"actualizado con éxito"
                )

                st.rerun()

        except Exception as e:

            st.error(
                f"Error leyendo conceptos: {e}"
            )

    else:

        st.info(
            "No hay conceptos registrados."
        )

# =================================
# GRID ENTRIES
# =================================

for idx, row in df_pagina.iterrows():

    with st.container(border=True):

        col1, col2, col3, col4, col5, col6, col7 = st.columns(
            [1, 2, 2, 2, 2, 1.2, 1.2]
        )

        # VER BUTTON
        with col1:

            if st.button(
                "Ver",
                key=f"ver_{idx}",
                use_container_width=True
            ):
                modal_ver_solicitud(row)

        # FOLIO
        with col2:

            st.caption("Folio")
            st.write(f"**{row.get('folio_solicitud', '')}**")

        # EMPLEADO
        with col3:

            st.caption("Empleado")
            st.write(f"**{row.get('nombre_empleado_solicita', '')}**")

        # FECHA
        with col4:

            st.caption("Fecha Solicitud")
            st.write(f"**{row.get('fecha_solicitud', '')}**")

        # TOTAL
        with col5:

            total_value = row.get("total_estimado", 0)

            try:
                total_value = float(total_value)
            except Exception:
                total_value = 0

            st.caption("Total")
            st.write(f"**${total_value:,.2f}**")

        # APROBAR
        with col6:

            if st.button(
                "Aprobar",
                key=f"aprobar_{idx}",
                use_container_width=True
            ):

                supabase.table(
                    "solicitud_viaje"
                ).update(
                    {
                        "estatus": "Aprobado",
                        "fecha_actualizacion": datetime.now(
                            timezone.utc
                        ).isoformat()
                    }
                ).eq(
                    "id",
                    row["id"]
                ).execute()

                # =================================
                # GET CREATOR EMAIL
                # =================================

                correo_creador = (
                    obtener_email_usuario(
                        row.get(
                            "nombre_empleado_solicita",
                            ""
                        )
                    )
                )

                destinatarios = construir_destinatarios(

                    empresa=row.get(
                        "empresa_brinda_servicio",
                        ""
                    ),

                    email_usuario_actual=email_usuario,

                    correo_creador=correo_creador
                )

                # =================================
                # SEND EMAIL
                # =================================

                try:

                    enviar_correo_estatus_solicitud(

                        destinatarios=destinatarios,

                        folio=row.get(
                            "folio_solicitud",
                            ""
                        ),

                        estatus="Aprobado",

                        fecha_inicio=row.get(
                            "fecha_inicio",
                            ""
                        ),

                        fecha_fin=row.get(
                            "fecha_fin",
                            ""
                        ),

                        motivo_viaje=row.get(
                            "motivo_viaje",
                            ""
                        ),

                        observaciones=row.get(
                            "observaciones",
                            ""
                        ),

                        conceptos=row.get(
                            "conceptos",
                            []
                        )
                    )

                except Exception as e:

                    st.warning(
                        f"No se pudo enviar correo: {e}"
                    )



                st.success("Solicitud aprobada")
                st.cache_data.clear()
                st.rerun()

        # RECHAZAR
        with col7:

            if st.button(
                "Rechazar",
                key=f"rechazar_{idx}",
                use_container_width=True
            ):

                supabase.table(
                    "solicitud_viaje"
                ).update(
                    {
                        "estatus": "Rechazado",
                        "fecha_actualizacion": datetime.now(
                            timezone.utc
                        ).isoformat()
                    }
                ).eq(
                    "id",
                    row["id"]
                ).execute()

                # =================================
                # GET CREATOR EMAIL
                # =================================

                correo_creador = (
                    obtener_email_usuario(
                        row.get(
                            "nombre_empleado_solicita",
                            ""
                        )
                    )
                )

                destinatarios = construir_destinatarios(

                    empresa=row.get(
                        "empresa_brinda_servicio",
                        ""
                    ),

                    email_usuario_actual=email_usuario,

                    correo_creador=correo_creador
                )

                # =================================
                # SEND EMAIL
                # =================================

                try:

                    enviar_correo_estatus_solicitud(

                        destinatarios=destinatarios,

                        folio=row.get(
                            "folio_solicitud",
                            ""
                        ),

                        estatus="Rechazado",

                        fecha_inicio=row.get(
                            "fecha_inicio",
                            ""
                        ),

                        fecha_fin=row.get(
                            "fecha_fin",
                            ""
                        ),

                        motivo_viaje=row.get(
                            "motivo_viaje",
                            ""
                        ),

                        observaciones=row.get(
                            "observaciones",
                            ""
                        ),

                        conceptos=row.get(
                            "conceptos",
                            []
                        )
                    )

                except Exception as e:

                    st.warning(
                        f"No se pudo enviar correo: {e}"
                    )

                st.error("Solicitud rechazada")
                st.cache_data.clear()
                st.rerun()

# =================================
# PAGINATION CONTROLS
# =================================

st.divider()

p1, p2, p3 = st.columns([1,2,1])

with p1:

    if st.button(
        "⬅ Anterior",
        disabled=st.session_state.pagina_viaticos <= 1,
        use_container_width=True,
        key="prev_pendientes"
    ):

        st.session_state.pagina_viaticos -= 1
        st.rerun()

with p2:

    st.markdown(
        f"""
        <div style="
            text-align:center;
            padding-top:8px;
            font-weight:700;
            color:#151F6D;
        ">
            Página {st.session_state.pagina_viaticos} de {total_paginas}
        </div>
        """,
        unsafe_allow_html=True
    )

with p3:

    if st.button(
        "Siguiente ➡",
        disabled=(
            st.session_state.pagina_viaticos
            >= total_paginas
        ),
        use_container_width=True,
        key="next_pendientes"
    ):

        st.session_state.pagina_viaticos += 1
        st.rerun()

# =================================
# COMPROBACIONES POR VERIFICAR
# =================================

st.header("🔎 Comprobaciones por Verificar")

df_verificar = df_comprobaciones[
    df_comprobaciones["estatus"] == "Verificar"
].copy()

# =================================
# FILTERS
# =================================

filtro_col1, filtro_col2 = st.columns([2, 5])

with filtro_col1:

    folios_disponibles = ["Todos"]

    if not df_verificar.empty:

        folios_disponibles += sorted(
            df_verificar["folio_solicitud"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

    filtro_folio_verificar = st.selectbox(
        "Filtrar por Folio",
        folios_disponibles,
        key="filtro_folio_verificar"
    )

# APPLY FILTER
if filtro_folio_verificar != "Todos":

    df_verificar = df_verificar[
        df_verificar["folio_solicitud"]
        .astype(str)
        == str(filtro_folio_verificar)
    ]

# =================================
# SORT
# =================================

if "created_at" in df_verificar.columns:

    df_verificar = df_verificar.sort_values(
        by="created_at",
        ascending=False
    )

# =================================
# PAGINATION
# =================================

POSTITS_POR_PAGINA = 5

total_verificar = len(df_verificar)

total_paginas_verificar = max(
    1,
    (
        total_verificar
        + POSTITS_POR_PAGINA
        - 1
    )
    // POSTITS_POR_PAGINA
)

if "pagina_verificar" not in st.session_state:
    st.session_state.pagina_verificar = 1

pagina_actual_verificar = (
    st.session_state.pagina_verificar
)

inicio_verificar = (
    (pagina_actual_verificar - 1)
    * POSTITS_POR_PAGINA
)

fin_verificar = (
    inicio_verificar
    + POSTITS_POR_PAGINA
)

df_verificar_pagina = (
    df_verificar.iloc[
        inicio_verificar:fin_verificar
    ]
)

# =================================
# POSTITS
# =================================

if df_verificar_pagina.empty:

    st.info(
        "No hay comprobaciones pendientes por verificar."
    )

else:

    cols = st.columns(5)

    for i, (_, row) in enumerate(
        df_verificar_pagina.iterrows()
    ):

        col = cols[i % 5]

        with col:

            folio = str(
                row.get(
                    "folio_solicitud",
                    ""
                )
            )

            empleado = str(
                row.get(
                    "nombre_empleado_solicita",
                    ""
                )
            )

            fecha = str(
                row.get(
                    "created_at",
                    ""
                )
            )[:10]

            total = row.get(
                "total_comprobado",
                0
            )

            try:
                total = float(total)
            except:
                total = 0

            html = f"""
            <div style="padding:6px;">
                <div style="
                    background:#ffffff;
                    padding:14px;
                    border-radius:16px;
                    box-shadow:0 4px 10px rgba(0,0,0,0.08);
                    color:#111;
                    min-height:190px;
                    font-family:sans-serif;
                ">

                    <div style="
                        font-weight:900;
                        font-size:1rem;
                    ">
                        {folio}
                    </div>

                    <div style="
                        font-size:0.8rem;
                        margin-top:4px;
                    ">
                        {empleado}
                    </div>

                    <hr style="margin:8px 0">

                    <div style="
                        font-size:0.8rem;
                    ">
                        <b>Fecha:</b> {fecha}
                    </div>

                    <div style="
                        font-size:0.9rem;
                        margin-top:10px;
                        font-weight:700;
                        color:#151F6D;
                    ">
                        ${total:,.2f}
                    </div>

                </div>
            </div>
            """

            components.html(
                html,
                height=230
            )

            if st.button(
                "👁 Ver",
                key=f"verificar_ver_{i}",
                use_container_width=True
            ):
                #right here
                folio_actual = row.get(
                    "folio_solicitud",
                    ""
                )

                solicitud_match = df_solicitudes[
                    df_solicitudes["folio_solicitud"]
                    .astype(str)
                    ==
                    str(folio_actual)
                ]

                if not solicitud_match.empty:

                    solicitud_row = (
                        solicitud_match
                        .iloc[0]
                        .to_dict()
                    )

                else:

                    solicitud_row = {}

                comprobacion_row = row.to_dict()

                # =================================
                # MODAL
                # =================================
                @st.dialog("Detalle de Comprobación")
                def modal_verificacion():

                    # =================================
                    # INFO GENERAL
                    # =================================

                    st.markdown(
                        "<h2 style='color:#151F6D;'>📋 Información General</h2>",
                        unsafe_allow_html=True
                    )

                    col1, col2 = st.columns(2)

                    with col1:

                        st.markdown(
                            f"<span style='color:black;'><b>Folio Solicitud:</b> {solicitud_row.get('folio_solicitud', '')}</span>",
                            unsafe_allow_html=True
                        )

                        st.markdown(
                            f"<span style='color:black;'><b>Folio Comprobación:</b> {comprobacion_row.get('folio_comprobacion', '')}</span>",
                            unsafe_allow_html=True
                        )

                        st.markdown(
                            f"<span style='color:black;'><b>Estatus:</b> {comprobacion_row.get('estatus', '')}</span>",
                            unsafe_allow_html=True
                        )

                        st.markdown(
                            f"<span style='color:black;'><b>Empleado Solicita:</b> {solicitud_row.get('nombre_empleado_solicita', '')}</span>",
                            unsafe_allow_html=True
                        )

                        st.markdown(
                            f"<span style='color:black;'><b>Fecha Solicitud:</b> {solicitud_row.get('fecha_solicitud', '')}</span>",
                            unsafe_allow_html=True
                        )

                        st.markdown(
                            f"<span style='color:black;'><b>Fecha Comprobación:</b> {comprobacion_row.get('created_at', '')}</span>",
                            unsafe_allow_html=True
                        )

                        st.markdown(
                            f"<span style='color:black;'><b>Fecha Inicio:</b> {solicitud_row.get('fecha_inicio', '')}</span>",
                            unsafe_allow_html=True
                        )

                        st.markdown(
                            f"<span style='color:black;'><b>Fecha Fin:</b> {solicitud_row.get('fecha_fin', '')}</span>",
                            unsafe_allow_html=True
                        )

                    with col2:

                        st.markdown(
                            f"<span style='color:black;'><b>Empresa Brinda Servicio:</b> {solicitud_row.get('empresa_brinda_servicio', '')}</span>",
                            unsafe_allow_html=True
                        )

                        st.markdown(
                            f"<span style='color:black;'><b>Empresa Cargo Gastos:</b> {solicitud_row.get('empresa_cargo_gastos', '')}</span>",
                            unsafe_allow_html=True
                        )

                        st.markdown(
                            f"<span style='color:black;'><b>Unidad Negocio:</b> {solicitud_row.get('unidad_negocio', '')}</span>",
                            unsafe_allow_html=True
                        )

                        st.markdown(
                            f"<span style='color:black;'><b>Sucursal:</b> {solicitud_row.get('sucursal', '')}</span>",
                            unsafe_allow_html=True
                        )

                        st.markdown(
                            f"<span style='color:black;'><b>Sucursal Especificar:</b> {solicitud_row.get('sucursal_especificar', '')}</span>",
                            unsafe_allow_html=True
                        )

                        label_cliente = (
                            "Motivo del Viaje"
                            if str(
                                solicitud_row.get(
                                    "motivo_viaje",
                                    ""
                                )
                            ).strip().upper() == "OTROS"
                            else "Nombre del Cliente"
                        )

                        st.markdown(
                            f"<span style='color:black;'><b>{label_cliente}:</b> {solicitud_row.get('nombre_cliente', '')}</span>",
                            unsafe_allow_html=True
                        )

                        st.markdown(
                            f"<span style='color:black;'><b>Registro SAC Ventas?:</b> {solicitud_row.get('folio_sac', '')}</span>",
                            unsafe_allow_html=True
                        )

                    # =================================
                    # MOTIVO
                    # =================================

                    st.markdown("---")

                    st.markdown(
                        "<h2 style='color:#151F6D;'>✈️ Motivo del Viaje</h2>",
                        unsafe_allow_html=True
                    )

                    st.markdown(
                        f"""
                        <div style='
                            background-color:#F3F4F6;
                            padding:16px;
                            border-radius:12px;
                            border:1px solid rgba(191,167,95,0.25);
                            margin-bottom:20px;
                            white-space:pre-wrap;
                            color:white;
                        '>
                            {solicitud_row.get('motivo_viaje', '')}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    # =================================
                    # OBSERVACIONES
                    # =================================

                    st.markdown(
                        "<h2 style='color:#151F6D;'>📝 Observaciones Solicitud</h2>",
                        unsafe_allow_html=True
                    )

                    st.markdown(
                        f"""
                        <div style='
                            background-color:#F3F4F6;
                            padding:16px;
                            border-radius:12px;
                            border:1px solid rgba(191,167,95,0.25);
                            margin-bottom:20px;
                            white-space:pre-wrap;
                            color:white;
                        '>
                            {solicitud_row.get('observaciones', '')}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    st.markdown(
                        "<h2 style='color:#151F6D;'>👤 Empleado que metió comprobación</h2>",
                        unsafe_allow_html=True
                    )

                    st.markdown(
                        f"""
                        <div style='
                            background-color:#F3F4F6;
                            padding:16px;
                            border-radius:12px;
                            border:1px solid rgba(191,167,95,0.25);
                            margin-bottom:20px;
                            white-space:pre-wrap;
                            font-size:18px;
                            font-weight:600;
                            color:white;
                        '>
                            {comprobacion_row.get('nombre_empleado_solicita', '')}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    st.markdown(
                        "<h2 style='color:#151F6D;'>📝 Observaciones Comprobación</h2>",
                        unsafe_allow_html=True
                    )

                    st.markdown(
                        f"""
                        <div style='
                            background-color:#F3F4F6;
                            padding:16px;
                            border-radius:12px;
                            border:1px solid rgba(191,167,95,0.25);
                            margin-bottom:20px;
                            white-space:pre-wrap;
                            color:white;
                        '>
                            {comprobacion_row.get('observaciones', '')}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    # =================================
                    # CONCEPTOS COMPROBACION
                    # =================================

                    st.markdown("---")

                    st.markdown(
                        "## 🧾 Conceptos Comprobación"
                    )

                    conceptos_comprobacion = (
                        comprobacion_row.get(
                            "conceptos",
                            []
                        )
                    )

                    total_comprobado = (
                        comprobacion_row.get(
                            "total_comprobado",
                            0
                        )
                    )

                    try:
                        total_comprobado = float(
                            total_comprobado
                        )
                    except:
                        total_comprobado = 0

                    st.markdown(
                        f"""
                        <div style='
                            font-size:22px;
                            font-weight:700;
                            color:#38BDF8;
                            margin-bottom:15px;
                        '>
                            Comprobación:
                            ${total_comprobado:,.2f}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    if conceptos_comprobacion:

                        df_comp = pd.DataFrame(
                            conceptos_comprobacion
                        )

                        if "Eliminar" in df_comp.columns:

                            df_comp = df_comp.drop(
                                columns=["Eliminar"]
                            )

                        columnas_comprobacion = [

                            "Tipo",
                            "Descripcion",
                            "Fecha Factura",
                            "Folio",
                            "Proveedor",
                            "Moneda",
                            "Monto",
                            "Comprobante",
                            "Aplica IVA",
                            "IVA %",
                            "Aplica Retencion",
                            "Impuesto Acreditable",
                            "Total Comprobado"
                        ]

                        for col_name in columnas_comprobacion:

                            if col_name not in df_comp.columns:

                                df_comp[col_name] = ""

                        df_comp = df_comp[
                            columnas_comprobacion
                        ]

                        currency_columns = [
                            "Monto",
                            "Impuesto Acreditable",
                            "Total Comprobado"
                        ]

                        for col_name in currency_columns:

                            if col_name in df_comp.columns:

                                df_comp[col_name] = (
                                    pd.to_numeric(
                                        df_comp[col_name],
                                        errors="coerce"
                                    )
                                    .fillna(0)
                                    .apply(
                                        lambda x: f"${x:,.2f}"
                                    )
                                )

                        st.data_editor(
                            df_comp,
                            use_container_width=True,
                            hide_index=True,
                            disabled=True,
                            height=350
                        )

                    else:

                        st.info(
                            "No hay conceptos comprobados."
                        )

                    # =================================
                    # TOTALES COMPROBACION
                    # =================================

                    st.markdown("---")

                    total_comp = comprobacion_row.get(
                        "total_comprobado",
                        0
                    )

                    anticipo = comprobacion_row.get(
                        "anticipo_viaje",
                        0
                    )

                    diferencia = comprobacion_row.get(
                        "diferencia_cargo_favor",
                        0
                    )

                    try:
                        total_comp = float(total_comp)
                    except:
                        total_comp = 0

                    try:
                        anticipo = float(anticipo)
                    except:
                        anticipo = 0

                    try:
                        diferencia = float(diferencia)
                    except:
                        diferencia = 0

                    col_tot1, col_tot2, col_tot3 = st.columns(3)

                    with col_tot1:

                        st.markdown(
                            f"""
                            ### Total Comprobado

                            ## ${total_comp:,.2f}
                            """
                        )

                    with col_tot2:

                        st.markdown(
                            f"""
                            ### Anticipo Viaje

                            ## ${anticipo:,.2f}
                            """
                        )

                    with col_tot3:

                        st.markdown(
                            f"""
                            ### Diferencia Cargo/Favor

                            ## ${diferencia:,.2f}
                            """
                        )

                    st.markdown("---")

                    btn1, btn2 = st.columns(2)

                    with btn1:

                        if st.button(
                            "✅ Aprobar Solicitud",
                            use_container_width=True
                        ):

                            supabase.table(
                                "solicitud_viaje"
                            ).update(
                                {
                                    "estatus": "Concluido",
                                }
                            ).eq(
                                "folio_solicitud",
                                folio_actual
                            ).execute()

                            supabase.table(
                                "comprobacion_viaje"
                            ).update(
                                {
                                    "estatus": "Concluido",
                                }
                            ).eq(
                                "folio_solicitud",
                                folio_actual
                            ).execute()

                            # =================================
                            # GET CREATOR EMAIL
                            # =================================

                            correo_creador = (
                                obtener_email_usuario(
                                    solicitud_row.get(
                                        "nombre_empleado_solicita",
                                        ""
                                    )
                                )
                            )

                            destinatarios = construir_destinatarios(

                                empresa=row.get(
                                    "empresa_brinda_servicio",
                                    ""
                                ),

                                email_usuario_actual=email_usuario,

                                correo_creador=correo_creador
                            )

                            # =================================
                            # SEND EMAIL
                            # =================================

                            try:

                                enviar_correo_estatus_solicitud(

                                    destinatarios=destinatarios,

                                    folio=solicitud_row.get(
                                        "folio_solicitud",
                                        ""
                                    ),

                                    estatus="Concluido",

                                    fecha_inicio=solicitud_row.get(
                                        "fecha_inicio",
                                        ""
                                    ),

                                    fecha_fin=solicitud_row.get(
                                        "fecha_fin",
                                        ""
                                    ),

                                    motivo_viaje=solicitud_row.get(
                                        "motivo_viaje",
                                        ""
                                    ),

                                    observaciones=row.get(
                                        "observaciones",
                                        ""
                                    ),

                                    conceptos=solicitud_row.get(
                                        "conceptos",
                                        []
                                    )
                                )

                            except Exception as e:

                                st.warning(
                                    f"No se pudo enviar correo: {e}"
                                )

                            st.success(
                                "Solicitud concluida"
                            )

                            st.cache_data.clear()
                            st.rerun()

                    with btn2:

                        if st.button(
                            "❌ Rechazar Solicitud",
                            use_container_width=True
                        ):

                            supabase.table(
                                "solicitud_viaje"
                            ).update(
                                {
                                    "estatus": "Rechazado",
                                }
                            ).eq(
                                "folio_solicitud",
                                folio_actual
                            ).execute()

                            supabase.table(
                                "comprobacion_viaje"
                            ).update(
                                {
                                    "estatus": "Rechazado",
                                }
                            ).eq(
                                "folio_solicitud",
                                folio_actual
                            ).execute()

                            # =================================
                            # GET CREATOR EMAIL
                            # =================================

                            correo_creador = (
                                obtener_email_usuario(
                                    solicitud_row.get(
                                        "nombre_empleado_solicita",
                                        ""
                                    )
                                )
                            )

                            destinatarios = construir_destinatarios(

                                empresa=row.get(
                                    "empresa_brinda_servicio",
                                    ""
                                ),

                                email_usuario_actual=email_usuario,

                                correo_creador=correo_creador
                            )

                            # =================================
                            # SEND EMAIL
                            # =================================

                            try:

                                enviar_correo_estatus_solicitud(

                                    destinatarios=destinatarios,

                                    folio=solicitud_row.get(
                                        "folio_solicitud",
                                        ""
                                    ),

                                    estatus="Rechazado",

                                    fecha_inicio=solicitud_row.get(
                                        "fecha_inicio",
                                        ""
                                    ),

                                    fecha_fin=solicitud_row.get(
                                        "fecha_fin",
                                        ""
                                    ),

                                    motivo_viaje=solicitud_row.get(
                                        "motivo_viaje",
                                        ""
                                    ),

                                    observaciones=row.get(
                                        "observaciones",
                                        ""
                                    ),

                                    conceptos=solicitud_row.get(
                                        "conceptos",
                                        []
                                    )
                                )

                            except Exception as e:

                                st.warning(
                                    f"No se pudo enviar correo: {e}"
                                )

                            st.error(
                                "Solicitud rechazada"
                            )

                            st.cache_data.clear()
                            st.rerun()    


                modal_verificacion()

# =================================
# PAGINATION CONTROLS
# =================================

st.divider()

p1, p2, p3 = st.columns([1,2,1])

with p1:

    if st.button(
        "⬅ Anterior",
        disabled=(
            st.session_state.pagina_verificar <= 1
        ),
        use_container_width=True,
        key="prev_verificar"
    ):

        st.session_state.pagina_verificar -= 1
        st.rerun()

with p2:

    st.markdown(
        f"""
        <div style="
            text-align:center;
            padding-top:8px;
            font-weight:700;
            color:#151F6D;
        ">
            Página {st.session_state.pagina_verificar} de {total_paginas_verificar}
        </div>
        """,
        unsafe_allow_html=True
    )

with p3:

    if st.button(
        "Siguiente ➡",
        disabled=(
            st.session_state.pagina_verificar
            >= total_paginas_verificar
        ),
        use_container_width=True,
        key="next_verificar"
    ):

        st.session_state.pagina_verificar += 1
        st.rerun()

# =================================
# SOLICITUDES FINALIZADAS
# =================================

st.header("🏁 Solicitudes Finalizadas")

# =================================
# BASE DATA
# =================================

df_comp_final = (
    df_comprobaciones
    .sort_values(
        by="created_at",
        ascending=False
    )
    .drop_duplicates(
        subset=["folio_solicitud"]
    )
)

df_finalizadas = pd.merge(

    df_solicitudes[
        df_solicitudes["estatus"].isin(
            [
                "Concluido",
                "Rechazado"
            ]
        )
    ],

    df_comp_final[
        [
            "folio_solicitud",
            "folio_comprobacion",
            "conceptos",
            "total_comprobado",
            "anticipo_viaje",
            "diferencia_cargo_favor",
            "observaciones",
            "created_at"
        ]
    ],

    on="folio_solicitud",

    how="left",

    suffixes=(
        "_solicitud",
        ""
    )
)

# =================================
# FILTERS
# =================================

f1, f2, f3 = st.columns(3)

with f1:

    folios_finalizados = ["Todos"]

    if not df_finalizadas.empty:

        folios_finalizados += sorted(
            df_finalizadas["folio_solicitud"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

    filtro_folio_finalizado = st.selectbox(
        "Filtrar por Folio",
        folios_finalizados,
        key="filtro_folio_finalizado"
    )

with f2:

    estatus_finalizados = ["Todos"]

    if not df_finalizadas.empty:

        estatus_finalizados += sorted(
            df_finalizadas["estatus"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

    filtro_estatus_finalizado = st.selectbox(
        "Filtrar por Estatus",
        estatus_finalizados,
        key="filtro_estatus_finalizado"
    )

with f3:

    empleados_finalizados = ["Todos"]

    if not df_finalizadas.empty:

        empleados_finalizados += sorted(
            df_finalizadas["nombre_empleado_solicita"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

    filtro_empleado_finalizado = st.selectbox(
        "Filtrar por Empleado",
        empleados_finalizados,
        key="filtro_empleado_finalizado"
    )

# =================================
# APPLY FILTERS
# =================================

if filtro_folio_finalizado != "Todos":

    df_finalizadas = df_finalizadas[
        df_finalizadas["folio_solicitud"]
        .astype(str)
        ==
        str(filtro_folio_finalizado)
    ]

if filtro_estatus_finalizado != "Todos":

    df_finalizadas = df_finalizadas[
        df_finalizadas["estatus"]
        .astype(str)
        ==
        str(filtro_estatus_finalizado)
    ]

if filtro_empleado_finalizado != "Todos":

    df_finalizadas = df_finalizadas[
        df_finalizadas["nombre_empleado_solicita"]
        .astype(str)
        ==
        str(filtro_empleado_finalizado)
    ]

# =================================
# SORT
# =================================

if "created_at" in df_finalizadas.columns:

    df_finalizadas = df_finalizadas.sort_values(
        by="created_at",
        ascending=False
    )

# =================================
# DESCARGAR REPORTE
# =================================

reporte_rows = []

for _, row in df_finalizadas.iterrows():

    solicitud_match = df_solicitudes[
        df_solicitudes["folio_solicitud"]
        .astype(str)
        ==
        str(row.get("folio_solicitud", ""))
    ]

    if not solicitud_match.empty:

        solicitud_row = (
            solicitud_match
            .iloc[0]
            .to_dict()
        )

    else:

        solicitud_row = {}

    # =================================
    # CONCEPTOS SOLICITUD
    # =================================

    conceptos_solicitud = solicitud_row.get("conceptos")

    if not isinstance(conceptos_solicitud, list):
        conceptos_solicitud = []

    if len(conceptos_solicitud) == 0:
        conceptos_solicitud = [{}]

    # =================================
    # CONCEPTOS COMPROBACION
    # =================================

    conceptos_comprobacion = row.get("conceptos")

    if not isinstance(conceptos_comprobacion, list):
        conceptos_comprobacion = []

    if len(conceptos_comprobacion) == 0:
        conceptos_comprobacion = [{}]

    max_len = max(
        len(conceptos_solicitud),
        len(conceptos_comprobacion)
    )

    for i in range(max_len):

        concepto_sol = (
            conceptos_solicitud[i]
            if i < len(conceptos_solicitud)
            else {}
        )

        concepto_comp = (
            conceptos_comprobacion[i]
            if i < len(conceptos_comprobacion)
            else {}
        )

        reporte_rows.append({

            # =================================
            # GENERAL
            # =================================

            "Folio Solicitud":
                solicitud_row.get(
                    "folio_solicitud",
                    ""
                ),

            "Folio Comprobacion":
                row.get(
                    "folio_comprobacion",
                    ""
                ),

            "Estatus":
                row.get(
                    "estatus",
                    ""
                ),

            "Empleado Solicita":
                solicitud_row.get(
                    "nombre_empleado_solicita",
                    ""
                ),

            "Fecha Solicitud":
                solicitud_row.get(
                    "fecha_solicitud",
                    ""
                ),

            "Fecha Comprobacion":
                row.get(
                    "created_at",
                    ""
                ),

            "Fecha Inicio":
                solicitud_row.get(
                    "fecha_inicio",
                    ""
                ),

            "Fecha Fin":
                solicitud_row.get(
                    "fecha_fin",
                    ""
                ),

            "Empresa Brinda Servicio":
                solicitud_row.get(
                    "empresa_brinda_servicio",
                    ""
                ),

            "Empresa Cargo Gastos":
                solicitud_row.get(
                    "empresa_cargo_gastos",
                    ""
                ),

            "Unidad Negocio":
                solicitud_row.get(
                    "unidad_negocio",
                    ""
                ),

            "Sucursal":
                solicitud_row.get(
                    "sucursal",
                    ""
                ),

            "Sucursal Especificar":
                solicitud_row.get(
                    "sucursal_especificar",
                    ""
                ),

            "Nombre Cliente":
                solicitud_row.get(
                    "nombre_cliente",
                    ""
                ),

            "Registro SAC Ventas":
                solicitud_row.get(
                    "folio_sac",
                    ""
                ),

            "Motivo Viaje":
                solicitud_row.get(
                    "motivo_viaje",
                    ""
                ),

            "Observaciones Solicitud":
                solicitud_row.get(
                    "observaciones",
                    ""
                ),

            "Observaciones Comprobacion":
                row.get(
                    "observaciones",
                    ""
                ),

            # =================================
            # TOTALES
            # =================================

            "Monto Solicitado":
                solicitud_row.get(
                    "total_estimado",
                    0
                ),

            "Total Comprobado":
                row.get(
                    "total_comprobado",
                    0
                ),

            "Anticipo Viaje":
                row.get(
                    "anticipo_viaje",
                    0
                ),

            "Diferencia Cargo Favor":
                row.get(
                    "diferencia_cargo_favor",
                    0
                ),

            # =================================
            # CONCEPTOS SOLICITUD
            # =================================

            "Solicitud Tipo":
                concepto_sol.get(
                    "Tipo",
                    ""
                ),

            "Solicitud Descripcion":
                concepto_sol.get(
                    "Descripcion",
                    ""
                ),

            "Solicitud Monto":
                concepto_sol.get(
                    "Monto",
                    ""
                ),

            "Solicitud Tipo Cambio":
                concepto_sol.get(
                    "Tipo Cambio",
                    ""
                ),

            "Solicitud Aprobado":
                concepto_sol.get(
                    "Aprobado",
                    ""
                ),

            "Solicitud Razon":
                concepto_sol.get(
                    "Razon",
                    ""
                ),

            # =================================
            # CONCEPTOS COMPROBACION
            # =================================

            "Comprobacion Tipo":
                concepto_comp.get(
                    "Tipo",
                    ""
                ),

            "Comprobacion Descripcion":
                concepto_comp.get(
                    "Descripcion",
                    ""
                ),

            "Comprobacion Fecha Factura":
                concepto_comp.get(
                    "Fecha Factura",
                    ""
                ),

            "Comprobacion Folio":
                concepto_comp.get(
                    "Folio",
                    ""
                ),

            "Comprobacion Proveedor":
                concepto_comp.get(
                    "Proveedor",
                    ""
                ),

            "Comprobacion Moneda":
                concepto_comp.get(
                    "Moneda",
                    ""
                ),

            "Comprobacion Monto":
                concepto_comp.get(
                    "Monto",
                    ""
                ),

            "Comprobacion Comprobante":
                concepto_comp.get(
                    "Comprobante",
                    ""
                ),

            "Comprobacion Aplica IVA":
                concepto_comp.get(
                    "Aplica IVA",
                    ""
                ),

            "Comprobacion IVA %":
                concepto_comp.get(
                    "IVA %",
                    ""
                ),

            "Comprobacion Aplica Retencion":
                concepto_comp.get(
                    "Aplica Retencion",
                    ""
                ),

            "Comprobacion Impuesto Acreditable":
                concepto_comp.get(
                    "Impuesto Acreditable",
                    ""
                ),

            "Comprobacion Total Comprobado":
                concepto_comp.get(
                    "Total Comprobado",
                    ""
                )
        })

df_reporte = pd.DataFrame(
    reporte_rows
)

output = BytesIO()

with pd.ExcelWriter(
    output,
    engine="openpyxl"
) as writer:

    df_reporte.to_excel(
        writer,
        index=False,
        sheet_name="Solicitudes"
    )

output.seek(0)

st.download_button(
    label="📥 Descargar reporte de Solicitudes",
    data=output.getvalue(),
    file_name="Reporte_Solicitudes_Finalizadas.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=False,
    key="descargar_reporte_final"
)

# =================================
# PAGINATION
# =================================

FINALIZADAS_POR_PAGINA = 5

total_finalizadas = len(df_finalizadas)

total_paginas_finalizadas = max(
    1,
    (
        total_finalizadas
        + FINALIZADAS_POR_PAGINA
        - 1
    )
    // FINALIZADAS_POR_PAGINA
)

if "pagina_finalizadas" not in st.session_state:

    st.session_state.pagina_finalizadas = 1

pagina_actual_finalizadas = (
    st.session_state.pagina_finalizadas
)

inicio_finalizadas = (
    (pagina_actual_finalizadas - 1)
    * FINALIZADAS_POR_PAGINA
)

fin_finalizadas = (
    inicio_finalizadas
    + FINALIZADAS_POR_PAGINA
)

df_finalizadas_pagina = (
    df_finalizadas.iloc[
        inicio_finalizadas:fin_finalizadas
    ]
)

# =================================
# POSTITS
# =================================

if df_finalizadas_pagina.empty:

    st.info(
        "No hay solicitudes finalizadas."
    )

else:

    cols = st.columns(5)

    for i, (_, row) in enumerate(
        df_finalizadas_pagina.iterrows()
    ):

        col = cols[i % 5]

        with col:

            folio = str(
                row.get(
                    "folio_solicitud",
                    ""
                )
            )

            empleado = str(
                row.get(
                    "nombre_empleado_solicita",
                    ""
                )
            )

            fecha = str(
                row.get(
                    "created_at",
                    ""
                )
            )[:10]

            total = row.get(
                "total_comprobado",
                0
            )

            try:
                total = float(total)
            except:
                total = 0

            estatus = str(
                row.get(
                    "estatus",
                    ""
                )
            )

            html = f"""
            <div style="padding:6px;">
                <div style="
                    background:#ffffff;
                    padding:14px;
                    border-radius:16px;
                    box-shadow:0 4px 10px rgba(0,0,0,0.08);
                    color:#111;
                    min-height:190px;
                    font-family:sans-serif;
                ">

                    <div style="
                        font-weight:900;
                        font-size:1rem;
                    ">
                        {folio}
                    </div>

                    <div style="
                        font-size:0.8rem;
                        margin-top:4px;
                    ">
                        {empleado}
                    </div>

                    <hr style="margin:8px 0">

                    <div style="
                        font-size:0.8rem;
                    ">
                        <b>Fecha:</b> {fecha}
                    </div>

                    <div style="
                        font-size:0.8rem;
                        margin-top:6px;
                    ">
                        <b>Estatus:</b> {estatus}
                    </div>

                    <div style="
                        font-size:0.9rem;
                        margin-top:10px;
                        font-weight:700;
                        color:#151F6D;
                    ">
                        ${total:,.2f}
                    </div>

                </div>
            </div>
            """

            components.html(
                html,
                height=230
            )

            if st.button(
                "👁 Ver",
                key=f"finalizada_ver_{i}",
                use_container_width=True
            ):

                folio_actual = row.get(
                    "folio_solicitud",
                    ""
                )

                solicitud_match = df_solicitudes[
                    df_solicitudes["folio_solicitud"]
                    .astype(str)
                    ==
                    str(folio_actual)
                ]

                if not solicitud_match.empty:

                    solicitud_row = (
                        solicitud_match
                        .iloc[0]
                        .to_dict()
                    )

                else:

                    solicitud_row = {}

                # =================================
                # MODAL
                # =================================
                @st.dialog("Detalle de Comprobación")
                def modal_verificacion_finalizada():

                    # =================================
                    # INFO GENERAL
                    # =================================

                    st.markdown(
                        "<h2 style='color:#151F6D;'>📋 Información General</h2>",
                        unsafe_allow_html=True
                    )

                    col1, col2 = st.columns(2)

                    with col1:

                        st.markdown(
                            f"<span style='color:black;'><b>Folio Solicitud:</b> {solicitud_row.get('folio_solicitud', '')}</span>",
                            unsafe_allow_html=True
                        )

                        st.markdown(
                            f"<span style='color:black;'><b>Folio Comprobación:</b> {row.get('folio_comprobacion', '')}</span>",
                            unsafe_allow_html=True
                        )

                        st.markdown(
                            f"<span style='color:black;'><b>Estatus:</b> {row.get('estatus', '')}</span>",
                            unsafe_allow_html=True
                        )

                        st.markdown(
                            f"<span style='color:black;'><b>Empleado Solicita:</b> {solicitud_row.get('nombre_empleado_solicita', '')}</span>",
                            unsafe_allow_html=True
                        )

                        st.markdown(
                            f"<span style='color:black;'><b>Fecha Solicitud:</b> {solicitud_row.get('fecha_solicitud', '')}</span>",
                            unsafe_allow_html=True
                        )

                        st.markdown(
                            f"<span style='color:black;'><b>Fecha Comprobación:</b> {row.get('created_at', '')}</span>",
                            unsafe_allow_html=True
                        )

                        st.markdown(
                            f"<span style='color:black;'><b>Fecha Inicio:</b> {solicitud_row.get('fecha_inicio', '')}</span>",
                            unsafe_allow_html=True
                        )

                        st.markdown(
                            f"<span style='color:black;'><b>Fecha Fin:</b> {solicitud_row.get('fecha_fin', '')}</span>",
                            unsafe_allow_html=True
                        )

                    with col2:

                        st.markdown(
                            f"<span style='color:black;'><b>Empresa Brinda Servicio:</b> {solicitud_row.get('empresa_brinda_servicio', '')}</span>",
                            unsafe_allow_html=True
                        )

                        st.markdown(
                            f"<span style='color:black;'><b>Empresa Cargo Gastos:</b> {solicitud_row.get('empresa_cargo_gastos', '')}</span>",
                            unsafe_allow_html=True
                        )

                        st.markdown(
                            f"<span style='color:black;'><b>Unidad Negocio:</b> {solicitud_row.get('unidad_negocio', '')}</span>",
                            unsafe_allow_html=True
                        )

                        st.markdown(
                            f"<span style='color:black;'><b>Sucursal:</b> {solicitud_row.get('sucursal', '')}</span>",
                            unsafe_allow_html=True
                        )

                        st.markdown(
                            f"<span style='color:black;'><b>Sucursal Especificar:</b> {solicitud_row.get('sucursal_especificar', '')}</span>",
                            unsafe_allow_html=True
                        )

                        label_cliente = (
                            "Motivo del Viaje"
                            if str(
                                solicitud_row.get(
                                    "motivo_viaje",
                                    ""
                                )
                            ).strip().upper() == "OTROS"
                            else "Nombre del Cliente"
                        )

                        st.markdown(
                            f"<span style='color:black;'><b>{label_cliente}:</b> {solicitud_row.get('nombre_cliente', '')}</span>",
                            unsafe_allow_html=True
                        )

                        st.markdown(
                            f"<span style='color:black;'><b>Registro SAC Ventas?:</b> {solicitud_row.get('folio_sac', '')}</span>",
                            unsafe_allow_html=True
                        )

                    # =================================
                    # MOTIVO
                    # =================================

                    st.markdown("---")

                    st.markdown(
                        "## ✈️ Motivo del Viaje"
                    )

                    st.markdown(
                        f"""
                        <div style='
                            background-color:#F3F4F6;
                            padding:16px;
                            border-radius:12px;
                            border:1px solid rgba(191,167,95,0.25);
                            margin-bottom:20px;
                            white-space:pre-wrap;
                        '>
                            {solicitud_row.get('motivo_viaje', '')}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    # =================================
                    # OBSERVACIONES
                    # =================================

                    st.markdown(
                        "## 📝 Observaciones Solicitud"
                    )

                    st.markdown(
                        f"""
                        <div style='
                            background-color:#F3F4F6;
                            padding:16px;
                            border-radius:12px;
                            border:1px solid rgba(191,167,95,0.25);
                            margin-bottom:20px;
                            white-space:pre-wrap;
                        '>
                            {solicitud_row.get('observaciones', '')}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    st.markdown(
                        "## 👤 Empleado que metió comprobación"
                    )

                    st.markdown(
                        f"""
                        <div style='
                            background-color:#F3F4F6;
                            padding:16px;
                            border-radius:12px;
                            border:1px solid rgba(191,167,95,0.25);
                            margin-bottom:20px;
                            white-space:pre-wrap;
                            font-size:18px;
                            font-weight:600;
                        '>
                            {row.get('nombre_empleado_solicita', '')}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    st.markdown(
                        "## 📝 Observaciones Comprobación"
                    )

                    st.markdown(
                        f"""
                        <div style='
                            background-color:#F3F4F6;
                            padding:16px;
                            border-radius:12px;
                            border:1px solid rgba(191,167,95,0.25);
                            margin-bottom:20px;
                            white-space:pre-wrap;
                        '>
                            {row.get('observaciones', '')}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    # =================================
                    # MONTO SOLICITADO
                    # =================================
                    # =================================
                    # MONTO SOLICITADO
                    # =================================

                    st.markdown("---")

                    conceptos_solicitud = (
                        solicitud_row.get(
                            "conceptos",
                            []
                        )
                    )

                    monto_solicitado = 0.0

                    for item in conceptos_solicitud:

                        try:

                            monto_solicitado += float(
                                item.get(
                                    "Monto",
                                    0
                                ) or 0
                            )

                        except:

                            pass

                    st.markdown(
                        f"""
                        <div style='
                            font-size:26px;
                            font-weight:800;
                            color:#BFA75F;
                            margin-top:10px;
                            margin-bottom:10px;
                        '>
                            Monto Solicitado:
                            ${monto_solicitado:,.2f}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    st.markdown(
                        "<h3 style='color:black;'>👁 Ver Detalles Solicitud</h3>",
                        unsafe_allow_html=True
                    )

                    with st.expander(
                        "",
                        expanded=False
                    ):

                        if conceptos_solicitud:

                            df_sol = pd.DataFrame(
                                conceptos_solicitud
                            )

                            columnas_solicitud = [
                                "Tipo",
                                "Descripcion",
                                "Monto",
                                "Tipo Cambio",
                                "Aprobado",
                                "Razon"
                            ]

                            for col_name in columnas_solicitud:

                                if col_name not in df_sol.columns:

                                    df_sol[col_name] = ""

                            df_sol = df_sol[
                                columnas_solicitud
                            ]

                            if "Monto" in df_sol.columns:

                                df_sol["Monto"] = (
                                    pd.to_numeric(
                                        df_sol["Monto"],
                                        errors="coerce"
                                    )
                                    .fillna(0)
                                    .apply(
                                        lambda x:
                                        f"${x:,.2f}"
                                    )
                                )

                            st.data_editor(
                                df_sol,
                                use_container_width=True,
                                hide_index=True,
                                disabled=True,
                                height=350
                            )

                        else:

                            st.info(
                                "No hay conceptos."
                            )

                    # =================================
                    # CONCEPTOS COMPROBACION
                    # =================================

                    st.markdown("---")

                    st.markdown(
                        "## 🧾 Conceptos Comprobación"
                    )

                    conceptos_comprobacion = (
                        row.get(
                            "conceptos",
                            []
                        )
                    )

                    total_comprobado = (
                        row.get(
                            "total_comprobado",
                            0
                        )
                    )

                    try:
                        total_comprobado = float(
                            total_comprobado
                        )
                    except:
                        total_comprobado = 0

                    st.markdown(
                        f"""
                        <div style='
                            font-size:22px;
                            font-weight:700;
                            color:#38BDF8;
                            margin-bottom:15px;
                        '>
                            Comprobación:
                            ${total_comprobado:,.2f}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    if conceptos_comprobacion:

                        df_comp = pd.DataFrame(
                            conceptos_comprobacion
                        )

                        if "Eliminar" in df_comp.columns:

                            df_comp = df_comp.drop(
                                columns=["Eliminar"]
                            )

                        columnas_comprobacion = [

                            "Tipo",

                            "Descripcion",

                            "Fecha Factura",

                            "Folio",

                            "Proveedor",

                            "Moneda",

                            "Monto",

                            "Comprobante",

                            "Aplica IVA",

                            "IVA %",

                            "Aplica Retencion",

                            "Impuesto Acreditable",

                            "Total Comprobado"
                        ]

                        for col_name in columnas_comprobacion:

                            if col_name not in df_comp.columns:

                                df_comp[col_name] = ""

                        df_comp = df_comp[
                            columnas_comprobacion
                        ]

                        currency_columns = [
                            "Monto",
                            "Impuesto Acreditable",
                            "Total Comprobado"
                        ]

                        for col_name in currency_columns:

                            if col_name in df_comp.columns:

                                df_comp[col_name] = (
                                    pd.to_numeric(
                                        df_comp[col_name],
                                        errors="coerce"
                                    )
                                    .fillna(0)
                                    .apply(
                                        lambda x:
                                        f"${x:,.2f}"
                                    )
                                )

                        st.data_editor(
                            df_comp,
                            use_container_width=True,
                            hide_index=True,
                            disabled=True,
                            height=350
                        )

                    else:

                        st.info(
                            "No hay conceptos comprobados."
                        )
                    # =================================
                    # TOTALES COMPROBACION
                    # =================================

                    st.markdown("---")

                    total_comp = row.get(
                        "total_comprobado",
                        0
                    )

                    anticipo = row.get(
                        "anticipo_viaje",
                        0
                    )

                    diferencia = row.get(
                        "diferencia_cargo_favor",
                        0
                    )

                    try:
                        total_comp = float(total_comp)
                    except:
                        total_comp = 0

                    try:
                        anticipo = float(anticipo)
                    except:
                        anticipo = 0

                    try:
                        diferencia = float(diferencia)
                    except:
                        diferencia = 0

                    col_tot1, col_tot2, col_tot3 = st.columns(3)

                    with col_tot1:

                        st.markdown(
                            f"""
                            ### Total Comprobado

                            ## ${total_comp:,.2f}
                            """
                        )

                    with col_tot2:

                        st.markdown(
                            f"""
                            ### Anticipo Viaje

                            ## ${anticipo:,.2f}
                            """
                        )

                    with col_tot3:

                        st.markdown(
                            f"""
                            ### Diferencia Cargo/Favor

                            ## ${diferencia:,.2f}
                            """
                        )

                modal_verificacion_finalizada()
                
# =================================
# PAGINATION CONTROLS
# =================================

st.divider()

p1, p2, p3 = st.columns([1,2,1])

with p1:

    if st.button(
        "⬅ Anterior",
        disabled=(
            st.session_state.pagina_finalizadas <= 1
        ),
        use_container_width=True,
        key="prev_finalizadas"
    ):

        st.session_state.pagina_finalizadas -= 1
        st.rerun()

with p2:

    st.markdown(
        f"""
        <div style="
            text-align:center;
            padding-top:8px;
            font-weight:700;
            color:#151F6D;
        ">
            Página {st.session_state.pagina_finalizadas} de {total_paginas_finalizadas}
        </div>
        """,
        unsafe_allow_html=True
    )

with p3:

    if st.button(
        "Siguiente ➡",
        disabled=(
            st.session_state.pagina_finalizadas
            >= total_paginas_finalizadas
        ),
        use_container_width=True,
        key="next_finalizadas"
    ):

        st.session_state.pagina_finalizadas += 1
        st.rerun()