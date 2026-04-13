import streamlit as st
import pandas as pd
from supabase import create_client
from auth import require_login, require_access
import time

# =================================
# Page configuration
# =================================
st.set_page_config(
    page_title="Gestionador de Unidades",
    layout="wide"
)

# =================================
# Hide sidebar + FIX BUTTON SIZES
# =================================
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] { display: none; }

    /* ONLY make the 2 main buttons big */
    div.stButton > button[kind="secondary"] {
        height: 120px;
        font-size: 20px;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# =================================
# Security
# =================================
require_login()
require_access("gestion_unidades")

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
# Load Data
# =================================
@st.cache_data(ttl=60)
def load_vehicle_units():
    response = supabase.table("vehicle_units").select("*").execute()
    df = pd.DataFrame(response.data)

    if not df.empty:
        df.columns = [col.lower() for col in df.columns]

    return df

df_units = load_vehicle_units()

# =================================
# Session state
# =================================
if "mode" not in st.session_state:
    st.session_state.mode = None

if "is_saving" not in st.session_state:
    st.session_state.is_saving = False

if "just_saved" not in st.session_state:
    st.session_state.just_saved = False

if "last_saved_unit" not in st.session_state:
    st.session_state.last_saved_unit = None

# =================================
# ONLY 2 BUTTONS FIRST
# =================================
col1, col2 = st.columns(2)

with col1:
    if st.button("Gestionar Unidades Existentes", use_container_width=True, type="secondary"):
        st.session_state.mode = "gestionar"
        st.rerun()

with col2:
    if st.button("Crear Nuevas Unidades", use_container_width=True, type="secondary"):
        st.session_state.mode = "crear"
        st.rerun()

# HARD STOP → NOTHING ELSE RENDERS
if st.session_state.mode is None:
    st.stop()

# =================================
# NOW SHOW EVERYTHING ELSE
# =================================

# SMALL back button (default size now)
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

    if st.session_state.just_saved:

        with st.spinner("Actualizando datos..."):
            time.sleep(2)

        st.cache_data.clear()

        st.session_state.just_saved = False
        st.session_state.is_saving = False

        st.session_state.pop("empresa_select", None)
        st.session_state.pop("unidad_select", None)

        st.toast(
            f"Datos actualizados con éxito para la unidad {st.session_state.last_saved_unit}"
        )

        st.session_state.last_saved_unit = None
        st.rerun()

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

    reverse_empresa_map = {v: k for k, v in empresa_map.items()}

    empresa_options = ["Selecciona empresa"] + list(empresa_map.values())

    empresa_nombre = st.selectbox(
        "Empresa",
        empresa_options,
        index=0,
        key="empresa_select",
        disabled=st.session_state.is_saving
    )

    if empresa_nombre == "Selecciona empresa":
        st.stop()

    empresa_codigo = reverse_empresa_map[empresa_nombre]

    df_filtered = df_units[df_units["empresa"] == empresa_codigo]

    unidades = sorted(df_filtered["unidad"].dropna().unique().tolist())
    unidad_options = ["Selecciona unidad"] + unidades

    unidad_selected = st.selectbox(
        "Unidad",
        unidad_options,
        index=0,
        key="unidad_select",
        disabled=st.session_state.is_saving
    )

    if unidad_selected == "Selecciona unidad":
        st.stop()

    selected_row = df_filtered[df_filtered["unidad"] == unidad_selected].iloc[0]

    st.divider()

    with st.form("form"):

        col1, col2, col3 = st.columns(3)

        tipo_options = ["CAJA SECA", "CAJA REFRIGERADA", "TRACTOR"]

        tipo_db = str(selected_row["tipo_unidad"]).upper().strip()
        tipo_index = tipo_options.index(tipo_db) if tipo_db in tipo_options else 0

        with col1:
            marca = st.text_input("Marca", value=selected_row["marca"] or "")
            modelo = st.text_input("Modelo", value=selected_row["modelo"] or "")

        with col2:
            vin = st.text_input("VIN", value=selected_row["vin"] or "")
            tipo_unidad = st.selectbox("Tipo Unidad", tipo_options, index=tipo_index)

        with col3:
            sucursal = st.text_input("Sucursal", value=selected_row["sucursal"] or "")
            estado = st.text_input("Estado", value=selected_row["estado"] or "")

        submitted = st.form_submit_button("Guardar Cambios")

        if submitted:

            st.session_state.is_saving = True
            st.session_state.last_saved_unit = unidad_selected

            supabase.table("vehicle_units") \
                .update({
                    "empresa": empresa_codigo,
                    "unidad": unidad_selected,
                    "marca": marca,
                    "modelo": modelo,
                    "vin": vin,
                    "tipo_unidad": tipo_unidad,
                    "sucursal": sucursal,
                    "estado": estado
                }) \
                .eq("unidad", unidad_selected) \
                .execute()

            st.session_state.just_saved = True
            st.rerun()