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

with st.expander("🛰️ GPS Insight Fleet Tracking", expanded=True):

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
            with st.expander("🚛 Fleet Table", expanded=True):

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