import streamlit as st
import requests
import io
import pandas as pd
import json
import pydeck as pdk
from auth import require_login, require_access
import streamlit.components.v1 as components
from streamlit_autorefresh import st_autorefresh # type: ignore
from datetime import datetime

# =================================
# Page configuration
# =================================
st.set_page_config(
    page_title="Rastreador y Seguimiento GPS de Unidades",
    layout="wide"
)

# =================================
# CSS THEME — BLUE + YELLOW
# =================================
st.markdown(
    """
    <style>

    /* Hide sidebar */
    [data-testid="stSidebar"] {
        display: none;
    }

    /* Main app background */
    .stApp {
        background-color: #151F6D;
    }

    /* Main container */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    /* Titles */
    h1 {
        color: #FFFFFF;
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }

    h2, h3 {
        color: #BFA75F;
        font-weight: 600;
    }

    /* General text */
    p, label, span {
        color: #F5F5F5 !important;
    }

    /* Divider */
    hr {
        border-color: rgba(191, 167, 95, 0.25);
    }

    /* File uploader */
    [data-testid="stFileUploader"] {
        background-color: #1B267A;
        border: 1px solid rgba(191, 167, 95, 0.25);
        border-radius: 12px;
        padding: 1rem;
    }

    /* Inputs / Selects */
    div[data-baseweb="input"] > div,
    div[data-baseweb="select"] > div {
        background-color: #1B267A !important;
        border: 1px solid rgba(191, 167, 95, 0.25) !important;
        border-radius: 10px !important;
        color: white !important;
    }

    input {
        color: white !important;
    }

    input::placeholder {
        color: #d0d0d0 !important;
    }

    div[data-baseweb="select"] * {
        color: white !important;
    }

    /* Buttons */
    div.stButton > button,
    div[data-testid="stDownloadButton"] > button {
        border-radius: 12px;
        font-weight: 600;
        transition: all 0.2s ease;
        border: none;
    }

    /* Standard buttons */
    div.stButton > button {
        background-color: #1B267A;
        color: white;
        border: 1px solid rgba(191, 167, 95, 0.25);
    }

    div.stButton > button:hover {
        background-color: #24338C;
        border-color: #BFA75F;
        color: #BFA75F;
        transform: translateY(-1px);
    }

    /* Download button */
    div[data-testid="stDownloadButton"] > button {
        background-color: #BFA75F;
        color: #151F6D;
        box-shadow: 0 4px 12px rgba(191, 167, 95, 0.25);
    }

    div[data-testid="stDownloadButton"] > button:hover {
        background-color: #d4bc73;
        color: #151F6D;
        transform: translateY(-1px);
    }

    /* Back button */
    button[kind="secondary"] {
        background-color: transparent !important;
        color: #BFA75F !important;
        border: 1px solid #BFA75F !important;
    }

    button[kind="secondary"]:hover {
        background-color: #BFA75F !important;
        color: #151F6D !important;
    }

    /* Metrics */
    [data-testid="metric-container"] {
        background-color: #1B267A;
        border: 1px solid rgba(191, 167, 95, 0.20);
        padding: 1rem;
        border-radius: 14px;
    }

    /* Dataframes */
    [data-testid="stDataFrame"] {
        border: 1px solid rgba(191, 167, 95, 0.20);
        border-radius: 12px;
        overflow: hidden;
    }

    /* Info / warning / success */
    div[data-baseweb="notification"] {
        border-radius: 12px;
    }

    </style>
    """,
    unsafe_allow_html=True
)

# =================================
# Security gates
# =================================
require_login()
require_access("gps_tracking")

# =================================
# Defensive modal reset
# =================================
if st.session_state.get("_reset_gps_page", True):

    st.session_state.modal_gps_unit = None

    st.session_state["_reset_gps_page"] = False

# Initialize modal state
st.session_state.setdefault("modal_gps_unit", None)

# =================================
# Top navigation
# =================================
if st.button("⬅ Volver al Dashboard"):

    st.session_state["_reset_gps_page"] = True
    st.session_state.modal_gps_unit = None

    st.switch_page("pages/dashboard.py")

st.title("🛰️  Rastreador y Seguimiento GPS de Unidades")

# =====================================================
# AUTO REFRESH TIMER
# =====================================================

