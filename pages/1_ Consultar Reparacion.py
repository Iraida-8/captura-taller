import streamlit as st
import pandas as pd
from datetime import date
from auth import require_login, require_access
import streamlit.components.v1 as components

st.cache_data.clear()

# =================================
# Page configuration
# =================================
st.set_page_config(
    page_title="Consulta de Reparación",
    layout="wide"
)

# =================================
# Hide sidebar
# =================================
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        display: none;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# =================================
# Security
# =================================
require_login()
require_access("consultar_reparacion")

st.session_state.setdefault("modal_orden", None)

# =================================
# Navigation
# =================================
if st.button("⬅ Volver al Dashboard"):
    st.switch_page("pages/dashboard.py")

st.divider()
st.title("📋 Consulta de Reparación")

# =================================
# EMPRESA DATA CONFIG
# =================================
EMPRESA_CONFIG = {
    "IGLOO TRANSPORT": {
        "ordenes": (
            "https://docs.google.com/spreadsheets/d/"
            "1OGYOp0ZqK7PQ93F4wdHJKEnB4oZbl5pU"
            "/export?format=csv&gid=770635060"
        ),
        "partes": (
            "https://docs.google.com/spreadsheets/d/"
            "18tFOA4prD-PWhtbc35cqKXxYcyuqGOC7"
            "/export?format=csv&gid=410297659"
        ),
        "ostes": (
            "https://docs.google.com/spreadsheets/d/"
            "1RZ1YcLQxXI0U81Vle6cXmRp0yMxuRVg4"
            "/export?format=csv&gid=1578839108"
        )
    },

    "LINCOLN FREIGHT": {
        "ordenes": (
            "https://docs.google.com/spreadsheets/d/"
            "1nqRT3LRixs45Wth5bXyrKSojv3uJfjbZ"
            "/export?format=csv&gid=332111886"
        ),
        "partes": (
            "https://docs.google.com/spreadsheets/d/"
            "1lcNr73nHrMpsqdYBNxtTQFqFmY1Ey9gp"
            "/export?format=csv&gid=41991257"
        ),
        "ostes": (
            "https://docs.google.com/spreadsheets/d/"
            "1lZO4SVKHXfW1-IzhYXvAmJ8WC7zgg8VD"
            "/export?format=csv&gid=1179811252"
        )
    },

    "PICUS": {
        "ordenes": (
            "https://docs.google.com/spreadsheets/d/"
            "1DSFFir8vQGzkIZdPGZKakMFygUUjA6vg"
            "/export?format=csv&gid=1157416037"
        ),
        "partes": (
            "https://docs.google.com/spreadsheets/d/"
            "1tzt6tYG94oVt8YwK3u9gR-DHFcuadpNN"
            "/export?format=csv&gid=354598948"
        ),
        "ostes": (
            "https://docs.google.com/spreadsheets/d/"
            "1vedjfjpQAHA4l1iby_mZRdVayH0H4cjg"
            "/export?format=csv&gid=1926750281"
        )
    },

    "SET FREIGHT INTERNATIONAL": {
        "ordenes": (
            "https://docs.google.com/spreadsheets/d/"
            "166RzQ6DxBiZ1c7xjMQzyPJk2uLJI_piO"
            "/export?format=csv&gid=1292870764"
        ),
        "partes": (
            "https://docs.google.com/spreadsheets/d/"
            "1Nqbhl8o5qaKhI4LNxreicPW5Ew8kqShS"
            "/export?format=csv&gid=849445619"
        ),
        "ostes": (
            "https://docs.google.com/spreadsheets/d/"
            "1lshd4YaUyuZiYctys3RplStzcYpABNRj"
            "/export?format=csv&gid=1882046877"
        )
    },

    "SET LOGIS PLUS": {
        "ordenes": (
            "https://docs.google.com/spreadsheets/d/"
            "11q580KXBn-kX5t-eHAbV0kp-kTqIQBR6"
            "/export?format=csv&gid=663362391"
        ),
        "partes": (
            "https://docs.google.com/spreadsheets/d/"
            "1yrzwm5ixsaYNKwkZpfmFpDdvZnohFH61"
            "/export?format=csv&gid=1837946138"
        ),
        "ostes": (
            "https://docs.google.com/spreadsheets/d/"
            "1kcemsViXwHBaCXK58SGBxjfYs-zakhki"
            "/export?format=csv&gid=1472656211"
        )
    }
}

