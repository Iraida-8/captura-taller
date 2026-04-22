import streamlit as st
import pandas as pd
from datetime import datetime, date
from auth import require_login, require_access
import html
from supabase import create_client

def clean(val):
    import pandas as pd
    if pd.isna(val) or val is None:
        return ""
    return str(val).strip()

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
# Page configuration
# =================================
st.set_page_config(
    page_title="Autorización y Actualización de Pases de Taller",
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
        margin-bottom: 0.5rem;
    }

    h2, h3 {
        color: #BFA75F;
        font-weight: 600;
    }

    /* General text */
    p, label, span {
        color: #F5F5F5 !important;
    }

    /* Caption */
    .stCaption {
        color: #D9D9D9 !important;
    }

    /* Divider */
    hr {
        border-color: rgba(191, 167, 95, 0.25);
    }

    /* Inputs / Selects / TextArea */
    div[data-baseweb="input"] > div,
    div[data-baseweb="select"] > div,
    textarea {
        background-color: #1B267A !important;
        border: 1px solid rgba(191, 167, 95, 0.25) !important;
        border-radius: 10px !important;
        color: white !important;
    }

    input,
    textarea {
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
    div.stButton > button,
    div[data-testid="stFormSubmitButton"] > button {
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

    /* Primary buttons */
    button[kind="primary"] {
        background-color: #BFA75F !important;
        color: #151F6D !important;
        border: none !important;
        box-shadow: 0 4px 12px rgba(191, 167, 95, 0.20);
    }

    button[kind="primary"]:hover {
        background-color: #d4bc73 !important;
        color: #151F6D !important;
    }

    /* Secondary navigation buttons */
    button[kind="secondary"] {
        background-color: transparent !important;
        color: #BFA75F !important;
        border: 1px solid #BFA75F !important;
    }

    button[kind="secondary"]:hover {
        background-color: #BFA75F !important;
        color: #151F6D !important;
    }

    /* Metric cards */
    [data-testid="metric-container"] {
        background-color: #1B267A;
        border: 1px solid rgba(191, 167, 95, 0.20);
        padding: 1rem;
        border-radius: 14px;
    }

    /* Containers with border=True */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border: 1px solid rgba(191, 167, 95, 0.20) !important;
        border-radius: 14px !important;
        background-color: #1B267A;
    }

    /* Data editor + dataframe */
    [data-testid="stDataEditor"],
    [data-testid="stDataFrame"] {
        border: 1px solid rgba(191, 167, 95, 0.20);
        border-radius: 12px;
        overflow: hidden;
    }

    /* Dialog modal */
    div[role="dialog"] {
        border-radius: 18px !important;
        border: 1px solid rgba(191, 167, 95, 0.20) !important;
    }

    /* Notifications */
    div[data-baseweb="notification"] {
        border-radius: 12px;
    }

    /* Expander */
    [data-testid="stExpander"] {
        background-color: #1B267A;
        border: 1px solid rgba(191, 167, 95, 0.20);
        border-radius: 14px;
    }

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
    st.session_state.modal_factura = None
    st.session_state.modal_factura_open = False
    st.session_state.buscar_trigger = False
    st.session_state["_reset_autorizacion_page"] = False
    
# =================================
# Navigation
# =================================
if st.button("⬅ Volver al Dashboard"):
    st.session_state.modal_reporte = None
    st.session_state.modal_factura = None
    st.session_state.modal_factura_open = False
    st.session_state.buscar_trigger = False
    st.switch_page("pages/dashboard.py")

st.divider()

# =================================
# Update Estado
# =================================
VALID_ESTADOS = [
    "Inicio / Nuevo",
    "En Curso / Proceso",
    "Cerrado / Terminado",
    "Cerrado / Cancelado",
]

def actualizar_estado_pase(empresa, folio, nuevo_estado):

    if nuevo_estado not in VALID_ESTADOS:
        return

    table_map = {
        "IGLOO TRANSPORT": "IGLOO",
        "LINCOLN FREIGHT": "LINCOLN",
        "PICUS": "PICUS",
        "SET FREIGHT INTERNATIONAL": "SFI",
        "SET LOGIS PLUS": "SLP",
    }

    table_name = table_map.get(empresa)
    if not table_name:
        return

    supabase = get_supabase_client()

    supabase.table(table_name)\
        .update({"Estado": nuevo_estado})\
        .eq('"No. de Folio"', folio)\
        .execute()

# =================================
# Update OSTE (SUPABASE)
# =================================
def actualizar_oste_pase(empresa, folio, oste):

    table_map = {
        "IGLOO TRANSPORT": "IGLOO",
        "LINCOLN FREIGHT": "LINCOLN",
        "PICUS": "PICUS",
        "SET FREIGHT INTERNATIONAL": "SFI",
        "SET LOGIS PLUS": "SLP",
    }

    table_name = table_map.get(empresa)

    if not table_name:
        return

    supabase = get_supabase_client()

    supabase.table(table_name)\
        .update({"Oste": oste})\
        .eq('"No. de Folio"', folio)\
        .execute()

# =================================
# Update No. de Orden (SUPABASE)
# =================================

def actualizar_no_reporte_pase(empresa, folio, nuevo_no_reporte):

    table_map = {
        "IGLOO TRANSPORT": "IGLOO",
        "LINCOLN FREIGHT": "LINCOLN",
        "PICUS": "PICUS",
        "SET FREIGHT INTERNATIONAL": "SFI",
        "SET LOGIS PLUS": "SLP",
    }

    table_name = table_map.get(empresa)

    if not table_name:
        return

    supabase = get_supabase_client()

    valor_final = str(nuevo_no_reporte).strip()

    if valor_final == "":
        valor_final = None

    supabase.table(table_name)\
        .update({
            "No. de Reporte": valor_final
        })\
        .eq('"No. de Folio"', folio)\
        .execute()
    
# =================================
# Update Descripcion Problema
# =================================
def actualizar_descripcion_pase(empresa, folio, nueva_descripcion):

    table_map = {
        "IGLOO TRANSPORT": "IGLOO",
        "LINCOLN FREIGHT": "LINCOLN",
        "PICUS": "PICUS",
        "SET FREIGHT INTERNATIONAL": "SFI",
        "SET LOGIS PLUS": "SLP",
    }

    table_name = table_map.get(empresa)
    if not table_name:
        return

    supabase = get_supabase_client()

    supabase.table(table_name)\
        .update({"Descripcion Problema": nueva_descripcion})\
        .eq('"No. de Folio"', folio)\
        .execute()

# =================================
# GUARDAR FACTURA
# =================================
def guardar_factura(folio, numero_factura):

    supabase = get_supabase_client()

    response = (
        supabase
        .table("INVOICES")
        .select("*")
        .eq('"No. de Folio"', folio)
        .execute()
    )

    data = response.data

    if data:
        supabase.table("INVOICES")\
            .update({"No. de Factura": numero_factura})\
            .eq('"No. de Folio"', folio)\
            .execute()
    else:
        supabase.table("INVOICES")\
            .insert({
                "No. de Folio": folio,
                "No. de Factura": numero_factura
            })\
            .execute()

# =================================
# Registrar Cambio en CHANGELOG
# =================================
def registrar_cambio_log(
    usuario,
    empresa,
    folio,
    tipo_cambio,
    estado_anterior=None,
    estado_nuevo=None,
    oste_anterior=None,
    oste_nuevo=None,
    comentario=""
):

    supabase = get_supabase_client()

    response = supabase.table("AUDIT").insert({
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Usuario": clean(usuario),
        "Empresa": clean(empresa),
        "No. de Folio": clean(folio),
        "Tipo Cambio": clean(tipo_cambio),
        "Estado Anterior": clean(estado_anterior),
        "Estado Nuevo": clean(estado_nuevo),
        "OSTE Anterior": clean(oste_anterior),
        "OSTE Nuevo": clean(oste_nuevo),
        "Comentario": clean(comentario)
    }).execute()

    if getattr(response, "error", None):
        st.error(f"Audit log error: {response.error}")

# =================================
# Log estado sin refacciones
# =================================
def registrar_cambio_estado_sin_servicios(folio, usuario, nuevo_estado):

    supabase = get_supabase_client()

    estado_fecha_map = {
        "En Curso / Proceso": "Fecha En Proceso",
        "Cerrado / Terminado": "Fecha Terminado",
        "Cerrado / Cancelado": "Fecha Cancelado",
    }

    fecha_col = estado_fecha_map.get(nuevo_estado)

    if not fecha_col:
        return

    fecha_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    payload = {
        "No. de Folio": folio,
        "Modifico": usuario,
        "Fecha Mod": fecha_now,
        fecha_col: fecha_now
    }

    supabase.table("SERVICES").insert(payload).execute()

# =================================
# Load Servicios for Folio (SUPABASE)
# =================================
def cargar_servicios_folio(folio):

    supabase = get_supabase_client()

    response = (
        supabase
        .table("SERVICES")
        .select("*")
        .eq('"No. de Folio"', folio)
        .execute()
    )

    data = response.data

    if not data:
        return pd.DataFrame(columns=[
            "Parte",
            "Tipo De Parte",
            "Posicion",
            "Cantidad"
        ])

    df = pd.DataFrame(data)

    # remove status rows
    if "Parte" in df.columns:
        df = df[df["Parte"].notna() & (df["Parte"].astype(str).str.strip() != "")]

    return df[
        ["Parte", "Tipo De Parte", "Posicion", "Cantidad"]
    ]

# =================================
# UPSERT Servicios / Refacciones (SUPABASE)
# =================================
def guardar_servicios_refacciones(folio, usuario, servicios_df, nuevo_estado=None):

    supabase = get_supabase_client()

    if servicios_df is None or servicios_df.empty:
        return

    fecha_mod = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    estado_fecha_map = {
        "En Curso / Proceso": "Fecha En Proceso",
        "Cerrado / Terminado": "Fecha Terminado",
        "Cerrado / Cancelado": "Fecha Cancelado",
    }

    fecha_col = estado_fecha_map.get(nuevo_estado)

    for _, r in servicios_df.iterrows():

        cantidad = r.get("Cantidad", 0)

        if pd.isna(cantidad) or cantidad == "":
            cantidad = 0

        payload = {
            "No. de Folio": folio,
            "Modifico": usuario,
            "Parte": str(r.get("Parte", "")).strip(),
            "Tipo De Parte": str(r.get("Tipo De Parte", "")).strip(),
            "Posicion": str(r.get("Posicion", "")).strip(),
            "Cantidad": int(float(cantidad)),
            "Fecha Mod": fecha_mod,
        }

        if fecha_col:
            payload[fecha_col] = fecha_mod

        supabase.table("SERVICES").insert(payload).execute()

# =================================
# Load Pase de Taller (SUPABASE)
# =================================
@st.cache_data(ttl=300)
def cargar_pases_taller():

    supabase = get_supabase_client()

    tablas = ["IGLOO", "LINCOLN", "PICUS", "SFI", "SLP"]

    dfs = []

    for tabla in tablas:

        response = (
            supabase
            .table(tabla)
            .select("*")
            .execute()
        )

        data = response.data

        if data:
            dfs.append(pd.DataFrame(data))

    if not dfs:
        return pd.DataFrame()

    df = pd.concat(dfs, ignore_index=True)

    df.rename(columns={
        "No. de Folio": "NoFolio",
        "Fecha de Captura": "Fecha",
        "Tipo de Proveedor": "Proveedor",
    }, inplace=True)

    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce", utc=True).dt.tz_localize(None)
    df["NoFolio"] = df["NoFolio"].astype(str)

    return df

# =================================
# Load FACTURAS (SUPABASE)
# =================================
@st.cache_data(ttl=300)
def cargar_facturas():

    supabase = get_supabase_client()

    response = (
        supabase
        .table("INVOICES")
        .select("*")
        .execute()
    )

    data = response.data

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

# =================================
# Load Audit Log
# =================================
@st.cache_data(ttl=120)
def cargar_audit():

    supabase = get_supabase_client()

    response = (
        supabase
        .table("AUDIT")
        .select("*")
        .order("Timestamp", desc=True)
        .limit(200)
        .execute()
    )

    data = response.data

    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)

    if "Timestamp" in df.columns:
        df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")

    return df

