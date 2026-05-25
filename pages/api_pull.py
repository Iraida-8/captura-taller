import streamlit as st
import requests
import pandas as pd

st.set_page_config(layout="wide")

st.title("GPS Insight Vehicles")

# Session token
SESSION_TOKEN = "YOUR_TOKEN"

# Vehicle list endpoint
url = f"https://api.gpsinsight.com/v2/vehicle/list?session_token=763aade0cf05363d50e5ddcb2f597f6cb0c94e73cecae0c8ac8c"

try:
    # API request
    response = requests.get(url)
    response.raise_for_status()

    # Convert to JSON
    result = response.json()

    # Show raw response
    st.subheader("Raw API Response")
    st.json(result)

    # Extract vehicles
    vehicles = result.get("data", [])

    if vehicles:

        # Convert to dataframe
        df = pd.DataFrame(vehicles)

        st.subheader("Vehicle Table")
        st.dataframe(df, use_container_width=True)

        # Save locally
        df.to_json("vehicles.json", orient="records", indent=4)

        st.success("Vehicles loaded and saved locally.")

    else:
        st.warning("No vehicles found.")

except requests.exceptions.RequestException as e:
    st.error(f"Request failed: {e}")

except Exception as e:
    st.error(f"Unexpected error: {e}")