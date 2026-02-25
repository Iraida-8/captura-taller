import streamlit as st
import pandas as pd
from datetime import datetime, date
from auth import require_login, require_access
import gspread
from google.oauth2.service_account import Credentials
import os
from datetime import datetime
from supabase import create_client

fecha_mod = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# =================================
# Page Cache and State Management
# =================================
@st.cache_resource
def get_supabase_client():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_ANON_KEY"]
    )

# =================================
# Page configuration
# =================================
st.set_page_config(
    page_title="Autorización y Actualización de Reporte",
    layout="wide"
)

st.session_state.setdefault("last_action", None)
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
    st.session_state.modal_factura = None   # ← ADD THIS
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

    try:
        if "gcp_service_account" in st.secrets:
            return Credentials.from_service_account_info(
                st.secrets["gcp_service_account"], scopes=scopes
            )
    except Exception as e:
        st.error(f"Error loading Google Sheets credentials: {e}")


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
# Update OSTE
# =================================
def actualizar_oste_pase(empresa, folio, oste):
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

    if "Oste" not in headers:
        return

    oste_col = headers.index("Oste") + 1
    ws.update_cell(row_idx, oste_col, oste)

# =================================
# GUARDAR FACTURA
# =================================
def guardar_factura(folio, numero_factura):

    client = gspread.authorize(get_gsheets_credentials())

    ws = client.open_by_key(
        "1ca46k4PCbvNMvZjsgU_2MHJULADRJS5fnghLopSWGDA"
    ).worksheet("FACTURAS")

    headers = [h.strip() for h in ws.row_values(1)]

    col_folio = headers.index("No. de Folio") + 1
    col_factura = headers.index("No. de Factura") + 1

    folios = ws.col_values(col_folio)

    # If folio already exists → update factura
    if folio in folios:
        row_idx = folios.index(folio) + 1
        ws.update_cell(row_idx, col_factura, numero_factura)
    else:
        # Append new row
        ws.append_row(
            [folio, numero_factura],
            value_input_option="USER_ENTERED"
        )

# =================================
# Log estado sin refacciones
# =================================
def registrar_cambio_estado_sin_servicios(folio, usuario, nuevo_estado):
    from datetime import datetime

    estado_fecha_map = {
        "En Curso / Autorizado": "Fecha Autorizado",
        "En Curso / Sin Comenzar": "Fecha Sin Comenzar",
        "En Curso / Espera Refacciones": "Fecha Espera Refacciones",
        "En Curso / En Proceso": "Fecha En Proceso",
        "Cerrado / Completado": "Fecha Completado",
        "Cerrado / Facturado": "Fecha Facturado",
        "Cerrado / Cancelado": "Fecha Cancelado",
    }

    fecha_col = estado_fecha_map.get(nuevo_estado)
    if not fecha_col:
        return

    client = gspread.authorize(get_gsheets_credentials())
    ws = client.open_by_key(
        "1ca46k4PCbvNMvZjsgU_2MHJULADRJS5fnghLopSWGDA"
    ).worksheet("SERVICES")

    fecha_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    headers = [h.strip() for h in ws.row_values(1)]

    # Build empty row aligned to headers
    row = [""] * len(headers)

    def set_if_exists(col_name, value):
        if col_name in headers:
            row[headers.index(col_name)] = value

    set_if_exists("No. de Folio", folio)
    set_if_exists("Modifico", usuario)
    set_if_exists("Fecha Mod", fecha_now)
    set_if_exists(fecha_col, fecha_now)

    ws.append_row(row, value_input_option="USER_ENTERED")

# =================================
# Load Servicios for Folio
# =================================
def cargar_servicios_folio(folio):
    client = gspread.authorize(get_gsheets_credentials())
    ws = client.open_by_key(
        "1ca46k4PCbvNMvZjsgU_2MHJULADRJS5fnghLopSWGDA"
    ).worksheet("SERVICES")

    data = ws.get_all_records()
    if not data:
        return pd.DataFrame(columns=[
            "Parte","Tipo De Parte","PU","IVA","Cantidad","Total"
        ])

    df = pd.DataFrame(data)

    # 🔹 PATCH: normalize headers
    df.columns = df.columns.str.strip()

    if "No. de Folio" in df.columns:
        df = df.rename(columns={"No. de Folio": "Folio"})

    if "Iva" in df.columns:
        df = df.rename(columns={"Iva": "IVA"})

    # 🔹 Ensure string comparison
    df["Folio"] = df["Folio"].astype(str)

    df = df[df["Folio"] == str(folio)]

    # ✅ NEW — REMOVE STATUS LOG ROWS
    if "Parte" in df.columns:
        df = df[df["Parte"].notna() & (df["Parte"].astype(str).str.strip() != "")]

    return df[
        ["Parte","Tipo De Parte","PU","IVA","Cantidad","Total"]
    ]

