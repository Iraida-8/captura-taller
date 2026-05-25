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
    # Request API
    response = requests.get(url)

    # Raise error if failed
    response.raise_for_status()

    # Convert response to JSON
    data = response.json()

    # Show raw JSON if you want
    st.subheader("Raw API Response")
    st.json(data)

    # OPTIONAL:
    # Convert to dataframe if response is list/dict structure
    if isinstance(data, list):
        df = pd.DataFrame(data)
        st.subheader("Vehicle Table")
        st.dataframe(df, use_container_width=True)

except requests.exceptions.RequestException as e:
    st.error(f"Request failed: {e}")

except Exception as e:
    st.error(f"Unexpected error: {e}")