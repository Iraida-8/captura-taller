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
        return pd.DataFrame(columns=[
            "Folio",
            "Modifico",
            "Parte",
            "Tipo De Parte",
            "Posicion",
            "Cantidad",
            "Fecha Mod",
            "Fecha Diagnostico",
            "Fecha No Diagnosticado",
            "Fecha En Reparacion",
            "Fecha Espera Refaccion",
            "Fecha Resuelto",
            "Fecha Terminado",
            "Fecha Concluido",
            "Fecha Cancelado",
        ])

    df = pd.DataFrame(data)
    df.columns = df.columns.str.strip()

    # Rename Folio
    if "No. de Folio" in df.columns:
        df = df.rename(columns={"No. de Folio": "Folio"})

    # Ensure Folio is string
    if "Folio" in df.columns:
        df["Folio"] = df["Folio"].astype(str)

    # Convert ALL date columns safely
    date_cols = [
        "Fecha Mod",
        "Fecha Diagnostico",
        "Fecha No Diagnosticado",
        "Fecha En Reparacion",
        "Fecha Espera Refaccion",
        "Fecha Resuelto",
        "Fecha Terminado",
        "Fecha Concluido",
        "Fecha Cancelado",
    ]

    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    return df

# =================================
# Load FACTURAS
# =================================
@st.cache_data(ttl=300)
def cargar_facturas():
    client = gspread.authorize(get_gsheets_credentials())
    ws = client.open_by_key(SPREADSHEET_ID).worksheet("FACTURAS")

    data = ws.get_all_records()

    # If sheet is empty, create structure manually
    if not data:
        return pd.DataFrame(columns=["Folio", "No. de Factura"])

    df = pd.DataFrame(data)
    df.columns = df.columns.str.strip()

    if "No. de Folio" in df.columns:
        df = df.rename(columns={"No. de Folio": "Folio"})

    df["Folio"] = df["Folio"].astype(str)

    return df

df_pases = cargar_pases()
df_services = cargar_servicios()
df_facturas = cargar_facturas()

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

pendientes = len(
    df_pases[df_pases["Estado"] == "En Curso / Nuevo"]
)

diagnosticos = len(
    df_pases[df_pases["Estado"].isin([
        "En Curso / Autorizado",
        "En Curso / Sin Comenzar",
    ])]
)

