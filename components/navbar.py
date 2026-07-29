import streamlit as st
import streamlit.components.v1 as components


# ==========================================================
# HELPERS
# ==========================================================

def has_access(user_access, permission):

    if permission is None:
        return True

    return permission in user_access


def get_page_suffix():

    access = st.session_state.user.get("access", [])

    return " Beta" if "beta" in access else ""


# ==========================================================
# NAVIGATION CONFIGURATION
# ==========================================================

NAVIGATION = [

    {
        "title": "HOME",

        "items": [

            {
                "label": "Dashboard",
                "permission": None,
                "page": "pages/dashboard_beta.py",
            }

        ]
    },

    {
        "title": "SOLICITUDES Y PASES",

        "items": [

            {
                "label": "Captura de Pases",
                "permission": "pase_taller",
                "page": "pages/3_ Solicitudes y Pases{suffix}.py",
            },

            {
                "label": "Bono Operadores",
                "permission": "bonos_operador",
                "page": "pages/3_ Solicitudes y Pases{suffix}.py",
            },

        ]
    },

    {
        "title": "GESTIÓN DE ÓRDENES Y PASES",

        "items": [

            {
                "label": "Autorización",
                "permission": "autorizacion",
                "page": "pages/4_ Autorizacion{suffix}.py",
            },

            {
                "label": "Gestión de Viáticos",
                "permission": "gestion_viaticos",
                "page": "pages/9_ Gestion Viaticos{suffix}.py",
            },

        ]
    },

    {
        "title": "CONSULTAS E HISTORIALES",

        "items": [

            {
                "label": "Consultar Reparación",
                "permission": "consultar_reparacion",
                "page": "pages/1_ Consultar Reparacion{suffix}.py",
            },

            {
                "label": "Consulta Bonos",
                "permission": "consulta_bonos_operador",
                "page": "pages/14_ Consulta Bonos{suffix}.py",
            },

        ]
    },

    {
        "title": "EXTRAS",

        "items": [

            {
                "label": "Lector PDF",
                "permission": "lector_pdf",
                "page": "pages/5_ Extras{suffix}.py",
            },

            {
                "label": "Reporte iFuel",
                "permission": "ifuel",
                "page": "pages/5_ Extras{suffix}.py",
            },

        ]
    },

    {
        "title": "SEGUIMIENTO GPS",

        "items": [

            {
                "label": "Rastreador GPS",
                "permission": "gps_tracking",
                "page": "pages/11_ api_pull{suffix}.py",
            },

        ]
    },

    {
        "title": "ADMINISTRACIÓN",

        "items": [

            {
                "label": "Preparación de Reportes",
                "permission": "prepara_reportes",
                "page": "pages/7_ Preparacion de Reportes{suffix}.py",
            },

            {
                "label": "Gestión Base de Datos",
                "permission": "gestion_unidades",
                "page": "pages/8_ Gestion de Base de Datos{suffix}.py",
            },

            {
                "label": "Pruebas IA",
                "permission": "ai_testing",
                "page": "pages/12_ AI_tests{suffix}.py",
            },

        ]
    },

]