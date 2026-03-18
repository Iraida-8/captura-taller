import streamlit as st
import pandas as pd
from datetime import date, datetime
from auth import require_login, require_access
import gspread
from google.oauth2.service_account import Credentials
import os
from supabase import create_client
import unicodedata

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

def get_supabase_client():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"]
    )

# =================================
# Top navigation
# =================================
if st.button("⬅ Volver al Dashboard"):
    st.switch_page("pages/dashboard.py")

st.divider()

st.title("📊 Preparación de Reportes")

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

if empresa == "SELECCIONA EMPRESA":
    st.warning("Debes seleccionar una empresa para continuar.")
    st.stop()

st.success(f"Empresa seleccionada: {empresa}")

# =================================
# Dynamic uploader keys (CRITICAL FIX)
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
            df["date"] = pd.to_datetime(df["date"], errors="coerce")

            # ✅ ADD THIS
            df["year"] = df["year"].astype(int)
            df["month"] = df["month"].astype(int)
            df["tc"] = df["tc"].astype(float)

        return df

    except Exception as e:
        st.error(f"Error cargando TC: {e}")
        return None

# =================================
# LOAD TC DATA
# =================================
df_tc = load_tc()

st.write("TC DATA:", df_tc.head() if df_tc is not None else "NO DATA")

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
    st.subheader(f"2. Reporte Ostes ({empresa})")
    file_ostes = st.file_uploader(
        "Sube Reporte Ostes",
        type=["csv", "xlsx"],
        key=key_ostes
    )

with col3:
    st.subheader(f"3. Reporte de Mantenimientos ({empresa})")
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

# OSTES
if file_ostes:
    if not validate_filename(file_ostes, ["ostes"]):
        st.error("El archivo debe contener: ostes en el nombre.")
    else:
        df = read_file(file_ostes)
        if df is not None:
            with st.expander(f"📄 Reporte Ostes ({empresa})"):
                st.dataframe(df, use_container_width=True)

# MANTENIMIENTOS
if file_mantenimientos:
    if not validate_filename(file_mantenimientos, ["mantenimientos"]):
        st.error("El archivo debe contener: mantenimientos en el nombre.")
    else:
        df = read_file(file_mantenimientos)
        if df is not None:
            with st.expander(f"📄 Reporte de Mantenimientos ({empresa})"):
                st.dataframe(df, use_container_width=True)

# =================================
# BUILD DATA LINCOLN REFACCIONES
# =================================
if file_ordenes and file_mantenimientos:

    valid_ordenes = validate_filename(file_ordenes, ["buscar", "ordenes", "sac"])
    valid_mant = validate_filename(file_mantenimientos, ["mantenimientos"])

    if valid_ordenes and valid_mant:

        df_ordenes = read_file(file_ordenes)
        df_mant = read_file(file_mantenimientos)

        if df_ordenes is not None and df_mant is not None:

            # =============================
            # NORMALIZE KEYS
            # =============================
            df_ordenes["Reporte"] = df_ordenes["Reporte"].astype(str).str.strip()
            df_mant["Reporte"] = df_mant["# Reporte"].astype(str).str.strip()

            # =============================
            # DATE HANDLING
            # =============================
            df_ordenes["Fecha Compra"] = pd.to_datetime(df_ordenes["Fecha"], errors="coerce")

            df_ordenes["Año"] = df_ordenes["Fecha Compra"].dt.year
            df_ordenes["Mes"] = df_ordenes["Fecha Compra"].dt.month

            # =============================
            # JOIN MANTENIMIENTOS
            # =============================
            df_final_ref = df_ordenes.merge(
                df_mant[[
                    "Reporte",
                    "Tipo Unidad",
                    "Descripcion",
                    "Razon Servicio",
                    "Fecha Liberada"
                ]],
                on="Reporte",
                how="left"
            )

            # =============================
            # DERIVED FIELDS
            # =============================
            df_final_ref["Fecha Analisis"] = pd.to_datetime(df_final_ref["Fecha Liberada"], errors="coerce")

            df_final_ref["Precio Sin IVA"] = df_final_ref["PrecioParte"] / (1 + df_final_ref["Tasaiva"].fillna(0))

            # =============================
            # TC MERGE
            # =============================
            df_final_ref["Año"] = df_final_ref["Año"].astype(int)
            df_final_ref["Mes"] = df_final_ref["Mes"].astype(int)

            df_final_ref = df_final_ref.merge(
                df_tc,
                left_on=["Año", "Mes"],
                right_on=["year", "month"],
                how="left"
            )

            df_final_ref["TC"] = df_final_ref["tc"].fillna(1)
            df_final_ref.drop(columns=["year", "month", "tc"], inplace=True, errors="ignore")

            # USD CALC
            df_final_ref["PU USD"] = df_final_ref["PU"] / df_final_ref["TC"]
            df_final_ref["Total USD"] = df_final_ref["PrecioParte"] / df_final_ref["TC"]

            df_final_ref["Total Correccion"] = df_final_ref["PrecioParte"]

            # =============================
            # MISSING FIELDS
            # =============================
            df_final_ref["Flotilla"] = "N/A"
            df_final_ref["Modelo"] = "N/A"
            df_final_ref["Sucursal"] = "N/A"

            # =============================
            # RENAME
            # =============================
            df_final_ref.rename(columns={
                "NombreProveedor": "Nombre Proveedor",
                "TipoCompra": "Tipo De Parte",
                "Tipo Unidad": "Tipo De Unidad",
                "Tasaiva": "Tasa IVA",
                "IvaParte": "IVA",
                "Descripcion": "Descripcion",
                "Razon Servicio": "Razon Reparacion"
            }, inplace=True)

            # =============================
            # SELECT FINAL COLUMNS
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

            df_final_ref = df_final_ref[final_cols_ref]

            # =============================
            # DISPLAY
            # =============================
            st.divider()
            st.subheader("🔧 DATA LINCOLN REFACCIONES")

            st.dataframe(df_final_ref, use_container_width=True)

