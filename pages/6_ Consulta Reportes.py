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

#Modal state initialization
st.session_state.setdefault("modal_reporte", None)

# =================================
# Navigation
# =================================
if st.button("⬅ Volver al Dashboard"):
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
                empresa = safe(r.get("Empresa"))
                unidad = safe(r.get("No. de Unidad"))
                estado = safe(r.get("Estado"))

                html = f"""
                <div style="padding:6px;">
                    <div style="
                        background:#e8f0ff;
                        padding:14px;
                        border-radius:16px;
                        box-shadow:0 4px 10px rgba(0,0,0,0.08);
                        color:#111;
                        min-height:170px;
                        font-family:sans-serif;
                    ">
                        <div style="font-weight:900;">{folio}</div>
                        <div style="font-size:0.8rem;">{tipo_unidad}</div>
                        <div style="font-size:0.8rem;">{fecha}</div>

                        <hr style="margin:6px 0">

                        <div style="font-size:0.8rem;">{empresa}</div>
                        <div style="font-size:0.8rem;">{unidad}</div>

                        <div style="
                            margin-top:6px;
                            font-size:0.75rem;
                            font-weight:700;
                            color:#1e40af;
                        ">
                            {estado}
                        </div>
                    </div>
                </div>
                """

                components.html(html, height=200)

                # =====================================
                # VIEW BUTTON
                # =====================================
                if st.button("👁 Ver", key=f"view_last_{folio}", use_container_width=True):
                    st.session_state.modal_reporte = r.to_dict()

else:
    st.info("No hay actividad reciente.")

st.divider()

# =================================
# FILTERS (3 PER ROW)
# =================================
st.subheader("Filtros")

# ---------- ROW 1 ----------
r1c1, r1c2, r1c3 = st.columns(3)

with r1c1:
    empresa = st.selectbox(
        "Empresa",
        ["Todas"] + sorted(df_pases["Empresa"].dropna().unique().tolist())
        if not df_pases.empty else ["Todas"]
    )

with r1c2:
    estado = st.selectbox(
        "Estado",
        ["Todos"] + sorted(df_pases["Estado"].dropna().unique().tolist())
        if not df_pases.empty else ["Todos"]
    )

with r1c3:
    no_unidad = st.selectbox(
        "No. de Unidad",
        ["Todas"] + sorted(df_pases["No. de Unidad"].dropna().astype(str).unique().tolist())
        if "No. de Unidad" in df_pases.columns else ["Todas"]
    )

# ---------- ROW 2 ----------
r2c1, r2c2, r2c3 = st.columns(3)

with r2c1:
    no_reporte = st.text_input("No. de Reporte")

with r2c2:
    tipo_reporte = st.selectbox(
        "Tipo de Reporte",
        ["Todos"] + sorted(df_pases["Tipo de Reporte"].dropna().unique().tolist())
        if "Tipo de Reporte" in df_pases.columns else ["Todos"]
    )

with r2c3:
    fecha_captura = st.date_input("Fecha de Captura", value=None)

# ---------- ROW 3 ----------
r3c1, r3c2, r3c3 = st.columns(3)

with r3c1:
    fecha_reporte = st.date_input("Fecha de Reporte", value=None)

with r3c2:
    fecha_mod = st.date_input("Fecha Mod (Servicios)", value=None)

with r3c3:
    buscar = st.button("🔍 Aplicar filtros", type="primary")

