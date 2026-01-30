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
    page_title="Autorización y Actualización de Reporte",
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
require_access("autorizacion")

# =================================
# Defensive reset on page entry
# =================================
if st.session_state.get("_reset_autorizacion_page", True):
    st.session_state.modal_reporte = None
    st.session_state.buscar_trigger = False
    st.session_state["_reset_autorizacion_page"] = False

# =================================
# Navigation
# =================================
if st.button("⬅ Volver al Dashboard"):
    st.session_state.modal_reporte = None
    st.session_state.buscar_trigger = False
    st.switch_page("pages/dashboard.py")

st.divider()

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

# =================================
# Update Estado
# =================================
def actualizar_estado_pase(empresa, folio, nuevo_estado):
    sheet_map = {
        "IGLOO TRANSPORT": "IGLOO",
        "LINCOLN FREIGHT": "LINCOLN",
        "PICUS": "PICUS",
        "SET FREIGHT INTERNATIONAL": "SFI",
        "SET LOGIS PLUS": "SLP",
    }

    hoja = sheet_map.get(empresa)
    if not hoja:
        return

    client = gspread.authorize(get_gsheets_credentials())
    ws = client.open_by_key(
        "1ca46k4PCbvNMvZjsgU_2MHJULADRJS5fnghLopSWGDA"
    ).worksheet(hoja)

    folios = ws.col_values(2)
    if folio not in folios:
        return

    row_idx = folios.index(folio) + 1
    headers = ws.row_values(1)
    estado_col = headers.index("Estado") + 1

    ws.update_cell(row_idx, estado_col, nuevo_estado)

# =================================
# Load Pase de Taller
# =================================
@st.cache_data(ttl=300)
def cargar_pases_taller():
    SPREADSHEET_ID = "1ca46k4PCbvNMvZjsgU_2MHJULADRJS5fnghLopSWGDA"
    hojas = ["IGLOO", "LINCOLN", "PICUS", "SFI", "SLP"]

    client = gspread.authorize(get_gsheets_credentials())
    dfs = []

    for hoja in hojas:
        try:
            ws = client.open_by_key(SPREADSHEET_ID).worksheet(hoja)
            data = ws.get_all_records()
            if data:
                dfs.append(pd.DataFrame(data))
        except Exception:
            pass

    if not dfs:
        return pd.DataFrame()

    df = pd.concat(dfs, ignore_index=True)

    df.rename(columns={
        "No. de Folio": "NoFolio",
        "Fecha de Captura": "Fecha",
        "Tipo de Proveedor": "Proveedor",
    }, inplace=True)

    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    return df

# =================================
# IGLOO catalog
# =================================
@st.cache_data(ttl=600)
def cargar_catalogo_igloo():
    URL = (
        "https://docs.google.com/spreadsheets/d/"
        "18tFOA4prD-PWhtbc35cqKXxYcyuqGOC7"
        "/export?format=csv&gid=410297659"
    )

    df = pd.read_csv(URL)
    df.columns = df.columns.str.strip()

    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    df = df[df["Fecha"] >= pd.Timestamp("2025-01-01")]
    df = df.sort_values("Fecha", ascending=False)
    df = df.drop_duplicates(subset=["Parte"], keep="first")

    def limpiar(v):
        return float(str(v).replace("$", "").replace(",", "").strip())

    df["Precio MXP"] = df["PrecioParte"].apply(limpiar)
    df["IVA"] = df["Tasaiva"].apply(limpiar).apply(
        lambda x: x / 100 if x > 1 else x
    )

    df["label"] = df.apply(
        lambda r: f"{r['Parte']} - ${r['Precio MXP']:,.2f}", axis=1
    )

    return df

# =================================
# Load data
# =================================
pases_df = cargar_pases_taller()

# =================================
# Title
# =================================
st.title("📋 Autorización y Actualización de Reporte")

# =================================
# Session state
# =================================
st.session_state.setdefault("buscar_trigger", False)
st.session_state.setdefault("modal_reporte", None)