#loaders
pases_df = cargar_pases_taller()
facturas_df = cargar_facturas()
audit_df = cargar_audit()

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

    page_size = 1000
    start = 0
    all_rows = []

    while True:
        response = (
            supabase
            .table("parts")
            .select("*")
            .range(start, start + page_size - 1)
            .execute()
        )

        data = response.data
        if not data:
            break

        all_rows.extend(data)
        start += page_size

    if not all_rows:
        return pd.DataFrame(columns=["Parte", "Tipo"])

    df = pd.DataFrame(all_rows)

    df.columns = df.columns.str.strip().str.lower()

    df = df.rename(columns={
        "parte": "Parte",
        "tipo": "Tipo"
    })

    return df

# =================================
# Title
# =================================
st.title("📋 Autorización y Actualización de Pases de Taller")

# =================================
# KPI STRIP
# =================================
st.markdown("### Resumen general")

total_ordenes = len(pases_df)

def porcentaje(n):
    if total_ordenes == 0:
        return 0
    return round((n / total_ordenes) * 100, 1)

pendientes = len(
    pases_df[pases_df["Estado"] == "Inicio / Nuevo"]
)

en_proceso = len(
    pases_df[pases_df["Estado"] == "En Curso / Proceso"]
)

completadas = len(
    pases_df[pases_df["Estado"] == "Cerrado / Terminado"]
)

