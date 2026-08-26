import streamlit as st
import pandas as pd
from supabase import create_client
from auth import require_login, require_access
from datetime import datetime, timezone
from pages.css import load_css
from io import BytesIO
import numpy as np

# =================================
# RELEASE CHANNEL
# =================================

APP_CHANNEL = "BETA"
#APP_CHANNEL = "RELEASE"

DASHBOARD_PAGE = (
    "pages/dashboard_beta.py"
    if APP_CHANNEL == "BETA"
    else "pages/dashboard.py"
)

# =================================
# Page configuration
# =================================
st.set_page_config(
    page_title=(
        "GESTIÓN DE BASE DE DATOS BETA"
        if APP_CHANNEL.upper() == "BETA"
        else "GESTIÓN DE BASE DE DATOS"
    ),
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
current_user = st.session_state["user"]
is_admin = current_user.get("role") == "admin"

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

st.title("🗄️ GESTIÓN DE BASE DE DATOS")

# =================================
# TABS
# =================================

if is_admin:

    (
        tab_unidades,
        tab_refacciones,
        tab_proveedores,
        tab_tc,
        tab_directorio,
        tab_admin,
        tab_audit,
    ) = st.tabs([
        "Gestión, Creación y Carga de Unidades",
        "Refacciones",
        "Proveedores IVA",
        "TC Mensual",
        "Directorio Auxilio Carretero",
        "👤 Administración de Usuarios",
        "📋 Audit",
    ])

else:

    (
        tab_unidades,
        tab_refacciones,
        tab_proveedores,
        tab_tc,
        tab_directorio,
    ) = st.tabs([
        "Gestión, Creación y Carga de Unidades",
        "Refacciones",
        "Proveedores IVA",
        "TC Mensual",
        "Directorio Auxilio Carretero",
    ])

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
def load_table(table_name):

    page_size = 1000
    start = 0
    all_rows = []

    while True:
        response = (
            supabase
            .table(table_name)
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
# Activity Log
# =================================
def log_action(action, table_name, record_key, details):

    user = st.session_state["user"]

    user_id = user["id"]

    profile = (
        supabase
        .table("profiles")
        .select("full_name")
        .eq("id", user_id)
        .single()
        .execute()
    )

    full_name = profile.data["full_name"]

    supabase.table("audit_log").insert({

        "user_id": user_id,
        "user_name": full_name,
        "action": action,
        "table_name": table_name,
        "record_key": record_key,
        "details": details

    }).execute()

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

#loaders
df_units = load_table("vehicle_units")
df_parts = load_table("parts")
df_proveedores = load_table("proveedores_iva")
df_tc = load_table("tc_mensual")
df_directorio = load_table("directorio_auxilio_carretero")
df_directorio_911 = load_table("directorio_auxilio_carretero_911")
df_profiles = load_table("profiles") if is_admin else pd.DataFrame()
df_activity = load_table("user_activity_log") if is_admin else pd.DataFrame()
df_audit_log = load_table("audit_log") if is_admin else pd.DataFrame()
df_audit = load_table("AUDIT") if is_admin else pd.DataFrame()

# ==========================================
# UNIDADES
# ==========================================
with tab_unidades:

    st.subheader("Gestión, Creación y Carga de Unidades")

    # ==========================================
    # DOWNLOAD
    # ==========================================

    excel_buffer = BytesIO()

    df_download = df_units.drop(columns=["id"], errors="ignore")

    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        df_download.to_excel(
            writer,
            index=False,
            sheet_name="Unidades"
        )

    excel_buffer.seek(0)

    st.download_button(
        "📥 Descargar Tabla",
        data=excel_buffer,
        file_name="Vehicle_Units.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

    st.divider()

    # ==========================================
    # TABLE
    # ==========================================

    st.dataframe(
        df_download,
        use_container_width=True,
        hide_index=True,
        height=450,
    )

    st.divider()

    tab_add, tab_edit, tab_delete, tab_replace = st.tabs([
        "➕ Agregar Unidad",
        "✏️ Modificar Unidad",
        "🗑 Eliminar Unidad",
        "🔄 Reemplazar Tabla"
    ])

    # =====================================================
    # ADD
    # =====================================================

    with tab_add:

        empresa_map = {
            "SET": "Set Freight International",
            "LIN": "Lincoln Freight",
            "PIC": "Picus",
            "IGT": "Igloo Transport",
            "SLP": "Set Logis Plus"
        }

        reverse_empresa = {v: k for k, v in empresa_map.items()}

        with st.form("add_unit"):

            empresa_nombre = st.selectbox(
                "Empresa",
                list(empresa_map.values())
            )

            col1, col2, col3 = st.columns(3)

            with col1:
                unidad = st.text_input("Unidad")
                marca = st.text_input("Marca")

            with col2:
                modelo = st.text_input("Modelo")
                vin = st.text_input("VIN")

            with col3:

                tipo_unidad = st.selectbox(
                    "Tipo Unidad",
                    [
                        "CAJA SECA",
                        "CAJA REFRIGERADA",
                        "TRACTOR"
                    ]
                )

                sucursal = st.text_input("Sucursal")

                estado = st.selectbox(
                    "Estado",
                    [
                        "ACTIVA",
                        "BAJA"
                    ]
                )

            submitted = st.form_submit_button(
                "Agregar Unidad",
                use_container_width=True
            )

            if submitted:

                empresa = reverse_empresa[empresa_nombre]

                existe = df_units[
                    (df_units["empresa"] == empresa) &
                    (df_units["unidad"] == unidad)
                ]

                if not unidad.strip():

                    st.error("La unidad es obligatoria.")

                elif not existe.empty:

                    st.error("La unidad ya existe.")

                else:

                    supabase.table("vehicle_units").insert({

                        "empresa": empresa,
                        "unidad": unidad.strip(),
                        "marca": marca.strip(),
                        "modelo": modelo.strip(),
                        "vin": vin.strip(),
                        "tipo_unidad": tipo_unidad,
                        "sucursal": sucursal.strip(),
                        "estado": estado,
                        "created_at": datetime.now(timezone.utc).strftime(
                            "%Y-%m-%d %H:%M:%S.%f+00"
                        )

                    }).execute()

                    log_action(
                        "INSERT",
                        "vehicle_units",
                        unidad,
                        f"Agregó unidad {unidad}"
                    )

                    st.cache_data.clear()

                    st.success("Unidad agregada.")

                    st.rerun()

    # =====================================================
    # MODIFY
    # =====================================================

    with tab_edit:

        empresa_map = {
            "SET": "Set Freight International",
            "LIN": "Lincoln Freight",
            "PIC": "Picus",
            "IGT": "Igloo Transport",
            "SLP": "Set Logis Plus"
        }

        reverse_empresa = {v: k for k, v in empresa_map.items()}

        empresa_nombre = st.selectbox(
            "Empresa",
            list(empresa_map.values()),
            key="edit_empresa"
        )

        empresa_codigo = reverse_empresa[empresa_nombre]

        df_empresa = df_units[
            df_units["empresa"] == empresa_codigo
        ].sort_values("unidad")

        if df_empresa.empty:

            st.info("No existen unidades para esta empresa.")

        else:

            unidad = st.selectbox(
                "Unidad",
                df_empresa["unidad"].tolist(),
                key="edit_unidad"
            )

            row = df_empresa[
                df_empresa["unidad"] == unidad
            ].iloc[0]

            with st.form("edit_unit"):

                col1, col2, col3 = st.columns(3)

                with col1:

                    marca = st.text_input(
                        "Marca",
                        value=row["marca"] or ""
                    )

                    modelo = st.text_input(
                        "Modelo",
                        value=row["modelo"] or ""
                    )

                with col2:

                    vin = st.text_input(
                        "VIN",
                        value=row["vin"] or ""
                    )

                    tipo_options = [
                        "CAJA SECA",
                        "CAJA REFRIGERADA",
                        "TRACTOR"
                    ]

                    tipo_actual = str(
                        row["tipo_unidad"]
                    ).upper()

                    tipo_index = (
                        tipo_options.index(tipo_actual)
                        if tipo_actual in tipo_options
                        else 0
                    )

                    tipo_unidad = st.selectbox(
                        "Tipo Unidad",
                        tipo_options,
                        index=tipo_index
                    )

                with col3:

                    sucursal = st.text_input(
                        "Sucursal",
                        value=row["sucursal"] or ""
                    )

                    estado_options = [
                        "ACTIVA",
                        "BAJA"
                    ]

                    estado_actual = str(
                        row["estado"]
                    ).upper()

                    estado_index = (
                        estado_options.index(estado_actual)
                        if estado_actual in estado_options
                        else 0
                    )

                    estado = st.selectbox(
                        "Estado",
                        estado_options,
                        index=estado_index
                    )

                guardar = st.form_submit_button(
                    "Guardar Cambios",
                    use_container_width=True
                )

                if guardar:

                    supabase.table("vehicle_units") \
                        .update({

                            "marca": marca.strip(),
                            "modelo": modelo.strip(),
                            "vin": vin.strip(),
                            "tipo_unidad": tipo_unidad,
                            "sucursal": sucursal.strip(),
                            "estado": estado

                        }) \
                        .eq("id", row["id"]) \
                        .execute()
                    
                    log_action(
                        "UPDATE",
                        "vehicle_units",
                        unidad,
                        f"Modificó unidad {unidad}"
                    )

                    st.cache_data.clear()

                    st.success("Unidad actualizada.")

                    st.rerun()

    # =====================================================
    # DELETE
    # =====================================================

    with tab_delete:

        empresa_map = {
            "SET": "Set Freight International",
            "LIN": "Lincoln Freight",
            "PIC": "Picus",
            "IGT": "Igloo Transport",
            "SLP": "Set Logis Plus"
        }

        reverse_empresa = {v: k for k, v in empresa_map.items()}

        empresa_nombre = st.selectbox(
            "Empresa",
            list(empresa_map.values()),
            key="delete_empresa"
        )

        empresa_codigo = reverse_empresa[empresa_nombre]

        df_empresa = (
            df_units[df_units["empresa"] == empresa_codigo]
            .sort_values("unidad")
        )

        if df_empresa.empty:

            st.info("No existen unidades para esta empresa.")

        else:

            unidad = st.selectbox(
                "Unidad",
                df_empresa["unidad"].tolist(),
                key="delete_unidad"
            )

            row = df_empresa[
                df_empresa["unidad"] == unidad
            ].iloc[0]

            st.warning(
                f"⚠️ Se eliminará la unidad **{unidad}** de forma permanente."
            )

            if st.button(
                "🗑 Eliminar Unidad",
                type="primary",
                use_container_width=True,
                key="delete_unit_button"
            ):

                supabase.table("vehicle_units") \
                    .delete() \
                    .eq("id", row["id"]) \
                    .execute()
                
                log_action(
                    "DELETE",
                    "vehicle_units",
                    unidad,
                    f"Eliminó unidad {unidad}"
                )

                st.cache_data.clear()

                st.success("Unidad eliminada correctamente.")

                st.rerun()

    # =====================================================
    # REPLACE TABLE
    # =====================================================

    with tab_replace:

        st.warning(
            "⚠️ Esta acción eliminará TODAS las unidades actuales y las reemplazará con el archivo cargado."
        )

        uploaded = st.file_uploader(
            "Selecciona el archivo",
            type=["xlsx", "csv"],
            key="vehicle_units_replace"
        )

        if uploaded:

            try:

                if uploaded.name.endswith(".csv"):
                    new_df = pd.read_csv(uploaded)
                else:
                    new_df = pd.read_excel(uploaded)

            except Exception as e:

                st.error(f"No fue posible leer el archivo.\n\n{e}")
                st.stop()

            st.subheader("Vista previa")

            st.dataframe(
                new_df,
                use_container_width=True,
                hide_index=True,
                height=350,
            )

            if st.button(
                "🔄 Reemplazar Tabla Completa",
                type="primary",
                use_container_width=True,
                key="replace_vehicle_units"
            ):

                new_df.columns = [
                    c.strip().lower()
                    for c in new_df.columns
                ]

                required = {
                    "empresa",
                    "unidad",
                    "marca",
                    "modelo",
                    "vin",
                    "tipo_unidad",
                    "sucursal",
                    "estado"
                }

                if not required.issubset(set(new_df.columns)):

                    st.error(
                        "El archivo no contiene las columnas requeridas."
                    )
                    st.stop()

                records = (
                    new_df[
                        [
                            "empresa",
                            "unidad",
                            "marca",
                            "modelo",
                            "vin",
                            "tipo_unidad",
                            "sucursal",
                            "estado",
                        ]
                    ]
                    .fillna("")
                    .to_dict("records")
                )

                # Delete existing rows
                supabase.table("vehicle_units") \
                    .delete() \
                    .neq("unidad", "") \
                    .execute()

                # Add timestamps
                now = datetime.now(timezone.utc).strftime(
                    "%Y-%m-%d %H:%M:%S.%f+00"
                )

                for record in records:
                    record["created_at"] = now

                if records:
                    supabase.table("vehicle_units") \
                        .insert(records) \
                        .execute()
                    
                log_action(
                    "REPLACE",
                    "vehicle_units",
                    f"{len(records)} registros",
                    f"Reemplazó completamente la tabla vehicle_units"
                )

                st.cache_data.clear()

                st.success(
                    f"Se cargaron correctamente {len(records)} unidades."
                )

                st.rerun()

# ==========================================
# REFACCIONES
# ==========================================
with tab_refacciones:

    st.subheader("Refacciones")

    # ==========================================
    # DOWNLOAD TABLE
    # ==========================================
    excel_buffer = BytesIO()

    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        df_parts.to_excel(writer, index=False, sheet_name="Refacciones")

    excel_buffer.seek(0)

    st.download_button(
        "📥 Descargar Tabla",
        data=excel_buffer,
        file_name="Refacciones.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

    st.divider()

    # ==========================================
    # TABLE
    # ==========================================
    st.dataframe(
        df_parts,
        use_container_width=True,
        hide_index=True,
        height=400,
    )

    st.divider()

    # ==========================================
    # SUB TABS
    # ==========================================
    tab_add, tab_edit, tab_delete, tab_replace = st.tabs([
        "➕ Agregar Refacción",
        "✏️ Modificar Refacción",
        "🗑 Eliminar Refacción",
        "🔄 Reemplazar Tabla"
    ])

    # =====================================================
    # ADD
    # =====================================================
    with tab_add:

        with st.form("add_part"):

            parte = st.text_input("Parte")
            tipo = st.text_input("Tipo")

            submitted = st.form_submit_button(
                "Agregar Refacción",
                use_container_width=True
            )

            if submitted:

                if not parte.strip():
                    st.error("La parte es obligatoria.")
                else:

                    existe = (
                        supabase
                        .table("parts")
                        .select("parte")
                        .eq("parte", parte)
                        .execute()
                    )

                    if existe.data:
                        st.error("La parte ya existe.")
                    else:

                        supabase.table("parts").insert({
                            "parte": parte.strip(),
                            "tipo": tipo.strip()
                        }).execute()

                        log_action(
                            "INSERT",
                            "parts",
                            parte.strip(),
                            f"Agregó refacción {parte.strip()}"
                        )

                        st.cache_data.clear()
                        st.success("Refacción agregada.")
                        st.rerun()

    # =====================================================
    # EDIT
    # =====================================================
    with tab_edit:

        if df_parts.empty:

            st.info("No hay refacciones.")

        else:

            selected = st.selectbox(
                "Selecciona la refacción",
                sorted(df_parts["parte"].tolist()),
                key="edit_part"
            )

            row = df_parts[
                df_parts["parte"] == selected
            ].iloc[0]

            with st.form("edit_part_form"):

                parte = st.text_input(
                    "Parte",
                    value=row["parte"]
                )

                tipo = st.text_input(
                    "Tipo",
                    value=row["tipo"]
                )

                submitted = st.form_submit_button(
                    "Guardar Cambios",
                    use_container_width=True
                )

                if submitted:

                    if not parte.strip():

                        st.error("La parte es obligatoria.")

                    else:

                        duplicate = df_parts[
                            (df_parts["parte"] == parte.strip()) &
                            (df_parts["parte"] != selected)
                        ]

                        if not duplicate.empty:

                            st.error("Ya existe una refacción con ese nombre.")

                        else:

                            supabase.table("parts") \
                                .update({
                                    "parte": parte.strip(),
                                    "tipo": tipo.strip()
                                }) \
                                .eq("parte", selected) \
                                .execute()
                            
                            log_action(
                                "UPDATE",
                                "parts",
                                parte.strip(),
                                f"Modificó refacción {parte.strip()}"
                            )

                            st.cache_data.clear()

                            st.success("Refacción actualizada.")

                            st.rerun()

    # =====================================================
    # DELETE
    # =====================================================
    with tab_delete:

        if df_parts.empty:

            st.info("No hay refacciones.")

        else:

            selected = st.selectbox(
                "Selecciona la refacción",
                sorted(df_parts["parte"].tolist())
            )

            if st.button(
                "Eliminar Refacción",
                type="primary",
                use_container_width=True
            ):

                supabase.table("parts") \
                    .delete() \
                    .eq("parte", selected) \
                    .execute()

                log_action(
                    "DELETE",
                    "parts",
                    selected,
                    f"Eliminó refacción {selected}"
                )

                st.cache_data.clear()
                st.success("Refacción eliminada.")
                st.rerun()

    # =====================================================
    # REPLACE TABLE
    # =====================================================
    with tab_replace:

        st.warning(
            "⚠️ Esta acción eliminará TODAS las refacciones actuales y las reemplazará con el archivo cargado."
        )

        uploaded = st.file_uploader(
            "Selecciona el archivo",
            type=["xlsx", "csv"],
            key="parts_replace"
        )

        if uploaded:

            if uploaded.name.endswith(".csv"):
                new_df = pd.read_csv(uploaded)
            else:
                new_df = pd.read_excel(uploaded)

            st.subheader("Vista previa")

            st.dataframe(
                new_df,
                use_container_width=True,
                hide_index=True,
                height=300,
            )

            if st.button(
                "Reemplazar Tabla Completa",
                type="primary",
                use_container_width=True
            ):

                required = {"parte", "tipo"}

                if not required.issubset(set(new_df.columns.str.lower())):
                    st.error("El archivo debe contener las columnas: parte y tipo.")
                    st.stop()

                new_df.columns = [c.lower() for c in new_df.columns]

                supabase.table("parts").delete().neq("parte", "").execute()

                records = new_df[["parte", "tipo"]].fillna("").to_dict("records")

                if records:
                    supabase.table("parts").insert(records).execute()

                log_action(
                    "REPLACE",
                    "parts",
                    f"{len(records)} registros",
                    "Reemplazó completamente la tabla parts"
                )

                st.cache_data.clear()

                st.success("Tabla reemplazada correctamente.")

                st.rerun()

# ==========================================
# PROVEEDORES
# ==========================================
with tab_proveedores:

    st.subheader("Proveedores IVA")

    # ==========================================
    # DOWNLOAD TABLE
    # ==========================================
    excel_buffer = BytesIO()

    df_download = df_proveedores.drop(columns=["id"], errors="ignore")

    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        df_download.to_excel(
            writer,
            index=False,
            sheet_name="Proveedores IVA"
        )

    excel_buffer.seek(0)

    st.download_button(
        "📥 Descargar Tabla",
        data=excel_buffer,
        file_name="Proveedores_IVA.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

    st.divider()

    # ==========================================
    # TABLE
    # ==========================================
    st.dataframe(
        df_download,
        use_container_width=True,
        hide_index=True,
        height=400,
    )

    st.divider()

    tab_add, tab_edit, tab_delete, tab_replace = st.tabs([
        "➕ Agregar Proveedor",
        "✏️ Modificar Proveedor",
        "🗑 Eliminar Proveedor",
        "🔄 Reemplazar Tabla"
    ])

    # =====================================================
    # ADD
    # =====================================================
    with tab_add:

        with st.form("add_supplier"):

            proveedor = st.text_input("Proveedor")
            clave = st.text_input("Clave")

            col1, col2 = st.columns(2)

            with col1:
                iva_pct = st.number_input(
                    "IVA %",
                    value=16.0,
                    step=0.01,
                    format="%.2f"
                )

            with col2:
                isr_pct = st.number_input(
                    "ISR %",
                    value=0.0,
                    step=0.01,
                    format="%.2f"
                )

            formula = st.text_input("Fórmula")

            submitted = st.form_submit_button(
                "Agregar Proveedor",
                use_container_width=True
            )

            if submitted:

                if not proveedor.strip():

                    st.error("El proveedor es obligatorio.")

                elif not df_proveedores[
                    df_proveedores["proveedor"] == proveedor.strip()
                ].empty:

                    st.error("El proveedor ya existe.")

                else:

                    supabase.table("proveedores_iva").insert({

                        "proveedor": proveedor.strip(),
                        "iva_pct": iva_pct,
                        "isr_pct": isr_pct,
                        "formula": formula.strip(),
                        "clave": clave.strip()

                    }).execute()

                    log_action(
                        "INSERT",
                        "proveedores_iva",
                        proveedor.strip(),
                        f"Agregó proveedor {proveedor.strip()}"
                    )

                    st.cache_data.clear()
                    st.success("Proveedor agregado.")
                    st.rerun()

    # =====================================================
    # EDIT
    # =====================================================
    with tab_edit:

        if df_proveedores.empty:

            st.info("No existen proveedores.")

        else:

            selected = st.selectbox(
                "Selecciona el proveedor",
                sorted(df_proveedores["proveedor"].tolist()),
                key="edit_supplier"
            )

            row = df_proveedores[
                df_proveedores["proveedor"] == selected
            ].iloc[0]

            with st.form("edit_supplier_form"):

                proveedor = st.text_input(
                    "Proveedor",
                    value=row["proveedor"]
                )

                clave = st.text_input(
                    "Clave",
                    value=row["clave"]
                )

                col1, col2 = st.columns(2)

                with col1:

                    iva_pct = st.number_input(
                        "IVA %",
                        value=float(row["iva_pct"]),
                        step=0.01,
                        format="%.2f"
                    )

                with col2:

                    isr_pct = st.number_input(
                        "ISR %",
                        value=float(row["isr_pct"]),
                        step=0.01,
                        format="%.2f"
                    )

                formula = st.text_input(
                    "Fórmula",
                    value=row["formula"]
                )

                submitted = st.form_submit_button(
                    "Guardar Cambios",
                    use_container_width=True
                )

                if submitted:

                    duplicate = df_proveedores[
                        (df_proveedores["proveedor"] == proveedor.strip()) &
                        (df_proveedores["proveedor"] != selected)
                    ]

                    if not duplicate.empty():

                        st.error("Ese proveedor ya existe.")

                    else:

                        supabase.table("proveedores_iva") \
                            .update({

                                "proveedor": proveedor.strip(),
                                "iva_pct": iva_pct,
                                "isr_pct": isr_pct,
                                "formula": formula.strip(),
                                "clave": clave.strip()

                            }) \
                            .eq("id", row["id"]) \
                            .execute()

                        log_action(
                            "UPDATE",
                            "proveedores_iva",
                            proveedor.strip(),
                            f"Modificó proveedor {proveedor.strip()}"
                        )

                        st.cache_data.clear()
                        st.success("Proveedor actualizado.")
                        st.rerun()

    # =====================================================
    # DELETE
    # =====================================================
    with tab_delete:

        if df_proveedores.empty:

            st.info("No existen proveedores.")

        else:

            selected = st.selectbox(
                "Selecciona el proveedor",
                sorted(df_proveedores["proveedor"].tolist()),
                key="delete_supplier"
            )

            row = df_proveedores[
                df_proveedores["proveedor"] == selected
            ].iloc[0]

            if st.button(
                "🗑 Eliminar Proveedor",
                type="primary",
                use_container_width=True
            ):

                supabase.table("proveedores_iva") \
                    .delete() \
                    .eq("id", row["id"]) \
                    .execute()
                
                log_action(
                    "DELETE",
                    "proveedores_iva",
                    selected,
                    f"Eliminó proveedor {selected}"
                )

                st.cache_data.clear()
                st.success("Proveedor eliminado.")
                st.rerun()

    # =====================================================
    # REPLACE TABLE
    # =====================================================
    with tab_replace:

        st.warning(
            "⚠️ Esta acción reemplazará completamente la tabla."
        )

        uploaded = st.file_uploader(
            "Selecciona el archivo",
            type=["xlsx", "csv"],
            key="proveedores_replace"
        )

        if uploaded:

            if uploaded.name.endswith(".csv"):
                new_df = pd.read_csv(uploaded)
            else:
                new_df = pd.read_excel(uploaded)

            st.dataframe(
                new_df,
                use_container_width=True,
                hide_index=True,
                height=300
            )

            if st.button(
                "🔄 Reemplazar Tabla",
                type="primary",
                use_container_width=True
            ):

                new_df.columns = [
                    c.lower().strip()
                    for c in new_df.columns
                ]

                required = {
                    "proveedor",
                    "iva_pct",
                    "isr_pct",
                    "formula",
                    "clave"
                }

                if not required.issubset(set(new_df.columns)):

                    st.error("El archivo no contiene las columnas requeridas.")
                    st.stop()

                records_df = new_df[
                    [
                        "proveedor",
                        "iva_pct",
                        "isr_pct",
                        "formula",
                        "clave"
                    ]
                ].copy()

                records_df["clave"] = (
                    pd.to_numeric(records_df["clave"], errors="coerce")
                    .round()
                    .astype("Int64")
                )

                records_df = records_df.replace({np.nan: None})

                records = records_df.where(pd.notnull(records_df), None).to_dict("records")

                supabase.table("proveedores_iva") \
                    .delete() \
                    .neq("id", 0) \
                    .execute()

                if records:

                    try:
                        supabase.table("proveedores_iva") \
                            .insert(records) \
                            .execute()

                    except Exception as e:
                        st.exception(e)
                        st.stop()
                    
                log_action(
                    "REPLACE",
                    "proveedores_iva",
                    f"{len(records)} registros",
                    "Reemplazó completamente la tabla proveedores_iva"
                )

                st.cache_data.clear()

                st.success(
                    f"Se cargaron {len(records)} proveedores."
                )

                st.rerun()

# ==========================================
# TC MENSUAL
# ==========================================
with tab_tc:

    st.subheader("TC Mensual")

    # ==========================================
    # DOWNLOAD
    # ==========================================
    excel_buffer = BytesIO()

    df_download = df_tc.drop(columns=["id"], errors="ignore")

    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        df_download.to_excel(
            writer,
            index=False,
            sheet_name="TC Mensual"
        )

    excel_buffer.seek(0)

    st.download_button(
        "📥 Descargar Tabla",
        data=excel_buffer,
        file_name="TC_Mensual.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

    st.divider()

    # ==========================================
    # TABLE
    # ==========================================
    st.dataframe(
        df_download,
        use_container_width=True,
        hide_index=True,
        height=400,
    )

    st.divider()

    tab_add, tab_edit, tab_delete, tab_replace = st.tabs([
        "➕ Agregar TC",
        "✏️ Modificar TC",
        "🗑 Eliminar TC",
        "🔄 Reemplazar Tabla"
    ])

    months = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December"
    ]

    # =====================================================
    # ADD
    # =====================================================
    with tab_add:

        with st.form("add_tc"):

            year = st.number_input(
                "Año",
                min_value=2020,
                max_value=2100,
                value=datetime.now().year,
                step=1
            )

            month = st.selectbox(
                "Mes",
                months
            )

            tc = st.number_input(
                "Tipo de Cambio",
                min_value=0.0,
                step=0.0001,
                format="%.4f"
            )

            submitted = st.form_submit_button(
                "Agregar Registro",
                use_container_width=True
            )

            if submitted:

                supabase.table("tc_mensual").insert({

                    "YEAR": int(year),
                    "MONTH": month,
                    "DATE": datetime.now().strftime("%Y-%m-%d"),
                    "TC": tc

                }).execute()

                log_action(
                    "INSERT",
                    "tc_mensual",
                    f"{year} - {month}",
                    f"Agregó TC {month} {year}"
                )

                st.cache_data.clear()

                st.success("Registro agregado.")

                st.rerun()

    # =====================================================
    # EDIT
    # =====================================================
    with tab_edit:

        if df_tc.empty:

            st.info("No existen registros.")

        else:

            df_sorted = df_tc.sort_values(
                ["year", "month", "date"],
                ascending=False
            )

            selected = st.selectbox(
                "Selecciona el registro",
                df_sorted["date"].astype(str).tolist(),
                key="edit_tc"
            )

            row = df_sorted[
                df_sorted["date"].astype(str) == selected
            ].iloc[0]

            with st.form("edit_tc_form"):

                st.text_input(
                    "Fecha de Captura",
                    value=str(row["date"]),
                    disabled=True
                )

                year = st.number_input(
                    "Año",
                    min_value=2020,
                    max_value=2100,
                    value=int(row["year"]),
                    step=1
                )

                month = st.selectbox(
                    "Mes",
                    months,
                    index=months.index(row["month"])
                    if row["month"] in months else 0
                )

                tc = st.number_input(
                    "Tipo de Cambio",
                    value=float(row["tc"]),
                    step=0.0001,
                    format="%.4f"
                )

                submitted = st.form_submit_button(
                    "Guardar Cambios",
                    use_container_width=True
                )

                if submitted:

                    supabase.table("tc_mensual") \
                        .update({

                            "YEAR": int(year),
                            "MONTH": month,
                            "TC": tc

                        }) \
                        .eq("id", row["id"]) \
                        .execute()
                    
                    log_action(
                        "UPDATE",
                        "tc_mensual",
                        f"{year} - {month}",
                        f"Modificó TC {month} {year}"
                    )

                    st.cache_data.clear()

                    st.success("Registro actualizado.")

                    st.rerun()

    # =====================================================
    # DELETE
    # =====================================================
    with tab_delete:

        if df_tc.empty:

            st.info("No existen registros.")

        else:

            df_sorted = df_tc.sort_values(
                ["year", "date"],
                ascending=False
            ).copy()

            df_sorted["display"] = (
                df_sorted["year"].astype(str)
                + " - "
                + df_sorted["month"].astype(str)
            )

            selected = st.selectbox(
                "Selecciona el registro",
                df_sorted["display"].tolist(),
                key="delete_tc"
            )

            row = df_sorted[
                df_sorted["display"] == selected
            ].iloc[0]

            st.warning(
                f"⚠️ Se eliminará el registro **{selected}**."
            )

            if st.button(
                "🗑 Eliminar Registro",
                type="primary",
                use_container_width=True
            ):

                supabase.table("tc_mensual") \
                    .delete() \
                    .eq("id", row["id"]) \
                    .execute()
                
                log_action(
                    "DELETE",
                    "tc_mensual",
                    selected,
                    f"Eliminó TC {selected}"
                )                

                st.cache_data.clear()

                st.success("Registro eliminado.")

                st.rerun()

    # =====================================================
    # REPLACE TABLE
    # =====================================================
    with tab_replace:

        st.warning(
            "⚠️ Esta acción reemplazará completamente la tabla."
        )

        uploaded = st.file_uploader(
            "Selecciona el archivo",
            type=["xlsx", "csv"],
            key="tc_replace"
        )

        if uploaded:

            if uploaded.name.endswith(".csv"):
                new_df = pd.read_csv(uploaded)
            else:
                new_df = pd.read_excel(uploaded)

            st.dataframe(
                new_df,
                use_container_width=True,
                hide_index=True,
                height=300,
            )

            if st.button(
                "🔄 Reemplazar Tabla",
                type="primary",
                use_container_width=True
            ):

                new_df.columns = [
                    c.strip().upper()
                    for c in new_df.columns
                ]

                required = {
                    "YEAR",
                    "MONTH",
                    "DATE",
                    "TC"
                }

                if not required.issubset(set(new_df.columns)):

                    st.error(
                        "El archivo no contiene las columnas requeridas."
                    )

                    st.stop()

                records = (
                    new_df[
                        [
                            "YEAR",
                            "MONTH",
                            "DATE",
                            "TC"
                        ]
                    ]
                    .fillna("")
                    .to_dict("records")
                )

                supabase.table("tc_mensual") \
                    .delete() \
                    .neq("id", 0) \
                    .execute()

                if records:

                    supabase.table("tc_mensual") \
                        .insert(records) \
                        .execute()
                    
                log_action(
                    "REPLACE",
                    "tc_mensual",
                    f"{len(records)} registros",
                    "Reemplazó completamente la tabla tc_mensual"
                )

                st.cache_data.clear()

                st.success(
                    f"Se cargaron {len(records)} registros."
                )

                st.rerun()

# ==========================================
# DIRECTORIO AUXILIO CARRETERO
# ==========================================
with tab_directorio:

    tab_directorio_1, tab_directorio_911 = st.tabs(["Directorio", "Auxilio Carretero 911"])

    with tab_directorio_1:


            st.subheader("Directorio Auxilio Carretero")

            directorio_columns = [
                "id",
                "estado",
                "ciudad_municipio",
                "corredor",
                "categoria",
                "proveedor",
                "telefono_principal",
                "telefono_alterno_whatsapp",
                "direccion",
                "horario",
                "servicio_movil",
                "equipo_pesado",
                "cobertura_declarada",
                "servicios",
                "precio_criterio",
                "calificacion_publica",
                "resenas",
                "nivel",
                "validacion_telefonica",
                "fecha_verificacion_web",
                "proximidad_uso_sugerido",
                "busqueda_en_maps",
            ]

            directorio_labels = {
                "id": "ID",
                "estado": "Estado",
                "ciudad_municipio": "Ciudad / municipio",
                "corredor": "Corredor",
                "categoria": "Categoría",
                "proveedor": "Proveedor",
                "telefono_principal": "Teléfono principal",
                "telefono_alterno_whatsapp": "Teléfono alterno / WhatsApp",
                "direccion": "Dirección",
                "horario": "Horario",
                "servicio_movil": "Servicio móvil",
                "equipo_pesado": "Equipo pesado",
                "cobertura_declarada": "Cobertura declarada",
                "servicios": "Servicios",
                "precio_criterio": "Precio / criterio",
                "calificacion_publica": "Calificación pública",
                "resenas": "Reseñas",
                "nivel": "Nivel",
                "validacion_telefonica": "Validación telefónica",
                "fecha_verificacion_web": "Fecha verificación web",
                "proximidad_uso_sugerido": "Proximidad / uso sugerido",
                "busqueda_en_maps": "Búsqueda en Maps",
            }

            directorio_excel_map = {
                "ID": "id",
                "Estado": "estado",
                "Ciudad / municipio": "ciudad_municipio",
                "Corredor": "corredor",
                "Categoría": "categoria",
                "Proveedor": "proveedor",
                "Teléfono principal": "telefono_principal",
                "Teléfono alterno / WhatsApp": "telefono_alterno_whatsapp",
                "Dirección": "direccion",
                "Horario": "horario",
                "Servicio móvil": "servicio_movil",
                "Equipo pesado": "equipo_pesado",
                "Cobertura declarada": "cobertura_declarada",
                "Servicios": "servicios",
                "Precio / criterio": "precio_criterio",
                "Calificación pública": "calificacion_publica",
                "Reseñas": "resenas",
                "Nivel": "nivel",
                "Validación telefónica": "validacion_telefonica",
                "Fecha verificación web": "fecha_verificacion_web",
                "Proximidad / uso sugerido": "proximidad_uso_sugerido",
                "Búsqueda en Maps": "busqueda_en_maps",
            }

            # ==========================================
            # DOWNLOAD TABLE
            # ==========================================
            excel_buffer = BytesIO()

            df_directorio_download = (
                df_directorio.reindex(columns=directorio_columns)
                if not df_directorio.empty
                else pd.DataFrame(columns=directorio_columns)
            )

            df_directorio_download = df_directorio_download.rename(
                columns=directorio_labels
            )

            with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
                df_directorio_download.to_excel(
                    writer,
                    index=False,
                    sheet_name="Directorio",
                )

            excel_buffer.seek(0)

            st.download_button(
                "📥 Descargar Tabla",
                data=excel_buffer,
                file_name="Directorio_Auxilio_Carretero.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

            st.divider()

            # ==========================================
            # TABLE
            # ==========================================
            st.dataframe(
                df_directorio_download,
                use_container_width=True,
                hide_index=True,
                height=450,
            )

            st.divider()

            tab_add, tab_edit, tab_delete, tab_replace = st.tabs([
                "➕ Agregar Entrada",
                "✏️ Modificar Entrada",
                "🗑 Eliminar Entrada",
                "🔄 Reemplazar Tabla",
            ])

            # =====================================================
            # ADD
            # =====================================================
            with tab_add:

                with st.form("add_directorio"):

                    st.markdown("##### Información de la entrada")

                    col1, col2, col3 = st.columns(3)

                    with col1:
                        dir_id = st.text_input("ID")
                        estado = st.text_input("Estado")
                        ciudad_municipio = st.text_input("Ciudad / municipio")
                        corredor = st.text_input("Corredor")
                        categoria = st.text_input("Categoría")
                        proveedor = st.text_input("Proveedor")
                        telefono_principal = st.text_input("Teléfono principal")
                        telefono_alterno_whatsapp = st.text_input(
                            "Teléfono alterno / WhatsApp"
                        )

                    with col2:
                        direccion = st.text_input("Dirección")
                        horario = st.text_input("Horario")
                        servicio_movil = st.text_input("Servicio móvil")
                        equipo_pesado = st.text_input("Equipo pesado")
                        cobertura_declarada = st.text_input("Cobertura declarada")
                        servicios = st.text_area("Servicios")
                        precio_criterio = st.text_input("Precio / criterio")

                    with col3:
                        calificacion_publica = st.number_input(
                            "Calificación pública",
                            min_value=0.0,
                            max_value=5.0,
                            value=0.0,
                            step=0.1,
                            format="%.1f",
                        )
                        resenas = st.text_input("Reseñas")
                        nivel = st.text_input("Nivel")
                        validacion_telefonica = st.text_input(
                            "Validación telefónica"
                        )
                        fecha_verificacion_web = st.date_input(
                            "Fecha verificación web",
                            value=datetime.now().date(),
                        )
                        proximidad_uso_sugerido = st.text_area(
                            "Proximidad / uso sugerido"
                        )
                        busqueda_en_maps = st.text_input("Búsqueda en Maps")

                    submitted = st.form_submit_button(
                        "Agregar Entrada",
                        use_container_width=True,
                    )

                    if submitted:

                        dir_id = dir_id.strip()

                        if not dir_id:
                            st.error("El ID es obligatorio.")

                        elif not proveedor.strip():
                            st.error("El proveedor es obligatorio.")

                        elif not df_directorio[
                            df_directorio["id"].astype(str) == dir_id
                        ].empty:
                            st.error("Ya existe una entrada con ese ID.")

                        else:

                            record = {
                                "id": dir_id,
                                "estado": estado.strip(),
                                "ciudad_municipio": ciudad_municipio.strip(),
                                "corredor": corredor.strip(),
                                "categoria": categoria.strip(),
                                "proveedor": proveedor.strip(),
                                "telefono_principal": telefono_principal.strip(),
                                "telefono_alterno_whatsapp": telefono_alterno_whatsapp.strip(),
                                "direccion": direccion.strip(),
                                "horario": horario.strip(),
                                "servicio_movil": servicio_movil.strip(),
                                "equipo_pesado": equipo_pesado.strip(),
                                "cobertura_declarada": cobertura_declarada.strip(),
                                "servicios": servicios.strip(),
                                "precio_criterio": precio_criterio.strip(),
                                "calificacion_publica": float(calificacion_publica),
                                "resenas": resenas.strip(),
                                "nivel": nivel.strip(),
                                "validacion_telefonica": validacion_telefonica.strip(),
                                "fecha_verificacion_web": fecha_verificacion_web.isoformat(),
                                "proximidad_uso_sugerido": proximidad_uso_sugerido.strip(),
                                "busqueda_en_maps": busqueda_en_maps.strip(),
                            }

                            supabase.table(
                                "directorio_auxilio_carretero"
                            ).insert(record).execute()

                            log_action(
                                "INSERT",
                                "directorio_auxilio_carretero",
                                dir_id,
                                f"Agregó entrada {dir_id} - {proveedor.strip()}",
                            )

                            st.cache_data.clear()
                            st.success("Entrada agregada correctamente.")
                            st.rerun()

            # =====================================================
            # EDIT
            # =====================================================
            with tab_edit:

                if df_directorio.empty:

                    st.info("No existen entradas en el directorio.")

                else:

                    df_directorio_edit = df_directorio.copy()

                    df_directorio_edit["display"] = (
                        df_directorio_edit["id"].astype(str)
                        + " — "
                        + df_directorio_edit["proveedor"].fillna("").astype(str)
                    )

                    selected_display = st.selectbox(
                        "Selecciona la entrada",
                        df_directorio_edit["display"].tolist(),
                        key="edit_directorio",
                    )

                    row = df_directorio_edit[
                        df_directorio_edit["display"] == selected_display
                    ].iloc[0]

                    def _str_value(value):
                        if pd.isna(value):
                            return ""
                        return str(value)

                    with st.form("edit_directorio_form"):

                        st.markdown(
                            f"##### Modificando: `{row['id']}`"
                        )

                        col1, col2, col3 = st.columns(3)

                        with col1:
                            dir_id = st.text_input(
                                "ID",
                                value=_str_value(row["id"]),
                            )
                            estado = st.text_input(
                                "Estado",
                                value=_str_value(row["estado"]),
                            )
                            ciudad_municipio = st.text_input(
                                "Ciudad / municipio",
                                value=_str_value(row["ciudad_municipio"]),
                            )
                            corredor = st.text_input(
                                "Corredor",
                                value=_str_value(row["corredor"]),
                            )
                            categoria = st.text_input(
                                "Categoría",
                                value=_str_value(row["categoria"]),
                            )
                            proveedor = st.text_input(
                                "Proveedor",
                                value=_str_value(row["proveedor"]),
                            )
                            telefono_principal = st.text_input(
                                "Teléfono principal",
                                value=_str_value(row["telefono_principal"]),
                            )
                            telefono_alterno_whatsapp = st.text_input(
                                "Teléfono alterno / WhatsApp",
                                value=_str_value(row["telefono_alterno_whatsapp"]),
                            )

                        with col2:
                            direccion = st.text_input(
                                "Dirección",
                                value=_str_value(row["direccion"]),
                            )
                            horario = st.text_input(
                                "Horario",
                                value=_str_value(row["horario"]),
                            )
                            servicio_movil = st.text_input(
                                "Servicio móvil",
                                value=_str_value(row["servicio_movil"]),
                            )
                            equipo_pesado = st.text_input(
                                "Equipo pesado",
                                value=_str_value(row["equipo_pesado"]),
                            )
                            cobertura_declarada = st.text_input(
                                "Cobertura declarada",
                                value=_str_value(row["cobertura_declarada"]),
                            )
                            servicios = st.text_area(
                                "Servicios",
                                value=_str_value(row["servicios"]),
                            )
                            precio_criterio = st.text_input(
                                "Precio / criterio",
                                value=_str_value(row["precio_criterio"]),
                            )

                        with col3:
                            try:
                                calificacion_value = float(row["calificacion_publica"])
                                if pd.isna(calificacion_value):
                                    calificacion_value = 0.0
                            except (TypeError, ValueError):
                                calificacion_value = 0.0

                            calificacion_publica = st.number_input(
                                "Calificación pública",
                                min_value=0.0,
                                max_value=5.0,
                                value=calificacion_value,
                                step=0.1,
                                format="%.1f",
                            )

                            resenas = st.text_input(
                                "Reseñas",
                                value=_str_value(row["resenas"]),
                            )
                            nivel = st.text_input(
                                "Nivel",
                                value=_str_value(row["nivel"]),
                            )
                            validacion_telefonica = st.text_input(
                                "Validación telefónica",
                                value=_str_value(row["validacion_telefonica"]),
                            )

                            try:
                                fecha_actual = pd.to_datetime(
                                    row["fecha_verificacion_web"]
                                ).date()
                            except (TypeError, ValueError):
                                fecha_actual = datetime.now().date()

                            fecha_verificacion_web = st.date_input(
                                "Fecha verificación web",
                                value=fecha_actual,
                            )
                            proximidad_uso_sugerido = st.text_area(
                                "Proximidad / uso sugerido",
                                value=_str_value(row["proximidad_uso_sugerido"]),
                            )
                            busqueda_en_maps = st.text_input(
                                "Búsqueda en Maps",
                                value=_str_value(row["busqueda_en_maps"]),
                            )

                        submitted = st.form_submit_button(
                            "Guardar Cambios",
                            use_container_width=True,
                        )

                        if submitted:

                            dir_id = dir_id.strip()

                            duplicate = df_directorio[
                                (df_directorio["id"].astype(str) == dir_id)
                                & (df_directorio["id"].astype(str) != str(row["id"]))
                            ]

                            if not dir_id:
                                st.error("El ID es obligatorio.")

                            elif not proveedor.strip():
                                st.error("El proveedor es obligatorio.")

                            elif not duplicate.empty:
                                st.error("Ya existe otra entrada con ese ID.")

                            else:

                                update_data = {
                                    "id": dir_id,
                                    "estado": estado.strip(),
                                    "ciudad_municipio": ciudad_municipio.strip(),
                                    "corredor": corredor.strip(),
                                    "categoria": categoria.strip(),
                                    "proveedor": proveedor.strip(),
                                    "telefono_principal": telefono_principal.strip(),
                                    "telefono_alterno_whatsapp": telefono_alterno_whatsapp.strip(),
                                    "direccion": direccion.strip(),
                                    "horario": horario.strip(),
                                    "servicio_movil": servicio_movil.strip(),
                                    "equipo_pesado": equipo_pesado.strip(),
                                    "cobertura_declarada": cobertura_declarada.strip(),
                                    "servicios": servicios.strip(),
                                    "precio_criterio": precio_criterio.strip(),
                                    "calificacion_publica": float(calificacion_publica),
                                    "resenas": resenas.strip(),
                                    "nivel": nivel.strip(),
                                    "validacion_telefonica": validacion_telefonica.strip(),
                                    "fecha_verificacion_web": fecha_verificacion_web.isoformat(),
                                    "proximidad_uso_sugerido": proximidad_uso_sugerido.strip(),
                                    "busqueda_en_maps": busqueda_en_maps.strip(),
                                }

                                supabase.table(
                                    "directorio_auxilio_carretero"
                                ).update(update_data).eq(
                                    "id", row["id"]
                                ).execute()

                                log_action(
                                    "UPDATE",
                                    "directorio_auxilio_carretero",
                                    dir_id,
                                    f"Modificó entrada {dir_id} - {proveedor.strip()}",
                                )

                                st.cache_data.clear()
                                st.success("Entrada actualizada correctamente.")
                                st.rerun()

            # =====================================================
            # DELETE
            # =====================================================
            with tab_delete:

                if df_directorio.empty:

                    st.info("No existen entradas en el directorio.")

                else:

                    df_directorio_delete = df_directorio.copy()

                    df_directorio_delete["display"] = (
                        df_directorio_delete["id"].astype(str)
                        + " — "
                        + df_directorio_delete["proveedor"].fillna("").astype(str)
                    )

                    selected_display = st.selectbox(
                        "Selecciona la entrada",
                        df_directorio_delete["display"].tolist(),
                        key="delete_directorio",
                    )

                    row = df_directorio_delete[
                        df_directorio_delete["display"] == selected_display
                    ].iloc[0]

                    st.warning(
                        f"⚠️ Se eliminará permanentemente la entrada "
                        f"**{row['id']} — {row['proveedor']}**."
                    )

                    if st.button(
                        "🗑 Eliminar Entrada",
                        type="primary",
                        use_container_width=True,
                        key="delete_directorio_button",
                    ):

                        supabase.table(
                            "directorio_auxilio_carretero"
                        ).delete().eq(
                            "id", row["id"]
                        ).execute()

                        log_action(
                            "DELETE",
                            "directorio_auxilio_carretero",
                            str(row["id"]),
                            f"Eliminó entrada {row['id']} - {row['proveedor']}",
                        )

                        st.cache_data.clear()
                        st.success("Entrada eliminada correctamente.")
                        st.rerun()

            # =====================================================
            # REPLACE TABLE
            # =====================================================
            with tab_replace:

                st.warning(
                    "⚠️ Esta acción eliminará TODAS las entradas actuales "
                    "y las reemplazará con el archivo cargado."
                )

                uploaded = st.file_uploader(
                    "Selecciona el archivo",
                    type=["xlsx", "csv"],
                    key="directorio_replace",
                )

                if uploaded:

                    try:
                        if uploaded.name.lower().endswith(".csv"):
                            new_df = pd.read_csv(uploaded)
                        else:
                            # Sheet 1 / first worksheet
                            new_df = pd.read_excel(uploaded, sheet_name=0)

                    except Exception as e:
                        st.error(
                            f"No fue posible leer el archivo.\n\n{e}"
                        )
                        st.stop()

                    # Accept either the Supabase column names or the
                    # original Excel headers from "Directorio".
                    new_df.columns = [
                        str(c).strip()
                        for c in new_df.columns
                    ]

                    if set(directorio_excel_map).issubset(set(new_df.columns)):
                        new_df = new_df.rename(
                            columns=directorio_excel_map
                        )
                    else:
                        new_df.columns = [
                            str(c).strip().lower()
                            for c in new_df.columns
                        ]

                    st.subheader("Vista previa")

                    preview = new_df.rename(
                        columns=directorio_labels
                    )

                    st.dataframe(
                        preview,
                        use_container_width=True,
                        hide_index=True,
                        height=350,
                    )

                    if st.button(
                        "🔄 Reemplazar Tabla Completa",
                        type="primary",
                        use_container_width=True,
                        key="replace_directorio",
                    ):

                        required = set(directorio_columns)

                        if not required.issubset(set(new_df.columns)):

                            missing = sorted(
                                required - set(new_df.columns)
                            )

                            st.error(
                                "El archivo no contiene todas las columnas requeridas.\n\n"
                                f"Faltantes: {', '.join(missing)}"
                            )
                            st.stop()

                        records_df = new_df[
                            directorio_columns
                        ].copy()

                        # ID and text fields
                        text_columns = [
                            c for c in directorio_columns
                            if c not in {
                                "calificacion_publica",
                                "fecha_verificacion_web",
                            }
                        ]

                        for column in text_columns:
                            records_df[column] = (
                                records_df[column]
                                .where(records_df[column].notna(), "")
                                .astype(str)
                                .str.strip()
                            )

                        # Numeric rating
                        records_df["calificacion_publica"] = pd.to_numeric(
                            records_df["calificacion_publica"],
                            errors="coerce",
                        )

                        records_df["calificacion_publica"] = (
                            records_df["calificacion_publica"]
                            .where(
                                records_df["calificacion_publica"].notna(),
                                None,
                            )
                        )

                        # Date
                        records_df["fecha_verificacion_web"] = (
                            pd.to_datetime(
                                records_df["fecha_verificacion_web"],
                                errors="coerce",
                            )
                            .dt.strftime("%Y-%m-%d")
                        )

                        records_df["fecha_verificacion_web"] = (
                            records_df["fecha_verificacion_web"]
                            .where(
                                records_df["fecha_verificacion_web"].notna(),
                                None,
                            )
                        )

                        records = records_df.to_dict(
                            "records"
                        )

                        # Remove NaN/NaT values that Supabase cannot accept.
                        cleaned_records = []

                        for record in records:
                            cleaned = {}

                            for key, value in record.items():

                                if pd.isna(value):
                                    cleaned[key] = None
                                else:
                                    cleaned[key] = value

                            cleaned_records.append(cleaned)

                        # Validate IDs before deleting existing data.
                        ids = [
                            str(record["id"]).strip()
                            for record in cleaned_records
                        ]

                        if any(not record_id for record_id in ids):
                            st.error(
                                "Todas las entradas deben tener un ID."
                            )
                            st.stop()

                        if len(ids) != len(set(ids)):
                            st.error(
                                "El archivo contiene IDs duplicados."
                            )
                            st.stop()

                        if any(
                            not str(record["proveedor"]).strip()
                            for record in cleaned_records
                        ):
                            st.error(
                                "Todas las entradas deben tener un proveedor."
                            )
                            st.stop()

                        try:

                            # Delete existing rows
                            supabase.table(
                                "directorio_auxilio_carretero"
                            ).delete().neq(
                                "id", ""
                            ).execute()

                            # Insert replacement data
                            if cleaned_records:
                                supabase.table(
                                    "directorio_auxilio_carretero"
                                ).insert(
                                    cleaned_records
                                ).execute()

                        except Exception as e:

                            st.exception(e)
                            st.stop()

                        log_action(
                            "REPLACE",
                            "directorio_auxilio_carretero",
                            f"{len(cleaned_records)} registros",
                            "Reemplazó completamente la tabla "
                            "directorio_auxilio_carretero",
                        )

                        st.cache_data.clear()

                        st.success(
                            f"Se cargaron correctamente "
                            f"{len(cleaned_records)} entradas."
                        )

                        st.rerun()


        # ==========================================
    # =====================================================
    # AUXILIO CARRETERO 911
    # =====================================================
    with tab_directorio_911:

        st.subheader("Auxilio Carretero 911")

        directorio_911_columns = [
            "id",
            "estado_ambito",
            "corredor",
            "contacto",
            "principal",
            "alterno",
            "servicio",
            "horario",
            "fuente",
            "nivel",
            "observaciones",
        ]

        directorio_911_labels = {
            "id": "ID",
            "estado_ambito": "Estado / ámbito",
            "corredor": "Corredor",
            "contacto": "Contacto",
            "principal": "Principal",
            "alterno": "Alterno",
            "servicio": "Servicio",
            "horario": "Horario",
            "fuente": "Fuente",
            "nivel": "Nivel",
            "observaciones": "Observaciones",
        }

        # ==========================================
        # DOWNLOAD TABLE
        # ==========================================
        excel_buffer = BytesIO()

        df_911_download = (
            df_directorio_911.reindex(columns=directorio_911_columns)
            if not df_directorio_911.empty
            else pd.DataFrame(columns=directorio_911_columns)
        )

        df_911_download = df_911_download.rename(
            columns=directorio_911_labels
        )

        with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
            df_911_download.to_excel(
                writer,
                index=False,
                sheet_name="Auxilio 911",
            )

        excel_buffer.seek(0)

        st.download_button(
            "📥 Descargar Tabla",
            data=excel_buffer,
            file_name="Directorio_Auxilio_Carretero_911.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

        st.divider()

        # ==========================================
        # TABLE
        # ==========================================
        st.dataframe(
            df_911_download,
            use_container_width=True,
            hide_index=True,
            height=400,
        )

        st.divider()

        tab_911_add, tab_911_edit, tab_911_delete, tab_911_replace = st.tabs([
            "➕ Agregar Entrada",
            "✏️ Modificar Entrada",
            "🗑 Eliminar Entrada",
            "🔄 Reemplazar Tabla",
        ])

        # =====================================================
        # ADD
        # =====================================================
        with tab_911_add:

            with st.form("add_directorio_911"):

                col1, col2, col3 = st.columns(3)

                with col1:
                    estado_ambito = st.text_input("Estado / ámbito")
                    corredor = st.text_input("Corredor")
                    contacto = st.text_input("Contacto")
                    principal = st.text_input("Principal")

                with col2:
                    alterno = st.text_input("Alterno")
                    servicio = st.text_input("Servicio")
                    horario = st.text_input("Horario")
                    fuente = st.text_input("Fuente")

                with col3:
                    nivel = st.text_input("Nivel")
                    observaciones = st.text_area("Observaciones")

                submitted = st.form_submit_button(
                    "Agregar Entrada",
                    use_container_width=True,
                )

                if submitted:

                    duplicate = df_directorio_911[
                        (df_directorio_911["estado_ambito"].fillna("").astype(str).str.strip().str.lower() == estado_ambito.strip().lower())
                        & (df_directorio_911["corredor"].fillna("").astype(str).str.strip().str.lower() == corredor.strip().lower())
                        & (df_directorio_911["contacto"].fillna("").astype(str).str.strip().str.lower() == contacto.strip().lower())
                    ]

                    if not estado_ambito.strip():
                        st.error("El Estado / ámbito es obligatorio.")

                    elif not contacto.strip():
                        st.error("El contacto es obligatorio.")

                    elif not duplicate.empty:
                        st.error("Ya existe una entrada con el mismo Estado / ámbito, Corredor y Contacto.")

                    else:

                        record = {
                            "estado_ambito": estado_ambito.strip(),
                            "corredor": corredor.strip(),
                            "contacto": contacto.strip(),
                            "principal": principal.strip(),
                            "alterno": alterno.strip(),
                            "servicio": servicio.strip(),
                            "horario": horario.strip(),
                            "fuente": fuente.strip(),
                            "nivel": nivel.strip(),
                            "observaciones": observaciones.strip(),
                        }

                        supabase.table(
                            "directorio_auxilio_carretero_911"
                        ).insert(record).execute()

                        log_action(
                            "INSERT",
                            "directorio_auxilio_carretero_911",
                            f"{estado_ambito.strip()} - {contacto.strip()}",
                            f"Agregó entrada 911: {contacto.strip()}",
                        )

                        st.cache_data.clear()
                        st.success("Entrada agregada correctamente.")
                        st.rerun()

        # =====================================================
        # EDIT
        # =====================================================
        with tab_911_edit:

            if df_directorio_911.empty:

                st.info("No existen entradas en el directorio 911.")

            else:

                df_911_edit = df_directorio_911.copy()

                df_911_edit["display"] = (
                    df_911_edit["id"].astype(str)
                    + " — "
                    + df_911_edit["contacto"].fillna("").astype(str)
                    + " — "
                    + df_911_edit["corredor"].fillna("").astype(str)
                )

                selected_display = st.selectbox(
                    "Selecciona la entrada",
                    df_911_edit["display"].tolist(),
                    key="edit_directorio_911",
                )

                row = df_911_edit[
                    df_911_edit["display"] == selected_display
                ].iloc[0]

                def _str_911(value):
                    if pd.isna(value):
                        return ""
                    return str(value)

                with st.form("edit_directorio_911_form"):

                    st.markdown(
                        f"##### Modificando: `{row['contacto']}`"
                    )

                    col1, col2, col3 = st.columns(3)

                    with col1:
                        estado_ambito = st.text_input(
                            "Estado / ámbito",
                            value=_str_911(row["estado_ambito"]),
                        )
                        corredor = st.text_input(
                            "Corredor",
                            value=_str_911(row["corredor"]),
                        )
                        contacto = st.text_input(
                            "Contacto",
                            value=_str_911(row["contacto"]),
                        )
                        principal = st.text_input(
                            "Principal",
                            value=_str_911(row["principal"]),
                        )

                    with col2:
                        alterno = st.text_input(
                            "Alterno",
                            value=_str_911(row["alterno"]),
                        )
                        servicio = st.text_input(
                            "Servicio",
                            value=_str_911(row["servicio"]),
                        )
                        horario = st.text_input(
                            "Horario",
                            value=_str_911(row["horario"]),
                        )
                        fuente = st.text_input(
                            "Fuente",
                            value=_str_911(row["fuente"]),
                        )

                    with col3:
                        nivel = st.text_input(
                            "Nivel",
                            value=_str_911(row["nivel"]),
                        )
                        observaciones = st.text_area(
                            "Observaciones",
                            value=_str_911(row["observaciones"]),
                        )

                    submitted = st.form_submit_button(
                        "Guardar Cambios",
                        use_container_width=True,
                    )

                    if submitted:

                        duplicate = df_directorio_911[
                            (df_directorio_911["id"].astype(str) != str(row["id"]))
                            & (
                                df_directorio_911["estado_ambito"].fillna("").astype(str).str.strip().str.lower()
                                == estado_ambito.strip().lower()
                            )
                            & (
                                df_directorio_911["corredor"].fillna("").astype(str).str.strip().str.lower()
                                == corredor.strip().lower()
                            )
                            & (
                                df_directorio_911["contacto"].fillna("").astype(str).str.strip().str.lower()
                                == contacto.strip().lower()
                            )
                        ]

                        if not estado_ambito.strip():
                            st.error("El Estado / ámbito es obligatorio.")

                        elif not contacto.strip():
                            st.error("El contacto es obligatorio.")

                        elif not duplicate.empty:
                            st.error("Ya existe otra entrada con el mismo Estado / ámbito, Corredor y Contacto.")

                        else:

                            update_data = {
                                "estado_ambito": estado_ambito.strip(),
                                "corredor": corredor.strip(),
                                "contacto": contacto.strip(),
                                "principal": principal.strip(),
                                "alterno": alterno.strip(),
                                "servicio": servicio.strip(),
                                "horario": horario.strip(),
                                "fuente": fuente.strip(),
                                "nivel": nivel.strip(),
                                "observaciones": observaciones.strip(),
                            }

                            supabase.table(
                                "directorio_auxilio_carretero_911"
                            ).update(update_data).eq(
                                "id", row["id"]
                            ).execute()

                            log_action(
                                "UPDATE",
                                "directorio_auxilio_carretero_911",
                                str(row["id"]),
                                f"Modificó entrada 911: {contacto.strip()}",
                            )

                            st.cache_data.clear()
                            st.success("Entrada actualizada correctamente.")
                            st.rerun()

        # =====================================================
        # DELETE
        # =====================================================
        with tab_911_delete:

            if df_directorio_911.empty:

                st.info("No existen entradas en el directorio 911.")

            else:

                df_911_delete = df_directorio_911.copy()

                df_911_delete["display"] = (
                    df_911_delete["id"].astype(str)
                    + " — "
                    + df_911_delete["contacto"].fillna("").astype(str)
                    + " — "
                    + df_911_delete["corredor"].fillna("").astype(str)
                )

                selected_display = st.selectbox(
                    "Selecciona la entrada",
                    df_911_delete["display"].tolist(),
                    key="delete_directorio_911",
                )

                row = df_911_delete[
                    df_911_delete["display"] == selected_display
                ].iloc[0]

                st.warning(
                    f"⚠️ Se eliminará permanentemente la entrada "
                    f"**{row['contacto']} — {row['corredor']}**."
                )

                if st.button(
                    "🗑 Eliminar Entrada",
                    type="primary",
                    use_container_width=True,
                    key="delete_directorio_911_button",
                ):

                    supabase.table(
                        "directorio_auxilio_carretero_911"
                    ).delete().eq(
                        "id", row["id"]
                    ).execute()

                    log_action(
                        "DELETE",
                        "directorio_auxilio_carretero_911",
                        str(row["id"]),
                        f"Eliminó entrada 911: {row['contacto']}",
                    )

                    st.cache_data.clear()
                    st.success("Entrada eliminada correctamente.")
                    st.rerun()

        # =====================================================
        # REPLACE TABLE
        # =====================================================
        with tab_911_replace:

            st.warning(
                "⚠️ Esta acción eliminará TODAS las entradas 911 "
                "y las reemplazará con el archivo cargado."
            )

            uploaded = st.file_uploader(
                "Selecciona el archivo",
                type=["xlsx", "csv"],
                key="directorio_911_replace",
            )

            if uploaded:

                try:
                    if uploaded.name.lower().endswith(".csv"):
                        new_df = pd.read_csv(uploaded, encoding="utf-8-sig")
                    else:
                        new_df = pd.read_excel(uploaded, sheet_name=0)

                except Exception as e:
                    st.error(
                        f"No fue posible leer el archivo.\n\n{e}"
                    )
                    st.stop()

                # Accept original CSV headers or Supabase column names.
                new_df.columns = [
                    str(c).strip()
                    for c in new_df.columns
                ]

                header_map_911 = {
                    "Estado / ámbito": "estado_ambito",
                    "Corredor": "corredor",
                    "Contacto": "contacto",
                    "Principal": "principal",
                    "Alterno": "alterno",
                    "Servicio": "servicio",
                    "Horario": "horario",
                    "Fuente": "fuente",
                    "Nivel": "nivel",
                    "Observaciones": "observaciones",
                }

                if set(header_map_911).issubset(set(new_df.columns)):
                    new_df = new_df.rename(columns=header_map_911)
                else:
                    new_df.columns = [
                        str(c).strip().lower()
                        for c in new_df.columns
                    ]

                st.subheader("Vista previa")

                preview = new_df.rename(
                    columns=directorio_911_labels
                )

                st.dataframe(
                    preview,
                    use_container_width=True,
                    hide_index=True,
                    height=350,
                )

                if st.button(
                    "🔄 Reemplazar Tabla Completa",
                    type="primary",
                    use_container_width=True,
                    key="replace_directorio_911",
                ):

                    required = {
                        c for c in directorio_911_columns
                        if c != "id"
                    }

                    if not required.issubset(set(new_df.columns)):

                        missing = sorted(
                            required - set(new_df.columns)
                        )

                        st.error(
                            "El archivo no contiene todas las columnas requeridas.\n\n"
                            f"Faltantes: {', '.join(missing)}"
                        )
                        st.stop()

                    records_df = new_df[
                        list(required)
                    ].copy()

                    for column in required:
                        records_df[column] = (
                            records_df[column]
                            .where(records_df[column].notna(), "")
                            .astype(str)
                            .str.strip()
                        )

                    records = records_df.to_dict("records")

                    try:

                        supabase.table(
                            "directorio_auxilio_carretero_911"
                        ).delete().neq(
                            "id", 0
                        ).execute()

                        if records:
                            supabase.table(
                                "directorio_auxilio_carretero_911"
                            ).insert(records).execute()

                    except Exception as e:

                        st.exception(e)
                        st.stop()

                    log_action(
                        "REPLACE",
                        "directorio_auxilio_carretero_911",
                        f"{len(records)} registros",
                        "Reemplazó completamente la tabla "
                        "directorio_auxilio_carretero_911",
                    )

                    st.cache_data.clear()

                    st.success(
                        f"Se cargaron correctamente "
                        f"{len(records)} entradas 911."
                    )

                    st.rerun()

# ADMINISTRACIÓN DE USUARIOS
# ==========================================

if is_admin:

    with tab_admin:
    
        USER_ROLES = [
            "admin",
            "manager",
            "field_user",
            "regular_user",
        ]

        BRANCHES = [
            "beta",
            "release",
        ]

        ENTERPRISES = [
            "picus",
            "igloo",
            "lincoln",
            "setlogis",
            "setfreight",
        ]

        PAGE_PERMITS = [
            "consulta_reportes",
            "consultar_reparacion",
            "lector_pdf",
            "pase_taller",
            "autorizacion",
            "ifuel",
            "prepara_reportes",
            "gestion_unidades",
            "solicitud_viaticos",
            "gestion_viaticos",
            "gps_tracking",
            "ai_testing",
            "bonos_operador",
            "consulta_bonos_operador",
            "directorio_auxilio",
        ]

        st.subheader("Administración de Usuarios")

        st.dataframe(
            df_profiles,
            use_container_width=True,
            hide_index=True,
            height=350,
        )

        st.divider()

        st.subheader("Modificar Usuario")

        if df_profiles.empty:

            st.info("No existen usuarios.")

        else:

            selected_email = st.selectbox(
                "Usuario",
                sorted(df_profiles["email"].tolist())
            )

            row = df_profiles[
                df_profiles["email"] == selected_email
            ].iloc[0]

            access = row["access"] or []

            selected_branch = next(
                (x for x in BRANCHES if x in access),
                "release"
            )

            selected_enterprises = [
                x for x in ENTERPRISES
                if x in access
            ]

            selected_pages = [
                x for x in PAGE_PERMITS
                if x in access
            ]

            with st.form("edit_profile"):

                st.text_input(
                    "Email",
                    value=row["email"],
                    disabled=True,
                )

                full_name = st.text_input(
                    "Nombre",
                    value=row["full_name"] or ""
                )

                role = st.selectbox(
                    "Rol",
                    USER_ROLES,
                    index=USER_ROLES.index(row["role"])
                    if row["role"] in USER_ROLES
                    else 0
                )

                branch = st.radio(
                    "Branch",
                    BRANCHES,
                    index=BRANCHES.index(selected_branch),
                    horizontal=True,
                )

                enterprises = st.multiselect(
                    "Empresas",
                    ENTERPRISES,
                    default=selected_enterprises,
                )

                permissions = st.multiselect(
                    "Permisos",
                    PAGE_PERMITS,
                    default=selected_pages,
                )

                save = st.form_submit_button(
                    "Guardar Cambios",
                    use_container_width=True
                )

                if save:

                    access = (
                        [branch]
                        + enterprises
                        + permissions
                    )

                    supabase.table("profiles") \
                        .update({

                            "full_name": full_name.strip(),
                            "role": role,
                            "access": access

                        }) \
                        .eq("id", row["id"]) \
                        .execute()

                    log_action(
                        "UPDATE",
                        "profiles",
                        row["email"],
                        f"Actualizó usuario {row['email']}"
                    )

                    st.cache_data.clear()

                    st.success("Usuario actualizado correctamente.")

                    st.rerun()

# ==========================================
# AUDIT
# ==========================================

if is_admin:

    with tab_audit:

        st.subheader("Actividad por Usuario")

        users = sorted(
            set(df_activity["user_name"].dropna().astype(str))
            | set(df_audit_log["user_name"].dropna().astype(str))
            | set(df_audit["usuario"].dropna().astype(str))
        )

        selected_user = st.selectbox(
            "Usuario",
            ["Todos"] + users,
            index=0,
            key="audit_selected_user"
        )

        # ==========================================
        # FILTER DATA
        # ==========================================

        if selected_user == "Todos":

            # TODOS = ALL RECORDS FROM ALL THREE TABLES
            activity_filtered = df_activity.copy()
            auditlog_filtered = df_audit_log.copy()
            audit_filtered = df_audit.copy()

        else:

            # SPECIFIC USER = ONLY THAT USER'S RECORDS
            activity_filtered = df_activity[
                df_activity["user_name"].astype(str) == selected_user
            ].copy()

            auditlog_filtered = df_audit_log[
                df_audit_log["user_name"].astype(str) == selected_user
            ].copy()

            audit_filtered = df_audit[
                df_audit["usuario"].astype(str) == selected_user
            ].copy()

        (
            tab_navigation,
            tab_database,
            tab_authorization,
        ) = st.tabs([
            "🧭 Actividad de Navegación",
            "🛠️ Auditoría Base de Datos",
            "✅ Auditoría Autorizaciones",
        ])

        # ==========================================
        # USER NAVIGATION
        # ==========================================

        with tab_navigation:

            st.caption(
                "Registra la navegación de los usuarios dentro de la aplicación, incluyendo inicios de sesión, acceso a módulos y visitas a las diferentes páginas."
            )

            # ==========================================
            # KPIs
            # ==========================================

            if activity_filtered.empty:

                st.info("No existen registros para el usuario seleccionado.")

            else:

                latest_login = (
                    activity_filtered
                    .sort_values("action_date", ascending=False)
                    .iloc[0]
                )

                latest_actions = (
                    activity_filtered
                    .sort_values("action_date", ascending=False)
                    .head(5)
                )

                col1, col2 = st.columns([1, 2])

                with col1:

                    st.metric(
                        "Último Login",
                        int(latest_login["login_counter"])
                    )

                with col2:

                    st.markdown("##### Últimas 5 acciones")

                    latest_actions_display = latest_actions[
                        ["action", "page"]
                    ].rename(columns={
                        "action": "Acción",
                        "page": "Página"
                    })

                    st.dataframe(
                        latest_actions_display,
                        use_container_width=True,
                        hide_index=True,
                        height=215,
                    )

            st.divider()

            col1, col2 = st.columns([4, 1])

            with col1:
                st.subheader("Historial de Actividad de Navegación")

            with col2:

                excel_buffer = BytesIO()

                activity_filtered.to_excel(
                    excel_buffer,
                    index=False,
                    engine="openpyxl"
                )

                excel_buffer.seek(0)

                st.download_button(
                    "📥 Descargar",
                    data=excel_buffer,
                    file_name="Actividad_Navegacion.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )

            st.dataframe(
                activity_filtered,
                use_container_width=True,
                hide_index=True,
                height=650,
            )

        # ==========================================
        # DATABASE AUDIT
        # ==========================================

        with tab_database:

            st.caption(
                "Registra todas las modificaciones realizadas por Administradores y Gerentes sobre las bases de datos de la aplicación, incluyendo inserciones, actualizaciones, eliminaciones y reemplazos completos de tablas."
            )

            # ==========================================
            # KPIs
            # ==========================================

            if auditlog_filtered.empty:

                st.info("No existen registros para el usuario seleccionado.")

            else:

                latest_change = (
                    auditlog_filtered
                    .sort_values("created_at", ascending=False)
                    .iloc[0]
                )

                latest_changes = (
                    auditlog_filtered
                    .sort_values("created_at", ascending=False)
                    .head(5)
                )

                col1, col2 = st.columns([1, 2])

                with col1:

                    st.metric(
                        "Última Tabla Modificada",
                        latest_change["table_name"]
                    )

                with col2:

                    st.markdown("##### Últimos 5 cambios")

                    latest_changes_display = latest_changes[
                        ["table_name", "details"]
                    ].rename(columns={
                        "table_name": "Tabla",
                        "details": "Detalle"
                    })

                    st.dataframe(
                        latest_changes_display,
                        use_container_width=True,
                        hide_index=True,
                        height=215,
                    )

            st.divider()

            col1, col2 = st.columns([4, 1])

            with col1:

                st.subheader("Historial de Cambios en Base de Datos")

            with col2:

                excel_buffer = BytesIO()

                auditlog_filtered.to_excel(
                    excel_buffer,
                    index=False,
                    engine="openpyxl"
                )

                excel_buffer.seek(0)

                st.download_button(
                    "📥 Descargar",
                    data=excel_buffer,
                    file_name="Auditoria_Base_Datos.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )

            st.dataframe(
                auditlog_filtered,
                use_container_width=True,
                hide_index=True,
                height=650,
            )

        # ==========================================
        # AUTHORIZATION AUDIT
        # ==========================================

        with tab_authorization:

            st.caption(
                "Registra todas las acciones realizadas por los usuarios dentro del módulo de Autorización, incluyendo aprobaciones, rechazos y cambios de estatus durante el flujo de autorización."
            )

            # ==========================================
            # KPIs
            # ==========================================

            if audit_filtered.empty:

                st.info("No existen registros para el usuario seleccionado.")

            else:

                latest_entries = (
                    audit_filtered
                    .sort_values("timestamp", ascending=False)
                    .head(5)
                )

                st.markdown("##### Últimas 5 acciones")

                latest_entries_display = latest_entries[
                    ["empresa", "no. de folio", "tipo cambio"]
                ].rename(columns={
                    "empresa": "Empresa",
                    "no. de folio": "No. de Folio",
                    "tipo cambio": "Tipo de Cambio"
                })

                st.dataframe(
                    latest_entries_display,
                    use_container_width=True,
                    hide_index=True,
                    height=215,
                )

            st.divider()

            col1, col2 = st.columns([4, 1])

            with col1:

                st.subheader("Historial del Módulo de Autorización")

            with col2:

                excel_buffer = BytesIO()

                audit_filtered.to_excel(
                    excel_buffer,
                    index=False,
                    engine="openpyxl"
                )

                excel_buffer.seek(0)

                st.download_button(
                    "📥 Descargar",
                    data=excel_buffer,
                    file_name="Auditoria_Autorizacion.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )

            st.dataframe(
                audit_filtered,
                use_container_width=True,
                hide_index=True,
                height=650,
            )