# =================================
# LOADERS
# =================================
@st.cache_data(ttl=600)
def cargar_ordenes(url):
    if not url:
        return pd.DataFrame()

    df = pd.read_csv(url)
    df.columns = df.columns.str.strip()

    # =====================================================
    # 🔥 COLUMN NORMALIZATION (DATABASE → SYSTEM)
    # =====================================================
    rename_map = {
        "Fecha Analisis": "FECHA",
        "Diferencia": "DIFERENCIA",
        "Comentarios": "COMENTARIOS",
        "Tipo De Unidad": "Tipo Unidad",
        "Razon de servicio": "Razon Reparacion",
    }

    df = df.rename(columns=rename_map)

    # =====================================================
    # DATE PARSE
    # =====================================================
    if "FECHA" in df.columns:
        df["FECHA"] = pd.to_datetime(
            df["FECHA"],
            errors="coerce",
            dayfirst=True
        )
        df = df[df["FECHA"] >= pd.Timestamp("2025-01-01")]

    return df

@st.cache_data(ttl=600)
def cargar_partes(url):
    if not url:
        return pd.DataFrame()

    df = pd.read_csv(url)
    df.columns = df.columns.str.strip()

    if "Fecha Analisis" in df.columns:
        df["Fecha Analisis"] = pd.to_datetime(
            df["Fecha Analisis"],
            errors="coerce",
            dayfirst=True
        )
        df = df[df["Fecha Analisis"] >= pd.Timestamp("2025-01-01")]


    return df

# =================================
# EMPRESA SELECTION
# =================================
st.subheader("Selección de Empresa")

empresa = st.selectbox(
    "Empresa",
    ["Selecciona empresa"] + list(EMPRESA_CONFIG.keys()),
    index=0
)

if empresa == "Selecciona empresa":
    st.info("Selecciona una empresa para consultar las órdenes.")
    st.stop()

config = EMPRESA_CONFIG[empresa]

df = cargar_ordenes(config["ordenes"])
df_partes = cargar_partes(config["partes"])
df_ostes = cargar_ordenes(config["ostes"])

if df.empty:
    st.warning("No hay datos disponibles para esta empresa.")
    st.stop()

def safe(x):
    if pd.isna(x) or x is None:
        return ""
    return str(x)

# =================================
# ÚLTIMOS 10 REGISTROS
# =================================
st.subheader("Últimos registros")

unidad_orden_sel = "Todas"

# collect unidades from both sources
unidades = set()

if "Unidad" in df.columns:
    unidades.update(df["Unidad"].dropna().astype(str).unique())

if not df_ostes.empty and "Unidad" in df_ostes.columns:
    unidades.update(df_ostes["Unidad"].dropna().astype(str).unique())

unidad_orden_sel = st.selectbox(
    "Filtrar por Unidad",
    ["Todas"] + sorted(unidades),
    index=0
)

columnas_resumen = [
    "Fecha Aceptado",
    "Fecha Iniciada",
    "Unidad",
    "Tipo Unidad",
    "Reporte",
    "Descripcion",
    "Razon Reparacion"
]

columnas_disponibles = [c for c in columnas_resumen if c in df.columns]

# =====================================================
# BUILD INTERNAL / EXTERNAL DATASETS
# =====================================================

df_interna = df.copy()
df_externa = df_ostes.copy()

# ==========================================
# FILTER BY UNIDAD
# ==========================================
if unidad_orden_sel != "Todas":
    if "Unidad" in df_interna.columns:
        df_interna = df_interna[df_interna["Unidad"].astype(str) == unidad_orden_sel]

    if "Unidad" in df_externa.columns:
        df_externa = df_externa[df_externa["Unidad"].astype(str) == unidad_orden_sel]