canceladas = len(
    pases_df[pases_df["Estado"] == "Cerrado / Cancelado"]
)

k1, k2, k3, k4 = st.columns(4)

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
postit(k2, "Órdenes en Proceso", en_proceso, porcentaje(en_proceso), "#E2E3FF")
postit(k3, "Órdenes Terminadas", completadas, porcentaje(completadas), "#D4EDDA")
postit(k4, "Canceladas", canceladas, porcentaje(canceladas), "#F8D7DA")

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

        empresas = sorted(pases_df["Empresa"].dropna().unique())
        total_global = len(pases_df)

        for empresa in empresas:

            df_emp = pases_df[pases_df["Empresa"] == empresa]
            total_emp = len(df_emp)
            pct = (total_emp / total_global * 100) if total_global else 0

            pendientes = len(
                df_emp[df_emp["Estado"] == "Inicio / Nuevo"]
            )

            proceso = len(
                df_emp[df_emp["Estado"] == "En Curso / Proceso"]
            )

            completadas = len(
                df_emp[df_emp["Estado"] == "Cerrado / Terminado"]
            )

            canceladas = len(
                df_emp[df_emp["Estado"] == "Cerrado / Cancelado"]
            )

            with st.container(border=True):

                st.markdown(f"**{empresa}**")
                st.caption(f"Total: {total_emp} ({pct:.1f}%)")

                c1, c2, c3, c4 = st.columns(4)

                c1.metric("Pendientes", pendientes)
                c2.metric("Proceso", proceso)
                c3.metric("Completadas", completadas)
                c4.metric("Canceladas", canceladas)

    else:
        st.info("No hay datos.")

