import streamlit as st
import pandas as pd
from datetime import datetime

from auth import require_login, require_access
import gspread
from google.oauth2.service_account import Credentials
import os

# =================================
# Page configuration
# =================================
st.set_page_config(
    page_title="Consulta de Reportes",
    layout="wide"
)

# =================================
# Hide sidebar
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
# Security
# =================================
require_login()
require_access("consulta_reportes")

# =================================
# Navigation
# =================================
if st.button("⬅ Volver al Dashboard"):
    st.switch_page("pages/dashboard.py")

st.divider()
st.title("📋 Consulta de Reportes")

# =================================
# Google Sheets credentials
# =================================
def get_gsheets_credentials():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]

    if "gcp_service_account" in st.secrets:
        return Credentials.from_service_account_info(
            st.secrets["gcp_service_account"], scopes=scopes
        )

    if os.path.exists("google_service_account.json"):
        return Credentials.from_service_account_file(
            "google_service_account.json", scopes=scopes
        )

    raise RuntimeError("Google Sheets credentials not found")

SPREADSHEET_ID = "1ca46k4PCbvNMvZjsgU_2MHJULADRJS5fnghLopSWGDA"

# =================================
# Load Pases (ALL companies)
# =================================
@st.cache_data(ttl=300)
def cargar_pases_unificados():
    hojas = ["IGLOO", "LINCOLN", "PICUS", "SFI", "SLP"]
    client = gspread.authorize(get_gsheets_credentials())

    dfs = []

    for hoja in hojas:
        try:
            ws = client.open_by_key(SPREADSHEET_ID).worksheet(hoja)
            data = ws.get_all_records()
            if data:
                df = pd.DataFrame(data)
                dfs.append(df)
        except Exception:
            pass

    if not dfs:
        return pd.DataFrame()

    df = pd.concat(dfs, ignore_index=True)

    # Normalize headers
    df.columns = df.columns.str.strip()
    df = df.rename(columns={
        "No. de Folio": "Folio",
        "Fecha de Captura": "Fecha",
        "Tipo de Proveedor": "Proveedor",
    })

    df["Folio"] = df["Folio"].astype(str)
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")

    return df


# =================================
# Load SERVICES
# =================================
@st.cache_data(ttl=300)
def cargar_services():
    client = gspread.authorize(get_gsheets_credentials())
    ws = client.open_by_key(SPREADSHEET_ID).worksheet("SERVICES")

    data = ws.get_all_records()
    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)

    # Normalize headers
    df.columns = df.columns.str.strip()
    df = df.rename(columns={
        "No. de Folio": "Folio",
        "Iva": "IVA"
    })

    df["Folio"] = df["Folio"].astype(str)

    return df


pases_df = cargar_pases_unificados()
services_df = cargar_services()

# =================================
# Filters
# =================================
st.subheader("Filtros")

c1, c2 = st.columns(2)

with c1:
    empresas = sorted(pases_df["Empresa"].dropna().unique()) if not pases_df.empty else []
    empresa_sel = st.selectbox(
        "Empresa",
        ["Todas"] + empresas
    )

with c2:
    folio_sel = st.text_input("No. de Folio")

# =================================
# Apply filters to Pases
# =================================
df_pases = pases_df.copy()

if empresa_sel != "Todas":
    df_pases = df_pases[df_pases["Empresa"] == empresa_sel]

if folio_sel:
    df_pases = df_pases[df_pases["Folio"].str.contains(folio_sel, na=False)]

# =================================
# Display Pases
# =================================
st.divider()
st.subheader("Pases de Taller")

if df_pases.empty:
    st.warning("No se encontraron pases con los filtros seleccionados.")
    st.stop()

st.dataframe(
    df_pases[
        ["Folio", "Empresa", "Fecha", "Proveedor", "Estado"]
    ],
    hide_index=True,
    width="stretch"
)

# =================================
# Filter SERVICES by Folio
# =================================
folios = df_pases["Folio"].unique()

df_services = services_df[
    services_df["Folio"].isin(folios)
].copy()

# =================================
# Display SERVICES
# =================================
st.divider()
st.subheader("Servicios y Refacciones")

if df_services.empty:
    st.info("No hay servicios asociados a los pases seleccionados.")
else:
    st.dataframe(
        df_services[
            [
                "Folio",
                "Parte",
                "TipoCompra",
                "Precio MXP",
                "IVA",
                "Cantidad",
                "Total MXN",
                "Fecha Mod"
            ]
        ],
        hide_index=True,
        width="stretch"
    )
