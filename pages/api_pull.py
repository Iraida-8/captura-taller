import streamlit as st
import requests
import pandas as pd

# Page title
st.title("GPS Insight Vehicles")

# Your session token
SESSION_TOKEN = "YOUR_SESSION_TOKEN"

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