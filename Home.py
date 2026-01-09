import streamlit as st
from datetime import date

# =================================
# Page configuration
# =================================
st.set_page_config(
    page_title="Login",
    layout="centered"
)

# =================================
# Session state init
# =================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "user" not in st.session_state:
    st.session_state.user = ""

# =================================
# MOCK AUTH FUNCTION
# =================================
def mock_login(username, password):
    """
    Mock authentication logic.
    Replace later with real auth (LDAP, DB, OAuth, etc.)
    """
    if username and password:
        return True
    return False

# =================================
# LOGGED IN VIEW
# =================================
if st.session_state.logged_in:

    st.success(f"Bienvenido, {st.session_state.user}")

    st.title("Home Page Super Pro")
    st.divider()

    st.write("Sesión iniciada correctamente.")
    st.write("Aquí irá el acceso al sistema.")

    if st.button("Cerrar sesión"):
        st.session_state.logged_in = False
        st.session_state.user = ""
        st.rerun()

# =================================
# LOGIN VIEW
# =================================
else:
    st.title("Inicio de Sesión")
    st.divider()

    with st.form("login_form"):
        usuario = st.text_input(
            "Usuario",
            placeholder="Ingrese su usuario"
        )

        password = st.text_input(
            "Contraseña",
            type="password",
            placeholder="Ingrese su contraseña"
        )

        submit = st.form_submit_button("Ingresar")

    if submit:
        if mock_login(usuario, password):
            st.session_state.logged_in = True
            st.session_state.user = usuario
            st.rerun()
        else:
            st.error("Usuario o contraseña inválidos")
