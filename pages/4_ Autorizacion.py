import streamlit as st
import pandas as pd
from datetime import date

# =================================
# Page configuration
# =================================
st.set_page_config(
    page_title="Autorización y Actualización de Reporte",
    layout="wide"
)

st.title("📋 Autorización y Actualización de Reporte")

# =================================
# Session State
# =================================
if "buscar_trigger" not in st.session_state:
    st.session_state.buscar_trigger = False

if "modal_reporte" not in st.session_state:
    st.session_state.modal_reporte = None

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

# =================================
# MOCK DATA (TEMPORARY – DO NOT REMOVE)
# =================================
mock_reportes = pd.DataFrame([
    {
        "NoFolio": "IG00001",
        "Empresa": "IGLOO TRANSPORT",
        "Fecha": date.today(),
        "Proveedor": "Interno",
        "Estado": "En Curso / Nuevo"
    },
    {
        "NoFolio": "IG00002",
        "Empresa": "LINCOLN FREIGHT",
        "Fecha": date.today(),
        "Proveedor": "Externo",
        "Estado": "Cerrado"
    }
])

# =================================
# SECCIÓN — TOP 10 EN CURSO
# =================================
st.divider()
st.subheader("Últimos 10 Pases de Taller (En Curso / Nuevo)")

top10 = mock_reportes[
    mock_reportes["Estado"] == "En Curso / Nuevo"
].sort_values("Fecha", ascending=False).head(10)

st.dataframe(top10, hide_index=True)

# =================================
# SECCIÓN — BUSCAR PASE DE TALLER
# =================================
st.divider()
st.subheader("Buscar Pase de Taller")

f1, f2, f3, f4 = st.columns(4)

with f1:
    f_folio = st.text_input("No. de Folio")

with f2:
    f_empresa = st.text_input("Empresa")

with f3:
    f_estado = st.selectbox(
        "Estado",
        ["", "En Curso / Nuevo", "Cerrado", "Cancelado"]
    )

with f4:
    f_fecha = st.date_input("Fecha", value=None)

if st.button("Buscar"):
    st.session_state.buscar_trigger = True

# =================================
# RESULTADOS (SOLO DESPUÉS DE BUSCAR)
# =================================
if st.session_state.buscar_trigger:

    if not any([f_folio, f_empresa, f_estado, f_fecha]):
        st.warning("Ingresa al menos un filtro para buscar.")
        st.stop()

    st.divider()
    st.subheader("Resultados de Búsqueda")

    for _, row in mock_reportes.iterrows():
        c1, c2, c3, c4, c5, c6 = st.columns([1, 2, 2, 2, 2, 1])

        with c1:
            if row["Estado"] == "En Curso / Nuevo":
                if st.button("Editar", key=f"edit_{row['NoFolio']}"):
                    st.session_state.modal_reporte = row.to_dict()
            else:
                if st.button("Ver", key=f"ver_{row['NoFolio']}"):
                    st.session_state.modal_reporte = row.to_dict()

        c2.write(row["NoFolio"])
        c3.write(row["Empresa"])
        c4.write(row["Proveedor"])
        c5.write(row["Estado"])
        c6.write(row["Fecha"])

# =================================
# MODAL — EDITAR / VER REPORTE
# =================================
if st.session_state.modal_reporte:

    reporte = st.session_state.modal_reporte
    editable = reporte["Estado"] == "En Curso / Nuevo"

    @st.dialog("Detalle del Pase de Taller")
    def modal():

        st.markdown(f"**No. de Folio:** {reporte['NoFolio']}")
        st.markdown(f"**Empresa:** {reporte['Empresa']}")
        st.markdown(f"**Fecha:** {reporte['Fecha']}")
        st.markdown(f"**Proveedor:** {reporte['Proveedor']}")

        nuevo_estado = st.selectbox(
            "Estado",
            ["En Curso / Nuevo", "Cerrado", "Cancelado"],
            index=["En Curso / Nuevo", "Cerrado", "Cancelado"].index(reporte["Estado"]),
            disabled=not editable
        )

        # Lock: cannot go back to En Curso / Nuevo
        if reporte["Estado"] != "En Curso / Nuevo" and nuevo_estado == "En Curso / Nuevo":
            st.error("No es posible regresar a En Curso / Nuevo.")
            st.stop()

        # =================================
        # SERVICIOS Y REFACCIONES (ORIGINAL LOGIC)
        # =================================
        st.divider()
        st.subheader("Servicios y Refacciones")

        IGLOO_ARTICULOS_URL = (
            "https://docs.google.com/spreadsheets/d/"
            "18tFOA4prD-PWhtbc35cqKXxYcyuqGOC7"
            "/export?format=csv&gid=410297659"
        )

        @st.cache_data(ttl=3600)
        def cargar_articulos_igloo():
            df = pd.read_csv(IGLOO_ARTICULOS_URL)
            df.columns = df.columns.str.strip()

            def limpiar(v):
                return str(v).replace("$", "").replace(",", "").strip()

            precio = df["PrecioParte"].apply(limpiar).astype(float)
            iva_raw = df["Tasaiva"].apply(limpiar).astype(float)
            iva = iva_raw.apply(lambda x: x / 100 if x >= 1 else x)

            return pd.DataFrame({
                "Seleccionar": False,
                "Artículo": df["Parte"],
                "Descripción": df["Parte"],
                "Precio MXP": precio,
                "Iva": iva,
                "Cantidad": 1,
                "Total MXN": precio * (1 + iva),
                "Tipo Mtto": df["Tipo de reparacion"]
            })

        if editable:
            if st.button("Añadir Servicios o Refacciones"):
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

                cantidad = st.number_input("Cantidad", min_value=1, value=1)

                if st.button("Agregar"):
                    nueva = fila.copy()
                    nueva["Cantidad"] = cantidad
                    nueva["Total MXN"] = cantidad * fila["Precio MXP"] * (1 + fila["Iva"])

                    st.session_state.articulos_df = pd.concat(
                        [st.session_state.articulos_df, nueva.to_frame().T],
                        ignore_index=True
                    )

        st.data_editor(
            st.session_state.articulos_df,
            hide_index=True,
            disabled=not editable
        )

        total = st.session_state.articulos_df["Total MXN"].sum() if not st.session_state.articulos_df.empty else 0
        st.metric("Total MXN", f"$ {total:,.2f}")

        if st.button("Cerrar"):
            st.session_state.modal_reporte = None

    modal()
