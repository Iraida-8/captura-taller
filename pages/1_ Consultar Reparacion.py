import streamlit as st
import pandas as pd
from datetime import date
from auth import require_login, require_access
import streamlit.components.v1 as components
from supabase import create_client

# =================================
# Page configuration
# =================================
st.set_page_config(
    page_title="Consulta de Reparación",
    layout="wide"
)

# =================================
# CSS THEME — BLUE + YELLOW
# =================================
st.markdown(
    """
    <style>

    /* Hide sidebar */
    [data-testid="stSidebar"] {
        display: none;
    }

    /* Main background */
    .stApp {
        background-color: #151F6D;
    }

    /* Main container */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    /* Titles */
    h1 {
        color: #FFFFFF;
        font-size: 2rem;
        font-weight: 700;
    }

    h2, h3 {
        color: #BFA75F;
        font-weight: 600;
    }

    /* General text */
    p, label, span {
        color: #F5F5F5 !important;
    }

    /* Divider */
    hr {
        border-color: rgba(191, 167, 95, 0.25);
    }

    /* Inputs */
    div[data-baseweb="input"] > div,
    div[data-baseweb="select"] > div,
    textarea {
        background-color: #1B267A !important;
        border: 1px solid rgba(191, 167, 95, 0.25) !important;
        border-radius: 10px !important;
        color: white !important;
    }

    input, textarea {
        color: white !important;
    }

    input::placeholder,
    textarea::placeholder {
        color: #d0d0d0 !important;
    }

    div[data-baseweb="select"] * {
        color: white !important;
    }

    /* Buttons */
    div.stButton > button {
        border-radius: 12px;
        font-weight: 600;
        transition: all 0.2s ease;
    }

    /* Standard buttons */
    div.stButton > button {
        background-color: #1B267A;
        color: white;
        border: 1px solid rgba(191, 167, 95, 0.25);
    }

    div.stButton > button:hover {
        background-color: #24338C;
        border-color: #BFA75F;
        color: #BFA75F;
        transform: translateY(-1px);
    }

    /* Secondary nav button */
    button[kind="secondary"] {
        background-color: transparent !important;
        color: #BFA75F !important;
        border: 1px solid #BFA75F !important;
    }

    button[kind="secondary"]:hover {
        background-color: #BFA75F !important;
        color: #151F6D !important;
    }

    /* Dataframes */
    [data-testid="stDataFrame"] {
        border: 1px solid rgba(191, 167, 95, 0.20);
        border-radius: 12px;
        overflow: hidden;
    }

    /* Info / warning / success boxes */
    div[data-baseweb="notification"] {
        border-radius: 12px;
    }

    /* Dialog modal */
    div[role="dialog"] {
        border-radius: 18px !important;
        border: 1px solid rgba(191, 167, 95, 0.20) !important;
    }

    </style>
    """,
    unsafe_allow_html=True
)

# =================================
# Security
# =================================
require_login()
require_access("consultar_reparacion")

# =================================
# Supabase Client
# =================================
@st.cache_resource
def get_supabase():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_SERVICE_KEY"]
    )

supabase = get_supabase()

# =================================
# HARD RESET ON PAGE LOAD
# =================================

if "consulta_reparacion_initialized" not in st.session_state:

    # Reset modals
    st.session_state["modal_orden"] = None
    st.session_state["modal_tipo"] = None

    # Mark as initialized to avoid loop
    st.session_state["consulta_reparacion_initialized"] = True

# =================================
# Navigation
# =================================
if st.button("⬅ Volver al Dashboard"):
    st.switch_page("pages/dashboard.py")

st.divider()
st.title("📋 Consulta de Reparación")

