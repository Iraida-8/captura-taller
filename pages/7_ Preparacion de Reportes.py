import streamlit as st
import pandas as pd
from datetime import date, datetime
from auth import require_login, require_access
import gspread
from google.oauth2.service_account import Credentials
import os
from supabase import create_client
from decimal import Decimal
import unicodedata

import io

def to_excel_bytes(dfs_dict):
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for sheet_name, df in dfs_dict.items():

            df_export = df.copy()

            df_export = df_export.astype(str)

            df_export.to_excel(writer, index=False, sheet_name=sheet_name[:31])

    output.seek(0)
    return output

# =================================
# Page configuration
# =================================
st.set_page_config(
    page_title="Preparación de Reportes",
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
require_access("prepara_reportes")

# =================================
# Page Cache and State Management
# =================================
@st.cache_resource
def get_supabase_client():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_SERVICE_KEY"]
    )

# =================================
# Top navigation
# =================================
if st.button("⬅ Volver al Dashboard"):
    st.switch_page("pages/dashboard.py")

st.divider()

st.title("📊 Consulta, Preparación y Generación de Reportes")

# =================================
# LOADERS
# =================================
@st.cache_data
def load_refacciones_igloo():
    supabase = get_supabase_client()

    all_data = []
    limit = 1000
    offset = 0

    while True:
        res = (
            supabase
            .table("refacciones_data_igloo")
            .select("*")
            .range(offset, offset + limit - 1)
            .execute()
        )

        data = res.data

        if not data:
            break

        all_data.extend(data)

        if len(data) < limit:
            break

        offset += limit

    return pd.DataFrame(all_data)

@st.cache_data
def load_ostes_igloo():
    supabase = get_supabase_client()

    all_data = []
    limit = 1000
    offset = 0

    while True:
        res = (
            supabase
            .table("ostes_igloo")
            .select("*")
            .range(offset, offset + limit - 1)
            .execute()
        )

        data = res.data

        if not data:
            break

        all_data.extend(data)

        if len(data) < limit:
            break

        offset += limit

    return pd.DataFrame(all_data)

@st.cache_data
def load_mano_obra_igloo():
    supabase = get_supabase_client()

    all_data = []
    limit = 1000
    offset = 0

    while True:
        res = (
            supabase
            .table("mano_obra_igloo")
            .select("*")
            .range(offset, offset + limit - 1)
            .execute()
        )

        data = res.data

        if not data:
            break

        all_data.extend(data)

        if len(data) < limit:
            break

        offset += limit

    return pd.DataFrame(all_data)

@st.cache_data
def load_refacciones_lincoln():
    supabase = get_supabase_client()
    all_data, limit, offset = [], 1000, 0

    while True:
        res = supabase.table("refacciones_data_lincoln").select("*").range(offset, offset + limit - 1).execute()
        data = res.data
        if not data: break
        all_data.extend(data)
        if len(data) < limit: break
        offset += limit

    return pd.DataFrame(all_data)

@st.cache_data
def load_ostes_lincoln():
    supabase = get_supabase_client()
    all_data, limit, offset = [], 1000, 0

    while True:
        res = supabase.table("ostes_lincoln").select("*").range(offset, offset + limit - 1).execute()
        data = res.data
        if not data: break
        all_data.extend(data)
        if len(data) < limit: break
        offset += limit

    return pd.DataFrame(all_data)

@st.cache_data
def load_mano_obra_lincoln():
    supabase = get_supabase_client()
    all_data, limit, offset = [], 1000, 0

    while True:
        res = supabase.table("mano_obra_lincoln").select("*").range(offset, offset + limit - 1).execute()
        data = res.data
        if not data: break
        all_data.extend(data)
        if len(data) < limit: break
        offset += limit

    return pd.DataFrame(all_data)

@st.cache_data
def load_refacciones_picus():
    supabase = get_supabase_client()
    all_data, limit, offset = [], 1000, 0

    while True:
        res = supabase.table("refacciones_data_picus").select("*").range(offset, offset + limit - 1).execute()
        data = res.data
        if not data: break
        all_data.extend(data)
        if len(data) < limit: break
        offset += limit

    return pd.DataFrame(all_data)

@st.cache_data
def load_ostes_picus():
    supabase = get_supabase_client()
    all_data, limit, offset = [], 1000, 0

    while True:
        res = supabase.table("ostes_picus").select("*").range(offset, offset + limit - 1).execute()
        data = res.data
        if not data: break
        all_data.extend(data)
        if len(data) < limit: break
        offset += limit

    return pd.DataFrame(all_data)

@st.cache_data
def load_mano_obra_picus():
    supabase = get_supabase_client()
    all_data, limit, offset = [], 1000, 0

    while True:
        res = supabase.table("mano_obra_picus").select("*").range(offset, offset + limit - 1).execute()
        data = res.data
        if not data: break
        all_data.extend(data)
        if len(data) < limit: break
        offset += limit

    return pd.DataFrame(all_data)

@st.cache_data
def load_refacciones_setfreight():
    supabase = get_supabase_client()
    all_data, limit, offset = [], 1000, 0

    while True:
        res = supabase.table("refacciones_data_setfreight").select("*").range(offset, offset + limit - 1).execute()
        data = res.data
        if not data: break
        all_data.extend(data)
        if len(data) < limit: break
        offset += limit

    return pd.DataFrame(all_data)

@st.cache_data
def load_ostes_setfreight():
    supabase = get_supabase_client()
    all_data, limit, offset = [], 1000, 0

    while True:
        res = supabase.table("ostes_setfreight").select("*").range(offset, offset + limit - 1).execute()
        data = res.data
        if not data: break
        all_data.extend(data)
        if len(data) < limit: break
        offset += limit

    return pd.DataFrame(all_data)

@st.cache_data
def load_mano_obra_setfreight():
    supabase = get_supabase_client()
    all_data, limit, offset = [], 1000, 0

    while True:
        res = supabase.table("mano_obra_setfreight").select("*").range(offset, offset + limit - 1).execute()
        data = res.data
        if not data: break
        all_data.extend(data)
        if len(data) < limit: break
        offset += limit

    return pd.DataFrame(all_data)

@st.cache_data
def load_refacciones_logis():
    supabase = get_supabase_client()
    all_data, limit, offset = [], 1000, 0

    while True:
        res = supabase.table("refacciones_data_logis").select("*").range(offset, offset + limit - 1).execute()
        data = res.data
        if not data: break
        all_data.extend(data)
        if len(data) < limit: break
        offset += limit

    return pd.DataFrame(all_data)

