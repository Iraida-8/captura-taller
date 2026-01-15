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

    def limpiar(valor):
        return str(valor).replace("$", "").replace(",", "").strip()

    precio = df["PrecioParte"].apply(limpiar).astype(float)
    iva_raw = df["Tasaiva"].apply(limpiar).astype(float)
    iva = iva_raw.apply(lambda x: x / 100 if x >= 1 else x)

    base = pd.DataFrame({
        "Seleccionar": False,
        "Artículo": df["Parte"],
        "Descripción": df["Parte"],
        "Precio MXP": precio,
        "Iva": iva,
        "Cantidad": 1,
        "Total MXN": precio * (1 + iva),
        "Tipo Mtto": df["Tipo de reparacion"]
    })

    return base

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

st.text_input("No. de Folio", disabled=True)
st.text_input("No. de Reporte", disabled=True)

capturo = st.text_input("Capturó")

estado = st.selectbox("Estado", ["----", "Edicion", "Proceso", "Terminado"])

# =================================
# SECCIÓN 2 — INFORMACIÓN DEL OPERADOR
# =================================
st.divider()
st.subheader("Información del Operador")

empresa = st.selectbox("Empresa", ["Selecciona Empresa"] + empresas)

tipo_reporte = st.selectbox(
    "Tipo de Reporte",
    [
        "Selecciona tipo de reporte",
        "Orden de Reparacion",
        "Orden de entrega de Material",
        "Orden Correctivo",
        "Orden Preventivo",
        "Orden Alineacion"
    ]
)

tipo_unidad_operador = st.selectbox(
    "Tipo de Unidad",
    ["Seleccionar tipo de unidad", "Tractores", "Remolques"]
)

if empresa != "Selecciona Empresa":
    catalogos_filtrados = catalogos_df[catalogos_df["EMPRESA"].astype(str).str.strip() == empresa]
    tractores_filtrados = tractores_df[tractores_df["EMPRESA"].astype(str).str.strip() == empresa]
else:
    catalogos_filtrados = pd.DataFrame()
    tractores_filtrados = pd.DataFrame()

operador = st.text_input(
    "Operador",
    disabled=tipo_unidad_operador != "Tractores"
)

c1, c2, c3, c4 = st.columns([2, 2, 2, 3])

if tipo_unidad_operador == "Tractores":
    unidades = ["Selecciona Unidad"] + sorted(tractores_filtrados["TRACTOR"].dropna().astype(str))
elif tipo_unidad_operador == "Remolques":
    unidades = ["Selecciona Unidad", "REMOLQUE EXTERNO"] + sorted(catalogos_filtrados["CAJA"].dropna().astype(str))
else:
    unidades = ["Selecciona Unidad"]

with c1:
    no_unidad = st.selectbox("No. de Unidad", unidades, disabled=tipo_unidad_operador == "Seleccionar tipo de unidad")

marca_valor = ""
modelo_valor = ""

if tipo_unidad_operador == "Tractores" and no_unidad != "Selecciona Unidad":
    fila = tractores_filtrados[tractores_filtrados["TRACTOR"].astype(str) == no_unidad].iloc[0]
    marca_valor = fila["MARCA"]
    modelo_valor = fila["MODELO"]

elif tipo_unidad_operador == "Remolques":
    if no_unidad == "REMOLQUE EXTERNO":
        marca_valor = "EXTERNO"
        modelo_valor = "0000"
    elif no_unidad != "Selecciona Unidad":
        fila = catalogos_filtrados[catalogos_filtrados["CAJA"].astype(str) == no_unidad].iloc[0]
        marca_valor = fila.get("MARCA", "")
        modelo_valor = fila.get("MODELO", "")

with c2:
    st.text_input("Marca", value=marca_valor, disabled=True)
with c3:
    st.text_input("Modelo", value=modelo_valor, disabled=True)
with c4:
    st.text_input(
        "No. de Unidad Externo",
        disabled=no_unidad != "REMOLQUE EXTERNO"
    )

tipo_caja = st.selectbox(
    "Tipo de Caja",
    ["Selecciona Caja", "Caja seca", "Caja fria"] if tipo_unidad_operador == "Remolques" else ["Caja no aplicable"],
    disabled=tipo_unidad_operador != "Remolques"
)

descripcion_problema = st.text_area("Descripción del problema")

genero_multa = st.checkbox("¿Generó multa?")

numero_inspeccion = st.text_input("No. de Inspección", disabled=not genero_multa)
reparacion_multa = st.text_area("Reparación que generó multa", disabled=not genero_multa)

# =================================
# BOTÓN + MODAL (SOLO AÑADIDO)
# =================================
st.divider()

if "mostrar_modal" not in st.session_state:
    st.session_state.mostrar_modal = False

if st.button("Añadir Servicios o Refacciones"):
    st.session_state.mostrar_modal = True

if st.session_state.mostrar_modal:

    @st.dialog("Añadir Servicios o Refacciones")
    def modal():
        igloo_df = cargar_articulos_igloo()

        tipo_mtto = st.selectbox(
            "Tipo de Mantenimiento",
            sorted(igloo_df["Tipo Mtto"].dropna().unique())
        )

        refaccion = st.selectbox(
            "Refacción",
            igloo_df["Artículo"].tolist()
        )

        fila = igloo_df[igloo_df["Artículo"] == refaccion].iloc[0]

        st.number_input("Precio de Parte MXN", value=float(fila["Precio MXP"]), disabled=True)

        cantidad = st.number_input("Cantidad", min_value=1, value=1)

        if st.button("Agregar"):
            nueva = fila.copy()
            nueva["Cantidad"] = cantidad
            nueva["Total MXN"] = cantidad * fila["Precio MXP"] * (1 + fila["Iva"])

            st.session_state.articulos_df = pd.concat(
                [st.session_state.get("articulos_df", pd.DataFrame()), nueva.to_frame().T],
                ignore_index=True
            )
            st.session_state.mostrar_modal = False

        if st.button("Cancelar"):
            st.session_state.mostrar_modal = False

    modal()

# =================================
# SECCIÓN 3 — ARTÍCULOS / ACTIVIDADES
# =================================
st.divider()
st.subheader("Artículos / Actividades")

if "articulos_df" not in st.session_state:
    st.session_state.articulos_df = pd.DataFrame(columns=[
        "Seleccionar",
        "Artículo",
        "Descripción",
        "Precio MXP",
        "Iva",
        "Cantidad",
        "Total MXN",
        "Tipo Mtto"
    ])

edited_df = st.data_editor(
    st.session_state.articulos_df,
    hide_index=True,
    key="editor"
)

total = edited_df.loc[edited_df["Seleccionar"] == True, "Total MXN"].sum() if not edited_df.empty else 0
st.metric("Total Seleccionado MXN", f"$ {total:,.2f}")