# =================================
# UPSERT Servicios / Refacciones
# =================================
def guardar_servicios_refacciones(folio, usuario, servicios_df, nuevo_estado=None):
    if servicios_df is None or servicios_df.empty:
        return

    client = gspread.authorize(get_gsheets_credentials())
    ws = client.open_by_key(
        "1ca46k4PCbvNMvZjsgU_2MHJULADRJS5fnghLopSWGDA"
    ).worksheet("SERVICES")

    fecha_mod = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # =====================================================
    # PHASE 1 — LOAD WITH REAL ROW NUMBERS
    # =====================================================
    all_values = ws.get_all_values()

    headers = [h.strip() for h in all_values[0]]
    rows = all_values[1:]
    df_db = pd.DataFrame(rows, columns=headers)
    df_db["__rownum__"] = range(2, len(rows) + 2)

    # =====================================================
    # Normalize headers
    # =====================================================
    if "No. de Folio" in df_db.columns:
        df_db = df_db.rename(columns={"No. de Folio": "Folio"})
    if "Iva" in df_db.columns:
        df_db = df_db.rename(columns={"Iva": "IVA"})

    df_db["Folio"] = df_db["Folio"].astype(str)

    servicios_df = servicios_df.copy()
    servicios_df["Parte"] = servicios_df["Parte"].astype(str)

    df_folio = df_db[df_db["Folio"] == str(folio)]

    # =====================================================
    # PHASE 2 — DELETE REMOVED ITEMS (REAL PARTS ONLY)
    # =====================================================
    partes_actuales = set(servicios_df["Parte"])

    rows_to_delete = df_folio[
        df_folio["Parte"].astype(str).str.strip().ne("")
        & ~df_folio["Parte"].isin(partes_actuales)
    ]["__rownum__"].tolist()

    for rownum in sorted(rows_to_delete, reverse=True):
        ws.delete_rows(int(rownum))

    # =====================================================
    # PHASE 3 — RELOAD AFTER DELETE
    # =====================================================
    all_values = ws.get_all_values()
    headers = [h.strip() for h in all_values[0]]
    rows = all_values[1:]
    df_db = pd.DataFrame(rows, columns=headers)
    df_db["__rownum__"] = range(2, len(rows) + 2)

    if "No. de Folio" in df_db.columns:
        df_db = df_db.rename(columns={"No. de Folio": "Folio"})
    if "Iva" in df_db.columns:
        df_db = df_db.rename(columns={"Iva": "IVA"})

    df_db["Folio"] = df_db["Folio"].astype(str)
    df_folio = df_db[df_db["Folio"] == str(folio)]

    # =====================================================
    # CAPTURE EXISTING DATES (FROM ANY ROW)
    # =====================================================
    date_columns = [
        "Fecha Autorizado",
        "Fecha Sin Comenzar",
        "Fecha Espera Refacciones",
        "Fecha En Proceso",
        "Fecha Facturado",
        "Fecha Completado",
        "Fecha Cancelado",
    ]

    fechas_existentes = {}

    for col in date_columns:
        if col in df_folio.columns:
            vals = df_folio[col].dropna()
            vals = vals[vals.astype(str).str.strip() != ""]
            if not vals.empty:
                fechas_existentes[col] = vals.iloc[0]

    # =====================================================
    # MAP NEW STATUS → DATE COLUMN
    # =====================================================
    estado_fecha_map = {
        "En Curso / Autorizado": "Fecha Autorizado",
        "En Curso / Sin Comenzar": "Fecha Sin Comenzar",
        "En Curso / Espera Refacciones": "Fecha Espera Refacciones",
        "En Curso / En Proceso": "Fecha En Proceso",
        "Cerrado / Facturado": "Fecha Facturado",
        "Cerrado / Completado": "Fecha Completado",
        "Cerrado / Cancelado": "Fecha Cancelado",
    }

    col_nueva_fecha = estado_fecha_map.get(nuevo_estado)

    # =====================================================
    # PHASE 4 — UPSERT WITH TRUE HISTORY PROTECTION
    # =====================================================
    for _, r in servicios_df.iterrows():
        match = df_folio[df_folio["Parte"] == r["Parte"]]

        row_data = [
            folio,
            usuario,
            r["Parte"],
            r["Tipo De Parte"],
            float(r["PU"] or 0),
            float(r["IVA"] or 0),
            int(r["Cantidad"] or 0),
            float(r["Total"] or 0),
            fecha_mod,
        ]

        for col in date_columns:
            existente = fechas_existentes.get(col, "")

            # keep old history
            if str(existente).strip() != "":
                row_data.append(existente)

            # write new milestone
            elif col == col_nueva_fecha:
                row_data.append(fecha_mod)

            else:
                row_data.append("")

        if not match.empty:
            rownum = int(match.iloc[0]["__rownum__"])
            ws.update(f"A{rownum}:P{rownum}", [row_data])
        else:
            ws.append_row(row_data, value_input_option="USER_ENTERED")

