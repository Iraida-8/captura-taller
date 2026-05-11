import streamlit as st
import streamlit.components.v1 as components
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
    page_title="Gestión de Viáticos",
    layout="wide"
)

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
# LOAD DATA
# =================================

@st.cache_data(ttl=30)
def cargar_solicitudes():

    response = (
        supabase
        .table("solicitud_viaje")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )

    return pd.DataFrame(response.data)

@st.cache_data(ttl=30)
def cargar_comprobaciones():

    response = (
        supabase
        .table("comprobacion_viaje")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )

    return pd.DataFrame(response.data)

df_solicitudes = cargar_solicitudes()
df_comprobaciones = cargar_comprobaciones()

# =================================
# Top navigation
# =================================
if st.button("⬅ Volver al Dashboard"):
    st.switch_page("pages/dashboard.py")

st.divider()

# =================================
# KPI VALUES
# =================================

# Normalize estatus columns

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

# TOTAL
# Only solicitud_viaje
total_registros = len(df_solicitudes)

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
    df_comprobaciones[
        df_comprobaciones["estatus"] == "Verificar"
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

concluidos_ids = set()

# solicitud_viaje
solicitudes_concluidas = df_solicitudes[
    df_solicitudes["estatus"] == "Concluido"
]

if "id" in solicitudes_concluidas.columns:

    concluidos_ids.update(
        solicitudes_concluidas["id"]
        .astype(str)
        .str.strip()
        .tolist()
    )

# comprobacion_viaje
comprobaciones_concluidas = df_comprobaciones[
    df_comprobaciones["estatus"] == "Concluido"
]

if "id" in comprobaciones_concluidas.columns:

    concluidos_ids.update(
        comprobaciones_concluidas["id"]
        .astype(str)
        .str.strip()
        .tolist()
    )

concluidos = len(concluidos_ids)

# =================================
# HEADER
# =================================

st.markdown(
    """
    <div style="
        font-size:48px;
        font-weight:800;
        color:white;
        margin-bottom:10px;
    ">
        ⚙ Gestión de Viáticos
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown("<br>", unsafe_allow_html=True)

# =================================
# KPI CARDS
# =================================

kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)

def render_kpi_card(
    title,
    value,
    emoji,
    border_color
):

    with st.container(border=True):

        st.markdown(
            f"""
            #### {emoji} {title}
            """,
            unsafe_allow_html=False
        )

        st.markdown(
            f"""
            <div style='
                color:{border_color};
                font-size:58px;
                font-weight:800;
                line-height:1;
                margin-top:10px;
            '>
                {value}
            </div>
            """,
            unsafe_allow_html=True
        )

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

st.markdown(
    """
    <h2 style='margin-bottom:20px;'>
        📋 Solicitudes Pendientes
    </h2>
    """,
    unsafe_allow_html=True
)

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

    st.markdown("## 📋 Información General")

    col1, col2 = st.columns(2)

    with col1:

        st.write(
            f"**Folio:** {row.get('folio_solicitud', '')}"
        )

        st.write(
            f"**Estatus:** {row.get('estatus', '')}"
        )

        st.write(
            f"**Empresa Brinda Servicio:** {row.get('empresa_brinda_servicio', '')}"
        )

        st.write(
            f"**Empleado Solicita:** {row.get('nombre_empleado_solicita', '')}"
        )

        st.write(
            f"**Fecha Solicitud:** {row.get('fecha_solicitud', '')}"
        )

        st.write(
            f"**Fecha Inicio:** {row.get('fecha_inicio', '')}"
        )

        st.write(
            f"**Fecha Fin:** {row.get('fecha_fin', '')}"
        )

    with col2:

        st.write(
            f"**Empresa Cargo Gastos:** {row.get('empresa_cargo_gastos', '')}"
        )

        st.write(
            f"**Unidad Negocio:** {row.get('unidad_negocio', '')}"
        )

        st.write(
            f"**Sucursal:** {row.get('sucursal', '')}"
        )

        st.write(
            f"**Sucursal Especificar:** {row.get('sucursal_especificar', '')}"
        )

    # =================================
    # MOTIVO VIAJE
    # =================================

    st.markdown("---")

    st.markdown("## ✈️ Motivo del Viaje")

    st.markdown(
        f"""
        <div style='
            background-color:#1B267A;
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

    st.markdown("## 📝 Observaciones")

    st.markdown(
        f"""
        <div style='
            background-color:#1B267A;
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
    # CONCEPTOS
    # =================================

    st.markdown("---")

    st.markdown("## 💰 Conceptos")

    total_value = row.get("total_estimado", 0)

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

    conceptos = row.get("conceptos", [])

    if conceptos:

        try:

            df_conceptos = pd.DataFrame(conceptos)

            columnas_mostrar = []

            if "Tipo" in df_conceptos.columns:
                columnas_mostrar.append("Tipo")

            if "Descripcion" in df_conceptos.columns:
                columnas_mostrar.append("Descripcion")

            if "Monto" in df_conceptos.columns:

                df_conceptos["Monto"] = (
                    pd.to_numeric(
                        df_conceptos["Monto"],
                        errors="coerce"
                    )
                    .fillna(0)
                    .apply(
                        lambda x: f"${x:,.2f}"
                    )
                )

                columnas_mostrar.append("Monto")

            df_conceptos = df_conceptos[columnas_mostrar]

            st.dataframe(
                df_conceptos,
                use_container_width=True,
                hide_index=True
            )

        except Exception as e:

            st.error(
                f"Error leyendo conceptos: {e}"
            )

    else:

        st.info("No hay conceptos registrados.")

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

            st.markdown(
                f"""
                <div style='font-size:13px;color:#BFA75F;'>
                    Folio
                </div>

                <div style='font-size:18px;font-weight:700;'>
                    {row.get("folio_solicitud", "")}
                </div>
                """,
                unsafe_allow_html=True
            )

        # EMPLEADO
        with col3:

            st.markdown(
                f"""
                <div style='font-size:13px;color:#BFA75F;'>
                    Empleado
                </div>

                <div style='font-size:18px;font-weight:700;'>
                    {row.get("nombre_empleado_solicita", "")}
                </div>
                """,
                unsafe_allow_html=True
            )

        # FECHA
        with col4:

            st.markdown(
                f"""
                <div style='font-size:13px;color:#BFA75F;'>
                    Fecha Solicitud
                </div>

                <div style='font-size:18px;font-weight:700;'>
                    {row.get("fecha_solicitud", "")}
                </div>
                """,
                unsafe_allow_html=True
            )

        # TOTAL
        with col5:

            total_value = row.get("total_estimado", 0)

            try:
                total_value = float(total_value)
            except:
                total_value = 0

            st.markdown(
                f"""
                <div style='font-size:13px;color:#BFA75F;'>
                    Total
                </div>

                <div style='font-size:18px;font-weight:700;'>
                    ${total_value:,.2f}
                </div>
                """,
                unsafe_allow_html=True
            )

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

                st.error("Solicitud rechazada")
                st.cache_data.clear()
                st.rerun()

# =================================
# PAGINATION BUTTONS
# =================================

st.markdown("<br>", unsafe_allow_html=True)

cols_paginas = st.columns(total_paginas)

for i in range(total_paginas):

    pagina_num = i + 1

    with cols_paginas[i]:

        if st.button(
            str(pagina_num),
            key=f"pagina_{pagina_num}",
        ):

            st.session_state.pagina_viaticos = pagina_num
            st.rerun()

# =================================
# COMPROBACIONES POR VERIFICAR
# =================================

st.markdown(
    """
    <h2 style='margin-bottom:20px;'>
        🔎 Comprobaciones por Verificar
    </h2>
    """,
    unsafe_allow_html=True
)

# =================================
# BASE DATA
# =================================

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

                @st.dialog("Detalle de Comprobación")
                def modal_verificacion():

                    # =================================
                    # INFO GENERAL
                    # =================================

                    st.markdown(
                        "## 📋 Información General"
                    )

                    col1, col2 = st.columns(2)

                    with col1:

                        st.write(
                            f"**Folio Solicitud:** "
                            f"{solicitud_row.get('folio_solicitud', '')}"
                        )

                        st.write(
                            f"**Folio Comprobación:** "
                            f"{row.get('folio_comprobacion', '')}"
                        )

                        st.write(
                            f"**Estatus:** "
                            f"{row.get('estatus', '')}"
                        )

                        st.write(
                            f"**Empleado Solicita:** "
                            f"{solicitud_row.get('nombre_empleado_solicita', '')}"
                        )

                        st.write(
                            f"**Fecha Solicitud:** "
                            f"{solicitud_row.get('fecha_solicitud', '')}"
                        )

                        st.write(
                            f"**Fecha Comprobación:** "
                            f"{row.get('created_at', '')}"
                        )

                        st.write(
                            f"**Fecha Inicio:** "
                            f"{solicitud_row.get('fecha_inicio', '')}"
                        )

                        st.write(
                            f"**Fecha Fin:** "
                            f"{solicitud_row.get('fecha_fin', '')}"
                        )

                    with col2:

                        st.write(
                            f"**Empresa Brinda Servicio:** "
                            f"{solicitud_row.get('empresa_brinda_servicio', '')}"
                        )

                        st.write(
                            f"**Empresa Cargo Gastos:** "
                            f"{solicitud_row.get('empresa_cargo_gastos', '')}"
                        )

                        st.write(
                            f"**Unidad Negocio:** "
                            f"{solicitud_row.get('unidad_negocio', '')}"
                        )

                        st.write(
                            f"**Sucursal:** "
                            f"{solicitud_row.get('sucursal', '')}"
                        )

                        st.write(
                            f"**Sucursal Especificar:** "
                            f"{solicitud_row.get('sucursal_especificar', '')}"
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
                            background-color:#1B267A;
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
                            background-color:#1B267A;
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
                            background-color:#1B267A;
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
                            background-color:#1B267A;
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
                    # CONCEPTOS
                    # =================================

                    st.markdown("---")

                    st.markdown(
                        "## 💰 Conceptos"
                    )

                    conceptos_solicitud = (
                        solicitud_row.get(
                            "conceptos",
                            []
                        )
                    )

                    conceptos_comprobacion = (
                        row.get(
                            "conceptos",
                            []
                        )
                    )

                    col_sol, col_comp = st.columns(2)

                    # =================================
                    # SOLICITUD
                    # =================================

                    with col_sol:

                        total_estimado = (
                            solicitud_row.get(
                                "total_estimado",
                                0
                            )
                        )

                        try:
                            total_estimado = (
                                float(total_estimado)
                            )
                        except:
                            total_estimado = 0

                        st.markdown(
                            f"""
                            <div style='
                                font-size:22px;
                                font-weight:700;
                                color:#BFA75F;
                                margin-bottom:15px;
                            '>
                                Solicitud:
                                ${total_estimado:,.2f}
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                        if conceptos_solicitud:

                            df_sol = pd.DataFrame(
                                conceptos_solicitud
                            )

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

                            edited_sol = st.data_editor(
                                df_sol,
                                use_container_width=True,
                                hide_index=True,
                                num_rows="dynamic"
                            )

                    # =================================
                    # COMPROBACION
                    # =================================

                    with col_comp:

                        total_comprobado = (
                            row.get(
                                "total_comprobado",
                                0
                            )
                        )

                        try:
                            total_comprobado = (
                                float(total_comprobado)
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

                            currency_columns = [
                                "Total Comprobado",
                                "Impuesto Acreditable",
                                "Gastos con Comprobante",
                                "Gastos sin Comprobante"
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

                            edited_comp = st.data_editor(
                                df_comp,
                                use_container_width=True,
                                hide_index=True,
                                num_rows="dynamic"
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
                                    "conceptos": edited_sol.to_dict(
                                        orient="records"
                                    )
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
                                    "conceptos": edited_comp.to_dict(
                                        orient="records"
                                    )
                                }
                            ).eq(
                                "folio_solicitud",
                                folio_actual
                            ).execute()

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
                                    "conceptos": edited_sol.to_dict(
                                        orient="records"
                                    )
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
                                    "conceptos": edited_comp.to_dict(
                                        orient="records"
                                    )
                                }
                            ).eq(
                                "folio_solicitud",
                                folio_actual
                            ).execute()

                            st.error(
                                "Solicitud rechazada"
                            )

                            st.cache_data.clear()
                            st.rerun()     


                modal_verificacion()

# =================================
# PAGE BUTTONS
# =================================

st.markdown("<br>", unsafe_allow_html=True)

cols_paginas_verificar = st.columns(
    total_paginas_verificar
)

for i in range(total_paginas_verificar):

    pagina_num = i + 1

    with cols_paginas_verificar[i]:

        if st.button(
            str(pagina_num),
            key=f"pagina_verificar_{pagina_num}",
        ):

            st.session_state.pagina_verificar = (
                pagina_num
            )

            st.rerun()

# =================================
# SOLICITUDES FINALIZADAS
# =================================

st.markdown("<br><br>", unsafe_allow_html=True)

st.markdown(
    """
    <h2 style='margin-bottom:20px;'>
        🏁 Solicitudes Finalizadas
    </h2>
    """,
    unsafe_allow_html=True
)

# =================================
# BASE DATA
# =================================

df_finalizadas = df_comprobaciones[
    df_comprobaciones["estatus"].isin(
        [
            "Concluido",
            "Rechazado"
        ]
    )
].copy()

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

                @st.dialog("Detalle de Comprobación")
                def modal_verificacion_finalizada():

                    # =================================
                    # INFO GENERAL
                    # =================================

                    st.markdown(
                        "## 📋 Información General"
                    )

                    col1, col2 = st.columns(2)

                    with col1:

                        st.write(
                            f"**Folio Solicitud:** "
                            f"{solicitud_row.get('folio_solicitud', '')}"
                        )

                        st.write(
                            f"**Folio Comprobación:** "
                            f"{row.get('folio_comprobacion', '')}"
                        )

                        st.write(
                            f"**Estatus:** "
                            f"{row.get('estatus', '')}"
                        )

                        st.write(
                            f"**Empleado Solicita:** "
                            f"{solicitud_row.get('nombre_empleado_solicita', '')}"
                        )

                        st.write(
                            f"**Fecha Solicitud:** "
                            f"{solicitud_row.get('fecha_solicitud', '')}"
                        )

                        st.write(
                            f"**Fecha Comprobación:** "
                            f"{row.get('created_at', '')}"
                        )

                        st.write(
                            f"**Fecha Inicio:** "
                            f"{solicitud_row.get('fecha_inicio', '')}"
                        )

                        st.write(
                            f"**Fecha Fin:** "
                            f"{solicitud_row.get('fecha_fin', '')}"
                        )

                    with col2:

                        st.write(
                            f"**Empresa Brinda Servicio:** "
                            f"{solicitud_row.get('empresa_brinda_servicio', '')}"
                        )

                        st.write(
                            f"**Empresa Cargo Gastos:** "
                            f"{solicitud_row.get('empresa_cargo_gastos', '')}"
                        )

                        st.write(
                            f"**Unidad Negocio:** "
                            f"{solicitud_row.get('unidad_negocio', '')}"
                        )

                        st.write(
                            f"**Sucursal:** "
                            f"{solicitud_row.get('sucursal', '')}"
                        )

                        st.write(
                            f"**Sucursal Especificar:** "
                            f"{solicitud_row.get('sucursal_especificar', '')}"
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
                            background-color:#1B267A;
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
                            background-color:#1B267A;
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
                            background-color:#1B267A;
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
                            background-color:#1B267A;
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
                    # CONCEPTOS
                    # =================================

                    st.markdown("---")

                    st.markdown(
                        "## 💰 Conceptos"
                    )

                    conceptos_solicitud = (
                        solicitud_row.get(
                            "conceptos",
                            []
                        )
                    )

                    conceptos_comprobacion = (
                        row.get(
                            "conceptos",
                            []
                        )
                    )

                    col_sol, col_comp = st.columns(2)

                    # =================================
                    # SOLICITUD
                    # =================================

                    with col_sol:

                        total_estimado = (
                            solicitud_row.get(
                                "total_estimado",
                                0
                            )
                        )

                        try:
                            total_estimado = (
                                float(total_estimado)
                            )
                        except:
                            total_estimado = 0

                        st.markdown(
                            f"""
                            <div style='
                                font-size:22px;
                                font-weight:700;
                                color:#BFA75F;
                                margin-bottom:15px;
                            '>
                                Solicitud:
                                ${total_estimado:,.2f}
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                        if conceptos_solicitud:

                            df_sol = pd.DataFrame(
                                conceptos_solicitud
                            )

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
                                num_rows="dynamic",
                                disabled=True
                            )

                    # =================================
                    # COMPROBACION
                    # =================================

                    with col_comp:

                        total_comprobado = (
                            row.get(
                                "total_comprobado",
                                0
                            )
                        )

                        try:
                            total_comprobado = (
                                float(total_comprobado)
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

                            st.data_editor(
                                df_comp,
                                use_container_width=True,
                                hide_index=True,
                                num_rows="dynamic",
                                disabled=True
                            )

# =================================
# PAGE BUTTONS
# =================================

st.markdown("<br>", unsafe_allow_html=True)

cols_paginas_finalizadas = st.columns(
    total_paginas_finalizadas
)

for i in range(total_paginas_finalizadas):

    pagina_num = i + 1

    with cols_paginas_finalizadas[i]:

        if st.button(
            str(pagina_num),
            key=f"pagina_finalizada_{pagina_num}",
        ):

            st.session_state.pagina_finalizadas = (
                pagina_num
            )

            st.rerun()



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
    DEFAULT BUTTONS
    ========================= */
    div.stButton > button {
        height: 38px;
        font-size: 0.85rem;
        border-radius: 10px;
        padding: 0.2rem 0.6rem;

        background-color: #1B267A;
        color: #FFFFFF;
        border: 1px solid rgba(191, 167, 95, 0.25);
        transition: all 0.2s ease-in-out;
    }

    /* Hover */
    div.stButton > button:hover {
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

    /* KPI cards fixed height */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        min-height: 190px;
        max-height: 190px;
    }
    /* Wider dialog modal */
    div[role="dialog"] {
        width: 98vw !important;
        max-width: 1800px !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)