en_proceso = len(
    df_pases[df_pases["Estado"].isin([
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
        num = min(len(ultimos), 5)
        cols = st.columns(num)

        for i, (_, srow) in enumerate(ultimos.iterrows()):
            col = cols[i]

            folio = safe(srow["Folio"])

            # find info in pases
            match = df_pases[df_pases["Folio"] == folio]

            if match.empty:
                continue

            r = match.iloc[0]

            # ===== FACTURA LOOKUP =====
            df_factura_folio = df_facturas[df_facturas["Folio"] == folio]

            if not df_factura_folio.empty:
                no_factura = df_factura_folio.iloc[0].get("No. de Factura", "")
            else:
                no_factura = ""

            with col:
                tipo_unidad = safe(r.get("Tipo de Unidad"))
                fecha = r.get("Fecha de Captura")
                oste_val = safe(r.get("Oste"))
                orden_val = safe(r.get("No. de Reporte"))
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
                        min-height:220px;
                        font-family:sans-serif;
                    ">
                        <div style="font-weight:900;">{folio}</div>
                        <div style="font-size:0.8rem;">{tipo_unidad}</div>
                        <div style="font-size:0.8rem;">{fecha}</div>

                        <hr style="margin:6px 0">

                        <div style="font-size:0.8rem;">{unidad}</div>

                        <div style="font-size:0.75rem; margin-top:4px;">
                            <strong>OSTE:</strong> {oste_val if oste_val else "-"}
                        </div>

                        <div style="font-size:0.75rem;">
                            <strong>No. Orden:</strong> {orden_val if orden_val else "-"}
                        </div>

                        <div style="font-size:0.75rem;">
                            <strong>Factura:</strong> {no_factura if no_factura else "-"}
                        </div>

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

# Close any open modal before running filters
if st.session_state.get("modal_reporte") and st.session_state.get("filtros_aplicados"):
    st.session_state.modal_reporte = None

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

    ESTADOS = [
        "En Curso / Nuevo",
        "En Curso / Autorizado",
        "En Curso / Sin Comenzar",
        "En Curso / Espera Refacciones",
        "En Curso / En Proceso",
        "Cerrado / Completado",
        "Cerrado / Facturado",
        "Cerrado / Cancelado",
    ]

    estado = st.selectbox(
        "Estado",
        ["Todos"] + ESTADOS
    )

# =========================================================
# SECTION 2 → DATE FILTERS (COLLAPSIBLE)
# =========================================================
with st.expander("📅 Filtrar por fechas", expanded=False):

    d1, d2, d3 = st.columns(3)

    with d1:
        fecha_mod = st.date_input("Fecha Mod", value=None)

    with d2:
        fecha_diag = st.date_input("Fecha Diagnostico", value=None)

    with d3:
        fecha_no_diag = st.date_input("Fecha No Diagnosticado", value=None)

    d4, d5, d6 = st.columns(3)

    with d4:
        fecha_reparacion = st.date_input("Fecha En Reparacion", value=None)

    with d5:
        fecha_espera = st.date_input("Fecha Espera Refaccion", value=None)

    with d6:
        fecha_resuelto = st.date_input("Fecha Resuelto", value=None)

    d7, d8 = st.columns(2)

    with d7:
        fecha_terminado = st.date_input("Fecha Terminado", value=None)

    with d8:
        fecha_concluido = st.date_input("Fecha Concluido", value=None)

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

# Ensure default flag exists
st.session_state.setdefault("filtros_aplicados", False)

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

    df_s = filtrar_fecha(df_s, "Fecha Diagnostico", fecha_diag)
    df_s = filtrar_fecha(df_s, "Fecha No Diagnosticado", fecha_no_diag)
    df_s = filtrar_fecha(df_s, "Fecha En Reparacion", fecha_reparacion)
    df_s = filtrar_fecha(df_s, "Fecha Espera Refaccion", fecha_espera)
    df_s = filtrar_fecha(df_s, "Fecha Resuelto", fecha_resuelto)
    df_s = filtrar_fecha(df_s, "Fecha Terminado", fecha_terminado)
    df_s = filtrar_fecha(df_s, "Fecha Concluido", fecha_concluido)
    df_s = filtrar_fecha(df_s, "Fecha Cancelado", fecha_cancel)

    # ======================================================
    # MATCH SERVICES → PASES
    # ======================================================

    if (
        fecha_diag or fecha_no_diag or fecha_reparacion
        or fecha_espera or fecha_resuelto
        or fecha_terminado or fecha_concluido
        or fecha_cancel
    ):
        folios_validos = df_s["Folio"].unique()
        df_p = df_p[df_p["Folio"].isin(folios_validos)]

    # Save filtered data
    st.session_state.df_filtrado_pases = df_p
    st.session_state.df_filtrado_servicios = df_s

    # ======================================================
    # FILTER FLAG
    # ======================================================

    st.session_state["filtros_aplicados"] = any([
        folio,
        no_reporte,
        oste,
        empresa != "Todas",
        estado != "Todos",
        no_unidad != "Todas",
        fecha_diag,
        fecha_no_diag,
        fecha_reparacion,
        fecha_espera,
        fecha_resuelto,
        fecha_terminado,
        fecha_concluido,
        fecha_cancel
    ])

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

# =================================
# MERGE FACTURAS
# =================================
if "Folio" in df_facturas.columns:
    df_detallado = df_detallado.merge(
        df_facturas[["Folio", "No. de Factura"]],
        on="Folio",
        how="left"
    )
else:
    df_detallado["No. de Factura"] = None


st.subheader("📄 Reporte Detallado")

# =================================
# POSTITS — RESULTADOS FILTRADOS
# =================================

if st.session_state.get("filtros_aplicados"):

    st.divider()
    st.subheader("📌 Órdenes Filtradas")

    df_postits = st.session_state.get("df_filtrado_pases", df_pases.copy())

    if not df_postits.empty:

        df_postits = df_postits.head(25)

        total = len(df_postits)
        rows_needed = min((total - 1) // 5 + 1, 5)

        idx = 0

        for _ in range(rows_needed):

            cols = st.columns(5)

            for col in cols:

                if idx >= total:
                    break

                r = df_postits.iloc[idx]

                folio = str(r.get("Folio", ""))
                tipo_unidad = r.get("Tipo de Unidad", "")
                fecha = r.get("Fecha de Captura")
                unidad = r.get("No. de Unidad", "")
                estado = r.get("Estado", "")
                oste_val = r.get("Oste", "")
                orden_val = r.get("No. de Reporte", "")
                capturo = r.get("Capturo", "")
                descripcion = r.get("Descripcion Problema", "")

                # Format date
                fecha = fecha.date() if pd.notna(fecha) else ""

                # Factura lookup
                df_factura_folio = df_facturas[df_facturas["Folio"] == folio]
                if not df_factura_folio.empty:
                    no_factura = df_factura_folio.iloc[0].get("No. de Factura", "")
                else:
                    no_factura = ""

                # Truncate description
                if descripcion and len(descripcion) > 120:
                    descripcion = descripcion[:120] + "..."

                with col:

                    html = f"""
                    <div style="padding:6px;">
                        <div style="
                            background:#e8f0ff;
                            padding:14px;
                            border-radius:16px;
                            box-shadow:0 4px 10px rgba(0,0,0,0.08);
                            color:#111;
                            min-height:220px;
                            font-family:sans-serif;
                        ">
                            <div style="font-weight:900;">{folio}</div>
                            <div style="font-size:0.8rem;">{tipo_unidad}</div>
                            <div style="font-size:0.8rem;">{fecha}</div>

                            <hr style="margin:6px 0">

                            <div style="font-size:0.8rem;">{unidad}</div>

                            <div style="font-size:0.75rem; margin-top:4px;">
                                <strong>OSTE:</strong> {oste_val if oste_val else "-"}
                            </div>

                            <div style="font-size:0.75rem;">
                                <strong>No. Orden:</strong> {orden_val if orden_val else "-"}
                            </div>

                            <div style="font-size:0.75rem;">
                                <strong>Factura:</strong> {no_factura if no_factura else "-"}
                            </div>

                            <div style="
                                font-size:0.75rem;
                                margin-top:6px;
                                padding:6px;
                                background:#fff;
                                border-radius:8px;
                                box-shadow: inset 0 0 3px rgba(0,0,0,0.05);
                            ">
                                {descripcion if descripcion else "-"}
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

                    if st.button(
                        "👁 Ver",
                        key=f"view_filtro_{folio}_{idx}",
                        use_container_width=True
                    ):
                        st.session_state.modal_reporte = r.to_dict()

                idx += 1

    else:
        st.info("No hay resultados con los filtros aplicados.")

# EXACT columns you requested
columnas = [
    # ===== COMPANY TAB =====
    "Fecha de Captura",
    "No. de Folio",
    "Fecha de Reporte",
    "Tipo de Proveedor",
    "Estado",
    "Capturo",
    "No. de Factura",
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
    "Partes",
    "Fecha Diagnostico",
    "Fecha No Diagnosticado",
    "Fecha En Reparacion",
    "Fecha Espera Refaccion",
    "Fecha Resuelto",
    "Fecha Terminado",
    "Fecha Concluido",
    "Fecha Cancelado",
]

# FIRST rename
df_detallado = df_detallado.rename(columns={
    "Folio": "No. de Folio"
})

# THEN validate columns
columnas = [c for c in columnas if c in df_detallado.columns]

st.divider()
st.subheader("📄 Reporte Detallado")

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
            "Parte": lambda x: ", ".join(
                sorted(set(str(v) for v in x if pd.notna(v)))
            ),

            "Fecha Diagnostico": "max",
            "Fecha No Diagnosticado": "max",
            "Fecha En Reparacion": "max",
            "Fecha Espera Refaccion": "max",
            "Fecha Resuelto": "max",
            "Fecha Terminado": "max",
            "Fecha Concluido": "max",
            "Fecha Cancelado": "max",
        })
        .rename(columns={
            "Parte": "Partes"
        })
    )

    # ===============================
    # MERGE WITH COMPANY DATA
    # ===============================
    df_resumen = df_p.merge(servicios_agg, on="Folio", how="left")

    # =================================
    # MERGE FACTURAS
    # =================================
    if "Folio" in df_facturas.columns:
        df_resumen = df_resumen.merge(
            df_facturas[["Folio", "No. de Factura"]],
            on="Folio",
            how="left"
        )
    else:
        df_resumen["No. de Factura"] = None

    df_resumen["Partes"] = df_resumen["Partes"].fillna("")

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
        "No. de Factura",
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
        "Partes",
        "Fecha Diagnostico",
        "Fecha No Diagnosticado",
        "Fecha En Reparacion",
        "Fecha Espera Refaccion",
        "Fecha Resuelto",
        "Fecha Terminado",
        "Fecha Concluido",
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

#date parse
def fmt_date(value):
    if value is None:
        return "-"
    if pd.isna(value):
        return "-"
    try:
        return pd.to_datetime(value).date()
    except Exception:
        return "-"
    
# =================================
# VIEW MODAL (READ ONLY)
# =================================
if st.session_state.get("modal_reporte"):

    r = st.session_state.modal_reporte
    folio = str(r.get("Folio"))

    @st.dialog("Reporte Completo")
    def modal_ver():

        st.markdown(f"# Folio {folio}")

        # Pull full merged data row
        df_full = df_detallado[df_detallado["No. de Folio"] == folio]

        if df_full.empty:
            st.error("No se encontró información completa.")
            return

        r_full = df_full.iloc[0]

        # ===============================
        # SECTION 1 — IDENTIFICACIÓN
        # ===============================
        st.subheader("📌 Información General")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown(f"**Empresa:** {r_full.get('Empresa','')}")
            st.markdown(f"**Tipo de Reporte:** {r_full.get('Tipo de Reporte','')}")
            st.markdown(f"**Tipo de Unidad:** {r_full.get('Tipo de Unidad','')}")

        with col2:
            st.markdown(f"**No. Unidad:** {r_full.get('No. de Unidad','')}")
            st.markdown(f"**Marca:** {r_full.get('Marca','')}")
            st.markdown(f"**Modelo:** {r_full.get('Modelo','')}")

        with col3:
            st.markdown(f"**Estado:** {r_full.get('Estado','')}")
            st.markdown(f"**Capturó:** {r_full.get('Capturo','')}")
            st.markdown(f"**Fecha Captura:** {fmt_date(r_full.get('Fecha de Captura'))}")

        st.divider()

        # ===============================
        # SECTION 2 — PROVEEDOR
        # ===============================
        st.subheader("🏭 Información de Proveedor")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"**Tipo Proveedor:** {r_full.get('Tipo de Proveedor','')}")
            st.markdown(f"**OSTE:** {r_full.get('Oste','')}")

        with col2:
            st.markdown(f"**No. Orden:** {r_full.get('No. de Reporte','')}")
            st.markdown(f"**No. Factura:** {r_full.get('No. de Factura','')}")

        st.divider()

        # ===============================
        # SECTION 3 — DESCRIPCIÓN
        # ===============================
        st.subheader("📝 Descripción del Problema")

        descripcion = r_full.get("Descripcion Problema","")

        st.markdown(
            f"""
            <div style="
                background:#f1f5f9;
                padding:16px;
                border-radius:12px;
                font-size:0.95rem;
                color:#111111;
                line-height:1.5;
            ">
                {descripcion if descripcion else "-"}
            </div>
            """,
            unsafe_allow_html=True
        )

        st.divider()

        # ===============================
        # SECTION 4 — SERVICIOS / PARTES
        # ===============================
        st.subheader("🔧 Servicios y Refacciones")

        df_serv = df_services[df_services["Folio"] == folio].copy()

        # Remove log-only rows (empty Parte)
        if "Parte" in df_serv.columns:
            df_serv = df_serv[
                df_serv["Parte"].notna() &
                (df_serv["Parte"].astype(str).str.strip() != "")
            ]

        if not df_serv.empty:
            cols = ["Parte","Tipo De Parte","Posicion","Cantidad"]
            cols = [c for c in cols if c in df_serv.columns]

            st.dataframe(df_serv[cols], use_container_width=True, hide_index=True)
        else:
            st.info("Sin servicios registrados.")

        st.divider()

        # ===============================
        # SECTION 5 — FECHAS OPERATIVAS
        # ===============================
        st.subheader("📅 Fechas Operativas")

        fecha_cols = [
            "Fecha Diagnostico",
            "Fecha No Diagnosticado",
            "Fecha En Reparacion",
            "Fecha Espera Refaccion",
            "Fecha Resuelto",
            "Fecha Terminado",
            "Fecha Concluido",
            "Fecha Cancelado",
        ]

        fechas = df_serv[fecha_cols].max() if not df_serv.empty else {}

        for col in fecha_cols:
            value = fechas[col] if col in fechas else None
            st.markdown(f"**{col}:** {fmt_date(value)}")

        st.divider()

        # ===============================
        # SECTION 6 — OTROS DATOS
        # ===============================
        st.subheader("📎 Información Adicional")

        st.markdown(f"**Sucursal:** {r_full.get('Sucursal','')}")
        st.markdown(f"**Operador:** {r_full.get('Operador','')}")
        st.markdown(f"**Responsable:** {r_full.get('Responsable','')}")
        st.markdown(f"**Cobro:** {r_full.get('Cobro','')}")
        st.markdown(f"**Multa:** {r_full.get('Multa','')}")
        st.markdown(f"**No. Inspección:** {r_full.get('No. de Inspeccion','')}")
        st.markdown(f"**Reparación Multa:** {r_full.get('Reparacion Multa','')}")

        st.divider()

        if st.button("Cerrar", key=f"cerrar_modal_{folio}"):
            st.session_state.modal_reporte = None
            st.rerun()

    modal_ver()