REFRESH_SECONDS = 300  # 5 minutes

# =============================================
# AUTO REFRESH
# =============================================
st_autorefresh(
    interval=REFRESH_SECONDS * 1000,
    key="gps_auto_refresh"
)

# =============================================
# LIVE JAVASCRIPT COUNTDOWN
# =============================================
timer_html = f"""
<div id="gps-refresh-timer" style="
    background:#1B267A;
    border:1px solid rgba(191,167,95,0.25);
    padding:12px;
    border-radius:14px;
    margin-top:10px;
    margin-bottom:20px;
    text-align:center;
    color:white;
    font-weight:700;
    font-size:1rem;
">
    🔄 Actualización automática en:
    <span id="countdown" style="
        color:#BFA75F;
        font-size:1.1rem;
    ">
        05:00
    </span>
</div>

<script>

let totalSeconds = {REFRESH_SECONDS};

function updateCountdown() {{

    let minutes = Math.floor(totalSeconds / 60);
    let seconds = totalSeconds % 60;

    minutes = String(minutes).padStart(2, '0');
    seconds = String(seconds).padStart(2, '0');

    document.getElementById("countdown").innerHTML =
        `${{minutes}}:${{seconds}}`;

    totalSeconds--;

    if (totalSeconds < 0) {{
        totalSeconds = {REFRESH_SECONDS};
    }}
}}

updateCountdown();

setInterval(updateCountdown, 1000);

</script>
"""

components.html(
    timer_html,
    height=80
)

#==============================================================================================================
# Session token
SESSION_TOKEN = "763aade0cf05363d50e5ddcb2f597f6cb0c94e73cecae0c8ac8c"

#==============================================================================================================
# Location endpoint
url = f"https://api.gpsinsight.com/v2/vehicle/location?session_token={SESSION_TOKEN}"

#==============================================================================================================

# =================================
# API REQUEST
# =================================
try:

    response = requests.get(url)
    response.raise_for_status()

    result = response.json()

    vehicles = result.get("data", [])

    if vehicles:

        df = pd.DataFrame(vehicles)

        with open(
            "vehicles.json",
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                vehicles,
                f,
                indent=4,
                ensure_ascii=False
            )

    else:
        st.warning(
            "No vehicle location data returned."
        )

except requests.exceptions.RequestException as e:

    st.error(f"Request failed: {e}")

except Exception as e:

    st.error(f"Unexpected error: {e}")

