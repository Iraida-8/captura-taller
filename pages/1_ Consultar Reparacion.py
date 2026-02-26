import streamlit as st
import pandas as pd
from auth import require_login, require_access
import streamlit.components.v1 as components

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
    st.session_state["modal_orden"] = None
    st.session_state["modal_tipo"] = None
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
        "ordenes": "https://docs.google.com/spreadsheets/d/1OGYOp0ZqK7PQ93F4wdHJKEnB4oZbl5pU/export?format=csv&gid=770635060",
        "ostes": "https://docs.google.com/spreadsheets/d/1RZ1YcLQxXI0U81Vle6cXmRp0yMxuRVg4/export?format=csv&gid=1578839108"
    },
    "LINCOLN FREIGHT": {
        "ordenes": "https://docs.google.com/spreadsheets/d/1nqRT3LRixs45Wth5bXyrKSojv3uJfjbZ/export?format=csv&gid=332111886",
        "ostes": "https://docs.google.com/spreadsheets/d/1lZO4SVKHXfW1-IzhYXvAmJ8WC7zgg8VD/export?format=csv&gid=1179811252"
    },
    "PICUS": {
        "ordenes": "https://docs.google.com/spreadsheets/d/1DSFFir8vQGzkIZdPGZKakMFygUUjA6vg/export?format=csv&gid=1157416037",
        "ostes": "https://docs.google.com/spreadsheets/d/1vedjfjpQAHA4l1iby_mZRdVayH0H4cjg/export?format=csv&gid=1926750281"
    },
    "SET FREIGHT INTERNATIONAL": {
        "ordenes": "https://docs.google.com/spreadsheets/d/166RzQ6DxBiZ1c7xjMQzyPJk2uLJI_piO/export?format=csv&gid=1292870764",
        "ostes": "https://docs.google.com/spreadsheets/d/1lshd4YaUyuZiYctys3RplStzcYpABNRj/export?format=csv&gid=1882046877"
    },
    "SET LOGIS PLUS": {
        "ordenes": "https://docs.google.com/spreadsheets/d/11q580KXBn-kX5t-eHAbV0kp-kTqIQBR6/export?format=csv&gid=663362391",
        "ostes": "https://docs.google.com/spreadsheets/d/1kcemsViXwHBaCXK58SGBxjfYs-zakhki/export?format=csv&gid=1472656211"
    }
}

# =================================
# LOADERS
# =================================
@st.cache_data(ttl=600)
def cargar_ordenes(url):
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip()

    rename_map = {
        "Diferencia": "DIFERENCIA",
        "Comentarios": "COMENTARIOS",
        "Tipo De Unidad": "Tipo Unidad",
        "Razon de servicio": "Razon Reparacion",
    }
    df = df.rename(columns=rename_map)

    if "Fecha Registro" in df.columns:
        df["Fecha Registro"] = pd.to_datetime(
            df["Fecha Registro"],
            errors="coerce",
            format="mixed"
        )

    return df


@st.cache_data(ttl=600)
def cargar_ostes(url):
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip()

    if "Fecha OSTE" in df.columns:
        df["Fecha OSTE"] = pd.to_datetime(
            df["Fecha OSTE"],
            errors="coerce",
            format="mixed"
        )

    return df


def safe(x):
    if pd.isna(x) or x is None:
        return ""
    return str(x)

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
df_ostes = cargar_ostes(config["ostes"])

if df.empty:
    st.warning("No hay datos disponibles para esta empresa.")
    st.stop()

# =================================
# BUILD DATASETS (LATEST 10)
# =================================
df_interna = df.copy()
if "Fecha Registro" in df_interna.columns:
    df_interna = df_interna.sort_values(
        by="Fecha Registro",
        ascending=False,
        na_position="last"
    ).head(10)

df_externa = df_ostes.copy()
if "Fecha OSTE" in df_externa.columns:
    df_externa = df_externa.sort_values(
        by="Fecha OSTE",
        ascending=False,
        na_position="last"
    ).head(10)

# =================================
# MANO DE OBRA INTERNA
# =================================
st.subheader("Últimos registros")
st.markdown("### 🔧 Mano de Obra Interna")

if df_interna.empty:
    st.info("No hay registros internos.")
else:
    cols = st.columns(5)
    for i, (_, row) in enumerate(df_interna.iterrows()):
        col = cols[i % 5]
        with col:
            fecha_registro = row.get("Fecha Registro")
            fecha_registro = (
                fecha_registro.strftime("%d/%m/%Y")
                if pd.notna(fecha_registro) else ""
            )

            html = f"""
            <div style="padding:6px;">
                <div style="
                    background:#ffffff;
                    padding:14px;
                    border-radius:16px;
                    box-shadow:0 4px 10px rgba(0,0,0,0.08);
                    min-height:190px;
                    font-family:sans-serif;">
                    
                    <div style="font-weight:900;">{safe(row.get("Reporte"))}</div>
                    <div style="font-size:0.8rem; margin-top:4px;">
                        {safe(row.get("Unidad"))} | {safe(row.get("Tipo Unidad"))}
                    </div>
                    <hr>
                    <div style="font-size:0.8rem;">
                        <b>Razón:</b> {safe(row.get("Razon Reparacion"))}
                    </div>
                    <div style="font-size:0.8rem;">
                        <b>Descripción:</b> {safe(row.get("Descripcion"))}
                    </div>
                    <hr>
                    <div style="font-size:0.75rem;">
                        <b>Fecha Registro:</b> {fecha_registro}
                    </div>
                </div>
            </div>
            """
            components.html(html, height=260)

# =================================
# MANO DE OBRA EXTERNA
# =================================
st.divider()
st.markdown("### 🧾 Mano de Obra Externa (OSTES)")

if df_externa.empty:
    st.info("No hay registros externos.")
else:
    cols = st.columns(5)
    for i, (_, row) in enumerate(df_externa.iterrows()):
        col = cols[i % 5]
        with col:
            fecha_oste = row.get("Fecha OSTE")
            fecha_oste = (
                fecha_oste.strftime("%d/%m/%Y")
                if pd.notna(fecha_oste) else ""
            )

            html = f"""
            <div style="padding:6px;">
                <div style="
                    background:#ffffff;
                    padding:14px;
                    border-radius:16px;
                    box-shadow:0 4px 10px rgba(0,0,0,0.08);
                    min-height:190px;
                    font-family:sans-serif;">
                    
                    <div style="font-weight:900;">{safe(row.get("Reporte"))}</div>
                    <div style="font-size:0.8rem; margin-top:4px;">
                        {safe(row.get("Unidad"))} | {safe(row.get("Tipo Unidad"))}
                    </div>
                    <hr>
                    <div style="font-size:0.8rem;">
                        <b>Razón:</b> {safe(row.get("Razon Reparacion"))}
                    </div>
                    <div style="font-size:0.8rem;">
                        <b>Descripción:</b> {safe(row.get("Descripcion"))}
                    </div>
                    <hr>
                    <div style="font-size:0.75rem;">
                        <b>Fecha OSTE:</b> {fecha_oste}
                    </div>
                </div>
            </div>
            """
            components.html(html, height=260)