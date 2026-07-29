import streamlit as st

st.set_page_config(layout="wide")

pg = st.navigation(
    [
        st.Page("pages/dashboard_beta.py", title="Dashboard", default=True),
    ],
    position="top",
)

pg.run()