EMPRESA_CONFIG = {
    "IGLOO TRANSPORT": {
        "ordenes": "mano_obra_igloo",
        "partes": "refacciones_data_igloo",
        "ostes": "ostes_igloo"
    },
    "LINCOLN FREIGHT": {
        "ordenes": "mano_obra_lincoln",
        "partes": "refacciones_data_lincoln",
        "ostes": "ostes_lincoln"
    },
    "PICUS": {
        "ordenes": "mano_obra_picus",
        "partes": "refacciones_data_picus",
        "ostes": "ostes_picus"
    },
    "SET LOGIS PLUS": {
        "ordenes": "mano_obra_logis",
        "partes": "refacciones_data_logis",
        "ostes": "ostes_logis"
    },
    "SET FREIGHT INTERNATIONAL": {
        "ordenes": "mano_obra_setfreight",
        "partes": "refacciones_data_setfreight",
        "ostes": "ostes_setfreight"
    }
}

# =================================
# LOADERS
# =================================
@st.cache_data(ttl=600)
def cargar_tabla(nombre_tabla):
    try:
        all_data = []
        chunk_size = 1000
        offset = 0

        while True:
            response = (
                supabase
                .table(nombre_tabla)
                .select("*")
                .range(offset, offset + chunk_size - 1)
                .execute()
            )

            data = response.data

            if not data:
                break

            all_data.extend(data)

            if len(data) < chunk_size:
                break

            offset += chunk_size

        if not all_data:
            return pd.DataFrame()

        df = pd.DataFrame(all_data)
        df.columns = df.columns.str.strip()

        return df

    except Exception as e:
        st.error(f"Error cargando {nombre_tabla}: {e}")
        return pd.DataFrame()
    
# =================================
# Le NORMALIZER
# =================================
def normalizar_columnas(df, tipo):
    if df.empty:
        return df

    # -------------------------
    # DROP SYSTEM COLUMNS
    # -------------------------
    df = df.drop(columns=["id", "created_at"], errors="ignore")

    # -------------------------
    # RENAME MAPS
    # -------------------------

    if tipo == "interna":
        rename_map = {
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
            "diferencia": "DIFERENCIA",
            "comentarios": "COMENTARIOS"
        }

    elif tipo == "ostes":
        rename_map = {
            "oste": "OSTE",
            "unidad": "Unidad",
            "flotilla": "Flotilla",
            "modelo": "Modelo",
            "tipo_de_unidad": "Tipo Unidad",
            "sucursal": "Sucursal",
            "reporte": "Reporte",
            "acreedor": "Acreedor",
            "factura": "Factura",
            "status_ct": "Status CT",
            "descripcion": "Descripcion",
            "razon_de_servicio": "Razon Reparacion",
            "fecha_analisis": "Fecha Analisis",
            "fecha_factura": "Fecha Factura",
            "fecha_oste": "Fecha OSTE",
            "fecha_cierre": "Fecha Cierre",
            "dias_reparacion": "Dias Reparacion",
            "subtotal": "Subtotal",
            "iva": "IVA",
            "total_oste": "Total oste",
            "tc": "TC",
            "total_correccion": "Total Correccion",
            "observaciones": "Observaciones"
        }

    elif tipo == "partes":
        rename_map = {
            "unidad": "Unidad",
            "fecha_compra": "Fecha Compra",
            "parte": "Parte",
            "cantidad": "Cantidad",
            "pu": "PU",
            "iva": "IVA",
            "total_correccion": "Total Correccion",
            "pu_usd": "PU USD",
            "total_usd": "Total USD"
        }

    else:
        return df

    df = df.rename(columns=rename_map)

    return df

# =================================
# EMPRESA SELECTION
# =================================
st.subheader("Selección de Empresa")

empresa = st.selectbox(
    "Empresa",
    ["Selecciona empresa"] + list(EMPRESA_CONFIG.keys()),
    index=0
)

if empresa == "Selecciona empresa":
    st.info("Selecciona una empresa para consultar las órdenes.")
    st.stop()

config = EMPRESA_CONFIG[empresa]

df = cargar_tabla(config["ordenes"])
df_partes = cargar_tabla(config["partes"])
df_ostes = cargar_tabla(config["ostes"])

# =============================
# NORMALIZACIÓN
# =============================
df = normalizar_columnas(df, "interna")
df_partes = normalizar_columnas(df_partes, "partes")
df_ostes = normalizar_columnas(df_ostes, "ostes")

