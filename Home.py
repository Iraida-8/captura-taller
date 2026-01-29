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
    page_title="Login",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.sidebar.empty()

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
# LOGGED IN VIEW
# =================================
if st.session_state.logged_in and st.session_state.user:

    st.success("Logged in")

    st.write("Email:", st.session_state.user["email"])
    st.write("Nombre:", st.session_state.user["name"])
    st.write("Login count:", st.session_state.user["login_count"])

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
    # Load logo ABOVE login
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
            # -------- AUTH --------
            res = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            if not res.user:
                st.error("Credenciales inválidas")
                st.stop()

            user_id = res.user.id

            # -------- INCREMENT LOGIN COUNTER (DB-side) --------
            supabase.rpc(
                "increment_login_count",
                {"user_id": user_id}
            ).execute()

            # -------- LOAD PROFILE (SAFE, RLS-COMPATIBLE) --------
            profile_res = (
                supabase
                .table("profiles")
                .select("full_name, login_count")
                .eq("id", user_id)
                .maybe_single()
                .execute()
            )

            profile_data = (
                profile_res.data
                if profile_res and profile_res.data
                else {}
            )

            # -------- SESSION --------
            st.session_state.logged_in = True
            st.session_state.user = {
                "id": user_id,
                "email": res.user.email,
                "name": profile_data.get("full_name"),
                "login_count": profile_data.get("login_count", 0)
            }

            st.rerun()

        except Exception as e:
            st.error(str(e))
