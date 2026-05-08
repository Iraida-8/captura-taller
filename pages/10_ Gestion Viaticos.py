import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
from auth import require_login, require_access

# =================================
# PAGE CONFIG
# =================================

st.set_page_config(
    page_title="Gestión de Viáticos",
    layout="wide"
)

# =================================
# SECURITY
# =================================

require_login()
require_access("gestion_viaticos")

# =================================
# SUPABASE
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
# NAVIGATION
# =================================

if st.button("⬅ Volver al Dashboard"):
    st.switch_page("pages/dashboard.py")

st.divider()

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
# DEFAULT STATUS
# =================================

if not df_solicitudes.empty:

    if "status" not in df_solicitudes.columns:
        df_solicitudes["status"] = "PENDIENTE"

if not df_comprobaciones.empty:

    if "status" not in df_comprobaciones.columns:
        df_comprobaciones["status"] = "VERIFICANDO"

# =================================
# KPIs
# =================================

total_solicitudes = len(df_solicitudes)

pendientes = 0
autorizados = 0
verificando = 0

if not df_solicitudes.empty:

    pendientes += len(
        df_solicitudes[
            df_solicitudes["status"] == "PENDIENTE"
        ]
    )

    autorizados += len(
        df_solicitudes[
            df_solicitudes["status"] == "AUTORIZADO"
        ]
    )

if not df_comprobaciones.empty:

    verificando += len(
        df_comprobaciones[
            df_comprobaciones["status"] == "VERIFICANDO"
        ]
    )

# =================================
# HEADER
# =================================

st.markdown(
    """
    <div style="
        font-size:42px;
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

col1, col2, col3, col4 = st.columns(4)

def render_kpi(title, value, emoji):

    st.markdown(
        f"""
        <div style="
            background:white;
            border-left:6px solid #BFA75F;
            border-radius:18px;
            padding:20px;
            height:140px;
            box-shadow:0 4px 12px rgba(0,0,0,0.12);
        ">
            <div style="
                color:#6B7280;
                font-size:18px;
                margin-bottom:15px;
                font-weight:600;
            ">
                {emoji} {title}
            </div>

            <div style="
                color:#151F6D;
                font-size:54px;
                font-weight:800;
                line-height:1;
            ">
                {value}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

with col1:
    render_kpi("Total", total_solicitudes, "📊")

with col2:
    render_kpi("Pendientes", pendientes, "⏳")

with col3:
    render_kpi("Autorizados", autorizados, "✅")

with col4:
    render_kpi("Verificando", verificando, "🔎")

st.markdown("<br><br>", unsafe_allow_html=True)

# =================================
# FILTER TABS
# =================================

filtro = st.radio(
    "",
    [
        "⏳ Pendientes Autorización",
        "✅ Autorizados",
        "🔎 Verificando",
        "📋 Todos"
    ],
    horizontal=True,
    label_visibility="collapsed"
)

# =================================
# FILTER LOGIC
# =================================

df_display = df_solicitudes.copy()

if filtro == "⏳ Pendientes Autorización":

    if not df_display.empty:

        df_display = df_display[
            df_display["status"] == "PENDIENTE"
        ]

elif filtro == "✅ Autorizados":

    if not df_display.empty:

        df_display = df_display[
            df_display["status"] == "AUTORIZADO"
        ]

elif filtro == "🔎 Verificando":

    df_display = df_comprobaciones.copy()

# =================================
# EMPTY
# =================================

if df_display.empty:

    st.info("No hay registros disponibles.")

# =================================
# CARDS
# =================================

else:

    for _, row in df_display.iterrows():

        if "folio_solicitud" in row:

            folio = row.get(
                "folio_solicitud",
                ""
            )

            monto = row.get(
                "total_estimado",
                0
            )

            empresa = row.get(
                "empresa_brinda_servicio",
                ""
            )

            empleado = row.get(
                "nombre_empleado_solicita",
                ""
            )

            motivo = row.get(
                "motivo_viaje",
                ""
            )

            status = row.get(
                "status",
                "PENDIENTE"
            )

        else:

            folio = row.get(
                "folio_comprobacion",
                ""
            )

            monto = row.get(
                "total_comprobado",
                0
            )

            empresa = row.get(
                "nombre_compania",
                ""
            )

            empleado = row.get(
                "nombre_empleado_solicita",
                ""
            )

            motivo = row.get(
                "motivo_viaje",
                ""
            )

            status = row.get(
                "status",
                "VERIFICANDO"
            )

        border_color = "#BFA75F"

        if status == "AUTORIZADO":
            border_color = "#10B981"

        elif status == "VERIFICANDO":
            border_color = "#38BDF8"

        elif status == "PENDIENTE":
            border_color = "#F59E0B"

        st.markdown(
            f"""
            <div style="
                background:white;
                border-left:8px solid {border_color};
                border-radius:18px;
                padding:28px;
                margin-bottom:18px;
                box-shadow:0 4px 12px rgba(0,0,0,0.12);
            ">

                <div style="
                    display:flex;
                    justify-content:space-between;
                    align-items:center;
                ">

                    <div>

                        <div style="
                            font-size:36px;
                            font-weight:800;
                            color:#151F6D;
                            margin-bottom:10px;
                        ">
                            {folio}
                        </div>

                        <div style="
                            color:#6B7280;
                            font-size:18px;
                            margin-bottom:6px;
                        ">
                            {empleado}
                        </div>

                        <div style="
                            color:#6B7280;
                            font-size:18px;
                            margin-bottom:6px;
                        ">
                            {empresa}
                        </div>

                        <div style="
                            color:#6B7280;
                            font-size:18px;
                        ">
                            {motivo}
                        </div>

                    </div>

                    <div style="
                        text-align:right;
                    ">

                        <div style="
                            font-size:22px;
                            font-weight:700;
                            color:{border_color};
                            margin-bottom:12px;
                        ">
                            {status}
                        </div>

                        <div style="
                            font-size:34px;
                            font-weight:800;
                            color:#151F6D;
                        ">
                            $ {monto:,.2f}
                        </div>

                    </div>

                </div>

            </div>
            """,
            unsafe_allow_html=True
        )

# =================================
# CURRENT USER
# =================================

st.markdown("<br><br>", unsafe_allow_html=True)

st.caption(
    f"Usuario actual: {nombre_usuario} | {email_usuario}"
)

# =================================
# CSS
# =================================

st.markdown(
    """
    <style>

    [data-testid="stSidebar"] {
        display:none;
    }

    .stApp {
        background-color:#151F6D;
    }

    .block-container {
        padding-top:2rem;
        padding-bottom:3rem;
    }

    h1, h2, h3, p, span, label {
        color:white;
    }

    div.stButton > button {
        border-radius:14px;
        background:#1B267A;
        color:white;
        border:1px solid rgba(191,167,95,0.25);
        font-weight:700;
    }

    div.stButton > button:hover {
        background:#24338C;
        color:#BFA75F;
        border-color:#BFA75F;
    }

    div[role="radiogroup"] > label {
        background:#1B267A;
        padding:10px 16px;
        border-radius:12px;
        margin-right:8px;
        border:1px solid rgba(191,167,95,0.25);
    }

    </style>
    """,
    unsafe_allow_html=True
)