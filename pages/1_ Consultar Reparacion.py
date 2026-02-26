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
        "Diferencia": "DIFERENCIA",
        "Comentarios": "COMENTARIOS",
        "Tipo De Unidad": "Tipo Unidad",
        "Razon de servicio": "Razon Reparacion",
    }

    df = df.rename(columns=rename_map)

    # =====================================================
    # DATE PARSE
    # =====================================================
    if "Fecha Registro" in df.columns:
        df["Fecha Registro"] = pd.to_datetime(
            df["Fecha Registro"],
            errors="coerce",
            dayfirst=True
        )

    return df

@st.cache_data(ttl=600)
def cargar_partes(url):
    if not url:
        return pd.DataFrame()

    df = pd.read_csv(url)
    df.columns = df.columns.str.strip()

    # Parse Fecha Compra (ONLY this column matters)
    if "Fecha Compra" in df.columns:
        df["Fecha Compra"] = pd.to_datetime(
            df["Fecha Compra"],
            errors="coerce",
            dayfirst=True
        )

        # Base rule → only 2025+
        df = df[df["Fecha Compra"] >= pd.Timestamp("2025-01-01")]

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
df_ostes = pd.read_csv(config["ostes"])
df_ostes.columns = df_ostes.columns.str.strip()

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

# ==========================================
# BUILD UNIDADES DROPDOWN BASED ON 2025+ DATA
# ==========================================
unidades = set()

# ---- INTERNA (Fecha Registro) ----
df_tmp_interna = df.copy()

if "Fecha Registro" in df_tmp_interna.columns:
    df_tmp_interna["Fecha Registro"] = pd.to_datetime(
        df_tmp_interna["Fecha Registro"],
        errors="coerce",
        dayfirst=True
    )

    df_tmp_interna = df_tmp_interna[
        df_tmp_interna["Fecha Registro"] >= pd.Timestamp("2025-01-01")
    ]

    if "Unidad" in df_tmp_interna.columns:
        unidades.update(
            df_tmp_interna["Unidad"]
            .dropna()
            .astype(str)
            .str.strip()
            .unique()
        )

# ---- EXTERNA (Fecha OSTE) ----
df_tmp_externa = df_ostes.copy()

if "Fecha OSTE" in df_tmp_externa.columns:
    df_tmp_externa["Fecha OSTE"] = pd.to_datetime(
        df_tmp_externa["Fecha OSTE"],
        errors="coerce"
    )

    df_tmp_externa = df_tmp_externa[
        df_tmp_externa["Fecha OSTE"] >= pd.Timestamp("2025-01-01")
    ]

    if "Unidad" in df_tmp_externa.columns:
        unidades.update(
            df_tmp_externa["Unidad"]
            .dropna()
            .astype(str)
            .str.strip()
            .unique()
        )

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
# BUILD INTERNAL DATASET
# =====================================================
df_interna = df.copy()

if "Fecha Registro" in df_interna.columns:

    df_interna["Fecha Registro"] = pd.to_datetime(
        df_interna["Fecha Registro"],
        errors="coerce",
        dayfirst=True
    )

    df_interna = df_interna[
        df_interna["Fecha Registro"] >= pd.Timestamp("2025-01-01")
    ]

    if unidad_orden_sel != "Todas" and "Unidad" in df_interna.columns:
        df_interna = df_interna[
            df_interna["Unidad"]
            .astype(str)
            .str.strip()
            .str.upper()
            == unidad_orden_sel.strip().upper()
        ]

    df_interna = df_interna.sort_values(
        "Fecha Registro",
        ascending=False
    ).head(10)

# =====================================================
# BUILD EXTERNAL DATASET (SAME STRUCTURE)
# =====================================================
df_externa = df_ostes.copy()

if "Fecha OSTE" in df_externa.columns:

    df_externa["Fecha OSTE"] = pd.to_datetime(
        df_externa["Fecha OSTE"],
        errors="coerce"
    )

    df_externa = df_externa[
        df_externa["Fecha OSTE"] >= pd.Timestamp("2025-01-01")
    ]

    if unidad_orden_sel != "Todas" and "Unidad" in df_externa.columns:
        df_externa = df_externa[
            df_externa["Unidad"]
            .astype(str)
            .str.strip()
            .str.upper()
            == unidad_orden_sel.strip().upper()
        ]

    df_externa = df_externa.sort_values(
        "Fecha OSTE",
        ascending=False
    ).head(10)

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
            f_oste = safe(row.get("Fecha OSTE"))
            f_factura = safe(row.get("Fecha Factura"))

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
                        {f_oste} &nbsp; | &nbsp; {f_factura}
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

    # Ensure Fecha Compra is datetime
    df_partes["Fecha Compra"] = pd.to_datetime(
        df_partes["Fecha Compra"],
        errors="coerce",
        dayfirst=True
    )

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
        ascending=False
    )

    # -----------------------------
    # DISPLAY WITH YOUR ORIGINAL COLUMN LOGIC
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
        width="stretch"
    )

else:
    st.info("No hay información de partes disponible para esta empresa.")