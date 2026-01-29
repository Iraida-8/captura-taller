import streamlit as st
import pandas as pd

from auth import require_login, require_access

# =================================
# Page configuration (MUST BE FIRST)
# =================================
st.set_page_config(
    page_title="Revisión de Órdenes",
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
require_access("revision_ordenes")

# =================================
# Top navigation
# =================================
if st.button("⬅ Volver al Dashboard"):
    st.switch_page("pages/dashboard.py")

st.divider()

# =================================
# Page title
# =================================
st.title("📋 Revisión de Órdenes (En Construcción)")

# =================================
# Load data from Google Sheets
# =================================
SHEET_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1RZ1YcLQxXI0U81Vle6cXmRp0yMxuRVg4"
    "/export?format=csv&gid=1578839108"
)

@st.cache_data(ttl=3600)
def cargar_ordenes():
    df = pd.read_csv(SHEET_URL)
    df.columns = df.columns.str.strip()
    return df

ordenes_df = cargar_ordenes()

st.success(f"Se cargaron {len(ordenes_df)} órdenes.")

# =================================
# Filtros
# =================================
st.subheader("Filtros")

empresas = ordenes_df["Empresa"].dropna().unique().tolist()
status = ordenes_df["Status CT"].dropna().unique().tolist()

f1, f2 = st.columns(2)

with f1:
    empresa_filter = st.selectbox(
        "Empresa",
        ["Todas"] + empresas
    )

with f2:
    status_filter = st.selectbox(
        "Status",
        ["Todos"] + status
    )

# =================================
# Apply filters
# =================================
df_filtrado = ordenes_df.copy()

if empresa_filter != "Todas":
    df_filtrado = df_filtrado[
        df_filtrado["Empresa"] == empresa_filter
    ]

if status_filter != "Todos":
    df_filtrado = df_filtrado[
        df_filtrado["Status CT"] == status_filter
    ]

# =================================
# Display table
# =================================
st.subheader("Órdenes")

st.dataframe(
    df_filtrado,
    use_container_width=True
)

# =================================
# Download CSV
# =================================
csv = df_filtrado.to_csv(index=False).encode("utf-8")

st.download_button(
    label="📥 Descargar CSV",
    data=csv,
    file_name="ordenes_filtradas.csv",
    mime="text/csv"
)