# =========================================================
# KPI DASHBOARD
# =========================================================
if "df" in locals() and not df.empty:

    st.divider()

    st.header("📊 Dashboard Operativo GPS")

    # =========================================
    # UNIT TYPE CLASSIFICATION
    # =========================================
    df["label"] = (
        df["label"]
        .astype(str)
    )

    # Cajas / Remolques
    cajas_df = df[
        df["label"]
        .str.lower()
        .str.contains(
            "caja",
            na=False
        )
    ]

    # Tractocamiones
    trucks_df = df[
        ~df["label"]
        .str.lower()
        .str.contains(
            "caja",
            na=False
        )
    ]

    # =========================================
    # COUNTS
    # =========================================
    total_cajas = len(cajas_df)
    total_trucks = len(trucks_df)

    moving_cajas = (
        cajas_df["inst_speed"] > 0
    ).sum()

    moving_trucks = (
        trucks_df["inst_speed"] > 0
    ).sum()

    stopped_cajas = (
        cajas_df["inst_speed"] <= 0
    ).sum()

    stopped_trucks = (
        trucks_df["inst_speed"] <= 0
    ).sum()

    # =========================================
    # KPI SECTION
    # =========================================
    st.subheader("🚛 KPIs Tractocamiones")

    tc1, tc2, tc3 = st.columns(3)

    tc1.metric(
        "🚛 Total Tractos",
        total_trucks
    )

    tc2.metric(
        "🟢 Tractos en Movimiento",
        moving_trucks
    )

    tc3.metric(
        "🔴 Tractos Detenidos",
        stopped_trucks
    )

    st.divider()

    st.subheader("📦 KPIs Cajas / Remolques")

    rc1, rc2, rc3 = st.columns(3)

    rc1.metric(
        "📦 Total Cajas",
        total_cajas
    )

    rc2.metric(
        "🟢 Cajas en Movimiento",
        moving_cajas
    )

    rc3.metric(
        "🔴 Cajas Detenidas",
        stopped_cajas
    )

    st.divider()

    # =========================================
    # DATA PREP
    # =========================================
    df["inst_speed"] = pd.to_numeric(
        df["inst_speed"],
        errors="coerce"
    ).fillna(0)

    df["odometer"] = pd.to_numeric(
        df["odometer"],
        errors="coerce"
    ).fillna(0)

    df["voltage"] = pd.to_numeric(
        df["voltage"],
        errors="coerce"
    ).fillna(0)

    # =========================================
    # BASIC COUNTS
    # =========================================
    total_units = len(df)

    moving_units = (df["inst_speed"] > 0).sum()

    stopped_units = (df["inst_speed"] <= 0).sum()

    ignition_on = (
        df["ignition"]
        .astype(str)
        .str.lower()
        .eq("on")
        .sum()
    )

    ignition_off = (
        df["ignition"]
        .astype(str)
        .str.lower()
        .eq("off")
        .sum()
    )

    avg_speed = round(df["inst_speed"].mean(), 1)

    max_speed = round(df["inst_speed"].max(), 1)

    # =========================================
    # KPI POST-ITS
    # =========================================
    c1, c2, c3, c4, c5, c6 = st.columns(6)

    c1.metric("🚛 Total Unidades", total_units)

    c2.metric("🟢 En Movimiento", moving_units)

    c3.metric("🔴 Detenidas", stopped_units)

    c4.metric("⚡ Ignición Encendida", ignition_on)

    c5.metric("⛔ Ignición Apagada", ignition_off)

    c6.metric("🏎️ Velocidad Promedio", f"{avg_speed} km/h")

    # =========================================
    # SECOND ROW
    # =========================================
    c7, c8, c9 = st.columns(3)

    c7.metric(
        "🔥 Velocidad Máxima",
        f"{max_speed} km/h"
    )

    low_voltage = (df["voltage"] < 11).sum()

    c8.metric(
        "🔋 Voltaje Bajo",
        low_voltage
    )

    panic_active = 0

    if "inputs" in df.columns:

        for val in df["inputs"]:

            if isinstance(val, dict):

                if "Panic Button" in val:

                    if str(val["Panic Button"]).lower() == "on":
                        panic_active += 1

    c9.metric(
        "🚨 Botón de Pánico",
        panic_active
    )

    st.divider()