# =============================
# RIGHT → LAST ACTIVITY
# =============================
with right:
    st.markdown("### Última actividad")

    if audit_df.empty:
        st.info("Sin actividad registrada.")
    else:

        audit_sorted = audit_df.head(9)

        rows_html = ""

        for _, row in audit_sorted.iterrows():

            timestamp = row.get("Timestamp")
            usuario = html.escape(str(row.get("Usuario", "")))
            empresa = html.escape(str(row.get("Empresa", "")))
            folio = html.escape(str(row.get("No. de Folio", "")))
            tipo = html.escape(str(row.get("Tipo Cambio", "")))
            estado_nuevo = html.escape(str(row.get("Estado Nuevo", "")))
            oste_nuevo = html.escape(str(row.get("OSTE Nuevo", "")))
            comentario = html.escape(str(row.get("Comentario", "")))

            fecha_txt = (
                timestamp.strftime("%Y-%m-%d %H:%M")
                if pd.notna(timestamp)
                else ""
            )

            detalle = tipo

            if estado_nuevo:
                detalle += f" → {estado_nuevo}"

            if oste_nuevo:
                detalle += f" (OSTE: {oste_nuevo})"

            if comentario:
                comentario_safe = html.escape(str(comentario))
                detalle += f" — {comentario_safe}"

            rows_html += f"""
            <div style="
                margin-bottom:10px;
                padding-bottom:8px;
                border-bottom:1px solid #eee;
            ">
                <div style="font-size:0.75rem; opacity:0.7;">
                    {fecha_txt}
                </div>
                <div style="font-weight:700;">
                    {folio} — {empresa}
                </div>
                <div style="font-size:0.8rem;">
                    {detalle}
                </div>
                <div style="font-size:0.75rem; opacity:0.6;">
                    por {usuario}
                </div>
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

# =================================
# Session state defaults
# =================================
st.session_state.setdefault("buscar_trigger", False)
st.session_state.setdefault("modal_reporte", None)
st.session_state.setdefault("modal_factura", None)
st.session_state.setdefault("modal_factura_open", False)
st.session_state.setdefault("refaccion_seleccionada", None)
st.session_state.setdefault(
    "servicios_df",
    pd.DataFrame(columns=[
        "Parte",
        "Tipo De Parte",
        "Posicion",
        "Cantidad"
    ])
)

# =================================
# DISTRIBUCIÓN POR TIPO DE PARTE
# =================================
st.divider()
st.subheader("Distribución por Tipo de Parte")

@st.cache_data(ttl=300)
def cargar_tipos_parte():

    supabase = get_supabase_client()

    page_size = 1000
    start = 0
    all_rows = []

    while True:
        response = (
            supabase
            .table("SERVICES")
            .select('"Tipo De Parte"')
            .range(start, start + page_size - 1)
            .execute()
        )

        data = response.data

        if not data:
            break

        all_rows.extend(data)
        start += page_size

    if not all_rows:
        return pd.DataFrame(columns=["Tipo De Parte"])

    df = pd.DataFrame(all_rows)

    if "Tipo De Parte" not in df.columns:
        return pd.DataFrame(columns=["Tipo De Parte"])

    # limpiar valores inválidos
    df["Tipo De Parte"] = (
        df["Tipo De Parte"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    # excluir vacíos, null, nan, none
    df = df[
        (df["Tipo De Parte"] != "")
        & (df["Tipo De Parte"].str.lower() != "nan")
        & (df["Tipo De Parte"].str.lower() != "none")
        & (df["Tipo De Parte"].str.lower() != "null")
    ]

    return df


tipos_df = cargar_tipos_parte()

if tipos_df.empty:
    st.info("No hay datos disponibles en Tipo De Parte.")
else:

    conteo_tipos = (
        tipos_df["Tipo De Parte"]
        .value_counts()
        .reset_index()
    )

    conteo_tipos.columns = ["Tipo De Parte", "Cantidad"]

    total_tipos = conteo_tipos["Cantidad"].sum()

    for _, row in conteo_tipos.iterrows():

        tipo = row["Tipo De Parte"]
        cantidad = int(row["Cantidad"])
        progreso = cantidad / total_tipos if total_tipos else 0
        porcentaje = round((cantidad / total_tipos) * 100, 1) if total_tipos else 0

        st.markdown(
            f"""
            <div style="
                background:#fff7d6;
                padding:18px;
                border-radius:16px;
                margin-bottom:18px;
                box-shadow:0 4px 10px rgba(0,0,0,0.08);
                color:#111;
                font-family:sans-serif;
            ">

                <div style="
                    font-size:1rem;
                    font-weight:800;
                    margin-bottom:6px;
                    color:#111;
                ">
                    {tipo}
                </div>

                <div style="
                    font-size:0.9rem;
                    margin-bottom:10px;
                    color:#111;
                ">
                    {cantidad} registros ({porcentaje}%)
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )

        st.progress(progreso)

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
        pases_df[pases_df["Estado"] == "Inicio / Nuevo"]
        .sort_values("Fecha", ascending=False)
        .head(10)
    )

    if top10.empty:
        st.info("No hay pases en estado Inicio / Nuevo.")

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
                            Inicio / Nuevo
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

                    st.session_state.modal_factura = None
                    st.session_state.modal_factura_open = False

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

    # CLOSE FACTURA MODAL IF USER STARTS FILTERING
    if filtro_folio_fact or filtro_factura_fact:
        st.session_state.modal_factura = None

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
                    st.session_state.modal_factura_open = True