# =================================
# Load Pase de Taller
# =================================
@st.cache_data(ttl=300)
def cargar_pases_taller():
    import time

    SPREADSHEET_ID = "1ca46k4PCbvNMvZjsgU_2MHJULADRJS5fnghLopSWGDA"
    hojas = ["IGLOO", "LINCOLN", "PICUS", "SFI", "SLP"]

    client = gspread.authorize(get_gsheets_credentials())
    dfs = []

    for hoja in hojas:

        for intento in range(3):  # retry up to 3 times
            try:
                ws = client.open_by_key(SPREADSHEET_ID).worksheet(hoja)
                data = ws.get_all_records()
                if data:
                    dfs.append(pd.DataFrame(data))
                break
            except Exception:
                time.sleep(2)  # wait and retry

    if not dfs:
        st.warning("Google Sheets is temporarily busy. Please wait a moment and refresh.")
        return pd.DataFrame()

    df = pd.concat(dfs, ignore_index=True)

    df.rename(columns={
        "No. de Folio": "NoFolio",
        "Fecha de Captura": "Fecha",
        "Tipo de Proveedor": "Proveedor",
    }, inplace=True)

    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    df["NoFolio"] = df["NoFolio"].astype(str)

    return df

# =================================
# Load FACTURAS
# =================================
@st.cache_data(ttl=300)
def cargar_facturas():
    client = gspread.authorize(get_gsheets_credentials())

    ws = client.open_by_key(
        "1ca46k4PCbvNMvZjsgU_2MHJULADRJS5fnghLopSWGDA"
    ).worksheet("FACTURAS")

    data = ws.get_all_records()

    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)
    df.columns = df.columns.str.strip()

    if "No. de Factura" in df.columns:
        df["No. de Factura"] = (
            df["No. de Factura"]
            .astype(str)
            .str.replace(".0", "", regex=False)
            .str.strip()
        )

    if "No. de Folio" in df.columns:
        df["No. de Folio"] = df["No. de Folio"].astype(str).str.strip()

    return df

pases_df = cargar_pases_taller()

facturas_df = cargar_facturas()

if not facturas_df.empty:
    facturas_df.columns = facturas_df.columns.str.strip()

    if "No. de Folio" in facturas_df.columns:
        facturas_df = facturas_df.rename(columns={"No. de Folio": "NoFolio"})

    facturas_df["NoFolio"] = facturas_df["NoFolio"].astype(str)

# =================================
# Load Refacciones (Supabase)
# =================================
@st.cache_data(ttl=300)
def cargar_refacciones():
    supabase = get_supabase_client()

    response = (
        supabase
        .table("parts")
        .select("parte, tipo")   # 🔴 lowercase
        .order("parte")
        .execute()
    )

    if not response.data:
        return pd.DataFrame(columns=["Parte", "Tipo"])

    df = pd.DataFrame(response.data)

    # Normalize to your app’s expected format
    df = df.rename(columns={
        "parte": "Parte",
        "tipo": "Tipo"
    })

    return df

# =================================
# Catalogs (READ ONLY)
# =================================

# IGLOO LOADER
@st.cache_data(ttl=600)
def cargar_catalogo_igloo_simple():
    URL = (
        "https://docs.google.com/spreadsheets/d/"
        "18tFOA4prD-PWhtbc35cqKXxYcyuqGOC7"
        "/export?format=csv&gid=410297659"
    )

    df = pd.read_csv(URL)
    df.columns = df.columns.str.strip()

    required = ["Parte", "Tipo De Parte", "PU", "IVA"]
    missing = [c for c in required if c not in df.columns]

    if missing:
        st.error(f"IGLOO → faltan columnas: {missing}")
        return pd.DataFrame()

    df["PU"] = (
        df["PU"]
        .astype(str)
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.strip()
    )

    df["PU"] = pd.to_numeric(df["PU"], errors="coerce").fillna(0)

    df["IVA"] = (
        df["IVA"]
        .astype(str)
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.replace("%", "", regex=False)
        .str.strip()
    )

    df["IVA"] = pd.to_numeric(df["IVA"], errors="coerce").fillna(0)

    df["label"] = df.apply(
        lambda r: f"{r['Parte']} - ${r['PU']:,.2f}",
        axis=1
    )

    return df[["Parte", "Tipo De Parte", "PU", "IVA", "label"]]

# LINCOLN LOADER
@st.cache_data(ttl=600)
def cargar_catalogo_lincoln():
    URL = (
        "https://docs.google.com/spreadsheets/d/"
        "1lcNr73nHrMpsqdYBNxtTQFqFmY1Ey9gp"
        "/export?format=csv&gid=41991257"
    )

    df = pd.read_csv(URL)
    df.columns = df.columns.str.strip()

    if "Tipo De Parte" not in df.columns:
        df["Tipo De Parte"] = "Servicio"

    df["PU"] = (
        df["PU USD"]
        .astype(str)
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.replace("USD", "", regex=False)
        .str.strip()
    )

    df["PU"] = pd.to_numeric(df["PU"], errors="coerce").fillna(0)

    df["IVA"] = 0

    df["label"] = df.apply(
        lambda r: f"{r['Parte']} - ${r['PU']:,.2f}",
        axis=1
    )

    return df[["Parte", "Tipo De Parte", "PU", "IVA", "label"]]

