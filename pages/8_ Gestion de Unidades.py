import streamlit as st
import pandas as pd
from supabase import create_client
from auth import require_login, require_access

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
# Load Data BEFORE buttons
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
# Session state for mode
# =================================
if "mode" not in st.session_state:
    st.session_state.mode = None

# =================================
# Title
# =================================
st.title("Gestionador de Unidades")

# =================================
# Buttons
# =================================
col1, col2 = st.columns(2)

with col1:
    if st.button("Gestionar Unidades Existentes"):
        st.session_state.mode = "gestionar"

with col2:
    if st.button("Crear Nuevas Unidades"):
        st.session_state.mode = "crear"

# =================================
# GESTIONAR EXISTENTES (FORM MODE)
# =================================
if st.session_state.mode == "gestionar":

    st.subheader("Gestionar Unidades")

    if df_units.empty:
        st.warning("No hay datos en la tabla vehicle_units.")
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
    # Empresa selector (EMPTY DEFAULT)
    # =============================
    empresa_options = ["Selecciona empresa"] + list(empresa_map.values())

    empresa_nombre = st.selectbox(
        "Empresa",
        empresa_options,
        index=0
    )

    if empresa_nombre == "Selecciona empresa":
        st.info("Selecciona una empresa para continuar.")
        st.stop()

    empresa_codigo = reverse_empresa_map[empresa_nombre]

    # =============================
    # Filter unidades
    # =============================
    df_filtered = df_units[df_units["empresa"] == empresa_codigo]

    if df_filtered.empty:
        st.warning("No hay unidades para esta empresa.")
        st.stop()

    # =============================
    # Unidad selector (EMPTY DEFAULT)
    # =============================
    unidades_list = sorted(df_filtered["unidad"].dropna().unique().tolist())
    unidad_options = ["Selecciona unidad"] + unidades_list

    unidad_selected = st.selectbox(
        "Unidad",
        unidad_options,
        index=0
    )

    if unidad_selected == "Selecciona unidad":
        st.info("Selecciona una unidad para editar.")
        st.stop()

    # =============================
    # Get selected row
    # =============================
    selected_row = df_filtered[df_filtered["unidad"] == unidad_selected].iloc[0]

    st.divider()

    # =============================
    # FORM
    # =============================
    with st.form("form_editar_unidad"):

        col1, col2, col3 = st.columns(3)

        # Tipo Unidad options
        tipo_options = ["CAJA SECA", "CAJA REFRIGERADA", "TRACTOR"]

        # Find index safely
        try:
            tipo_index = tipo_options.index(selected_row["tipo_unidad"])
        except:
            tipo_index = 0

        with col1:
            marca = st.text_input("Marca", value=selected_row["marca"] or "")
            modelo = st.text_input("Modelo", value=selected_row["modelo"] or "")

        with col2:
            vin = st.text_input("VIN", value=selected_row["vin"] or "")
            tipo_unidad = st.selectbox(
                "Tipo Unidad",
                tipo_options,
                index=tipo_index
            )

        with col3:
            sucursal = st.text_input("Sucursal", value=selected_row["sucursal"] or "")
            estado = st.text_input("Estado", value=selected_row["estado"] or "")

        submitted = st.form_submit_button("Guardar Cambios")

        if submitted:

            update_data = {
                "empresa": empresa_codigo,
                "unidad": unidad_selected,
                "marca": marca,
                "modelo": modelo,
                "vin": vin,
                "tipo_unidad": tipo_unidad,
                "sucursal": sucursal,
                "estado": estado
            }

            supabase.table("vehicle_units") \
                .update(update_data) \
                .eq("unidad", unidad_selected) \
                .execute()

            st.success("Unidad actualizada correctamente.")

            st.cache_data.clear()
            st.rerun()