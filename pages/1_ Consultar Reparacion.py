import streamlit as st
import pandas as pd
from datetime import date
from auth import require_login, require_access
import streamlit.components.v1 as components

st.cache_data.clear()
# =================================
# Page configuration
# =================================
st.set_page_config(
    page_title="Consulta de Reparación",
    layout="wide"
)

# =================================
# Hide sidebar
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
# Security
# =================================
require_login()
require_access("consultar_reparacion")

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

# =================================
# EMPRESA DATA CONFIG
# =================================
EMPRESA_CONFIG = {
    "IGLOO TRANSPORT": {
        "ordenes": (
            "https://docs.google.com/spreadsheets/d/"
            "1OGYOp0ZqK7PQ93F4wdHJKEnB4oZbl5pU"
            "/export?format=csv&gid=770635060"
        ),
        "partes": (
            "https://docs.google.com/spreadsheets/d/"
            "18tFOA4prD-PWhtbc35cqKXxYcyuqGOC7"
            "/export?format=csv&gid=410297659"
        ),
        "ostes": (
            "https://docs.google.com/spreadsheets/d/"
            "1RZ1YcLQxXI0U81Vle6cXmRp0yMxuRVg4"
            "/export?format=csv&gid=1578839108"
        )
    },

    "LINCOLN FREIGHT": {
        "ordenes": (
            "https://docs.google.com/spreadsheets/d/"
            "1nqRT3LRixs45Wth5bXyrKSojv3uJfjbZ"
            "/export?format=csv&gid=332111886"
        ),
        "partes": (
            "https://docs.google.com/spreadsheets/d/"
            "1lcNr73nHrMpsqdYBNxtTQFqFmY1Ey9gp"
            "/export?format=csv&gid=41991257"
        ),
        "ostes": (
            "https://docs.google.com/spreadsheets/d/"
            "1lZO4SVKHXfW1-IzhYXvAmJ8WC7zgg8VD"
            "/export?format=csv&gid=1179811252"
        )
    },

    "PICUS": {
        "ordenes": (
            "https://docs.google.com/spreadsheets/d/"
            "1DSFFir8vQGzkIZdPGZKakMFygUUjA6vg"
            "/export?format=csv&gid=1157416037"
        ),
        "partes": (
            "https://docs.google.com/spreadsheets/d/"
            "1tzt6tYG94oVt8YwK3u9gR-DHFcuadpNN"
            "/export?format=csv&gid=354598948"
        ),
        "ostes": (
            "https://docs.google.com/spreadsheets/d/"
            "1vedjfjpQAHA4l1iby_mZRdVayH0H4cjg"
            "/export?format=csv&gid=1926750281"
        )
    },

    "SET FREIGHT INTERNATIONAL": {
        "ordenes": (
            "https://docs.google.com/spreadsheets/d/"
            "166RzQ6DxBiZ1c7xjMQzyPJk2uLJI_piO"
            "/export?format=csv&gid=1292870764"
        ),
        "partes": (
            "https://docs.google.com/spreadsheets/d/"
            "1Nqbhl8o5qaKhI4LNxreicPW5Ew8kqShS"
            "/export?format=csv&gid=849445619"
        ),
        "ostes": (
            "https://docs.google.com/spreadsheets/d/"
            "1lshd4YaUyuZiYctys3RplStzcYpABNRj"
            "/export?format=csv&gid=1882046877"
        )
    },

    "SET LOGIS PLUS": {
        "ordenes": (
            "https://docs.google.com/spreadsheets/d/"
            "11q580KXBn-kX5t-eHAbV0kp-kTqIQBR6"
            "/export?format=csv&gid=663362391"
        ),
        "partes": (
            "https://docs.google.com/spreadsheets/d/"
            "1yrzwm5ixsaYNKwkZpfmFpDdvZnohFH61"
            "/export?format=csv&gid=1837946138"
        ),
        "ostes": (
            "https://docs.google.com/spreadsheets/d/"
            "1kcemsViXwHBaCXK58SGBxjfYs-zakhki"
            "/export?format=csv&gid=1472656211"
        )
    }
}

