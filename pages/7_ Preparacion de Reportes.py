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
# LOADERS - CONSULTA IGLOO
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

# =================================
# MODE SELECTOR
# =================================
st.subheader("¿Qué quieres hacer?")

col_a, col_b = st.columns(2)

st.session_state.modo_reportes = None

with col_a:
    if st.button("📄 Consultar Reportes", use_container_width=True):
        st.session_state.modo_reportes = "consultar"

with col_b:
    if st.button("📤 Cargar Reportes", use_container_width=True):
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
        temp_df_mes = load_refacciones_igloo()

        if not temp_df_mes.empty and "mes" in temp_df_mes.columns:
            meses = sorted(temp_df_mes["mes"].dropna().unique())
        else:
            meses = []

        mes_options = ["Todos"] + list(meses)

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
    # LOAD DATA (IGLOO ONLY)
    # =================================
    if empresa_consulta == "IGLOO":

        # LOAD
        df_ref = load_refacciones_igloo()
        df_ost = load_ostes_igloo()
        df_mo  = load_mano_obra_igloo()

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
        # 🔥 RENAME (ALWAYS RUNS)
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
        # DISPLAY
        # -------------------------------
        st.subheader("🔧 Refacciones IGLOO")
        st.dataframe(df_ref, use_container_width=True)

        st.divider()

        st.subheader("💰 OSTES IGLOO")
        st.dataframe(df_ost, use_container_width=True)

        st.divider()

        st.subheader("🚛 Mano de Obra IGLOO")
        st.dataframe(df_mo, use_container_width=True)

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

if empresa == "SELECCIONA EMPRESA":
    st.warning("Debes seleccionar una empresa para continuar.")
    st.stop()

st.success(f"Empresa seleccionada: {empresa}")

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
            df["tc"] = df["tc"].astype(float)
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
# BUILD DATA REFACCIONES
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

            df_ordenes["Mes Nombre"] = df_ordenes["Fecha Compra"].dt.month_name()

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
            # TC SAFE MERGE
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

                df_final_ref["TC"] = df_final_ref["tc"]
                df_final_ref.drop(columns=["year", "month", "tc"], inplace=True, errors="ignore")

            else:
                df_final_ref["TC"] = 1

            # =============================
            # USD CALC
            # =============================
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

            df_final_ref["Mes"] = df_final_ref["Mes"].map({
                1: "January", 2: "February", 3: "March", 4: "April",
                5: "May", 6: "June", 7: "July", 8: "August",
                9: "September", 10: "October", 11: "November", 12: "December"
            })

            # =============================
            # FORMAT DISPLAY
            # =============================
            df_final_ref["Fecha Compra"] = df_final_ref["Fecha Compra"].dt.date

            # Ensure numeric
            currency_cols = [
                "PU", "PrecioParte", "Precio Sin IVA",
                "TC", "PU USD", "Total USD", "Total Correccion"
            ]

            for col in currency_cols:
                df_final_ref[col] = pd.to_numeric(df_final_ref[col], errors="coerce")

            # =============================
            # DISPLAY
            # =============================
            st.divider()
            st.subheader(f"🔧 DATA {empresa} REFACCIONES")

            # 🔥 ADD THIS
            df_final_ref["Fecha Analisis"] = pd.to_datetime(df_final_ref["Fecha Analisis"], errors="coerce").dt.date

            st.dataframe(
                df_final_ref,
                use_container_width=True,
                column_config={
                    "PU": st.column_config.NumberColumn(format="$ %.2f"),
                    "PrecioParte": st.column_config.NumberColumn(format="$ %.2f"),
                    "Precio Sin IVA": st.column_config.NumberColumn(format="$ %.2f"),
                    "TC": st.column_config.NumberColumn(format="$ %.4f"),
                    "PU USD": st.column_config.NumberColumn(format="$ %.2f"),
                    "Total USD": st.column_config.NumberColumn(format="$ %.2f"),
                    "Total Correccion": st.column_config.NumberColumn(format="$ %.2f"),
                }
            )

            if st.button("📥 Cargar Datos - Ordenes", use_container_width=True):
                st.success("Datos Cargados")