# PICUS LOADER
@st.cache_data(ttl=600)
def cargar_catalogo_picus():
    URL = (
        "https://docs.google.com/spreadsheets/d/"
        "1tzt6tYG94oVt8YwK3u9gR-DHFcuadpNN"
        "/export?format=csv&gid=354598948"
    )

    df = pd.read_csv(URL)
    df.columns = df.columns.str.strip()

    # Ensure required columns exist
    required = ["Parte", "PU", "IVA"]
    missing = [c for c in required if c not in df.columns]

    if missing:
        st.error(f"PICUS → faltan columnas: {missing}")
        return pd.DataFrame()

    # Ensure Tipo De Parte exists
    if "Tipo De Parte" not in df.columns:
        df["Tipo De Parte"] = "Servicio"

    # 🔹 CLEAN PU (same logic as IGLOO)
    df["PU"] = (
        df["PU"]
        .astype(str)
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.replace("USD", "", regex=False)
        .str.strip()
    )

    df["PU"] = pd.to_numeric(df["PU"], errors="coerce")

    # 🔹 CLEAN IVA
    df["IVA"] = (
        df["IVA"]
        .astype(str)
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.replace("%", "", regex=False)
        .str.strip()
    )

    df["IVA"] = pd.to_numeric(df["IVA"], errors="coerce")

    # 🚨 DEBUG SAFETY — warn if everything became zero
    if df["PU"].isna().all():
        st.warning("PICUS → Todos los PU se convirtieron en NaN. Revisa formato de la hoja.")

    df["PU"] = df["PU"].fillna(0)
    df["IVA"] = df["IVA"].fillna(0)

    # Dropdown label (parte + pu)
    df["label"] = df.apply(
        lambda r: f"{r['Parte']} - ${r['PU']:,.2f}",
        axis=1
    )

    return df[["Parte", "Tipo De Parte", "PU", "IVA", "label"]]

# SET FREIGHT LOADER
@st.cache_data(ttl=600)
def cargar_catalogo_sfi():
    URL = (
        "https://docs.google.com/spreadsheets/d/"
        "1Nqbhl8o5qaKhI4LNxreicPW5Ew8kqShS"
        "/export?format=csv&gid=849445619"
    )

    df = pd.read_csv(URL)
    df.columns = df.columns.str.strip()

    if "Tipo De Parte" not in df.columns:
        df["Tipo De Parte"] = "Servicio"

    df["PU"] = (
        df["PU USD"]
        .astype(str)
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.replace("USD", "", regex=False)
        .str.strip()
    )

    df["PU"] = pd.to_numeric(df["PU"], errors="coerce").fillna(0)

    df["IVA"] = 0

    df["label"] = df.apply(
        lambda r: f"{r['Parte']} - ${r['PU']:,.2f}",
        axis=1
    )

    return df[["Parte", "Tipo De Parte", "PU", "IVA", "label"]]

# SET LOGIS LOADER
@st.cache_data(ttl=600)
def cargar_catalogo_slp():
    URL = (
        "https://docs.google.com/spreadsheets/d/"
        "1yrzwm5ixsaYNKwkZpfmFpDdvZnohFH61"
        "/export?format=csv&gid=1837946138"
    )

    df = pd.read_csv(URL)
    df.columns = df.columns.str.strip()

    if "Tipo De Parte" not in df.columns:
        df["Tipo De Parte"] = "Servicio"

    df["PU"] = (
        df["PU USD"]
        .astype(str)
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.replace("USD", "", regex=False)
        .str.strip()
    )

    df["PU"] = pd.to_numeric(df["PU"], errors="coerce").fillna(0)

    df["IVA"] = 0

    df["label"] = df.apply(
        lambda r: f"{r['Parte']} - ${r['PU']:,.2f}",
        axis=1
    )

    return df[["Parte", "Tipo De Parte", "PU", "IVA", "label"]]

# =================================
# Catalog dispatcher by Empresa
# =================================
def cargar_catalogo_por_empresa(empresa):
    if empresa == "IGLOO TRANSPORT":
        return cargar_catalogo_igloo_simple()

    if empresa == "LINCOLN FREIGHT":
        return cargar_catalogo_lincoln()

    if empresa == "PICUS":
        return cargar_catalogo_picus()

    if empresa == "SET FREIGHT INTERNATIONAL":
        return cargar_catalogo_sfi()

    if empresa == "SET LOGIS PLUS":
        return cargar_catalogo_slp()

    return None

# =================================
# Title
# =================================
st.title("📋 Autorización y Actualización de Reporte")

# =================================
# KPI STRIP
# =================================
st.markdown("### Resumen general")

total_ordenes = len(pases_df)

def porcentaje(n):
    if total_ordenes == 0:
        return 0
    return round((n / total_ordenes) * 100, 1)

pendientes = len(pases_df[pases_df["Estado"] == "En Curso / Nuevo"])

diagnosticos = len(
    pases_df[pases_df["Estado"] == "En Curso / Autorizado"]
)

en_proceso = len(
    pases_df[pases_df["Estado"].isin([
        "En Curso / Sin Comenzar",
        "En Curso / Espera Refacciones",
        "En Curso / En Proceso",
    ])]
)

completadas = len(
    pases_df[pases_df["Estado"].isin([
        "Cerrado / Completado",
        "Cerrado / Facturado",
    ])]
)

canceladas = len(
    pases_df[pases_df["Estado"] == "Cerrado / Cancelado"]
)

k1, k2, k3, k4, k5 = st.columns(5)

