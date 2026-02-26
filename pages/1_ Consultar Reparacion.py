import streamlit as st
import pandas as pd
from datetime import date
from auth import require_login, require_access
import streamlit.components.v1 as components

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

# =================================
# HARD RESET ON PAGE LOAD
# =================================

if "consulta_reparacion_initialized" not in st.session_state:

    # Reset modals
    st.session_state["modal_orden"] = None
    st.session_state["modal_tipo"] = None

    # Mark as initialized to avoid loop
    st.session_state["consulta_reparacion_initialized"] = True

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
#Internas
@st.cache_data(ttl=600)
def cargar_ordenes(url):
    if not url:
        return pd.DataFrame()

    df = pd.read_csv(url)
    df.columns = df.columns.str.strip()

    rename_map = {
        "Diferencia": "DIFERENCIA",
        "Comentarios": "COMENTARIOS",
        "Tipo De Unidad": "Tipo Unidad",
        "Razon de servicio": "Razon Reparacion",
    }

    df = df.rename(columns=rename_map)

    if "Fecha Registro" in df.columns:
        df["Fecha Registro"] = pd.to_datetime(
            df["Fecha Registro"],
            errors="coerce",
            format="mixed"
        )

    return df

#Ostes
@st.cache_data(ttl=600)
def cargar_ostes(url):
    if not url:
        return pd.DataFrame()

    df = pd.read_csv(url)
    df.columns = df.columns.str.strip()

    if "Fecha OSTE" in df.columns:
        df["Fecha OSTE"] = pd.to_datetime(
            df["Fecha OSTE"],
            errors="coerce",
            format="mixed"
        )

    return df

#Cargar Partes
@st.cache_data(ttl=600)
def cargar_partes(url):
    if not url:
        return pd.DataFrame()

    df = pd.read_csv(url)
    df.columns = df.columns.str.strip()

    if "Fecha Compra" in df.columns:
        df["Fecha Compra"] = pd.to_datetime(
            df["Fecha Compra"],
            errors="coerce",
            format="mixed"
        )

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
df_ostes = cargar_ostes(config["ostes"])

# =================================
# HARD LOCK 2025+ FOR INTERNA & EXTERNA
# =================================
LOCK_DATE = pd.Timestamp("2025-01-01")

if "Fecha Registro" in df.columns:
    df = df[df["Fecha Registro"] >= LOCK_DATE]

if "Fecha OSTE" in df_ostes.columns:
    df_ostes = df_ostes[df_ostes["Fecha OSTE"] >= LOCK_DATE]

if df.empty:
    st.warning("No hay datos disponibles para esta empresa.")
    st.stop()

# =================================
# UNIDAD FILTER (INTERNA + EXTERNA)
# =================================
st.markdown("### Filtro por Unidad")

unidades_interna = []
unidades_externa = []

if "Unidad" in df.columns:
    unidades_interna = df["Unidad"].dropna().astype(str).str.strip()

if "Unidad" in df_ostes.columns:
    unidades_externa = df_ostes["Unidad"].dropna().astype(str).str.strip()

unidades_unificadas = sorted(
    pd.concat([unidades_interna, unidades_externa]).unique()
)

unidad_sel = st.selectbox(
    "Unidad",
    ["Todas"] + unidades_unificadas,
    index=0
)

def safe(x):
    if pd.isna(x) or x is None:
        return ""
    return str(x)

# =====================================================
# BUILD INTERNAL DATASET (LATEST 10)
# =====================================================
df_interna = df.copy()

if unidad_sel != "Todas":
    df_interna = df_interna[
        df_interna["Unidad"].astype(str).str.strip() == unidad_sel.strip()
    ]

if "Fecha Registro" in df_interna.columns:

    df_interna = df_interna.sort_values(
        by="Fecha Registro",
        ascending=False,
        na_position="last"
    ).head(10)

# =====================================================
# BUILD EXTERNAL DATASET (LATEST 10)
# =====================================================
df_externa = df_ostes.copy()

if unidad_sel != "Todas":
    df_externa = df_externa[
        df_externa["Unidad"].astype(str).str.strip() == unidad_sel.strip()
    ]

if "Fecha OSTE" in df_externa.columns:

    df_externa = df_externa.sort_values(
        by="Fecha OSTE",
        ascending=False,
        na_position="last"
    ).head(10)