# ==========================================
# SORT & TAKE LAST 10
# ==========================================
if "FECHA" in df_interna.columns:
    df_interna = df_interna.sort_values("FECHA", ascending=False).head(10)

if "FECHA" in df_externa.columns:
    df_externa = df_externa.sort_values("FECHA", ascending=False).head(10)

# =====================================================
# MANO DE OBRA INTERNA
# =====================================================
st.markdown("### 🔧 Mano de Obra Interna")

if df_interna.empty:
    st.info("No hay registros internos.")
else:
    cols = st.columns(5)

    for i, (_, row) in enumerate(df_interna.iterrows()):
        col = cols[i % 5]

        with col:
            reporte = safe(row.get("Reporte"))
            unidad = safe(row.get("Unidad"))
            tipo = safe(row.get("Tipo Unidad"))
            razon = safe(row.get("Razon Reparacion"))
            desc = safe(row.get("Descripcion"))
            f_acep = safe(row.get("Fecha Aceptado"))
            f_ini = safe(row.get("Fecha Iniciada"))

            html = f"""
            <div style="padding:6px;">
                <div style="
                    background:#ffffff;
                    padding:14px;
                    border-radius:16px;
                    box-shadow:0 4px 10px rgba(0,0,0,0.08);
                    color:#111;
                    min-height:190px;
                    font-family:sans-serif;
                ">
                    <div style="font-weight:900;">{reporte}</div>

                    <div style="font-size:0.8rem; margin-top:4px;">
                        {unidad} &nbsp; | &nbsp; {tipo}
                    </div>

                    <hr style="margin:6px 0">

                    <div style="font-size:0.8rem;">
                        <b>Razón:</b> {razon}
                    </div>

                    <div style="font-size:0.8rem;">
                        <b>Descripción:</b> {desc}
                    </div>

                    <hr style="margin:6px 0">

                    <div style="font-size:0.75rem;">
                        {f_acep} &nbsp; | &nbsp; {f_ini}
                    </div>
                </div>
            </div>
            """

            components.html(html, height=260)

            if st.button("👁 Ver", key=f"ver_interna_{i}", use_container_width=True):
                st.session_state.modal_orden = row.to_dict()
                st.session_state.modal_tipo = "interna"

st.divider()
# =====================================================
# MANO DE OBRA EXTERNA (OSTES)
# =====================================================
st.markdown("### 🧾 Mano de Obra Externa (OSTES)")

if df_externa.empty:
    st.info("No hay registros externos.")
else:
    cols = st.columns(5)

    for i, (_, row) in enumerate(df_externa.iterrows()):
        col = cols[i % 5]

        with col:
            reporte = safe(row.get("Reporte"))
            unidad = safe(row.get("Unidad"))
            tipo = safe(row.get("Tipo Unidad"))
            razon = safe(row.get("Razon Reparacion"))
            desc = safe(row.get("Descripcion"))
            f_acep = safe(row.get("Fecha Aceptado"))
            f_ini = safe(row.get("Fecha Iniciada"))

            html = f"""
            <div style="padding:6px;">
                <div style="
                    background:#ffffff;
                    padding:14px;
                    border-radius:16px;
                    box-shadow:0 4px 10px rgba(0,0,0,0.08);
                    color:#111;
                    min-height:190px;
                    font-family:sans-serif;
                ">
                    <div style="font-weight:900;">{reporte}</div>

                    <div style="font-size:0.8rem; margin-top:4px;">
                        {unidad} &nbsp; | &nbsp; {tipo}
                    </div>

                    <hr style="margin:6px 0">

                    <div style="font-size:0.8rem;">
                        <b>Razón:</b> {razon}
                    </div>

                    <div style="font-size:0.8rem;">
                        <b>Descripción:</b> {desc}
                    </div>

                    <hr style="margin:6px 0">

                    <div style="font-size:0.75rem;">
                        {f_acep} &nbsp; | &nbsp; {f_ini}
                    </div>
                </div>
            </div>
            """

            components.html(html, height=260)

            if st.button("👁 Ver", key=f"ver_externa_{i}", use_container_width=True):
                st.session_state.modal_orden = row.to_dict()
                st.session_state.modal_tipo = "oste"