def postit(col, titulo, valor, pct, color):
    with col:
        st.markdown(
            f"""
            <div style="
                background:{color};
                padding:18px;
                border-radius:14px;
                text-align:center;
                box-shadow:0 4px 10px rgba(0,0,0,0.08);
                color:#111;
            ">
                <div style="font-size:0.9rem; font-weight:700;">{titulo}</div>
                <div style="font-size:2rem; font-weight:900; margin-top:6px;">{valor}</div>
                <div style="font-size:0.8rem; opacity:0.8;">{pct}% del total</div>
            </div>
            """,
            unsafe_allow_html=True
        )

postit(k1, "Solicitudes Pendientes", pendientes, porcentaje(pendientes), "#FFF3CD")
postit(k2, "Diagnósticos Activos", diagnosticos, porcentaje(diagnosticos), "#D1ECF1")
postit(k3, "Órdenes en Proceso", en_proceso, porcentaje(en_proceso), "#E2E3FF")
postit(k4, "Órdenes Completadas", completadas, porcentaje(completadas), "#D4EDDA")
postit(k5, "Canceladas", canceladas, porcentaje(canceladas), "#F8D7DA")

# =================================
# COMPANY DISTRIBUTION and LOG
# =================================
st.divider()

left, right = st.columns([2, 1])

# =============================
# LEFT → COMPANY SUMMARY
# =============================
with left:
    st.markdown("### Órdenes por Empresa")

    if not pases_df.empty:
        conteo_empresas = (
            pases_df["Empresa"]
            .value_counts()
            .reset_index()
        )
        conteo_empresas.columns = ["Empresa", "Cantidad"]

        total = conteo_empresas["Cantidad"].sum()

        rows_html = ""
        for _, row_emp in conteo_empresas.iterrows():
            empresa = row_emp["Empresa"]
            cantidad = row_emp["Cantidad"]
            pct = (cantidad / total) * 100 if total else 0

            rows_html += f"""
            <div style="
                display:flex;
                justify-content:space-between;
                margin-bottom:6px;
                font-weight:600;
            ">
                <span>{empresa}</span>
                <span>{cantidad} &nbsp; ({pct:.1f}%)</span>
            </div>
            """

        st.markdown(
            f"""
            <div style="
                background:#ffffff;
                padding:18px;
                border-radius:14px;
                box-shadow:0 3px 8px rgba(0,0,0,0.06);
                color:#111;
            ">
                {rows_html}
            </div>
            """,
            unsafe_allow_html=True
        )

    else:
        st.info("No hay datos.")