# =================================
# DATE PARSING
# =================================
# Interna
if "Fecha Registro" in df.columns:
    df["Fecha Registro"] = pd.to_datetime(df["Fecha Registro"], errors="coerce")

if "Fecha Analisis" in df.columns:
    df["Fecha Analisis"] = pd.to_datetime(df["Fecha Analisis"], errors="coerce")

if "Fecha Aceptado" in df.columns:
    df["Fecha Aceptado"] = pd.to_datetime(df["Fecha Aceptado"], errors="coerce")

if "Fecha Iniciada" in df.columns:
    df["Fecha Iniciada"] = pd.to_datetime(df["Fecha Iniciada"], errors="coerce")

if "Fecha Liberada" in df.columns:
    df["Fecha Liberada"] = pd.to_datetime(df["Fecha Liberada"], errors="coerce")

if "Fecha Terminada" in df.columns:
    df["Fecha Terminada"] = pd.to_datetime(df["Fecha Terminada"], errors="coerce")

# OSTES
if "Fecha OSTE" in df_ostes.columns:
    df_ostes["Fecha OSTE"] = pd.to_datetime(df_ostes["Fecha OSTE"], errors="coerce")

if "Fecha Factura" in df_ostes.columns:
    df_ostes["Fecha Factura"] = pd.to_datetime(df_ostes["Fecha Factura"], errors="coerce")

if "Fecha Analisis" in df_ostes.columns:
    df_ostes["Fecha Analisis"] = pd.to_datetime(df_ostes["Fecha Analisis"], errors="coerce")

if "Fecha Cierre" in df_ostes.columns:
    df_ostes["Fecha Cierre"] = pd.to_datetime(df_ostes["Fecha Cierre"], errors="coerce")

# PARTES
if "Fecha Compra" in df_partes.columns:
    df_partes["Fecha Compra"] = pd.to_datetime(df_partes["Fecha Compra"], errors="coerce")

if "Fecha Analisis" in df_partes.columns:
    df_partes["Fecha Analisis"] = pd.to_datetime(df_partes["Fecha Analisis"], errors="coerce")

# =================================
# HARD LOCK 2025+ FOR INTERNA & EXTERNA
# =================================
LOCK_DATE = pd.Timestamp("2025-01-01")

if "Fecha Registro" in df.columns:
    df = df[df["Fecha Registro"] >= LOCK_DATE]

if "Fecha OSTE" in df_ostes.columns:
    df_ostes = df_ostes[df_ostes["Fecha OSTE"] >= LOCK_DATE]

if df.empty and df_ostes.empty:
    st.warning("No hay datos disponibles para esta empresa.")
    st.stop()

# =================================
# SAFE HELPERS
# =================================
def safe(x):
    if pd.isna(x) or x is None:
        return ""
    return str(x)

# =================================
# TOP FILTERS (UNIDAD + FACTURA)
# =================================
st.markdown("### Filtros")

col1, col2 = st.columns(2)

# -------- UNIDAD --------
with col1:

    unidades_interna = []
    unidades_externa = []

    if "Unidad" in df.columns:
        unidades_interna = df["Unidad"].dropna().astype(str).str.strip()

    if "Unidad" in df_ostes.columns:
        unidades_externa = df_ostes["Unidad"].dropna().astype(str).str.strip()

    unidades_unificadas = sorted(
        pd.concat([unidades_interna, unidades_externa]).unique()
    )

    unidad_sel = st.selectbox(
        "Unidad",
        ["Todas"] + unidades_unificadas,
        index=0
    )

# -------- FACTURA --------
with col2:

    facturas_interna = []
    facturas_externa = []

    if "Factura" in df.columns:
        facturas_interna = (
            df["Factura"]
            .dropna()
            .astype(str)
            .str.strip()
        )
        facturas_interna = facturas_interna[facturas_interna != ""]

    if "Factura" in df_ostes.columns:
        facturas_externa = (
            df_ostes["Factura"]
            .dropna()
            .astype(str)
            .str.strip()
        )
        facturas_externa = facturas_externa[facturas_externa != ""]

    facturas_unificadas = sorted(
        pd.concat([facturas_interna, facturas_externa]).unique()
    )

    factura_sel = st.selectbox(
        "Factura",
        ["Todas"] + facturas_unificadas,
        index=0
    )