# =================================
# APPLY FILTERS
# =================================
if buscar:
    df_p = df_pases.copy()
    df_s = df_services.copy()

    if empresa != "Todas":
        df_p = df_p[df_p["Empresa"] == empresa]

    if estado != "Todos":
        df_p = df_p[df_p["Estado"] == estado]

    if no_unidad != "Todas" and "No. de Unidad" in df_p.columns:
        df_p = df_p[df_p["No. de Unidad"].astype(str) == no_unidad]

    if no_reporte and "No. de Reporte" in df_p.columns:
        df_p = df_p[df_p["No. de Reporte"].astype(str).str.contains(no_reporte, na=False)]

    if tipo_reporte != "Todos" and "Tipo de Reporte" in df_p.columns:
        df_p = df_p[df_p["Tipo de Reporte"] == tipo_reporte]

    if fecha_captura and "Fecha de Captura" in df_p.columns:
        df_p = df_p[df_p["Fecha de Captura"].dt.date == fecha_captura]

    if fecha_reporte and "Fecha de Reporte" in df_p.columns:
        df_p = df_p[df_p["Fecha de Reporte"].dt.date == fecha_reporte]

    if fecha_mod and "Fecha Mod" in df_s.columns:
        df_s = df_s[df_s["Fecha Mod"].dt.date == fecha_mod]

    # =================================
    # TABLE 1 — REPORTE DETALLADO
    # =================================
    df_detallado = df_p.merge(df_s, on="Folio", how="left")

    st.divider()
    st.subheader("📄 Reporte Detallado")

    st.dataframe(df_detallado, hide_index=True, width="stretch")

    # =================================
    # TABLE 2 — RESUMEN POR ORDEN
    # =================================
    st.divider()
    st.subheader("📦 Resumen por Orden")

    servicios_agg = (
        df_s
        .groupby("Folio", as_index=False)
        .agg({
            "Parte": lambda x: ", ".join(sorted(set(str(v) for v in x if pd.notna(v)))),
            "Total MXN": lambda x: pd.to_numeric(x, errors="coerce").fillna(0).sum()
        })
        .rename(columns={
            "Parte": "Partes",
            "Total MXN": "Total MXN Servicios"
        })
    )

    df_resumen = df_p.merge(servicios_agg, on="Folio", how="left")
    df_resumen["Partes"] = df_resumen["Partes"].fillna("")
    df_resumen["Total MXN Servicios"] = df_resumen["Total MXN Servicios"].fillna(0)

    st.dataframe(df_resumen, hide_index=True, width="stretch")

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
        st.markdown(f"**Empresa:** {r.get('Empresa','')}")
        st.markdown(f"**Proveedor:** {r.get('Tipo de Proveedor','')}")
        st.markdown(f"**No. de Unidad:** {r.get('No. de Unidad','')}")
        st.markdown(f"**Sucursal:** {r.get('Sucursal','')}")

        # ===============================
        # LAST MOD DATE (FROM SERVICES)
        # ===============================
        df_folio = df_services[df_services["Folio"] == folio]

        if not df_folio.empty and "Fecha Mod" in df_folio.columns:
            fecha_mod = df_folio["Fecha Mod"].max()
            st.markdown(f"**Fecha Mod:** {fecha_mod}")
        else:
            st.markdown("**Fecha Mod:** -")

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
            es_lincoln = r.get("Empresa") == "LINCOLN FREIGHT"

            if es_lincoln:
                df_show = df_folio.copy()
                df_show["PrecioParte"] = df_show.get("Precio MXP", 0)
                df_show["Cantidad"] = df_show.get("Cantidad", 0)
                df_show["Total USD"] = df_show.get("Total MXN", 0)

                st.dataframe(
                    df_show[["Parte","TipoCompra","PrecioParte","Cantidad","Total USD"]],
                    hide_index=True,
                    width="stretch"
                )

                total = pd.to_numeric(df_show["Total USD"], errors="coerce").fillna(0).sum()
                st.metric("Total USD", f"$ {total:,.2f}")

            else:
                st.dataframe(
                    df_folio[["Parte","TipoCompra","Precio MXP","IVA","Cantidad","Total MXN"]],
                    hide_index=True,
                    width="stretch"
                )

                total = pd.to_numeric(df_folio["Total MXN"], errors="coerce").fillna(0).sum()
                st.metric("Total MXN", f"$ {total:,.2f}")

        st.divider()

        if st.button("Cerrar"):
            st.session_state.modal_reporte = None
            st.rerun()

    modal_ver()