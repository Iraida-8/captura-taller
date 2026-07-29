import streamlit as st
from pathlib import Path


# =====================================================
# HELPERS
# =====================================================

def _has_access(user_access, permissions):
    return any(p in user_access for p in permissions)


def _page_suffix():

    access = st.session_state.user.get("access", [])

    return " Beta" if "beta" in access else ""


def _logout():

    st.session_state.logged_in = False
    st.session_state.user = None

    st.switch_page("Home.py")


# =====================================================
# NAVBAR
# =====================================================

def render_navbar():

    user = st.session_state.user

    access = user.get("access", [])
    role = (user.get("role") or "").lower()

    PAGE_SUFFIX = _page_suffix()

    # -------------------------------------------------
    # NAVBAR CSS
    # -------------------------------------------------

    st.markdown("""
    <style>

    div[data-testid="stHorizontalBlock"]{
        align-items:center;
    }

    .omega-logo{

        font-size:34px;
        font-weight:800;

        color:#151F6D;

        letter-spacing:1px;

        margin-top:8px;
    }

    .omega-divider{
        border-top:1px solid #D9D9D9;
        margin-top:8px;
        margin-bottom:8px;
    }

    </style>
    """, unsafe_allow_html=True)

    # -------------------------------------------------
    # TOP ROW
    # -------------------------------------------------

    logo, nav, account = st.columns([1.2, 6.5, 1.5])

    with logo:

        st.markdown(
            '<div class="omega-logo">Ω OMEGA</div>',
            unsafe_allow_html=True
        )

    with account:

        with st.popover(user["name"]):

            st.write(user["email"])

            st.divider()

            if st.button(
                "Cerrar sesión",
                use_container_width=True,
                key="logout_navbar",
            ):
                _logout()

    # -------------------------------------------------
    # MENU ROW
    # -------------------------------------------------

    with nav:

        home, solicitudes, gestion, consultas, extras, admin = st.columns(6)

        # ===========================
        # HOME
        # ===========================

        with home:

            if st.button(
                "🏠 Home",
                use_container_width=True,
                key="nav_home",
            ):
                st.switch_page("pages/dashboard_beta.py")

        # ===========================
        # SOLICITUDES
        # ===========================

        with solicitudes:

            with st.popover("🏭 Solicitudes"):

                if _has_access(
                    access,
                    [
                        "pase_taller",
                        "bonos_operador",
                    ],
                ):

                    if st.button(
                        "Solicitudes y Pases",
                        use_container_width=True,
                        key="nav_solicitudes",
                    ):

                        st.switch_page(
                            f"pages/3_ Solicitudes y Pases{PAGE_SUFFIX}.py"
                        )

        # ===========================
        # GESTION
        # ===========================

        with gestion:

            with st.popover("📋 Gestión"):

                if _has_access(
                    access,
                    [
                        "autorizacion",
                        "gestion_viaticos",
                    ],
                ):

                    if st.button(
                        "Autorización",
                        use_container_width=True,
                        key="nav_gestion",
                    ):

                        st.switch_page(
                            f"pages/4_ Autorizacion{PAGE_SUFFIX}.py"
                        )

    st.markdown(
        '<div class="omega-divider"></div>',
        unsafe_allow_html=True
    )