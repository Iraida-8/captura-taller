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
# Hide sidebar
# =================================
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] { display: none; }

    div.stButton > button {
        height: 40px;
        font-size: 14px;
        font-weight: 500;
    }

    /* ONLY big buttons */
    .main-btn div.stButton > button {
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

# FORCE RESET EVERY TIME PAGE LOADS
if st.session_state.get("_reset_gestion_page", True):
    st.session_state.mode = None
    st.session_state["_reset_gestion_page"] = False

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
# Top navigation
# =================================
if st.button("⬅ Volver al Dashboard"):
    st.session_state.mode = None
    st.session_state["_reset_gestion_page"] = True
    st.switch_page("pages/dashboard.py")

st.divider()

st.title("📊 Consulta, Carga y Edición de Unidades")

if st.session_state.get("success_modal"):

    unidad = st.session_state.success_modal

    @st.dialog("Actualización exitosa")
    def success_modal():

        st.markdown(f"Unidad **{unidad}** actualizada correctamente.")

        if st.button("Aceptar", type="primary"):
            st.session_state.success_modal = None

    success_modal()

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

# =================================
# Session state
# =================================

st.session_state.setdefault("success_modal", None)

if "mode" not in st.session_state:
    st.session_state.mode = None

if "is_saving" not in st.session_state:
    st.session_state.is_saving = False

if "just_saved" not in st.session_state:
    st.session_state.just_saved = False

if "last_saved_unit" not in st.session_state:
    st.session_state.last_saved_unit = None

# =================================
# Buttons (ONLY THING VISIBLE INITIALLY)
# =================================
st.divider()

st.markdown('<div class="main-btn">', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    if st.button("Gestionar Unidades Existentes", use_container_width=True):
        st.session_state.mode = "gestionar"

with col2:
    if st.button("Crear Nuevas Unidades", use_container_width=True):
        st.session_state.mode = "crear"


# STOP HERE if nothing selected
if st.session_state.mode is None:
    st.stop()

df_units = load_vehicle_units()

st.markdown('</div>', unsafe_allow_html=True)

# =================================
# GESTIONAR
# =================================
if st.session_state.mode == "gestionar":

    st.subheader("Gestionar Unidades")

    # =============================
    # POST SAVE
    # =============================
    if st.session_state.just_saved:

        with st.spinner("Actualizando datos..."):
            time.sleep(2)

        st.cache_data.clear()

        unidad = st.session_state.last_saved_unit

        st.session_state.just_saved = False
        st.session_state.is_saving = False

        st.session_state.pop("empresa_select", None)
        st.session_state.pop("unidad_select", None)

        st.session_state.last_saved_unit = None

        st.session_state.show_toast = unidad

        st.rerun()

    if df_units.empty:
        st.warning("No hay datos.")
        st.stop()

    # =============================
    # Empresa mapping
    # =============================
    empresa_map = {
        "SET": "Set Freight International",
        "LIN": "Lincoln Freight",
        "PIC": "Picus",
        "IGT": "Igloo Transport",
        "SLP": "Set Logis Plus"
    }

    reverse_empresa_map = {v: k for k, v in empresa_map.items()}

    # =============================
    # Empresa selector
    # =============================
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

    # =============================
    # Unidad selector
    # =============================
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

    # =============================
    # FORM
    # =============================
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

            st.session_state.success_modal = unidad_selected
            st.rerun()