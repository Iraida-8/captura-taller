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
# DEFAULT STATUS
# =================================

if not df_solicitudes.empty:

    if "status" not in df_solicitudes.columns:
        df_solicitudes["status"] = "PENDIENTE"

if not df_comprobaciones.empty:

    if "status" not in df_comprobaciones.columns:
        df_comprobaciones["status"] = "VERIFICANDO"

# =================================
# Top navigation
# =================================
if st.button("⬅ Volver al Dashboard"):
    st.switch_page("pages/dashboard.py")

st.divider()

# =================================
# KPI VALUES
# =================================

total_registros = (
    len(df_solicitudes) +
    len(df_comprobaciones)
)

pendientes = 0
autorizados = 0
verificando = 0

if not df_solicitudes.empty:

    pendientes = len(
        df_solicitudes[
            df_solicitudes["status"] == "PENDIENTE"
        ]
    )

    autorizados = len(
        df_solicitudes[
            df_solicitudes["status"] == "AUTORIZADO"
        ]
    )

if not df_comprobaciones.empty:

    verificando = len(
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

kpi1, kpi2, kpi3, kpi4 = st.columns(4)

def render_kpi_card(
    title,
    value,
    emoji,
    border_color
):

    st.markdown(
        f"""
        <div style="
            background:white;
            border-left:7px solid {border_color};
            border-radius:18px;
            padding:24px;
            height:145px;
            box-shadow:0 4px 12px rgba(0,0,0,0.12);
        ">

            <div style="
                color:#6B7280;
                font-size:20px;
                font-weight:600;
                margin-bottom:14px;
            ">
                {emoji} {title}
            </div>

            <div style="
                color:#151F6D;
                font-size:56px;
                font-weight:800;
                line-height:1;
            ">
                {value}
            </div>

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
        "Autorizados",
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

st.markdown("<br><br>", unsafe_allow_html=True)

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