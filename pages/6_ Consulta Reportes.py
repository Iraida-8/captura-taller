import streamlit as st
import pandas as pd
from supabase import create_client
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
# Supabase pagination helper
# =================================
def fetch_all_rows(table_name, page_size=1000):

    start = 0
    all_rows = []

    while True:

        response = (
            supabase
            .table(table_name)
            .select("*")
            .range(start, start + page_size - 1)
            .execute()
        )

        data = response.data

        if not data:
            break

        all_rows.extend(data)

        if len(data) < page_size:
            break

        start += page_size

    return all_rows

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
# Load PASES (SUPABASE PAGINATED)
# =================================
@st.cache_data(ttl=300)
def cargar_pases():

    tablas = ["IGLOO", "LINCOLN", "PICUS", "SFI", "SLP"]

    dfs = []

    for tabla in tablas:

        data = fetch_all_rows(tabla)

        if data:
            dfs.append(pd.DataFrame(data))

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
# Load SERVICES (SUPABASE PAGINATED)
# =================================
@st.cache_data(ttl=300)
def cargar_servicios():

    data = fetch_all_rows("SERVICES")

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
            "Fecha Cancelado",
        ])

    df = pd.DataFrame(data)

    df.columns = df.columns.str.strip()

    if "No. de Folio" in df.columns:
        df = df.rename(columns={"No. de Folio": "Folio"})

    df["Folio"] = df["Folio"].astype(str)

    if "Posicion" in df.columns:
        df["Posicion"] = df["Posicion"].astype(str)

    date_cols = [
        "Fecha Mod",
        "Fecha Diagnostico",
        "Fecha No Diagnosticado",
        "Fecha En Reparacion",
        "Fecha Espera Refaccion",
        "Fecha Resuelto",
        "Fecha Cancelado",
    ]

    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    return df

# =================================
# Load FACTURAS (SUPABASE PAGINATED)
# =================================
@st.cache_data(ttl=300)
def cargar_facturas():

    data = fetch_all_rows("INVOICES")

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
        "En Curso / En Diagnostico",
        "En Curso / No Diagnosticado",
    ])]
)

en_proceso = len(
    df_pases[df_pases["Estado"].isin([
        "En Curso / En Reparacion",
        "En Curso / Espera de Refaccion",
    ])]
)

