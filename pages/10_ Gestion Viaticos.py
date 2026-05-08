import streamlit as st
import pandas as pd
from supabase import create_client
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
# TEMP COUNTS
# =================================

total_registros = (
    len(df_solicitudes) +
    len(df_comprobaciones)
)

pendientes = len(df_solicitudes)

verificando = len(df_comprobaciones)

autorizadas = 0

rechazadas = 0

# =================================
# CSS
# =================================

st.markdown(
    """
    <style>

    /* Hide sidebar */
    [data-testid="stSidebar"] {
        display: none;
    }

    /* Background */
    .stApp {
        background-color: #151F6D;
    }

    /* Spacing */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    /* Text */
    h1, h2, h3, p, span, label {
        color: white;
    }

    /* Buttons */
    div.stButton > button {
        height: 70px;
        font-size: 1rem;
        font-weight: 700;
        border-radius: 14px;
        background-color: #1B267A;
        color: white;
        border: 1px solid rgba(191,167,95,0.25);
    }

    div.stButton > button:hover {
        background-color: #24338C;
        border-color: #BFA75F;
        color: #BFA75F;
    }

    </style>
    """,
    unsafe_allow_html=True
)

# =================================
# TOP NAVIGATION
# =================================

if st.button("⬅ Volver al Dashboard"):
    st.switch_page("pages/dashboard.py")

st.divider()

# =================================
# HEADER
# =================================

st.markdown(
    """
    <div style="
        font-size:48px;
        font-weight:800;
        color:white;
        margin-bottom:25px;
    ">
        ⚙ Gestión de Viáticos
    </div>
    """,
    unsafe_allow_html=True
)

# =================================
# KPI STRIP
# =================================

k1, k2, k3, k4, k5 = st.columns(5)

def postit(
    col,
    titulo,
    valor,
    bg_color,
    border_color
):

    with col:

        st.markdown(
            f"""
            <div style="
                background-color:{bg_color};
                border-left:6px solid {border_color};
                border-radius:18px;
                padding:22px;
                height:160px;
                display:flex;
                flex-direction:column;
                justify-content:space-between;
                box-shadow:0 4px 12px rgba(0,0,0,0.15);
            ">

                <div style="
                    color:white;
                    font-size:20px;
                    font-weight:700;
                ">
                    {titulo}
                </div>

                <div style="
                    color:white;
                    font-size:58px;
                    font-weight:900;
                    line-height:1;
                ">
                    {valor}
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )

postit(
    k1,
    "📊 Total",
    total_registros,
    "#24338C",
    "#BFA75F"
)

postit(
    k2,
    "⏳ Pendientes",
    pendientes,
    "#7C4A03",
    "#F59E0B"
)

postit(
    k3,
    "🔎 Verificando",
    verificando,
    "#0C4A6E",
    "#38BDF8"
)

postit(
    k4,
    "✅ Autorizadas",
    autorizadas,
    "#065F46",
    "#10B981"
)

postit(
    k5,
    "❌ Rechazadas",
    rechazadas,
    "#7F1D1D",
    "#EF4444"
)

st.markdown("<br><br>", unsafe_allow_html=True)

# =================================
# CURRENT USER
# =================================

st.caption(
    f"Usuario actual: {nombre_usuario} | {email_usuario}"
)