# =================================
# BUILD OSTES LINCOLN
# =================================
if file_ostes and file_mantenimientos:

    valid_ostes = validate_filename(file_ostes, ["ostes"])
    valid_mant = validate_filename(file_mantenimientos, ["mantenimientos"])

    if valid_ostes and valid_mant:

        df_ostes = read_file(file_ostes)
        df_mant = read_file(file_mantenimientos)

        if df_ostes is not None and df_mant is not None:

            # =============================
            # NORMALIZE KEYS
            # =============================
            df_ostes.columns = df_ostes.columns.str.strip()
            df_mant.columns = df_mant.columns.str.strip()

            df_ostes["Reporte"] = df_ostes["# Reporte"].astype(str).str.strip()
            df_mant["Reporte"] = df_mant["# Reporte"].astype(str).str.strip()

            # =============================
            # DATE HANDLING
            # =============================
            df_ostes["Fecha Analisis"] = pd.to_datetime(df_ostes["Fecha Cierre"], errors="coerce")

            df_ostes["Año"] = df_ostes["Fecha Analisis"].dt.year
            df_ostes["Mes"] = df_ostes["Fecha Analisis"].dt.month

            # =============================
            # JOIN MANTENIMIENTOS
            # =============================
            df_final_ostes = df_ostes.merge(
                df_mant[[
                    "Reporte",
                    "Descripcion",
                    "Razon Servicio"
                ]],
                on="Reporte",
                how="left"
            )

            # =============================
            # TIME METRICS (CORRECTED)
            # =============================
            fecha_cierre = pd.to_datetime(df_final_ostes.get("Fecha Cierre"), errors="coerce")
            fecha_oste = pd.to_datetime(df_final_ostes.get("Fecha Oste"), errors="coerce")
            fecha_factura = pd.to_datetime(df_final_ostes.get("Fecha Factura"), errors="coerce")

            # Dias para cerrar orden → Cierre - Oste
            dias_cierre = (fecha_cierre - fecha_oste).dt.days
            df_final_ostes["Dias para cerrar orden"] = dias_cierre
            df_final_ostes.loc[df_final_ostes["Dias para cerrar orden"] < 0, "Dias para cerrar orden"] = 0

            # Dias Reparacion → Factura - Oste (NEW LOGIC)
            dias_rep = (fecha_factura - fecha_oste).dt.days
            df_final_ostes["Dias Reparacion"] = dias_rep
            df_final_ostes.loc[df_final_ostes["Dias Reparacion"] < 0, "Dias Reparacion"] = 0

            # =============================
            # FINANCIAL DERIVATIONS
            # =============================
            df_final_ostes["Total oste"] = df_final_ostes["Total Pesos"]

            df_final_ostes["Subtotal"] = df_final_ostes["Total oste"] / 1.16
            df_final_ostes["IVA"] = df_final_ostes["Total oste"] - df_final_ostes["Subtotal"]

            # =============================
            # TC MERGE
            # =============================
            df_final_ostes["Año"] = df_final_ostes["Año"].astype(int)
            df_final_ostes["Mes"] = df_final_ostes["Mes"].astype(int)

            df_final_ostes = df_final_ostes.merge(
                df_tc,
                left_on=["Año", "Mes"],
                right_on=["year", "month"],
                how="left"
            )

            df_final_ostes["TC"] = df_final_ostes["tc"].fillna(1)

            df_final_ostes.drop(columns=["year", "month", "tc"], inplace=True, errors="ignore")

            df_final_ostes["Total Correccion"] = df_final_ostes["Total oste"]

            # =============================
            # PLACEHOLDERS
            # =============================
            df_final_ostes["Flotilla"] = "N/A"
            df_final_ostes["Modelo"] = "N/A"
            df_final_ostes["Sucursal"] = "N/A"
            df_final_ostes["Status CT"] = df_final_ostes["Status"]

            # =============================
            # RENAME
            # =============================
            df_final_ostes.rename(columns={
                "# Oste": "OSTE",
                "Proveedor": "Acreedor",
                "No. Factura": "Factura",
                "Observaciones": "Observaciones",
                "Tipo Unidad": "Tipo De Unidad",
                "Razon Servicio": "Razon de servicio"
            }, inplace=True)

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

            # SAFETY
            for col in final_cols_ostes:
                if col not in df_final_ostes.columns:
                    df_final_ostes[col] = None

            df_final_ostes = df_final_ostes[final_cols_ostes]

            # =============================
            # DISPLAY
            # =============================
            st.divider()
            st.subheader("💰 OSTES LINCOLN")

            st.dataframe(df_final_ostes, use_container_width=True)