@st.cache_data
def load_ostes_logis():
    supabase = get_supabase_client()
    all_data, limit, offset = [], 1000, 0

    while True:
        res = supabase.table("ostes_logis").select("*").range(offset, offset + limit - 1).execute()
        data = res.data
        if not data: break
        all_data.extend(data)
        if len(data) < limit: break
        offset += limit

    return pd.DataFrame(all_data)

@st.cache_data
def load_mano_obra_logis():
    supabase = get_supabase_client()
    all_data, limit, offset = [], 1000, 0

    while True:
        res = supabase.table("mano_obra_logis").select("*").range(offset, offset + limit - 1).execute()
        data = res.data
        if not data: break
        all_data.extend(data)
        if len(data) < limit: break
        offset += limit

    return pd.DataFrame(all_data)

#Load Units my dude
@st.cache_data
def load_vehicle_units():
    try:
        supabase = get_supabase_client()

        response = supabase.table("vehicle_units").select("*").execute()
        df = pd.DataFrame(response.data)

        if not df.empty:
            df.columns = df.columns.str.strip().str.lower()

        return df

    except Exception as e:
        st.error(f"Error cargando vehicle_units: {e}")
        return pd.DataFrame()

# =================================
# MODE SELECTOR
# =================================
st.subheader("¿Qué quieres hacer?")

col_a, col_b = st.columns(2)

if "modo_reportes" not in st.session_state:
    st.session_state.modo_reportes = None

with col_a:
    if st.button("📄 Consultar Reportes", use_container_width=True):

        keys_to_delete = [
            "ordenes_IGLOO", "ordenes_LINCOLN_FREIGHT", "ordenes_PICUS",
            "ordenes_SET_FREIGHT_INTERNATIONAL", "ordenes_SET_LOGIS_PLUS",
            "ostes_IGLOO", "ostes_LINCOLN_FREIGHT", "ostes_PICUS",
            "ostes_SET_FREIGHT_INTERNATIONAL", "ostes_SET_LOGIS_PLUS",
            "mantenimientos_IGLOO", "mantenimientos_LINCOLN_FREIGHT",
            "mantenimientos_PICUS", "mantenimientos_SET_FREIGHT_INTERNATIONAL",
            "mantenimientos_SET_LOGIS_PLUS"
        ]

        for k in keys_to_delete:
            if k in st.session_state:
                del st.session_state[k]

        st.session_state.modo_reportes = "consultar"


with col_b:
    if st.button("📤 Cargar Reportes", use_container_width=True):

        keys_to_delete = [
            "consulta_empresa",
            "consulta_year",
            "consulta_mes"
        ]

        for k in keys_to_delete:
            if k in st.session_state:
                del st.session_state[k]

        st.session_state.modo_reportes = "cargar"

# =================================
# FLOW CONTROL
# =================================
if st.session_state.modo_reportes is None:
    st.info("Selecciona una opción para continuar.")
    st.stop()