st.session_state.setdefault(
    "servicios_df",
    pd.DataFrame(columns=[
        "Seleccionar",
        "Parte",
        "TipoCompra",
        "Precio MXP",
        "IVA",
        "Cantidad",
        "Total MXN",
    ])
)

# =================================
# BUSCAR + RESULTADOS (UNCHANGED)
# =================================
# (kept exactly as before – omitted here for brevity)
# ---------------------------------

# =================================
# MODAL
# =================================
if st.session_state.modal_reporte:

    r = st.session_state.modal_reporte
    editable = r["Estado"].startswith("En Curso")

    @st.dialog("Detalle del Pase de Taller")
    def modal():

        st.markdown(f"**No. de Folio:** {r['NoFolio']}")
        st.markdown(f"**Empresa:** {r['Empresa']}")
        st.markdown(f"**Fecha:** {r['Fecha']}")
        st.markdown(f"**Proveedor:** {r['Proveedor']}")

        opciones_estado = [
            "En Curso / Autorizado",
            "En Curso / Sin Comenzar",
            "En Curso / Espera Refacciones",
            "Cerrado / Cancelado",
            "Cerrado / Completado",
        ]

        nuevo_estado = st.selectbox(
            "Estado",
            opciones_estado,
            index=opciones_estado.index(r["Estado"])
            if r["Estado"] in opciones_estado else 0,
            disabled=not editable
        )

        st.divider()
        st.subheader("Servicios y Refacciones")

        habilitado = nuevo_estado in [
            "En Curso / Sin Comenzar",
            "En Curso / Espera Refacciones",
        ]

        if r["Empresa"] == "IGLOO TRANSPORT":
            catalogo = cargar_catalogo_igloo()
            seleccion = st.selectbox(
                "Refacción / Servicio",
                catalogo["label"].tolist(),
                index=None,
                placeholder="Selecciona una refacción o servicio",
                disabled=not habilitado
            )
        else:
            seleccion = None
            st.selectbox(
                "Refacción / Servicio",
                [],
                disabled=True,
                placeholder="No hay catálogo para esta empresa"
            )

        if st.button(
            "Agregar refacciones o servicios",
            disabled=not habilitado or not seleccion,
            width="stretch"
        ):
            fila = catalogo[catalogo["label"] == seleccion].iloc[0]

            if fila["Parte"] not in st.session_state.servicios_df["Parte"].values:
                nueva = {
                    "Seleccionar": True,
                    "Parte": fila["Parte"],
                    "TipoCompra": fila.get("TipoCompra", ""),
                    "Precio MXP": fila["Precio MXP"],
                    "IVA": fila["IVA"],
                    "Cantidad": 1,
                    "Total MXN": fila["Precio MXP"],
                }

                st.session_state.servicios_df = pd.concat(
                    [st.session_state.servicios_df, pd.DataFrame([nueva])],
                    ignore_index=True
                )

        # Update totals
        df = st.session_state.servicios_df.copy()
        df["Total MXN"] = df["Precio MXP"] * df["Cantidad"]
        st.session_state.servicios_df = df

        st.session_state.servicios_df = st.data_editor(
            st.session_state.servicios_df,
            hide_index=True,
            column_config={
                "Seleccionar": st.column_config.CheckboxColumn(),
                "Cantidad": st.column_config.SelectboxColumn(
                    options=list(range(1, 51))
                ),
                "Precio MXP": st.column_config.NumberColumn(format="$ %.2f"),
                "IVA": st.column_config.NumberColumn(format="%.2f"),
                "Total MXN": st.column_config.NumberColumn(format="$ %.2f"),
            }
        )

        total = (
            st.session_state.servicios_df[
                st.session_state.servicios_df["Seleccionar"] == True
            ]["Total MXN"]
            .sum()
        )

        st.metric("Total MXN", f"$ {total:,.2f}")

    modal()