# =================================
# BUILD OSTES
# =================================
if file_ostes and file_mantenimientos and file_ordenes:

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
            df_ostes["Fecha Analisis"] = pd.to_datetime(
                df_ostes["Fecha Cierre"],
                errors="coerce",
                dayfirst=True
            )

            df_ostes["Año"] = df_ostes["Fecha Analisis"].dt.year
            df_ostes["Mes"] = df_ostes["Fecha Analisis"].dt.month

            df_ostes["Mes Nombre"] = df_ostes["Fecha Analisis"].dt.month_name()

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
            # MAP ACREEDOR FROM ORDENES
            # =============================
            df_ordenes = read_file(file_ordenes)

            if df_ordenes is not None:

                df_ordenes.columns = df_ordenes.columns.str.strip()

                # 🔥 FORCE SAME TYPE
                df_ordenes["Proveedor_key"] = pd.to_numeric(df_ordenes["Proveedor"], errors="coerce").astype("Int64")
                df_final_ostes["Proveedor_key"] = pd.to_numeric(df_final_ostes["Proveedor"], errors="coerce").astype("Int64")

                # Clean name
                df_ordenes["NombreProveedor"] = df_ordenes["NombreProveedor"].astype(str).str.strip()

                # Lookup
                proveedor_lookup = (
                    df_ordenes[["Proveedor_key", "NombreProveedor"]]
                    .dropna()
                    .drop_duplicates(subset=["Proveedor_key"])
                )

                # Merge
                df_final_ostes = df_final_ostes.merge(
                    proveedor_lookup,
                    on="Proveedor_key",
                    how="left"
                )

                df_final_ostes["Acreedor"] = df_final_ostes["NombreProveedor"]

            # =============================
            # TIME METRICS
            # =============================
            fecha_cierre = pd.to_datetime(df_final_ostes["Fecha Cierre"], errors="coerce", dayfirst=True)
            fecha_oste = pd.to_datetime(df_final_ostes["Fecha Oste"], errors="coerce", dayfirst=True)
            fecha_factura = pd.to_datetime(df_final_ostes["Fecha Factura"], errors="coerce", dayfirst=True)

            df_final_ostes["Dias para cerrar orden"] = (fecha_cierre - fecha_oste).dt.days
            df_final_ostes["Dias Reparacion"] = (fecha_factura - fecha_oste).dt.days

            df_final_ostes["Dias para cerrar orden"] = df_final_ostes["Dias para cerrar orden"].clip(lower=0)
            df_final_ostes["Dias Reparacion"] = df_final_ostes["Dias Reparacion"].clip(lower=0)

            # =============================
            # FINANCIAL DERIVATIONS
            # =============================
            df_final_ostes["Total oste"] = df_final_ostes["Total Pesos"]
            df_final_ostes["Subtotal"] = df_final_ostes["Total oste"] / 1.16
            df_final_ostes["IVA"] = df_final_ostes["Total oste"] - df_final_ostes["Subtotal"]

            # =============================
            # TC MERGE
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
                "No. Factura": "Factura",
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

            for col in final_cols_ostes:
                if col not in df_final_ostes.columns:
                    df_final_ostes[col] = None

            df_final_ostes = df_final_ostes[final_cols_ostes]

            df_final_ostes["Mes"] = df_final_ostes["Mes"].map({
                1: "January", 2: "February", 3: "March", 4: "April",
                5: "May", 6: "June", 7: "July", 8: "August",
                9: "September", 10: "October", 11: "November", 12: "December"
            })

            # =============================
            # FORMAT DISPLAY
            # =============================
            df_final_ostes["Reporte"] = df_final_ostes["Reporte"].astype(str).str.replace(".0", "", regex=False)

            date_cols = ["Fecha Analisis", "Fecha Factura", "Fecha Oste", "Fecha Cierre"]
            for col in date_cols:
                if col in df_final_ostes.columns:
                    df_final_ostes[col] = pd.to_datetime(df_final_ostes[col], errors="coerce").dt.date

            currency_cols = [
                "Subtotal", "IVA", "Total oste",
                "TC", "Total Correccion"
            ]

            for col in currency_cols:
                if col in df_final_ostes.columns:
                    df_final_ostes[col] = pd.to_numeric(df_final_ostes[col], errors="coerce")

            # =============================
            # DISPLAY
            # =============================
            st.divider()
            st.subheader(f"💰 OSTES {empresa}")

            st.dataframe(
                df_final_ostes,
                use_container_width=True,
                column_config={
                    "Subtotal": st.column_config.NumberColumn(format="$ %.2f"),
                    "IVA": st.column_config.NumberColumn(format="$ %.2f"),
                    "Total oste": st.column_config.NumberColumn(format="$ %.2f"),
                    "TC": st.column_config.NumberColumn(format="$ %.4f"),
                    "Total Correccion": st.column_config.NumberColumn(format="$ %.2f"),
                }
            )
            if st.button("📥 Cargar Datos - OSTES", use_container_width=True):
                st.success("Datos Cargados")