# =============================
# RIGHT → LAST ACTIVITY
# =============================
with right:
    st.markdown("### Última actividad")

    acciones = st.session_state.get("last_action", [])

    # if someone saved a single string → convert to list
    if isinstance(acciones, str):
        acciones = [acciones]

    if acciones:
        acciones = acciones[:3]  # max 3

        rows_html = ""
        for a in acciones:
            rows_html += f"""
            <div style="
                margin-bottom:8px;
                padding-bottom:8px;
                border-bottom:1px solid #eee;
            ">
                {a}
            </div>
            """

        st.markdown(
            f"""
            <div style="
                background:#ffffff;
                padding:18px;
                border-radius:14px;
                box-shadow:0 3px 8px rgba(0,0,0,0.06);
                color:#111;
                font-weight:600;
            ">
                {rows_html}
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.info("Sin actividad reciente.")

# =================================
# Session state defaults
# =================================
st.session_state.setdefault("buscar_trigger", False)
st.session_state.setdefault("modal_reporte", None)
st.session_state.setdefault("modal_factura", None)
st.session_state.setdefault("refaccion_seleccionada", None)
st.session_state.setdefault(
    "servicios_df",
    pd.DataFrame(columns=[
        "Parte","Tipo De Parte","PU","IVA","Cantidad","Total"
    ])
)

# =================================
# TOP 10 EN CURSO → POST ITS
# =================================
st.subheader("Últimos 10 Pases de Taller (Nuevos)")

import streamlit.components.v1 as components

def safe(x):
    if pd.isna(x) or x is None:
        return ""
    return str(x)

if not pases_df.empty:

    top10 = (
        pases_df[pases_df["Estado"] == "En Curso / Nuevo"]
        .sort_values("Fecha", ascending=False)
        .head(10)
    )

    if top10.empty:
        st.info("No hay pases en estado Nuevo.")

    else:
        cols = st.columns(5)

        for i, (_, r) in enumerate(top10.iterrows()):
            col = cols[i % 5]

            with col:
                folio = safe(r.get("NoFolio"))
                tipo_unidad = safe(r.get("Tipo de Unidad"))
                fecha = r.get("Fecha")
                fecha = fecha.date() if pd.notna(fecha) else ""
                unidad = safe(r.get("No. de Unidad"))
                capturo = safe(r.get("Capturo"))
                descripcion = safe(r.get("Descripcion Problema"))

                if len(descripcion) > 120:
                    descripcion = descripcion[:120] + "..."

                html = f"""
                <div style="padding:6px;">
                    <div style="
                        background:#fff7d6;
                        padding:14px;
                        border-radius:16px;
                        box-shadow:0 4px 10px rgba(0,0,0,0.08);
                        color:#111;
                        min-height:160px;
                        font-family:sans-serif;
                    ">
                        <div style="font-weight:900;">{folio}</div>
                        <div style="font-size:0.8rem;">{tipo_unidad}</div>
                        <div style="font-size:0.8rem;">{fecha}</div>

                        <hr style="margin:6px 0">

                        <div style="font-size:0.8rem;">{unidad}</div>

                        <div style="
                            font-size:0.75rem;
                            margin-top:6px;
                            padding:6px;
                            background:#fff;
                            border-radius:8px;
                            box-shadow: inset 0 0 3px rgba(0,0,0,0.05);
                        ">
                            {descripcion}
                        </div>

                        <div style="
                            margin-top:6px;
                            font-size:0.75rem;
                            font-weight:700;
                            color:#856404;
                        ">
                            En Curso / Nuevo
                        </div>

                        <div style="
                            font-size:0.75rem;
                            margin-top:4px;
                            opacity:0.8;
                        ">
                            Capturó: {capturo}
                        </div>
                    </div>
                </div>
                """

                components.html(html, height=220)

                # =====================================
                # BUTTON
                # =====================================
                if st.button("✏ Editar", key=f"top10_{folio}", use_container_width=True):

                    st.session_state.modal_reporte = r.to_dict()

                    df = cargar_servicios_folio(r["NoFolio"])

                    st.session_state.servicios_df = df

else:
    st.info("No hay pases registrados.")

# =================================
# FACTURACIÓN
# =================================
st.divider()
st.subheader("Facturación")
st.caption("Todas las órdenes (con información de factura)")

if not pases_df.empty:

    # =============================================
    # FILTER INPUTS
    # =============================================
    fcol1, fcol2 = st.columns(2)

    with fcol1:
        filtro_folio_fact = st.text_input("Filtrar por No. de Folio")

    with fcol2:
        filtro_factura_fact = st.text_input("Filtrar por No. de Factura")

    # =============================================
    # MERGE ALL ORDERS WITH FACTURAS
    # =============================================
    base = pases_df.copy()

    if not facturas_df.empty:
        merged = base.merge(
            facturas_df[["NoFolio", "No. de Factura"]],
            on="NoFolio",
            how="left"
        )
    else:
        merged = base.copy()
        merged["No. de Factura"] = None

    # =============================================
    # APPLY FILTERS
    # =============================================
    if filtro_folio_fact:
        merged = merged[
            merged["NoFolio"]
            .astype(str)
            .str.contains(filtro_folio_fact, case=False, na=False)
        ]

    if filtro_factura_fact:
        merged = merged[
            merged["No. de Factura"]
            .astype(str)
            .str.contains(filtro_factura_fact, case=False, na=False)
        ]

    # =============================================
    # LIMIT TO 5 POST-ITS
    # =============================================
    merged = merged.head(5)

    if merged.empty:
        st.info("No hay resultados con los filtros aplicados.")
    else:
        cols = st.columns(5)

        for i, (_, r) in enumerate(merged.iterrows()):
            col = cols[i]

            with col:
                folio = r.get("NoFolio", "")
                estado = r.get("Estado", "")
                factura_raw = r.get("No. de Factura")

                factura_vacia = (
                    pd.isna(factura_raw)
                    or str(factura_raw).strip() == ""
                )

                if factura_vacia:
                    factura = "-"
                    label_btn = "Agregar Factura"
                else:
                    factura = str(factura_raw)
                    label_btn = "Ver"

                html = f"""
                <div style="padding:6px;">
                    <div style="
                        background:#ffe2e2;
                        padding:14px;
                        border-radius:16px;
                        box-shadow:0 4px 10px rgba(0,0,0,0.08);
                        color:#111;
                        min-height:120px;
                        font-family:sans-serif;
                    ">
                        <div style="font-weight:900;">{folio}</div>

                        <hr style="margin:6px 0">

                        <div style="
                            font-size:0.8rem;
                            font-weight:700;
                            color:#721c24;
                        ">
                            {estado}
                        </div>

                        <div style="
                            margin-top:8px;
                            font-size:0.75rem;
                        ">
                            No. de Factura: {factura}
                        </div>
                    </div>
                </div>
                """

                components.html(html, height=160)

                # View facturas
                if st.button(
                    label_btn,
                    key=f"fact_btn_{folio}",
                    use_container_width=True
                ):
                    st.session_state.modal_factura = {
                        "NoFolio": folio,
                        "NoFactura": None if factura_vacia else factura
                    }

else:
    st.info("No hay datos disponibles.")

# =================================
# FACTURA MODAL
# =================================
if st.session_state.modal_factura:

    data_fact = st.session_state.modal_factura

    @st.dialog("Factura")
    def modal_factura():

        folio = data_fact["NoFolio"]
        factura_actual = data_fact["NoFactura"]

        st.markdown(f"**No. de Folio:** {folio}")

        factura_vacia = (
            factura_actual is None
            or str(factura_actual).strip() == ""
        )

        nueva_factura = st.text_input(
            "No. de Factura",
            value="" if factura_vacia else factura_actual,
            disabled=not factura_vacia
        )

        st.divider()

        # =================================
        # BUTTON LOGIC
        # =================================
        if factura_vacia:
            label_btn = "Aceptar / Guardar"
        else:
            label_btn = "Aceptar / Cerrar"

        if st.button(label_btn, type="primary"):

            # If editable and user typed something → save
            if factura_vacia and nueva_factura.strip() != "":
                guardar_factura(folio, nueva_factura.strip())
                st.cache_data.clear()

            st.session_state.modal_factura = None
            st.rerun()

    modal_factura()

# =================================
# BUSCAR
# =================================
st.divider()
st.subheader("Buscar Pase de Taller")

empresas = sorted(pases_df["Empresa"].dropna().unique()) if not pases_df.empty else []

f1, f2, f3, f4 = st.columns(4)

with f1:
    f_folio = st.text_input("No. de Folio")

with f2:
    f_empresa = st.selectbox("Empresa", ["Selecciona empresa"] + empresas)

with f3:
    f_estado = st.selectbox(
        "Estado",
        [
            "Selecciona estado",
            "En Curso / Nuevo",
            "En Curso / Autorizado",
            "En Curso / Sin Comenzar",
            "En Curso / Espera Refacciones",
            "En Curso / En Proceso",
            "Cerrado / Cancelado",
            "Cerrado / Completado",
            "Cerrado / Facturado",
        ]
    )

with f4:
    f_fecha = st.date_input("Fecha", value=None)

if st.button("Buscar"):
    st.session_state.buscar_trigger = True
    st.session_state.modal_reporte = None

# =================================
# RESULTADOS
# =================================
if st.session_state.buscar_trigger:
    resultados = pases_df.copy()

    if f_folio:
        resultados = resultados[resultados["NoFolio"].str.contains(f_folio)]

    if f_empresa != "Selecciona empresa":
        resultados = resultados[resultados["Empresa"] == f_empresa]

    if f_estado != "Selecciona estado":
        resultados = resultados[resultados["Estado"] == f_estado]

    if f_fecha:
        resultados = resultados[resultados["Fecha"].dt.date == f_fecha]

    st.divider()
    st.subheader("Resultados")

    for _, row in resultados.iterrows():
        c1, c2, c3, c4, c5, c6 = st.columns([1,2,2,2,2,1])

        editable = row["Estado"].startswith("En Curso")

        # ======================================================
        # BUTTON COLUMN
        # ======================================================
        with c1:
            label = "Editar" if editable else "Ver"
            if st.button(label, key=f"accion_{row['NoFolio']}"):
                st.session_state.modal_reporte = row.to_dict()

                df = cargar_servicios_folio(row["NoFolio"])

                st.session_state.servicios_df = df

        # ======================================================
        # INFO COLUMNS (UNCHANGED)
        # ======================================================
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
    editable_estado = r["Estado"].startswith("En Curso")

    @st.dialog("Detalle del Pase de Taller")
    def modal():

        st.markdown(f"**No. de Folio:** {r['NoFolio']}")
        st.markdown(f"**Empresa:** {r['Empresa']}")
        st.markdown(f"**Fecha:** {r['Fecha']}")
        st.markdown(f"**Capturó:** {r.get('Capturo', '')}")
        st.markdown(f"**Proveedor:** {r['Proveedor']}")
        st.markdown(f"**No. de Unidad:** {r.get('No. de Unidad', '')}")
        st.markdown(f"**Descripción del Problema:** {r.get('Descripcion Problema', '')}")

        st.divider()
        st.subheader("Información del Proveedor")

        oste_editable = (
            r["Estado"] == "Cerrado / Facturado"
            and not str(r.get("Oste", "")).strip()
        )

        proveedor = (r.get("Proveedor") or "").lower()

        if "interno" in proveedor:
            st.text_input(
                "No. de Reporte",
                value=r.get("No. de Reporte", ""),
                disabled=True
            )
        else:
            oste_val = st.text_input(
                "OSTE",
                value=r.get("Oste", "") or "",
                disabled=not oste_editable
            )

        if (
            r["Estado"] == "Cerrado / Facturado"
            and str(r.get("Oste", "")).strip()
        ):
            st.caption("🔒 OSTE ya registrado — orden en modo solo lectura")

        # ==========================================
        # SMART STATE VISIBILITY
        # ==========================================
        estado_actual = r["Estado"]

        transiciones = {
            "En Curso / Nuevo": [
                "En Curso / Autorizado",
                "Cerrado / Cancelado",
            ],
            "En Curso / Autorizado": [
                "En Curso / Sin Comenzar",
                "En Curso / Espera Refacciones",
                "Cerrado / Cancelado",
            ],
            "En Curso / Sin Comenzar": [
                "En Curso / Espera Refacciones",
                "En Curso / En Proceso",
                "Cerrado / Cancelado",
            ],
            "En Curso / Espera Refacciones": [
                "En Curso / Sin Comenzar",
                "En Curso / En Proceso",
                "Cerrado / Cancelado",
            ],
            "En Curso / En Proceso": [
                "Cerrado / Completado",
                "Cerrado / Facturado",
                "Cerrado / Cancelado",
            ],
        }

        opciones_estado = [estado_actual] + transiciones.get(estado_actual, [])
        opciones_estado = list(dict.fromkeys(opciones_estado))

        nuevo_estado = st.selectbox(
            "Estado",
            opciones_estado,
            index=0,
            disabled=not editable_estado
        )

        editable_servicios = nuevo_estado in [
            "En Curso / Sin Comenzar",
            "En Curso / Espera Refacciones",
        ]

        st.divider()
        st.subheader("Servicios y Refacciones")

        catalogo = cargar_refacciones()

        if catalogo is not None and not catalogo.empty:
            st.session_state.refaccion_seleccionada = st.selectbox(
                "Refacción / Servicio",
                options=catalogo["label"].tolist(),
                index=None,
                disabled=not editable_servicios
            )
        else:
            st.info("Catálogo no disponible para esta empresa.")

        # =====================================================
        # ADD ITEM
        # =====================================================
        if st.button(
            "Agregar refacciones o servicios",
            disabled=not editable_servicios or not st.session_state.refaccion_seleccionada
        ):
            fila = catalogo[catalogo["label"] == st.session_state.refaccion_seleccionada].iloc[0]

            if fila["Parte"] not in st.session_state.servicios_df["Parte"].values:

                precio = pd.to_numeric(fila.get("PU", 0), errors="coerce") or 0
                iva = pd.to_numeric(fila.get("IVA", 0), errors="coerce") or 0

                nueva = {
                    "Parte": fila.get("Parte", ""),
                    "Tipo De Parte": fila.get("Tipo De Parte", "Servicio"),
                    "PU": precio,
                    "IVA": iva,
                    "Cantidad": 1,
                    "Total": (precio + iva),
                }

                st.session_state.servicios_df = pd.concat(
                    [st.session_state.servicios_df, pd.DataFrame([nueva])],
                    ignore_index=True
                )

        # =====================================================
        # EDITOR
        # =====================================================
        column_config = {
            "PU": st.column_config.NumberColumn(format="$ %.2f"),
            "IVA": st.column_config.NumberColumn(format="$ %.2f"),
            "Cantidad": st.column_config.NumberColumn(min_value=1, step=1),
            "Total": st.column_config.NumberColumn(format="$ %.2f"),
        }

        edited_df = st.data_editor(
            st.session_state.servicios_df,
            num_rows="dynamic",
            hide_index=True,
            disabled=not editable_servicios,
            column_config=column_config,
        )

        # =====================================================
        # RECALC TOTALS
        # =====================================================
        if not edited_df.empty:

            for col in ["PU", "Cantidad", "IVA"]:
                edited_df[col] = pd.to_numeric(edited_df[col], errors="coerce").fillna(0)

            edited_df["Total"] = (edited_df["PU"] + edited_df["IVA"]) * edited_df["Cantidad"]

        st.session_state.servicios_df = edited_df

        # =====================================================
        # METRIC
        # =====================================================
        # =============================================
        # VISUAL CURRENCY (UI ONLY)
        # =============================================
        empresa = r.get("Empresa", "")

        if empresa in ["IGLOO TRANSPORT", "PICUS"]:
            moneda = "MXN"
        else:
            moneda = "USD"

        st.metric(
            f"Total ({moneda})",
            f"$ {edited_df.get('Total', pd.Series()).fillna(0).sum():,.2f}"
        )

        st.divider()
        c1, c2 = st.columns(2)

        with c1:
            if st.button("Cancelar"):
                st.session_state.modal_reporte = None
                st.rerun()

        with c2:

            mostrar_aceptar = (
                editable_estado
                or ("interno" not in proveedor and oste_editable)
            )

            label_btn = "Guardar cambios" if editable_estado else "Guardar"

            if mostrar_aceptar and st.button(label_btn, type="primary"):

                estado_actual = r["Estado"]

                if (
                    not editable_servicios
                    and not oste_editable
                    and nuevo_estado == estado_actual
                ):
                    st.session_state.modal_reporte = None
                    st.rerun()

                if nuevo_estado == "En Curso / En Proceso" and st.session_state.servicios_df.empty:
                    st.error("Debe agregar refacciones antes de pasar a 'En Proceso'.")
                    st.stop()

                if nuevo_estado != estado_actual:
                    actualizar_estado_pase(r["Empresa"], r["NoFolio"], nuevo_estado)

                if "interno" not in proveedor:
                    if nuevo_estado == "Cerrado / Facturado":
                        actualizar_oste_pase(
                            r["Empresa"],
                            r["NoFolio"],
                            oste_val
                        )

                usuario = (
                    st.session_state.user.get("name")
                    or st.session_state.user.get("email")
                )
                # =====================================================
                # CREATE MILESTONE ROW IF NO REAL SERVICES
                # =====================================================
                df_serv = st.session_state.servicios_df

                sin_partes = (
                    df_serv.empty
                    or "Parte" not in df_serv.columns
                    or df_serv["Parte"].astype(str).str.strip().eq("").all()
                )

                if sin_partes:
                    registrar_cambio_estado_sin_servicios(
                        r["NoFolio"],
                        usuario,
                        nuevo_estado
                    )

                guardar_servicios_refacciones(
                    r["NoFolio"],
                    usuario,
                    st.session_state.servicios_df,
                    nuevo_estado
                )
                #Log activity
                st.session_state.last_action = f"Folio {r['NoFolio']} → {nuevo_estado}"
                
                st.session_state.modal_reporte = None
                st.cache_data.clear()
                st.rerun()

    modal()
    st.session_state.modal_reporte = None