# =====================================================
# MANO DE OBRA INTERNA
# =====================================================
if unidad_sel != "Todas" and df_interna.empty and df_externa.empty:
    st.warning("No hay reportes para esta unidad.")

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
            fecha_registro = row.get("Fecha Registro")
            if pd.notna(fecha_registro):
                fecha_registro = fecha_registro.strftime("%d/%m/%Y")
            else:
                fecha_registro = ""

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
                        <b>Fecha Registro:</b> {fecha_registro}
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
            fecha_oste = row.get("Fecha OSTE")
            if pd.notna(fecha_oste):
                fecha_oste = fecha_oste.strftime("%d/%m/%Y")
            else:
                fecha_oste = ""

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
                        <b>Fecha OSTE:</b> {fecha_oste}
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

    # 🔒 Hard lock to 2025+
    LOCK_DATE = pd.Timestamp("2025-01-01")

    df_partes_base = df_partes[
        df_partes["Fecha Compra"] >= LOCK_DATE
    ].copy()

    # -----------------------------
    # DROPDOWNS
    # -----------------------------
    col1, col2 = st.columns(2)

    with col1:
        unidad_partes_sel = st.selectbox(
            "Filtrar por Unidad",
            ["Todas"] + sorted(
                df_partes_base["Unidad"]
                .dropna()
                .astype(str)
                .str.strip()
                .unique()
            ),
            index=0
        )

    with col2:
        if "Parte" in df_partes_base.columns:
            parte_sel = st.selectbox(
                "Filtrar por Parte",
                ["Todas"] + sorted(
                    df_partes_base["Parte"]
                    .dropna()
                    .astype(str)
                    .str.strip()
                    .unique()
                ),
                index=0
            )
        else:
            parte_sel = "Todas"

    # -----------------------------
    # APPLY FILTERS
    # -----------------------------
    df_partes_filtrado = df_partes_base.copy()

    if unidad_partes_sel != "Todas":
        df_partes_filtrado = df_partes_filtrado[
            df_partes_filtrado["Unidad"]
            .astype(str)
            .str.strip()
            == unidad_partes_sel.strip()
        ]

    if parte_sel != "Todas":
        df_partes_filtrado = df_partes_filtrado[
            df_partes_filtrado["Parte"]
            .astype(str)
            .str.strip()
            == parte_sel.strip()
        ]

    # -----------------------------
    # SORT
    # -----------------------------
    df_partes_filtrado = df_partes_filtrado.sort_values(
        "Fecha Compra",
        ascending=False,
        na_position="last"
    )

    # -----------------------------
    # COLUMN LOGIC (UNCHANGED)
    # -----------------------------
    if empresa in ["LINCOLN FREIGHT", "SET FREIGHT INTERNATIONAL", "SET LOGIS PLUS"]:
        columnas_partes = [
            "Unidad",
            "Fecha Compra",
            "Parte",
            "PU USD",
            "Cantidad",
            "Total USD"
        ]
    elif empresa in ["IGLOO TRANSPORT", "PICUS"]:
        columnas_partes = [
            "Unidad",
            "Fecha Compra",
            "Parte",
            "PU",
            "IVA",
            "Cantidad",
            "Total Correccion"
        ]
    else:
        columnas_partes = [
            "Unidad",
            "Fecha Compra",
            "Parte"
        ]

    df_partes_final = df_partes_filtrado[
        [c for c in columnas_partes if c in df_partes_filtrado.columns]
    ]

    st.dataframe(
        df_partes_final,
        hide_index=True,
        use_container_width=True
    )

else:
    st.info("No hay información de partes disponible para esta empresa.")

# =================================
# FILTRO UNIDAD - TABLAS COMPLETAS (2025+)
# =================================
st.divider()
st.markdown("### Filtro Unidad - Tablas Completas")

unidades_interna_tabla = []
unidades_externa_tabla = []

if "Unidad" in df.columns:
    unidades_interna_tabla = df["Unidad"].dropna().astype(str).str.strip()

if "Unidad" in df_ostes.columns:
    unidades_externa_tabla = df_ostes["Unidad"].dropna().astype(str).str.strip()

unidades_tabla_unificadas = sorted(
    pd.concat([unidades_interna_tabla, unidades_externa_tabla]).unique()
)

unidad_tabla_sel = st.selectbox(
    "Unidad (Tablas Completas)",
    ["Todas"] + unidades_tabla_unificadas,
    index=0
)

# =================================
# TABLA COMPLETA - INTERNAS (2025+)
# =================================
st.subheader("Todas las Órdenes Internas")

df_tabla_interna = df.copy()

if unidad_tabla_sel != "Todas":
    df_tabla_interna = df_tabla_interna[
        df_tabla_interna["Unidad"].astype(str).str.strip() == unidad_tabla_sel.strip()
    ]

if df_tabla_interna.empty:
    st.info("No hay órdenes internas.")
else:

    columnas_ocultar = ["DIFERENCIA", "COMENTARIOS"]
    columnas_mostrar = [
        c for c in df_tabla_interna.columns
        if c not in columnas_ocultar
    ]

    if "Fecha Registro" in df_tabla_interna.columns:
        df_tabla_interna = df_tabla_interna.sort_values(
            "Fecha Registro",
            ascending=False
        )

    st.dataframe(
        df_tabla_interna[columnas_mostrar],
        hide_index=True,
        use_container_width=True
    )

