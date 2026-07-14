import io
from datetime import datetime
import streamlit as st
import pandas as pd
from supabase import create_client
from auth import require_login, require_access
from pages.css import load_css

# =================================
# RELEASE CHANNEL
# =================================

APP_CHANNEL = "BETA"
# APP_CHANNEL = "RELEASE"

DASHBOARD_PAGE = (
    "pages/dashboard_beta.py"
    if APP_CHANNEL == "BETA"
    else "pages/dashboard.py"
)

# =================================
# Page configuration
# =================================
st.set_page_config(
    page_title="Consulta Bono Operadores",
    layout="wide"
)

# -------------------------------
# PAGE STYLE
# -------------------------------
load_css()

# =================================
# SECURITY
# =================================

require_login()
require_access("consulta_bonos_operador")

user = st.session_state.user

# =================================
# SUPABASE
# =================================

@st.cache_resource
def get_supabase():

    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_SERVICE_KEY"]
    )

supabase = get_supabase()

# =================================
# Navigation
# =================================
st.write("")
if st.button("⬅ Volver al Dashboard"):
    st.switch_page(DASHBOARD_PAGE)

st.divider()

# =================================
# TITLE
# =================================

st.title("💰 Consulta y Reportes Bono de Operadores")

# =================================
# LOAD DATA
# =================================

try:

    response = (
        supabase
        .table("bonos_operadores")
        .select("*")
        .order("fecha_registro", desc=True)
        .execute()
    )

    df = pd.DataFrame(response.data)

except Exception as e:

    st.error(f"Error cargando registros: {e}")
    st.stop()

if df.empty:

    st.warning("No existen formularios registrados.")
    st.stop()

# =================================
# KPIs
# =================================

bonos = df[df["monto"] >= 0]["monto"].sum()

descuentos = abs(
    df[df["monto"] < 0]["monto"].sum()
)

promedio = df["rendimiento_real"].mean()

k1,k2,k3,k4 = st.columns(4)

k1.metric(
    "Formularios",
    len(df)
)

k2.metric(
    "Bonos",
    f"${bonos:,.2f}"
)

k3.metric(
    "Descuentos",
    f"${descuentos:,.2f}"
)

k4.metric(
    "Rend. Promedio",
    f"{promedio:.2f} km/l"
)

st.divider()

# =================================
# FILTROS
# =================================

st.subheader("🔎 Filtros")

f1,f2,f3 = st.columns(3)

with f1:

    empresa = st.selectbox(
        "Empresa",
        ["Todas"] +
        sorted(df["empresa"].dropna().unique().tolist())
    )

with f2:

    unidad = st.selectbox(
        "Unidad",
        ["Todas"] +
        sorted(df["unidad"].dropna().unique().tolist())
    )

with f3:

    usuario = st.selectbox(
        "Usuario",
        ["Todos"] +
        sorted(df["usuario"].dropna().unique().tolist())
    )

f4,f5 = st.columns(2)

with f4:

    fecha_inicio = st.date_input(
        "Fecha Desde",
        value=pd.to_datetime(
            df["fecha_registro"]
        ).min()
    )

with f5:

    fecha_fin = st.date_input(
        "Fecha Hasta",
        value=pd.to_datetime(
            df["fecha_registro"]
        ).max()
    )

st.divider()

# =================================
# APPLY FILTERS
# =================================

filtered = df.copy()

filtered["fecha_registro"] = pd.to_datetime(
    filtered["fecha_registro"]
)

if empresa != "Todas":
    filtered = filtered[
        filtered["empresa"] == empresa
    ]

if unidad != "Todas":
    filtered = filtered[
        filtered["unidad"] == unidad
    ]

if usuario != "Todos":
    filtered = filtered[
        filtered["usuario"] == usuario
    ]

filtered = filtered[
    (
        filtered["fecha_registro"].dt.date
        >= fecha_inicio
    )
    &
    (
        filtered["fecha_registro"].dt.date
        <= fecha_fin
    )
]

# =================================
# TABLE TO DISPLAY
# =================================

tabla = filtered[[
    "fecha_registro",
    "empresa",
    "unidad",
    "usuario",
    "ruta",
    "tipo_ruta",
    "numero_trafico",
    "kilometros",
    "litros_cargados",
    "rendimiento_real",
    "monto"
]].copy()

tabla.columns = [
    "Fecha",
    "Empresa",
    "Unidad",
    "Usuario",
    "Ruta",
    "Tipo Ruta",
    "Tráfico",
    "Kilómetros",
    "Litros",
    "Rendimiento",
    "Monto"
]

st.subheader("📋 Formularios Registrados")

evento = st.dataframe(
    tabla,
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row"
)

# =================================
# DOWNLOAD REPORT
# =================================

st.divider()

excel_df = filtered.copy()

if "fecha_registro" in excel_df.columns:

    excel_df["fecha_registro"] = (
        pd.to_datetime(
            excel_df["fecha_registro"]
        )
        .dt.tz_localize(None)
    )

excel_buffer = io.BytesIO()

with pd.ExcelWriter(
    excel_buffer,
    engine="openpyxl"
) as writer:

    excel_df.to_excel(
        writer,
        sheet_name="Bonos",
        index=False
    )

st.download_button(
    "📥 Descargar Reporte",
    data=excel_buffer.getvalue(),
    file_name=f"Bonos_Operadores_{datetime.now():%Y%m%d}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True
)

# =================================
# DETALLE DEL REGISTRO
# =================================

if (
    evento.selection is not None
    and len(evento.selection["rows"]) > 0
):

    indice = evento.selection["rows"][0]

    registro = filtered.iloc[indice]

    st.divider()

    st.subheader("📄 Información del Registro")

    c1, c2, c3 = st.columns(3)

    with c1:

        st.text_input(
            "Fecha",
            value=str(registro["fecha_registro"]),
            disabled=True
        )

        st.text_input(
            "Usuario",
            value=str(registro["usuario"]),
            disabled=True
        )

        st.text_input(
            "Empresa",
            value=str(registro["empresa"]),
            disabled=True
        )

        st.text_input(
            "Unidad",
            value=str(registro["unidad"]),
            disabled=True
        )

        st.text_input(
            "VIN",
            value=str(registro["vin"]),
            disabled=True
        )

        st.text_input(
            "Placa",
            value=str(registro["placa_mex"]),
            disabled=True
        )

    with c2:

        st.text_input(
            "Marca",
            value=str(registro["marca"]),
            disabled=True
        )

        st.text_input(
            "Modelo",
            value=str(registro["modelo"]),
            disabled=True
        )

        st.text_input(
            "Motor",
            value=str(registro["motor"]),
            disabled=True
        )

        st.text_input(
            "Año",
            value=str(registro["anio"]),
            disabled=True
        )

        st.text_input(
            "Ruta",
            value=str(registro["ruta"]),
            disabled=True
        )

        st.text_input(
            "Tipo Ruta",
            value=str(registro["tipo_ruta"]),
            disabled=True
        )

    with c3:

        st.text_input(
            "Número Tráfico",
            value=str(registro["numero_trafico"]),
            disabled=True
        )

        st.text_input(
            "Kilómetros",
            value=f"{registro['kilometros']:,.2f}",
            disabled=True
        )

        st.text_input(
            "Litros Cargados",
            value=f"{registro['litros_cargados']:,.2f}",
            disabled=True
        )

        st.text_input(
            "Precio Diesel",
            value=f"${registro['precio_diesel']:,.2f}",
            disabled=True
        )

        st.text_input(
            "Monto",
            value=f"${registro['monto']:,.2f}",
            disabled=True
        )

st.divider()