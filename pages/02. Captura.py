import streamlit as st
import pandas as pd
from datetime import date

# =================================
# Page configuration
# =================================
st.set_page_config(
    page_title="Captura Pase de Taller",
    layout="wide"
)

# =================================
# Google Sheets configuration
# =================================
CATALOGOS_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1qlIcKouGS2cxsCsCdNh5pMgLfWXj41dXfaeq5cyktZ8"
    "/export?format=csv&gid=0"
)

TRACTORES_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1qlIcKouGS2cxsCsCdNh5pMgLfWXj41dXfaeq5cyktZ8"
    "/export?format=csv&gid=1152583226"
)

IGLOO_ARTICULOS_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "18tFOA4prD-PWhtbc35cqKXxYcyuqGOC7"
    "/export?format=csv&gid=410297659"
)

# =================================
# Load catalogs
# =================================
@st.cache_data(ttl=3600)
def cargar_catalogos():
    df = pd.read_csv(CATALOGOS_URL)
    df.columns = df.columns.str.strip()

    empresas = (
        df["EMPRESA"]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )

    return df, sorted(empresas)

@st.cache_data(ttl=3600)
def cargar_tractores():
    df = pd.read_csv(TRACTORES_URL)
    df.columns = df.columns.str.strip()
    return df

@st.cache_data(ttl=3600)
def cargar_articulos_igloo():
    df = pd.read_csv(IGLOO_ARTICULOS_URL)
    df.columns = df.columns.str.strip()

    def limpiar_numero(valor):
        return (
            str(valor)
            .replace("$", "")
            .replace(",", "")
            .strip()
        )

    precio = df["PU"].apply(limpiar_numero).astype(float)
    iva_raw = df["Tasaiva"].apply(limpiar_numero).astype(float)
    iva = iva_raw.apply(lambda x: x / 100 if x >= 1 else x)

    df_final = pd.DataFrame({
        "Seleccionar": False,
        "Artículo": df["TipoCompra"],
        "Descripción": df["Parte"],
        "Tipo": df["TipoCompra"],
        "Precio MXP": precio,
        "Iva": iva,
        "Cantidad": 1,
        "Total MXN": 0.0,
        "Tipo Mtto": df["Tipo de reparacion"]
    })

    df_final["Total MXN"] = (
        df_final["Precio MXP"] * (1 + df_final["Iva"]) * df_final["Cantidad"]
    )

    return df_final

catalogos_df, empresas = cargar_catalogos()
tractores_df = cargar_tractores()

# =================================
# Title
# =================================
st.title("🛠️ Captura Pase de Taller")

# =================================
# SECCIÓN 1 — DATOS DEL REPORTE
# =================================
st.divider()
st.subheader("Datos del Reporte")

fecha_reporte = st.date_input("Fecha de reporte", value=date.today())

numero_reporte = st.text_input(
    "No. de reporte",
    placeholder="Folio generado al guardar",
    disabled=True
)

capturo = st.text_input("Capturó", placeholder="Nombre del responsable")

estado = st.selectbox(
    "Estado",
    ["----", "Edicion", "Proceso", "Terminado"]
)

# =================================
# SECCIÓN 2 — INFORMACIÓN DEL OPERADOR
# =================================
st.divider()
st.subheader("Información del Operador")

# ---------------- Empresa ----------------
empresa = st.selectbox(
    "Empresa",
    ["Selecciona Empresa"] + empresas,
    index=0
)

# ---------------- Tipo de Reporte ----------------
tipo_reporte = st.selectbox(
    "Tipo de Reporte",
    ["Selecciona tipo de reporte",
     "Orden de Reparacion",
     "Orden de entrega de Material",
     "Orden Correctivo",
     "Orden Preventivo",
     "Orden Alineacion"],
    index=0
)

# ---------------- Tipo de Unidad ----------------
tipo_unidad_operador = st.selectbox(
    "Tipo de Unidad",
    ["Seleccionar tipo de unidad", "Tractores", "Remolques"],
    index=0
)

# -------- UNIDADES FILTRADAS POR EMPRESA --------
if empresa and empresa != "Selecciona Empresa":
    catalogos_filtrados = catalogos_df[
        catalogos_df["EMPRESA"].astype(str).str.strip() == empresa
    ]
    tractores_filtrados_df = tractores_df[
        tractores_df["EMPRESA"].astype(str).str.strip() == empresa
    ]
else:
    catalogos_filtrados = pd.DataFrame()
    tractores_filtrados_df = pd.DataFrame()

# ---------------- Operador ----------------
operador_disabled = tipo_unidad_operador != "Tractores"
operador = st.text_input(
    "Operador",
    placeholder="Nombre del operador",
    disabled=operador_disabled
)