else:
    st.info("No hay datos disponibles.")

# =================================
# FACTURA MODAL
# =================================
if st.session_state.get("modal_factura") and st.session_state.get("modal_factura_open"):

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
            st.session_state.modal_factura_open = False
            st.rerun()

    modal_factura()

# =================================
# BUSCAR
# =================================
st.divider()
st.subheader("Buscar Pase de Taller")

empresas = sorted(pases_df["Empresa"].dropna().unique()) if not pases_df.empty else []

f1, f2, f3, f4, f5 = st.columns(5)

with f1:
    f_folio = st.text_input("No. de Folio")

with f2:
    unidades = (
        sorted(
            pases_df["No. de Unidad"]
            .dropna()
            .astype(str)
            .unique()
        )
        if not pases_df.empty and "No. de Unidad" in pases_df.columns
        else []
    )

    f_unidad = st.selectbox(
        "No. de Unidad",
        ["Selecciona unidad"] + unidades
    )

with f3:
    f_empresa = st.selectbox("Empresa", ["Selecciona empresa"] + empresas)

with f4:
    f_estado = st.selectbox(
        "Estado",
        [
            "Selecciona estado",
            "Inicio / Nuevo",
            "En Curso / Proceso",
            "Cerrado / Terminado",
            "Cerrado / Cancelado",
        ]
    )