# Reset modal if filters change
if "last_filters" not in st.session_state:
    st.session_state.last_filters = (unidad_sel, factura_sel)

current_filters = (unidad_sel, factura_sel)

if st.session_state.last_filters != current_filters:
    st.session_state.modal_orden = None
    st.session_state.modal_tipo = None
    st.session_state.last_filters = current_filters

# =====================================================
# BUILD INTERNAL DATASET (LATEST 10)
# =====================================================
df_interna = df.copy()

if unidad_sel != "Todas":
    df_interna = df_interna[
        df_interna["Unidad"].astype(str).str.strip() == unidad_sel.strip()
    ]

if factura_sel != "Todas":
    df_interna = df_interna[
        df_interna["Factura"].astype(str).str.strip() == factura_sel.strip()
    ]

if "Fecha Registro" in df_interna.columns:
    df_interna = df_interna.sort_values(
        by="Fecha Registro",
        ascending=False,
        na_position="last"
    ).head(10)

# =====================================================
# BUILD EXTERNAL DATASET (LATEST 10)
# =====================================================
df_externa = df_ostes.copy()

if unidad_sel != "Todas":
    df_externa = df_externa[
        df_externa["Unidad"].astype(str).str.strip() == unidad_sel.strip()
    ]

if factura_sel != "Todas":
    df_externa = df_externa[
        df_externa["Factura"].astype(str).str.strip() == factura_sel.strip()
    ]

if "Fecha OSTE" in df_externa.columns:
    df_externa = df_externa.sort_values(
        by="Fecha OSTE",
        ascending=False,
        na_position="last"
    ).head(10)

# =====================================================
# MANO DE OBRA INTERNA
# =====================================================
if (
    (unidad_sel != "Todas" or factura_sel != "Todas")
    and df_interna.empty
    and df_externa.empty
):
    st.warning("No hay reportes para el filtro seleccionado.")

st.markdown("### 🔧 Mano de Obra Interna")

if df_interna.empty:
    st.info("No hay registros internos.")
else:
    cols = st.columns(5)

    for i, (_, row) in enumerate(df_interna.iterrows()):
        col = cols[i % 5]

        with col:
            reporte = safe(row.get("Reporte"))
            unidad = safe(row.get("Unidad"))
            tipo = safe(row.get("Tipo Unidad"))
            factura = safe(row.get("Factura"))
            razon = safe(row.get("Razon Reparacion"))
            desc = safe(row.get("Descripcion"))
            fecha_registro = row.get("Fecha Registro")
            if pd.notna(fecha_registro):
                fecha_registro = fecha_registro.strftime("%d/%m/%Y")
            else:
                fecha_registro = ""

            html = f"""
            <div style="padding:6px;">
                <div style="
                    background:#ffffff;
                    padding:14px;
                    border-radius:16px;
                    box-shadow:0 4px 10px rgba(0,0,0,0.08);
                    color:#111;
                    min-height:190px;
                    font-family:sans-serif;
                ">
                    <div style="font-weight:900;">{reporte}</div>

                    <div style="font-size:0.8rem; margin-top:4px;">
                        {unidad} &nbsp; | &nbsp; {tipo}
                    </div>

                    <div style="font-size:0.8rem; font-weight:600; margin-top:4px;">
                        {factura}
                    </div>

                    <hr style="margin:6px 0">

                    <div style="font-size:0.8rem;">
                        <b>Razón:</b> {razon}
                    </div>

                    <div style="font-size:0.8rem;">
                        <b>Descripción:</b> {desc}
                    </div>

                    <hr style="margin:6px 0">

                    <div style="font-size:0.75rem;">
                        <b>Fecha Registro:</b> {fecha_registro}
                    </div>
                </div>
            </div>
            """

            components.html(html, height=260)

            if st.button("👁 Ver", key=f"ver_interna_{i}", use_container_width=True):
                st.session_state.modal_orden = row.to_dict()
                st.session_state.modal_tipo = "interna"