if st.session_state.modo_reportes == "consultar":

    st.divider()
    st.header("📄 Consulta de Reportes")

    # =================================
    # FILTERS
    # =================================
    col1, col2, col3 = st.columns([2, 1, 1])

    companies = [
        "SELECCIONA EMPRESA",
        "IGLOO",
        "LINCOLN FREIGHT",
        "PICUS",
        "SET FREIGHT INTERNATIONAL",
        "SET LOGIS PLUS"
    ]

    with col1:
        empresa_consulta = st.selectbox(
            "Selecciona la empresa:",
            companies,
            key="consulta_empresa"
        )

    with col2:
        temp_df = load_refacciones_igloo()

        if not temp_df.empty and "anio" in temp_df.columns:
            temp_df["anio"] = pd.to_numeric(temp_df["anio"], errors="coerce")
            years = sorted(temp_df["anio"].dropna().unique(), reverse=True)
        else:
            years = []

        year_options = ["Todos"] + list(years)

        year_filter = st.selectbox(
            "Filtrar por año (opcional):",
            year_options,
            key="consulta_year"
        )
    with col3:
        if empresa_consulta == "IGLOO":
            temp_df_mes = load_refacciones_igloo()
        elif empresa_consulta == "LINCOLN FREIGHT":
            temp_df_mes = load_refacciones_lincoln()
        elif empresa_consulta == "PICUS":
            temp_df_mes = load_refacciones_picus()
        elif empresa_consulta == "SET FREIGHT INTERNATIONAL":
            temp_df_mes = load_refacciones_setfreight()
        elif empresa_consulta == "SET LOGIS PLUS":
            temp_df_mes = load_refacciones_logis()
        else:
            temp_df_mes = pd.DataFrame()

        MONTH_ORDER = {
            "january": 1, "february": 2, "march": 3, "april": 4,
            "may": 5, "june": 6, "july": 7, "august": 8,
            "september": 9, "october": 10, "november": 11, "december": 12
        }

        if not temp_df_mes.empty and "mes" in temp_df_mes.columns:

            meses_clean = (
                temp_df_mes["mes"]
                .dropna()
                .astype(str)
                .str.strip()
                .str.lower()
            )

            meses_clean = meses_clean[meses_clean.isin(MONTH_ORDER.keys())]

            meses_sorted = sorted(
                meses_clean.unique(),
                key=lambda x: MONTH_ORDER[x]
            )

            meses = [m.capitalize() for m in meses_sorted]

        else:
            meses = []

        mes_options = ["Todos"] + meses

        mes_filter = st.selectbox(
            "Filtrar por mes (opcional):",
            mes_options,
            key="consulta_mes"
        )

        mes_filter_norm = mes_filter.lower() if mes_filter != "Todos" else "Todos"

    # =================================
    # VALIDATION
    # =================================
    if empresa_consulta == "SELECCIONA EMPRESA":
        st.warning("Selecciona una empresa para consultar.")
        st.stop()

    st.success(f"Consultando: {empresa_consulta}")

    if year_filter != "Todos":
        st.info(f"Filtro activo: Año {year_filter}")

    st.divider()

    # =================================
    # LOAD DATA
    # =================================
    if empresa_consulta == "IGLOO":
        df_ref = load_refacciones_igloo()
        df_ost = load_ostes_igloo()
        df_mo  = load_mano_obra_igloo()

    elif empresa_consulta == "LINCOLN FREIGHT":
        df_ref = load_refacciones_lincoln()
        df_ost = load_ostes_lincoln()
        df_mo  = load_mano_obra_lincoln()

    elif empresa_consulta == "PICUS":
        df_ref = load_refacciones_picus()
        df_ost = load_ostes_picus()
        df_mo  = load_mano_obra_picus()

    elif empresa_consulta == "SET FREIGHT INTERNATIONAL":
        df_ref = load_refacciones_setfreight()
        df_ost = load_ostes_setfreight()
        df_mo  = load_mano_obra_setfreight()

    elif empresa_consulta == "SET LOGIS PLUS":
        df_ref = load_refacciones_logis()
        df_ost = load_ostes_logis()
        df_mo  = load_mano_obra_logis()

    # -------------------------------
    # CLEAN COLUMNS
    # -------------------------------
    def clean(df):
        df.columns = df.columns.str.strip().str.lower()
        return df

    df_ref = clean(df_ref)
    df_ost = clean(df_ost)
    df_mo  = clean(df_mo)

    # -------------------------------
    # NORMALIZE MES
    # -------------------------------
    def normalize_mes(val):
        if pd.isna(val):
            return None
        return str(val).strip().lower()

    for df in [df_ref, df_ost, df_mo]:
        if "mes" in df.columns:
            df["mes"] = df["mes"].apply(normalize_mes)

    # -------------------------------
    # DROP UNUSED
    # -------------------------------
    cols_to_drop = ["id", "created_at"]

    df_ref = df_ref.drop(columns=[c for c in cols_to_drop if c in df_ref.columns])
    df_ost = df_ost.drop(columns=[c for c in cols_to_drop if c in df_ost.columns])
    df_mo  = df_mo.drop(columns=[c for c in cols_to_drop if c in df_mo.columns])

    # -------------------------------
    # ENSURE YEAR NUMERIC
    # -------------------------------
    for df in [df_ref, df_ost, df_mo]:
        if "anio" in df.columns:
            df["anio"] = pd.to_numeric(df["anio"], errors="coerce")

    # -------------------------------
    # FILTER YEAR
    # -------------------------------
    if year_filter != "Todos":
        df_ref = df_ref[df_ref["anio"] == year_filter]
        df_ost = df_ost[df_ost["anio"] == year_filter]
        df_mo  = df_mo[df_mo["anio"] == year_filter]

    # -------------------------------
    # FILTER MES
    # -------------------------------
    if mes_filter_norm != "Todos":
        df_ref = df_ref[df_ref["mes"] == mes_filter_norm]
        df_ost = df_ost[df_ost["mes"] == mes_filter_norm]
        df_mo  = df_mo[df_mo["mes"] == mes_filter_norm]

    # -------------------------------
    # RENAME
    # -------------------------------
    df_ref = df_ref.rename(columns={
        "anio": "Año",
        "mes": "Mes",
        "fecha_analisis": "Fecha Analisis",
        "folio": "Folio",
        "contrarecibo": "Contrarecibo",
        "fecha_compra": "Fecha Compra",
        "nombre_proveedor": "NombreProveedor",
        "factura": "Factura",
        "unidad": "Unidad",
        "flotilla": "Flotilla",
        "modelo": "Modelo",
        "tipo_unidad": "Tipo De Unidad",
        "sucursal": "Sucursal",
        "parte": "Parte",
        "tipo_parte": "Tipo De Parte",
        "cantidad": "Cantidad",
        "pu": "PU",
        "precio_parte": "PrecioParte",
        "precio_sin_iva": "Precio Sin IVA",
        "tasa_iva": "Tasa IVA",
        "iva": "IVA",
        "tc": "TC",
        "pu_usd": "PU USD",
        "total_usd": "Total USD",
        "total_correccion": "Total Correccion",
        "moneda": "Moneda",
        "usuario": "Usuario",
        "reporte": "Reporte",
        "descripcion": "Descripcion",
        "razon_reparacion": "Razon Reparacion"
    })

    df_ost = df_ost.rename(columns={
        "anio": "Año",
        "mes": "Mes",
        "oste": "OSTE",
        "fecha_analisis": "Fecha Analisis",
        "reporte": "Reporte",
        "acreedor": "Acreedor",
        "fecha_factura": "Fecha Factura",
        "fecha_oste": "Fecha OSTE",
        "fecha_cierre": "Fecha Cierre",
        "dias_para_cerrar_orden": "Dias para cerrar orden",
        "dias_reparacion": "Dias Reparacion",
        "empresa": "Empresa",
        "sucursal": "Sucursal",
        "observaciones": "Observaciones",
        "status_ct": "Status CT",
        "factura": "Factura",
        "subtotal": "Subtotal",
        "iva": "IVA",
        "total_oste": "Total oste",
        "moneda": "Moneda",
        "tc": "TC",
        "total_correccion": "Total Correccion",
        "unidad": "Unidad",
        "flotilla": "Flotilla",
        "modelo": "Modelo",
        "descripcion": "Descripcion",
        "tipo_de_unidad": "Tipo De Unidad",
        "razon_de_servicio": "Razon de servicio"
    })

    df_mo = df_mo.rename(columns={
        "anio": "Año",
        "mes": "Mes",
        "unidad": "Unidad",
        "fecha_analisis": "Fecha Analisis",
        "flotilla": "Flotilla",
        "modelo": "Modelo",
        "tipo_unidad": "Tipo Unidad",
        "sucursal": "Sucursal",
        "reporte": "Reporte",
        "fecha_registro": "Fecha Registro",
        "fecha_aceptado": "Fecha Aceptado",
        "fecha_iniciada": "Fecha Iniciada",
        "fecha_liberada": "Fecha Liberada",
        "fecha_terminada": "Fecha Terminada",
        "nombre_cliente": "Nombre Cliente",
        "factura": "Factura",
        "estatus": "Estatus",
        "subtotal": "Sub Total",
        "iva": "IVA",
        "total": "Total",
        "total_correccion": "Total Correccion",
        "tc": "TC",
        "total_usd": "Total USD",
        "descripcion": "Descripcion",
        "razon_reparacion": "Razon Reparacion",
        "diferencia": "Diferencia",
        "comentarios": "Comentarios"
    })

    # -------------------------------
    # FORMAT DATES (GLOBAL)
    # -------------------------------
    def format_dates(df):
        for col in df.columns:
            if "fecha" in col.lower():
                df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime("%d/%m/%y")
        return df

    df_ref = format_dates(df_ref)
    df_ost = format_dates(df_ost)
    df_mo  = format_dates(df_mo)

    # -------------------------------
    # DISPLAY
    # -------------------------------
    st.subheader(f"🔧 Refacciones {empresa_consulta}")
    st.dataframe(df_ref, use_container_width=True)

    st.download_button(
        label="⬇️ Descargar Refacciones",
        data=to_excel_bytes({"Refacciones": df_ref}),
        file_name=f"Refacciones_{empresa_consulta}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

    st.divider()

    st.subheader(f"💰 OSTES {empresa_consulta}")
    st.dataframe(df_ost, use_container_width=True)

    st.download_button(
        label="⬇️ Descargar OSTES",
        data=to_excel_bytes({"OSTES": df_ost}),
        file_name=f"OSTES_{empresa_consulta}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

    st.divider()

    st.subheader(f"🚛 Mano de Obra {empresa_consulta}")
    st.dataframe(df_mo, use_container_width=True)

    st.download_button(
        label="⬇️ Descargar Mano de Obra",
        data=to_excel_bytes({"Mano_de_Obra": df_mo}),
        file_name=f"Mano_de_Obra_{empresa_consulta}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

    st.stop()
# =================================
# Company selector
# =================================
companies = [
    "SELECCIONA EMPRESA",
    "IGLOO",
    "LINCOLN FREIGHT",
    "PICUS",
    "SET FREIGHT INTERNATIONAL",
    "SET LOGIS PLUS"
]

empresa = st.selectbox("Selecciona la empresa:", companies)

EMPRESA_MAP = {
    "IGLOO": "IGT",
    "LINCOLN FREIGHT": "LIN",
    "PICUS": "PIC",
    "SET LOGIS PLUS": "SLP",
    "SET FREIGHT INTERNATIONAL": "SET"
}

if empresa == "SELECCIONA EMPRESA":
    st.warning("Debes seleccionar una empresa para continuar.")
    st.stop()

st.success(f"Empresa seleccionada: {empresa}")

# =============================
# LOAD VEHICLE UNITS (HIDDEN)
# =============================
df_units = load_vehicle_units()

empresa_code = EMPRESA_MAP.get(empresa)

if df_units is not None and not df_units.empty and empresa_code:

    df_units_filtered = df_units[df_units["empresa"] == empresa_code].copy()

    # Keep only relevant columns
    cols_keep = [
        "empresa", "unidad", "marca", "modelo",
        "vin", "tipo_unidad", "sucursal", "estado"
    ]

    df_units_filtered = df_units_filtered[[c for c in cols_keep if c in df_units_filtered.columns]]

# =================================
# Dynamic uploader keys
# =================================
key_suffix = empresa.replace(" ", "_")

key_ordenes = f"ordenes_{key_suffix}"
key_ostes = f"ostes_{key_suffix}"
key_mantenimientos = f"mantenimientos_{key_suffix}"

# =================================
# Normalize text
# =================================
def normalize_text(text):
    text = text.lower()
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c))

# =================================
# Validate filename
# =================================
def validate_filename(file, required_words):
    name = normalize_text(file.name)
    return all(word in name for word in required_words)

# =================================
# Read file safely
# =================================
def read_file(file):
    try:
        if file.name.endswith(".csv"):
            try:
                return pd.read_csv(file, encoding="utf-8")
            except:
                file.seek(0)
                return pd.read_csv(file, encoding="latin-1")
        elif file.name.endswith(".xlsx"):
            return pd.read_excel(file, engine="openpyxl")
        else:
            st.error("Formato no soportado. Usa CSV o XLSX.")
            return None
    except Exception as e:
        st.error(f"Error al leer archivo: {e}")
        return None

# =================================
# LOAD TC FROM SUPABASE
# =================================
@st.cache_data
def load_tc():
    try:
        supabase = get_supabase_client()

        response = supabase.table("tc_mensual").select("*").execute()

        df = pd.DataFrame(response.data)

        if not df.empty:
            df.columns = df.columns.str.lower()

            MESES_MAP = {
                "january": 1, "february": 2, "march": 3, "april": 4,
                "may": 5, "june": 6, "july": 7, "august": 8,
                "september": 9, "october": 10, "november": 11, "december": 12
            }

            df["month"] = df["month"].str.lower().map(MESES_MAP)

            df["year"] = df["year"].astype(int)
            df["month"] = df["month"].astype(int)
            df["date"] = pd.to_datetime(df["date"], errors="coerce")

            # ✅ ADD THIS
            df["year"] = df["year"].astype(int)
            df["month"] = df["month"].astype(int)


        return df

    except Exception as e:
        st.error(f"Error cargando TC: {e}")
        return None
        
# =================================
# LOAD TC DATA
# =================================
df_tc = load_tc()

# =================================
# Uploaders
# =================================
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("1. Buscar Ordenes SAC")
    file_ordenes = st.file_uploader(
        "Sube Buscar Ordenes SAC",
        type=["csv", "xlsx"],
        key=key_ordenes
    )

with col2:
    st.subheader("2. Reporte Ostes")
    file_ostes = st.file_uploader(
        "Sube Reporte Ostes",
        type=["csv", "xlsx"],
        key=key_ostes
    )

with col3:
    st.subheader("3. Reporte de Mantenimientos")
    file_mantenimientos = st.file_uploader(
        "Sube Reporte de Mantenimientos",
        type=["csv", "xlsx"],
        key=key_mantenimientos
    )

st.divider()

# =================================
# Display tables (collapsible)
# =================================

# ORDENES
if file_ordenes:
    if not validate_filename(file_ordenes, ["buscar", "ordenes", "sac"]):
        st.error("El archivo debe contener: buscar + ordenes + sac en el nombre.")
    else:
        df = read_file(file_ordenes)
        if df is not None:
            with st.expander("📄 Buscar Ordenes SAC"):
                st.dataframe(df, use_container_width=True)

                st.download_button(
                    label="⬇️ Descargar Ordenes SAC",
                    data=to_excel_bytes({"Ordenes": df}),
                    file_name="Ordenes_SAC.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

# OSTES
if file_ostes:
    if not validate_filename(file_ostes, ["ostes"]):
        st.error("El archivo debe contener: ostes en el nombre.")
    else:
        df = read_file(file_ostes)
        if df is not None:
            with st.expander(f"📄 Reporte Ostes ({empresa})"):
                st.dataframe(df, use_container_width=True)

                st.download_button(
                    label="⬇️ Descargar Ostes",
                    data=to_excel_bytes({"Ostes": df}),
                    file_name=f"Ostes_{empresa}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

# MANTENIMIENTOS
if file_mantenimientos:
    if not validate_filename(file_mantenimientos, ["mantenimientos"]):
        st.error("El archivo debe contener: mantenimientos en el nombre.")
    else:
        df = read_file(file_mantenimientos)
        if df is not None:
            with st.expander(f"📄 Reporte de Mantenimientos ({empresa})"):
                st.dataframe(df, use_container_width=True)

                st.download_button(
                    label="⬇️ Descargar Mantenimientos",
                    data=to_excel_bytes({"Mantenimientos": df}),
                    file_name=f"Mantenimientos_{empresa}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )


# =================================
# BUILD DATA REFACCIONES (CLEAN)
# =================================
if file_ordenes and file_mantenimientos:

    valid_ordenes = validate_filename(file_ordenes, ["buscar", "ordenes", "sac"])
    valid_mant = validate_filename(file_mantenimientos, ["mantenimientos"])

    if valid_ordenes and valid_mant:

        df_ordenes = read_file(file_ordenes)
        df_mant = read_file(file_mantenimientos)

        if df_ordenes is not None and df_mant is not None:

            # =============================
            # NORMALIZE KEYS (CRITICAL)
            # =============================
            df_ordenes["Reporte"] = (
                pd.to_numeric(df_ordenes["Reporte"], errors="coerce")
                .astype("Int64")
                .astype(str)
            )

            df_mant["Reporte"] = (
                pd.to_numeric(df_mant["# Reporte"], errors="coerce")
                .astype("Int64")
                .astype(str)
            )

            # =============================
            # DATE FROM SAC
            # =============================
            df_ordenes["Fecha Compra"] = pd.to_datetime(df_ordenes["Fecha"], errors="coerce")

            df_ordenes["Año"] = df_ordenes["Fecha Compra"].dt.year
            df_ordenes["Mes"] = df_ordenes["Fecha Compra"].dt.month

            # =============================
            # JOIN MANTENIMIENTOS
            # =============================
            mant_lookup = df_mant[[
                "Reporte",
                "Tipo Unidad",
                "Descripcion",
                "Razon Servicio",
                "Fecha Liberada"
            ]].drop_duplicates(subset=["Reporte"])

            df_final_ref = df_ordenes.merge(
                mant_lookup,
                on="Reporte",
                how="left"
            )

            # =============================
            # FECHA ANALISIS
            # =============================
            df_final_ref["Fecha Analisis"] = pd.to_datetime(
                df_final_ref["Fecha Liberada"],
                errors="coerce"
            )

            # =============================
            # TC MERGE
            # =============================
            df_final_ref = df_final_ref.dropna(subset=["Año", "Mes"])

            df_final_ref["Año"] = df_final_ref["Año"].astype(int)
            df_final_ref["Mes"] = df_final_ref["Mes"].astype(int)

            if df_tc is not None and not df_tc.empty:

                df_final_ref = df_final_ref.merge(
                    df_tc,
                    left_on=["Año", "Mes"],
                    right_on=["year", "month"],
                    how="left"
                )

                df_final_ref["TC"] = df_final_ref["tc"]    # numeric for calculations

            else:
                df_final_ref["TC"] = 1

            # =============================
            # FINANCIALS
            # =============================
            df_final_ref["Precio Sin IVA"] = df_final_ref["PrecioParte"] / (
                1 + df_final_ref["Tasaiva"].fillna(0)
            )

            df_final_ref["IVA"] = df_final_ref["IvaParte"]

            df_final_ref["Total Correccion"] = (
                df_final_ref["Precio Sin IVA"] + df_final_ref["IVA"]
            )

            # =============================
            # USD CALC (MODIFIED)
            # =============================
            df_final_ref["PU USD"] = df_final_ref["PU"] / df_final_ref["TC"].astype(object)
            df_final_ref["Total USD"] = df_final_ref["PrecioParte"] / df_final_ref["TC"].astype(object)

            # =============================
            # RENAME (STRICT SAC BASE)
            # =============================
            df_final_ref.rename(columns={
                "NombreProveedor": "Nombre Proveedor",
                "TipoCompra": "Tipo De Parte",
                "Tipo Unidad": "Tipo De Unidad",
                "Tasaiva": "Tasa IVA",
                "Descripcion": "Descripcion",
                "Razon Servicio": "Razon Reparacion"
            }, inplace=True)

            # =============================
            # SELECT FINAL COLUMNS (LOCK)
            # =============================
            final_cols_ref = [
                "Año", "Mes", "Fecha Analisis",
                "Folio", "Contrarecibo", "Fecha Compra",
                "Nombre Proveedor", "Factura", "Unidad",
                "Flotilla", "Modelo", "Tipo De Unidad", "Sucursal",
                "Parte", "Tipo De Parte", "Cantidad", "PU",
                "PrecioParte", "Precio Sin IVA", "Tasa IVA", "IVA",
                "TC", "PU USD", "Total USD", "Total Correccion",
                "Moneda", "Usuario", "Reporte",
                "Descripcion", "Razon Reparacion"
            ]

            for col in final_cols_ref:
                if col not in df_final_ref.columns:
                    df_final_ref[col] = None

            df_final_ref = df_final_ref.reindex(columns=final_cols_ref)

            # =============================
            # VEHICLE UNITS ENRICHMENT
            # =============================
            if "df_units_filtered" in locals() and not df_units_filtered.empty:

                units_lookup = df_units_filtered[[
                    "unidad", "marca", "modelo", "tipo_unidad", "sucursal"
                ]].copy()

                units_lookup["unidad"] = units_lookup["unidad"].astype(str).str.strip()
                df_final_ref["Unidad"] = df_final_ref["Unidad"].astype(str).str.strip()

                units_lookup = units_lookup.drop_duplicates(subset=["unidad"])

                df_final_ref = df_final_ref.merge(
                    units_lookup,
                    left_on="Unidad",
                    right_on="unidad",
                    how="left"
                )

                df_final_ref["Flotilla"] = df_final_ref["marca"]

                if "modelo_y" in df_final_ref.columns:
                    df_final_ref["Modelo"] = df_final_ref["modelo_y"]
                else:
                    df_final_ref["Modelo"] = df_final_ref["modelo"]

                df_final_ref["Tipo De Unidad"] = df_final_ref["tipo_unidad"]
                df_final_ref["Sucursal"] = df_final_ref["sucursal"]

                df_final_ref = df_final_ref.drop(
                    columns=[c for c in ["unidad", "marca", "modelo", "modelo_y", "tipo_unidad", "sucursal"] if c in df_final_ref.columns]
                )

            # =============================
            # FORMAT
            # =============================
            df_final_ref["Mes"] = df_final_ref["Mes"].map({
                1: "January", 2: "February", 3: "March", 4: "April",
                5: "May", 6: "June", 7: "July", 8: "August",
                9: "September", 10: "October", 11: "November", 12: "December"
            })

            df_final_ref["Fecha Compra"] = pd.to_datetime(df_final_ref["Fecha Compra"], errors="coerce").dt.strftime("%d/%m/%y")
            df_final_ref["Fecha Analisis"] = pd.to_datetime(df_final_ref["Fecha Analisis"], errors="coerce").dt.strftime("%d/%m/%y")

            safe_cols = ["PU USD", "Total USD", "Total Correccion"]

            df_final_ref = df_final_ref.fillna("")
            # =============================
            # DISPLAY
            # =============================
            st.divider()
            st.subheader(f"🔧 DATA {empresa} REFACCIONES")
            df_final_ref["TC"] = df_final_ref["TC"].astype(str)
            edited_ref = st.data_editor(
                df_final_ref,
                use_container_width=True,
                num_rows="dynamic",
                key=f"edit_ref_{empresa}",
                column_config={
                    "PU": st.column_config.NumberColumn(format="$ %.2f"),
                    "PrecioParte": st.column_config.NumberColumn(format="$ %.2f"),
                    "Precio Sin IVA": st.column_config.NumberColumn(format="$ %.2f"),
                    "TC": st.column_config.TextColumn(),
                    "PU USD": st.column_config.NumberColumn(format="$ %.2f"),
                    "Total USD": st.column_config.NumberColumn(format="$ %.2f"),
                    "Total Correccion": st.column_config.NumberColumn(format="$ %.2f"),
                }
            )

            df_final_ref = edited_ref

            st.download_button(
                label="⬇️ Descargar Refacciones Final",
                data=to_excel_bytes({"Refacciones": df_final_ref}),
                file_name=f"Refacciones_Final_{empresa}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

            if st.button("📥 Cargar Datos - Ordenes", use_container_width=True):
                st.success("Datos Cargados")

# =================================
# BUILD OSTES (FROM SCRATCH - YOUR LOGIC)
# =================================
if file_ostes and file_mantenimientos and file_ordenes:

    valid_ostes = validate_filename(file_ostes, ["ostes"])
    valid_mant = validate_filename(file_mantenimientos, ["mantenimientos"])

    if valid_ostes and valid_mant:

        df_ostes = read_file(file_ostes)
        df_mant = read_file(file_mantenimientos)
        df_ordenes = read_file(file_ordenes)

        if df_ostes is not None and df_mant is not None and df_ordenes is not None:

            # =============================
            # CLEAN
            # =============================
            df_ostes.columns = df_ostes.columns.str.strip()
            df_mant.columns = df_mant.columns.str.strip()
            df_ordenes.columns = df_ordenes.columns.str.strip()

            # =============================
            # NORMALIZE KEYS
            # =============================
            df_ostes["Reporte"] = pd.to_numeric(df_ostes["# Reporte"], errors="coerce").astype("Int64").astype(str)
            df_mant["Reporte"] = pd.to_numeric(df_mant["# Reporte"], errors="coerce").astype("Int64").astype(str)
            df_ordenes["Reporte"] = pd.to_numeric(df_ordenes["Reporte"], errors="coerce").astype("Int64").astype(str)

            # =============================
            # BASE DATA (NO MERGE FIRST)
            # =============================
            df_final_ostes = df_ostes.copy()

            # =============================
            # DATE (FROM FECHA FACTURA)
            # =============================
            df_final_ostes["Fecha Factura"] = pd.to_datetime(df_final_ostes["Fecha Factura"], errors="coerce")

            df_final_ostes["Año"] = df_final_ostes["Fecha Factura"].dt.year
            df_final_ostes["Mes"] = df_final_ostes["Fecha Factura"].dt.month

            # =============================
            # DIRECT FIELDS (OSTES ONLY)
            # =============================
            df_final_ostes["OSTE"] = df_final_ostes["# Oste"]
            df_final_ostes["Factura"] = df_final_ostes["No. Factura"]
            df_final_ostes["Status CT"] = df_final_ostes["Status"]

            # =============================
            # ACREEDOR (KEEP EXISTING LOGIC)
            # =============================
            df_ordenes["Proveedor_key"] = pd.to_numeric(df_ordenes["Proveedor"], errors="coerce").astype("Int64")
            df_final_ostes["Proveedor_key"] = pd.to_numeric(df_final_ostes["Proveedor"], errors="coerce").astype("Int64")

            proveedor_lookup = (
                df_ordenes[["Proveedor_key", "NombreProveedor"]]
                .dropna()
                .drop_duplicates(subset=["Proveedor_key"])
                .rename(columns={"NombreProveedor": "Acreedor_lookup"})
            )

            df_final_ostes = df_final_ostes.merge(
                proveedor_lookup,
                on="Proveedor_key",
                how="left"
            )

            df_final_ostes["Acreedor"] = df_final_ostes["Acreedor_lookup"]

            # =============================
            # DESCRIPCION + RAZON (FROM MANT)
            # =============================
            mant_lookup = df_mant[[
                "Reporte", "Descripcion", "Razon Servicio"
            ]].drop_duplicates(subset=["Reporte"])

            df_final_ostes = df_final_ostes.merge(
                mant_lookup,
                on="Reporte",
                how="left"
            )

            df_final_ostes.rename(columns={
                "Razon Servicio": "Razon de servicio"
            }, inplace=True)

            # =============================
            # IVA (FROM SAC USING REPORTE)
            # =============================
            iva_lookup = (
                df_ordenes[["Reporte", "IvaParte"]]
                .dropna()
                .drop_duplicates(subset=["Reporte"])
                .set_index("Reporte")["IvaParte"]
            )

            df_final_ostes["IVA"] = df_final_ostes["Reporte"].map(iva_lookup)

            # =============================
            # MONEDA (FROM SAC USING REPORTE)
            # =============================
            moneda_lookup = (
                df_ordenes[["Reporte", "Moneda"]]
                .dropna()
                .drop_duplicates(subset=["Reporte"])
                .set_index("Reporte")["Moneda"]
            )

            df_final_ostes["Moneda"] = df_final_ostes["Reporte"].map(moneda_lookup)

            # =============================
            # TIME METRICS
            # =============================
            fecha_cierre = pd.to_datetime(df_final_ostes["Fecha Cierre"], errors="coerce", dayfirst=True)
            fecha_oste = pd.to_datetime(df_final_ostes["Fecha Oste"], errors="coerce", dayfirst=True)
            fecha_factura = pd.to_datetime(df_final_ostes["Fecha Factura"], errors="coerce", dayfirst=True)

            df_final_ostes["Dias para cerrar orden"] = (fecha_cierre - fecha_oste).dt.days
            df_final_ostes["Dias Reparacion"] = (fecha_cierre - fecha_factura).dt.days

            df_final_ostes["Dias para cerrar orden"] = df_final_ostes["Dias para cerrar orden"].clip(lower=0)
            df_final_ostes["Dias Reparacion"] = df_final_ostes["Dias Reparacion"].clip(lower=0)

            # =============================
            # FINANCIALS (YOUR RULES)
            # =============================
            df_final_ostes["Subtotal"] = df_final_ostes["Total"]

            def calc_total(row):
                moneda = str(row.get("Moneda", "")).upper()

                if moneda == "USD":
                    return row["Subtotal"] * row["TC"]
                else:
                    return row["Subtotal"]

            # =============================
            # TC (UNCHANGED)
            # =============================
            df_final_ostes = df_final_ostes.dropna(subset=["Año", "Mes"])
            df_final_ostes["Año"] = df_final_ostes["Año"].astype(int)
            df_final_ostes["Mes"] = df_final_ostes["Mes"].astype(int)

            if df_tc is not None and not df_tc.empty:
                df_final_ostes = df_final_ostes.merge(
                    df_tc,
                    left_on=["Año", "Mes"],
                    right_on=["year", "month"],
                    how="left"
                )
                df_final_ostes["TC"] = df_final_ostes["tc"]
                df_final_ostes.drop(columns=["year", "month", "tc"], inplace=True, errors="ignore")
            else:
                df_final_ostes["TC"] = 1

            df_final_ostes["Total oste"] = df_final_ostes.apply(calc_total, axis=1)
            df_final_ostes["Total Correccion"] = df_final_ostes["Total oste"]

            # =============================
            # FINAL COLUMNS
            # =============================
            final_cols_ostes = [
                "Año", "Mes", "OSTE", "Fecha Analisis", "Reporte",
                "Acreedor", "Fecha Factura", "Fecha Oste", "Fecha Cierre",
                "Dias para cerrar orden", "Dias Reparacion",
                "Empresa", "Sucursal", "Observaciones", "Status CT",
                "Factura", "Subtotal", "IVA", "Total oste",
                "Moneda", "TC", "Total Correccion",
                "Unidad", "Flotilla", "Modelo",
                "Descripcion", "Tipo De Unidad", "Razon de servicio"
            ]

            for col in final_cols_ostes:
                if col not in df_final_ostes.columns:
                    df_final_ostes[col] = None

            df_final_ostes = df_final_ostes[final_cols_ostes]

            # =============================
            # VEHICLE ENRICHMENT
            # =============================
            if "df_units_filtered" in locals() and not df_units_filtered.empty:

                units_lookup = df_units_filtered[[
                    "unidad", "marca", "modelo", "tipo_unidad", "sucursal"
                ]].copy()

                units_lookup["unidad"] = units_lookup["unidad"].astype(str).str.strip()
                df_final_ostes["Unidad"] = df_final_ostes["Unidad"].astype(str).str.strip()

                units_lookup = units_lookup.drop_duplicates(subset=["unidad"])

                df_final_ostes = df_final_ostes.merge(
                    units_lookup,
                    left_on="Unidad",
                    right_on="unidad",
                    how="left"
                )

                df_final_ostes["Flotilla"] = df_final_ostes["marca"]
                df_final_ostes["Modelo"] = df_final_ostes["modelo"]
                df_final_ostes["Tipo De Unidad"] = df_final_ostes["tipo_unidad"]
                df_final_ostes["Sucursal"] = df_final_ostes["sucursal"]

                df_final_ostes = df_final_ostes.drop(
                    columns=[c for c in ["unidad", "marca", "modelo", "tipo_unidad", "sucursal", "Acreedor_lookup"] if c in df_final_ostes.columns]
                )

            # =============================
            # FORMAT
            # =============================
            df_final_ostes["Mes"] = df_final_ostes["Mes"].map({
                1: "January", 2: "February", 3: "March", 4: "April",
                5: "May", 6: "June", 7: "July", 8: "August",
                9: "September", 10: "October", 11: "November", 12: "December"
            })

            date_cols = ["Fecha Analisis", "Fecha Factura", "Fecha Oste", "Fecha Cierre"]
            for col in date_cols:
                if col in df_final_ostes.columns:
                    df_final_ostes[col] = pd.to_datetime(df_final_ostes[col], errors="coerce").dt.strftime("%d/%m/%y")

            for col in ["Subtotal", "IVA", "Total oste", "Total Correccion"]:
                df_final_ostes[col] = pd.to_numeric(df_final_ostes[col], errors="coerce")

            # =============================
            # DISPLAY
            # =============================
            st.divider()
            st.subheader(f"💰 OSTES {empresa}")

            edited_ostes = st.data_editor(
                df_final_ostes,
                use_container_width=True,
                num_rows="dynamic",
                key=f"edit_ostes_{empresa}",
                column_config={
                    "Subtotal": st.column_config.NumberColumn(format="$ %.2f"),
                    "IVA": st.column_config.NumberColumn(format="$ %.2f"),
                    "Total oste": st.column_config.NumberColumn(format="$ %.2f"),
                    "TC": st.column_config.NumberColumn(format="%.5f", disabled=True),
                    "Total Correccion": st.column_config.NumberColumn(format="$ %.2f"),
                }
            )

            # overwrite with edited version
            df_final_ostes = edited_ostes

            st.download_button(
                label="⬇️ Descargar OSTES Final",
                data=to_excel_bytes({"OSTES": df_final_ostes}),
                file_name=f"OSTES_Final_{empresa}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

            if st.button("📥 Cargar Datos - OSTES", use_container_width=True):
                st.success("Datos Cargados")

# =================================
# BUILD MANO DE OBRA REPORT (FIXED, NOT STRIPPED)
# =================================
if file_ordenes and file_ostes and file_mantenimientos:

    valid_ordenes = validate_filename(file_ordenes, ["buscar", "ordenes", "sac"])
    valid_ostes = validate_filename(file_ostes, ["ostes"])
    valid_mant = validate_filename(file_mantenimientos, ["mantenimientos"])

    if valid_ordenes and valid_ostes and valid_mant:

        df_ordenes = read_file(file_ordenes)
        df_ostes = read_file(file_ostes)
        df_mant = read_file(file_mantenimientos)

        if df_ordenes is not None and df_ostes is not None and df_mant is not None:

            # =============================
            # NORMALIZE KEYS
            # =============================
            df_mant["Reporte"] = pd.to_numeric(df_mant["# Reporte"], errors="coerce").astype("Int64").astype(str)
            df_ostes["Reporte"] = pd.to_numeric(df_ostes["# Reporte"], errors="coerce").astype("Int64").astype(str)
            df_ordenes["Reporte"] = pd.to_numeric(df_ordenes["Reporte"], errors="coerce").astype("Int64").astype(str)

            # =============================
            # LOOKUPS (UNCHANGED)
            # =============================
            df_ostes_lookup = df_ostes[[
                "Reporte",
                "Empresa",
                "No. Factura",
                "Status",
                "Total Pesos"
            ]].copy()

            df_ostes_lookup.rename(columns={
                "Empresa": "Nombre Cliente",
                "No. Factura": "Factura",
                "Status": "Estatus",
                "Total Pesos": "Total"
            }, inplace=True)

            df_ostes_lookup = df_ostes_lookup.drop_duplicates(subset=["Reporte"])

            # =============================
            # UNIDAD LOOKUP (UNCHANGED)
            # =============================
            ordenes_unidad = df_ordenes[["Reporte", "Unidad"]].copy()
            ostes_unidad = df_ostes[["Reporte", "Unidad"]].copy()

            unidad_lookup = pd.concat([ordenes_unidad, ostes_unidad])
            unidad_lookup["Unidad"] = unidad_lookup["Unidad"].astype(str).str.strip()
            unidad_lookup = unidad_lookup.drop_duplicates(subset=["Reporte"], keep="first")

            # =============================
            # MERGE (UNCHANGED)
            # =============================
            df_final = df_mant.merge(df_ostes_lookup, on="Reporte", how="left")

            df_final = df_final.merge(
                unidad_lookup,
                on="Reporte",
                how="left",
                suffixes=("", "_lookup")
            )

            if "Unidad_lookup" in df_final.columns:
                df_final["Unidad"] = df_final["Unidad_lookup"].combine_first(df_final["Unidad"])

            df_final["Unidad"] = df_final["Unidad"].replace(["nan", "None"], None)

            # =============================
            # RAZON REPARACION
            # =============================
            df_final["Razon Reparacion"] = df_final.get("Razon Servicio")

            # =============================
            # 🔥 DATE FIX (YOUR RULE)
            # =============================
            df_final["Fecha Registro"] = pd.to_datetime(df_final["Fecha Registro"], errors="coerce")

            df_final["Año"] = df_final["Fecha Registro"].dt.year
            df_final["Mes"] = df_final["Fecha Registro"].dt.month

            # KEEP THIS AS YOU HAD IT
            df_final["Fecha Analisis"] = pd.to_datetime(
                df_final["Fecha Liberada"],
                errors="coerce",
                dayfirst=True
            )

            # =============================
            # FINANCIALS (UNCHANGED)
            # =============================
            df_final["Sub Total"] = df_final["Total"] / 1.16
            df_final["IVA"] = df_final["Total"] - df_final["Sub Total"]

            # =============================
            # TC (UNCHANGED)
            # =============================
            df_final = df_final.dropna(subset=["Año", "Mes"])

            df_final["Año"] = df_final["Año"].astype(int)
            df_final["Mes"] = df_final["Mes"].astype(int)

            if df_tc is not None and not df_tc.empty:
                df_final = df_final.merge(
                    df_tc,
                    left_on=["Año", "Mes"],
                    right_on=["year", "month"],
                    how="left"
                )
                df_final["TC"] = df_final["tc"]
                df_final.drop(columns=["year", "month", "tc"], inplace=True, errors="ignore")
            else:
                df_final["TC"] = 1

            df_final["Total USD"] = df_final["Total"] / df_final["TC"]
            df_final["Total Correccion"] = df_final["Total"]
            df_final["Diferencia"] = 0

            # =============================
            # 🔥 VEHICLE ENRICHMENT (FIXED)
            # =============================
            if "df_units_filtered" in locals() and not df_units_filtered.empty:

                units_lookup = df_units_filtered[[
                    "unidad", "marca", "modelo", "tipo_unidad", "sucursal"
                ]].copy()

                units_lookup["unidad"] = units_lookup["unidad"].astype(str).str.strip()
                df_final["Unidad"] = df_final["Unidad"].astype(str).str.strip()

                units_lookup = units_lookup.drop_duplicates(subset=["unidad"])

                df_final = df_final.merge(
                    units_lookup,
                    left_on="Unidad",
                    right_on="unidad",
                    how="left"
                )

                df_final["Flotilla"] = df_final["marca"]
                df_final["Modelo"] = df_final["modelo"]
                df_final["Tipo Unidad"] = df_final["tipo_unidad"]
                df_final["Sucursal"] = df_final["sucursal"]

                df_final = df_final.drop(
                    columns=[c for c in ["unidad", "marca", "modelo", "tipo_unidad", "sucursal"] if c in df_final.columns]
                )

            # =============================
            # FORMATTING (UNCHANGED)
            # =============================
            df_final["Reporte"] = df_final["Reporte"].astype(str).str.replace(".0", "", regex=False)

            date_cols = [
                "Fecha Analisis",
                "Fecha Registro",
                "Fecha Aceptado",
                "Fecha Iniciada",
                "Fecha Liberada",
                "Fecha Terminada"
            ]

            for col in date_cols:
                if col in df_final.columns:
                    df_final[col] = pd.to_datetime(df_final[col], errors="coerce").dt.strftime("%d/%m/%y")

            currency_cols = [
                "PU", "PrecioParte", "Precio Sin IVA",
                "PU USD", "Total USD", "Total Correccion"
            ]

            for col in currency_cols:
                if col in df_final.columns:
                    df_final[col] = pd.to_numeric(df_final[col], errors="coerce")

            # =============================
            # FINAL COLUMNS (UNCHANGED)
            # =============================
            final_columns = [
                "Año", "Mes", "Unidad", "Fecha Analisis",
                "Flotilla", "Modelo", "Tipo Unidad", "Sucursal",
                "Reporte", "Fecha Registro", "Fecha Aceptado",
                "Fecha Iniciada", "Fecha Liberada", "Fecha Terminada",
                "Nombre Cliente", "Factura", "Estatus",
                "Sub Total", "IVA", "Total", "Total Correccion",
                "TC", "Total USD", "Descripcion",
                "Razon Reparacion", "Diferencia", "Comentarios"
            ]

            for col in final_columns:
                if col not in df_final.columns:
                    df_final[col] = None

            df_final = df_final[final_columns]

            df_final["Mes"] = df_final["Mes"].map({
                1: "January", 2: "February", 3: "March", 4: "April",
                5: "May", 6: "June", 7: "July", 8: "August",
                9: "September", 10: "October", 11: "November", 12: "December"
            })

            # =============================
            # DISPLAY
            # =============================
            st.divider()
            st.subheader(f"🚛 Reporte Mano de Obra {empresa}")

            edited_mo = st.data_editor(
                df_final,
                use_container_width=True,
                num_rows="dynamic",
                key=f"edit_mo_{empresa}",
                column_config={
                    "Sub Total": st.column_config.NumberColumn(format="$ %.2f"),
                    "IVA": st.column_config.NumberColumn(format="$ %.2f"),
                    "Total": st.column_config.NumberColumn(format="$ %.2f"),
                    "Total Correccion": st.column_config.NumberColumn(format="$ %.2f"),
                    "TC": st.column_config.NumberColumn(format="%.5f", disabled=True),
                    "Total USD": st.column_config.NumberColumn(format="$ %.2f"),
                }
            )

            # overwrite dataframe with edited version
            df_final = edited_mo

            st.download_button(
                label="⬇️ Descargar Mano de Obra Final",
                data=to_excel_bytes({"Mano_de_Obra": df_final}),
                file_name=f"Mano_de_Obra_Final_{empresa}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

            if st.button("📥 Cargar Datos - Mantenimientos", use_container_width=True):
                st.success("Datos Cargados")