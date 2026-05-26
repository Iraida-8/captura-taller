import streamlit as st
import requests
import pandas as pd
import json
from auth import require_login, require_access

# =================================
# Page configuration
# =================================
st.set_page_config(
    page_title="Rastreador y Seguimiento GPS de Unidades",
    layout="wide"
)

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

    /* Main app background */
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

    /* Divider */
    hr {
        border-color: rgba(191, 167, 95, 0.25);
    }

    /* File uploader */
    [data-testid="stFileUploader"] {
        background-color: #1B267A;
        border: 1px solid rgba(191, 167, 95, 0.25);
        border-radius: 12px;
        padding: 1rem;
    }

    /* Inputs / Selects */
    div[data-baseweb="input"] > div,
    div[data-baseweb="select"] > div {
        background-color: #1B267A !important;
        border: 1px solid rgba(191, 167, 95, 0.25) !important;
        border-radius: 10px !important;
        color: white !important;
    }

    input {
        color: white !important;
    }

    input::placeholder {
        color: #d0d0d0 !important;
    }

    div[data-baseweb="select"] * {
        color: white !important;
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
        box-shadow: 0 4px 12px rgba(191, 167, 95, 0.25);
    }

    div[data-testid="stDownloadButton"] > button:hover {
        background-color: #d4bc73;
        color: #151F6D;
        transform: translateY(-1px);
    }

    /* Back button */
    button[kind="secondary"] {
        background-color: transparent !important;
        color: #BFA75F !important;
        border: 1px solid #BFA75F !important;
    }

    button[kind="secondary"]:hover {
        background-color: #BFA75F !important;
        color: #151F6D !important;
    }

    /* Metrics */
    [data-testid="metric-container"] {
        background-color: #1B267A;
        border: 1px solid rgba(191, 167, 95, 0.20);
        padding: 1rem;
        border-radius: 14px;
    }

    /* Dataframes */
    [data-testid="stDataFrame"] {
        border: 1px solid rgba(191, 167, 95, 0.20);
        border-radius: 12px;
        overflow: hidden;
    }

    /* Info / warning / success */
    div[data-baseweb="notification"] {
        border-radius: 12px;
    }

    </style>
    """,
    unsafe_allow_html=True
)

# =================================
# Security gates
# =================================
require_login()
require_access("gps_tracking")

# =================================
# Top navigation
# =================================
if st.button("⬅ Volver al Dashboard"):
    st.switch_page("pages/dashboard.py")

st.title("🛰️  Rastreador y Seguimiento GPS de Unidades")
st.divider()

#==============================================================================================================
# Session token
SESSION_TOKEN = "763aade0cf05363d50e5ddcb2f597f6cb0c94e73cecae0c8ac8c"

#==============================================================================================================
# Location endpoint
url = f"https://api.gpsinsight.com/v2/vehicle/location?session_token={SESSION_TOKEN}"

#==============================================================================================================

with st.expander("🛰️ GPS Insight Fleet Tracking", expanded=False):

    try:
        # API request
        response = requests.get(url)
        response.raise_for_status()

        # Convert to JSON
        result = response.json()

        # =================================
        # Raw API Response
        # =================================
        with st.expander("📦 Raw API Response", expanded=False):
            st.json(result)

        # Extract data
        vehicles = result.get("data", [])

        if vehicles:

            # Convert to dataframe
            df = pd.DataFrame(vehicles)

            # Save locally
            with open("vehicles.json", "w", encoding="utf-8") as f:
                json.dump(vehicles, f, indent=4, ensure_ascii=False)

            # =================================
            # Dashboard metrics
            # =================================
            col1, col2, col3 = st.columns(3)

            col1.metric("Vehicles", len(df))

            if "inst_speed" in df.columns:
                moving = (
                    pd.to_numeric(df["inst_speed"], errors="coerce") > 0
                ).sum()

                col2.metric("Moving", moving)

            if "ignition" in df.columns:
                on_count = (
                    df["ignition"]
                    .astype(str)
                    .str.lower()
                    .eq("on")
                    .sum()
                )

                col3.metric("Ignition On", on_count)

            # =================================
            # Fleet Table
            # =================================
            with st.expander("🚛 Fleet Table", expanded=False):

                st.dataframe(
                    df,
                    use_container_width=True,
                    height=700
                )

            st.success("Fleet data loaded successfully.")

        else:
            st.warning("No vehicle location data returned.")

    except requests.exceptions.RequestException as e:
        st.error(f"Request failed: {e}")

    except Exception as e:
        st.error(f"Unexpected error: {e}")

# =========================================================
# KPI DASHBOARD
# =========================================================
if "df" in locals() and not df.empty:

    st.divider()

    st.header("📊 Dashboard Operativo GPS")

    # =========================================
    # DATA PREP
    # =========================================
    df["inst_speed"] = pd.to_numeric(
        df["inst_speed"],
        errors="coerce"
    ).fillna(0)

    df["odometer"] = pd.to_numeric(
        df["odometer"],
        errors="coerce"
    ).fillna(0)

    df["voltage"] = pd.to_numeric(
        df["voltage"],
        errors="coerce"
    ).fillna(0)

    # =========================================
    # BASIC COUNTS
    # =========================================
    total_units = len(df)

    moving_units = (df["inst_speed"] > 0).sum()

    stopped_units = (df["inst_speed"] <= 0).sum()

    ignition_on = (
        df["ignition"]
        .astype(str)
        .str.lower()
        .eq("on")
        .sum()
    )

    ignition_off = (
        df["ignition"]
        .astype(str)
        .str.lower()
        .eq("off")
        .sum()
    )

    avg_speed = round(df["inst_speed"].mean(), 1)

    max_speed = round(df["inst_speed"].max(), 1)

    # =========================================
    # KPI POST-ITS
    # =========================================
    c1, c2, c3, c4, c5, c6 = st.columns(6)

    c1.metric("🚛 Total Unidades", total_units)

    c2.metric("🟢 En Movimiento", moving_units)

    c3.metric("🔴 Detenidas", stopped_units)

    c4.metric("⚡ Ignición Encendida", ignition_on)

    c5.metric("⛔ Ignición Apagada", ignition_off)

    c6.metric("🏎️ Velocidad Promedio", f"{avg_speed} km/h")

    # =========================================
    # SECOND ROW
    # =========================================
    c7, c8, c9 = st.columns(3)

    c7.metric(
        "🔥 Velocidad Máxima",
        f"{max_speed} km/h"
    )

    low_voltage = (df["voltage"] < 11).sum()

    c8.metric(
        "🔋 Voltaje Bajo",
        low_voltage
    )

    panic_active = 0

    if "inputs" in df.columns:

        for val in df["inputs"]:

            if isinstance(val, dict):

                if "Panic Button" in val:

                    if str(val["Panic Button"]).lower() == "on":
                        panic_active += 1

    c9.metric(
        "🚨 Botón de Pánico",
        panic_active
    )

    st.divider()

    # =====================================================
    # CHARTS
    # =====================================================
    col1, col2 = st.columns(2)

    with col1:

        st.subheader("Estado de Ignición")

        ignition_counts = (
            df["ignition"]
            .astype(str)
            .value_counts()
        )

        st.bar_chart(ignition_counts)

    with col2:

        st.subheader("Distribución de Velocidades")

        speed_df = df[df["inst_speed"] > 0]

        if not speed_df.empty:

            st.bar_chart(
                speed_df["inst_speed"]
            )

        else:
            st.info("No se detectaron unidades en movimiento.")

    st.divider()

    # =====================================================
    # LONGEST STOPPED UNITS
    # =====================================================
    st.subheader("🛑 Unidades Detenidas por Más Tiempo")

    if "speed_label" in df.columns:

        stopped_df = df[
            df["speed_label"]
            .astype(str)
            .str.contains("Stopped", case=False, na=False)
        ][[
            "label",
            "speed_label",
            "address",
            "fix_time"
        ]]

        st.dataframe(
            stopped_df,
            use_container_width=True,
            height=350
        )

    # =====================================================
    # LOW VOLTAGE ALERTS
    # =====================================================
    st.subheader("🔋 Alertas de Voltaje Bajo")

    voltage_df = df[df["voltage"] < 11][[
        "label",
        "voltage",
        "address",
        "fix_time"
    ]]

    if not voltage_df.empty:

        st.dataframe(
            voltage_df,
            use_container_width=True,
            height=250
        )

    else:
        st.success("No se detectaron unidades con voltaje bajo.")