st.divider()

# =====================================================
# MANO DE OBRA EXTERNA (OSTES)
# =====================================================
st.markdown("### 🧾 Mano de Obra Externa (OSTES)")

if df_externa.empty:
    st.info("No hay registros externos.")
else:
    cols = st.columns(5)

    for i, (_, row) in enumerate(df_externa.iterrows()):
        col = cols[i % 5]

        with col:
            reporte = safe(row.get("Reporte"))
            unidad = safe(row.get("Unidad"))
            tipo = safe(row.get("Tipo Unidad"))
            factura = safe(row.get("Factura"))
            razon = safe(row.get("Razon Reparacion"))
            desc = safe(row.get("Descripcion"))
            fecha_oste = row.get("Fecha OSTE")
            if pd.notna(fecha_oste):
                fecha_oste = fecha_oste.strftime("%d/%m/%Y")
            else:
                fecha_oste = ""

            html = f"""
            <div style="padding:6px;">
                <div style="
                    background:#ffffff;
                    padding:14px;
                    border-radius:16px;
                    box-shadow:0 4px 10px rgba(0,0,0,0.08);
                    color:#111;
                    min-height:190px;
                    font-family:sans-serif;
                ">
                    <div style="font-weight:900;">{reporte}</div>

                    <div style="font-size:0.8rem; margin-top:4px;">
                        {unidad} &nbsp; | &nbsp; {tipo}
                    </div>

                    <div style="font-size:0.8rem; font-weight:600; margin-top:4px;">
                        {factura}
                    </div>

                    <hr style="margin:6px 0">

                    <div style="font-size:0.8rem;">
                        <b>Razón:</b> {razon}
                    </div>

                    <div style="font-size:0.8rem;">
                        <b>Descripción:</b> {desc}
                    </div>

                    <hr style="margin:6px 0">

                    <div style="font-size:0.75rem;">
                        <b>Fecha OSTE:</b> {fecha_oste}
                    </div>
                </div>
            </div>
            """

            components.html(html, height=260)

            if st.button("👁 Ver", key=f"ver_externa_{i}", use_container_width=True):
                st.session_state.modal_orden = row.to_dict()
                st.session_state.modal_tipo = "oste"

st.divider()

# =================================
# REFACCIONES RECIENTES
# =================================
st.subheader("Refacciones Recientes")