# =========================================================
# INDIVIDUAL UNIT TRACKING
# =========================================================
if "df" in locals() and not df.empty:

    st.header("🚛 Seguimiento Individual de Unidades")

    # =====================================================
    # FILTERS
    # =====================================================
    f1, f2, f3 = st.columns(3)

    # =============================================
    # UNIT FILTER
    # =============================================
    with f1:

        unidades = sorted(
            df["label"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        unidad_select = st.selectbox(
            "No. de Unidad",
            ["Todas"] + unidades
        )

    # =============================================
    # IGNITION FILTER
    # =============================================
    with f2:

        estado_select = st.selectbox(
            "Estado de Ignición",
            ["Todos", "on", "off"]
        )

    # =============================================
    # TYPE FILTER
    # =============================================
    with f3:

        tipo_select = st.selectbox(
            "Tipo de Unidad",
            [
                "Todos",
                "Tracto",
                "Caja"
            ]
        )

    # =====================================================
    # APPLY FILTERS
    # =====================================================
    df_units = df.copy()

    # =============================================
    # UNIT FILTER
    # =============================================
    if unidad_select != "Todas":

        df_units = df_units[
            df_units["label"]
            .astype(str) == unidad_select
        ]

    # =============================================
    # IGNITION FILTER
    # =============================================
    if estado_select != "Todos":

        df_units = df_units[
            df_units["ignition"]
            .astype(str)
            .str.lower() == estado_select
        ]

    # =============================================
    # TYPE FILTER
    # =============================================
    if tipo_select == "Caja":

        df_units = df_units[
            df_units["label"]
            .astype(str)
            .str.lower()
            .str.contains(
                "caja",
                na=False
            )
        ]

    elif tipo_select == "Tracto":

        df_units = df_units[
            ~df_units["label"]
            .astype(str)
            .str.lower()
            .str.contains(
                "caja",
                na=False
            )
        ]

    # =====================================================
    # RESET MODAL ON FILTER CHANGE
    # =====================================================
    current_filter_state = (
        unidad_select,
        estado_select
    )

    previous_filter_state = st.session_state.get(
        "_gps_filter_state"
    )

    if previous_filter_state != current_filter_state:

        st.session_state.modal_gps_unit = None
        st.session_state.gps_page = 1

    st.session_state["_gps_filter_state"] = current_filter_state

    # =====================================================
    # MODAL STATE
    # =====================================================
    st.session_state.setdefault("modal_gps_unit", None)

    # =====================================================
    # PAGINATION
    # =====================================================
    ITEMS_PER_PAGE = 10

    total_items = len(df_units)

    total_pages = max(
        (total_items - 1) // ITEMS_PER_PAGE + 1,
        1
    )

    st.session_state.setdefault("gps_page", 1)

    # Prevent overflow
    if st.session_state.gps_page > total_pages:
        st.session_state.gps_page = total_pages

    if st.session_state.gps_page < 1:
        st.session_state.gps_page = 1

    start_idx = (st.session_state.gps_page - 1) * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE

    df_units_page = df_units.iloc[start_idx:end_idx]

    # =====================================================
    # POSTITS
    # =====================================================
    total = len(df_units_page)

    if total == 0:

        st.warning("No se encontraron unidades.")

    else:

        idx = 0
        rows_needed = (total - 1) // 5 + 1

        for _ in range(rows_needed):

            cols = st.columns(5)

            for col in cols:

                if idx >= total:
                    break

                r = df_units_page.iloc[idx]

                unidad = str(r.get("label", "-"))
                direccion = str(r.get("address", "-"))
                velocidad = r.get("inst_speed", 0)
                ignicion = str(r.get("ignition", "-")).upper()
                odometro = r.get("odometer", "-")
                speed_label = str(r.get("speed_label", "-"))
                ultima_conexion = str(r.get("fix_time", "-"))
                voltaje = str(r.get("voltage", "-"))

                color_estado = (
                    "#D4EDDA"
                    if ignicion.lower() == "on"
                    else "#F8D7DA"
                )

                with col:

                    html = f"""
                    <div style="padding:6px;">
                        <div style="
                            background:#e8f0ff;
                            padding:14px;
                            border-radius:16px;
                            box-shadow:0 4px 10px rgba(0,0,0,0.08);
                            color:#111;
                            min-height:260px;
                            font-family:sans-serif;
                        ">

                            <div style="
                                font-size:1.1rem;
                                font-weight:900;
                            ">
                                🚛 {unidad}
                            </div>

                            <hr style="margin:8px 0">

                            <div style="
                                font-size:0.75rem;
                                min-height:55px;
                            ">
                                {direccion}
                            </div>

                            <div style="
                                margin-top:8px;
                                font-size:0.8rem;
                            ">
                                <strong>Velocidad:</strong> {velocidad} km/h
                            </div>

                            <div style="
                                font-size:0.8rem;
                            ">
                                <strong>Odómetro:</strong> {odometro}
                            </div>

                            <div style="
                                font-size:0.8rem;
                            ">
                                <strong>Voltaje:</strong> {voltaje}V
                            </div>

                            <div style="
                                margin-top:8px;
                                padding:6px;
                                border-radius:8px;
                                background:{color_estado};
                                text-align:center;
                                font-weight:700;
                            ">
                                Ignición: {ignicion}
                            </div>

                            <div style="
                                margin-top:8px;
                                font-size:0.75rem;
                                color:#444;
                            ">
                                {speed_label}
                            </div>

                            <div style="
                                margin-top:6px;
                                font-size:0.72rem;
                                opacity:0.75;
                            ">
                                Última conexión:
                                <br>
                                {ultima_conexion}
                            </div>

                        </div>
                    </div>
                    """

                    components.html(html, height=310)

                    # =====================================
                    # BUTTONS
                    # =====================================
                    b1, b2 = st.columns(2)

                    with b1:

                        if st.button(
                            "👁 Ver",
                            key=f"gps_unit_{unidad}_{idx}",
                            use_container_width=True
                        ):
                            st.session_state.modal_gps_unit = r.to_dict()

                    with b2:

                        excel_df = pd.DataFrame([r])

                        excel_filename = (
                            f"Unidad_{unidad}.xlsx"
                        )

                        excel_buffer = io.BytesIO()

                        with pd.ExcelWriter(
                            excel_buffer,
                            engine="openpyxl"
                        ) as writer:

                            excel_df.to_excel(
                                writer,
                                index=False,
                                sheet_name="GPS"
                            )

                        excel_buffer.seek(0)

                        st.download_button(
                            label="💾 Guardar",
                            data=excel_buffer,
                            file_name=excel_filename,
                            mime=(
                                "application/"
                                "vnd.openxmlformats-officedocument."
                                "spreadsheetml.sheet"
                            ),
                            key=f"save_excel_{unidad}_{idx}",
                            use_container_width=True
                        )

                idx += 1

    # =====================================================
    # PAGINATION CONTROLS
    # =====================================================
    st.divider()

    p1, p2, p3 = st.columns([1,2,1])

    with p1:

        if st.button(
            "⬅ Anterior",
            disabled=st.session_state.gps_page <= 1,
            use_container_width=True
        ):
            st.session_state.gps_page -= 1
            st.session_state.modal_gps_unit = None
            st.rerun()

    with p2:

        st.markdown(
            f"""
            <div style="
                text-align:center;
                padding-top:8px;
                font-weight:700;
                color:white;
            ">
                Página {st.session_state.gps_page} de {total_pages}
            </div>
            """,
            unsafe_allow_html=True
        )

    with p3:

        if st.button(
            "Siguiente ➡",
            disabled=st.session_state.gps_page >= total_pages,
            use_container_width=True
        ):
            st.session_state.gps_page += 1
            st.session_state.modal_gps_unit = None
            st.rerun()

    # =====================================================
    # MODAL
    # =====================================================
    if st.session_state.get("modal_gps_unit"):

        gps_row = st.session_state.modal_gps_unit

        unidad_modal = gps_row.get("label", "-")

        @st.dialog(f"Unidad {unidad_modal}")
        def modal_gps():

            st.subheader("📍 Ubicación")

            st.markdown(
                f"""
                **Dirección:**  
                {gps_row.get("address", "-")}
                """
            )

            c1, c2, c3 = st.columns(3)

            with c1:
                st.metric(
                    "Velocidad",
                    f"{gps_row.get('inst_speed', 0)} km/h"
                )

            with c2:
                st.metric(
                    "Ignición",
                    str(gps_row.get("ignition", "-")).upper()
                )

            with c3:
                st.metric(
                    "Voltaje",
                    f"{gps_row.get('voltage', '-')}"
                )

            st.divider()

            st.subheader("📡 Información GPS")

            st.markdown(
                f"""
                - **Latitud:** {gps_row.get("latitude", "-")}
                - **Longitud:** {gps_row.get("longitude", "-")}
                - **Dirección:** {gps_row.get("direction", "-")}
                - **Heading:** {gps_row.get("heading", "-")}
                - **Última conexión:** {gps_row.get("fix_time", "-")}
                - **Tiempo detenido:** {gps_row.get("speed_label", "-")}
                - **Odómetro:** {gps_row.get("odometer", "-")}
                """
            )

            st.divider()

            st.subheader("👤 Operador")

            st.markdown(
                f"""
                - **Driver ID:** {gps_row.get("driver_id", "-")}
                - **Estado Driver:** {gps_row.get("driver_status", "-")}
                - **Último cambio:** {gps_row.get("driver_date", "-")}
                """
            )

            st.divider()

            st.subheader("🔌 Inputs")

            st.json(gps_row.get("inputs", {}))

            if st.button("Cerrar"):
                st.session_state.modal_gps_unit = None
                st.rerun()

        modal_gps()

    st.divider()

    st.subheader("📊 Estado de Ignición de Unidades")

    # =====================================================
    # CHARTS
    # =====================================================
    col1, col2 = st.columns(2)

    with col1:

        st.subheader("Estado de Ignición")

        ignition_counts = (
            df["ignition"]
            .astype(str)
            .value_counts()
        )

        st.bar_chart(ignition_counts)

    with col2:

        st.subheader("Distribución de Velocidades")

        speed_df = df[df["inst_speed"] > 0]

        if not speed_df.empty:

            st.bar_chart(
                speed_df["inst_speed"]
            )

        else:
            st.info("No se detectaron unidades en movimiento.")

    st.divider()

    # =====================================================
    # LONGEST STOPPED UNITS
    # =====================================================
    with st.expander(
        "🛑 Unidades Detenidas por Más Tiempo",
        expanded=False
    ):

        if "speed_label" in df.columns:

            stopped_df = df[
                df["speed_label"]
                .astype(str)
                .str.contains(
                    "Stopped",
                    case=False,
                    na=False
                )
            ][[
                "label",
                "speed_label",
                "address",
                "fix_time"
            ]]

            st.dataframe(
                stopped_df,
                use_container_width=True,
                height=350
            )

            stopped_buffer = io.BytesIO()

            with pd.ExcelWriter(
                stopped_buffer,
                engine="openpyxl"
            ) as writer:

                stopped_df.to_excel(
                    writer,
                    index=False,
                    sheet_name="Detenidas"
                )

            stopped_buffer.seek(0)

            st.download_button(
                label="💾 Descargar Unidades Detenidas",
                data=stopped_buffer,
                file_name="Unidades_Detenidas.xlsx",
                mime=(
                    "application/"
                    "vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                ),
                use_container_width=True
            )

    st.divider()

    # =====================================================
    # LOW VOLTAGE ALERTS
    # =====================================================
    with st.expander(
        "🔋 Alertas de Voltaje Bajo",
        expanded=False
    ):

        voltage_df = df[df["voltage"] < 11][[
            "label",
            "voltage",
            "address",
            "fix_time"
        ]]

        if not voltage_df.empty:

            st.dataframe(
                voltage_df,
                use_container_width=True,
                height=250
            )

            voltage_buffer = io.BytesIO()

            with pd.ExcelWriter(
                voltage_buffer,
                engine="openpyxl"
            ) as writer:

                voltage_df.to_excel(
                    writer,
                    index=False,
                    sheet_name="Voltaje_Bajo"
                )

            voltage_buffer.seek(0)

            st.download_button(
                label="💾 Descargar Voltaje Bajo",
                data=voltage_buffer,
                file_name="Voltaje_Bajo.xlsx",
                mime=(
                    "application/"
                    "vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                ),
                use_container_width=True
            )

        else:
            st.success(
                "No se detectaron unidades con voltaje bajo."
            )

    st.divider()

    # =====================================================
    # FULL UNIT TABLE
    # =====================================================
    with st.expander(
        "🚛 Tabla General de Flotilla",
        expanded=False
    ):

        # =====================================
        # SAFE DATAFRAME COPY
        # =====================================
        display_df = df.copy()

        for col in display_df.columns:

            display_df[col] = display_df[col].apply(
                lambda x:
                json.dumps(
                    x,
                    ensure_ascii=False
                )
                if isinstance(x, (dict, list))
                else x
            )

        # =====================================
        # DISPLAY TABLE
        # =====================================
        st.dataframe(
            display_df,
            use_container_width=True,
            height=700
        )

        # =====================================
        # EXPORT
        # =====================================
        fleet_buffer = io.BytesIO()

        with pd.ExcelWriter(
            fleet_buffer,
            engine="openpyxl"
        ) as writer:

            display_df.to_excel(
                writer,
                index=False,
                sheet_name="Flotilla"
            )

        fleet_buffer.seek(0)

        st.download_button(
            label="💾 Descargar Tabla General",
            data=fleet_buffer,
            file_name="Flotilla_GPS.xlsx",
            mime=(
                "application/"
                "vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            use_container_width=True
        )

    st.divider()

    # =====================================================
    # LIVE GPS MAP
    # =====================================================
    st.subheader("🗺️ Mapa GPS de Unidades")

    map_df = df.copy()

    # =============================================
    # CLEAN GPS DATA
    # =============================================
    map_df["latitude"] = pd.to_numeric(
        map_df["latitude"],
        errors="coerce"
    )

    map_df["longitude"] = pd.to_numeric(
        map_df["longitude"],
        errors="coerce"
    )

    map_df["inst_speed"] = pd.to_numeric(
        map_df["inst_speed"],
        errors="coerce"
    ).fillna(0)

    map_df = map_df.dropna(
        subset=["latitude", "longitude"]
    )

    # =============================================
    # STOPPED TIME PARSER
    # =============================================
    import re

    def extract_stopped_minutes(speed_label):

        if not isinstance(speed_label, str):
            return 0

        speed_label = speed_label.lower()

        total_minutes = 0

        # days
        d = re.search(r"(\d+)\s*day", speed_label)
        if d:
            total_minutes += int(d.group(1)) * 1440

        # hours
        h = re.search(r"(\d+)\s*hr", speed_label)
        if h:
            total_minutes += int(h.group(1)) * 60

        # minutes
        m = re.search(r"(\d+)\s*min", speed_label)
        if m:
            total_minutes += int(m.group(1))

        return total_minutes

    # =============================================
    # COLOR STATES
    # =============================================
    def get_color(row):

        speed = float(
            row.get("inst_speed", 0)
        )

        speed_label = str(
            row.get("speed_label", "")
        )

        # =====================================
        # MOVING = GREEN
        # =====================================
        if speed > 0:
            return [0, 255, 0]

        stopped_minutes = extract_stopped_minutes(
            speed_label
        )

        # =====================================
        # < 1 HOUR = ORANGE
        # =====================================
        if stopped_minutes < 60:
            return [255, 165, 0]

        # =====================================
        # 1-6 HOURS = RED-ORANGE
        # =====================================
        if stopped_minutes < 360:
            return [255, 80, 0]

        # =====================================
        # 6-24 HOURS = RED
        # =====================================
        if stopped_minutes < 1440:
            return [255, 0, 0]

        # =====================================
        # 1-7 DAYS = DARK RED
        # =====================================
        if stopped_minutes < 10080:
            return [139, 0, 0]

        # =====================================
        # CRITICAL STOPPED = BLACK
        # =====================================
        return [0, 0, 0]

    map_df["color"] = map_df.apply(
        get_color,
        axis=1
    )

    if not map_df.empty:

        st.info(
            """
🟢 En Movimiento  
🟠 Detenido < 1 Hora  
🔴 Detenido Varias Horas  
🟥 Detenido +1 Día  
⚫ Detenido Crítico
            """
        )

        # =============================================
        # PYDECK LAYER
        # =============================================
        layer = pdk.Layer(
            "ScatterplotLayer",
            data=map_df,

            get_position="[longitude, latitude]",

            get_fill_color="color",

            # =====================================
            # INTERACTIVE SCALING
            # =====================================
            radius_units="pixels",

            get_radius=12,

            radius_min_pixels=6,
            radius_max_pixels=30,

            pickable=True,
            auto_highlight=True,

            stroked=True,
            filled=True,

            line_width_min_pixels=2,

            get_line_color=[255, 255, 255]
        )

        # =============================================
        # TOOLTIP
        # =============================================
        tooltip = {
            "html": """
                <b>Unidad:</b> {label} <br/>
                <b>Latitud:</b> {latitude} <br/>
                <b>Longitud:</b> {longitude} <br/>
                <b>Velocidad:</b> {inst_speed} km/h <br/>
                <b>Ignición:</b> {ignition} <br/>
                <b>Tiempo detenido:</b> {speed_label} <br/>
                <b>Dirección:</b> {address}
            """,
            "style": {
                "backgroundColor": "#1B267A",
                "color": "white"
            }
        }

        # =============================================
        # VIEW STATE
        # =============================================
        view_state = pdk.ViewState(
            latitude=map_df["latitude"].mean(),
            longitude=map_df["longitude"].mean(),
            zoom=6.5,
            pitch=0
        )

        # =============================================
        # DISPLAY MAP
        # =============================================
        st.pydeck_chart(
            pdk.Deck(
                height=700,

                layers=[layer],

                initial_view_state=view_state,

                tooltip=tooltip,

                map_style="light"
            ),
            use_container_width=True
        )

        # =============================================
        # GPS COORDINATE TABLE
        # =============================================
        with st.expander(
            "📍 Coordenadas de Unidades",
            expanded=False
        ):

            st.dataframe(
                map_df[[
                    "label",
                    "latitude",
                    "longitude",
                    "address",
                    "ignition",
                    "inst_speed",
                    "speed_label"
                ]],
                use_container_width=True,
                height=300
            )

    else:

        st.warning(
            "No se encontraron coordenadas GPS válidas."
        )


#tests
# =====================================================
# GPS INSIGHT API TESTBENCH
# =====================================================
st.divider()

st.header("🧪 GPS Insight API Testbench")

st.caption(
    "Pruebas manuales de endpoints GPS Insight."
)

# =====================================================
# ENDPOINT SELECTOR
# =====================================================
endpoint_options = {
    "Vehicle Location":
        "vehicle/location",

    "Vehicle Attributes":
        "vehicle/getattributes",

    "Vehicle List":
        "vehicle/list",

    "Vehicle Groups":
        "vehicle/listvehiclegroups"
}

tb1, tb2 = st.columns(2)

with tb1:

    selected_label = st.selectbox(
        "Endpoint",
        list(endpoint_options.keys())
    )

endpoint = endpoint_options[selected_label]

# =====================================================
# VEHICLE DROPDOWN
# =====================================================
with tb2:

    vehicle_ids = []

    if "id" in df.columns:

        vehicle_ids = sorted(
            df["id"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

    tb_vehicle = st.selectbox(
        "Unidad / Vehicle ID",
        ["Todos"] + vehicle_ids
    )

# =====================================================
# EXECUTE
# =====================================================
if st.button(
    "🚀 Ejecutar Endpoint",
    use_container_width=True
):

    try:

        # =========================================
        # BUILD URL
        # =========================================
        test_url = (
            "https://api.gpsinsight.com/v2/"
            f"{endpoint}"
            f"?session_token={SESSION_TOKEN}"
        )

        # =========================================
        # OPTIONAL VEHICLE FILTER
        # =========================================
        if tb_vehicle != "Todos":

            test_url += (
                f"&vehicle={tb_vehicle}"
            )

        # =========================================
        # REQUEST
        # =========================================
        tb_response = requests.get(
            test_url
        )

        tb_response.raise_for_status()

        tb_json = tb_response.json()

        # =========================================
        # STATUS
        # =========================================
        st.success(
            "Endpoint ejecutado correctamente."
        )

        # =========================================
        # REQUEST URL
        # =========================================
        st.subheader("🔗 Request URL")

        st.code(
            test_url,
            language="text"
        )

        # =========================================
        # RAW RESPONSE
        # =========================================
        with st.expander(
            "📦 Raw JSON Response",
            expanded=True
        ):

            st.json(tb_json)

        # =========================================
        # TABLE VIEW
        # =========================================
        if "data" in tb_json:

            if isinstance(tb_json["data"], list):

                tb_df = pd.DataFrame(
                    tb_json["data"]
                )

                if not tb_df.empty:

                    st.subheader(
                        "📋 Data Table"
                    )

                    st.dataframe(
                        tb_df,
                        use_container_width=True,
                        height=500
                    )

                    # =================================
                    # EXPORT
                    # =================================
                    export_buffer = io.BytesIO()

                    with pd.ExcelWriter(
                        export_buffer,
                        engine="openpyxl"
                    ) as writer:

                        tb_df.to_excel(
                            writer,
                            index=False,
                            sheet_name="API_Test"
                        )

                    export_buffer.seek(0)

                    st.download_button(
                        label="💾 Descargar Resultado",
                        data=export_buffer,
                        file_name=(
                            f"{endpoint.replace('/', '_')}.xlsx"
                        ),
                        mime=(
                            "application/"
                            "vnd.openxmlformats-officedocument."
                            "spreadsheetml.sheet"
                        ),
                        use_container_width=True
                    )

                else:

                    st.warning(
                        "El endpoint no regresó datos."
                    )

            elif isinstance(tb_json["data"], dict):

                st.subheader(
                    "📋 Data Object"
                )

                st.json(tb_json["data"])

            else:

                st.info(
                    "El endpoint no contiene una estructura tabular."
                )

        else:

            st.warning(
                "La respuesta no contiene la llave 'data'."
            )

    except requests.exceptions.RequestException as e:

        st.error(
            f"Request failed: {e}"
        )

    except Exception as e:

        st.error(
            f"Unexpected error: {e}"
        )