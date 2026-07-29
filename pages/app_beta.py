import streamlit as st

st.set_page_config(
    page_title="OMEGA",
    layout="wide"
)

nav = {
    "Home": [
        st.Page(
            "pages/dashboard_beta.py",
            title="🏠 Dashboard",
            default=True,
        )
    ]
}

pg = st.navigation(
    nav,
    position="top",
)

pg.run()