if not df_partes.empty and "Unidad" in df_partes.columns:

    LOCK_DATE = pd.Timestamp("2025-01-01")

    df_partes_base = df_partes[
        df_partes["Fecha Compra"] >= LOCK_DATE
    ].copy()

    # -----------------------------
    # DROPDOWNS
    # -----------------------------
    col1, col2 = st.columns(2)

    with col1:
        unidad_partes_sel = st.selectbox(
            "Filtrar por Unidad",
            ["Todas"] + sorted(
                df_partes_base["Unidad"]
                .dropna()
                .astype(str)
                .str.strip()
                .unique()
            ),
            index=0
        )

    with col2:
        if "Parte" in df_partes_base.columns:
            parte_sel = st.selectbox(
                "Filtrar por Parte",
                ["Todas"] + sorted(
                    df_partes_base["Parte"]
                    .dropna()
                    .astype(str)
                    .str.strip()
                    .unique()
                ),
                index=0
            )
        else:
            parte_sel = "Todas"

    # -----------------------------
    # APPLY FILTERS
    # -----------------------------
    df_partes_filtrado = df_partes_base.copy()

    if unidad_partes_sel != "Todas":
        df_partes_filtrado = df_partes_filtrado[
            df_partes_filtrado["Unidad"]
            .astype(str)
            .str.strip()
            == unidad_partes_sel.strip()
        ]

    if parte_sel != "Todas":
        df_partes_filtrado = df_partes_filtrado[
            df_partes_filtrado["Parte"]
            .astype(str)
            .str.strip()
            == parte_sel.strip()
        ]

    # -----------------------------
    # SORT
    # -----------------------------
    df_partes_filtrado = df_partes_filtrado.sort_values(
        "Fecha Compra",
        ascending=False,
        na_position="last"
    )

    # -----------------------------
    # COLUMN LOGIC
    # -----------------------------
    if empresa in ["LINCOLN FREIGHT", "SET FREIGHT INTERNATIONAL", "SET LOGIS PLUS"]:
        columnas_partes = [
            "Unidad",
            "Fecha Compra",
            "Parte",
            "PU USD",
            "Cantidad",
            "Total USD"
        ]
    elif empresa in ["IGLOO TRANSPORT", "PICUS"]:
        columnas_partes = [
            "Unidad",
            "Fecha Compra",
            "Parte",
            "PU",
            "IVA",
            "Cantidad",
            "Total Correccion"
        ]
    else:
        columnas_partes = [
            "Unidad",
            "Fecha Compra",
            "Parte"
        ]

    df_partes_final = df_partes_filtrado[
        [c for c in columnas_partes if c in df_partes_filtrado.columns]
    ]

    st.dataframe(
        df_partes_final,
        hide_index=True,
        use_container_width=True
    )
    st.caption(f"Total de refacciones: {len(df_partes_final)}")

else:
    st.info("No hay información de partes disponible para esta empresa.")

# =================================
# FILTROS - TABLAS COMPLETAS (2025+)
# =================================
st.divider()
st.markdown("### Filtros - Tablas Completas")

col1, col2 = st.columns(2)

# -------- UNIDAD TABLA --------
with col1:

    unidades_interna_tabla = []
    unidades_externa_tabla = []

    if "Unidad" in df.columns:
        unidades_interna_tabla = df["Unidad"].dropna().astype(str).str.strip()

    if "Unidad" in df_ostes.columns:
        unidades_externa_tabla = df_ostes["Unidad"].dropna().astype(str).str.strip()

    unidades_tabla_unificadas = sorted(
        pd.concat([unidades_interna_tabla, unidades_externa_tabla]).unique()
    )

    unidad_tabla_sel = st.selectbox(
        "Unidad",
        ["Todas"] + unidades_tabla_unificadas,
        index=0,
        key="unidad_tabla"
    )

# -------- FACTURA TABLA --------
with col2:

    facturas_interna_tabla = []
    facturas_externa_tabla = []

    if "Factura" in df.columns:
        facturas_interna_tabla = (
            df["Factura"]
            .dropna()
            .astype(str)
            .str.strip()
        )
        facturas_interna_tabla = facturas_interna_tabla[facturas_interna_tabla != ""]

    if "Factura" in df_ostes.columns:
        facturas_externa_tabla = (
            df_ostes["Factura"]
            .dropna()
            .astype(str)
            .str.strip()
        )
        facturas_externa_tabla = facturas_externa_tabla[facturas_externa_tabla != ""]

    facturas_tabla_unificadas = sorted(
        pd.concat([facturas_interna_tabla, facturas_externa_tabla]).unique()
    )

    factura_tabla_sel = st.selectbox(
        "Factura",
        ["Todas"] + facturas_tabla_unificadas,
        index=0,
        key="factura_tabla"
    )

# =================================
# TABLA COMPLETA - INTERNAS (2025+)
# =================================
st.subheader("Todas las Órdenes Internas")

df_tabla_interna = df.copy()

df_tabla_interna = df.copy()

if unidad_tabla_sel != "Todas":
    df_tabla_interna = df_tabla_interna[
        df_tabla_interna["Unidad"].astype(str).str.strip() == unidad_tabla_sel.strip()
    ]

if factura_tabla_sel != "Todas":
    df_tabla_interna = df_tabla_interna[
        df_tabla_interna["Factura"].astype(str).str.strip() == factura_tabla_sel.strip()
    ]

