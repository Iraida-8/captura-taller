import streamlit as st


# ============================================================
# HELPERS
# ============================================================

def has_access(user_access, permissions):
    return any(p in user_access for p in permissions)


def get_page_suffix():

    access = st.session_state.user.get("access", [])

    return " Beta" if "beta" in access else ""


def logout():

    st.session_state.logged_in = False
    st.session_state.user = None

    st.switch_page("Home.py")


# ============================================================
# NAVBAR
# ============================================================

def render_navbar():

    user = st.session_state.user

    access = user.get("access", [])

    PAGE_SUFFIX = get_page_suffix()

    # =======================================================
    # CSS
    # =======================================================

    st.markdown(
        """
<style>

div[data-testid="stHorizontalBlock"]{
    align-items:center;
}

div[data-testid="stPopover"] > button{

    width:100%;

    background:none !important;

    border:none !important;

    color:white !important;

    font-weight:700;

    font-size:14px;

    box-shadow:none !important;
}

div[data-testid="stPopover"] > button:hover{

    background:rgba(255,255,255,.12)!important;
}

div.stButton > button{

    width:100%;
}

.navbar{

    background:#151F6D;

    padding:12px 18px;

    border-radius:12px;

    margin-bottom:20px;
}

</style>
        """,
        unsafe_allow_html=True,
    )

    # =======================================================
    # BAR
    # =======================================================

    st.markdown(
        '<div class="navbar">',
        unsafe_allow_html=True,
    )

    home,\
    solicitudes,\
    gestion,\
    consultas,\
    extras,\
    gps,\
    administracion,\
    cuenta = st.columns(
        [1.0,2.2,2.7,2.4,1.3,1.9,2.2,1.3]
    )

    # =======================================================
    # HOME
    # =======================================================

    with home:

        if st.button(
            "HOME",
            use_container_width=True,
            key="nav_home",
        ):

            st.switch_page(
                "pages/dashboard_beta.py"
            )

    # =======================================================
    # SOLICITUDES Y PASES
    # =======================================================

    with solicitudes:

        with st.popover("SOLICITUDES Y PASES"):

            if has_access(
                access,
                [
                    "pase_taller",
                ]
            ):

                if st.button(
                    "Captura de Pases",
                    use_container_width=True,
                    key="nav_pases",
                ):

                    st.switch_page(
                        f"pages/3_ Solicitudes y Pases{PAGE_SUFFIX}.py"
                    )

            if has_access(
                access,
                [
                    "bonos_operador",
                ]
            ):

                if st.button(
                    "Bono Operadores",
                    use_container_width=True,
                    key="nav_bonos",
                ):

                    st.switch_page(
                        f"pages/3_ Solicitudes y Pases{PAGE_SUFFIX}.py"
                    )

    # =======================================================
    # GESTION DE ORDENES Y PASES
    # =======================================================

    with gestion:

        with st.popover("GESTIÓN DE ÓRDENES Y PASES"):
#
            if has_access(
                access,
                [
                    "autorizacion",
                ]
            ):

                if st.button(
                    "Autorización",
                    use_container_width=True,
                    key="nav_autorizacion",
                ):

                    st.switch_page(
                        f"pages/4_ Autorizacion{PAGE_SUFFIX}.py"
                    )

            if has_access(
                access,
                [
                    "gestion_viaticos",
                ]
            ):

                if st.button(
                    "Gestión de Viáticos",
                    use_container_width=True,
                    key="nav_viaticos",
                ):

                    st.switch_page(
                        f"pages/9_ Gestion Viaticos{PAGE_SUFFIX}.py"
                    )

    # =======================================================
    # CONSULTAS E HISTORIALES
    # =======================================================

    with consultas:

        with st.popover("CONSULTAS E HISTORIALES"):

            if has_access(
                access,
                [
                    "consultar_reparacion",
                ]
            ):

                if st.button(
                    "Consultar Reparación",
                    use_container_width=True,
                    key="nav_consultar_reparacion",
                ):

                    st.switch_page(
                        f"pages/1_ Consultar Reparacion{PAGE_SUFFIX}.py"
                    )

            if has_access(
                access,
                [
                    "consulta_bonos_operador",
                ]
            ):

                if st.button(
                    "Consulta de Bonos",
                    use_container_width=True,
                    key="nav_consulta_bonos",
                ):

                    st.switch_page(
                        f"pages/14_ Consulta Bonos{PAGE_SUFFIX}.py"
                    )

    # =======================================================
    # EXTRAS
    # =======================================================

    with extras:

        with st.popover("EXTRAS"):
            if has_access(
                access,
                [
                    "lector_pdf",
                ]
            ):

                if st.button(
                    "Lector PDF",
                    use_container_width=True,
                    key="nav_pdf",
                ):

                    st.switch_page(
                        f"pages/5_ Extras{PAGE_SUFFIX}.py"
                    )

            if has_access(
                access,
                [
                    "ifuel",
                ]
            ):

                if st.button(
                    "Reporte iFuel",
                    use_container_width=True,
                    key="nav_ifuel",
                ):

                    st.switch_page(
                        f"pages/5_ Extras{PAGE_SUFFIX}.py"
                    )

    # =======================================================
    # SEGUIMIENTO GPS
    # =======================================================

    with gps:

        with st.popover("SEGUIMIENTO GPS"):

            if has_access(
                access,
                [
                    "gps_tracking",
                ]
            ):

                if st.button(
                    "Rastreador GPS",
                    use_container_width=True,
                    key="nav_gps",
                ):

                    st.switch_page(
                        f"pages/11_ api_pull{PAGE_SUFFIX}.py"
                    )

    # =======================================================
    # ADMINISTRACIÓN
    # =======================================================

    with administracion:

        with st.popover("ADMINISTRACIÓN"):

            if has_access(
                access,
                [
                    "prepara_reportes",
                ]
            ):

                if st.button(
                    "Preparación de Reportes",
                    use_container_width=True,
                    key="nav_reportes",
                ):

                    st.switch_page(
                        f"pages/7_ Preparacion de Reportes{PAGE_SUFFIX}.py"
                    )

            if has_access(
                access,
                [
                    "gestion_unidades",
                ]
            ):

                if st.button(
                    "Gestión Base de Datos",
                    use_container_width=True,
                    key="nav_database",
                ):

                    st.switch_page(
                        f"pages/8_ Gestion de Base de Datos{PAGE_SUFFIX}.py"
                    )

            if has_access(
                access,
                [
                    "ai_testing",
                ]
            ):

                if st.button(
                    "Pruebas IA",
                    use_container_width=True,
                    key="nav_ai",
                ):

                    st.switch_page(
                        f"pages/12_ AI_tests{PAGE_SUFFIX}.py"
                    )

    # =======================================================
    # CUENTA
    # =======================================================

    with cuenta:

        with st.popover("CUENTA"):
                        
                        st.markdown(
                            f"**{user.get('name', 'Usuario')}**"
                        )

                        if user.get("email"):
                            st.caption(user["email"])

                        st.divider()

                        if st.button(
                            "Cerrar sesión",
                            use_container_width=True,
                            key="nav_logout",
                        ):
                            logout()

    # =======================================================
    # CLOSE NAVBAR
    # =======================================================

    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <style>

        hr{
            margin-top:0.25rem;
            margin-bottom:1rem;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )