import streamlit as st
import requests
import pandas as pd

# Page title
st.title("GPS Insight Vehicles")

# Your session token
SESSION_TOKEN = "763aade0cf05363d50e5ddcb2f597f6cb0c94e73cecae0c8ac8c"

# API URL
url = f"https://api.gpsinsight.com/v2/vehicle/getattributes?session_token={SESSION_TOKEN}"

try:
    response = requests.get(url)
    response.raise_for_status()

    data = response.json()

    # Show raw response
    st.subheader("Raw Response")
    st.json(data)

    # Extract vehicle data
    vehicles = data.get("data", [])

    if vehicles:
        df = pd.DataFrame(vehicles)

        st.subheader("Vehicles")
        st.dataframe(df, use_container_width=True)

    else:
        st.warning("No vehicles returned.")

except requests.exceptions.RequestException as e:
    st.error(f"Request failed: {e}")