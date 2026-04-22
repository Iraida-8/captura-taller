import streamlit as st
import pandas as pd
from supabase import create_client
from auth import require_login, require_access
from datetime import datetime, timezone
import time

# =================================
# Page configuration
# =================================
st.set_page_config(
    page_title="Gestionador de Unidades",
    layout="wide"
)

# =================================
# CSS THEME — BLUE + YELLOW
# =================================
st.markdown(
    """
    <style>

    /* Hide sidebar */
    [data-testid="stSidebar"] {
        display: none;
    }

    /* Main app background */
    .stApp {
        background-color: #151F6D;
    }

    /* Main container */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    /* Titles */
    h1 {
        color: #FFFFFF;
        font-size: 2rem;
        font-weight: 700;
    }

    h2, h3 {
        color: #BFA75F;
        font-weight: 600;
    }

    /* General text */
    p, label, span {
        color: #F5F5F5 !important;
    }

    /* Divider */
    hr {
        border-color: rgba(191, 167, 95, 0.25);
    }

    /* Standard buttons */
    div.stButton > button {
        height: 42px;
        font-size: 14px;
        font-weight: 600;
        border-radius: 12px;
        background-color: #1B267A;
        color: white;
        border: 1px solid rgba(191, 167, 95, 0.25);
        transition: all 0.2s ease;
    }

    div.stButton > button:hover {
        background-color: #24338C;
        border-color: #BFA75F;
        color: #BFA75F;
        transform: translateY(-1px);
    }

    /* Main module buttons */
    .main-btn div.stButton > button {
        height: 120px;
        font-size: 20px;
        font-weight: 700;
        border-radius: 18px;
        background-color: #1B267A;
        color: white;
        border: 1px solid rgba(191, 167, 95, 0.30);
        box-shadow: 0 6px 18px rgba(0,0,0,0.12);
    }

    .main-btn div.stButton > button:hover {
        background-color: #24338C;
        border-color: #BFA75F;
        color: #BFA75F;
        transform: translateY(-2px);
    }

    /* Inputs / Selects / Uploaders */
    div[data-baseweb="input"] > div,
    div[data-baseweb="select"] > div,
    [data-testid="stFileUploader"] {
        background-color: #1B267A !important;
        border: 1px solid rgba(191, 167, 95, 0.25) !important;
        border-radius: 12px !important;
        color: white !important;
    }

    input {
        color: white !important;
    }

    input::placeholder {
        color: #d0d0d0 !important;
    }

    div[data-baseweb="select"] * {
        color: white !important;
    }

    /* Dataframes */
    [data-testid="stDataFrame"] {
        border: 1px solid rgba(191, 167, 95, 0.20);
        border-radius: 12px;
        overflow: hidden;
    }

    /* Expanders */
    [data-testid="stExpander"] {
        background-color: #1B267A;
        border: 1px solid rgba(191, 167, 95, 0.20);
        border-radius: 14px;
    }

    /* Form container */
    form[data-testid="stForm"] {
        background-color: #1B267A;
        padding: 2rem;
        border-radius: 16px;
        border: 1px solid rgba(191, 167, 95, 0.20);
        box-shadow: 0 4px 14px rgba(0,0,0,0.10);
    }

    /* Save button */
    div[data-testid="stFormSubmitButton"] > button {
        border-radius: 12px;
        font-weight: 600;
        background-color: #BFA75F !important;
        color: #151F6D !important;
        border: none !important;
    }

    div[data-testid="stFormSubmitButton"] > button:hover {
        background-color: #d4bc73 !important;
        color: #151F6D !important;
    }

    /* Delete button inside form */
    div.stForm div[data-testid="column"]:nth-child(2) div.stButton > button {
        background-color: transparent !important;
        color: #BFA75F !important;
        border: 1px solid #BFA75F !important;
    }

    div.stForm div[data-testid="column"]:nth-child(2) div.stButton > button:hover {
        background-color: #BFA75F !important;
        color: #151F6D !important;
    }

    /* Secondary nav button */
    button[kind="secondary"] {
        background-color: transparent !important;
        color: #BFA75F !important;
        border: 1px solid #BFA75F !important;
    }

    button[kind="secondary"]:hover {
        background-color: #BFA75F !important;
        color: #151F6D !important;
    }

    /* Success / warning / info */
    div[data-baseweb="notification"] {
        border-radius: 12px;
    }

    /* Dialog modal */
    div[role="dialog"] {
        border-radius: 18px !important;
        border: 1px solid rgba(191, 167, 95, 0.20) !important;
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

st.title("📊 Gestión, Creación y Carga de Unidades")

if st.session_state.get("success_modal"):

    unidad = st.session_state.success_modal

    @st.dialog("Actualización exitosa")
    def success_modal():

        st.markdown(f"Unidad **{unidad}** actualizada correctamente.")

        if st.button("Aceptar", type="primary"):
            st.session_state.success_modal = None

            # RESET EVERYTHING
            st.session_state.mode = None
            st.session_state["_reset_gestion_page"] = True

            st.session_state.pop("empresa_select", None)
            st.session_state.pop("unidad_select", None)

            st.rerun()

    success_modal()

if st.session_state.get("delete_modal"):

    unidad = st.session_state.delete_modal

    @st.dialog("Confirmar eliminación")
    def delete_modal():

        st.markdown(f"""
        ¿Estás seguro que quieres eliminar la unidad **{unidad}**?

        **Esta acción es irreversible.**
        """)

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Cancelar"):
                st.session_state.delete_modal = None

        with col2:
            if st.button("Eliminar", type="primary"):

                supabase.table("vehicle_units") \
                    .delete() \
                    .eq("unidad", unidad) \
                    .execute()

                st.cache_data.clear()

                st.session_state.delete_modal = None

                # RESET PAGE
                st.session_state.mode = None
                st.session_state["_reset_gestion_page"] = True
                st.session_state.pop("empresa_select", None)
                st.session_state.pop("unidad_select", None)

                st.rerun()

    delete_modal()

# =================================
# Load Data
# =================================
@st.cache_data(ttl=60)
def load_vehicle_units():

    page_size = 1000
    start = 0
    all_rows = []

    while True:
        response = (
            supabase
            .table("vehicle_units")
            .select("*")
            .range(start, start + page_size - 1)
            .execute()
        )

        data = response.data

        if not data:
            break

        all_rows.extend(data)
        start += page_size

    df = pd.DataFrame(all_rows)

    if not df.empty:
        df.columns = [col.lower() for col in df.columns]

    return df

# =================================
# Session state
# =================================

st.session_state.setdefault("success_modal", None)

st.session_state.setdefault("delete_modal", None)

if "mode" not in st.session_state:
    st.session_state.mode = None

if "is_saving" not in st.session_state:
    st.session_state.is_saving = False

if "just_saved" not in st.session_state:
    st.session_state.just_saved = False

if "last_saved_unit" not in st.session_state:
    st.session_state.last_saved_unit = None

# =================================
# Buttons
# =================================
st.divider()

st.markdown('<div class="main-btn">', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("Gestionar Unidades Existentes", use_container_width=True):
        st.session_state.mode = "gestionar"

with col2:
    if st.button("Crear Nuevas Unidades", use_container_width=True):
        st.session_state.mode = "crear"

with col3:
    if st.button("Cargar Reporte de Unidades", use_container_width=True):
        st.session_state.mode = "cargar"


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
        disabled=False
    )

    if empresa_nombre == "Selecciona empresa":
        st.stop()

    empresa_codigo = reverse_empresa_map[empresa_nombre]

    # =============================
    # TABLE — UNIDADES
    # =============================
    st.divider()

    st.subheader("📄 Unidades de la empresa seleccionada")

    df_filtered = df_units[df_units["empresa"] == empresa_codigo]

    df_display = df_filtered.drop(columns=["id", "created_at"], errors="ignore")

    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
        height=300
    )

    # =============================
    # Unidad selector
    # =============================
    df_filtered = df_units[df_units["empresa"] == empresa_codigo]

    unidades = sorted(df_filtered["unidad"].dropna().unique().tolist())
    unidad_options = ["Selecciona unidad"] + unidades

    st.markdown("### 🔧 Selección de Unidad")

    st.caption("Selecciona unidad para editar")

    unidad_selected = st.selectbox(
        "",  # remove default label
        unidad_options,
        index=0,
        key="unidad_select",
        disabled=False
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
            estado_options = ["ACTIVA", "BAJA"]

            estado_db = str(selected_row["estado"]).upper().strip()
            estado_index = estado_options.index(estado_db) if estado_db in estado_options else 0

            estado = st.selectbox("Estado", estado_options, index=estado_index)

        col_btn1, col_btn2 = st.columns(2)

        with col_btn1:
            submitted = st.form_submit_button("Guardar Cambios", type="secondary")

        with col_btn2:
            delete_clicked = st.form_submit_button("Eliminar", type="primary")

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
                    "estado": estado,
                    "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f+00")
                }) \
                .eq("unidad", unidad_selected) \
                .execute()
            
            st.cache_data.clear()

            st.session_state.success_modal = unidad_selected
            st.rerun()
        
        if delete_clicked:
            st.session_state.delete_modal = unidad_selected
            st.rerun()
        
# =================================
# CREAR
# =================================
if st.session_state.mode == "crear":

    st.subheader("Crear Nueva Unidad")

    if df_units.empty:
        st.warning("No hay datos base.")
        st.stop()

    # =============================
    # Empresa mapping (same)
    # =============================
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
        key="empresa_crear"
    )

    if empresa_nombre == "Selecciona empresa":
        st.stop()

    empresa_codigo = reverse_empresa_map[empresa_nombre]

    st.divider()

    # =============================
    # FORM
    # =============================
    with st.form("crear_form"):

        col1, col2, col3 = st.columns(3)

        tipo_options = ["Selecciona tipo de unidad", "CAJA SECA", "CAJA REFRIGERADA", "TRACTOR"]

        with col1:
            unidad = st.text_input("Unidad")
            marca = st.text_input("Marca")
            modelo = st.text_input("Modelo")

        with col2:
            vin = st.text_input("VIN")
            tipo_unidad = st.selectbox("Tipo Unidad", tipo_options, index=0)

        with col3:
            sucursal = st.text_input("Sucursal")
            estado = st.text_input("Estado")

        submitted = st.form_submit_button("Crear Unidad")

        if submitted:

            if not unidad.strip():
                st.error("Unidad es obligatoria")
                st.stop()

            if tipo_unidad == "Selecciona tipo de unidad":
                st.error("Selecciona tipo de unidad")
                st.stop()

            # =============================
            # CHECK IF EXISTS
            # =============================
            exists = df_units[
                (df_units["empresa"] == empresa_codigo) &
                (df_units["unidad"].astype(str) == unidad.strip())
            ]

            if not exists.empty:
                st.error("La unidad ya existe para esta empresa")
                st.stop()

            # =============================
            # INSERT
            # =============================
            created_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f+00")

            supabase.table("vehicle_units").insert({
                "empresa": empresa_codigo,
                "unidad": unidad.strip(),
                "marca": marca,
                "modelo": modelo,
                "vin": vin,
                "tipo_unidad": tipo_unidad,
                "sucursal": sucursal,
                "estado": estado,
                "created_at": created_at
            }).execute()

            st.cache_data.clear()

            st.session_state.success_modal = unidad.strip()
            st.rerun()

# =================================
# CARGAR REPORTE DE UNIDADES
# =================================
if st.session_state.mode == "cargar":

    st.subheader("Cargar Reporte de Unidades")

    st.markdown("### 📂 Carga el reporte de unidades a actualizar o crear")

    uploaded_file = st.file_uploader(
        "Selecciona un archivo (.xlsx o .csv)",
        type=["xlsx", "csv"]
    )

    st.divider()

    df_preview = None

    if uploaded_file:
        st.success(f"Archivo cargado: {uploaded_file.name}")

        try:
            if uploaded_file.name.endswith(".csv"):
                df_preview = pd.read_csv(uploaded_file)
            else:
                df_preview = pd.read_excel(uploaded_file)

        except Exception as e:
            st.error(f"Error al leer el archivo: {e}")
            df_preview = None

    # ===============================
    # PREVIEW TABLE
    # ===============================
    if df_preview is not None and not df_preview.empty:

        with st.expander("📄 Vista previa del archivo", expanded=False):
            st.dataframe(
                df_preview,
                use_container_width=True,
                hide_index=True
            )

    # Dummy button (no logic yet)
    if st.button("Cargar datos", type="primary"):
        st.info("Funcionalidad aún no implementada")