# ---------------- No. de Unidad | Marca | Modelo | No. de Unidad Externo ----------------
c1, c2, c3, c4 = st.columns([2,2,2,3])

# Determine options and disabled state
if tipo_unidad_operador == "Tractores":
    unidad_options = ["Selecciona Unidad"] + sorted(
        tractores_filtrados_df["TRACTOR"].dropna().astype(str).str.strip().unique().tolist()
    )
    no_unidad_disabled = False
elif tipo_unidad_operador == "Remolques":
    unidad_options = ["Selecciona Unidad", "REMOLQUE EXTERNO"] + sorted(
        catalogos_filtrados["CAJA"].dropna().astype(str).str.strip().unique().tolist()
    )
    no_unidad_disabled = False
else:
    unidad_options = ["Selecciona Unidad"]
    no_unidad_disabled = True

with c1:
    no_unidad = st.selectbox(
        "No. de Unidad",
        unidad_options,
        index=0,
        disabled=no_unidad_disabled
    )

# Auto-fill Marca / Modelo
if tipo_unidad_operador == "Tractores" and no_unidad != "Selecciona Unidad":
    fila = tractores_filtrados_df[
        tractores_filtrados_df["TRACTOR"].astype(str).str.strip() == no_unidad
    ].iloc[0]
    marca_valor = str(fila["MARCA"]).strip()
    modelo_valor = str(fila["MODELO"]).strip()
elif tipo_unidad_operador == "Remolques":
    if no_unidad == "REMOLQUE EXTERNO":
        marca_valor = "EXTERNO"
        modelo_valor = "0000"
    elif no_unidad != "Selecciona Unidad":
        fila = catalogos_filtrados[
            catalogos_filtrados["CAJA"].astype(str).str.strip() == no_unidad
        ].iloc[0]
        marca_valor = str(fila.get("MARCA", "")).strip()
        modelo_valor = str(fila.get("MODELO", "")).strip()
    else:
        marca_valor = ""
        modelo_valor = ""
else:
    marca_valor = ""
    modelo_valor = ""

with c2:
    marca = st.text_input("Marca", value=marca_valor, disabled=True)
with c3:
    modelo = st.text_input("Modelo", value=modelo_valor, disabled=True)
with c4:
    no_unidad_externo = st.text_input(
        "No. de Unidad Externo",
        disabled=no_unidad != "REMOLQUE EXTERNO",
        placeholder="Escribe información del remolque externo"
    )

# ---------------- Tipo de Caja ----------------
if tipo_unidad_operador == "Remolques":
    tipo_caja_options = ["Selecciona Caja", "Caja seca", "Caja fria"]
    tipo_caja_disabled = False
else:
    tipo_caja_options = ["Caja no aplicable"]
    tipo_caja_disabled = True

tipo_caja = st.selectbox(
    "Tipo de Caja",
    tipo_caja_options,
    index=0,
    disabled=tipo_caja_disabled
)

# ---------------- Descripción ----------------
descripcion_problema = st.text_area("Descripción del problema", height=120)

# ---------------- Generó Multa ----------------
genero_multa = st.checkbox("¿Generó multa?")

# ---------------- No. de Inspección & Reparación que generó multa ----------------
numero_inspeccion = st.text_input(
    "No. de Inspección",
    disabled=not genero_multa
)
reparacion_multa = st.text_area(
    "Reparación que generó multa",
    height=100,
    disabled=not genero_multa
)

# =================================
# SECCIÓN 3 — ARTÍCULOS / ACTIVIDADES
# =================================
st.divider()
st.subheader("Artículos / Actividades")

if "empresa_prev" not in st.session_state:
    st.session_state.empresa_prev = empresa

if empresa != st.session_state.empresa_prev:
    if empresa == "IGLOO TRANSPORT":
        st.session_state.articulos_df = cargar_articulos_igloo()
    else:
        st.session_state.articulos_df = pd.DataFrame(columns=[
            "Seleccionar",
            "Artículo",
            "Descripción",
            "Tipo quitar--",
            "Precio MXP",
            "Iva",
            "Cantidad",
            "Total MXN",
            "Tipo Mtto"
        ])
    st.session_state.empresa_prev = empresa

df_base = st.session_state.get("articulos_df", pd.DataFrame())

edited_df = st.data_editor(
    df_base,
    key="editor_articulos",
    hide_index=True
)

# =================================
# TOTAL SELECCIONADO
# =================================

total_seleccionado = (
    edited_df.loc[edited_df["Seleccionar"] == True, "Total MXN"].sum()
    if not edited_df.empty else 0.0
)

st.metric("Total Seleccionado MXN", f"$ {total_seleccionado:,.2f}")