# =================================
# TABLA COMPLETA - EXTERNAS (OSTES 2025+)
# =================================
st.divider()
st.subheader("Todas las Órdenes Externas (OSTES)")

df_tabla_externa = df_ostes.copy()

if unidad_tabla_sel != "Todas":
    df_tabla_externa = df_tabla_externa[
        df_tabla_externa["Unidad"].astype(str).str.strip() == unidad_tabla_sel.strip()
    ]

if df_tabla_externa.empty:
    st.info("No hay registros externos.")
else:

    if "Fecha OSTE" in df_tabla_externa.columns:
        df_tabla_externa = df_tabla_externa.sort_values(
            "Fecha OSTE",
            ascending=False
        )

    st.dataframe(
        df_tabla_externa,
        hide_index=True,
        use_container_width=True
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

            st.subheader("Unidad")

            c1, c2, c3 = st.columns(3)
            c1.markdown(f"**Unidad:** {safe(r.get('Unidad'))}")
            c2.markdown(f"**Modelo:** {safe(r.get('Modelo'))}")
            c3.markdown(f"**Tipo:** {safe(r.get('Tipo Unidad'))}")

            c4, c5 = st.columns(2)
            c4.markdown(f"**Flotilla:** {safe(r.get('Flotilla'))}")
            c5.markdown(f"**Sucursal:** {safe(r.get('Sucursal'))}")

            st.divider()

            st.subheader("Cliente")

            c1, c2 = st.columns(2)
            c1.markdown(f"**Nombre:** {safe(r.get('Nombre Cliente'))}")
            c2.markdown(f"**Factura:** {safe(r.get('Factura'))}")

            st.divider()

            st.subheader("Estatus")
            st.markdown(f"**{safe(r.get('Estatus'))}**")

            st.divider()

            st.subheader("Razón de reparación")
            st.write(safe(r.get("Razon Reparacion")))

            st.subheader("Descripción")
            st.write(safe(r.get("Descripcion")))

            st.divider()

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

            st.subheader("Observaciones")
            st.markdown(f"**Diferencia:** {safe(r.get('DIFERENCIA'))}")
            st.write(safe(r.get("COMENTARIOS")))

        # =====================================================
        # ================== OSTE =============================
        # =====================================================
        else:

            st.markdown(f"## OSTE {safe(r.get('OSTE'))}")

            st.subheader("Unidad")

            c1, c2, c3 = st.columns(3)
            c1.markdown(f"**Unidad:** {safe(r.get('Unidad'))}")
            c2.markdown(f"**Modelo:** {safe(r.get('Modelo'))}")
            c3.markdown(f"**Tipo:** {safe(r.get('Tipo Unidad'))}")

            c4, c5 = st.columns(2)
            c4.markdown(f"**Flotilla:** {safe(r.get('Flotilla'))}")
            c5.markdown(f"**Sucursal:** {safe(r.get('Sucursal'))}")

            st.divider()

            st.subheader("Proveedor")

            c1, c2 = st.columns(2)
            c1.markdown(f"**Acreedor:** {safe(r.get('Acreedor'))}")
            c2.markdown(f"**Factura:** {safe(r.get('Factura'))}")

            st.divider()

            st.subheader("Estado")
            st.markdown(f"**{safe(r.get('Status CT'))}**")

            st.divider()

            st.subheader("Servicio")
            st.markdown(f"**Reporte:** {safe(r.get('Reporte'))}")
            st.markdown(f"**Razón:** {safe(r.get('Razon Reparacion'))}")
            st.write(safe(r.get("Descripcion")))

            st.divider()

            st.subheader("Fechas")

            c1, c2, c3 = st.columns(3)
            c1.markdown(f"**Análisis:** {safe_date(r.get('Fecha Analisis'))}")
            c2.markdown(f"**Factura:** {safe_date(r.get('Fecha Factura'))}")
            c3.markdown(f"**OSTE:** {safe_date(r.get('Fecha OSTE'))}")

            c4, c5 = st.columns(2)
            c4.markdown(f"**Cierre:** {safe_date(r.get('Fecha Cierre'))}")
            c5.markdown(f"**Días reparación:** {safe(r.get('Dias Reparacion'))}")

            st.divider()

            st.subheader("Totales")

            c1, c2, c3 = st.columns(3)
            c1.markdown(f"**Subtotal:** {safe(r.get('Subtotal'))}")
            c2.markdown(f"**IVA:** {safe(r.get('IVA'))}")
            c3.markdown(f"**Total OSTE:** {safe(r.get('Total oste'))}")

            c4, c5 = st.columns(2)
            c4.markdown(f"**TC:** {safe(r.get('TC'))}")
            c5.markdown(f"**Total Corrección:** {safe(r.get('Total Correccion'))}")

            st.divider()

            st.subheader("Observaciones")
            st.write(safe(r.get("Observaciones")))

        st.divider()

        if st.button("Cerrar"):
            st.session_state.modal_orden = None
            st.rerun()

    modal()