import streamlit as st
from supabase import create_client
from pathlib import Path
from PIL import Image

# =================================
# Page configuration
# =================================
st.set_page_config(
    page_title="Login",
    layout="centered"
)

# =================================
# Supabase client (Streamlit Cloud)
# =================================
try:
    supabase = create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_ANON_KEY"]
    )
except Exception:
    st.error("Supabase credentials not found. Check Streamlit Secrets.")
    st.stop()

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
            st.error("Credenciales inválidas")