with f5:
    f_fecha = st.date_input("Fecha de Captura", value=None)

if st.button("Buscar"):
    st.session_state.buscar_trigger = True
    st.session_state.modal_reporte = None
    st.session_state.modal_factura = None
    st.session_state.modal_factura_open = False

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

    if f_unidad != "Selecciona unidad":
        resultados = resultados[
            resultados["No. de Unidad"].astype(str) == f_unidad]

    if f_fecha:
        resultados = resultados[resultados["Fecha"].dt.date == f_fecha]

    st.divider()
    st.subheader("Resultados")

    for _, row in resultados.iterrows():
        c1, c2, c3, c4, c5, c6, c7, c8 = st.columns([1,2,2,2,2,3,2,1])

        editable = row["Estado"] in [
            "Inicio / Nuevo",
            "En Curso / Proceso"
        ]

        # ======================================================
        # BUTTON COLUMN
        # ======================================================
        with c1:
            label = "Editar" if editable else "Ver"
            if st.button(label, key=f"accion_{row['NoFolio']}"):

                st.session_state.modal_factura = None
                st.session_state.modal_factura_open = False

                st.session_state.modal_reporte = row.to_dict()

                df = cargar_servicios_folio(row["NoFolio"])

                st.session_state.servicios_df = df

        # ======================================================
        # INFO COLUMNS (UNCHANGED)
        # ======================================================
        c2.write(row["NoFolio"])
        c3.write(row.get("No. de Unidad", ""))
        c4.write(row["Empresa"])
        c5.write(row["Proveedor"])
        c6.write(row["Estado"])

        descripcion = row.get("Descripcion Problema", "")
        if isinstance(descripcion, str) and len(descripcion) > 80:
            descripcion = descripcion[:80] + "..."

        c7.write(descripcion)

        c8.write(row["Fecha"].date() if pd.notna(row["Fecha"]) else "")

