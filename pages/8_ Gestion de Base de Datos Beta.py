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

st.title("📚 Administración de Catálogos")

# =================================
# TABS
# =================================

tab_unidades, tab_refacciones, tab_proveedores, tab_tc = st.tabs([
    "Gestión, Creación y Carga de Unidades",
    "Refacciones",
    "Proveedores IVA",
    "TC Mensual",
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
                    .neq("id", 0) \
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

                records = (
                    new_df[
                        [
                            "proveedor",
                            "iva_pct",
                            "isr_pct",
                            "formula",
                            "clave"
                        ]
                    ]
                    .fillna("")
                    .to_dict("records")
                )

                supabase.table("proveedores_iva") \
                    .delete() \
                    .neq("id", 0) \
                    .execute()

                if records:

                    supabase.table("proveedores_iva") \
                        .insert(records) \
                        .execute()

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

    # =====================================================
    # ADD
    # =====================================================
    with tab_add:

        with st.form("add_tc"):

            current_year = datetime.now().year

            year = st.number_input(
                "Año",
                min_value=2020,
                max_value=2100,
                value=current_year,
                step=1
            )

            month = st.selectbox(
                "Mes",
                [
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

                today = datetime.now()

                supabase.table("tc_mensual").insert({

                    "YEAR": int(year),
                    "MONTH": month,
                    "DATE": today.strftime("%Y-%m-%d"),
                    "TC": tc

                }).execute()

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

            selected = st.selectbox(
                "Selecciona la fecha",
                df_tc["DATE"].astype(str).tolist(),
                key="edit_tc"
            )

            row = df_tc[
                df_tc["DATE"].astype(str) == selected
            ].iloc[0]

            with st.form("edit_tc_form"):

                st.text_input(
                    "Fecha",
                    value=str(row["DATE"]),
                    disabled=True
                )

                tc = st.number_input(
                    "Tipo de Cambio",
                    value=float(row["TC"]),
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

                            "TC": tc

                        }) \
                        .eq("id", row["id"]) \
                        .execute()

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

            selected = st.selectbox(
                "Selecciona la fecha",
                df_tc["DATE"].astype(str).tolist(),
                key="delete_tc"
            )

            row = df_tc[
                df_tc["DATE"].astype(str) == selected
            ].iloc[0]

            if st.button(
                "🗑 Eliminar Registro",
                type="primary",
                use_container_width=True
            ):

                supabase.table("tc_mensual") \
                    .delete() \
                    .eq("id", row["id"]) \
                    .execute()

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

                st.cache_data.clear()

                st.success(
                    f"Se cargaron {len(records)} registros."
                )

                st.rerun()