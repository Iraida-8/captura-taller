import streamlit as st
import pandas as pd
from datetime import datetime, date

from auth import require_login, require_access

import gspread
from google.oauth2.service_account import Credentials
import os

# =================================
# Page configuration (MUST BE FIRST)
# =================================
st.set_page_config(
    page_title="Autorización y Actualización de Reporte",
    layout="wide"
)

# =================================
# Hide sidebar completely
# =================================
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        display: none;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# =================================
# Security gates
# =================================
require_login()
require_access("autorizacion")

# =================================
# Top navigation
# =================================
if st.button("⬅ Volver al Dashboard"):
    st.switch_page("pages/dashboard.py")

st.divider()

# =================================
# Google Sheets credentials
# =================================
def get_gsheets_credentials():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]

    if "gcp_service_account" in st.secrets:
        return Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=scopes
        )

    if os.path.exists("google_service_account.json"):
        return Credentials.from_service_account_file(
            "google_service_account.json",
            scopes=scopes
        )

    raise RuntimeError("Google Sheets credentials not found")

# =================================
# Load Pase de Taller data (REAL)
# =================================
@st.cache_data(ttl=300)
def cargar_pases_taller():
    SPREADSHEET_ID = "1ca46k4PCbvNMvZjsgU_2MHJULADRJS5fnghLopSWGDA"
    hojas = ["IGLOO", "LINCOLN", "PICUS", "SFI", "SLP"]

    creds = get_gsheets_credentials()
    client = gspread.authorize(creds)

    dfs = []

    for hoja in hojas:
        try:
            ws = client.open_by_key(SPREADSHEET_ID).worksheet(hoja)
            records = ws.get_all_records()
            if records:
                df = pd.DataFrame(records)
                df["Empresa"] = hoja
                dfs.append(df)
        except Exception:
            pass

    if not dfs:
        return pd.DataFrame()

    df = pd.concat(dfs, ignore_index=True)

    # Normalize / rename expected columns
    df.rename(columns={
        "No. de Folio": "NoFolio",
        "Fecha de Captura": "Fecha",
        "Tipo de Proveedor": "Proveedor",
    }, inplace=True)

    # Parse dates safely
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")

    return df

pases_df = cargar_pases_taller()

# =================================
# Page title
# =================================
st.title("📋 Autorización y Actualización de Reporte")

# =================================
# Session State
# =================================
if "buscar_trigger" not in st.session_state:
    st.session_state.buscar_trigger = False

if "modal_reporte" not in st.session_state:
    st.session_state.modal_reporte = None

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
# TOP 10 EN CURSO
# =================================
st.subheader("Últimos 10 Pases de Taller (En Curso / Nuevo)")

if pases_df.empty:
    st.info("No hay pases de taller registrados.")
else:
    top10 = (
        pases_df[pases_df["Estado"] == "En Curso / Nuevo"]
        .sort_values("Fecha", ascending=False)
        .head(10)
        [["NoFolio", "Empresa", "Fecha", "Proveedor", "Estado"]]
    )

    st.dataframe(top10, hide_index=True, use_container_width=True)

# =================================
# BUSCAR
# =================================
st.divider()
st.subheader("Buscar Pase de Taller")

f1, f2, f3, f4 = st.columns(4)

with f1:
    f_folio = st.text_input("No. de Folio")

with f2:
    f_empresa = st.text_input("Empresa")

with f3:
    f_estado = st.selectbox(
        "Estado",
        ["", "En Curso / Nuevo", "Cerrado", "Cancelado"]
    )

with f4:
    f_fecha = st.date_input("Fecha", value=None)

if st.button("Buscar"):
    st.session_state.buscar_trigger = True

# =================================
# RESULTADOS
# =================================
if st.session_state.buscar_trigger:

    if pases_df.empty:
        st.warning("No hay datos para buscar.")
        st.stop()

    resultados = pases_df.copy()

    if f_folio:
        resultados = resultados[resultados["NoFolio"].astype(str).str.contains(f_folio, case=False)]

    if f_empresa:
        resultados = resultados[resultados["Empresa"].astype(str).str.contains(f_empresa, case=False)]

    if f_estado:
        resultados = resultados[resultados["Estado"] == f_estado]

    if f_fecha:
        resultados = resultados[resultados["Fecha"].dt.date == f_fecha]

    if resultados.empty:
        st.warning("No se encontraron resultados.")
        st.stop()

    st.divider()
    st.subheader("Resultados de Búsqueda")

    for _, row in resultados.iterrows():
        c1, c2, c3, c4, c5, c6 = st.columns([1, 2, 2, 2, 2, 1])

        with c1:
            label = "Editar" if row["Estado"] == "En Curso / Nuevo" else "Ver"
            if st.button(label, key=f"accion_{row['NoFolio']}"):
                st.session_state.modal_reporte = row.to_dict()

        c2.write(row["NoFolio"])
        c3.write(row["Empresa"])
        c4.write(row["Proveedor"])
        c5.write(row["Estado"])
        c6.write(row["Fecha"].date() if pd.notna(row["Fecha"]) else "")

# =================================
# MODAL
# =================================
if st.session_state.modal_reporte:

    reporte = st.session_state.modal_reporte
    editable = reporte["Estado"] == "En Curso / Nuevo"

    @st.dialog("Detalle del Pase de Taller")
    def modal():

        st.markdown(f"**No. de Folio:** {reporte['NoFolio']}")
        st.markdown(f"**Empresa:** {reporte['Empresa']}")
        st.markdown(f"**Fecha:** {reporte['Fecha']}")
        st.markdown(f"**Proveedor:** {reporte['Proveedor']}")

        nuevo_estado = st.selectbox(
            "Estado",
            ["En Curso / Nuevo", "Cerrado", "Cancelado"],
            index=["En Curso / Nuevo", "Cerrado", "Cancelado"].index(reporte["Estado"]),
            disabled=not editable
        )

        if reporte["Estado"] != "En Curso / Nuevo" and nuevo_estado == "En Curso / Nuevo":
            st.error("No es posible regresar a En Curso / Nuevo.")
            st.stop()

        st.divider()
        st.subheader("Servicios y Refacciones")

        st.data_editor(
            st.session_state.articulos_df,
            hide_index=True,
            disabled=not editable
        )

        total = (
            st.session_state.articulos_df["Total MXN"].sum()
            if not st.session_state.articulos_df.empty
            else 0
        )

        st.metric("Total MXN", f"$ {total:,.2f}")

        if st.button("Cerrar"):
            st.session_state.modal_reporte = None

    modal()
