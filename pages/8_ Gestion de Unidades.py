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
# GESTIONAR EXISTENTES
# =================================
if st.session_state.mode == "gestionar":

    st.subheader("Editar Unidades")

    if df_units.empty:
        st.warning("No hay datos en la tabla vehicle_units.")
        st.stop()

    editable_df = st.data_editor(
        df_units,
        use_container_width=True,
        num_rows="dynamic",
        key="editor_unidades"
    )

    # =================================
    # Save Changes
    # =================================
    if st.button("Guardar Cambios"):

        updates = 0

        for i, row in editable_df.iterrows():

            original = df_units.iloc[i]

            if not row.equals(original):

                update_data = row.to_dict()

                # IMPORTANT: you need a unique identifier
                # assuming "unidad" is unique
                supabase.table("vehicle_units") \
                    .update(update_data) \
                    .eq("unidad", row["unidad"]) \
                    .execute()

                updates += 1

        st.success(f"{updates} registros actualizados correctamente.")

        # refresh cache
        st.cache_data.clear()
        st.rerun()