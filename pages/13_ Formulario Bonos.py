import io
from datetime import datetime
import streamlit as st
import pandas as pd
from supabase import create_client
from auth import require_login, require_access
import streamlit.components.v1 as components

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

    div[data-testid="stVerticalBlockBorderWrapper"]{
        background-color:#27348F !important;
        border:1px solid rgba(191,167,95,.25) !important;
        border-radius:18px !important;
        padding:24px !important;
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
# Page Cache and State Management
# =================================
@st.cache_resource
def get_supabase_client():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_SERVICE_KEY"]
    )

supabase = get_supabase_client()

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

# ==========================================
# CATALOGO DE UNIDADES
# ==========================================

try:

    unidades_response = (
        supabase
        .table("catalogo_unidades_bonos")
        .select("*")
        .order("unidad")
        .execute()
    )

    unidades_df = pd.DataFrame(
        unidades_response.data
    )

except Exception as e:

    st.error(
        f"Error cargando catálogo de unidades: {e}"
    )
    st.stop()

if unidades_df.empty:
    st.warning(
        "No existen unidades en el catálogo."
    )
    st.stop()

# ==========================================
# VEHICLE UNITS TABLE
# ==========================================

vehicle_response = (
    supabase
    .table("vehicle_units")
    .select("*")
    .order("unidad")
    .execute()
)

vehicle_df = pd.DataFrame(
    vehicle_response.data
)

# ==========================================
# MERGE BOTH TABLES
# ==========================================

import re

def normalize_unit(unit):

    if pd.isna(unit):
        return ""

    unit = str(unit).strip().upper()

    # Extract only the numeric part
    numbers = re.findall(r"\d+", unit)

    if not numbers:
        return unit

    number = int(numbers[0])

    if unit.startswith("IG-"):
        return f"G{number:05d}"

    if unit.startswith("G"):
        return f"G{number:05d}"

    if unit.startswith("P"):
        return f"P{number:05d}"

    if unit.startswith("A"):
        return f"A{number:05d}"

    return unit
    return unit


vehicle_df["join_key"] = vehicle_df["unidad"].apply(normalize_unit)

unidades_df["join_key"] = unidades_df["unidad"].apply(normalize_unit)

unidades_df = vehicle_df.merge(
    unidades_df,
    on="join_key",
    how="left",
    suffixes=("", "_bono")
)

# ==========================================
# FORMULARIO
# ==========================================

st.subheader("📋 Formulario")

empresa = st.selectbox(
    "Empresa",
    ["Selecciona Empresa", "Igloo", "Picus"],
    index=0
)

if empresa == "Igloo":

    unidades_filtradas = unidades_df[
        unidades_df["empresa"] == "IGT"
    ]

elif empresa == "Picus":

    unidades_filtradas = unidades_df[
        unidades_df["empresa"] == "PIC"
    ]

else:

    unidades_filtradas = unidades_df.iloc[0:0]

unidad = st.selectbox(
    "Unidad",
    unidades_filtradas["unidad"].tolist()
    if not unidades_filtradas.empty
    else [],
    index=None,
    placeholder="Seleccione una empresa primero"
)

if unidad is None:

    st.stop()

unidad_info = unidades_filtradas[
    unidades_filtradas["unidad"] == unidad
].iloc[0]

# ==========================================
# Unidad Info (Hidden)
# ==========================================

def clean_value(value):
    return "" if pd.isna(value) else str(value)

vin = clean_value(unidad_info["vin"])
placa_mex = clean_value(unidad_info["placa_mex"])
marca = clean_value(unidad_info["marca"])
modelo = clean_value(unidad_info["modelo"])
motor = clean_value(unidad_info["motor"])
anio = clean_value(unidad_info["anio"])
rendimiento_esperado_txt = clean_value(unidad_info["rendimiento_esperado"])
rendimiento_minimo_txt = clean_value(unidad_info["rendimiento_minimo"])

with st.container(border=True, key="bono_form"):

    col_form, col_calc = st.columns([1, 1])

    # ==========================================
    # LEFT COLUMN - FORM
    # ==========================================

    with col_form:

        st.subheader("📝 Información del Viaje")

        ruta = st.text_input(
            "Ruta: Origen - Destino"
        )

        tipo_ruta = st.selectbox(
            "Tipo Ruta",
            ["Corta", "Larga"]
        )

        trafico = st.text_input(
            "Número de Tráfico"
        )

        kilometros = st.number_input(
            "Kilómetros",
            min_value=0.0,
            step=1.0
        )

        litros_cargados = st.number_input(
            "Litros Cargados",
            min_value=0.0,
            step=1.0
        )

        rendimiento_minimo = pd.to_numeric(
            unidad_info["rendimiento_minimo"],
            errors="coerce"
        )

        rendimiento_esperado = pd.to_numeric(
            unidad_info["rendimiento_esperado"],
            errors="coerce"
        )

        if pd.isna(rendimiento_minimo):
            rendimiento_minimo = 0.0

        if pd.isna(rendimiento_esperado):
            rendimiento_esperado = 0.0

        param1, param2 = st.columns(2)

        with param1:
            st.metric(
                "Rendimiento Mínimo",
                f"{rendimiento_minimo:.2f} km/l"
            )

        with param2:
            PRECIO_DIESEL = st.number_input(
                "Precio Diesel ($)",
                min_value=0.0,
                value=10.55,
                step=0.01,
                format="%.2f",
                key="precio_diesel"
            )

        calcular = st.button(
            "🧮 Calcular",
            use_container_width=True
        )

    # ==========================================
    # RIGHT COLUMN - RESULTADO
    # ==========================================

    with col_calc:

        if calcular:

            rendimiento_real = (
                kilometros / litros_cargados
                if litros_cargados > 0
                else 0
            )

            litros_permitidos = (
                kilometros / rendimiento_minimo
                if rendimiento_minimo > 0
                else 0
            )

            diferencia_litros = (
                litros_permitidos - litros_cargados
            )

            monto = (
                diferencia_litros * PRECIO_DIESEL
            )

            st.subheader("📊 Resultado")

            st.text_input(
                "Rendimiento Real",
                value=f"{rendimiento_real:.2f}",
                disabled=True
            )

            st.text_input(
                "Dif. a Favor o en Contra del Rendimiento",
                value=f"{rendimiento_real - rendimiento_minimo:.2f}",
                disabled=True
            )

            st.text_input(
                "Litros Permitidos",
                value=f"{litros_permitidos:.2f}",
                disabled=True
            )

            st.text_input(
                "Litros Ahorrados / Excedidos",
                value=f"{diferencia_litros:.2f}",
                disabled=True
            )

            if monto >= 0:
                st.success(
                    f"💰 BONO A PAGAR: ${monto:,.2f}"
                )
            else:
                st.error(
                    f"🚨 DESCUENTO: ${abs(monto):,.2f}"
                )

            st.info(
                f"Precio Diesel Utilizado: ${PRECIO_DIESEL:,.2f}"
            )

            st.info(
                f"Rendimiento Esperado: {rendimiento_esperado:.2f} km/l"
            )