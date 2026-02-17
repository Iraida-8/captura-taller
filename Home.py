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
# Convert Supabase hash fragment to query params
# =================================
st.markdown("""
<script>
const hash = window.location.hash;
if (hash && hash.includes("access_token")) {
    const query = hash.substring(1);
    const newUrl = window.location.origin + window.location.pathname + "?" + query;
    window.location.replace(newUrl);
}
</script>
""", unsafe_allow_html=True)


# =================================
# CSS Styling
# =================================
st.markdown(
    """
    <style>
    /* Hide sidebar */
    [data-testid="stSidebar"] { display: none; }

    /* Page background */
    .stApp {
        background-color: #0e1117;
    }

    /* Main width + centering */
    .block-container {
        max-width: 420px;
        padding-top: 4.2rem;   
        padding-bottom: 3rem;
    }

    /* =========================
       LOGO
       ========================= */
    img {
        display: block;
        margin-left: auto;
        margin-right: auto;
        margin-bottom: 2rem;
        transform: scale(1.18);   
    }

    /* =========================
       AUTH CARD
       ========================= */
    form[data-testid="stForm"] {
        background-color: #161b22;
        padding: 2rem;
        border-radius: 16px;
        box-shadow: 0 0 0 1px rgba(255,255,255,0.06);
    }

    /* Title */
    h1 {
        text-align: center;
        font-size: 1.6rem;
        margin-bottom: 0.3rem;
    }

    /* Divider */
    hr {
        margin: 1rem 0 1.4rem 0;
    }

    /* Inputs */
    input {
        font-size: 1rem !important;
        padding: 0.7rem !important;
        border-radius: 10px !important;
    }

    /* Labels */
    label {
        font-size: 0.9rem !important;
        font-weight: 500;
    }

    /* =========================
       CENTERED BUTTON
       ========================= */
    div.stButton > button,
    button[kind="primary"] {
        width: auto;             
        min-width: 180px;
        display: block;
        margin-left: auto;
        margin-right: auto;
        padding: 0.75rem 2rem;
        border-radius: 12px;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True
)

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
# Handle Supabase recovery token
# =================================
params = st.query_params

if params.get("type") == "recovery":
    st.title("Restablecer contraseña")

    access_token = params.get("access_token")
    refresh_token = params.get("refresh_token")

    if not access_token or not refresh_token:
        st.error("Token de recuperación inválido o expirado")
        st.stop()

    # Set the session using recovery tokens
    try:
        supabase.auth.set_session(access_token, refresh_token)
    except Exception:
        st.error("El enlace ha expirado o es inválido")
        st.stop()

    with st.form("reset_password_form"):
        new_password = st.text_input(
            "Nueva contraseña",
            type="password"
        )
        confirm_password = st.text_input(
            "Confirmar contraseña",
            type="password"
        )
        reset_submit = st.form_submit_button("Actualizar contraseña")

    if reset_submit:
        if new_password != confirm_password:
            st.error("Las contraseñas no coinciden")
            st.stop()

        if len(new_password) < 6:
            st.error("La contraseña debe tener al menos 6 caracteres")
            st.stop()

        supabase.auth.update_user({
            "password": new_password
        })

        st.success("Contraseña actualizada correctamente")

        # Clear recovery params
        st.query_params.clear()

        st.info("Ya puedes iniciar sesión")
        st.stop()


# =================================
# Session state
# =================================
st.session_state.setdefault("logged_in", False)
st.session_state.setdefault("user", None)

# =================================
# LOGIN VIEW ONLY
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

with st.form("login_form"):
    email = st.text_input(
        "Correo electrónico",
        placeholder="usuario@palosgarza.com"
    )
    password = st.text_input(
        "Contraseña",
        type="password"
    )
    submit = st.form_submit_button("Ingresar")

if submit:
    try:
        # =================================
        # AUTH
        # =================================
        res = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })

        if not res.user:
            st.error("Credenciales inválidas")
            st.stop()

        user_id = res.user.id

        # =================================
        # Increment login counter
        # =================================
        supabase.rpc(
            "increment_login_count",
            {"user_id": user_id}
        ).execute()

        # =================================
        # Load profile
        # =================================
        profile_res = (
            supabase
            .table("profiles")
            .select("full_name, login_count, role, access")
            .eq("id", user_id)
            .maybe_single()
            .execute()
        )

        profile_data = profile_res.data if profile_res and profile_res.data else {}

        # =================================
        # Session bootstrap
        # =================================
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