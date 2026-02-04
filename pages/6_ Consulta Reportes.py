import streamlit as st
import pandas as pd
from datetime import datetime, date

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
    [data-testid="stSidebar"] { display: none; }
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
st.title("📊 Consulta de Reportes")

# =================================
# Google Sheets credentials
# =================================
def get_gsheets_credentials():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]

    try:
        if "gcp_service_account" in st.secrets:
            return Credentials.from_service_account_info(
                st.secrets["gcp_service_account"], scopes=scopes
            )
    except Exception:
        pass

    if os.path.exists("google_service_account.json"):
        return Credentials.from_service_account_file(
            "google_service_account.json", scopes=scopes
        )

    raise RuntimeError("Google Sheets credentials not found")

SPREADSHEET_ID = "1ca46k4PCbvNMvZjsgU_2MHJULADRJS5fnghLopSWGDA"

# =================================
# Load PASES (ALL COMPANIES)
# =================================
@st.cache_data(ttl=300)
def cargar_pases():
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

    df.columns = df.columns.str.strip()

    # Normalize key fields
    if "No. de Folio" in df.columns:
        df = df.rename(columns={"No. de Folio": "Folio"})

    df["Folio"] = df["Folio"].astype(str)

    # Dates
    for col in ["Fecha de Captura", "Fecha de Reporte"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    return df


# =================================
# Load SERVICES
# =================================
@st.cache_data(ttl=300)
def cargar_servicios():
    client = gspread.authorize(get_gsheets_credentials())
    ws = client.open_by_key(SPREADSHEET_ID).worksheet("SERVICES")

    data = ws.get_all_records()
    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)
    df.columns = df.columns.str.strip()

    if "No. de Folio" in df.columns:
        df = df.rename(columns={"No. de Folio": "Folio"})
    if "Iva" in df.columns:
        df = df.rename(columns={"Iva": "IVA"})

    df["Folio"] = df["Folio"].astype(str)

    if "Fecha Mod" in df.columns:
        df["Fecha Mod"] = pd.to_datetime(df["Fecha Mod"], errors="coerce")

    return df


df_pases = cargar_pases()
df_services = cargar_servicios()

# =================================
# FILTERS
# =================================
st.subheader("Filtros")

c1, c2, c3, c4 = st.columns(4)

with c1:
    empresa = st.selectbox(
        "Empresa",
        ["Todas"] + sorted(df_pases["Empresa"].dropna().unique().tolist())
        if not df_pases.empty else ["Todas"]
    )

with c2:
    estado = st.selectbox(
        "Estado",
        ["Todos"] + sorted(df_pases["Estado"].dropna().unique().tolist())
        if not df_pases.empty else ["Todos"]
    )

with c3:
    no_unidad = st.text_input("No. de Unidad")

with c4:
    no_reporte = st.text_input("No. de Reporte")

c5, c6, c7 = st.columns(3)

with c5:
    tipo_reporte = st.selectbox(
        "Tipo de Reporte",
        ["Todos"] + sorted(df_pases["Tipo de Reporte"].dropna().unique().tolist())
        if "Tipo de Reporte" in df_pases.columns else ["Todos"]
    )

with c6:
    fecha_captura = st.date_input("Fecha de Captura", value=None)

with c7:
    fecha_reporte = st.date_input("Fecha de Reporte", value=None)

c8, c9 = st.columns(2)

with c8:
    fecha_mod = st.date_input("Fecha Mod (Servicios)", value=None)

with c9:
    buscar = st.button("Aplicar filtros", type="primary")

# =================================
# APPLY FILTERS
# =================================
if buscar:
    df_p = df_pases.copy()
    df_s = df_services.copy()

    if empresa != "Todas":
        df_p = df_p[df_p["Empresa"] == empresa]

    if estado != "Todos":
        df_p = df_p[df_p["Estado"] == estado]

    if no_unidad and "No. de Unidad" in df_p.columns:
        df_p = df_p[df_p["No. de Unidad"].astype(str).str.contains(no_unidad, na=False)]

    if no_reporte and "No. de Reporte" in df_p.columns:
        df_p = df_p[df_p["No. de Reporte"].astype(str).str.contains(no_reporte, na=False)]

    if tipo_reporte != "Todos" and "Tipo de Reporte" in df_p.columns:
        df_p = df_p[df_p["Tipo de Reporte"] == tipo_reporte]

    if fecha_captura and "Fecha de Captura" in df_p.columns:
        df_p = df_p[df_p["Fecha de Captura"].dt.date == fecha_captura]

    if fecha_reporte and "Fecha de Reporte" in df_p.columns:
        df_p = df_p[df_p["Fecha de Reporte"].dt.date == fecha_reporte]

    if fecha_mod and "Fecha Mod" in df_s.columns:
        df_s = df_s[df_s["Fecha Mod"].dt.date == fecha_mod]

    # =================================
    # COMBINE (1 → MANY)
    # =================================
    if df_p.empty or df_s.empty:
        st.warning("No hay datos para los filtros seleccionados.")
    else:
        df_final = df_s.merge(
            df_p,
            on="Folio",
            how="left"
        )

        st.divider()
        st.subheader("Reporte Consolidado")

        st.dataframe(
            df_final,
            hide_index=True,
            width="stretch"
        )
