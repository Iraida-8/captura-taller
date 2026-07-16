import streamlit as st
import pandas as pd
from supabase import create_client
from auth import require_login, require_access
from datetime import datetime, timezone
from pages.css import load_css
from io import BytesIO

# =================================
# RELEASE CHANNEL
# =================================

#APP_CHANNEL = "BETA"
APP_CHANNEL = "RELEASE"

DASHBOARD_PAGE = (
    "pages/dashboard_beta.py"
    if APP_CHANNEL == "BETA"
    else "pages/dashboard.py"
)

# =================================
# Page configuration
# =================================
st.set_page_config(
    page_title="Gestionador de Unidades",
    layout="wide"
)

# -------------------------------
# PAGE STYLE
# -------------------------------
load_css()

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
st.write("")
if st.button("⬅ Volver al Dashboard"):
    st.session_state.mode = None
    st.session_state["_reset_gestion_page"] = True
    st.switch_page(DASHBOARD_PAGE)

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

    # =================================
    # DOWNLOAD TABLE
    # =================================
    excel_buffer = BytesIO()

    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        df_display.to_excel(writer, index=False, sheet_name="Unidades")

    excel_buffer.seek(0)

    st.download_button(
        label="📥 Descargar Tabla",
        data=excel_buffer,
        file_name=f"Unidades_{empresa_codigo}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
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