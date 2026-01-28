import streamlit as st
from PIL import Image
from supabase import create_client
from dotenv import load_dotenv
import os

# =================================
# Load environment variables
# =================================
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    st.error("Supabase credentials not found. Check .env file.")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# =================================
# Page configuration
# =================================
st.set_page_config(
    page_title="Login",
    layout="centered"
)

# =================================
# Session state
# =================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "user" not in st.session_state:
    st.session_state.user = None

# =================================
# LOGGED IN VIEW
# =================================
if st.session_state.logged_in and st.session_state.user:

    st.success(f"Bienvenido, {st.session_state.user['email']}")
    st.title("Home Page Super Pro")
    st.divider()

    if st.button("Cerrar sesión"):
        supabase.auth.sign_out()
        st.session_state.logged_in = False
        st.session_state.user = None
        st.rerun()

# =================================
# LOGIN VIEW
# =================================
else:
    logo_path = "/workspaces/captura-taller/PG Brand.png"

    try:
        img = Image.open(logo_path)
        if img.width > 600:
            ratio = 600 / img.width
            img = img.resize((600, int(img.height * ratio)), Image.LANCZOS)
        st.image(img, width="stretch")
    except Exception:
        pass

    st.title("Inicio de Sesión")
    st.divider()

    with st.form("login_form"):
        email = st.text_input("Correo electrónico")
        password = st.text_input("Contraseña", type="password")
        submit = st.form_submit_button("Ingresar")

    if submit:
        try:
            res = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            if res.user:
                st.session_state.logged_in = True
                st.session_state.user = {
                    "id": res.user.id,
                    "email": res.user.email
                }
                st.rerun()
            else:
                st.error("Credenciales inválidas")

        except Exception as e:
            st.error("Error al iniciar sesión")