# =================================
# LOADERS
# =================================
@st.cache_data(ttl=600)
def cargar_ordenes(url):
    if not url:
        return pd.DataFrame()

    df = pd.read_csv(url)
    df.columns = df.columns.str.strip()

    # =====================================================
    # COLUMN NORMALIZATION (DATABASE → SYSTEM)
    # =====================================================
    rename_map = {
        "Diferencia": "DIFERENCIA",
        "Comentarios": "COMENTARIOS",
        "Tipo De Unidad": "Tipo Unidad",
        "Razon de servicio": "Razon Reparacion",
    }

    df = df.rename(columns=rename_map)

    # =====================================================
    # DATE PARSE
    # =====================================================
    if "Fecha Registro" in df.columns:
        df["Fecha Registro"] = pd.to_datetime(
            df["Fecha Registro"],
            errors="coerce",
            infer_datetime_format=True
        )

    return df

@st.cache_data(ttl=600)
def cargar_partes(url):
    if not url:
        return pd.DataFrame()

    df = pd.read_csv(url)
    df.columns = df.columns.str.strip()

    # Parse Fecha Compra (ONLY this column matters)
    if "Fecha Compra" in df.columns:
        df["Fecha Compra"] = pd.to_datetime(
            df["Fecha Compra"],
            errors="coerce",
            dayfirst=True
        )

        # Base rule → only 2025+
        df = df[df["Fecha Compra"] >= pd.Timestamp("2025-01-01")]

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

df = cargar_ordenes(config["ordenes"])
df_partes = cargar_partes(config["partes"])
df_ostes = pd.read_csv(config["ostes"])
df_ostes.columns = df_ostes.columns.str.strip()

if df.empty:
    st.warning("No hay datos disponibles para esta empresa.")
    st.stop()

def safe(x):
    if pd.isna(x) or x is None:
        return ""
    return str(x)

# =================================
# ÚLTIMOS 10 REGISTROS
# =================================
st.subheader("Últimos registros")

unidad_orden_sel = "Todas"

columnas_resumen = [
    "Fecha Aceptado",
    "Fecha Iniciada",
    "Unidad",
    "Tipo Unidad",
    "Reporte",
    "Descripcion",
    "Razon Reparacion"
]

columnas_disponibles = [c for c in columnas_resumen if c in df.columns]

# =====================================================
# BUILD INTERNAL DATASET (LATEST 10)
# =====================================================
df_interna = df.copy()

if "Fecha Registro" in df_interna.columns:
    df_interna["Fecha Registro"] = pd.to_datetime(
        df_interna["Fecha Registro"],
        errors="coerce",
        dayfirst=True
    )

    df_interna = df_interna.sort_values(
        by="Fecha Registro",
        ascending=False,
        na_position="last"
    ).head(10)

# =====================================================
# BUILD EXTERNAL DATASET (LATEST 10)
# =====================================================
df_externa = df_ostes.copy()

if "Fecha OSTE" in df_externa.columns:
    df_externa["Fecha OSTE"] = pd.to_datetime(
        df_externa["Fecha OSTE"],
        errors="coerce"
    )

    df_externa = df_externa.sort_values(
        by="Fecha OSTE",
        ascending=False,
        na_position="last"
    ).head(10)

# =====================================================
# MANO DE OBRA INTERNA
# =====================================================
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
            razon = safe(row.get("Razon Reparacion"))
            desc = safe(row.get("Descripcion"))
            fecha_registro = row.get("Fecha Registro")
            if pd.notna(fecha_registro):
                fecha_registro = pd.to_datetime(fecha_registro, errors="coerce")
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
            razon = safe(row.get("Razon Reparacion"))
            desc = safe(row.get("Descripcion"))
            fecha_oste = row.get("Fecha OSTE")
            if pd.notna(fecha_oste):
                fecha_oste = pd.to_datetime(fecha_oste, errors="coerce")
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