if df_tabla_interna.empty:
    st.info("No hay órdenes internas.")
else:

    columnas_ocultar = ["DIFERENCIA", "COMENTARIOS"]
    columnas_mostrar = [
        c for c in df_tabla_interna.columns
        if c not in columnas_ocultar
    ]

    if "Fecha Registro" in df_tabla_interna.columns:
        df_tabla_interna = df_tabla_interna.sort_values(
            "Fecha Registro",
            ascending=False
        )

    st.dataframe(
        df_tabla_interna[columnas_mostrar],
        hide_index=True,
        use_container_width=True
    )

    st.caption(f"Total de órdenes internas: {len(df_tabla_interna)}")

# =================================
# TABLA COMPLETA - EXTERNAS (OSTES 2025+)
# =================================
st.divider()
st.subheader("Todas las Órdenes Externas (OSTES)")

df_tabla_externa = df_ostes.copy()

if unidad_tabla_sel != "Todas":
    df_tabla_externa = df_tabla_externa[
        df_tabla_externa["Unidad"].astype(str).str.strip() == unidad_tabla_sel.strip()
    ]

if factura_tabla_sel != "Todas":
    df_tabla_externa = df_tabla_externa[
        df_tabla_externa["Factura"].astype(str).str.strip() == factura_tabla_sel.strip()
    ]

if df_tabla_externa.empty:
    st.info("No hay registros externos.")
else:

    if "Fecha OSTE" in df_tabla_externa.columns:
        df_tabla_externa = df_tabla_externa.sort_values(
            "Fecha OSTE",
            ascending=False
        )

    st.dataframe(
        df_tabla_externa,
        hide_index=True,
        use_container_width=True
    )

    st.caption(f"Total de órdenes externas: {len(df_tabla_externa)}")