st.divider()
# =================================
# REFACCIONES RECIENTES
# =================================
st.subheader("Refacciones Recientes")

if not df_partes.empty and "Unidad" in df_partes.columns:

    unidad_partes_sel = st.selectbox(
        "Filtrar por Unidad",
        ["Todas"] + sorted(df_partes["Unidad"].dropna().astype(str).unique()),
        index=0
    )

    df_partes_filtrado = df_partes.copy()

    # Filter by Unidad
    if unidad_partes_sel != "Todas":
        df_partes_filtrado = df_partes_filtrado[
            df_partes_filtrado["Unidad"].astype(str) == unidad_partes_sel
        ]

    # Ensure Fecha Analisis is datetime
    if "Fecha Analisis" in df_partes_filtrado.columns:
        df_partes_filtrado["Fecha Analisis"] = pd.to_datetime(
            df_partes_filtrado["Fecha Analisis"],
            errors="coerce",
            dayfirst=True
        )

        # Sort newest first
        df_partes_filtrado = df_partes_filtrado.sort_values(
            "Fecha Analisis",
            ascending=False
        )

    # UNIQUE BY PARTE (keep newest record)
    if "Parte" in df_partes_filtrado.columns:
        df_partes_clean = df_partes_filtrado.drop_duplicates(
            subset=["Parte"],
            keep="first"
        )
    else:
        df_partes_clean = df_partes_filtrado.copy()

    # ==========================================
    # CORRECT COLUMN STRUCTURE PER EMPRESA
    # ==========================================

    if empresa in ["LINCOLN FREIGHT", "SET FREIGHT INTERNATIONAL", "SET LOGIS PLUS"]:

        columnas_partes = [
            "Unidad",
            "Parte",
            "Cantidad",
            "PU USD",
            "Total USD"
        ]

    elif empresa in ["IGLOO TRANSPORT", "PICUS"]:

        columnas_partes = [
            "Unidad",
            "Parte",
            "PU",
            "Cantidad",
            "Total Correccion"
        ]

    else:
        columnas_partes = [
            "Unidad",
            "Parte"
        ]

    df_partes_final = df_partes_clean[
        [c for c in columnas_partes if c in df_partes_clean.columns]
    ]

    st.dataframe(
        df_partes_final,
        hide_index=True,
        width="stretch"
    )

else:
    st.info("No hay información de partes disponible para esta empresa.")

# =================================
# FILTROS
# =================================
st.divider()
st.subheader("Filtros")

c1, c2, c3 = st.columns(3)

with c1:
    fecha_inicio = st.date_input(
        "Fecha inicio",
        value=date(2025, 1, 1),
        min_value=date(2025, 1, 1)
    )

with c2:
    fecha_fin = st.date_input(
        "Fecha fin",
        value=date.today()
    )

with c3:
    if "Unidad" in df.columns:
        unidad_sel = st.selectbox(
            "Unidad",
            ["Todas"] + sorted(df["Unidad"].dropna().astype(str).unique())
        )
    else:
        unidad_sel = "Todas"

# =================================
# APPLY FILTERS
# =================================
df_filtrado = df.copy()
df_ostes_filtrado = df_ostes.copy()

if "FECHA" in df_filtrado.columns:
    df_filtrado["FECHA"] = pd.to_datetime(
        df_filtrado["FECHA"],
        errors="coerce",
        dayfirst=True
    )

    df_filtrado = df_filtrado[
        (df_filtrado["FECHA"] >= pd.Timestamp("2025-01-01")) &
        (df_filtrado["FECHA"] <= pd.to_datetime(fecha_fin))
    ]

if "FECHA" in df_ostes_filtrado.columns:
    df_ostes_filtrado["FECHA"] = pd.to_datetime(
        df_ostes_filtrado["FECHA"],
        errors="coerce",
        dayfirst=True
    )

    df_ostes_filtrado = df_ostes_filtrado[
        (df_ostes_filtrado["FECHA"] >= pd.Timestamp("2025-01-01")) &
        (df_ostes_filtrado["FECHA"] <= pd.to_datetime(fecha_fin))
    ]


