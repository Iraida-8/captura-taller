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

pases_df = cargar_pases_taller()

# =================================
# Title
# =================================
st.title("📋 Autorización y Actualización de Reporte")

# =================================
# Session state defaults
# =================================
st.session_state.setdefault("buscar_trigger", False)
st.session_state.setdefault("modal_reporte", None)

st.session_state.setdefault(
    "servicios_df",
    pd.DataFrame(columns=[
        "Seleccionar",
        "Artículo",
        "Descripción",
        "Precio MXP",
        "IVA",
        "Cantidad",
        "Total MXN",
    ])
)

# 🔹 ADDED: control for IGLOO catalog modal
st.session_state.setdefault("abrir_catalogo_igloo", False)

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
        # SERVICIOS Y REFACCIONES
        # =================================
        st.divider()
        st.subheader("Servicios y Refacciones")

        habilita_boton = nuevo_estado in [
            "En Curso / Sin Comenzar",
            "En Curso / Espera Refacciones",
        ]

        # 🔹 MODIFIED: button now opens catalog (no behavior removed)
        if st.button(
            "Agregar refacciones o servicios",
            disabled=not habilita_boton,
            use_container_width=True
        ):
            st.session_state.abrir_catalogo_igloo = True

        st.session_state.servicios_df = st.data_editor(
            st.session_state.servicios_df,
            num_rows="dynamic",
            hide_index=True,
            disabled=not editable,
            column_config={
                "Seleccionar": st.column_config.CheckboxColumn(),
                "Precio MXP": st.column_config.NumberColumn(format="$ %.2f"),
                "IVA": st.column_config.NumberColumn(format="%.2f"),
                "Cantidad": st.column_config.NumberColumn(min_value=0, step=1),
                "Total MXN": st.column_config.NumberColumn(format="$ %.2f"),
            },
        )

        if not st.session_state.servicios_df.empty:
            total = (
                st.session_state.servicios_df[
                    st.session_state.servicios_df["Seleccionar"] == True
                ]["Total MXN"]
                .fillna(0)
                .sum()
            )
        else:
            total = 0

        st.metric("Total MXN", f"$ {total:,.2f}")

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

# =================================
# 🔹 ADDED: IGLOO CATALOG LOADER
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

    df = (
        df.sort_values("Fecha", ascending=False)
        .drop_duplicates(subset=["Parte"], keep="first")
    )

    def limpiar_num(v):
        return float(str(v).replace("$", "").replace(",", "").strip())

    df["Precio MXP"] = df["PrecioParte"].apply(limpiar_num)
    df["IVA"] = df["Tasaiva"].apply(limpiar_num).apply(
        lambda x: x / 100 if x > 1 else x
    )

    return df

# =================================
# 🔹 ADDED: IGLOO CATALOG MODAL
# =================================
if st.session_state.abrir_catalogo_igloo:

    catalogo_df = cargar_catalogo_igloo()

    @st.dialog("Catálogo de Refacciones y Servicios (IGLOO)")
    def modal_catalogo_igloo():

        articulo = st.selectbox(
            "Artículo",
            sorted(catalogo_df["Parte"].dropna().unique())
        )

        fila = catalogo_df[catalogo_df["Parte"] == articulo].iloc[0]

        st.markdown(f"**Descripción:** {fila['Parte']}")
        st.markdown(f"**Precio MXP:** ${fila['Precio MXP']:,.2f}")
        st.markdown(f"**IVA:** {fila['IVA']:.2f}")

        c1, c2 = st.columns(2)

        with c1:
            if st.button("Cancelar"):
                st.session_state.abrir_catalogo_igloo = False
                st.rerun()

        with c2:
            if st.button("Agregar"):
                if articulo not in st.session_state.servicios_df["Artículo"].values:
                    cantidad = 1
                    total = cantidad * fila["Precio MXP"] * (1 + fila["IVA"])

                    nueva = {
                        "Seleccionar": True,
                        "Artículo": articulo,
                        "Descripción": fila["Parte"],
                        "Precio MXP": fila["Precio MXP"],
                        "IVA": fila["IVA"],
                        "Cantidad": cantidad,
                        "Total MXN": total,
                    }

                    st.session_state.servicios_df = pd.concat(
                        [
                            st.session_state.servicios_df,
                            pd.DataFrame([nueva])
                        ],
                        ignore_index=True
                    )

                st.session_state.abrir_catalogo_igloo = False
                st.rerun()

    modal_catalogo_igloo()