# =================================
# BUILD MANO DE OBRA REPORT
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
            # NORMALIZE KEYS (CRITICAL FIX)
            # =============================
            df_mant["Reporte"] = (
                pd.to_numeric(df_mant["# Reporte"], errors="coerce")
                .astype("Int64")
                .astype(str)
            )

            df_ostes["Reporte"] = (
                pd.to_numeric(df_ostes["# Reporte"], errors="coerce")
                .astype("Int64")
                .astype(str)
            )

            # =============================
            # BUILD OSTES LOOKUP (NO GROUPBY)
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
            # MERGE
            # =============================
            df_final = df_mant.merge(df_ostes_lookup, on="Reporte", how="left")

            # =============================
            # MAP RAZON REPARACION (FIX)
            # =============================
            df_final["Razon Reparacion"] = df_final.get("Razon Servicio")

            # =============================
            # DATE HANDLING
            # =============================
            df_final["Fecha Analisis"] = pd.to_datetime(
                df_final["Fecha Liberada"],
                errors="coerce",
                dayfirst=True
            )

            df_final["Año"] = df_final["Fecha Analisis"].dt.year
            df_final["Mes"] = df_final["Fecha Analisis"].dt.month

            # =============================
            # FINANCIALS
            # =============================
            df_final["Sub Total"] = df_final["Total"] / 1.16
            df_final["IVA"] = df_final["Total"] - df_final["Sub Total"]

            # =============================
            # TC MERGE
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

            # =============================
            # USD + CORRECTIONS
            # =============================
            df_final["Total USD"] = df_final["Total"] / df_final["TC"]
            df_final["Total Correccion"] = df_final["Total"]
            df_final["Diferencia"] = 0

            # =============================
            # STATIC FIELDS
            # =============================
            df_final["Flotilla"] = "N/A"
            df_final["Modelo"] = "N/A"
            df_final["Sucursal"] = "N/A"
            df_final["Comentarios"] = "N/A"

            # =============================
            # CLEAN FORMATS
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
                    df_final[col] = pd.to_datetime(df_final[col], errors="coerce").dt.date

            currency_cols = [
                "Sub Total", "IVA", "Total",
                "Total Correccion", "TC", "Total USD"
            ]

            for col in currency_cols:
                df_final[col] = pd.to_numeric(df_final[col], errors="coerce")

            # =============================
            # FINAL COLUMNS
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

            # Month names
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

            st.dataframe(
                df_final,
                use_container_width=True,
                column_config={
                    "Sub Total": st.column_config.NumberColumn(format="$ %.2f"),
                    "IVA": st.column_config.NumberColumn(format="$ %.2f"),
                    "Total": st.column_config.NumberColumn(format="$ %.2f"),
                    "Total Correccion": st.column_config.NumberColumn(format="$ %.2f"),
                    "TC": st.column_config.NumberColumn(format="$ %.4f"),
                    "Total USD": st.column_config.NumberColumn(format="$ %.2f"),
                }
            )
            if st.button("📥 Cargar Datos - Mantenimientos", use_container_width=True):
                    st.success("Datos Cargados")