if unidad_sel != "Todas" and "Unidad" in df_filtrado.columns:
    df_filtrado = df_filtrado[
        df_filtrado["Unidad"].astype(str) == unidad_sel
    ]

if unidad_sel != "Todas" and "Unidad" in df_ostes_filtrado.columns:
    df_ostes_filtrado = df_ostes_filtrado[
        df_ostes_filtrado["Unidad"].astype(str) == unidad_sel
    ]


# =================================
# TABLA COMPLETA
# =================================
st.divider()
st.subheader("Todas las Órdenes")

columnas_ocultar = ["DIFERENCIA", "COMENTARIOS"]
columnas_mostrar = [c for c in df_filtrado.columns if c not in columnas_ocultar]

st.dataframe(
    df_filtrado[columnas_mostrar]
        .sort_values("FECHA", ascending=False),
    hide_index=True,
    width="stretch"
)

# =================================
# TABLA COMPLETA OSTE
# =================================
st.divider()
st.subheader("Todas las Órdenes Externas (OSTES)")

df_ostes_tabla = df_ostes_filtrado.copy()

# safety → make sure FECHA exists
if "FECHA" in df_ostes_tabla.columns:
    df_ostes_tabla = df_ostes_tabla.sort_values("FECHA", ascending=False)

if df_ostes_tabla.empty:
    st.info("No hay registros externos.")
else:
    st.dataframe(
        df_ostes_tabla,
        hide_index=True,
        width="stretch"
    )

# =================================
# FOOTER
# =================================
st.caption(
    f"Mostrando {len(df_filtrado)} registros | "
    f"Desde {fecha_inicio} hasta {fecha_fin}"
)

