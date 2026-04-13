import streamlit as st
import pandas as pd
from supabase import create_client
from auth import require_login, require_access
import time

# =================================
# CONFIG
# =================================
st.set_page_config(page_title="Gestionador de Unidades", layout="wide")

st.markdown(
    """
    <style>
    [data-testid="stSidebar"] { display: none; }

    /* ONLY main buttons big */
    div.stButton > button.main-btn {
        height: 120px;
        font-size: 20px;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# =================================
# SECURITY
# =================================
require_login()
require_access("gestion_unidades")

# =================================
# DB
# =================================
@st.cache_resource
def get_supabase():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_SERVICE_KEY"]
    )

supabase = get_supabase()

@st.cache_data(ttl=60)
def load_vehicle_units():
    response = supabase.table("vehicle_units").select("*").execute()
    df = pd.DataFrame(response.data)
    if not df.empty:
        df.columns = [c.lower() for c in df.columns]
    return df

df_units = load_vehicle_units()

# =================================
# STATE
# =================================
if "mode" not in st.session_state:
    st.session_state.mode = None

# =================================
# ========= ENTRY SCREEN ===========
# =================================
if st.session_state.mode is None:

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Gestionar Unidades Existentes", use_container_width=True):
            st.session_state.mode = "gestionar"
            st.rerun()

    with col2:
        if st.button("Crear Nuevas Unidades", use_container_width=True):
            st.session_state.mode = "crear"
            st.rerun()

    # 🔒 HARD STOP — NOTHING ELSE CAN RENDER
    st.stop()

# =================================
# ========= AFTER SELECTION =========
# =================================

# Back button (normal size)
if st.button("⬅ Volver al Dashboard"):
    st.session_state.mode = None
    st.rerun()

st.divider()
st.title("📊 Consulta, Carga y Edición de Unidades")

# =================================
# GESTIONAR
# =================================
if st.session_state.mode == "gestionar":

    st.subheader("Gestionar Unidades")

    if df_units.empty:
        st.warning("No hay datos.")
        st.stop()

    empresa_map = {
        "SET": "Set Freight International",
        "LIN": "Lincoln Freight",
        "PIC": "Picus",
        "IGT": "Igloo Transport",
        "SLP": "Set Logis Plus"
    }

    reverse_map = {v: k for k, v in empresa_map.items()}

    empresa = st.selectbox(
        "Empresa",
        ["Selecciona empresa"] + list(empresa_map.values())
    )

    if empresa == "Selecciona empresa":
        st.stop()

    codigo = reverse_map[empresa]

    df_filtered = df_units[df_units["empresa"] == codigo]

    unidad = st.selectbox(
        "Unidad",
        ["Selecciona unidad"] + sorted(df_filtered["unidad"].dropna().unique())
    )

    if unidad == "Selecciona unidad":
        st.stop()

    row = df_filtered[df_filtered["unidad"] == unidad].iloc[0]

    with st.form("form"):

        col1, col2, col3 = st.columns(3)

        with col1:
            marca = st.text_input("Marca", value=row["marca"] or "")
            modelo = st.text_input("Modelo", value=row["modelo"] or "")

        with col2:
            vin = st.text_input("VIN", value=row["vin"] or "")
            tipo = st.selectbox("Tipo Unidad", ["CAJA SECA", "CAJA REFRIGERADA", "TRACTOR"])

        with col3:
            sucursal = st.text_input("Sucursal", value=row["sucursal"] or "")
            estado = st.text_input("Estado", value=row["estado"] or "")

        if st.form_submit_button("Guardar Cambios"):

            supabase.table("vehicle_units") \
                .update({
                    "empresa": codigo,
                    "unidad": unidad,
                    "marca": marca,
                    "modelo": modelo,
                    "vin": vin,
                    "tipo_unidad": tipo,
                    "sucursal": sucursal,
                    "estado": estado
                }) \
                .eq("unidad", unidad) \
                .execute()

            st.success("Guardado correctamente")
            st.rerun()