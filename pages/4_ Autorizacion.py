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
# Navigation
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

# =================================
# TOP 10 EN CURSO
# =================================
st.subheader("Últimos 10 Pases de Taller (En Curso)")

if not pases_df.empty:
    top10 = (
        pases_df[pases_df["Estado"].str.startswith("En Curso", na=False)]
        .sort_values("Fecha", ascending=False)
        .head(10)
        [["NoFolio", "Empresa", "Fecha", "Proveedor", "Estado"]]
    )
    st.dataframe(top10, hide_index=True, use_container_width=True)
else:
    st.info("No hay pases registrados.")

# =================================
# BUSCAR
# =================================
st.divider()
st.subheader("Buscar Pase de Taller")

empresas = sorted(pases_df["Empresa"].dropna().unique()) if not pases_df.empty else []

f1, f2, f3, f4 = st.columns(4)

with f1:
    f_folio = st.text_input("No. de Folio", placeholder="Escribe número de folio")

with f2:
    f_empresa = st.selectbox("Empresa", ["Selecciona empresa"] + empresas)

with f3:
    f_estado = st.selectbox(
        "Estado",
        [
            "Selecciona estado",
            "En Curso / Sin Comenzar",
            "En Curso / Espera Refacciones",
            "Cerrado / Cancelado",
            "Cerrado / Completado",
        ]
    )

with f4:
    f_fecha = st.date_input("Fecha", value=None)

if st.button("Buscar"):
    st.session_state.buscar_trigger = True

# =================================
# RESULTADOS
# =================================
if st.session_state.buscar_trigger:

    resultados = pases_df.copy()

    if f_folio:
        resultados = resultados[resultados["NoFolio"].str.contains(f_folio, case=False)]

    if f_empresa != "Selecciona empresa":
        resultados = resultados[resultados["Empresa"] == f_empresa]

    if f_estado != "Selecciona estado":
        resultados = resultados[resultados["Estado"] == f_estado]

    if f_fecha:
        resultados = resultados[resultados["Fecha"].dt.date == f_fecha]

    if resultados.empty:
        st.warning("No se encontraron resultados.")
        st.stop()

    st.divider()
    st.subheader("Resultados")

    for _, row in resultados.iterrows():
        c1, c2, c3, c4, c5, c6 = st.columns([1,2,2,2,2,1])

        editable = row["Estado"].startswith("En Curso")

        with c1:
            label = "Editar" if editable else "Ver"
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

    r = st.session_state.modal_reporte
    editable = r["Estado"].startswith("En Curso")

    @st.dialog("Detalle del Pase de Taller")
    def modal():

        st.markdown(f"**No. de Folio:** {r['NoFolio']}")
        st.markdown(f"**Empresa:** {r['Empresa']}")
        st.markdown(f"**Fecha:** {r['Fecha']}")
        st.markdown(f"**Proveedor:** {r['Proveedor']}")

        opciones_estado = [
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

        # =================================
        # BOTÓN CONDICIONAL (NUEVO)
        # =================================
        estado_habilita_boton = nuevo_estado in [
            "En Curso / Sin Comenzar",
            "En Curso / Espera Refacciones",
        ]

        st.button(
            "🧩 Acción adicional",
            disabled=not estado_habilita_boton,
            use_container_width=True
        )

        st.divider()

        c1, c2 = st.columns(2)

        with c1:
            if st.button("Cancelar"):
                st.session_state.modal_reporte = None
                st.rerun()

        with c2:
            if st.button("Aceptar", type="primary") and editable:
                if nuevo_estado != r["Estado"]:
                    actualizar_estado_pase(
                        r["Empresa"], r["NoFolio"], nuevo_estado
                    )
                st.session_state.modal_reporte = None
                st.cache_data.clear()
                st.rerun()

    modal()
