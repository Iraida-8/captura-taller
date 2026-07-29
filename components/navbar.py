import streamlit as st

def render_navbar():

    user = st.session_state.user
    access = user.get("access", [])

    PAGE_SUFFIX = " Beta" if "beta" in access else ""

    NAVIGATION = [
        {
            "title": "🏭 Solicitudes",
            "items": [
                {
                    "label": "Solicitudes y Pases",
                    "page": f"pages/3_ Solicitudes y Pases{PAGE_SUFFIX}.py",
                    "access": ["pase_taller", "bonos_operador"],
                },
            ],
        },

        {
            "title": "📋 Gestión",
            "items": [
                {
                    "label": "Autorización",
                    "page": f"pages/4_ Autorizacion{PAGE_SUFFIX}.py",
                    "access": ["autorizacion", "gestion_viaticos"],
                },
            ],
        },

        {
            "title": "🔍 Consultas",
            "items": [
                {
                    "label": "Historial Reparación",
                    "page": f"pages/1_ Consultar Reparacion{PAGE_SUFFIX}.py",
                    "access": ["consultar_reparacion"],
                },
                {
                    "label": "Bonos Operadores",
                    "page": f"pages/14_ Consulta Bonos{PAGE_SUFFIX}.py",
                    "access": ["consulta_bonos_operador"],
                },
            ],
        },

        {
            "title": "⚙ Extras",
            "items": [
                {
                    "label": "Extras",
                    "page": f"pages/5_ Extras{PAGE_SUFFIX}.py",
                    "access": ["ifuel", "lector_pdf"],
                },
                {
                    "label": "GPS",
                    "page": f"pages/11_ api_pull{PAGE_SUFFIX}.py",
                    "access": ["gps_tracking"],
                },
            ],
        },

        {
            "title": "🗄 Administración",
            "items": [
                {
                    "label": "Reportes",
                    "page": f"pages/7_ Preparacion de Reportes{PAGE_SUFFIX}.py",
                    "access": ["prepara_reportes"],
                },
                {
                    "label": "Base de Datos",
                    "page": f"pages/8_ Gestion de Base de Datos{PAGE_SUFFIX}.py",
                    "access": ["gestion_unidades"],
                },
                {
                    "label": "IA",
                    "page": f"pages/12_ AI_tests{PAGE_SUFFIX}.py",
                    "access": ["ai_testing"],
                },
            ],
        },
    ]