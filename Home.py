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

.stApp {
    background-color: #0e1117;
}

.block-container {
    max-width: 420px;
    padding-top: 4rem;
    padding-bottom: 3rem;
}

img {
    display:block;
    margin:auto;
    margin-bottom:2rem;
    transform:scale(1.18);
}

form[data-testid="stForm"] {
    background-color:#161b22;
    padding:2rem;
    border-radius:16px;
    box-shadow:0 0 0 1px rgba(255,255,255,0.06);
}

h1 {
    text-align:center;
    font-size:1.6rem;
    margin-bottom:1.2rem;
}

div.stButton > button {
    width:100%;
    padding:0.75rem;
    border-radius:10px;
    font-weight:600;
}

.small-text {
    text-align:center;
    margin-top:1rem;
    font-size:0.85rem;
    color:#8b949e;
}
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
st.session_state.setdefault("auth_view", "login")

# =================================
# PASSWORD RECOVERY DETECTION
# =================================

params = st.query_params
is_recovery_mode = False

if (
    params.get("type") == "recovery"
    and params.get("token")
):
    try:
        supabase.auth.verify_otp({
            "type": "recovery",
            "token": params.get("token")
        })

        is_recovery_mode = True

    except Exception as e:
        st.error(
            "El enlace de recuperación es inválido o expiró"
        )
        st.stop()

# =================================
# LOGIN / RESET REQUEST VIEW
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


# =================================
# LOGIN VIEW
# =================================
if st.session_state.auth_view == "login":

    st.title("Inicio de Sesión")

    with st.form("login_form"):

        email = st.text_input(
            "Correo electrónico",
            placeholder="usuario@palosgarza.com",
            key="login_email"
        )

        password = st.text_input(
            "Contraseña",
            type="password",
            key="login_password"
        )

        login_clicked = st.form_submit_button(
            "Ingresar",
            use_container_width=True
        )

    # visually aligned with form
    reset_clicked = st.button(
        "Recuperar contraseña",
        use_container_width=True
    )

    if login_clicked:
        try:
            res = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            if not res.user:
                st.error("Credenciales inválidas")
                st.stop()

            user_id = res.user.id

            profile_res = (
                supabase
                .table("profiles")
                .select("full_name, login_count, role, access")
                .eq("id", user_id)
                .maybe_single()
                .execute()
            )

            profile_data = (
                profile_res.data
                if profile_res and profile_res.data
                else {}
            )

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

    if reset_clicked:
        st.session_state.auth_view = "reset_request"
        st.rerun()

# =================================
# RESET PASSWORD VIEW (OTP FLOW)
# =================================

if st.session_state.auth_view == "reset_request":

    st.title("Restablecer contraseña")

    reset_email = st.text_input(
        "Correo electrónico",
        placeholder="usuario@palosgarza.com",
        key="reset_email"
    )

    recovery_code = st.text_input(
        "Código de recuperación",
        placeholder="Ingresa el código recibido",
        key="recovery_code"
    )

    new_password = st.text_input(
        "Nueva contraseña",
        type="password",
        key="new_password_reset"
    )

    confirm_password = st.text_input(
        "Confirmar contraseña",
        type="password",
        key="confirm_password_reset"
    )

    col1, col2 = st.columns(2)

    with col1:
        send_code = st.button(
            "Enviar código",
            use_container_width=True
        )

    with col2:
        back_btn = st.button(
            "Volver",
            use_container_width=True
        )

    if send_code:
        if not reset_email:
            st.warning("Ingresa un correo")
        else:
            try:
                supabase.auth.reset_password_for_email(
                    reset_email
                )

                st.success(
                    "Se envió el código de recuperación al correo"
                )

            except Exception as e:
                st.error(str(e))

    update_clicked = st.button(
        "Actualizar contraseña",
        use_container_width=True
    )

    if update_clicked:

        if not reset_email:
            st.error("Falta correo")
            st.stop()

        if not recovery_code:
            st.error("Falta código de recuperación")
            st.stop()

        if new_password != confirm_password:
            st.error("Las contraseñas no coinciden")
            st.stop()

        if len(new_password) < 6:
            st.error("Mínimo 6 caracteres")
            st.stop()

        try:
            supabase.auth.verify_otp({
                "email": reset_email,
                "token": recovery_code,
                "type": "recovery"
            })

            supabase.auth.update_user({
                "password": new_password
            })

            supabase.auth.sign_out()

            st.success(
                "Contraseña actualizada correctamente"
            )

            st.session_state.auth_view = "login"
            st.rerun()

        except Exception as e:
            st.error(
                f"Error: {str(e)}"
            )

    if back_btn:
        st.session_state.auth_view = "login"
        st.rerun()