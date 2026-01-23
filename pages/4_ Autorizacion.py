import streamlit as st
import pandas as pd
from datetime import date

# =================================
# Page configuration
# =================================
st.set_page_config(
    page_title="Autorización y Actualización de Reporte",
    layout="wide"
)

st.title("📋 Autorización y Actualización de Reporte")

# =================================
# Session state
# =================================
if "buscar_ejecutado" not in st.session_state:
    st.session_state.buscar_ejecutado = False

if "resultados_busqueda" not in st.session_state:
    st.session_state.resultados_busqueda = pd.DataFrame()

if "reporte_en_edicion" not in st.session_state:
    st.session_state.reporte_en_edicion = None

if "articulos_df" not in st.session_state:
    st.session_state.articulos_df = pd.DataFrame(columns=[
        "Seleccionar",
        "Artículo",
        "Descripción",
        "Precio MXP",
        "Iva",
        "Cantidad",
        "Total MXN",
        "Tipo Mtto"
    ])

# =================================
# MOCK DATA — Simula Captura Pase
# =================================
def cargar_mock_reportes():
    return pd.DataFrame([
        {
            "No. de Folio": "IG00001",
            "Empresa": "IGLOO TRANSPORT",
            "Estado": "En Curso / Nuevo",
            "Fecha de Reporte": date.today(),
            "Tipo de Proveedor": "Interno"
        },
        {
            "No. de Folio": "IG00002",
            "Empresa": "IGLOO TRANSPORT",
            "Estado": "Cerrado",
            "Fecha de Reporte": date.today(),
            "Tipo de Proveedor": "Externo"
        },
        {
            "No. de Folio": "IG00003",
            "Empresa": "LINCOLN FREIGHT",
            "Estado": "En Curso / Nuevo",
            "Fecha de Reporte": date.today(),
            "Tipo de Proveedor": "Externo"
        }
    ])

# =================================
# TOP 10
# =================================
st.divider()
st.subheader("Últimos 10 Reportes En Curso / Nuevo")

top10 = cargar_mock_reportes()
top10 = top10[top10["Estado"] == "En Curso / Nuevo"].head(10)

st.dataframe(top10, hide_index=True, use_container_width=True)

# =================================
# BUSCAR PASE DE TALLER
# =================================
st.divider()
st.subheader("🔍 Buscar Pase de Taller")

f1, f2, f3, f4 = st.columns(4)

with f1:
    filtro_folio = st.text_input("No. de Folio")

with f2:
    filtro_empresa = st.text_input("Empresa")

with f3:
    filtro_estado = st.selectbox(
        "Estado",
        ["", "En Curso / Nuevo", "Cerrado", "Cancelado"]
    )

with f4:
    filtro_fecha = st.date_input("Fecha de Reporte", value=None)

st.markdown("###")

if st.button("Buscar", type="primary"):
    if not any([filtro_folio, filtro_empresa, filtro_estado, filtro_fecha]):
        st.warning("Debes seleccionar al menos un filtro.")
    else:
        # IGNORE FILTERS — always return mock data
        st.session_state.resultados_busqueda = cargar_mock_reportes()
        st.session_state.buscar_ejecutado = True

# =================================
# RESULTADOS
# =================================
if st.session_state.buscar_ejecutado:

    st.divider()
    st.subheader("Resultados de la Búsqueda")

    for i, row in st.session_state.resultados_busqueda.iterrows():

        c1, c2, c3, c4, c5, c6 = st.columns([1, 2, 2, 2, 2, 2])

        with c1:
            if st.button("Editar", key=f"editar_{i}"):
                st.session_state.reporte_en_edicion = row.to_dict()
                st.rerun()

        with c2:
            st.write(row["No. de Folio"])
        with c3:
            st.write(row["Empresa"])
        with c4:
            st.write(row["Estado"])
        with c5:
            st.write(row["Fecha de Reporte"])
        with c6:
            st.write(row["Tipo de Proveedor"])

# =================================
# MODAL — EDITAR PASE
# =================================
if st.session_state.reporte_en_edicion:

    reporte = st.session_state.reporte_en_edicion

    @st.dialog("Editar Pase de Taller")
    def editar_pase():

        st.text_input("No. de Folio", reporte["No. de Folio"], disabled=True)
        st.text_input("Empresa", reporte["Empresa"], disabled=True)
        st.text_input("Fecha de Reporte", str(reporte["Fecha de Reporte"]), disabled=True)
        st.text_input("Proveedor", reporte["Tipo de Proveedor"], disabled=True)

        nuevo_estado = st.selectbox(
            "Estado",
            ["En Curso / Nuevo", "Cerrado", "Cancelado"],
            index=["En Curso / Nuevo", "Cerrado", "Cancelado"].index(reporte["Estado"])
        )

        if reporte["Estado"] == "En Curso / Nuevo":
            st.divider()
            st.subheader("🔧 Servicios y Refacciones")

            st.data_editor(
                st.session_state.articulos_df,
                hide_index=True,
                use_container_width=True
            )

        st.divider()

        if st.button("Guardar Cambios", type="primary"):
            st.success("Cambios guardados (mock)")
            st.session_state.reporte_en_edicion = None
            st.rerun()

        if st.button("Cerrar"):
            st.session_state.reporte_en_edicion = None
            st.rerun()

    editar_pase()
