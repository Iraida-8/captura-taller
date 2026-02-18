import streamlit as st
from supabase import create_client
import os
from dotenv import load_dotenv
from pathlib import Path
from PIL import Image

# =================================
# Page configuration
# =================================
st.set_page_config(
    page_title="Portal Taller",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# =================================
# CSS Styling
# =================================
st.markdown("""
<style>
[data-testid="stSidebar"] { display: none; }
.stApp { background-color: #0e1117; }
.block-container { max-width: 420px; padding-top: 4.2rem; padding-bottom: 3rem; }
img { display:block; margin:auto; margin-bottom:2rem; transform:scale(1.18); }
form[data-testid="stForm"] {
    background-color:#161b22;
    padding:2rem;
    border-radius:16px;
    box-shadow:0 0 0 1px rgba(255,255,255,0.06);
}
h1 { text-align:center; font-size:1.6rem; }
</style>
""", unsafe_allow_html=True)

# =================================
# Supabase setup
# =================================
load_dotenv(Path(__file__).parent / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    st.error("Supabase credentials not found")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# =================================
# Session state
# =================================
st.session_state.setdefault("logged_in", False)
st.session_state.setdefault("user", None)

# =================================
# Detect Recovery Session (Correct Method)
# =================================
session = supabase.auth.get_session()

if session and session.user and not st.session_state.get("logged_in"):

    st.title("Restablecer contraseña")

    with st.form("reset_password_form"):
        new_password = st.text_input("Nueva contraseña", type="password")
        confirm_password = st.text_input("Confirmar contraseña", type="password")
        submit_reset = st.form_submit_button("Actualizar contraseña")

    if submit_reset:

        if new_password != confirm_password:
            st.error("Las contraseñas no coinciden")
            st.stop()

        if len(new_password) < 6:
            st.error("La contraseña debe tener al menos 6 caracteres")
            st.stop()

        try:
            supabase.auth.update_user({"password": new_password})
            supabase.auth.sign_out()
            st.success("Contraseña actualizada correctamente")
            st.info("Ya puedes iniciar sesión")
        except Exception as e:
            st.error(f"Error actualizando contraseña: {e}")

        st.stop()

# =================================
# LOGIN VIEW
# =================================
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

st.divider()
st.title("Inicio de Sesión")

# Email outside form
email = st.text_input(
    "Correo electrónico",
    placeholder="usuario@palosgarza.com"
)

with st.form("login_form"):
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

        if not res.user:
            st.error("Credenciales inválidas")
            st.stop()

        user_id = res.user.id

        supabase.rpc(
            "increment_login_count",
            {"user_id": user_id}
        ).execute()

        profile_res = (
            supabase
            .table("profiles")
            .select("full_name, login_count, role, access")
            .eq("id", user_id)
            .maybe_single()
            .execute()
        )

        profile_data = profile_res.data if profile_res and profile_res.data else {}

        st.session_state.logged_in = True
        st.session_state.user = {
            "id": user_id,
            "email": res.user.email,
            "name": profile_data.get("full_name"),
            "login_count": profile_data.get("login_count", 0),
            "role": profile_data.get("role", "user"),
            "access": profile_data.get("access", [])
        }

        st.switch_page("pages/dashboard.py")

    except Exception as e:
        st.error(str(e))

# =================================
# Forgot Password Button
# =================================
st.markdown("---")

if st.button("¿Olvidaste tu contraseña?"):

    if not email:
        st.warning("Ingresa tu correo primero")
    else:
        try:
            supabase.auth.reset_password_for_email(
                email,
                {
                    "redirect_to": "https://captura-taller-cthtp8mj8fhvgu5ygugxye.streamlit.app"
                }
            )
            st.success("Correo de recuperación enviado")
        except Exception as e:
            st.error(f"No se pudo enviar el correo: {e}")