# =================================
# VIEW MODAL
# =================================
if st.session_state.get("modal_orden"):

    r = st.session_state.modal_orden
    tipo = st.session_state.get("modal_tipo", "interna")

    @st.dialog("Detalle de la Reparación")
    def modal():

        def safe(x):
            if pd.isna(x) or x is None:
                return ""
            return str(x)

        def safe_date(x):
            d = pd.to_datetime(x, errors="coerce")
            return d.date() if pd.notna(d) else "-"

        # =====================================================
        # ================== INTERNA ==========================
        # =====================================================
        if tipo == "interna":

            st.markdown(f"## Reporte {safe(r.get('Reporte'))}")

            # VEHICLE
            st.subheader("Unidad")

            c1, c2, c3 = st.columns(3)
            c1.markdown(f"**Unidad:** {safe(r.get('Unidad'))}")
            c2.markdown(f"**Modelo:** {safe(r.get('Modelo'))}")
            c3.markdown(f"**Tipo:** {safe(r.get('Tipo Unidad'))}")

            c4, c5 = st.columns(2)
            c4.markdown(f"**Flotilla:** {safe(r.get('Flotilla'))}")
            c5.markdown(f"**Sucursal:** {safe(r.get('Sucursal'))}")

            st.divider()

            # CLIENT
            st.subheader("Cliente")

            c1, c2 = st.columns(2)
            c1.markdown(f"**Nombre:** {safe(r.get('Nombre Cliente'))}")
            c2.markdown(f"**Factura:** {safe(r.get('Factura'))}")

            st.divider()

            # STATUS
            st.subheader("Estatus")
            st.markdown(f"**{safe(r.get('Estatus'))}**")

            st.divider()

            # DESCRIPTION
            st.subheader("Razón de reparación")
            st.write(safe(r.get("Razon Reparacion")))

            st.subheader("Descripción")
            st.write(safe(r.get("Descripcion")))

            st.divider()

            # DATES
            st.subheader("Fechas")

            c1, c2, c3 = st.columns(3)
            c1.markdown(f"**Análisis:** {safe_date(r.get('Fecha Analisis'))}")
            c2.markdown(f"**Registro:** {safe_date(r.get('Fecha Registro'))}")
            c3.markdown(f"**Aceptado:** {safe_date(r.get('Fecha Aceptado'))}")

            c4, c5, c6 = st.columns(3)
            c4.markdown(f"**Iniciado:** {safe_date(r.get('Fecha Iniciada'))}")
            c5.markdown(f"**Liberada:** {safe_date(r.get('Fecha Liberada'))}")
            c6.markdown(f"**Terminada:** {safe_date(r.get('Fecha Terminada'))}")

            st.divider()

            # TOTALS
            st.subheader("Totales")

            c1, c2, c3 = st.columns(3)
            c1.markdown(f"**Sub Total:** {safe(r.get('Sub Total'))}")
            c2.markdown(f"**IVA:** {safe(r.get('IVA'))}")
            c3.markdown(f"**Total:** {safe(r.get('Total'))}")

            c4, c5, c6 = st.columns(3)
            c4.markdown(f"**Total Corrección:** {safe(r.get('Total Correccion'))}")
            c5.markdown(f"**TC:** {safe(r.get('TC'))}")
            c6.markdown(f"**Total USD:** {safe(r.get('Total USD'))}")

            st.divider()

            # EXTRA
            st.subheader("Observaciones")
            st.markdown(f"**Diferencia:** {safe(r.get('DIFERENCIA'))}")
            st.write(safe(r.get("COMENTARIOS")))

        # =====================================================
        # ================== OSTE =============================
        # =====================================================
        else:

            st.markdown(f"## OSTE {safe(r.get('OSTE'))}")

            # VEHICLE
            st.subheader("Unidad")

            c1, c2, c3 = st.columns(3)
            c1.markdown(f"**Unidad:** {safe(r.get('Unidad'))}")
            c2.markdown(f"**Modelo:** {safe(r.get('Modelo'))}")
            c3.markdown(f"**Tipo:** {safe(r.get('Tipo Unidad'))}")

            c4, c5 = st.columns(2)
            c4.markdown(f"**Flotilla:** {safe(r.get('Flotilla'))}")
            c5.markdown(f"**Sucursal:** {safe(r.get('Sucursal'))}")

            st.divider()

            # PROVIDER
            st.subheader("Proveedor")

            c1, c2 = st.columns(2)
            c1.markdown(f"**Acreedor:** {safe(r.get('Acreedor'))}")
            c2.markdown(f"**Factura:** {safe(r.get('Factura'))}")

            st.divider()

            # STATUS
            st.subheader("Estado")
            st.markdown(f"**{safe(r.get('Status CT'))}**")

            st.divider()

            # SERVICE
            st.subheader("Servicio")
            st.markdown(f"**Reporte:** {safe(r.get('Reporte'))}")
            st.markdown(f"**Razón:** {safe(r.get('Razon Reparacion'))}")
            st.write(safe(r.get("Descripcion")))

            st.divider()

            # DATES
            st.subheader("Fechas")

            c1, c2, c3 = st.columns(3)
            c1.markdown(f"**Análisis:** {safe_date(r.get('Fecha Analisis'))}")
            c2.markdown(f"**Factura:** {safe_date(r.get('Fecha Factura'))}")
            c3.markdown(f"**OSTE:** {safe_date(r.get('Fecha OSTE'))}")

            c4, c5 = st.columns(2)
            c4.markdown(f"**Cierre:** {safe_date(r.get('Fecha Cierre'))}")
            c5.markdown(f"**Días reparación:** {safe(r.get('Dias Reparacion'))}")

            st.divider()

            # TOTALS
            st.subheader("Totales")

            c1, c2, c3 = st.columns(3)
            c1.markdown(f"**Subtotal:** {safe(r.get('Subtotal'))}")
            c2.markdown(f"**IVA:** {safe(r.get('IVA'))}")
            c3.markdown(f"**Total OSTE:** {safe(r.get('Total oste'))}")

            c4, c5 = st.columns(2)
            c4.markdown(f"**TC:** {safe(r.get('TC'))}")
            c5.markdown(f"**Total Corrección:** {safe(r.get('Total Correccion'))}")

            st.divider()

            # NOTES
            st.subheader("Observaciones")
            st.write(safe(r.get("Observaciones")))

        st.divider()

        if st.button("Cerrar"):
            st.session_state.modal_orden = None
            st.rerun()

    modal()
    st.session_state.modal_orden = None