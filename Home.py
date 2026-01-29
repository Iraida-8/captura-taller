from dotenv import load_dotenv
import streamlit as st
from supabase import create_client
from pathlib import Path
from PIL import Image
import os

# =================================
# Page configuration
# =================================
st.set_page_config(
    page_title="Login",
    layout="centered"
)

# =================================
# Supabase client (SAFE for all modes)
# =================================
load_dotenv(Path(__file__).parent / ".env")

SUPABASE_URL = None
SUPABASE_ANON_KEY = None

# Try Streamlit secrets (only valid in `streamlit run`)
try:
    SUPABASE_URL = st.secrets.get("SUPABASE_URL")
    SUPABASE_ANON_KEY = st.secrets.get("SUPABASE_ANON_KEY")
except Exception:
    pass

# Fallback to environment variables (local / Codespaces)
if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    st.error(
        "Supabase credentials not found.\n\n"
        "• Run with: streamlit run Home.py\n"
        "• Or define SUPABASE_URL and SUPABASE_ANON_KEY"
    )
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

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

    st.write("Sesión iniciada correctamente.")

    if st.button("Cerrar sesión"):
        supabase.auth.sign_out()
        st.session_state.logged_in = False
        st.session_state.user = None
        st.rerun()

# =================================
# LOGIN VIEW
# =================================
else:
    # ---------------------------------
    # Load logo (portable path)
    # ---------------------------------
    assets_dir = Path(__file__).parent / "assets"
    logo_path = assets_dir / "pg_brand.png"

    if logo_path.exists():
        img = Image.open(logo_path)
        if img.width > 600:
            ratio = 600 / img.width
            img = img.resize(
                (600, int(img.height * ratio)),
                Image.LANCZOS
            )
        st.image(img, width="stretch")

    st.title("Inicio de Sesión")
    st.divider()

    with st.form("login_form"):
        email = st.text_input(
            "Correo electrónico",
            placeholder="usuario@empresa.com"
        )
        password = st.text_input(
            "Contraseña",
            type="password"
        )
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

        except Exception:
            st.error("Credenciales inválidas")