# =================================
# MODAL
# =================================
if st.session_state.modal_reporte:

    r = st.session_state.modal_reporte
    editable_estado = r["Estado"] in [
        "Inicio / Nuevo",
        "En Curso / Proceso"
    ]

    @st.dialog("Detalle del Pase de Taller")
    def modal():

        st.markdown(f"**No. de Folio:** {r.get('NoFolio', r.get('No. de Folio',''))}")
        st.markdown(f"**Empresa:** {r['Empresa']}")
        fecha_modal = r.get("Fecha")
        if pd.notna(fecha_modal):
            try:
                fecha_modal = pd.to_datetime(fecha_modal).strftime("%Y-%m-%d %H:%M")
            except:
                fecha_modal = str(fecha_modal)
        else:
            fecha_modal = "-"

        st.markdown(f"**Fecha:** {fecha_modal}")
        st.markdown(f"**Capturó:** {r.get('Capturo', '')}")
        st.markdown(f"**Proveedor:** {r['Proveedor']}")
        st.markdown(f"**No. de Unidad:** {r.get('No. de Unidad', '')}")
        descripcion_actual = r.get("Descripcion Problema", "") or ""
        es_cerrado = r["Estado"].startswith("Cerrado")
        descripcion_editada = st.text_area(
            "Descripción del Problema",
            value=descripcion_actual,
            height=120,
            disabled=es_cerrado
        )

        st.divider()
        st.subheader("Información del Proveedor")

        es_cerrado = "Cerrado" in str(r.get("Estado", ""))

        proveedor = (r.get("Proveedor") or "").lower()

        # ==========================================
        # NO. DE ORDEN (editable + no decimals)
        # ==========================================
        reporte_actual = r.get("No. de Reporte", "")

        if pd.notna(reporte_actual) and str(reporte_actual).strip() != "":
            try:
                reporte_actual = str(int(float(reporte_actual)))
            except:
                reporte_actual = str(reporte_actual).strip()
        else:
            reporte_actual = ""

        reporte_editado = st.text_input(
            "No. de Reporte",
            value=reporte_actual,
            disabled=es_cerrado
        )

        # ==========================================
        # OSTE (externo only)
        # editable until order is Cerrado
        # ==========================================
        if "interno" not in proveedor:
            oste_val = st.text_input(
                "OSTE",
                value=clean(r.get("Oste", "")),
                disabled=es_cerrado
            )

        # ==========================================
        # SMART STATE VISIBILITY
        # ==========================================
        estado_actual = r["Estado"]

        transiciones = {
            "Inicio / Nuevo": [
                "En Curso / Proceso",
                "Cerrado / Cancelado",
            ],
            "En Curso / Proceso": [
                "Cerrado / Terminado",
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

        editable_servicios = nuevo_estado == "En Curso / Proceso"

        st.divider()
        st.subheader("Servicios y Refacciones")

        catalogo = cargar_refacciones()

        # ==========================================
        # BUILD TIPO FILTER
        # ==========================================
        tipos_disponibles = []

        if catalogo is not None and not catalogo.empty:
            tipos_disponibles = (
                sorted(
                    catalogo["Tipo"]
                    .dropna()
                    .astype(str)
                    .unique()
                )
            )

        if catalogo is not None and not catalogo.empty:
            # ==========================================
            # TIPO FILTER SELECTBOX
            # ==========================================
            tipo_seleccionado = st.selectbox(
                "Tipo",
                ["Selecciona tipo"] + tipos_disponibles,
                disabled=not editable_servicios
            )

            # ==========================================
            # FILTER PARTES BASED ON TIPO
            # ==========================================
            if tipo_seleccionado != "Selecciona tipo":
                catalogo_filtrado = catalogo[
                    catalogo["Tipo"] == tipo_seleccionado
                ]
            else:
                catalogo_filtrado = catalogo

            partes_opciones = (
                catalogo_filtrado["Parte"]
                .dropna()
                .astype(str)
                .tolist()
            )

            tipo_elegido = tipo_seleccionado != "Selecciona tipo"

            st.session_state.refaccion_seleccionada = st.selectbox(
                "Refacción / Servicio",
                options=partes_opciones if tipo_elegido else [],
                index=None,
                disabled=(not editable_servicios or not tipo_elegido)
            )

        else:
            st.info("Catálogo no disponible para esta empresa.")

        # =====================================================
        # ADD ITEM
        # =====================================================
        if st.button(
            "Agregar refacción",
            disabled=not editable_servicios or not st.session_state.refaccion_seleccionada
        ):

            parte_seleccionada = st.session_state.refaccion_seleccionada

            fila = catalogo[
                catalogo["Parte"] == parte_seleccionada
            ].iloc[0]

            if fila["Parte"] not in st.session_state.servicios_df["Parte"].values:

                nueva = {
                    "Parte": fila["Parte"],
                    "Tipo De Parte": fila["Tipo"],
                    "Posicion": "",
                    "Cantidad": 1,
                }

                st.session_state.servicios_df = pd.concat(
                    [st.session_state.servicios_df, pd.DataFrame([nueva])],
                    ignore_index=True
                )

        # =====================================================
        # EDITOR
        # =====================================================
        column_config = {
            "Parte": st.column_config.TextColumn(required=False),
            "Tipo De Parte": st.column_config.TextColumn(required=False),
            "Posicion": st.column_config.TextColumn(),
            "Cantidad": st.column_config.NumberColumn(min_value=1, step=1),
        }

        edited_df = st.data_editor(
            st.session_state.servicios_df,
            num_rows="dynamic",
            hide_index=True,
            disabled=not editable_servicios,
            column_config=column_config,
        )

        # =====================================================
        # METRIC
        # =====================================================
        st.divider()
        c1, c2 = st.columns(2)

        with c1:
            if st.button("Cancelar"):
                st.session_state.modal_reporte = None
                st.rerun()

        with c2:

            mostrar_aceptar = True

            label_btn = "Guardar cambios" if editable_estado else "Cerrar"

            if mostrar_aceptar and st.button(label_btn, type="primary"):

                usuario = (
                    st.session_state.user.get("name")
                    or st.session_state.user.get("email")
                )
  
                # =================================
                # UPDATE DESCRIPCION IF CHANGED
                # =================================
                descripcion_original = descripcion_actual or ""
                descripcion_nueva = descripcion_editada or ""

                if descripcion_nueva.strip() != descripcion_original.strip():

                    actualizar_descripcion_pase(
                        r["Empresa"],
                        r["NoFolio"],
                        descripcion_nueva.strip()
                    )

                    registrar_cambio_log(
                        usuario=usuario,
                        empresa=r["Empresa"],
                        folio=r["NoFolio"],
                        tipo_cambio="Edición Descripción",
                        estado_anterior=r["Estado"],
                        estado_nuevo=r["Estado"],
                        comentario="Descripción modificada"
                    )

                estado_actual = r["Estado"]

                if nuevo_estado != estado_actual:

                    actualizar_estado_pase(
                        r["Empresa"],
                        r["NoFolio"],
                        nuevo_estado
                    )

                    registrar_cambio_log(
                        usuario=usuario,
                        empresa=r["Empresa"],
                        folio=r["NoFolio"],
                        tipo_cambio="Cambio Estado",
                        estado_anterior=estado_actual,
                        estado_nuevo=nuevo_estado,
                        oste_anterior=clean(r.get("Oste")),
                        oste_nuevo=clean(r.get("Oste"))
                    )

                if "interno" not in proveedor:
                    if oste_val.strip() != clean(r.get("Oste")):

                        oste_anterior = clean(r.get("Oste"))
                        oste_nuevo = clean(oste_val)

                        actualizar_oste_pase(
                            r["Empresa"],
                            r["NoFolio"],
                            oste_nuevo
                        )

                        registrar_cambio_log(
                            usuario=usuario,
                            empresa=r["Empresa"],
                            folio=r["NoFolio"],
                            tipo_cambio="Actualización OSTE",
                            estado_anterior=nuevo_estado,
                            estado_nuevo=nuevo_estado,
                            oste_anterior=oste_anterior,
                            oste_nuevo=oste_nuevo
                        )
                    
                # =================================
                # UPDATE NO. DE REPORTE IF CHANGED
                # =================================
                reporte_original = clean(
                    r.get("No. de Reporte", "")
                )

                try:
                    reporte_original = str(int(float(reporte_original))) if reporte_original else ""
                except:
                    reporte_original = str(reporte_original).strip()

                reporte_nuevo = clean(reporte_editado)

                try:
                    reporte_nuevo = str(int(float(reporte_nuevo))) if reporte_nuevo else ""
                except:
                    reporte_nuevo = str(reporte_nuevo).strip()

                if reporte_nuevo != reporte_original:

                    actualizar_no_reporte_pase(
                        r["Empresa"],
                        r["NoFolio"],
                        reporte_nuevo
                    )

                    registrar_cambio_log(
                        usuario=usuario,
                        empresa=r["Empresa"],
                        folio=r["NoFolio"],
                        tipo_cambio="Actualización No. de Reporte",
                        estado_anterior=r["Estado"],
                        estado_nuevo=r["Estado"],
                        comentario=f"No. de Reporte actualizado: {reporte_original} → {reporte_nuevo}"
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

                # Normalize edited dataframe
                df_final = edited_df.copy()

                # Ensure columns exist
                if "Tipo De Parte" in df_final.columns:
                    df_final["Tipo De Parte"] = (
                        df_final["Tipo De Parte"]
                        .fillna("")
                        .astype(str)
                        .str.strip()
                    )

                    # If empty → default to Mano de Obra
                    df_final.loc[
                        df_final["Tipo De Parte"] == "",
                        "Tipo De Parte"
                    ] = "Mano de Obra"

                # Clean Parte column as well
                if "Parte" in df_final.columns:
                    df_final["Parte"] = (
                        df_final["Parte"]
                        .fillna("")
                        .astype(str)
                        .str.strip()
                    )

                st.session_state.servicios_df = df_final

                guardar_servicios_refacciones(
                    r["NoFolio"],
                    usuario,
                    st.session_state.servicios_df,
                    nuevo_estado
                )
                
                st.session_state.modal_reporte = None
                st.cache_data.clear()
                st.rerun()

    modal()
    st.session_state.modal_reporte = None