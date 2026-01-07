import streamlit as st
from datetime import date

# =================================
# Page configuration
# =================================
st.set_page_config(
    page_title="Captura Pase de Taller",
    layout="centered"
)

# =================================
# Title
# =================================
st.title("🛠️ Captura Pase de Taller")

# =================================
# SECCIÓN 1 — DATOS DEL REPORTE
# =================================
st.subheader("Datos del Reporte")
st.divider()

fecha_reporte = st.date_input(
    "Fecha de reporte",
    value=date.today()
)

numero_reporte = st.text_input(
    "No. de reporte",
    placeholder="Ej. REP-2026-001"
)

capturo = st.text_input(
    "Capturó",
    placeholder="Nombre del responsable"
)

estado = st.selectbox(
    "Estado",
    options=[
        "EDICION",
        "PLACEHOLDER",
        "PLACEHOLDER",
        "PLACEHOLDER"
    ]
)

# =================================
# SECCIÓN 2 — INFORMACIÓN DEL OPERADOR
# =================================
st.subheader("Información del Operador")
st.divider()

empresa = st.selectbox(
    "Empresa",
    [
     "LINCOLN FREIGHT COMPANY, LLC",
     "PICUS",
     "SET LOGIS PLUS"
     ]
)

tipo_unidad = st.selectbox(
    "Tipo de Unidad",
    ["Caja seca", "Termo seco"]
)

unidad = st.text_input(
    "Unidad",
    placeholder="Número o identificador de la unidad"
)

operador = st.text_input(
    "Operador",
    placeholder="Nombre del operador"
)

tipo_reporte = st.selectbox(
    "Tipo de Reporte",
    ["Reporte de reparación"]
)

descripcion_problema = st.text_area(
    "Descripción del problema",
    height=120
)

col1, col2 = st.columns([2, 1])

with col1:
    numero_inspeccion = st.text_input(
        "No. de Inspección"
    )

with col2:
    genero_multa = st.checkbox("¿Generó multa?")

reparacion_multa = st.text_area(
    "Reparación que generó multa",
    height=100,
    disabled=not genero_multa
)

# =================================
# SECCIÓN 3 — ARTÍCULOS / ACTIVIDADES
# =================================
st.subheader("Artículos / Actividades")
st.divider()

# ---------------------------------
# Column filters
# ---------------------------------
f1, f2, f3, f4, f5, f6, f7 = st.columns([1, 2, 3, 2, 2, 2, 2])

with f1:
    filtro_sel = st.text_input(" ", placeholder="✔")

with f2:
    filtro_articulo = st.text_input(" ", placeholder="Artículo")

with f3:
    filtro_desc = st.text_input(" ", placeholder="Descripción")

with f4:
    filtro_tiempo = st.text_input(" ", placeholder="Tiempo")

with f5:
    filtro_precio = st.text_input(" ", placeholder="Precio")

with f6:
    filtro_tipo_act = st.text_input(" ", placeholder="Actividad")

with f7:
    filtro_tipo_mtto = st.text_input(" ", placeholder="Mtto")

# ---------------------------------
# Sample data (placeholder)
# ---------------------------------
rows = [
    {
        "Seleccionar": False,
        "Artículo": "Balata de freno",
        "Descripción": "Cambio de balatas eje delantero",
        "Tiempo Est.": "2 hrs",
        "Precio MXP": 3500,
        "Tipo Actividad": "Reparación",
        "Tipo Mtto": "Correctivo"
    },
    {
        "Seleccionar": False,
        "Artículo": "Filtro de aceite",
        "Descripción": "Reemplazo de filtro y aceite",
        "Tiempo Est.": "1 hr",
        "Precio MXP": 1200,
        "Tipo Actividad": "Servicio",
        "Tipo Mtto": "Preventivo"
    }
]

# ---------------------------------
# Filtering logic
# ---------------------------------
def match(value, filtro):
    return filtro.lower() in str(value).lower()

filtered_rows = [
    r for r in rows
    if match(r["Artículo"], filtro_articulo)
    and match(r["Descripción"], filtro_desc)
    and match(r["Tiempo Est."], filtro_tiempo)
    and match(r["Precio MXP"], filtro_precio)
    and match(r["Tipo Actividad"], filtro_tipo_act)
    and match(r["Tipo Mtto"], filtro_tipo_mtto)
]

# ---------------------------------
# Table editor
# ---------------------------------
st.data_editor(
    filtered_rows,
    hide_index=True,
    column_config={
        "Seleccionar": st.column_config.CheckboxColumn(
            label="✔",
            width="small"
        ),
        "Artículo": st.column_config.TextColumn("Artículo"),
        "Descripción": st.column_config.TextColumn("Descripción"),
        "Tiempo Est.": st.column_config.TextColumn("Tiempo Est."),
        "Precio MXP": st.column_config.NumberColumn(
            "Precio MXP",
            format="$ %d",
            min_value=0
        ),
        "Tipo Actividad": st.column_config.TextColumn("Tipo Actividad"),
        "Tipo Mtto": st.column_config.TextColumn("Tipo Mtto")
    },
    disabled=[
        "Artículo",
        "Descripción",
        "Tiempo Est.",
        "Precio MXP",
        "Tipo Actividad",
        "Tipo Mtto"
    ]
)