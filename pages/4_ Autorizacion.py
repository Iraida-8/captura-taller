import streamlit as st
import pandas as pd
from datetime import datetime, date
from auth import require_login, require_access
import gspread
from google.oauth2.service_account import Credentials
import os
from datetime import datetime

fecha_mod = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
# Log estado sin refacciones
# =================================
def registrar_cambio_estado_sin_servicios(folio, usuario, nuevo_estado):
    from datetime import datetime

    estado_fecha_map = {
        "En Curso / Autorizado": "Fecha Autorizado",
        "En Curso / Sin Comenzar": "Fecha Sin Comenzar",
        "En Curso / Espera Refacciones": "Fecha Espera Refacciones",
        "En Curso / En Proceso": "Fecha En Proceso",
        "Cerrado / Facturado": "Fecha Facturado",
        "Cerrado / Completado": "Fecha Completado",
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
            "Parte","TipoCompra","Precio MXP","IVA","Cantidad","Total MXN"
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
        ["Parte","TipoCompra","Precio MXP","IVA","Cantidad","Total MXN"]
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

    # =====================================================
    # 🔥 LINCOLN NORMALIZATION (USD → system columns)
    # =====================================================
    if "PrecioParte" in servicios_df.columns:
        servicios_df["Precio MXP"] = servicios_df["PrecioParte"]
        servicios_df["IVA"] = 0
        servicios_df["Total MXN"] = servicios_df.get("Total USD", 0)

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
            r["TipoCompra"],
            float(r["Precio MXP"] or 0),
            float(r["IVA"] or 0),
            int(r["Cantidad"] or 0),
            float(r["Total MXN"] or 0),
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

pases_df = cargar_pases_taller()

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

    # =================================
    # FECHA H (REQUIRED)
    # =================================
    if "FECHA H" not in df.columns:
        st.error("El catálogo IGLOO no contiene la columna requerida: FECHA H")
        return pd.DataFrame(columns=["Parte", "PU", "IvaParte", "TipoCompra", "label"])

    df["FECHA H"] = pd.to_datetime(df["FECHA H"], errors="coerce")
    df = df[df["FECHA H"] >= pd.Timestamp("2025-01-01")]
    df = df.sort_values("FECHA H", ascending=False)
    df = df.drop_duplicates(subset=["Parte"], keep="first")

    # =================================
    # NUMBER CLEANER (money)
    # =================================
    def limpiar_num(v):
        try:
            return float(str(v).replace("$", "").replace(",", "").strip())
        except:
            return None

    # =================================
    # PRICE DETECTION
    # =================================
    normalized_cols = {c: str(c).strip().lower() for c in df.columns}

    precio_col = next(
        (orig for orig, norm in normalized_cols.items()
         if norm in ["precioparte", "precio", "pu", "costo"]),
        None
    )

    if not precio_col:
        st.error(f"Columnas encontradas: {list(df.columns)}")
        st.error("El catálogo IGLOO no contiene una columna de precio válida.")
        return pd.DataFrame(columns=["Parte", "PU", "IvaParte", "TipoCompra", "label"])

    df["PU"] = df[precio_col].apply(limpiar_num)

    # =================================
    # NORMALIZE IVA (money, not percent)
    # =================================
    if "IvaParte" in df.columns:
        df["IvaParte"] = df["IvaParte"].apply(limpiar_num).fillna(0)
    else:
        df["IvaParte"] = 0

    # =================================
    # ENSURE TipoCompra
    # =================================
    if "TipoCompra" not in df.columns:
        df["TipoCompra"] = "Servicio"

    # =================================
    # BUILD LABEL
    # =================================
    df["label"] = df.apply(
        lambda r: f"{r['Parte']} - ${r['PU']:,.2f}"
        if pd.notna(r["PU"]) else r["Parte"],
        axis=1
    )

    # =================================
    # RETURN
    # =================================
    return df[["Parte", "PU", "IvaParte", "TipoCompra", "label"]]

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

    def limpiar_num(v):
        try:
            return float(str(v).replace("$", "").replace(",", "").strip())
        except:
            return None

    # ================================
    # PRICE → PrecioParte (USD)
    # ================================
    if "PrecioParte" in df.columns:
        df["PrecioParte"] = df["PrecioParte"].apply(limpiar_num)
    else:
        df["PrecioParte"] = None

    # ================================
    # TipoCompra default
    # ================================
    if "TipoCompra" not in df.columns:
        df["TipoCompra"] = "Servicio"

    # ================================
    # Label (USD)
    # ================================
    df["label"] = df.apply(
        lambda r: f"{r['Parte']} - USD ${r['PrecioParte']:,.2f}"
        if pd.notna(r["PrecioParte"]) else r["Parte"],
        axis=1
    )

    return df[["Parte", "TipoCompra", "PrecioParte", "label"]]

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

    def limpiar_num(v):
        try:
            return float(str(v).replace("$", "").replace(",", "").strip())
        except:
            return None

    normalized_cols = {c: str(c).strip().lower() for c in df.columns}

    precio_col = next(
        (orig for orig, norm in normalized_cols.items()
         if norm in ["precioparte", "precio", "pu", "costo"]),
        None
    )

    if precio_col:
        df["PU"] = df[precio_col].apply(limpiar_num)
    else:
        df["PU"] = None

    if "IvaParte" in df.columns:
        df["IvaParte"] = df["IvaParte"].apply(limpiar_num).fillna(0)
    else:
        df["IvaParte"] = 0

    if "TipoCompra" not in df.columns:
        df["TipoCompra"] = "Servicio"

    df["label"] = df.apply(
        lambda r: f"{r['Parte']} - ${r['PU']:,.2f}"
        if pd.notna(r["PU"]) else r["Parte"],
        axis=1
    )

    return df[["Parte", "PU", "IvaParte", "TipoCompra", "label"]]

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

    def limpiar_num(v):
        try:
            return float(str(v).replace("$", "").replace(",", "").strip())
        except:
            return None

    # Defensive price-column detection (same pattern we discussed)
    precio_col = next(
        (c for c in df.columns if c.lower() in ["precioparte", "precio", "pu", "costo"]),
        None
    )

    if precio_col:
        df["PU"] = df[precio_col].apply(limpiar_num)
    else:
        df["PU"] = None

    df["label"] = df.apply(
        lambda r: f"{r['Parte']} - ${r['PU']:,.2f}"
        if pd.notna(r["PU"]) else r["Parte"],
        axis=1
    )

    return df[["Parte", "PU", "label"]]

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

    def limpiar_num(v):
        try:
            return float(str(v).replace("$", "").replace(",", "").strip())
        except:
            return None

    # Defensive price-column detection
    precio_col = next(
        (c for c in df.columns if c.lower() in ["precioparte", "precio", "pu", "costo"]),
        None
    )

    if precio_col:
        df["PU"] = df[precio_col].apply(limpiar_num)
    else:
        df["PU"] = None

    df["label"] = df.apply(
        lambda r: f"{r['Parte']} - ${r['PU']:,.2f}"
        if pd.notna(r["PU"]) else r["Parte"],
        axis=1
    )

    return df[["Parte", "PU", "label"]]

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

    if st.session_state.get("last_action"):
        ultima = st.session_state.last_action

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
                {ultima}
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
st.session_state.setdefault("refaccion_seleccionada", None)
st.session_state.setdefault(
    "servicios_df",
    pd.DataFrame(columns=[
        "Parte","TipoCompra","Precio MXP","IVA","Cantidad","Total MXN"
    ])
)

# =================================
# TOP 10 EN CURSO
# =================================
st.subheader("Últimos 10 Pases de Taller (Nuevos)")

if not pases_df.empty:
    top10 = (
        pases_df[pases_df["Estado"] == "En Curso / Nuevo"]
        .sort_values("Fecha", ascending=False)
        .head(10)
        [["NoFolio","Empresa","Capturo","Fecha","Proveedor","Estado"]]
    )

    if top10.empty:
        st.info("No hay pases en estado Nuevo.")
    else:
        st.dataframe(top10, hide_index=True, width="stretch")

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

                # ==========================================
                # LINCOLN → ALWAYS FORCE USD STRUCTURE
                # ==========================================
                if row["Empresa"] == "LINCOLN FREIGHT":

                    if df.empty:
                        df = pd.DataFrame(columns=[
                            "Parte", "TipoCompra", "PrecioParte", "Cantidad", "Total USD"
                        ])
                    else:
                        df["PrecioParte"] = df.get("Precio MXP", 0)
                        df["Cantidad"] = df.get("Cantidad", 0)
                        df["Total USD"] = df.get("Total MXN", 0)

                        df = df[[
                            "Parte", "TipoCompra", "PrecioParte", "Cantidad", "Total USD"
                        ]]

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
        st.markdown(f"**Sucursal:** {r.get('Sucursal', '')}")

        st.divider()
        st.subheader("Información del Proveedor")

        oste_editable = (
            r["Estado"] == "Cerrado / Facturado"
            and not str(r.get("Oste", "")).strip()
        )

        proveedor = (r.get("Proveedor") or "").lower()

        #currency detector
        es_lincoln = r["Empresa"] == "LINCOLN FREIGHT"

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

        catalogo = cargar_catalogo_por_empresa(r["Empresa"])

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

                if es_lincoln:
                    precio = pd.to_numeric(fila.get("PrecioParte", 0), errors="coerce") or 0

                    nueva = {
                        "Parte": fila.get("Parte", ""),
                        "TipoCompra": fila.get("TipoCompra", "Servicio"),
                        "PrecioParte": precio,
                        "Cantidad": 1,
                        "Total USD": precio,
                    }

                else:
                    precio = pd.to_numeric(fila.get("PU", 0), errors="coerce") or 0
                    iva = pd.to_numeric(fila.get("IvaParte", 0), errors="coerce") or 0

                    nueva = {
                        "Parte": fila.get("Parte", ""),
                        "TipoCompra": fila.get("TipoCompra", "Servicio"),
                        "Precio MXP": precio,
                        "IVA": iva,
                        "Cantidad": 1,
                        "Total MXN": (precio + iva),
                    }

                st.session_state.servicios_df = pd.concat(
                    [st.session_state.servicios_df, pd.DataFrame([nueva])],
                    ignore_index=True
                )

        # =====================================================
        # EDITOR
        # =====================================================
        if es_lincoln:
            column_config = {
                "PrecioParte": st.column_config.NumberColumn(format="$ %.2f"),
                "Cantidad": st.column_config.NumberColumn(min_value=1, step=1),
                "Total USD": st.column_config.NumberColumn(format="$ %.2f"),
            }
        else:
            column_config = {
                "Precio MXP": st.column_config.NumberColumn(format="$ %.2f"),
                "IVA": st.column_config.NumberColumn(format="$ %.2f"),
                "Cantidad": st.column_config.NumberColumn(min_value=1, step=1),
                "Total MXN": st.column_config.NumberColumn(format="$ %.2f"),
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

            if es_lincoln:
                for col in ["PrecioParte", "Cantidad"]:
                    edited_df[col] = pd.to_numeric(edited_df[col], errors="coerce").fillna(0)

                edited_df["Total USD"] = edited_df["PrecioParte"] * edited_df["Cantidad"]

            else:
                for col in ["Precio MXP", "Cantidad", "IVA"]:
                    edited_df[col] = pd.to_numeric(edited_df[col], errors="coerce").fillna(0)

                edited_df["Total MXN"] = (
                    (edited_df["Precio MXP"] + edited_df["IVA"])
                    * edited_df["Cantidad"]
                )

        st.session_state.servicios_df = edited_df

        # =====================================================
        # METRIC
        # =====================================================
        if es_lincoln:
            st.metric(
                "Total USD",
                f"$ {edited_df.get('Total USD', pd.Series()).fillna(0).sum():,.2f}"
            )
        else:
            st.metric(
                "Total MXN",
                f"$ {edited_df.get('Total MXN', pd.Series()).fillna(0).sum():,.2f}"
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