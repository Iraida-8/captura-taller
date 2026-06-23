import re
import io
import unicodedata
from typing import List, Dict, Any, Tuple
import pandas as pd
import pdfplumber
import streamlit as st
from auth import require_login, require_access

# =================================
# Page configuration
# =================================
st.set_page_config(page_title="Lector Facturas PDF → Excel", layout="wide")

# =================================
# CSS THEME — BLUE + YELLOW
# =================================
st.markdown(
    """
    <style>

    /* Hide sidebar */
    [data-testid="stSidebar"] {
        display: none;
    }

    /* Main background */
    .stApp {
        background-color: #151F6D;
    }

    /* Main container */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    /* Titles */
    h1 {
        color: #FFFFFF;
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }

    h2, h3 {
        color: #BFA75F;
        font-weight: 600;
    }

    /* General text */
    p, label, span {
        color: #F5F5F5 !important;
    }

    /* Caption text */
    .stCaption {
        color: #D9D9D9 !important;
    }

    /* Divider */
    hr {
        border-color: rgba(191, 167, 95, 0.25);
    }

    /* File uploader */
    [data-testid="stFileUploader"] {
        background-color: #1B267A;
        border: 1px solid rgba(191, 167, 95, 0.25);
        border-radius: 14px;
        padding: 1rem;
    }

    /* Checkbox labels */
    .stCheckbox label {
        color: #FFFFFF !important;
    }

    /* Buttons */
    div.stButton > button,
    div[data-testid="stDownloadButton"] > button {
        border-radius: 12px;
        font-weight: 600;
        transition: all 0.2s ease;
        border: none;
    }

    /* Standard buttons */
    div.stButton > button {
        background-color: #1B267A;
        color: white;
        border: 1px solid rgba(191, 167, 95, 0.25);
        height: 42px;
    }

    div.stButton > button:hover {
        background-color: #24338C;
        border-color: #BFA75F;
        color: #BFA75F;
        transform: translateY(-1px);
    }

    /* Download button */
    div[data-testid="stDownloadButton"] > button {
        background-color: #BFA75F;
        color: #151F6D;
        box-shadow: 0 4px 12px rgba(191, 167, 95, 0.20);
    }

    div[data-testid="stDownloadButton"] > button:hover {
        background-color: #d4bc73;
        color: #151F6D;
        transform: translateY(-1px);
    }

    /* Secondary nav button */
    button[kind="secondary"] {
        background-color: transparent !important;
        color: #BFA75F !important;
        border: 1px solid #BFA75F !important;
    }

    button[kind="secondary"]:hover {
        background-color: #BFA75F !important;
        color: #151F6D !important;
    }

    /* Dataframes */
    [data-testid="stDataFrame"] {
        border: 1px solid rgba(191, 167, 95, 0.20);
        border-radius: 12px;
        overflow: hidden;
    }

    /* Success / warning / info messages */
    div[data-baseweb="notification"] {
        border-radius: 12px;
    }

    /* Metric containers if used later */
    [data-testid="metric-container"] {
        background-color: #1B267A;
        border: 1px solid rgba(191, 167, 95, 0.20);
        padding: 1rem;
        border-radius: 14px;
    }

    </style>
    """,
    unsafe_allow_html=True
)

# =================================
# Security gates
# =================================
require_login()
require_access("bonos_operador")

# =================================
# Navigation
# =================================
if st.button("⬅ Volver al Dashboard"):
    st.switch_page("pages/dashboard.py")

st.divider()

# ==========================================
# BONO DE OPERADORES
# ==========================================

st.title("💰 Bono de Operadores")

# ------------------------------------------
# PARAMETROS TEMPORALES
# ------------------------------------------

PRECIO_DIESEL = 10.00

RENDIMIENTOS = {
    "TR-001": {"min": 2.8, "max": 3.2},
    "TR-002": {"min": 2.6, "max": 3.0},
    "TR-003": {"min": 3.0, "max": 3.4},
}

# ------------------------------------------
# FORMULARIO
# ------------------------------------------

st.subheader("📋 Datos del Viaje")

col1, col2 = st.columns(2)

with col1:
    unidad = st.selectbox(
        "Unidad",
        list(RENDIMIENTOS.keys())
    )

    operador = st.text_input("Operador")

    origen = st.text_input("Origen")

    destino = st.text_input("Destino")

with col2:
    tipo_ruta = st.selectbox(
        "Tipo de Ruta",
        ["Corta", "Larga"]
    )

    numero_trafico = st.text_input(
        "Número de Tráfico"
    )

    kilometros = st.number_input(
        "Kilómetros Recorridos",
        min_value=0.0,
        step=1.0
    )

    litros_cargados = st.number_input(
        "Litros Cargados",
        min_value=0.0,
        step=1.0
    )

st.divider()

# ------------------------------------------
# PARAMETROS
# ------------------------------------------

st.subheader("⚙️ Parámetros")

rend_min = RENDIMIENTOS[unidad]["min"]
rend_max = RENDIMIENTOS[unidad]["max"]

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Rendimiento Mínimo",
        f"{rend_min:.2f} km/l"
    )

with col2:
    st.metric(
        "Rendimiento Máximo",
        f"{rend_max:.2f} km/l"
    )

with col3:
    precio_diesel = st.number_input(
        "Precio Diesel ($)",
        value=PRECIO_DIESEL,
        step=0.5
    )

st.divider()

# ------------------------------------------
# CALCULO
# ------------------------------------------

if st.button(
    "🧮 Calcular Bono",
    use_container_width=True
):

    errores = []

    if kilometros <= 0:
        errores.append(
            "Los kilómetros recorridos deben ser mayores a cero."
        )

    if litros_cargados <= 0:
        errores.append(
            "Los litros cargados deben ser mayores a cero."
        )

    if kilometros > 5000:
        errores.append(
            "Kilometraje fuera de rango."
        )

    rendimiento_real = (
        kilometros / litros_cargados
        if litros_cargados > 0
        else 0
    )

    if rendimiento_real < 1:
        errores.append(
            f"Rendimiento ilógico ({rendimiento_real:.2f} km/l)."
        )

    if rendimiento_real > 8:
        errores.append(
            f"Rendimiento ilógico ({rendimiento_real:.2f} km/l)."
        )

    if errores:

        for error in errores:
            st.error(error)

    else:

        rendimiento_objetivo = (
            rend_min + rend_max
        ) / 2

        litros_esperados = (
            kilometros / rendimiento_objetivo
        )

        diferencia_litros = (
            litros_esperados - litros_cargados
        )

        monto = (
            diferencia_litros * precio_diesel
        )

        st.divider()

        st.subheader("📊 Resultado")

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Rendimiento Real",
            f"{rendimiento_real:.2f} km/l"
        )

        c2.metric(
            "Litros Esperados",
            f"{litros_esperados:.2f}"
        )

        c3.metric(
            "Litros Reales",
            f"{litros_cargados:.2f}"
        )

        c4.metric(
            "Diferencia",
            f"{diferencia_litros:.2f}"
        )

        if monto > 0:

            st.success(
                f"✅ BONO AL OPERADOR: ${monto:,.2f}"
            )

        elif monto < 0:

            st.error(
                f"❌ COBRO AL OPERADOR: ${abs(monto):,.2f}"
            )

        else:

            st.info(
                "Sin bono ni cobro."
            )