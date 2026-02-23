import streamlit as st
import pandas as pd
from datetime import datetime, date
import gspread
from google.oauth2.service_account import Credentials
import os
from auth import require_login, require_access

# =================================
# Page configuration
# =================================
st.set_page_config(
    page_title="Consulta de Reportes",
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
require_access("consulta_reportes")

# =================================
# Defensive reset on page entry
# =================================
if st.session_state.get("_reset_consulta_page", True):
    st.session_state.modal_reporte = None
    st.session_state["_reset_consulta_page"] = False


#Modal state initialization
st.session_state.setdefault("modal_reporte", None)

# =================================
# Navigation
# =================================
if st.button("⬅ Volver al Dashboard"):
    st.session_state["_reset_consulta_page"] = True
    st.switch_page("pages/dashboard.py")

st.divider()
st.title("📊 Consulta de Reportes")

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
    except Exception:
        pass

    if os.path.exists("google_service_account.json"):
        return Credentials.from_service_account_file(
            "google_service_account.json", scopes=scopes
        )

    raise RuntimeError("Google Sheets credentials not found")

SPREADSHEET_ID = "1ca46k4PCbvNMvZjsgU_2MHJULADRJS5fnghLopSWGDA"

# =================================
# Load PASES (ALL COMPANIES)
# =================================
@st.cache_data(ttl=300)
def cargar_pases():
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
    df.columns = df.columns.str.strip()

    if "No. de Folio" in df.columns:
        df = df.rename(columns={"No. de Folio": "Folio"})

    df["Folio"] = df["Folio"].astype(str)

    for col in ["Fecha de Captura", "Fecha de Reporte"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    return df

# =================================
# Load SERVICES
# =================================
@st.cache_data(ttl=300)
def cargar_servicios():
    client = gspread.authorize(get_gsheets_credentials())
    ws = client.open_by_key(SPREADSHEET_ID).worksheet("SERVICES")

    data = ws.get_all_records()
    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)
    df.columns = df.columns.str.strip()

    if "No. de Folio" in df.columns:
        df = df.rename(columns={"No. de Folio": "Folio"})
    if "Iva" in df.columns:
        df = df.rename(columns={"Iva": "IVA"})

    df["Folio"] = df["Folio"].astype(str)

    if "Fecha Mod" in df.columns:
        df["Fecha Mod"] = pd.to_datetime(df["Fecha Mod"], errors="coerce")

    return df

df_pases = cargar_pases()
df_services = cargar_servicios()

# =================================
# KPI STRIP (GLOBAL)
# =================================

if df_pases.empty:
    st.info("No hay información disponible.")
    st.stop()

st.markdown("### Resumen general")

total_ordenes = len(df_pases)

def porcentaje(n):
    if total_ordenes == 0:
        return 0
    return round((n / total_ordenes) * 100, 1)

pendientes = len(df_pases[df_pases["Estado"] == "En Curso / Nuevo"])

diagnosticos = len(
    df_pases[df_pases["Estado"] == "En Curso / Autorizado"]
)

en_proceso = len(
    df_pases[df_pases["Estado"].isin([
        "En Curso / Sin Comenzar",
        "En Curso / Espera Refacciones",
        "En Curso / En Proceso",
    ])]
)

completadas = len(
    df_pases[df_pases["Estado"].isin([
        "Cerrado / Completado",
        "Cerrado / Facturado",
    ])]
)

canceladas = len(
    df_pases[df_pases["Estado"] == "Cerrado / Cancelado"]
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
# LAST 5 CHANGES (POST ITS)
# =================================
st.divider()
st.subheader("🕘 Últimos 5 cambios")

import streamlit.components.v1 as components

def safe(x):
    if pd.isna(x) or x is None:
        return ""
    return str(x)

if not df_services.empty and "Fecha Mod" in df_services.columns:

    ultimos = (
        df_services
        .sort_values("Fecha Mod", ascending=False)
        .drop_duplicates("Folio")
        .head(5)
    )

    if ultimos.empty:
        st.info("No hay actividad reciente.")
    else:
        cols = st.columns(5)

        for i, (_, srow) in enumerate(ultimos.iterrows()):
            col = cols[i]

            folio = safe(srow["Folio"])

            # find info in pases
            match = df_pases[df_pases["Folio"] == folio]

            if match.empty:
                continue

            r = match.iloc[0]

            with col:
                tipo_unidad = safe(r.get("Tipo de Unidad"))
                fecha = r.get("Fecha de Captura")
                fecha = fecha.date() if pd.notna(fecha) else ""
                unidad = safe(r.get("No. de Unidad"))
                estado = safe(r.get("Estado"))
                capturo = safe(r.get("Capturo"))
                descripcion = safe(r.get("Descripcion Problema"))

                if len(descripcion) > 120:
                    descripcion = descripcion[:120] + "..."

                html = f"""
                <div style="padding:6px;">
                    <div style="
                        background:#e8f0ff;
                        padding:14px;
                        border-radius:16px;
                        box-shadow:0 4px 10px rgba(0,0,0,0.08);
                        color:#111;
                        min-height:22-px;
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
                            color:#1e40af;
                        ">
                            {estado}
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

                components.html(html, height=260)

                # =====================================
                # VIEW BUTTON
                # =====================================
                if st.button("👁 Ver", key=f"view_last_{folio}", use_container_width=True):
                    st.session_state.modal_reporte = r.to_dict()

else:
    st.info("No hay actividad reciente.")

st.divider()

# =================================
# FILTERS
# =================================
st.subheader("Filtros")

# =========================================================
# SECTION 1 → MAIN DATA
# =========================================================
r1c1, r1c2, r1c3 = st.columns(3)

with r1c1:
    folio = st.text_input("No. de Folio")

with r1c2:
    no_reporte = st.text_input("No. de Reporte")

with r1c3:
    oste = st.text_input("OSTE")


r2c1, r2c2, r2c3 = st.columns(3)

with r2c1:
    empresa = st.selectbox(
        "Empresa",
        ["Todas"] + sorted(df_pases["Empresa"].dropna().unique().tolist())
        if not df_pases.empty else ["Todas"]
    )

with r2c2:
    no_unidad = st.selectbox(
        "No. de Unidad",
        ["Todas"] + sorted(df_pases["No. de Unidad"].dropna().astype(str).unique().tolist())
        if "No. de Unidad" in df_pases.columns else ["Todas"]
    )

with r2c3:
    estado = st.selectbox(
        "Estado",
        ["Todos"] + sorted(df_pases["Estado"].dropna().unique().tolist())
        if not df_pases.empty else ["Todos"]
    )

# =========================================================
# SECTION 2 → DATE FILTERS (COLLAPSIBLE)
# =========================================================
with st.expander("📅 Filtrar por fechas", expanded=False):

    d1, d2, d3 = st.columns(3)

    with d1:
        fecha_mod = st.date_input("Fecha Mod", value=None)

    with d2:
        fecha_aut = st.date_input("Fecha Autorizado", value=None)

    with d3:
        fecha_sin = st.date_input("Fecha Sin Comenzar", value=None)


    d4, d5, d6 = st.columns(3)

    with d4:
        fecha_espera = st.date_input("Fecha Espera Refacciones", value=None)

    with d5:
        fecha_proceso = st.date_input("Fecha En Proceso", value=None)

    with d6:
        fecha_fact = st.date_input("Fecha Facturado", value=None)


    d7, d8 = st.columns(2)

    with d7:
        fecha_comp = st.date_input("Fecha Completado", value=None)

    with d8:
        fecha_cancel = st.date_input("Fecha Cancelado", value=None)

c1, c2 = st.columns([1,1])

with c1:
    buscar = st.button("🔍 Aplicar filtros", type="primary", use_container_width=True)

with c2:
    if st.button("🧹 Borrar filtros", use_container_width=True):
        st.session_state.pop("df_filtrado_pases", None)
        st.session_state.pop("df_filtrado_servicios", None)
        st.session_state.modal_reporte = None
        st.rerun()

# =================================
# APPLY FILTERS
# =================================
if buscar:
    st.session_state.modal_reporte = None
    df_p = df_pases.copy()
    df_s = df_services.copy()

    # ======================================================
    # BASIC INFO (PASES)
    # ======================================================

    if folio:
        df_p = df_p[df_p["Folio"].astype(str).str.contains(folio, na=False)]

    if empresa != "Todas":
        df_p = df_p[df_p["Empresa"] == empresa]

    if estado != "Todos":
        df_p = df_p[df_p["Estado"] == estado]

    if no_unidad != "Todas" and "No. de Unidad" in df_p.columns:
        df_p = df_p[df_p["No. de Unidad"].astype(str) == no_unidad]

    if no_reporte and "No. de Reporte" in df_p.columns:
        df_p = df_p[df_p["No. de Reporte"].astype(str).str.contains(no_reporte, na=False)]

    if oste and "Oste" in df_p.columns:
        df_p = df_p[df_p["Oste"].astype(str).str.contains(oste, na=False)]

    # ======================================================
    # DATE FILTERS (SERVICES)
    # ======================================================

    def filtrar_fecha(df, columna, valor):
        if valor and columna in df.columns:
            df = df[df[columna].dt.date == valor]
        return df

    df_s = filtrar_fecha(df_s, "Fecha Mod", fecha_mod)
    df_s = filtrar_fecha(df_s, "Fecha Autorizado", fecha_aut)
    df_s = filtrar_fecha(df_s, "Fecha Sin Comenzar", fecha_sin)
    df_s = filtrar_fecha(df_s, "Fecha Espera Refacciones", fecha_espera)
    df_s = filtrar_fecha(df_s, "Fecha En Proceso", fecha_proceso)
    df_s = filtrar_fecha(df_s, "Fecha Facturado", fecha_fact)
    df_s = filtrar_fecha(df_s, "Fecha Completado", fecha_comp)
    df_s = filtrar_fecha(df_s, "Fecha Cancelado", fecha_cancel)

    # ======================================================
    # MATCH SERVICES → PASES
    # ======================================================
    if (
        fecha_mod or fecha_aut or fecha_sin or fecha_espera
        or fecha_proceso or fecha_fact or fecha_comp or fecha_cancel
    ):
        folios_validos = df_s["Folio"].unique()
        df_p = df_p[df_p["Folio"].isin(folios_validos)]

    st.session_state.df_filtrado_pases = df_p
    st.session_state.df_filtrado_servicios = df_s

# ======================================================
# TABLE 1 — REPORTE DETALLADO
# ======================================================

# use filtered data if available
df_p = st.session_state.get("df_filtrado_pases", df_pases.copy())
df_s = st.session_state.get("df_filtrado_servicios", df_services.copy())

# remove service log rows (no part)
if "Parte" in df_s.columns:
    df_s = df_s[
        df_s["Parte"].notna() &
        (df_s["Parte"].astype(str).str.strip() != "")
    ]

# merge → one row per servicio
df_detallado = df_p.merge(df_s, on="Folio", how="left")

st.divider()
st.subheader("📄 Reporte Detallado")

# EXACT columns you requested
columnas = [
    # ===== COMPANY TAB =====
    "Fecha de Captura",
    "No. de Folio",
    "Fecha de Reporte",
    "Tipo de Proveedor",
    "Estado",
    "Capturo",
    "Oste",
    "No. de Reporte",
    "Empresa",
    "Tipo de Reporte",
    "Tipo de Unidad",
    "Operador",
    "No. de Unidad",
    "Marca",
    "Modelo",
    "Sucursal",
    "Tipo de Caja",
    "No. de Unidad Externo",
    "Nombre Linea Externa",
    "Cobro",
    "Responsable",
    "Descripcion Problema",
    "Multa",
    "No. de Inspeccion",
    "Reparacion Multa",

    # ===== SERVICES =====
    "Modifico",
    "Parte",
    "Tipo De Parte",
    "PU",
    "IVA",
    "Cantidad",
    "Total",
    "Fecha Mod",
    "Fecha Autorizado",
    "Fecha Sin Comenzar",
    "Fecha Espera Refacciones",
    "Fecha En Proceso",
    "Fecha Facturado",
    "Fecha Completado",
    "Fecha Cancelado",
]

# FIRST rename
df_detallado = df_detallado.rename(columns={
    "Folio": "No. de Folio"
})

# THEN validate columns
columnas = [c for c in columnas if c in df_detallado.columns]


st.dataframe(
    df_detallado[columnas],
    hide_index=True,
    width="stretch"
)

# ======================================================
# TABLE 2 — RESUMEN POR ORDEN (1 LINE PER FOLIO)
# ======================================================
st.divider()
st.subheader("📦 Resumen por Orden")

df_s = df_s.copy()

# remove log rows
if "Parte" in df_s.columns:
    df_s = df_s[
        df_s["Parte"].notna() &
        (df_s["Parte"].astype(str).str.strip() != "")
    ]

if df_s.empty:
    st.info("Sin servicios.")
else:

    # ===============================
    # AGGREGATE SERVICES
    # ===============================
    servicios_agg = (
        df_s
        .groupby("Folio", as_index=False)
        .agg({
            # concatenate parts
            "Parte": lambda x: ", ".join(
                sorted(set(str(v) for v in x if pd.notna(v)))
            ),

            # sum totals
            "Total": lambda x: pd.to_numeric(
                x, errors="coerce"
            ).fillna(0).sum(),

            # latest dates
            "Fecha Mod": "max",
            "Fecha Autorizado": "max",
            "Fecha Sin Comenzar": "max",
            "Fecha Espera Refacciones": "max",
            "Fecha En Proceso": "max",
            "Fecha Facturado": "max",
            "Fecha Completado": "max",
            "Fecha Cancelado": "max",
        })
        .rename(columns={
            "Parte": "Partes",
            "Total": "Total Servicio",
        })
    )

    # ===============================
    # MERGE WITH COMPANY DATA
    # ===============================
    df_resumen = df_p.merge(servicios_agg, on="Folio", how="left")

    df_resumen["Partes"] = df_resumen["Partes"].fillna("")
    df_resumen["Total Servicio"] = df_resumen["Total Servicio"].fillna(0)

    # ===============================
    # COLUMN ORDER
    # ===============================
    columnas = [
        # ===== COMPANY TAB =====
        "Fecha de Captura",
        "No. de Folio",
        "Fecha de Reporte",
        "Tipo de Proveedor",
        "Estado",
        "Capturo",
        "Oste",
        "No. de Reporte",
        "Empresa",
        "Tipo de Reporte",
        "Tipo de Unidad",
        "Operador",
        "No. de Unidad",
        "Marca",
        "Modelo",
        "Sucursal",
        "Tipo de Caja",
        "No. de Unidad Externo",
        "Nombre Linea Externa",
        "Cobro",
        "Responsable",
        "Descripcion Problema",
        "Multa",
        "No. de Inspeccion",
        "Reparacion Multa",

        # ===== CONSOLIDATED SERVICES =====
        "Modifico",
        "Partes",
        "Cantidad",  # will remain if exists in merge
        "Total Servicio",
        "Fecha Mod",
        "Fecha Autorizado",
        "Fecha Sin Comenzar",
        "Fecha Espera Refacciones",
        "Fecha En Proceso",
        "Fecha Facturado",
        "Fecha Completado",
        "Fecha Cancelado",
    ]

    # FIRST rename
    df_resumen = df_resumen.rename(columns={
        "Folio": "No. de Folio"
    })

    # THEN validate
    columnas = [c for c in columnas if c in df_resumen.columns]

    st.dataframe(
        df_resumen[columnas],
        hide_index=True,
        width="stretch"
    )

# =================================
# VIEW MODAL (READ ONLY)
# =================================
if st.session_state.get("modal_reporte"):

    r = st.session_state.modal_reporte
    folio = str(r.get("Folio"))

    @st.dialog("Detalle del Pase de Taller")
    def modal_ver():

        # =================================
        # STATUS CAPSULE
        # =================================
        estado = r.get("Estado", "")

        color_map = {
            "En Curso / Nuevo": "#856404",
            "En Curso / Autorizado": "#0c5460",
            "En Curso / Sin Comenzar": "#383d41",
            "En Curso / Espera Refacciones": "#5a189a",
            "En Curso / En Proceso": "#4f46e5",
            "Cerrado / Completado": "#155724",
            "Cerrado / Facturado": "#155724",
            "Cerrado / Cancelado": "#721c24",
        }

        bg_map = {
            "En Curso / Nuevo": "#fff3cd",
            "En Curso / Autorizado": "#d1ecf1",
            "En Curso / Sin Comenzar": "#e2e3e5",
            "En Curso / Espera Refacciones": "#e2d9f3",
            "En Curso / En Proceso": "#e0e7ff",
            "Cerrado / Completado": "#d4edda",
            "Cerrado / Facturado": "#d4edda",
            "Cerrado / Cancelado": "#f8d7da",
        }

        st.markdown(
            f"""
            <div style="
                display:inline-block;
                padding:6px 12px;
                border-radius:999px;
                font-weight:700;
                background:{bg_map.get(estado, '#eee')};
                color:{color_map.get(estado, '#111')};
                margin-bottom:10px;
            ">
                {estado}
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown(f"**No. de Folio:** {folio}")
        st.markdown(f"**Proveedor:** {r.get('Tipo de Proveedor','')}")
        st.markdown(f"**No. de Unidad:** {r.get('No. de Unidad','')}")
        st.markdown(f"**Sucursal:** {r.get('Sucursal','')}")

        # ===============================
        # LAST MOD DATE (FROM SERVICES)
        # ===============================
        df_folio = df_services[df_services["Folio"] == folio]

        # REMOVE LOG / EMPTY ROWS
        if "Parte" in df_folio.columns:
            df_folio = df_folio[
                df_folio["Parte"].notna() &
                (df_folio["Parte"].astype(str).str.strip() != "")
            ]

        if not df_folio.empty and "Fecha Mod" in df_folio.columns:
            fecha_mod = df_folio["Fecha Mod"].max()
            st.markdown(f"**Fecha Mod:** {fecha_mod}")
        else:
            st.markdown("**Fecha Mod:** -")

        descripcion = r.get("Descripcion Problema", "")

        st.markdown("**Descripción del Problema:**")
        if descripcion:
            st.markdown(
                f"""
                <div style="
                    background:#f1f5f9;
                    padding:12px;
                    border-radius:10px;
                    margin-bottom:12px;
                    color:#111;
                    font-size:0.9rem;
                    line-height:1.4;
                ">
                    {descripcion}
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.markdown("-")

        st.divider()

        proveedor = (r.get("Tipo de Proveedor") or "").lower()

        st.subheader("Información del proveedor")

        if "interno" in proveedor:
            st.markdown(f"**No. de Reporte:** {r.get('No. de Reporte','')}")
        else:
            st.markdown(f"**OSTE:** {r.get('Oste','')}")

        st.divider()
        st.subheader("Servicios y Refacciones")

        if df_folio.empty:
            st.info("Sin servicios registrados.")
        else:
            # show unified structure for all companies
            cols = ["Parte","Tipo De Parte","PU","IVA","Cantidad","Total"]
            cols = [c for c in cols if c in df_folio.columns]

            st.dataframe(
                df_folio[cols],
                hide_index=True,
                width="stretch"
            )

            total = pd.to_numeric(df_folio.get("Total", 0), errors="coerce").fillna(0).sum()

            empresa = r.get("Empresa", "")

            if empresa in ["IGLOO TRANSPORT", "PICUS"]:
                moneda = "MXN"
            else:
                moneda = "USD"

            st.metric(f"Total ({moneda})", f"$ {total:,.2f}")

        st.divider()

        if st.button("Cerrar"):
            st.session_state.modal_reporte = None
            st.rerun()

    modal_ver()