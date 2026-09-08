import streamlit as st
from auth import require_login, require_access
from pages.css import load_css
from supabase import create_client


# =================================
# RELEASE CHANNEL
# =================================
APP_CHANNEL = "BETA"
# APP_CHANNEL = "RELEASE"

DASHBOARD_PAGE = (
    "pages/dashboard_beta.py"
    if APP_CHANNEL == "BETA"
    else "pages/dashboard.py"
)

# =================================
# Page configuration
# =================================
st.set_page_config(
    page_title=(
        "AI STOOF BETA"
        if APP_CHANNEL.upper() == "BETA"
        else "AI STOOF"
    ),
    layout="wide"
)

# -------------------------------
# PAGE STYLE
# -------------------------------
load_css()

# =================================
# Navigation
# =================================
st.write("")

if st.button("⬅ Volver al Dashboard"):
    st.switch_page(DASHBOARD_PAGE)

st.divider()

# =================================
# Security gates
# =================================
require_login()

user = st.session_state.user

require_access("ai_testing")

# =================================
# ROLE
# =================================
user_role = str(
    user.get("role", "")
).strip().lower()

if user_role != "field_user":
    st.info("Comming soon")
    st.stop()


# =================================
# SUPABASE
# =================================
@st.cache_resource
def get_supabase():

    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_SERVICE_KEY"]
    )

supabase = get_supabase()

# =================================
# ACTIVITY LOG
# =================================
def log_activity(action, page):

    try:

        supabase.table("user_activity_log").insert({

            "user_id": user.get("id"),
            "user_name": user.get("name"),
            "login_counter": st.session_state.get("login_counter"),
            "action": action,
            "page": page,

        }).execute()

    except Exception as e:
        print(e)

# =================================
# PAGE ACTIVITY
# =================================
log_activity(
    "Abrió módulo AI Tester",
    "AI Tester"
)

# =================================
# HEADER
# =================================
st.title("💳 AI Tester")