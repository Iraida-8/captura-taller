import streamlit as st

def require_login():
    if not st.session_state.get("logged_in", False):
        st.set_page_config(
            page_title="Login",
            layout="centered",
            initial_sidebar_state="collapsed"
        )
        st.sidebar.empty()
        st.stop()