completadas = len(
    df_pases[df_pases["Estado"] == "Cerrado / Resuelto"]
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
# MAIN FILTERS (2 rows × 4 columns)
# =========================================================

# ===== ROW 1 =====
f1, f2, f3, f4 = st.columns(4)

with f1:
    folio = st.text_input("No. de Folio", key="f_folio")

with f2:
    no_reporte = st.text_input("No. de Reporte", key="f_no_reporte")

with f3:
    oste = st.text_input("OSTE", key="f_oste")

with f4:
    no_factura = st.text_input("No. de Factura", key="f_no_factura")


# ===== ROW 2 =====
f5, f6, f7, f8 = st.columns(4)

with f5:
    empresa = st.selectbox(
        "Empresa",
        ["Todas"] + sorted(df_pases["Empresa"].dropna().unique().tolist()),
        key="f_empresa"
    )

with f6:
    no_unidad = st.selectbox(
        "No. de Unidad",
        ["Todas"] + sorted(
            df_pases["No. de Unidad"].dropna().astype(str).unique().tolist()
        ) if "No. de Unidad" in df_pases.columns else ["Todas"],
        key="f_unidad"
    )

with f7:
    capturo = st.selectbox(
        "Capturó",
        ["Todos"] + sorted(
            df_pases["Capturo"].dropna().unique().tolist()
        ) if "Capturo" in df_pases.columns else ["Todos"],
        key="f_capturo"
    )

with f8:
    ESTADOS = [
        "En Curso / Nuevo",
        "En Curso / En Diagnostico",
        "En Curso / No Diagnosticado",
        "En Curso / En Reparacion",
        "En Curso / Espera de Refaccion",
        "Cerrado / Resuelto",
        "Cerrado / Cancelado",
    ]

    estado = st.selectbox(
        "Estado",
        ["Todos"] + ESTADOS,
        key="f_estado"
    )

# =========================================================
# SECTION 2 → DATE FILTERS (COLLAPSIBLE)
# =========================================================
with st.expander("📅 Filtrar por fechas", expanded=False):

    d1, d2, d3 = st.columns(3)

    with d1:
        fecha_diag = st.date_input("Fecha Diagnostico", value=None, key="f_fecha_diag")

    with d2:
        fecha_no_diag = st.date_input("Fecha No Diagnosticado", value=None, key="f_fecha_no_diag")

    with d3:
        fecha_reparacion = st.date_input("Fecha En Reparacion", value=None, key="f_fecha_reparacion")

    d4, d5, d6 = st.columns(3)

    with d4:
        fecha_espera = st.date_input("Fecha Espera Refaccion", value=None, key="f_fecha_espera")

    with d5:
        fecha_resuelto = st.date_input("Fecha Resuelto", value=None, key="f_fecha_resuelto")

    with d6:
        fecha_cancel = st.date_input("Fecha Cancelado", value=None, key="f_fecha_cancel")

c1, c2 = st.columns([1,1])

with c1:
    buscar = st.button("🔍 Aplicar filtros", type="primary", use_container_width=True)

with c2:
    if st.button("🧹 Borrar filtros", use_container_width=True):

        # Reset widget values
        st.session_state["f_folio"] = ""
        st.session_state["f_no_reporte"] = ""
        st.session_state["f_oste"] = ""
        st.session_state["f_no_factura"] = ""

        st.session_state["f_empresa"] = "Todas"
        st.session_state["f_unidad"] = "Todas"
        st.session_state["f_capturo"] = "Todos"
        st.session_state["f_estado"] = "Todos"

        # Reset date filters
        st.session_state["f_fecha_diag"] = None
        st.session_state["f_fecha_no_diag"] = None
        st.session_state["f_fecha_reparacion"] = None
        st.session_state["f_fecha_espera"] = None
        st.session_state["f_fecha_resuelto"] = None
        st.session_state["f_fecha_cancel"] = None

        # Reset filtered data
        st.session_state.pop("df_filtrado_pases", None)
        st.session_state.pop("df_filtrado_servicios", None)

        # Reset filter flag
        st.session_state["filtros_aplicados"] = False

        # Close modal
        st.session_state.modal_reporte = None

        st.rerun()

# =================================
# APPLY FILTERS
# =================================

# Ensure default flag exists
st.session_state.setdefault("filtros_aplicados", False)

if buscar:

    st.cache_data.clear()
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
    
    if capturo != "Todos":
      df_p = df_p[df_p["Capturo"] == capturo]

    if estado != "Todos":
        df_p = df_p[df_p["Estado"] == estado]

    if no_unidad != "Todas" and "No. de Unidad" in df_p.columns:
        df_p = df_p[df_p["No. de Unidad"].astype(str) == no_unidad]

    if no_reporte and "No. de Reporte" in df_p.columns:
        df_p = df_p[df_p["No. de Reporte"].astype(str).str.contains(no_reporte, na=False)]

    if oste and "Oste" in df_p.columns:
        df_p = df_p[df_p["Oste"].astype(str).str.contains(oste, na=False)]

    if no_factura:
        df_fact_filter = df_facturas[
            df_facturas["No. de Factura"].astype(str).str.contains(no_factura, na=False)
        ]
        folios_fact = df_fact_filter["Folio"].unique()
        df_p = df_p[df_p["Folio"].isin(folios_fact)]

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
    df_s = filtrar_fecha(df_s, "Fecha Cancelado", fecha_cancel)

    # ======================================================
    # MATCH SERVICES → PASES
    # ======================================================

    if (
        fecha_diag or fecha_no_diag or fecha_reparacion
        or fecha_espera or fecha_resuelto
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

    # Only BASIC filters trigger post-its
    filtros_basicos = any([
        folio,
        no_reporte,
        oste,
        no_factura,
        empresa != "Todas",
        estado != "Todos",
        no_unidad != "Todas",
        capturo != "Todos"
    ])

    st.session_state["filtros_aplicados"] = filtros_basicos

# ======================================================
# TABLE 1 — REPORTE DETALLADO
# ======================================================

# use filtered data if available
df_p = st.session_state.get("df_filtrado_pases", df_pases.copy())
df_s = st.session_state.get("df_filtrado_servicios", df_services.copy())

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

# =================================
# POSTITS — RESULTADOS FILTRADOS
# =================================
st.divider()

if not st.session_state.get("filtros_aplicados"):
    st.markdown("## 📌 Órdenes Filtradas")
    st.info(
        "Aplica al menos un filtro para visualizar las órdenes. "
        "Máximo 25 resultados."
    )

else:
    st.markdown("## 📌 Órdenes Filtradas")
    st.caption("Mostrando máximo 25 resultados")

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

                fecha = fecha.date() if pd.notna(fecha) else ""

                if "Folio" in df_facturas.columns:
                    df_factura_folio = df_facturas[df_facturas["Folio"] == folio]
                else:
                    df_factura_folio = pd.DataFrame()
                no_factura = (
                    df_factura_folio.iloc[0].get("No. de Factura", "")
                    if not df_factura_folio.empty else ""
                )

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
        st.warning("No se encontraron órdenes con los filtros aplicados.")

# EXACT columns you requested
columnas = [
    # ===== COMPANY =====
    "Fecha de Captura",
    "No. de Folio",
    "Fecha de Reporte",
    "Empresa",
    "Estado",
    "Capturo",
    "No. de Factura",
    "Oste",
    "No. de Reporte",
    "Tipo de Unidad",
    "No. de Unidad",
    "Marca",
    "Modelo",
    "Descripcion Problema",

    # ===== SERVICES (RAW) =====
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
    "Fecha Cancelado",
]

# FIRST rename
df_detallado = df_detallado.rename(columns={
    "Folio": "No. de Folio"
})

# THEN validate columns
columnas = [c for c in columnas if c in df_detallado.columns]

st.divider()

st.info(
    "Para consultar el Reporte Detallado, expanda la sección inferior."
)

with st.expander("📄 Reporte Detallado", expanded=False):

    st.dataframe(
        df_detallado[columnas],
        hide_index=True,
        width="stretch"
    )

# ======================================================
# TABLE 2 — RESUMEN POR ORDEN (1 LINE PER FOLIO)
# ======================================================
st.divider()

st.info(
    "Para consultar el Resumen por Orden, expanda la sección inferior."
)

with st.expander("📦 Resumen por Orden", expanded=False):

    df_s = df_s.copy()

    if df_s.empty:
        st.info("Sin servicios.")
    else:

        # ===============================
        # AGGREGATE SERVICES
        # ===============================
        def join_unique(series):
            seen = set()
            result = []
            for v in series:
                if pd.notna(v):
                    s = str(v).strip()
                    if s and s not in seen:
                        seen.add(s)
                        result.append(s)
            return ", ".join(result)

        servicios_agg = (
            df_s
            .groupby("Folio", as_index=False)
            .agg({
                # ===== TEXT FIELDS =====
                "Parte": join_unique,
                "Tipo De Parte": join_unique,
                "Posicion": join_unique,

                # ===== NUMERIC =====
                "Cantidad": join_unique,

                # ===== DATES (take latest available) =====
                "Fecha Mod": "max",
                "Fecha Diagnostico": "max",
                "Fecha No Diagnosticado": "max",
                "Fecha En Reparacion": "max",
                "Fecha Espera Refaccion": "max",
                "Fecha Resuelto": "max",
                "Fecha Cancelado": "max",
            })
        )

        # ===============================
        # MERGE WITH COMPANY DATA
        # ===============================
        df_resumen = df_p.merge(servicios_agg, on="Folio", how="left")

        # ===============================
        # MERGE FACTURAS
        # ===============================
        if "Folio" in df_facturas.columns:
            df_resumen = df_resumen.merge(
                df_facturas[["Folio", "No. de Factura"]],
                on="Folio",
                how="left"
            )
        else:
            df_resumen["No. de Factura"] = None

        # ===============================
        # COLUMN ORDER
        # ===============================
        columnas = [
            # ===== COMPANY =====
            "Fecha de Captura",
            "No. de Folio",
            "Fecha de Reporte",
            "Empresa",
            "Estado",
            "Capturo",
            "No. de Factura",
            "Oste",
            "No. de Reporte",
            "Tipo de Unidad",
            "No. de Unidad",
            "Marca",
            "Modelo",
            "Descripcion Problema",

            # ===== SERVICES (AGGREGATED) =====
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
            "Fecha Cancelado",
        ]

        df_resumen = df_resumen.rename(columns={
            "Folio": "No. de Folio"
        })

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
        if "Posicion" in df_serv.columns:

            def format_posicion(x):

                # Handle empty values
                if x is None or pd.isna(x):
                    return ""

                s = str(x).strip()

                if s == "" or s.lower() == "none":
                    return ""

                # If already formatted correctly
                if "," in s:
                    return s

                # If it contains letters, don't touch it
                if not s.isdigit():
                    return s

                # Rebuild positions
                parts = []
                i = 0
                while i < len(s):
                    if i == 0 and len(s) % 2 == 1:
                        parts.append(s[i])
                        i += 1
                    else:
                        parts.append(s[i:i+2])
                        i += 2

                return ",".join(parts)

            df_serv["Posicion"] = df_serv["Posicion"].apply(format_posicion)

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