# =================================
# VIEW MODAL
# =================================
if st.session_state.get("modal_orden"):

    r = st.session_state.modal_orden
    tipo = st.session_state.get("modal_tipo", "interna")

    @st.dialog("Detalle de la Reparación")
    def modal():

        def safe(x):
            if pd.isna(x) or x is None:
                return ""
            return str(x)

        def safe_date(x):
            d = pd.to_datetime(x, errors="coerce")
            return d.date() if pd.notna(d) else "-"

        # =====================================================
        # ================== INTERNA ==========================
        # =====================================================
        if tipo == "interna":

            st.markdown(f"## Reporte {safe(r.get('Reporte'))}")

            st.subheader("Unidad")

            c1, c2, c3 = st.columns(3)
            c1.markdown(f"**Unidad:** {safe(r.get('Unidad'))}")
            c2.markdown(f"**Modelo:** {safe(r.get('Modelo'))}")
            c3.markdown(f"**Tipo:** {safe(r.get('Tipo Unidad'))}")

            c4, c5 = st.columns(2)
            c4.markdown(f"**Flotilla:** {safe(r.get('Flotilla'))}")
            c5.markdown(f"**Sucursal:** {safe(r.get('Sucursal'))}")

            st.divider()

            st.subheader("Cliente")

            c1, c2 = st.columns(2)
            c1.markdown(f"**Nombre:** {safe(r.get('Nombre Cliente'))}")
            c2.markdown(f"**Factura:** {safe(r.get('Factura'))}")

            st.divider()

            st.subheader("Estatus")
            st.markdown(f"**{safe(r.get('Estatus'))}**")

            st.divider()

            st.subheader("Razón de reparación")
            st.write(safe(r.get("Razon Reparacion")))

            st.subheader("Descripción")
            st.write(safe(r.get("Descripcion")))

            st.divider()

            st.subheader("Fechas")

            c1, c2, c3 = st.columns(3)
            c1.markdown(f"**Análisis:** {safe_date(r.get('Fecha Analisis'))}")
            c2.markdown(f"**Registro:** {safe_date(r.get('Fecha Registro'))}")
            c3.markdown(f"**Aceptado:** {safe_date(r.get('Fecha Aceptado'))}")

            c4, c5, c6 = st.columns(3)
            c4.markdown(f"**Iniciado:** {safe_date(r.get('Fecha Iniciada'))}")
            c5.markdown(f"**Liberada:** {safe_date(r.get('Fecha Liberada'))}")
            c6.markdown(f"**Terminada:** {safe_date(r.get('Fecha Terminada'))}")

            st.divider()

            st.subheader("Totales")

            c1, c2, c3 = st.columns(3)
            c1.markdown(f"**Sub Total:** {safe(r.get('Sub Total'))}")
            c2.markdown(f"**IVA:** {safe(r.get('IVA'))}")
            c3.markdown(f"**Total:** {safe(r.get('Total'))}")

            c4, c5, c6 = st.columns(3)
            c4.markdown(f"**Total Corrección:** {safe(r.get('Total Correccion'))}")
            c5.markdown(f"**TC:** {safe(r.get('TC'))}")
            c6.markdown(f"**Total USD:** {safe(r.get('Total USD'))}")

            st.divider()

            st.subheader("Observaciones")
            st.markdown(f"**Diferencia:** {safe(r.get('DIFERENCIA'))}")
            st.write(safe(r.get("COMENTARIOS")))

        # =====================================================
        # ================== OSTE =============================
        # =====================================================
        else:

            st.markdown(f"## OSTE {safe(r.get('OSTE'))}")

            st.subheader("Unidad")

            c1, c2, c3 = st.columns(3)
            c1.markdown(f"**Unidad:** {safe(r.get('Unidad'))}")
            c2.markdown(f"**Modelo:** {safe(r.get('Modelo'))}")
            c3.markdown(f"**Tipo:** {safe(r.get('Tipo Unidad'))}")

            c4, c5 = st.columns(2)
            c4.markdown(f"**Flotilla:** {safe(r.get('Flotilla'))}")
            c5.markdown(f"**Sucursal:** {safe(r.get('Sucursal'))}")

            st.divider()

            st.subheader("Proveedor")

            c1, c2 = st.columns(2)
            c1.markdown(f"**Acreedor:** {safe(r.get('Acreedor'))}")
            c2.markdown(f"**Factura:** {safe(r.get('Factura'))}")

            st.divider()

            st.subheader("Estado")
            st.markdown(f"**{safe(r.get('Status CT'))}**")

            st.divider()

            st.subheader("Servicio")
            st.markdown(f"**Reporte:** {safe(r.get('Reporte'))}")
            st.markdown(f"**Razón:** {safe(r.get('Razon Reparacion'))}")
            st.write(safe(r.get("Descripcion")))

            st.divider()

            st.subheader("Fechas")

            c1, c2, c3 = st.columns(3)
            c1.markdown(f"**Análisis:** {safe_date(r.get('Fecha Analisis'))}")
            c2.markdown(f"**Factura:** {safe_date(r.get('Fecha Factura'))}")
            c3.markdown(f"**OSTE:** {safe_date(r.get('Fecha OSTE'))}")

            c4, c5 = st.columns(2)
            c4.markdown(f"**Cierre:** {safe_date(r.get('Fecha Cierre'))}")
            c5.markdown(f"**Días reparación:** {safe(r.get('Dias Reparacion'))}")

            st.divider()

            st.subheader("Totales")

            c1, c2, c3 = st.columns(3)
            c1.markdown(f"**Subtotal:** {safe(r.get('Subtotal'))}")
            c2.markdown(f"**IVA:** {safe(r.get('IVA'))}")
            c3.markdown(f"**Total OSTE:** {safe(r.get('Total oste'))}")

            c4, c5 = st.columns(2)
            c4.markdown(f"**TC:** {safe(r.get('TC'))}")
            c5.markdown(f"**Total Corrección:** {safe(r.get('Total Correccion'))}")

            st.divider()

            st.subheader("Observaciones")
            st.write(safe(r.get("Observaciones")))

        st.divider()

        if st.button("Cerrar"):
            st.session_state.modal_orden = None
            st.rerun()

    modal()