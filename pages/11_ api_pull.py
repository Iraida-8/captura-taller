import streamlit as st
import requests
import pandas as pd
import json
from auth import require_login, require_access

# =================================
# Page configuration
# =================================
st.set_page_config(
    page_title="Seguimiento de Unidades y GPS",
    layout="wide"
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

st.title("⛽ Reporte iFuel")
st.divider()

st.title("GPS Insight Fleet Tracking")

# Session token
SESSION_TOKEN = "YOUR_TOKEN"

# Location endpoint
url = f"https://api.gpsinsight.com/v2/vehicle/location?session_token=763aade0cf05363d50e5ddcb2f597f6cb0c94e73cecae0c8ac8c"

try:
    # API request
    response = requests.get(url)
    response.raise_for_status()

    # Convert to JSON
    result = response.json()

    # Show raw response
    st.subheader("Raw API Response")
    st.json(result)

    # Extract data
    vehicles = result.get("data", [])

    if vehicles:

        # Convert to dataframe
        df = pd.DataFrame(vehicles)

        # Save locally
        with open("vehicles.json", "w", encoding="utf-8") as f:
            json.dump(vehicles, f, indent=4, ensure_ascii=False)

        # Dashboard metrics
        col1, col2, col3 = st.columns(3)

        col1.metric("Vehicles", len(df))

        if "inst_speed" in df.columns:
            moving = (pd.to_numeric(df["inst_speed"], errors="coerce") > 0).sum()
            col2.metric("Moving", moving)

        if "ignition" in df.columns:
            on_count = (df["ignition"].astype(str).str.lower() == "on").sum()
            col3.metric("Ignition On", on_count)

        st.subheader("Fleet Table")

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