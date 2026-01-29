import streamlit as st
import pandas as pd
from auth import require_login

require_login()

st.title("Dashboard")
# =================================
# Page configuration
# =================================
st.set_page_config(
    page_title="Autorización y Actualización de Reporte",
    layout="wide"
)

# =================================
# Google Sheets configuration
# =================================
IGLOO_ARTICULOS_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "18tFOA4prD-PWhtbc35cqKXxYcyuqGOC7"
    "/export?format=csv&gid=410297659"
)

# =================================
# Title
# =================================
st.title("📋 Consulta de Reportes (WIP)")

# =================================
# Load artículos catálogo
# =================================
@st.cache_data(ttl=3600)
def cargar_articulos_igloo():
    df = pd.read_csv(IGLOO_ARTICULOS_URL)
    df.columns = df.columns.str.strip()

    def limpiar(valor):
        return str(valor).replace("$", "").replace(",", "").strip()

    precio = df["PrecioParte"].apply(limpiar).astype(float)
    iva_raw = df["Tasaiva"].apply(limpiar).astype(float)
    iva = iva_raw.apply(lambda x: x / 100 if x >= 1 else x)

    base = pd.DataFrame({
        "Seleccionar": False,
        "Artículo": df["Parte"],
        "Descripción": df["Parte"],
        "Precio MXP": precio,
        "Iva": iva,
        "Cantidad": 1,
        "Total MXN": precio * (1 + iva),
        "Tipo Mtto": df["Tipo de reparacion"]
    })

    return base

# =================================
# SECCIÓN — SERVICIOS Y REFACCIONES
# =================================
st.divider()
st.subheader("🔧 Servicios y Refacciones")

# =================================
# Session state init
# =================================
if "mostrar_modal" not in st.session_state:
    st.session_state.mostrar_modal = False

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
# Button to open modal
# =================================
if st.button("Añadir Servicios o Refacciones"):
    st.session_state.mostrar_modal = True

# =================================
# Modal dialog
# =================================
if st.session_state.mostrar_modal:

    @st.dialog("Añadir Servicios o Refacciones")
    def modal():
        igloo_df = cargar_articulos_igloo()

        tipo_mtto = st.selectbox(
            "Tipo de Mantenimiento",
            sorted(igloo_df["Tipo Mtto"].dropna().unique())
        )

        refaccion = st.selectbox(
            "Refacción",
            igloo_df["Artículo"].tolist()
        )

        fila = igloo_df[igloo_df["Artículo"] == refaccion].iloc[0]

        st.number_input(
            "Precio de Parte MXN",
            value=float(fila["Precio MXP"]),
            disabled=True
        )

        cantidad = st.number_input(
            "Cantidad",
            min_value=1,
            value=1
        )

        if st.button("Agregar"):
            nueva = fila.copy()
            nueva["Cantidad"] = cantidad
            nueva["Total MXN"] = cantidad * fila["Precio MXP"] * (1 + fila["Iva"])

            st.session_state.articulos_df = pd.concat(
                [st.session_state.articulos_df, nueva.to_frame().T],
                ignore_index=True
            )

            st.session_state.mostrar_modal = False

        if st.button("Cancelar"):
            st.session_state.mostrar_modal = False

    modal()

# =================================
# Artículos / Actividades table
# =================================
st.divider()
st.subheader("Artículos / Actividades")

edited_df = st.data_editor(
    st.session_state.articulos_df,
    hide_index=True,
    key="editor"
)

# =================================
# Total seleccionado
# =================================
total = (
    edited_df.loc[edited_df["Seleccionar"] == True, "Total MXN"].sum()
    if not edited_df.empty
    else 0
)

st.metric("Total Seleccionado MXN", f"$ {total:,.2f}")
