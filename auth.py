import streamlit as st

def require_login():
    if not st.session_state.get("logged_in", False):
        st.stop()

def require_access(permission: str):
    user = st.session_state.get("user")
    if not user or permission not in user.get("access", []):
        st.error("Acceso denegado")
        st.stop()