# =================================
# BUILD LINCOLN MANO DE OBRA REPORT
# =================================
if file_ordenes and file_ostes and file_mantenimientos:

    # Validate all first
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
            df_mant["Reporte"] = df_mant["# Reporte"].astype(str).str.strip()
            df_ostes["Reporte"] = df_ostes["# Reporte"].astype(str).str.strip()
            df_ordenes["Reporte"] = df_ordenes["Reporte"].astype(str).str.strip()

            # =============================
            # AGGREGATE OSTES
            # =============================
            df_ostes_agg = (
                df_ostes
                .groupby("Reporte", as_index=False)
                .agg({
                    "Total Pesos": "sum",
                    "No. Factura": "first"
                })
            )

            df_ostes_agg.rename(columns={
                "Total Pesos": "Total",
                "No. Factura": "Factura"
            }, inplace=True)

            # =============================
            # MERGE BASE (MANTENIMIENTOS)
            # =============================
            df_final = df_mant.merge(df_ostes_agg, on="Reporte", how="left")

            # =============================
            # DATE HANDLING
            # =============================
            df_final["Fecha Analisis"] = pd.to_datetime(df_final["Fecha Liberada"], errors="coerce")

            df_final["Año"] = df_final["Fecha Analisis"].dt.year
            df_final["Mes"] = df_final["Fecha Analisis"].dt.month

            # =============================
            # FINANCIAL DERIVATIONS
            # =============================
            df_final["Sub Total"] = df_final["Total"] / 1.16
            df_final["IVA"] = df_final["Total"] - df_final["Sub Total"]

            # =============================
            # TC MERGE
            # =============================
            df_final["Año"] = df_final["Año"].astype(int)
            df_final["Mes"] = df_final["Mes"].astype(int)

            df_final = df_final.merge(
                df_tc,
                left_on=["Año", "Mes"],
                right_on=["year", "month"],
                how="left"
            )

            df_final["TC"] = df_final["tc"].fillna(1)

            df_final.drop(columns=["year", "month", "tc"], inplace=True, errors="ignore")

            df_final["Total USD"] = df_final["Total"] / df_final["TC"]

            df_final["Total Correccion"] = df_final["Total"]  # Placeholder
            df_final["Diferencia"] = 0  # Placeholder

            # =============================
            # MISSING FIELDS (PLACEHOLDERS)
            # =============================
            df_final["Flotilla"] = "N/A"
            df_final["Modelo"] = "N/A"
            df_final["Sucursal"] = "N/A"
            df_final["Nombre Cliente"] = "N/A"
            df_final["Comentarios"] = "N/A"

            # =============================
            # RENAME FIELDS
            # =============================
            df_final.rename(columns={
                "Tipo Unidad": "Tipo Unidad",
                "Descripcion": "Descripcion",
                "Razon Servicio": "Razon Reparacion",
                "Status": "Estatus"
            }, inplace=True)

            # =============================
            # SELECT FINAL COLUMNS
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

            df_final = df_final[final_columns]

            # =============================
            # DISPLAY (NOT COLLAPSED)
            # =============================
            st.divider()
            st.subheader("🚛 Reporte Mano de Obra Lincoln")

            st.dataframe(df_final, use_container_width=True)