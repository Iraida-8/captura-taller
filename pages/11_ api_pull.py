import streamlit as st
import requests
import io
import pandas as pd
import json
import re
from supabase import create_client
import pydeck as pdk
from auth import require_login, require_access
import streamlit.components.v1 as components
from datetime import datetime
from pages.css import load_css
from concurrent.futures import ThreadPoolExecutor, as_completed

# =================================
# RELEASE CHANNEL
# =================================

#APP_CHANNEL = "BETA"
APP_CHANNEL = "RELEASE"

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
        "Rastreador y Seguimiento GPS de Unidades - BETA"
        if APP_CHANNEL.upper() == "BETA"
        else "Rastreador y Seguimiento GPS de Unidades"
    ),
    layout="wide"
)


# -------------------------------
# PAGE STYLE
# -------------------------------

load_css()


# =================================
# Security gates
# =================================

require_login()
require_access("gps_tracking")

user = st.session_state.user


# =================================
# SUPABASE
# =================================

@st.cache_resource
def get_supabase():

    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_SERVICE_KEY"]
    )


supabase = get_supabase()


# =================================
# Defensive modal reset
# =================================

if st.session_state.get("_reset_gps_page", True):

    st.session_state.modal_gps_unit = None

    st.session_state["_reset_gps_page"] = False


# Initialize modal state

st.session_state.setdefault(
    "modal_gps_unit",
    None
)


# =================================
# Top navigation
# =================================

st.write("")

if st.button("⬅ Volver al Dashboard"):

    st.session_state["_reset_gps_page"] = True
    st.session_state.modal_gps_unit = None
    st.session_state.gps_history_report_generated = False

    st.switch_page(DASHBOARD_PAGE)


# =========================================
# TOP-LEVEL DATA TABS
# =========================================

tab_monarch, tab_wialon = st.tabs([
    "Monarch Data",
    "Wialon Data",
])

# =========================================
# MONARCH API
# =========================================
with tab_monarch:

    st.title("🛰️ Rastreador y Seguimiento GPS de Unidades - MONARCH")


    # =========================================
    # COMPANY FILTERS
    # =========================================

    st.session_state.setdefault(
        "gps_company_filter",
        "TODAS"
    )


    with st.container(key="company_filters"):

        c1, c2, c3, c4, c5, c6 = st.columns(6)

        with c1:

            if st.button(
                "PICUS",
                use_container_width=True,
                type="primary"
                if st.session_state.gps_company_filter == "PICUS"
                else "secondary"
            ):

                st.session_state.gps_company_filter = "PICUS"
                st.rerun()

        with c2:

            if st.button(
                "LINCOLN",
                use_container_width=True,
                type="primary"
                if st.session_state.gps_company_filter == "LINCOLN"
                else "secondary"
            ):

                st.session_state.gps_company_filter = "LINCOLN"
                st.rerun()

        with c3:

            if st.button(
                "SET FREIGHT",
                use_container_width=True,
                type="primary"
                if st.session_state.gps_company_filter == "SET FREIGHT"
                else "secondary"
            ):

                st.session_state.gps_company_filter = "SET FREIGHT"
                st.rerun()

        with c4:

            if st.button(
                "SET LOGIS",
                use_container_width=True,
                type="primary"
                if st.session_state.gps_company_filter == "SET LOGIS"
                else "secondary"
            ):

                st.session_state.gps_company_filter = "SET LOGIS"
                st.rerun()

        with c5:

            if st.button(
                "OTROS",
                use_container_width=True,
                type="primary"
                if st.session_state.gps_company_filter == "OTROS"
                else "secondary"
            ):

                st.session_state.gps_company_filter = "OTROS"
                st.rerun()

        with c6:

            if st.button(
                "TODAS",
                use_container_width=True,
                type="primary"
                if st.session_state.gps_company_filter == "TODAS"
                else "secondary"
            ):

                st.session_state.gps_company_filter = "TODAS"
                st.rerun()


    # =========================================
    # TABS
    # =========================================

    tab_dashboard, tab_seguimiento, tab_mapa, tab_historial = st.tabs([
        "📊 Dashboard",
        "🚛 Seguimiento",
        "🗺️ Mapa",
        "📈 Historial",
    ])


    # ==============================================================================================================
    # GPS INSIGHT AUTH
    # ==============================================================================================================

    # IMPORTANT:
    # GPS Insight authentication remains because the HISTORIAL tab
    # still uses GPS Insight's /vehicle/trips endpoint.
    #
    # It is NOT used to load the current vehicle data for the
    # Dashboard, Seguimiento or Mapa tabs.


    @st.cache_data(ttl=3600)
    def get_gps_token(
        username,
        app_token
    ):

        auth_url = (
            "https://api.gpsinsight.com/v2/userauth/login"
            f"?username={username}"
            f"&app_token={app_token}"
        )

        response = requests.post(
            auth_url,
            timeout=30
        )

        response.raise_for_status()

        auth_json = response.json()

        token = (
            auth_json
            .get("data", {})
            .get("token")
        )

        if not token:

            raise Exception(
                f"No token returned for {username}"
            )

        return token


    try:

        PICUS_TOKEN = get_gps_token(
            "aldodevpicus",
            "6a10839fe4fb6"
        )

        PGL_TOKEN = get_gps_token(
            "pglfslpsf",
            "6a289d87854a6"
        )

    except Exception as e:

        st.error(
            f"Error obteniendo token GPS Insight: {e}"
        )

        st.stop()


    # ==============================================================================================================
    # CURRENT VEHICLE DATA — SUPABASE
    # ==============================================================================================================

    # Dashboard / Seguimiento / Mapa now use gps_vehicle.
    #
    # GPS Insight /vehicle/location is intentionally NOT called here.
    #
    # Historial continues using GPS Insight below.


    try:

        vehicle_response = (
            supabase
            .table("gps_vehicle_history")
            .select("*")
            .execute()
        )

        vehicle_data = (
            vehicle_response.data
            or []
        )

        if vehicle_data:

            df = pd.DataFrame(
                vehicle_data
            )

        else:

            df = pd.DataFrame()

    except Exception as e:

        df = pd.DataFrame()

        st.error(
            f"Error cargando gps_vehicle desde Supabase: {e}"
        )


    # =========================================================
    # GLOBAL DATA PREP
    # =========================================================

    if not df.empty:

        df = df.copy()

        if "label" in df.columns:

            df["label"] = (
                df["label"]
                .astype(str)
            )

        if "inst_speed" in df.columns:

            df["inst_speed"] = pd.to_numeric(
                df["inst_speed"],
                errors="coerce"
            ).fillna(0)

        if "odometer" in df.columns:

            df["odometer"] = pd.to_numeric(
                df["odometer"],
                errors="coerce"
            ).fillna(0)

        if "voltage" in df.columns:

            df["voltage"] = pd.to_numeric(
                df["voltage"],
                errors="coerce"
            ).fillna(0)


    # =========================================================
    # GLOBAL COMPANY FILTER
    # =========================================================

    company_filter = st.session_state.get(
        "gps_company_filter",
        "TODAS"
    )

    filtered_df = df.copy()

    if not filtered_df.empty:
        company_labels = (
            filtered_df["label"]
            .fillna("")
            .astype(str)
            .str.upper()
        )

        picus_mask = (
            company_labels.str.contains("PI", na=False)
            | company_labels.str.startswith("P")
        )

        lincoln_mask = (
            company_labels.str.contains("LF", na=False)
            | company_labels.str.startswith("L")
        )

        set_freight_mask = company_labels.str.contains("SET", na=False)

        set_logis_mask = (
            company_labels.str.contains("SPL", na=False)
            | company_labels.str.contains("STL", na=False)
        )

        known_company_mask = (
            picus_mask | lincoln_mask | set_freight_mask | set_logis_mask
        )

        if company_filter == "PICUS":
            filtered_df = filtered_df[picus_mask].copy()
        elif company_filter == "LINCOLN":
            filtered_df = filtered_df[lincoln_mask].copy()
        elif company_filter == "SET FREIGHT":
            filtered_df = filtered_df[set_freight_mask].copy()
        elif company_filter == "SET LOGIS":
            filtered_df = filtered_df[set_logis_mask].copy()
        elif company_filter == "OTROS":
            filtered_df = filtered_df[~known_company_mask].copy()

    # Reset selectors when the top company changes.
    previous_company = st.session_state.get("_gps_previous_company_filter")

    if previous_company != company_filter:
        st.session_state.pop("trip_history_unit", None)
        st.session_state.pop("map_unit_filter", None)
        st.session_state.pop("gps_page", None)
        st.session_state.modal_gps_unit = None
        st.session_state["_gps_previous_company_filter"] = company_filter


    # =========================================================
    # KPI DASHBOARD
    # =========================================================

    with tab_dashboard:

        if not df.empty:

            st.header("📊 Dashboard Operativo GPS")

            # =========================================
            # WORKING COPY
            # =========================================

            dashboard_df = filtered_df.copy()

            # =========================================
            # COMPANY MASKS
            # =========================================

            picus_mask = (
                dashboard_df["label"]
                .str.upper()
                .str.contains("PI", na=False)
            ) | (
                dashboard_df["label"]
                .str.upper()
                .str.match(r"^P\d+", na=False)
            )

            lincoln_mask = (
                dashboard_df["label"]
                .str.upper()
                .str.contains("LF", na=False)
            ) | (
                dashboard_df["label"]
                .str.upper()
                .str.match(r"^L\d+", na=False)
            )

            set_freight_mask = (
                dashboard_df["label"]
                .str.upper()
                .str.contains("SET", na=False)
            )

            set_logis_mask = (
                dashboard_df["label"]
                .str.upper()
                .str.contains("SPL", na=False)
            ) | (
                dashboard_df["label"]
                .str.upper()
                .str.contains("STL", na=False)
            )

            otros_mask = ~(
                picus_mask
                | lincoln_mask
                | set_freight_mask
                | set_logis_mask
            )

            company_filter = st.session_state.get(
                "gps_company_filter",
                "TODAS"
            )

            # =========================================
            # FILTER DATAFRAME
            # =========================================

            if company_filter == "PICUS":

                dashboard_df = dashboard_df[
                    picus_mask
                ].copy()

            elif company_filter == "LINCOLN":

                dashboard_df = dashboard_df[
                    lincoln_mask
                ].copy()

            elif company_filter == "SET FREIGHT":

                dashboard_df = dashboard_df[
                    set_freight_mask
                ].copy()

            elif company_filter == "SET LOGIS":

                dashboard_df = dashboard_df[
                    set_logis_mask
                ].copy()

            elif company_filter == "OTROS":

                dashboard_df = dashboard_df[
                    otros_mask
                ].copy()

            # =========================================
            # SPEED NORMALIZATION
            # =========================================

            KM_TO_MILES = 0.621371
            MILES_TO_KM = 1.60934

            dashboard_df["speed_calc"] = pd.to_numeric(
                dashboard_df["inst_speed"],
                errors="coerce"
            ).fillna(0.0).astype(float)

            if company_filter == "TODAS":

                picus_rows = (
                    dashboard_df["label"]
                    .str.upper()
                    .str.contains("PI", na=False)
                ) | (
                    dashboard_df["label"]
                    .str.upper()
                    .str.match(r"^P\d+", na=False)
                )

                lincoln_rows = (
                    dashboard_df["label"]
                    .str.upper()
                    .str.contains("LF", na=False)
                ) | (
                    dashboard_df["label"]
                    .str.upper()
                    .str.match(r"^L\d+", na=False)
                )

                set_freight_rows = (
                    dashboard_df["label"]
                    .str.upper()
                    .str.contains(
                        "SET",
                        na=False
                    )
                )

                set_logis_rows = (
                    dashboard_df["label"]
                    .str.upper()
                    .str.contains(
                        "SPL",
                        na=False
                    )
                ) | (
                    dashboard_df["label"]
                    .str.upper()
                    .str.contains(
                        "STL",
                        na=False
                    )
                )

                otros_rows = ~(
                    picus_rows
                    | lincoln_rows
                    | set_freight_rows
                    | set_logis_rows
                )

                kmh_rows = (
                    picus_rows
                    | otros_rows
                )

                dashboard_df["speed_calc"] = (
                    dashboard_df["speed_calc"]
                    * (
                        1
                        + kmh_rows.astype(float)
                        * (KM_TO_MILES - 1)
                    )
                )

            elif company_filter in [
                "PICUS",
                "OTROS"
            ]:

                dashboard_df["speed_calc"] = pd.to_numeric(
                    dashboard_df["inst_speed"],
                    errors="coerce"
                ).fillna(0.0).astype(float)

            else:

                dashboard_df["speed_calc"] = pd.to_numeric(
                    dashboard_df["inst_speed"],
                    errors="coerce"
                ).fillna(0.0).astype(float)

            # =========================================
            # UNIT CLASSIFICATION
            # =========================================

            cajas_df = dashboard_df[
                dashboard_df["label"]
                .str.lower()
                .str.contains(
                    "caja",
                    na=False
                )
            ].copy()

            trucks_df = dashboard_df[
                ~dashboard_df["label"]
                .str.lower()
                .str.contains(
                    "caja",
                    na=False
                )
            ].copy()

            # =========================================
            # FORMAT SPEED
            # =========================================

            def format_speed(speed):

                speed = round(
                    float(speed),
                    1
                )

                if company_filter == "TODAS":

                    kmh = round(
                        speed * MILES_TO_KM,
                        1
                    )

                    return (
                        f"{speed} mph "
                        f"({kmh} km/h)"
                    )

                elif company_filter in [
                    "PICUS",
                    "OTROS"
                ]:

                    return f"{speed} km/h"

                else:

                    return f"{speed} mph"

            # =========================================
            # KPI FUNCTION
            # =========================================

            def render_kpis(
                dataframe,
                title
            ):

                total_units = len(
                    dataframe
                )

                moving_units = (
                    dataframe["speed_calc"] > 0
                ).sum()

                stopped_units = (
                    dataframe["speed_calc"] <= 0
                ).sum()

                ignition_on = (
                    dataframe["ignition"]
                    .astype(str)
                    .str.lower()
                    .eq("on")
                    .sum()
                    if "ignition" in dataframe.columns
                    else 0
                )

                ignition_off = (
                    dataframe["ignition"]
                    .astype(str)
                    .str.lower()
                    .eq("off")
                    .sum()
                    if "ignition" in dataframe.columns
                    else 0
                )

                avg_speed = (
                    dataframe["speed_calc"]
                    .fillna(0)
                    .mean()
                    if not dataframe.empty
                    else 0
                )

                max_speed = (
                    dataframe["speed_calc"]
                    .fillna(0)
                    .max()
                    if not dataframe.empty
                    else 0
                )

                low_voltage = (
                    dataframe["voltage"] < 11
                ).sum() if "voltage" in dataframe.columns else 0

                panic_active = 0

                if "inputs" in dataframe.columns:

                    for val in dataframe["inputs"]:

                        if isinstance(
                            val,
                            dict
                        ):

                            if (
                                str(
                                    val.get(
                                        "Panic Button",
                                        "off"
                                    )
                                ).lower()
                                == "on"
                            ):

                                panic_active += 1

                        elif isinstance(
                            val,
                            str
                        ):

                            try:

                                parsed_inputs = json.loads(
                                    val
                                )

                                if isinstance(
                                    parsed_inputs,
                                    dict
                                ):

                                    if (
                                        str(
                                            parsed_inputs.get(
                                                "Panic Button",
                                                "off"
                                            )
                                        ).lower()
                                        == "on"
                                    ):

                                        panic_active += 1

                            except Exception:

                                pass

                st.subheader(title)

                c1, c2, c3, c4, c5, c6 = st.columns(6)

                c1.metric(
                    "🚛 Total",
                    total_units
                )

                c2.metric(
                    "🟢 Movimiento",
                    moving_units
                )

                c3.metric(
                    "🔴 Detenidas",
                    stopped_units
                )

                c4.metric(
                    "⚡ Ignición ON",
                    ignition_on
                )

                c5.metric(
                    "⛔ Ignición OFF",
                    ignition_off
                )

                c6.metric(
                    "🏎️ Vel. Promedio",
                    format_speed(avg_speed)
                )

                c7, c8, c9 = st.columns(3)

                c7.metric(
                    "🔥 Velocidad Máxima",
                    format_speed(max_speed)
                )

                c8.metric(
                    "🔋 Voltaje Bajo",
                    low_voltage
                )

                c9.metric(
                    "🚨 Pánico",
                    panic_active
                )

                st.divider()

            # =========================================
            # RENDER
            # =========================================

            render_kpis(
                trucks_df,
                "🚛 KPIs Tractocamiones"
            )

            render_kpis(
                cajas_df,
                "📦 KPIs Cajas / Remolques"
            )

            render_kpis(
                dashboard_df,
                "🌐 KPIs Generales"
            )

        else:

            st.warning(
                "No hay información de unidades disponible."
            )


    # =========================================================
    # INDIVIDUAL UNIT TRACKING
    # =========================================================

    with tab_seguimiento:

        def get_speed_display(row):

            speed = float(
                pd.to_numeric(
                    row.get(
                        "inst_speed",
                        0
                    ),
                    errors="coerce"
                ) or 0
            )

            label = str(
                row.get(
                    "label",
                    ""
                )
            ).upper()

            if (
                "PI" in label
                or label.startswith("P")
            ):

                return f"{round(speed, 1)} km/h"

            if (
                "LF" in label
                or label.startswith("L")
            ):

                return f"{round(speed, 1)} mph"

            if (
                "SPL" in label
                or "STL" in label
            ):

                return f"{round(speed, 1)} mph"

            if "SET" in label:

                return f"{round(speed, 1)} mph"

            return f"{round(speed, 1)} km/h"

        if not df.empty:

            st.header(
                "🚛 Seguimiento Individual de Unidades"
            )

            # =====================================================
            # FILTERS
            # =====================================================

            f1, f2, f3 = st.columns(3)

            # =============================================
            # UNIT FILTER
            # =============================================

            with f1:

                unidades = sorted(
                    filtered_df["label"]
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

            df_units = filtered_df.copy()

            if unidad_select != "Todas":

                df_units = df_units[
                    df_units["label"]
                    .astype(str)
                    == unidad_select
                ]

            if estado_select != "Todos":

                df_units = df_units[
                    df_units["ignition"]
                    .astype(str)
                    .str.lower()
                    == estado_select
                ]

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
                estado_select,
                tipo_select
            )

            previous_filter_state = st.session_state.get(
                "_gps_filter_state"
            )

            if previous_filter_state != current_filter_state:

                st.session_state.modal_gps_unit = None
                st.session_state.gps_page = 1

            st.session_state[
                "_gps_filter_state"
            ] = current_filter_state

            # =====================================================
            # PAGINATION
            # =====================================================

            ITEMS_PER_PAGE = 10

            total_items = len(
                df_units
            )

            total_pages = max(
                (total_items - 1)
                // ITEMS_PER_PAGE
                + 1,
                1
            )

            st.session_state.setdefault(
                "gps_page",
                1
            )

            if (
                st.session_state.gps_page
                > total_pages
            ):

                st.session_state.gps_page = total_pages

            if (
                st.session_state.gps_page
                < 1
            ):

                st.session_state.gps_page = 1

            start_idx = (
                st.session_state.gps_page - 1
            ) * ITEMS_PER_PAGE

            end_idx = (
                start_idx
                + ITEMS_PER_PAGE
            )

            df_units_page = df_units.iloc[
                start_idx:end_idx
            ]

            # =====================================================
            # POSTITS
            # =====================================================

            total = len(
                df_units_page
            )

            if total == 0:

                st.warning(
                    "No se encontraron unidades."
                )

            else:

                idx = 0

                rows_needed = (
                    (total - 1) // 5
                    + 1
                )

                for _ in range(rows_needed):

                    cols = st.columns(5)

                    for col in cols:

                        if idx >= total:
                            break

                        r = df_units_page.iloc[idx]

                        unidad = str(
                            r.get(
                                "label",
                                "-"
                            )
                        )

                        direccion = str(
                            r.get(
                                "address",
                                "-"
                            )
                        )

                        velocidad = get_speed_display(
                            r
                        )

                        ignicion = str(
                            r.get(
                                "ignition",
                                "-"
                            )
                        ).upper()

                        odometro = r.get(
                            "odometer",
                            "-"
                        )

                        speed_label = str(
                            r.get(
                                "speed_label",
                                "-"
                            )
                        )

                        ultima_conexion = str(
                            r.get(
                                "fix_time",
                                "-"
                            )
                        )

                        voltaje = str(
                            r.get(
                                "voltage",
                                "-"
                            )
                        )

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
                                        <strong>Velocidad:</strong>
                                        {velocidad}
                                    </div>

                                    <div style="
                                        font-size:0.8rem;
                                    ">
                                        <strong>Odómetro:</strong>
                                        {odometro}
                                    </div>

                                    <div style="
                                        font-size:0.8rem;
                                    ">
                                        <strong>Voltaje:</strong>
                                        {voltaje}V
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

                            components.html(
                                html,
                                height=310
                            )

                            # =====================================
                            # BUTTONS
                            # =====================================

                            b1, b2 = st.columns(2)

                            with b1:

                                if st.button(
                                    "👁 Ver",
                                    key=(
                                        f"gps_unit_"
                                        f"{unidad}_"
                                        f"{idx}"
                                    ),
                                    use_container_width=True
                                ):

                                    st.session_state.modal_gps_unit = (
                                        r.to_dict()
                                    )

                                    st.rerun()

                            with b2:

                                excel_df = pd.DataFrame(
                                    [r]
                                )

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
                                    key=(
                                        f"save_excel_"
                                        f"{unidad}_"
                                        f"{idx}"
                                    ),
                                    use_container_width=True
                                )

                        idx += 1

            # =====================================================
            # PAGINATION CONTROLS
            # =====================================================

            st.divider()

            p1, p2, p3 = st.columns(
                [1, 2, 1]
            )

            with p1:

                if st.button(
                    "⬅ Anterior",
                    disabled=(
                        st.session_state.gps_page <= 1
                    ),
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
                        Página {st.session_state.gps_page}
                        de {total_pages}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            with p3:

                if st.button(
                    "Siguiente ➡",
                    disabled=(
                        st.session_state.gps_page
                        >= total_pages
                    ),
                    use_container_width=True
                ):

                    st.session_state.gps_page += 1
                    st.session_state.modal_gps_unit = None
                    st.rerun()

            # =====================================================
            # MODAL
            # =====================================================

            if st.session_state.get(
                "modal_gps_unit"
            ):

                modal_label = str(
                    st.session_state.modal_gps_unit.get(
                        "label",
                        ""
                    )
                )

                valid_labels = set(
                    df_units["label"]
                    .astype(str)
                    .tolist()
                )

                if modal_label not in valid_labels:

                    st.session_state.modal_gps_unit = None

            if st.session_state.get(
                "modal_gps_unit"
            ):

                gps_row = (
                    st.session_state.modal_gps_unit
                )

                unidad_modal = gps_row.get(
                    "label",
                    "-"
                )

                @st.dialog(
                    f"Unidad {unidad_modal}"
                )
                def modal_gps():

                    st.subheader(
                        "📍 Ubicación"
                    )

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
                            get_speed_display(
                                gps_row
                            )
                        )

                    with c2:

                        st.metric(
                            "Ignición",
                            str(
                                gps_row.get(
                                    "ignition",
                                    "-"
                                )
                            ).upper()
                        )

                    with c3:

                        st.metric(
                            "Voltaje",
                            f"{gps_row.get('voltage', '-')}"
                        )

                    st.divider()

                    st.subheader(
                        "📡 Información GPS"
                    )

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

                    st.subheader(
                        "👤 Operador"
                    )

                    st.markdown(
                        f"""
                        - **Driver ID:** {gps_row.get("driver_id", "-")}
                        - **Estado Driver:** {gps_row.get("driver_status", "-")}
                        - **Último cambio:** {gps_row.get("driver_date", "-")}
                        """
                    )

                    st.divider()

                    st.subheader(
                        "🔌 Inputs"
                    )

                    inputs_value = gps_row.get(
                        "inputs",
                        {}
                    )

                    if isinstance(
                        inputs_value,
                        str
                    ):

                        try:

                            inputs_value = json.loads(
                                inputs_value
                            )

                        except Exception:

                            pass

                    st.json(
                        inputs_value
                    )

                    if st.button(
                        "Cerrar",
                        key="close_gps_modal"
                    ):

                        st.session_state.modal_gps_unit = None
                        st.rerun()

                modal_gps()

            st.divider()

            st.subheader(
                "📊 Estado de Ignición de Unidades"
            )

            # =====================================================
            # CHARTS
            # =====================================================

            col1, col2 = st.columns(2)

            with col1:

                st.subheader(
                    "Estado de Ignición"
                )

                ignition_counts = (
                    df["ignition"]
                    .astype(str)
                    .value_counts()
                )

                st.bar_chart(
                    ignition_counts
                )

            with col2:

                st.subheader(
                    "Distribución de Velocidades"
                )

                speed_df = df[
                    df["inst_speed"] > 0
                ]

                if not speed_df.empty:

                    st.bar_chart(
                        speed_df["inst_speed"]
                    )

                else:

                    st.info(
                        "No se detectaron unidades en movimiento."
                    )

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

                voltage_df = df[
                    df["voltage"] < 11
                ][[
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

                display_df = df.copy()

                display_df.drop(
                    columns=[
                        "session_token",
                        "gps_account",
                    ],
                    inplace=True,
                    errors="ignore"
                )

                for col in display_df.columns:

                    display_df[col] = display_df[col].apply(
                        lambda x:
                        json.dumps(
                            x,
                            ensure_ascii=False
                        )
                        if isinstance(
                            x,
                            (dict, list)
                        )
                        else x
                    )

                st.dataframe(
                    display_df,
                    use_container_width=True,
                    height=700
                )

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

        else:

            st.warning(
                "No hay información de unidades disponible."
            )


    # =====================================================
    # LIVE GPS MAP
    # =====================================================

    with tab_mapa:

        # =====================================================
        # LANDMARKS
        # =====================================================

        st.header(
            "📍 Landmarks GPS Insight"
        )

        try:

            all_landmarks = []

            PAGE_SIZE = 1000
            offset = 0

            while True:

                landmark_response = (
                    supabase
                    .table("gps_landmarks")
                    .select("*")
                    .range(
                        offset,
                        offset + PAGE_SIZE - 1
                    )
                    .execute()
                )

                page_data = (
                    landmark_response.data
                    or []
                )

                if not page_data:
                    break

                all_landmarks.extend(
                    page_data
                )

                if len(page_data) < PAGE_SIZE:
                    break

                offset += PAGE_SIZE

            if all_landmarks:

                landmark_df = pd.DataFrame(
                    all_landmarks
                )

                k1, k2, k3, k4 = st.columns(4)

                with k1:

                    st.metric(
                        "📍 Total Landmarks",
                        len(landmark_df)
                    )

                with k2:

                    st.metric(
                        "PICUS",
                        (
                            landmark_df["gps_account"]
                            == "PICUS"
                        ).sum()
                    )

                with k3:

                    st.metric(
                        "PGL",
                        (
                            landmark_df["gps_account"]
                            == "PGL"
                        ).sum()
                    )

                with k4:

                    st.metric(
                        "⭕ Circulares",
                        (
                            landmark_df["polygon"] == 0
                        ).sum()
                        if "polygon" in landmark_df.columns
                        else 0
                    )

                st.divider()

            else:

                landmark_df = pd.DataFrame()

                st.warning(
                    "No se encontraron landmarks en Supabase."
                )

        except Exception as e:

            landmark_df = pd.DataFrame()

            st.error(
                f"Error cargando landmarks desde Supabase: {e}"
            )

        # =============================================
        # LANDMARK POLYGON PREPARATION
        # =============================================

        landmark_map_df = pd.DataFrame()

        if not landmark_df.empty:

            landmark_map_df = landmark_df.copy()

            def parse_landmark_coordinates(
                value
            ):

                if not isinstance(
                    value,
                    str
                ):

                    return []

                points = []

                coordinate_pairs = (
                    value
                    .strip()
                    .split()
                )

                for coordinate in coordinate_pairs:

                    try:

                        parts = coordinate.split(",")

                        longitude = float(
                            parts[0]
                        )

                        latitude = float(
                            parts[1]
                        )

                        points.append(
                            [
                                longitude,
                                latitude
                            ]
                        )

                    except (
                        ValueError,
                        IndexError
                    ):

                        continue

                return points

            if "coordinates" in landmark_map_df.columns:

                landmark_map_df[
                    "polygon_coordinates"
                ] = (
                    landmark_map_df[
                        "coordinates"
                    ]
                    .apply(
                        parse_landmark_coordinates
                    )
                )

                landmark_map_df = (
                    landmark_map_df[
                        landmark_map_df[
                            "polygon_coordinates"
                        ].apply(
                            lambda x:
                            len(x) >= 3
                        )
                    ]
                    .copy()
                )

                def get_landmark_center(
                    points
                ):

                    if not points:

                        return [
                            0,
                            0
                        ]

                    longitude = sum(
                        point[0]
                        for point in points
                    ) / len(points)

                    latitude = sum(
                        point[1]
                        for point in points
                    ) / len(points)

                    return [
                        longitude,
                        latitude
                    ]

                landmark_map_df[
                    "label_position"
                ] = (
                    landmark_map_df[
                        "polygon_coordinates"
                    ]
                    .apply(
                        get_landmark_center
                    )
                )

        st.subheader(
            "🗺️ Mapa GPS de Unidades"
        )

        if df.empty:

            st.warning(
                "No hay unidades disponibles para mostrar en el mapa."
            )

        else:

            map_df = filtered_df.copy()

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

            # =============================================
            # SPEED DISPLAY
            # =============================================

            def get_map_speed(
                row
            ):

                speed = float(
                    row.get(
                        "inst_speed",
                        0
                    )
                )

                label = str(
                    row.get(
                        "label",
                        ""
                    )
                ).upper()

                picus = (
                    "PI" in label
                    or label.startswith("P")
                )

                lincoln = (
                    "LF" in label
                    or label.startswith("L")
                )

                set_freight = (
                    "SET" in label
                )

                set_logis = (
                    "SPL" in label
                    or "STL" in label
                )

                otros = not (
                    picus
                    or lincoln
                    or set_freight
                    or set_logis
                )

                if picus or otros:

                    return (
                        f"{round(speed, 1)} km/h"
                    )

                return (
                    f"{round(speed, 1)} mph"
                )

            map_df["speed_display"] = (
                map_df.apply(
                    get_map_speed,
                    axis=1
                )
            )

            map_df = map_df.dropna(
                subset=[
                    "latitude",
                    "longitude"
                ]
            )

            # =============================================
            # STOPPED TIME PARSER
            # =============================================

            def extract_stopped_minutes(
                speed_label
            ):

                if not isinstance(
                    speed_label,
                    str
                ):

                    return 0

                speed_label = (
                    speed_label.lower()
                )

                total_minutes = 0

                d = re.search(
                    r"(\d+)\s*day",
                    speed_label
                )

                if d:

                    total_minutes += (
                        int(d.group(1))
                        * 1440
                    )

                h = re.search(
                    r"(\d+)\s*hr",
                    speed_label
                )

                if h:

                    total_minutes += (
                        int(h.group(1))
                        * 60
                    )

                m = re.search(
                    r"(\d+)\s*min",
                    speed_label
                )

                if m:

                    total_minutes += (
                        int(m.group(1))
                    )

                return total_minutes

            # =============================================
            # COLOR STATES
            # =============================================

            def get_color(
                row
            ):

                speed = float(
                    row.get(
                        "inst_speed",
                        0
                    )
                )

                speed_label = str(
                    row.get(
                        "speed_label",
                        ""
                    )
                )

                if speed > 0:

                    return [
                        0,
                        255,
                        0
                    ]

                stopped_minutes = (
                    extract_stopped_minutes(
                        speed_label
                    )
                )

                if stopped_minutes < 60:

                    return [
                        255,
                        165,
                        0
                    ]

                if stopped_minutes < 360:

                    return [
                        255,
                        80,
                        0
                    ]

                if stopped_minutes < 1440:

                    return [
                        255,
                        0,
                        0
                    ]

                if stopped_minutes < 10080:

                    return [
                        139,
                        0,
                        0
                    ]

                return [
                    0,
                    0,
                    0
                ]

            map_df["color"] = (
                map_df.apply(
                    get_color,
                    axis=1
                )
            )

            # =============================================
            # MAP FILTERS
            # =============================================

            map_source_df = map_df.copy()

            filter_col1, filter_col2 = st.columns(2)

            with filter_col1:

                map_status_filter = st.selectbox(
                    "Estado en mapa",
                    [
                        "Todas",
                        "🟢 En Movimiento",
                        "🟠 Detenido < 1 Hora",
                        "🔴 Detenido 1-6 Horas",
                        "🟥 Detenido 6-24 Horas",
                        "⚫ Detenido +1 Día"
                    ],
                    key="map_status_filter"
                )

            map_df = map_source_df.copy()

            # =============================================
            # APPLY STATUS FILTER
            # =============================================

            if map_status_filter == "🟢 En Movimiento":

                map_df = map_df[
                    map_df["inst_speed"] > 0
                ]

            elif map_status_filter == "🟠 Detenido < 1 Hora":

                map_df = map_df[
                    (
                        map_df["inst_speed"] <= 0
                    )
                    &
                    (
                        map_df["speed_label"]
                        .apply(
                            extract_stopped_minutes
                        )
                        < 60
                    )
                ]

            elif map_status_filter == "🔴 Detenido 1-6 Horas":

                map_df = map_df[
                    (
                        map_df["inst_speed"] <= 0
                    )
                    &
                    (
                        map_df["speed_label"]
                        .apply(
                            extract_stopped_minutes
                        )
                        >= 60
                    )
                    &
                    (
                        map_df["speed_label"]
                        .apply(
                            extract_stopped_minutes
                        )
                        < 360
                    )
                ]

            elif map_status_filter == "🟥 Detenido 6-24 Horas":

                map_df = map_df[
                    (
                        map_df["inst_speed"] <= 0
                    )
                    &
                    (
                        map_df["speed_label"]
                        .apply(
                            extract_stopped_minutes
                        )
                        >= 360
                    )
                    &
                    (
                        map_df["speed_label"]
                        .apply(
                            extract_stopped_minutes
                        )
                        < 1440
                    )
                ]

            elif map_status_filter == "⚫ Detenido +1 Día":

                map_df = map_df[
                    (
                        map_df["inst_speed"] <= 0
                    )
                    &
                    (
                        map_df["speed_label"]
                        .apply(
                            extract_stopped_minutes
                        )
                        >= 1440
                    )
                ]

            # =============================================
            # UNIT FILTER
            # =============================================

            with filter_col2:

                map_company_df = filtered_df.copy()

                map_unit_options = sorted(
                    map_company_df["label"]
                    .dropna()
                    .astype(str)
                    .unique()
                    .tolist()
                )

                map_unit_filter = st.selectbox(
                    "Unidad en mapa",
                    ["Todas"] + map_unit_options,
                    key="map_unit_filter"
                )

            if map_unit_filter != "Todas":

                map_df = map_df[
                    map_df["label"]
                    .astype(str)
                    .eq(
                        map_unit_filter
                    )
                ]

            # =============================================
            # DISPLAY MAP
            # =============================================

            if not map_df.empty:

                landmark_layers = []

                if not landmark_map_df.empty:

                    landmark_map_df[
                        "tooltip_title"
                    ] = (
                        "📍 "
                        + landmark_map_df[
                            "label"
                        ].astype(str)
                    )

                    landmark_map_df[
                        "tooltip_info"
                    ] = (
                        "Cuenta: "
                        + landmark_map_df[
                            "gps_account"
                        ].astype(str)
                    )

                    landmark_polygon_layer = pdk.Layer(
                        "PolygonLayer",
                        data=landmark_map_df,
                        get_polygon="polygon_coordinates",
                        get_fill_color=[
                            21,
                            31,
                            109,
                            55
                        ],
                        get_line_color=[
                            21,
                            31,
                            109,
                            230
                        ],
                        line_width_min_pixels=5,
                        line_width_max_pixels=8,
                        filled=True,
                        stroked=True,
                        pickable=True,
                        auto_highlight=True,
                    )

                    landmark_layers = [
                        landmark_polygon_layer
                    ]

                # =============================================
                # VEHICLE TOOLTIP FIELDS
                # =============================================

                map_df["tooltip_title"] = (
                    "🚛 "
                    + map_df["label"].astype(str)
                )

                map_df["tooltip_info"] = (
                    "Latitud: "
                    + map_df["latitude"].astype(str)
                    + " | Longitud: "
                    + map_df["longitude"].astype(str)
                    + " | Velocidad: "
                    + map_df["speed_display"].astype(str)
                    + " | Ignición: "
                    + map_df["ignition"].astype(str)
                    + " | Tiempo detenido: "
                    + map_df["speed_label"].astype(str)
                    + " | Dirección: "
                    + map_df["address"].astype(str)
                )

                # =============================================
                # PYDECK VEHICLE LAYER
                # =============================================

                layer = pdk.Layer(
                    "ScatterplotLayer",
                    data=map_df,
                    get_position="[longitude, latitude]",
                    get_fill_color="color",
                    radius_units="pixels",
                    get_radius=12,
                    radius_min_pixels=6,
                    radius_max_pixels=30,
                    pickable=True,
                    auto_highlight=True,
                    stroked=True,
                    filled=True,
                    line_width_min_pixels=2,
                    get_line_color=[
                        255,
                        255,
                        255
                    ]
                )

                # =============================================
                # TOOLTIP
                # =============================================

                tooltip = {
                    "html": """
                        <b>{tooltip_title}</b><br/>
                        {tooltip_info}
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
                        layers=(
                            landmark_layers
                            + [layer]
                        ),
                        initial_view_state=view_state,
                        tooltip=tooltip,
                        map_style="light"
                    ),
                    use_container_width=True
                )

                # =============================================
                # GPS COORDINATE REPORT
                # =============================================

                with st.expander(
                    "📍 Coordenadas de Unidades",
                    expanded=False
                ):

                    coords_df = map_df[[
                        "label",
                        "latitude",
                        "longitude",
                        "address",
                        "ignition",
                        "speed_display",
                        "speed_label"
                    ]].copy()

                    coords_df.rename(
                        columns={
                            "label": "Unidad",
                            "latitude": "Latitud",
                            "longitude": "Longitud",
                            "address": "Dirección",
                            "ignition": "Ignición",
                            "speed_display": "Velocidad",
                            "speed_label": "Tiempo detenido"
                        },
                        inplace=True
                    )

                    st.dataframe(
                        coords_df,
                        use_container_width=True,
                        height=300
                    )

                    coordinates_buffer = io.BytesIO()

                    with pd.ExcelWriter(
                        coordinates_buffer,
                        engine="openpyxl"
                    ) as writer:

                        coords_df.to_excel(
                            writer,
                            index=False,
                            sheet_name="Coordenadas"
                        )

                    coordinates_buffer.seek(0)

                    st.download_button(
                        label="💾 Descargar Coordenadas de Unidades",
                        data=coordinates_buffer,
                        file_name="Coordenadas_Unidades_GPS.xlsx",
                        mime=(
                            "application/"
                            "vnd.openxmlformats-officedocument."
                            "spreadsheetml.sheet"
                        ),
                        use_container_width=True
                    )

            else:

                st.warning(
                    "No se encontraron unidades que coincidan "
                    "con los filtros seleccionados."
                )

    # =====================================================
    # UNIT TRIP HISTORY
    # =====================================================

    with tab_historial:

        st.header(
            "📈 Historial de Viajes de Unidad"
        )

        try:

            if df.empty:

                st.warning(
                    "No hay unidades cargadas."
                )

            else:

                # =========================================
                # COMPANY FILTER
                # =========================================

                company_filter = st.session_state.get(
                    "gps_company_filter",
                    "TODAS"
                )

                # =========================================
                # UNIT SELECTOR
                # =========================================

                unit_options = sorted(
                    filtered_df["label"]
                    .dropna()
                    .astype(str)
                    .unique()
                    .tolist()
                )

                selected_unit = st.selectbox(
                    "Unidad",
                    unit_options,
                    key="trip_history_unit"
                )

                # =====================================
                # SPEED / DISTANCE UNITS
                # =====================================

                selected_label = (
                    str(selected_unit)
                    .upper()
                )

                is_kmh_unit = (
                    "PI" in selected_label
                    or selected_label.startswith("P")
                )

                is_lincoln = (
                    "LF" in selected_label
                    or selected_label.startswith("L")
                )

                is_set_freight = (
                    "SET" in selected_label
                )

                is_set_logis = (
                    "SPL" in selected_label
                    or "STL" in selected_label
                )

                is_otros = not (
                    is_kmh_unit
                    or is_lincoln
                    or is_set_freight
                    or is_set_logis
                )

                distance_unit = (
                    "km"
                    if (
                        is_kmh_unit
                        or is_otros
                    )
                    else "mi"
                )

                speed_unit = (
                    "km/h"
                    if (
                        is_kmh_unit
                        or is_otros
                    )
                    else "mph"
                )

                # =========================================
                # DATE FILTERS
                # =========================================

                c1, c2 = st.columns(2)

                with c1:

                    start_date = st.date_input(
                        "Fecha Inicial",
                        value=pd.to_datetime(
                            "2026-05-01"
                        ),
                        key="trip_start"
                    )

                with c2:

                    end_date = st.date_input(
                        "Fecha Final",
                        value=datetime.today(),
                        key="trip_end"
                    )

                start_str = start_date.strftime("%m/%d/%Y")
                end_str = end_date.strftime("%m/%d/%Y") + " 23:59:59"

                # =========================================
                # REQUEST
                # =========================================

                # IMPORTANT:
                # The vehicle list comes from Supabase,
                # but the trip history continues to come
                # directly from GPS Insight.

                token = (
                    PICUS_TOKEN
                    if (
                        "PI" in selected_label
                        or selected_label.startswith("P")
                    )
                    else PGL_TOKEN
                )

                url = (
                    "https://api.gpsinsight.com/v2/"
                    "vehicle/trips"
                    f"?session_token={token}"
                    f"&vehicle={selected_unit}"
                    f"&start={start_str}"
                    f"&end={end_str}"
                )

                response = requests.get(
                    url,
                    timeout=60
                )

                response.raise_for_status()

                result = response.json()

                data = result.get(
                    "data",
                    []
                )

                if not data:

                    st.warning(
                        "No se encontraron viajes."
                    )

                else:

                    activity_df = pd.DataFrame(
                        data
                    )

                    # =====================================
                    # ONLY REAL TRIPS
                    # =====================================

                    trip_df = activity_df.copy()

                    #trip_df = activity_df[
                    #    activity_df["trip_type"] == "T"
                    #].copy()

                    if trip_df.empty:

                        st.warning(
                            "No se encontraron viajes tipo T."
                        )

                    else:

                        # =====================================
                        # NUMERIC CLEANUP
                        # =====================================

                        numeric_cols = [
                            "trip_distance",
                            "max_speed",
                            "avg_speed",
                            "trip_duration"
                        ]

                        for col in numeric_cols:

                            if col in trip_df.columns:

                                trip_df[col] = pd.to_numeric(
                                    trip_df[col],
                                    errors="coerce"
                                ).fillna(0)

                        # =====================================
                        # PICUS UNIT CONVERSION
                        # =====================================

                        if is_kmh_unit:

                            MILES_TO_KM = 1.609344

                            for col in [
                                "trip_distance",
                                "max_speed",
                                "avg_speed",
                                "fastest_distance"
                            ]:

                                if col in trip_df.columns:

                                    trip_df[col] = pd.to_numeric(
                                        trip_df[col],
                                        errors="coerce"
                                    ).fillna(0)

                                    trip_df[col] = (
                                        trip_df[col] * MILES_TO_KM
                                    )


                        # =====================================
                        # VIN
                        # =====================================

                        vin = trip_df.iloc[0].get(
                            "vin",
                            "-"
                        )

                        st.info(
                            f"VIN: {vin}"
                        )

                        # =====================================
                        # KPIs
                        # =====================================

                        total_km = round(
                            trip_df[
                                "trip_distance"
                            ].sum(),
                            1
                        )

                        total_trips = len(
                            trip_df
                        )

                        max_speed = round(
                            trip_df[
                                "max_speed"
                            ].max(),
                            1
                        )

                        avg_speed = round(
                            trip_df[
                                "avg_speed"
                            ].mean(),
                            1
                        )

                        k1, k2, k3, k4 = st.columns(4)

                        k1.metric(
                            f"🛣️ {distance_unit.upper()} Recorridos",
                            f"{total_km:,}"
                        )

                        k2.metric(
                            "🚛 Viajes",
                            total_trips
                        )

                        k3.metric(
                            "🔥 Velocidad Máxima",
                            f"{max_speed} {speed_unit}"
                        )

                        k4.metric(
                            "🏎️ Velocidad Promedio",
                            f"{avg_speed} {speed_unit}"
                        )

                        st.divider()

                        # =====================================
                        # DISPLAY TABLE
                        # =====================================

                        trip_display = trip_df[[
                            "trip_start",
                            "trip_end",
                            "trip_distance",
                            "trip_duration",
                            "max_speed",
                            "avg_speed"
                        ]].copy()

                        trip_display.rename(
                            columns={
                                "trip_start": "Inicio",
                                "trip_end": "Fin",
                                "trip_distance": distance_unit.upper(),
                                "trip_duration": "Duración (Seg)",
                                "max_speed": "Vel Máxima",
                                "avg_speed": "Vel Promedio"
                            },
                            inplace=True
                        )

                        trip_display["Duración"] = (
                            trip_display[
                                "Duración (Seg)"
                            ]
                            .apply(
                                lambda x:
                                f"{int(x // 3600)}h "
                                f"{int((x % 3600) // 60)}m"
                            )
                        )

                        trip_display = trip_display[[
                            "Inicio",
                            "Fin",
                            distance_unit.upper(),
                            "Duración",
                            "Vel Máxima",
                            "Vel Promedio"
                        ]]

                        trip_display[
                            "Vel Máxima"
                        ] = (
                            trip_display[
                                "Vel Máxima"
                            ]
                            .round(1)
                            .astype(str)
                            + f" {speed_unit}"
                        )

                        trip_display[
                            "Vel Promedio"
                        ] = (
                            trip_display[
                                "Vel Promedio"
                            ]
                            .round(1)
                            .astype(str)
                            + f" {speed_unit}"
                        )

                        st.subheader(
                            "🚛 Viajes Detectados"
                        )

                        st.dataframe(
                            trip_display,
                            use_container_width=True,
                            height=700
                        )

                        # =====================================
                        # DOWNLOAD DISPLAYED REPORT
                        # =====================================

                        viajes_display_buffer = io.BytesIO()

                        with pd.ExcelWriter(
                            viajes_display_buffer,
                            engine="openpyxl"
                        ) as writer:

                            trip_display.to_excel(
                                writer,
                                index=False,
                                sheet_name="Viajes Detectados"
                            )

                        viajes_display_buffer.seek(0)

                        st.download_button(
                            label="💾 Descargar Viajes Detectados",
                            data=viajes_display_buffer,
                            file_name=(
                                f"Viajes_Detectados_{selected_unit}.xlsx"
                            ),
                            mime=(
                                "application/vnd.openxmlformats-officedocument."
                                "spreadsheetml.sheet"
                            ),
                            use_container_width=True,
                            key=f"download_viajes_detectados_{selected_unit}"
                        )

                        # =====================================
                        # FULL DEBUG
                        # =====================================

                        with st.expander(
                            "🔍 Datos Completos GPS Insight",
                            expanded=False
                        ):

                            st.dataframe(
                                trip_df,
                                use_container_width=True,
                                height=600
                            )

                        # =====================================
                        # EXPORT
                        # =====================================

                        export_df = trip_df.copy()

                        export_unit = str(
                            selected_unit
                        ).strip()

                        if " " in export_unit:

                            export_unit = (
                                export_unit
                                .split(
                                    " ",
                                    1
                                )[1]
                                .strip()
                            )

                        export_df.insert(
                            0,
                            "Unidad",
                            export_unit
                        )

                        export_df.insert(
                            1,
                            "Reporte Fecha Inicial",
                            start_str
                        )

                        export_df.insert(
                            2,
                            "Reporte Fecha Final",
                            end_str
                        )

                        export_df.insert(
                            3,
                            "Reporte Total Viajes",
                            total_trips
                        )

                        export_df.insert(
                            4,
                            f"Reporte Total {distance_unit.upper()}",
                            total_km
                        )

                        export_df.insert(
                            5,
                            f"Reporte Velocidad Máxima ({speed_unit})",
                            max_speed
                        )

                        export_df.insert(
                            6,
                            f"Reporte Velocidad Promedio ({speed_unit})",
                            avg_speed
                        )

                        export_buffer = io.BytesIO()

                        with pd.ExcelWriter(
                            export_buffer,
                            engine="openpyxl"
                        ) as writer:

                            export_df.to_excel(
                                writer,
                                index=False,
                                sheet_name="Historial Viajes"
                            )

                        export_buffer.seek(0)

                        st.download_button(
                            label="💾 Descargar Reporte Completo",
                            data=export_buffer,
                            file_name=(
                                f"Historial_{selected_unit}.xlsx"
                            ),
                            mime=(
                                "application/vnd.openxmlformats-officedocument."
                                "spreadsheetml.sheet"
                            ),
                            use_container_width=True
                        )

                # =================================================
                # GENERAL FLEET TRIP HISTORY
                # =================================================

                st.divider()

                st.subheader(
                    "📊 Historial General de Flotilla"
                )

                st.write(
                    "Reporte consolidado de viajes de las unidades "
                    "de la empresa seleccionada para el rango "
                    "de fechas seleccionado."
                )

                # =================================================
                # BUILD COMPANY-FILTERED FLEET
                # =================================================

                history_df = df.copy()

                history_labels = (
                    history_df["label"]
                    .fillna("")
                    .astype(str)
                    .str.upper()
                )

                picus_mask = (
                    history_labels.str.contains(
                        "PI",
                        na=False
                    )
                    | history_labels.str.startswith("P")
                )

                lincoln_mask = (
                    history_labels.str.contains(
                        "LF",
                        na=False
                    )
                    | history_labels.str.startswith("L")
                )

                set_freight_mask = (
                    history_labels.str.contains(
                        "SET",
                        na=False
                    )
                )

                set_logis_mask = (
                    history_labels.str.contains(
                        "SPL",
                        na=False
                    )
                    | history_labels.str.contains(
                        "STL",
                        na=False
                    )
                )

                if company_filter == "PICUS":

                    history_df = history_df[
                        picus_mask
                    ].copy()

                elif company_filter == "LINCOLN":

                    history_df = history_df[
                        lincoln_mask
                    ].copy()

                elif company_filter == "SET FREIGHT":

                    history_df = history_df[
                        set_freight_mask
                    ].copy()

                elif company_filter == "SET LOGIS":

                    history_df = history_df[
                        set_logis_mask
                    ].copy()

                elif company_filter == "OTROS":

                    known_company_mask = (
                        picus_mask
                        | lincoln_mask
                        | set_freight_mask
                        | set_logis_mask
                    )

                    history_df = history_df[
                        ~known_company_mask
                    ].copy()

                # =================================================
                # RESET REPORT WHEN COMPANY CHANGES
                # =================================================

                previous_company = st.session_state.get(
                    "gps_history_report_company"
                )

                if previous_company != company_filter:

                    st.session_state[
                        "gps_history_report_generated"
                    ] = False

                    st.session_state[
                        "gps_history_report_company"
                    ] = company_filter

                # =================================================
                # TODAS = REPORT DISABLED
                # =================================================

                if company_filter == "TODAS":

                    st.warning(
                        "⚠️ Por favor utiliza los filtros superiores "
                        "para elegir una empresa y generar el reporte "
                        "de unidades."
                    )

                    st.info(
                        "Selecciona una empresa en los filtros superiores "
                        "para habilitar el Historial General de Flotilla."
                    )

                else:

                    fleet_units = sorted(
                        history_df["label"]
                        .dropna()
                        .astype(str)
                        .unique()
                        .tolist()
                    )

                    total_units = len(
                        fleet_units
                    )

                    if total_units == 0:

                        st.warning(
                            f"No se encontraron unidades para "
                            f"{company_filter}."
                        )

                    else:

                        st.success(
                            f"Empresa seleccionada: **{company_filter}**  \n"
                            f"Unidades disponibles para el reporte: "
                            f"**{total_units}**"
                        )

                        # =================================================
                        # GENERATE REPORT BUTTON
                        # =================================================

                        st.session_state.setdefault(
                            "gps_history_report_generated",
                            False
                        )

                        if not st.session_state.gps_history_report_generated:

                            st.info(
                                f"Presiona el botón para consultar las "
                                f"{total_units} unidades de {company_filter}."
                            )

                            if st.button(
                                "📊 Generar Reporte",
                                type="primary",
                                use_container_width=True
                            ):

                                st.session_state[
                                    "gps_history_report_generated"
                                ] = True

                                st.rerun()

                        else:

                            # =================================================
                            # COLLECT ALL UNIT TRIPS
                            # =================================================

                            all_trip_data = []

                            fleet_progress = st.progress(
                                0,
                                text=(
                                    f"Preparando historial de flotilla... "
                                    f"0 de {total_units} unidades"
                                )
                            )

                            # =================================================
                            # GET TRIPS FOR ONE UNIT
                            # =================================================

                            def get_fleet_unit_trips(
                                fleet_unit
                            ):

                                try:

                                    # =============================================
                                    # GET CORRECT TOKEN
                                    # =============================================

                                    fleet_label = str(
                                        fleet_unit
                                    ).upper()

                                    if (
                                        "PI" in fleet_label
                                        or fleet_label.startswith("P")
                                    ):

                                        fleet_token = PICUS_TOKEN

                                    else:

                                        fleet_token = PGL_TOKEN

                                    # =============================================
                                    # BUILD REQUEST
                                    # =============================================

                                    fleet_url = (
                                        "https://api.gpsinsight.com/v2/"
                                        "vehicle/trips"
                                        f"?session_token={fleet_token}"
                                        f"&vehicle={fleet_unit}"
                                        f"&start={start_str}"
                                        f"&end={end_str}"
                                    )

                                    # =============================================
                                    # REQUEST
                                    # =============================================

                                    fleet_response = requests.get(
                                        fleet_url,
                                        timeout=60
                                    )

                                    fleet_response.raise_for_status()

                                    fleet_result = (
                                        fleet_response.json()
                                    )

                                    fleet_data = fleet_result.get(
                                        "data",
                                        []
                                    )

                                    # =============================================
                                    # PROCESS TRIPS
                                    # =============================================

                                    if not fleet_data:

                                        return {
                                            "unit": fleet_unit,
                                            "trip_df": pd.DataFrame(),
                                            "error": None
                                        }

                                    fleet_activity_df = pd.DataFrame(
                                        fleet_data
                                    )

                                    # =============================================
                                    # ONLY REAL TRIPS
                                    # =============================================

                                    fleet_trip_df = fleet_activity_df.copy()

                                    #if "trip_type" not in fleet_activity_df.columns:

                                     #   return {
                                      #      "unit": fleet_unit,
                                       #     "trip_df": pd.DataFrame(),
                                        #    "error": None
                                        #}

                                    #fleet_trip_df = (
                                    #    fleet_activity_df[
                                    #        fleet_activity_df[
                                    #            "trip_type"
                                    #        ] == "T"
                                    #    ].copy()
                                    #)

                                    # =============================================
                                    # PICUS UNIT CONVERSION
                                    # =============================================

                                    if (
                                        "PI" in fleet_label
                                        or fleet_label.startswith("P")
                                    ):

                                        MILES_TO_KM = 1.609344

                                        for col in [
                                            "trip_distance",
                                            "max_speed",
                                            "avg_speed"
                                        ]:

                                            if col in fleet_trip_df.columns:

                                                fleet_trip_df[col] = pd.to_numeric(
                                                    fleet_trip_df[col],
                                                    errors="coerce"
                                                ).fillna(0)

                                                fleet_trip_df[col] = (
                                                    fleet_trip_df[col]
                                                    * MILES_TO_KM
                                                )

                                    # =============================================
                                    # ADD UNIT
                                    # =============================================

                                    if not fleet_trip_df.empty:

                                        fleet_trip_df.insert(
                                            0,
                                            "Unidad",
                                            fleet_unit
                                        )

                                    return {
                                        "unit": fleet_unit,
                                        "trip_df": fleet_trip_df,
                                        "error": None
                                    }

                                except Exception as unit_error:

                                    return {
                                        "unit": fleet_unit,
                                        "trip_df": pd.DataFrame(),
                                        "error": str(unit_error)
                                    }

                            # =================================================
                            # PARALLEL REQUESTS
                            # =================================================

                            completed_units = 0

                            # Units that successfully returned no trips
                            units_without_records = []

                            # Keep this conservative.
                            # 8 requests will run simultaneously.
                            MAX_WORKERS = 8

                            with ThreadPoolExecutor(
                                max_workers=MAX_WORKERS
                            ) as executor:

                                future_to_unit = {
                                    executor.submit(
                                        get_fleet_unit_trips,
                                        fleet_unit
                                    ): fleet_unit

                                    for fleet_unit in fleet_units
                                }

                                for future in as_completed(
                                    future_to_unit
                                ):

                                    fleet_unit = future_to_unit[
                                        future
                                    ]

                                    try:

                                        result = future.result()

                                        result_unit = result[
                                            "unit"
                                        ]

                                        fleet_trip_df = result[
                                            "trip_df"
                                        ]

                                        unit_error = result[
                                            "error"
                                        ]

                                        # =========================================
                                        # ADD SUCCESSFUL TRIPS
                                        # =========================================

                                        if (
                                            fleet_trip_df is not None
                                            and not fleet_trip_df.empty
                                        ):

                                            all_trip_data.append(
                                                fleet_trip_df
                                            )

                                        # =========================================
                                        # HANDLE UNITS WITHOUT TRIPS
                                        # =========================================

                                        if (
                                            not unit_error
                                            and (
                                                fleet_trip_df is None
                                                or fleet_trip_df.empty
                                            )
                                        ):

                                            units_without_records.append(
                                                result_unit
                                            )

                                    except Exception as future_error:

                                        st.warning(
                                            f"Error procesando "
                                            f"{fleet_unit}: "
                                            f"{future_error}"
                                        )

                                    # =============================================
                                    # UPDATE PROGRESS
                                    # =============================================

                                    completed_units += 1

                                    progress_value = (
                                        completed_units / total_units
                                        if total_units
                                        else 1
                                    )

                                    fleet_progress.progress(
                                        progress_value,
                                        text=(
                                            f"Consultando historial de "
                                            f"{company_filter}: "
                                            f"{completed_units} de "
                                            f"{total_units} unidades..."
                                        )
                                    )

                            # =================================================
                            # FINISH PROGRESS
                            # =================================================

                            fleet_progress.empty()

                            # =================================================
                            # COMBINE ALL TRIPS
                            # =================================================

                            if all_trip_data:

                                fleet_trip_df = pd.concat(
                                    all_trip_data,
                                    ignore_index=True
                                )

                                st.session_state["gps_history_report_data"] = (
                                    fleet_trip_df.copy()
                                )

                                # =============================================
                                # NUMERIC CLEANUP
                                # =============================================

                                numeric_cols = [
                                    "trip_distance",
                                    "max_speed",
                                    "avg_speed",
                                    "trip_duration"
                                ]

                                for col in numeric_cols:

                                    if col in fleet_trip_df.columns:

                                        fleet_trip_df[col] = pd.to_numeric(
                                            fleet_trip_df[col],
                                            errors="coerce"
                                        ).fillna(0)

                                # =============================================
                                # DISPLAY TABLE
                                # =============================================

                                fleet_display = (
                                    fleet_trip_df.copy()
                                )

                                # =============================================
                                # DISTANCE UNIT
                                # =============================================

                                def fleet_distance_unit(
                                    unit
                                ):

                                    unit_label = (
                                        str(unit)
                                        .upper()
                                    )

                                    picus = (
                                        "PI" in unit_label
                                        or unit_label.startswith("P")
                                    )

                                    otros = not (
                                        picus
                                        or "LF" in unit_label
                                        or unit_label.startswith("L")
                                        or "SET" in unit_label
                                        or "SPL" in unit_label
                                        or "STL" in unit_label
                                    )

                                    return (
                                        "km"
                                        if picus or otros
                                        else "mi"
                                    )

                                # =============================================
                                # SPEED UNIT
                                # =============================================

                                def fleet_speed_unit(
                                    unit
                                ):

                                    return (
                                        "km/h"
                                        if fleet_distance_unit(unit)
                                        == "km"
                                        else "mph"
                                    )

                                # =============================================
                                # DISTANCE
                                # =============================================

                                if "trip_distance" in fleet_display.columns:

                                    fleet_display[
                                        "Distancia"
                                    ] = fleet_display.apply(
                                        lambda row:
                                        f"{round(float(row['trip_distance']), 1)} "
                                        f"{fleet_distance_unit(row['Unidad'])}",
                                        axis=1
                                    )

                                # =============================================
                                # DURATION
                                # =============================================

                                if "trip_duration" in fleet_display.columns:

                                    fleet_display[
                                        "Duración"
                                    ] = (
                                        fleet_display[
                                            "trip_duration"
                                        ]
                                        .apply(
                                            lambda x:
                                            f"{int(x // 3600)}h "
                                            f"{int((x % 3600) // 60)}m"
                                        )
                                    )

                                # =============================================
                                # MAX SPEED
                                # =============================================

                                if "max_speed" in fleet_display.columns:

                                    fleet_display[
                                        "Vel Máxima"
                                    ] = fleet_display.apply(
                                        lambda row:
                                        f"{round(float(row['max_speed']), 1)} "
                                        f"{fleet_speed_unit(row['Unidad'])}",
                                        axis=1
                                    )

                                # =============================================
                                # AVG SPEED
                                # =============================================

                                if "avg_speed" in fleet_display.columns:

                                    fleet_display[
                                        "Vel Promedio"
                                    ] = fleet_display.apply(
                                        lambda row:
                                        f"{round(float(row['avg_speed']), 1)} "
                                        f"{fleet_speed_unit(row['Unidad'])}",
                                        axis=1
                                    )

                                # =============================================
                                # RENAME DATES
                                # =============================================

                                fleet_display.rename(
                                    columns={
                                        "trip_start": "Inicio",
                                        "trip_end": "Fin"
                                    },
                                    inplace=True
                                )

                                # =============================================
                                # DISPLAY TABLE
                                # =============================================

                                preferred_columns = [
                                    "Unidad",
                                    "Inicio",
                                    "Fin",
                                    "Distancia",
                                    "Duración",
                                    "Vel Máxima",
                                    "Vel Promedio"
                                ]

                                available_columns = [
                                    col
                                    for col in preferred_columns
                                    if col in fleet_display.columns
                                ]

                                fleet_display = (
                                    fleet_display[
                                        available_columns
                                    ]
                                )

                                fleet_display.sort_values(
                                    by=[
                                        col
                                        for col in [
                                            "Unidad",
                                            "Inicio"
                                        ]
                                        if col in fleet_display.columns
                                    ],
                                    inplace=True
                                )

                                fleet_display.reset_index(
                                    drop=True,
                                    inplace=True
                                )

                                # =============================================
                                # SUMMARY
                                # =============================================

                                units_with_records = (
                                    fleet_display["Unidad"].nunique()
                                )

                                units_without_records_count = (
                                    len(units_without_records)
                                )

                                message = (
                                    f"Reporte generado correctamente. "
                                    f"Empresa: **{company_filter}** | "
                                    f"Unidades: **{units_with_records}** | "
                                    f"Viajes: **{len(fleet_display):,}**"
                                )

                                if units_without_records_count > 0:

                                    message += (
                                        f" | **{units_without_records_count} unidades "
                                        f"no contienen registro en el rango de "
                                        f"fechas seleccionado.**"
                                    )

                                st.success(message)

                                st.dataframe(
                                    fleet_display,
                                    use_container_width=True,
                                    height=700
                                )

                                # =============================================
                                # EXPORT
                                # =============================================

                                fleet_export_buffer = io.BytesIO()

                                with pd.ExcelWriter(
                                    fleet_export_buffer,
                                    engine="openpyxl"
                                ) as writer:

                                    fleet_trip_df.to_excel(
                                        writer,
                                        index=False,
                                        sheet_name="Historial Flotilla"
                                    )

                                fleet_export_buffer.seek(0)

                                st.download_button(
                                    label=(
                                        "💾 Descargar Historial General "
                                        "de Flotilla"
                                    ),
                                    data=fleet_export_buffer,
                                    file_name=(
                                        f"Historial_General_"
                                        f"{company_filter.replace(' ', '_')}.xlsx"
                                    ),
                                    mime=(
                                        "application/"
                                        "vnd.openxmlformats-officedocument."
                                        "spreadsheetml.sheet"
                                    ),
                                    use_container_width=True,
                                    on_click="ignore"
                                )

                            else:

                                st.warning(
                                    "No se encontraron viajes para ninguna "
                                    f"unidad de {company_filter} en el rango "
                                    "de fechas seleccionado."
                                )

        except Exception as e:

            st.error(
                f"Error consultando historial: {e}"
            )

# WIALON API
# =========================================
with tab_wialon:

    # =========================================================
    # WIALON DATA
    # =========================================================

    st.header(
        "🛰️ Rastreador y Seguimiento GPS de Unidades - WIALON"
    )

    WIALON_API_URL = (
        "https://hst-api.wialon.com/wialon/ajax.html"
    )

    WIALON_TOKEN = (
        "80116688b2812ec4b012e91c4783618122D6783187118B551FDD06B30949543E37B40683"
    )

    # =========================================================
    # HELPERS
    # =========================================================

    def wialon_request(
        service,
        params,
        sid=None
    ):

        request_params = {
            "svc": service,
            "params": json.dumps(params)
        }

        if sid:
            request_params["sid"] = sid

        response = requests.post(
            WIALON_API_URL,
            data=request_params,
            headers={
                "Content-Type": (
                    "application/x-www-form-urlencoded"
                )
            },
            timeout=30
        )

        response.raise_for_status()

        return response.json()

    def safe_dict(value):
        return value if isinstance(value, dict) else {}

    def safe_list(value):
        return value if isinstance(value, list) else []

    def safe_value(value, key, default=""):
        if isinstance(value, dict):
            result = value.get(key, default)
            return default if result is None else result
        return default

    def numeric_value(value, default=0.0):
        try:
            if value is None or value == "":
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    def get_unit_position(unit):
        return safe_dict(unit.get("pos"))

    def get_unit_message(unit):
        return safe_dict(unit.get("lmsg"))

    def get_unit_params(unit):
        return safe_dict(
            get_unit_message(unit).get("p")
        )

    def get_unit_speed(unit):
        return numeric_value(
            get_unit_position(unit).get("s")
        )

    def get_unit_engine(unit):
        params = get_unit_params(unit)
        value = str(
            params.get(
                "engine_on",
                ""
            )
        ).lower()

        if value in ("1", "true", "on", "yes"):
            return "ON"

        if value in ("0", "false", "off", "no"):
            return "OFF"

        return "-"

    def get_unit_power(unit):
        params = get_unit_params(unit)

        power = params.get(
            "power",
            ""
        )

        if power in ("", None):
            power = params.get(
                "battery",
                ""
            )

        return power

    def get_unit_status(unit):
        return (
            "🟢 En Movimiento"
            if get_unit_speed(unit) > 0
            else "🔴 Detenida"
        )

    # =========================================================
    # WIALON CONNECTION
    # =========================================================

    try:

        login_response = wialon_request(
            "token/login",
            {
                "token": WIALON_TOKEN,
                "fl": 15
            }
        )

        sid = login_response.get("eid")

        if not sid:
            st.error(
                "❌ Wialon no devolvió un session ID."
            )
            st.stop()

        # =====================================================
        # GET ALL UNITS
        # =====================================================

        units_response = wialon_request(
            "core/search_items",
            {
                "spec": {
                    "itemsType": "avl_unit",
                    "propName": "sys_name",
                    "propValueMask": "*",
                    "sortType": "sys_name"
                },
                "force": 1,
                "flags": 1025,
                "from": 0,
                "to": 0
            },
            sid=sid
        )

        units = safe_list(
            safe_dict(units_response).get("items")
        )

        # =====================================================
        # GET ALL TRAILERS
        # =====================================================

        trailers_response = wialon_request(
            "core/search_items",
            {
                "spec": {
                    "itemsType": "avl_resource",
                    "propName": "sys_name",
                    "propValueMask": "*",
                    "sortType": "sys_name"
                },
                "force": 1,
                "flags": 65537,
                "from": 0,
                "to": 0
            },
            sid=sid
        )

        trailer_resources = safe_list(
            safe_dict(trailers_response).get("items")
        )

        trailer_catalog = []

        for resource in trailer_resources:

            resource = safe_dict(resource)

            resource_id = safe_value(
                resource,
                "id"
            )

            resource_name = safe_value(
                resource,
                "nm"
            )

            trailers = safe_dict(
                resource.get("trlrs")
            )

            for trailer_key, trailer in trailers.items():

                trailer = safe_dict(trailer)

                trailer_id = safe_value(
                    trailer,
                    "id",
                    trailer_key
                )

                trailer_name = safe_value(
                    trailer,
                    "n",
                    safe_value(
                        trailer,
                        "nm",
                        safe_value(
                            trailer,
                            "name",
                            trailer_id
                        )
                    )
                )

                trailer_catalog.append(
                    {
                        "resource_id": resource_id,
                        "resource_name": resource_name,
                        "trailer_id": trailer_id,
                        "trailer_name": trailer_name,
                        "raw": trailer
                    }
                )

        trailer_catalog = sorted(
            trailer_catalog,
            key=lambda item: (
                str(
                    item.get(
                        "trailer_name",
                        ""
                    )
                ).lower(),
                str(
                    item.get(
                        "trailer_id",
                        ""
                    )
                )
            )
        )

        # =====================================================
        # TOP-LEVEL WIALON TABS
        # =====================================================

        (
            tab_wialon_dashboard,
            tab_wialon_seguimiento,
            tab_wialon_mapa,
            tab_wialon_historial
        ) = st.tabs(
            [
                "📊 Dashboard",
                "🚛 Seguimiento",
                "🗺️ Mapa",
                "📈 Historial"
            ]
        )

        # =====================================================
        # DASHBOARD
        # =====================================================

        with tab_wialon_dashboard:

            st.header(
                "📊 Dashboard Operativo Wialon"
            )

            if not units:

                st.warning(
                    "Wialon respondió correctamente, "
                    "pero no devolvió unidades."
                )

            else:

                moving_units = sum(
                    get_unit_speed(unit) > 0
                    for unit in units
                )

                stopped_units = (
                    len(units) - moving_units
                )

                engine_on = sum(
                    get_unit_engine(unit) == "ON"
                    for unit in units
                )

                engine_off = sum(
                    get_unit_engine(unit) == "OFF"
                    for unit in units
                )

                speeds = [
                    get_unit_speed(unit)
                    for unit in units
                ]

                avg_speed = (
                    sum(speeds) / len(speeds)
                    if speeds
                    else 0
                )

                max_speed = (
                    max(speeds)
                    if speeds
                    else 0
                )

                low_power = 0

                for unit in units:

                    power = numeric_value(
                        get_unit_power(unit),
                        None
                    )

                    if (
                        power is not None
                        and power > 0
                        and power < 11
                    ):
                        low_power += 1

                avg_satellites = 0

                satellite_values = []

                for unit in units:

                    satellites = numeric_value(
                        get_unit_position(unit).get(
                            "sc"
                        ),
                        None
                    )

                    if satellites is not None:
                        satellite_values.append(
                            satellites
                        )

                if satellite_values:
                    avg_satellites = (
                        sum(satellite_values)
                        / len(satellite_values)
                    )

                # -------------------------------------------------
                # KPI ROW 1
                # -------------------------------------------------

                c1, c2, c3, c4, c5, c6 = st.columns(6)

                c1.metric(
                    "🚛 Total",
                    len(units)
                )

                c2.metric(
                    "🟢 Movimiento",
                    moving_units
                )

                c3.metric(
                    "🔴 Detenidas",
                    stopped_units
                )

                c4.metric(
                    "⚡ Engine ON",
                    engine_on
                )

                c5.metric(
                    "⛔ Engine OFF",
                    engine_off
                )

                c6.metric(
                    "🏎️ Vel. Promedio",
                    f"{avg_speed:.1f} km/h"
                )

                c7, c8, c9, c10 = st.columns(4)

                c7.metric(
                    "🔥 Velocidad Máxima",
                    f"{max_speed:.1f} km/h"
                )

                c8.metric(
                    "🔋 Power Bajo",
                    low_power
                )

                c9.metric(
                    "🛰️ Satélites Promedio",
                    f"{avg_satellites:.1f}"
                )

                c10.metric(
                    "📦 Cajas / Remolques",
                    len(trailer_catalog)
                )

                st.divider()

                # -------------------------------------------------
                # STATUS SUMMARY
                # -------------------------------------------------

                st.subheader(
                    "📡 Estado actual de la flotilla"
                )

                dashboard_rows = []

                for unit in units:

                    position = get_unit_position(unit)
                    message = get_unit_message(unit)

                    dashboard_rows.append(
                        {
                            "Unidad": safe_value(
                                unit,
                                "nm"
                            ),
                            "ID Wialon": safe_value(
                                unit,
                                "id"
                            ),
                            "Estado": get_unit_status(
                                unit
                            ),
                            "Velocidad": (
                                f"{get_unit_speed(unit):.1f} km/h"
                            ),
                            "Engine": get_unit_engine(
                                unit
                            ),
                            "Power": get_unit_power(
                                unit
                            ),
                            "Latitud": safe_value(
                                position,
                                "y"
                            ),
                            "Longitud": safe_value(
                                position,
                                "x"
                            ),
                            "Satélites": safe_value(
                                position,
                                "sc"
                            ),
                            "Hora Posición": safe_value(
                                position,
                                "t"
                            ),
                            "Último Mensaje": safe_value(
                                message,
                                "t"
                            )
                        }
                    )

                dashboard_df = pd.DataFrame(
                    dashboard_rows
                )

                st.dataframe(
                    dashboard_df,
                    use_container_width=True,
                    height=500,
                    hide_index=True
                )

                dashboard_buffer = io.BytesIO()

                with pd.ExcelWriter(
                    dashboard_buffer,
                    engine="openpyxl"
                ) as writer:

                    dashboard_df.to_excel(
                        writer,
                        index=False,
                        sheet_name="Wialon Dashboard"
                    )

                dashboard_buffer.seek(0)

                st.download_button(
                    label="💾 Descargar Dashboard Wialon",
                    data=dashboard_buffer,
                    file_name="Wialon_Dashboard.xlsx",
                    mime=(
                        "application/"
                        "vnd.openxmlformats-officedocument."
                        "spreadsheetml.sheet"
                    ),
                    use_container_width=True,
                    key="wialon_dashboard_download"
                )

                st.divider()

                # -------------------------------------------------
                # UNIT TYPE SUMMARY
                # -------------------------------------------------

                st.subheader(
                    "🚛 Resumen de unidades"
                )

                s1, s2 = st.columns(2)

                with s1:

                    st.metric(
                        "Unidades con posición",
                        sum(
                            bool(
                                get_unit_position(unit)
                            )
                            for unit in units
                        )
                    )

                with s2:

                    st.metric(
                        "Unidades con último mensaje",
                        sum(
                            bool(
                                get_unit_message(unit)
                            )
                            for unit in units
                        )
                    )

        # =====================================================
        # SEGUIMIENTO
        # =====================================================

        with tab_wialon_seguimiento:

            st.header(
                "🚛 Seguimiento Individual de Unidades"
            )

            if not units:

                st.warning(
                    "No hay información de unidades disponible."
                )

            else:

                # -------------------------------------------------
                # FILTERS
                # -------------------------------------------------

                f1, f2, f3 = st.columns(3)

                unit_names = sorted(
                    [
                        str(
                            safe_value(
                                unit,
                                "nm"
                            )
                        )
                        for unit in units
                        if safe_value(
                            unit,
                            "nm"
                        )
                    ]
                )

                with f1:

                    selected_unit_name = st.selectbox(
                        "No. de Unidad",
                        ["Todas"] + unit_names,
                        key="wialon_tracking_unit"
                    )

                with f2:

                    selected_status = st.selectbox(
                        "Estado",
                        [
                            "Todos",
                            "🟢 En Movimiento",
                            "🔴 Detenida"
                        ],
                        key="wialon_tracking_status"
                    )

                with f3:

                    selected_engine = st.selectbox(
                        "Estado de Engine",
                        [
                            "Todos",
                            "ON",
                            "OFF",
                            "-"
                        ],
                        key="wialon_tracking_engine"
                    )

                filtered_units = list(units)

                if selected_unit_name != "Todas":

                    filtered_units = [
                        unit
                        for unit in filtered_units
                        if str(
                            safe_value(
                                unit,
                                "nm"
                            )
                        ) == selected_unit_name
                    ]

                if selected_status == "🟢 En Movimiento":

                    filtered_units = [
                        unit
                        for unit in filtered_units
                        if get_unit_speed(unit) > 0
                    ]

                elif selected_status == "🔴 Detenida":

                    filtered_units = [
                        unit
                        for unit in filtered_units
                        if get_unit_speed(unit) <= 0
                    ]

                if selected_engine != "Todos":

                    filtered_units = [
                        unit
                        for unit in filtered_units
                        if get_unit_engine(unit)
                        == selected_engine
                    ]

                st.caption(
                    f"{len(filtered_units)} unidad(es) encontradas"
                )

                # -------------------------------------------------
                # POST-IT CARDS
                # -------------------------------------------------

                if not filtered_units:

                    st.warning(
                        "No se encontraron unidades con los filtros seleccionados."
                    )

                else:

                    ITEMS_PER_PAGE = 10

                    st.session_state.setdefault(
                        "wialon_tracking_page",
                        1
                    )

                    total_pages = max(
                        (
                            len(filtered_units) - 1
                        )
                        // ITEMS_PER_PAGE
                        + 1,
                        1
                    )

                    if (
                        st.session_state.wialon_tracking_page
                        > total_pages
                    ):
                        st.session_state.wialon_tracking_page = (
                            total_pages
                        )

                    start_idx = (
                        st.session_state.wialon_tracking_page
                        - 1
                    ) * ITEMS_PER_PAGE

                    page_units = filtered_units[
                        start_idx:
                        start_idx + ITEMS_PER_PAGE
                    ]

                    idx = 0

                    rows_needed = (
                        (len(page_units) - 1)
                        // 5
                        + 1
                    )

                    for _ in range(rows_needed):

                        cols = st.columns(5)

                        for col in cols:

                            if idx >= len(page_units):
                                break

                            unit = page_units[idx]

                            unit_name = str(
                                safe_value(
                                    unit,
                                    "nm",
                                    "-"
                                )
                            )

                            position = get_unit_position(
                                unit
                            )

                            message = get_unit_message(
                                unit
                            )

                            speed = get_unit_speed(
                                unit
                            )

                            engine = get_unit_engine(
                                unit
                            )

                            power = get_unit_power(
                                unit
                            )

                            status = get_unit_status(
                                unit
                            )

                            lat = safe_value(
                                position,
                                "y",
                                "-"
                            )

                            lon = safe_value(
                                position,
                                "x",
                                "-"
                            )

                            pos_time = safe_value(
                                position,
                                "t",
                                "-"
                            )

                            satellites = safe_value(
                                position,
                                "sc",
                                "-"
                            )

                            last_message = safe_value(
                                message,
                                "t",
                                "-"
                            )

                            status_bg = (
                                "#D4EDDA"
                                if speed > 0
                                else "#F8D7DA"
                            )

                            with col:

                                html = f"""
                                <div style="
                                    padding:6px;
                                ">
                                    <div style="
                                        background:#e8f0ff;
                                        padding:14px;
                                        border-radius:16px;
                                        box-shadow:0 4px 10px rgba(0,0,0,0.08);
                                        color:#111;
                                        min-height:300px;
                                        font-family:sans-serif;
                                    ">

                                        <div style="
                                            font-size:1.1rem;
                                            font-weight:900;
                                        ">
                                            🚛 {unit_name}
                                        </div>

                                        <hr style="margin:8px 0">

                                        <div style="
                                            font-size:0.82rem;
                                            margin-top:8px;
                                        ">
                                            <strong>Velocidad:</strong>
                                            {speed:.1f} km/h
                                        </div>

                                        <div style="
                                            font-size:0.82rem;
                                        ">
                                            <strong>Engine:</strong>
                                            {engine}
                                        </div>

                                        <div style="
                                            font-size:0.82rem;
                                        ">
                                            <strong>Power:</strong>
                                            {power}
                                        </div>

                                        <div style="
                                            font-size:0.82rem;
                                        ">
                                            <strong>Satélites:</strong>
                                            {satellites}
                                        </div>

                                        <div style="
                                            margin-top:8px;
                                            padding:6px;
                                            border-radius:8px;
                                            background:{status_bg};
                                            text-align:center;
                                            font-weight:700;
                                        ">
                                            {status}
                                        </div>

                                        <div style="
                                            margin-top:8px;
                                            font-size:0.72rem;
                                            opacity:0.75;
                                        ">
                                            Posición:
                                            <br>
                                            {lat}, {lon}
                                            <br><br>
                                            Hora posición:
                                            <br>
                                            {pos_time}
                                            <br><br>
                                            Último mensaje:
                                            <br>
                                            {last_message}
                                        </div>

                                    </div>
                                </div>
                                """

                                components.html(
                                    html,
                                    height=350
                                )

                                b1, b2 = st.columns(2)

                                with b1:

                                    if st.button(
                                        "👁 Ver",
                                        key=(
                                            "wialon_view_"
                                            f"{safe_value(unit, 'id', idx)}"
                                        ),
                                        use_container_width=True
                                    ):

                                        st.session_state[
                                            "wialon_detail_unit_id"
                                        ] = safe_value(
                                            unit,
                                            "id"
                                        )

                                        st.rerun()

                                with b2:

                                    unit_excel = pd.DataFrame(
                                        [
                                            {
                                                "ID Wialon": safe_value(
                                                    unit,
                                                    "id"
                                                ),
                                                "Unidad": unit_name,
                                                "Clase": safe_value(
                                                    unit,
                                                    "cls"
                                                ),
                                                "Sistema de Medición": safe_value(
                                                    unit,
                                                    "mu"
                                                ),
                                                "Velocidad": speed,
                                                "Engine": engine,
                                                "Power": power,
                                                "Latitud": lat,
                                                "Longitud": lon,
                                                "Satélites": satellites,
                                                "Hora Posición": pos_time,
                                                "Último Mensaje": last_message
                                            }
                                        ]
                                    )

                                    unit_buffer = io.BytesIO()

                                    with pd.ExcelWriter(
                                        unit_buffer,
                                        engine="openpyxl"
                                    ) as writer:

                                        unit_excel.to_excel(
                                            writer,
                                            index=False,
                                            sheet_name="Wialon"
                                        )

                                    unit_buffer.seek(0)

                                    st.download_button(
                                        label="💾 Guardar",
                                        data=unit_buffer,
                                        file_name=(
                                            f"Wialon_{unit_name}.xlsx"
                                        ),
                                        mime=(
                                            "application/"
                                            "vnd.openxmlformats-officedocument."
                                            "spreadsheetml.sheet"
                                        ),
                                        key=(
                                            "wialon_save_"
                                            f"{safe_value(unit, 'id', idx)}"
                                        ),
                                        use_container_width=True
                                    )

                            idx += 1

                    st.divider()

                    p1, p2, p3 = st.columns(
                        [1, 2, 1]
                    )

                    with p1:

                        if st.button(
                            "⬅ Anterior",
                            disabled=(
                                st.session_state.wialon_tracking_page
                                <= 1
                            ),
                            use_container_width=True,
                            key="wialon_tracking_prev"
                        ):

                            st.session_state.wialon_tracking_page -= 1
                            st.rerun()

                    with p2:

                        st.markdown(
                            f"""
                            <div style="
                                text-align:center;
                                padding-top:8px;
                                font-weight:700;
                            ">
                                Página {
                                    st.session_state.wialon_tracking_page
                                }
                                de {total_pages}
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                    with p3:

                        if st.button(
                            "Siguiente ➡",
                            disabled=(
                                st.session_state.wialon_tracking_page
                                >= total_pages
                            ),
                            use_container_width=True,
                            key="wialon_tracking_next"
                        ):

                            st.session_state.wialon_tracking_page += 1
                            st.rerun()

                # -------------------------------------------------
                # DETAILED UNIT INFORMATION MODAL
                # -------------------------------------------------

                detail_unit_id = st.session_state.get(
                    "wialon_detail_unit_id"
                )

                detail_unit = next(
                    (
                        unit
                        for unit in units
                        if str(
                            safe_value(
                                unit,
                                "id"
                            )
                        ) == str(
                            detail_unit_id
                        )
                    ),
                    None
                )

                if detail_unit:

                    @st.dialog(
                        f"Unidad {safe_value(detail_unit, 'nm', '-')}",
                        width="large"
                    )
                    def wialon_unit_detail_dialog():


                        st.divider()

                        st.subheader(
                            "🔎 Información detallada de unidad"
                        )

                        detailed_unit_response = wialon_request(
                            "core/search_item",
                            {
                                "id": safe_value(
                                    detail_unit,
                                    "id"
                                ),
                                "flags": 4611686018427387903
                            },
                            sid=sid
                        )

                        detailed_item = safe_dict(
                            safe_dict(
                                detailed_unit_response
                            ).get(
                                "item"
                            )
                        )

                        if not detailed_item:
                            detailed_item = safe_dict(
                                detail_unit
                            )

                        # ---------------------------------------------
                        # GENERAL
                        # ---------------------------------------------

                        st.markdown(
                            "### 📋 Identificación general"
                        )

                        general_rows = [
                            {
                                "Campo": "Nombre",
                                "Valor": safe_value(
                                    detailed_item,
                                    "nm"
                                )
                            },
                            {
                                "Campo": "ID Wialon",
                                "Valor": safe_value(
                                    detailed_item,
                                    "id"
                                )
                            },
                            {
                                "Campo": "Clase",
                                "Valor": safe_value(
                                    detailed_item,
                                    "cls"
                                )
                            },
                            {
                                "Campo": "Sistema de medición",
                                "Valor": safe_value(
                                    detailed_item,
                                    "mu"
                                )
                            },
                            {
                                "Campo": "Fecha de creación",
                                "Valor": safe_value(
                                    detailed_item,
                                    "ct"
                                )
                            },
                            {
                                "Campo": "ID creador",
                                "Valor": safe_value(
                                    detailed_item,
                                    "crt"
                                )
                            },
                            {
                                "Campo": "ID cuenta",
                                "Valor": safe_value(
                                    detailed_item,
                                    "bact"
                                )
                            },
                            {
                                "Campo": "GUID",
                                "Valor": safe_value(
                                    detailed_item,
                                    "gd"
                                )
                            },
                            {
                                "Campo": "Derechos de acceso",
                                "Valor": safe_value(
                                    detailed_item,
                                    "uacl"
                                )
                            }
                        ]

                        st.dataframe(
                            pd.DataFrame(
                                general_rows
                            ),
                            use_container_width=True,
                            hide_index=True
                        )

                        # ---------------------------------------------
                        # VEHICLE FIELDS
                        # ---------------------------------------------

                        flds = safe_dict(
                            detailed_item.get("flds")
                        )

                        pflds = safe_dict(
                            detailed_item.get("pflds")
                        )

                        vehicle_rows = []

                        for field in list(flds.values()) + list(pflds.values()):

                            field = safe_dict(field)

                            vehicle_rows.append(
                                {
                                    "Origen": (
                                        "Campo personalizado"
                                        if field in flds.values()
                                        else "Perfil"
                                    ),
                                    "Campo": safe_value(
                                        field,
                                        "n"
                                    ),
                                    "Valor": safe_value(
                                        field,
                                        "v"
                                    )
                                }
                            )

                        st.markdown(
                            "### 🚛 Información del vehículo"
                        )

                        if vehicle_rows:

                            st.dataframe(
                                pd.DataFrame(
                                    vehicle_rows
                                ),
                                use_container_width=True,
                                hide_index=True
                            )

                        else:

                            st.info(
                                "No hay campos de vehículo configurados para esta unidad."
                            )

                        # ---------------------------------------------
                        # POSITION
                        # ---------------------------------------------

                        position = safe_dict(
                            detailed_item.get("pos")
                        )

                        st.markdown(
                            "### 📍 Posición actual"
                        )

                        position_rows = [
                            {
                                "Campo": "Latitud",
                                "Valor": safe_value(
                                    position,
                                    "y"
                                )
                            },
                            {
                                "Campo": "Longitud",
                                "Valor": safe_value(
                                    position,
                                    "x"
                                )
                            },
                            {
                                "Campo": "Altitud",
                                "Valor": safe_value(
                                    position,
                                    "z"
                                )
                            },
                            {
                                "Campo": "Rumbo",
                                "Valor": safe_value(
                                    position,
                                    "c"
                                )
                            },
                            {
                                "Campo": "Velocidad",
                                "Valor": safe_value(
                                    position,
                                    "s"
                                )
                            },
                            {
                                "Campo": "Satélites",
                                "Valor": safe_value(
                                    position,
                                    "sc"
                                )
                            },
                            {
                                "Campo": "Timestamp",
                                "Valor": safe_value(
                                    position,
                                    "t"
                                )
                            }
                        ]

                        st.dataframe(
                            pd.DataFrame(
                                position_rows
                            ),
                            use_container_width=True,
                            hide_index=True
                        )

                        # ---------------------------------------------
                        # CONNECTION
                        # ---------------------------------------------

                        st.markdown(
                            "### 📡 Estado de conexión"
                        )

                        last_message = safe_dict(
                            detailed_item.get("lmsg")
                        )

                        connection_rows = [
                            {
                                "Campo": "Conexión TCP/UDP",
                                "Valor": safe_value(
                                    detailed_item,
                                    "netconn"
                                )
                            },
                            {
                                "Campo": "Activación",
                                "Valor": safe_value(
                                    detailed_item,
                                    "act"
                                )
                            },
                            {
                                "Campo": "Razón de activación",
                                "Valor": safe_value(
                                    detailed_item,
                                    "act_reason"
                                )
                            },
                            {
                                "Campo": "Último mensaje",
                                "Valor": safe_value(
                                    last_message,
                                    "t"
                                )
                            },
                            {
                                "Campo": "Registro en servidor",
                                "Valor": safe_value(
                                    last_message,
                                    "rt"
                                )
                            }
                        ]

                        st.dataframe(
                            pd.DataFrame(
                                connection_rows
                            ),
                            use_container_width=True,
                            hide_index=True
                        )

                        # ---------------------------------------------
                        # SENSORS
                        # ---------------------------------------------

                        sensors = safe_dict(
                            detailed_item.get("sens")
                        )

                        st.markdown(
                            "### 📊 Sensores configurados"
                        )

                        sensor_rows = []

                        for sensor in sensors.values():

                            sensor = safe_dict(sensor)

                            sensor_rows.append(
                                {
                                    "ID": safe_value(
                                        sensor,
                                        "id"
                                    ),
                                    "Nombre": safe_value(
                                        sensor,
                                        "n"
                                    ),
                                    "Tipo": safe_value(
                                        sensor,
                                        "t"
                                    ),
                                    "Unidad": safe_value(
                                        sensor,
                                        "m"
                                    ),
                                    "Parámetro": safe_value(
                                        sensor,
                                        "p"
                                    )
                                }
                            )

                        if sensor_rows:

                            st.dataframe(
                                pd.DataFrame(
                                    sensor_rows
                                ),
                                use_container_width=True,
                                hide_index=True
                            )

                        else:

                            st.info(
                                "No hay sensores configurados para esta unidad."
                            )

                        # ---------------------------------------------
                        # COUNTERS
                        # ---------------------------------------------

                        st.markdown(
                            "### 📈 Contadores"
                        )

                        counter_rows = [
                            {
                                "Contador": "Kilometraje",
                                "Valor": safe_value(
                                    detailed_item,
                                    "cnm"
                                )
                            },
                            {
                                "Contador": "Kilometraje (km)",
                                "Valor": safe_value(
                                    detailed_item,
                                    "cnm_km"
                                )
                            },
                            {
                                "Contador": "Horas de motor",
                                "Valor": safe_value(
                                    detailed_item,
                                    "cneh"
                                )
                            },
                            {
                                "Contador": "Tráfico GPRS acumulado",
                                "Valor": safe_value(
                                    detailed_item,
                                    "cnkb"
                                )
                            }
                        ]

                        st.dataframe(
                            pd.DataFrame(
                                counter_rows
                            ),
                            use_container_width=True,
                            hide_index=True
                        )

                        # ---------------------------------------------
                        # COMMANDS
                        # ---------------------------------------------

                        cmds = safe_dict(
                            detailed_item.get("cmds")
                        )

                        st.markdown(
                            "### 🎛️ Comandos disponibles"
                        )

                        command_rows = []

                        for command in cmds.values():

                            command = safe_dict(command)

                            command_rows.append(
                                {
                                    "ID": safe_value(
                                        command,
                                        "id"
                                    ),
                                    "Nombre": safe_value(
                                        command,
                                        "n"
                                    ),
                                    "Tipo": safe_value(
                                        command,
                                        "c"
                                    ),
                                    "Canal": safe_value(
                                        command,
                                        "t"
                                    ),
                                    "Parámetro": safe_value(
                                        command,
                                        "p"
                                    )
                                }
                            )

                        if command_rows:

                            st.dataframe(
                                pd.DataFrame(
                                    command_rows
                                ),
                                use_container_width=True,
                                hide_index=True
                            )

                        else:

                            st.info(
                                "No hay comandos disponibles para esta unidad."
                            )

                        # ---------------------------------------------
                        # TRIP DETECTOR
                        # ---------------------------------------------

                        rtd = safe_dict(
                            detailed_item.get("rtd")
                        )

                        st.markdown(
                            "### 🚦 Configuración del detector de viajes"
                        )

                        trip_rows = [
                            {
                                "Parámetro": "Tipo",
                                "Valor": safe_value(
                                    rtd,
                                    "type"
                                )
                            },
                            {
                                "Parámetro": "Corrección GPS",
                                "Valor": safe_value(
                                    rtd,
                                    "gpsCorrection"
                                )
                            },
                            {
                                "Parámetro": "Satélites mínimos",
                                "Valor": safe_value(
                                    rtd,
                                    "minSat"
                                )
                            },
                            {
                                "Parámetro": "Velocidad mínima",
                                "Valor": safe_value(
                                    rtd,
                                    "minMovingSpeed"
                                )
                            },
                            {
                                "Parámetro": "Tiempo mínimo de parada",
                                "Valor": safe_value(
                                    rtd,
                                    "minStayTime"
                                )
                            },
                            {
                                "Parámetro": "Distancia máxima entre mensajes",
                                "Valor": safe_value(
                                    rtd,
                                    "maxMessagesDistance"
                                )
                            },
                            {
                                "Parámetro": "Tiempo mínimo de viaje",
                                "Valor": safe_value(
                                    rtd,
                                    "minTripTime"
                                )
                            },
                            {
                                "Parámetro": "Distancia mínima de viaje",
                                "Valor": safe_value(
                                    rtd,
                                    "minTripDistance"
                                )
                            }
                        ]

                        st.dataframe(
                            pd.DataFrame(
                                trip_rows
                            ),
                            use_container_width=True,
                            hide_index=True
                        )

                        # ---------------------------------------------
                        # FUEL
                        # ---------------------------------------------

                        rfc = safe_dict(
                            detailed_item.get("rfc")
                        )

                        st.markdown(
                            "### ⛽ Configuración de combustible"
                        )

                        fuel_rows = [
                            {
                                "Sección": "General",
                                "Parámetro": "Tipo de cálculo",
                                "Valor": safe_value(
                                    rfc,
                                    "calcTypes"
                                )
                            }
                        ]

                        for section_key, section_name in [
                            (
                                "fuelLevelParams",
                                "Nivel de combustible"
                            ),
                            (
                                "fuelConsMath",
                                "Consumo matemático"
                            ),
                            (
                                "fuelConsRates",
                                "Tasas de consumo"
                            )
                        ]:

                            section_data = safe_dict(
                                rfc.get(
                                    section_key
                                )
                            )

                            for key, value in section_data.items():

                                fuel_rows.append(
                                    {
                                        "Sección": section_name,
                                        "Parámetro": key,
                                        "Valor": (
                                            ""
                                            if value is None
                                            else value
                                        )
                                    }
                                )

                        st.dataframe(
                            pd.DataFrame(
                                fuel_rows
                            ),
                            use_container_width=True,
                            hide_index=True
                        )

                        # ---------------------------------------------
                        # HEALTH CHECK
                        # ---------------------------------------------

                        hch = safe_dict(
                            detailed_item.get("hch")
                        )

                        st.markdown(
                            "### 🏥 Health Check"
                        )

                        health_rows = []

                        for check_name, check_data in hch.items():

                            check_data = safe_dict(
                                check_data
                            )

                            conditions = check_data.get(
                                "unhealthy_conditions",
                                []
                            )

                            if not isinstance(
                                conditions,
                                list
                            ):
                                conditions = []

                            condition_parts = []

                            for condition in conditions:

                                condition = safe_dict(
                                    condition
                                )

                                condition_text = (
                                    f"{safe_value(condition, 'type')} "
                                    f"{safe_value(condition, 'value')}"
                                ).strip()

                                if condition_text:
                                    condition_parts.append(
                                        condition_text
                                    )

                            health_rows.append(
                                {
                                    "Criterio": check_name,
                                    "Periodo": safe_value(
                                        check_data,
                                        "period"
                                    ),
                                    "Condición": "; ".join(
                                        condition_parts
                                    )
                                }
                            )

                        if health_rows:

                            st.dataframe(
                                pd.DataFrame(
                                    health_rows
                                ),
                                use_container_width=True,
                                hide_index=True
                            )

                        else:

                            st.info(
                                "No hay criterios de Health Check configurados para esta unidad."
                            )

                        # ---------------------------------------------
                        # MEDIA
                        # ---------------------------------------------

                        st.markdown(
                            "### 🎥 Video, retransmisión e imagen"
                        )

                        media_rows = [
                            {
                                "Elemento": "Video",
                                "Valor": safe_value(
                                    detailed_item,
                                    "vp"
                                )
                            },
                            {
                                "Elemento": "Retransmisión",
                                "Valor": safe_value(
                                    detailed_item,
                                    "retr"
                                )
                            },
                            {
                                "Elemento": "URI de imagen",
                                "Valor": safe_value(
                                    detailed_item,
                                    "uri"
                                )
                            },
                            {
                                "Elemento": "UGI",
                                "Valor": safe_value(
                                    detailed_item,
                                    "ugi"
                                )
                            }
                        ]

                        st.dataframe(
                            pd.DataFrame(
                                media_rows
                            ),
                            use_container_width=True,
                            hide_index=True
                        )


                        st.divider()

                        if st.button(
                            "Cerrar",
                            key="wialon_detail_close",
                            use_container_width=True
                        ):

                            st.session_state[
                                "wialon_detail_unit_id"
                            ] = None

                            st.rerun()

                    wialon_unit_detail_dialog()

        # =====================================================
        # MAPA
        # =====================================================

        with tab_wialon_mapa:

            st.header(
                "🗺️ Mapa GPS de Unidades Wialon"
            )

            if not units:

                st.warning(
                    "No hay unidades disponibles para mostrar en el mapa."
                )

            else:

                map_rows = []

                for unit in units:

                    position = get_unit_position(
                        unit
                    )

                    latitude = numeric_value(
                        position.get("y"),
                        None
                    )

                    longitude = numeric_value(
                        position.get("x"),
                        None
                    )

                    if (
                        latitude is None
                        or longitude is None
                    ):
                        continue

                    speed = get_unit_speed(
                        unit
                    )

                    map_rows.append(
                        {
                            "Unidad": safe_value(
                                unit,
                                "nm"
                            ),
                            "Latitud": latitude,
                            "Longitud": longitude,
                            "Velocidad": speed,
                            "Estado": (
                                "🟢 En Movimiento"
                                if speed > 0
                                else "🔴 Detenida"
                            ),
                            "Engine": get_unit_engine(
                                unit
                            ),
                            "Power": get_unit_power(
                                unit
                            ),
                            "Satélites": safe_value(
                                position,
                                "sc"
                            ),
                            "Hora": safe_value(
                                position,
                                "t"
                            )
                        }
                    )

                map_df = pd.DataFrame(
                    map_rows
                )

                if map_df.empty:

                    st.warning(
                        "No hay unidades con coordenadas válidas."
                    )

                else:

                    map_filter_1, map_filter_2 = st.columns(2)

                    with map_filter_1:

                        map_status = st.selectbox(
                            "Estado en mapa",
                            [
                                "Todas",
                                "🟢 En Movimiento",
                                "🔴 Detenida"
                            ],
                            key="wialon_map_status"
                        )

                    with map_filter_2:

                        map_unit = st.selectbox(
                            "Unidad en mapa",
                            [
                                "Todas"
                            ]
                            + sorted(
                                map_df[
                                    "Unidad"
                                ]
                                .astype(str)
                                .unique()
                                .tolist()
                            ),
                            key="wialon_map_unit"
                        )

                    display_map_df = map_df.copy()

                    if map_status == "🟢 En Movimiento":

                        display_map_df = display_map_df[
                            display_map_df["Velocidad"] > 0
                        ]

                    elif map_status == "🔴 Detenida":

                        display_map_df = display_map_df[
                            display_map_df["Velocidad"] <= 0
                        ]

                    if map_unit != "Todas":

                        display_map_df = display_map_df[
                            display_map_df["Unidad"].astype(str)
                            == map_unit
                        ]

                    if display_map_df.empty:

                        st.info(
                            "No hay unidades que coincidan con los filtros seleccionados."
                        )

                    else:

                        display_map_df["color"] = (
                            display_map_df["Velocidad"]
                            .apply(
                                lambda value:
                                [
                                    0,
                                    180,
                                    0
                                ]
                                if value > 0
                                else [
                                    220,
                                    0,
                                    0
                                ]
                            )
                        )

                        tooltip = {
                            "html": """
                                <b>{Unidad}</b><br/>
                                Estado: {Estado}<br/>
                                Velocidad: {Velocidad} km/h<br/>
                                Engine: {Engine}<br/>
                                Power: {Power}<br/>
                                Satélites: {Satélites}<br/>
                                Latitud: {Latitud}<br/>
                                Longitud: {Longitud}<br/>
                                Hora: {Hora}
                            """,
                            "style": {
                                "backgroundColor": "#111",
                                "color": "white"
                            }
                        }

                        layer = pdk.Layer(
                            "ScatterplotLayer",
                            data=display_map_df,
                            get_position=(
                                "[Longitud, Latitud]"
                            ),
                            get_fill_color="color",
                            radius_units="pixels",
                            get_radius=12,
                            radius_min_pixels=6,
                            radius_max_pixels=30,
                            pickable=True,
                            auto_highlight=True,
                            stroked=True,
                            filled=True,
                            line_width_min_pixels=2,
                            get_line_color=[
                                255,
                                255,
                                255
                            ]
                        )

                        center_lat = display_map_df[
                            "Latitud"
                        ].mean()

                        center_lon = display_map_df[
                            "Longitud"
                        ].mean()

                        view_state = pdk.ViewState(
                            latitude=center_lat,
                            longitude=center_lon,
                            zoom=5,
                            pitch=0
                        )

                        st.pydeck_chart(
                            pdk.Deck(
                                map_style=None,
                                initial_view_state=view_state,
                                layers=[layer],
                                tooltip=tooltip
                            ),
                            use_container_width=True
                        )

                        st.caption(
                            f"{len(display_map_df)} unidad(es) mostradas en el mapa."
                        )

        # =====================================================
        # HISTORIAL
        # =====================================================

        with tab_wialon_historial:

            st.header(
                "📈 Historial Wialon"
            )

            st.info(
                "La integración Wialon actual está obteniendo el estado "
                "actual de las unidades y su último mensaje. "
                "No se ha agregado una consulta histórica de viajes o "
                "mensajes, por lo que esta sección no inventa historial."
            )

            if units:

                history_rows = []

                for unit in units:

                    position = get_unit_position(
                        unit
                    )

                    message = get_unit_message(
                        unit
                    )

                    history_rows.append(
                        {
                            "Unidad": safe_value(
                                unit,
                                "nm"
                            ),
                            "ID Wialon": safe_value(
                                unit,
                                "id"
                            ),
                            "Hora Posición": safe_value(
                                position,
                                "t"
                            ),
                            "Latitud": safe_value(
                                position,
                                "y"
                            ),
                            "Longitud": safe_value(
                                position,
                                "x"
                            ),
                            "Velocidad": (
                                f"{get_unit_speed(unit):.1f} km/h"
                            ),
                            "Rumbo": safe_value(
                                position,
                                "c"
                            ),
                            "Altitud": safe_value(
                                position,
                                "z"
                            ),
                            "Satélites": safe_value(
                                position,
                                "sc"
                            ),
                            "Último Mensaje": safe_value(
                                message,
                                "t"
                            ),
                            "Registro Wialon": safe_value(
                                message,
                                "rt"
                            )
                        }
                    )

                history_df = pd.DataFrame(
                    history_rows
                )

                h1, h2 = st.columns(2)

                with h1:

                    history_unit = st.selectbox(
                        "Unidad",
                        ["Todas"]
                        + sorted(
                            history_df[
                                "Unidad"
                            ]
                            .astype(str)
                            .unique()
                            .tolist()
                        ),
                        key="wialon_history_unit"
                    )

                with h2:

                    history_status = st.selectbox(
                        "Estado",
                        [
                            "Todos",
                            "🟢 En Movimiento",
                            "🔴 Detenida"
                        ],
                        key="wialon_history_status"
                    )

                if history_unit != "Todas":

                    history_df = history_df[
                        history_df["Unidad"].astype(str)
                        == history_unit
                    ]

                if history_status == "🟢 En Movimiento":

                    history_df = history_df[
                        history_df["Velocidad"]
                        .str.replace(
                            " km/h",
                            "",
                            regex=False
                        )
                        .astype(float)
                        > 0
                    ]

                elif history_status == "🔴 Detenida":

                    history_df = history_df[
                        history_df["Velocidad"]
                        .str.replace(
                            " km/h",
                            "",
                            regex=False
                        )
                        .astype(float)
                        <= 0
                    ]

                st.dataframe(
                    history_df,
                    use_container_width=True,
                    height=500,
                    hide_index=True
                )

                history_buffer = io.BytesIO()

                with pd.ExcelWriter(
                    history_buffer,
                    engine="openpyxl"
                ) as writer:

                    history_df.to_excel(
                        writer,
                        index=False,
                        sheet_name="Ultimo Mensaje"
                    )

                history_buffer.seek(0)

                st.download_button(
                    label="💾 Descargar último estado",
                    data=history_buffer,
                    file_name="Wialon_Ultimo_Estado.xlsx",
                    mime=(
                        "application/"
                        "vnd.openxmlformats-officedocument."
                        "spreadsheetml.sheet"
                    ),
                    use_container_width=True,
                    key="wialon_history_download"
                )

        # =========================================================
        # INDEPENDENT TRAILER SECTION
        # =========================================================

        st.divider()

        st.header(
            "📦 Información de cajas / remolques"
        )

        if not trailer_catalog:

            st.info(
                "Wialon no devolvió cajas/remolques en los recursos disponibles."
            )

        else:

            # -----------------------------------------------------
            # TRAILER FILTERS
            # -----------------------------------------------------

            trailer_resources_names = sorted(
                {
                    str(
                        item.get(
                            "resource_name",
                            ""
                        )
                    )
                    for item in trailer_catalog
                    if item.get(
                        "resource_name"
                    )
                }
            )

            tf1, tf2 = st.columns(2)

            with tf1:

                selected_trailer_resource = st.selectbox(
                    "Recurso",
                    ["Todos"] + trailer_resources_names,
                    key="wialon_trailer_resource"
                )

            trailer_filtered = trailer_catalog

            if selected_trailer_resource != "Todos":

                trailer_filtered = [
                    item
                    for item in trailer_filtered
                    if str(
                        item.get(
                            "resource_name",
                            ""
                        )
                    ) == selected_trailer_resource
                ]

            with tf2:

                selected_trailer = st.selectbox(
                    "Selecciona una caja / remolque",
                    trailer_filtered,
                    index=0,
                    format_func=lambda item: str(
                        item.get(
                            "trailer_name",
                            ""
                        )
                    ),
                    key="wialon_selected_trailer"
                )

            st.caption(
                f"{len(trailer_filtered)} caja(s) encontradas"
            )

            if selected_trailer:

                st.subheader(
                    "📋 Información de la caja / remolque"
                )

                trailer = safe_dict(
                    selected_trailer.get("raw")
                )

                trailer_rows = [
                    {
                        "Campo": "Nombre",
                        "Valor": selected_trailer.get(
                            "trailer_name",
                            ""
                        )
                    },
                    {
                        "Campo": "ID Caja / Remolque",
                        "Valor": selected_trailer.get(
                            "trailer_id",
                            ""
                        )
                    },
                    {
                        "Campo": "ID Recurso",
                        "Valor": selected_trailer.get(
                            "resource_id",
                            ""
                        )
                    },
                    {
                        "Campo": "Recurso",
                        "Valor": selected_trailer.get(
                            "resource_name",
                            ""
                        )
                    }
                ]

                for key, value in trailer.items():

                    if key in (
                        "id",
                        "nm",
                        "name"
                    ):
                        continue

                    trailer_rows.append(
                        {
                            "Campo": str(key),
                            "Valor": (
                                ""
                                if value is None
                                else value
                            )
                        }
                    )

                trailer_df = pd.DataFrame(
                    trailer_rows
                )

                st.dataframe(
                    trailer_df,
                    use_container_width=True,
                    height=450,
                    hide_index=True
                )

                trailer_buffer = io.BytesIO()

                with pd.ExcelWriter(
                    trailer_buffer,
                    engine="openpyxl"
                ) as writer:

                    trailer_df.to_excel(
                        writer,
                        index=False,
                        sheet_name="Caja_Remolque"
                    )

                trailer_buffer.seek(0)

                st.download_button(
                    label="💾 Descargar información de caja",
                    data=trailer_buffer,
                    file_name=(
                        "Wialon_Caja_"
                        f"{selected_trailer.get('trailer_name', 'remolque')}.xlsx"
                    ),
                    mime=(
                        "application/"
                        "vnd.openxmlformats-officedocument."
                        "spreadsheetml.sheet"
                    ),
                    use_container_width=True,
                    key="wialon_trailer_download"
                )

                st.divider()

                trailer_k1, trailer_k2, trailer_k3 = st.columns(3)

                trailer_k1.metric(
                    "ID Caja",
                    selected_trailer.get(
                        "trailer_id",
                        "-"
                    )
                )

                trailer_k2.metric(
                    "ID Recurso",
                    selected_trailer.get(
                        "resource_id",
                        "-"
                    )
                )

                trailer_k3.metric(
                    "Campos recibidos",
                    len(trailer)
                )

        # =========================================================
        # FULL WIALON UNIT TABLE
        # =========================================================

        st.divider()

        st.subheader(
            "🚛 Tabla General de Flotilla Wialon"
        )

        if units:

            full_rows = []

            for unit in units:

                position = get_unit_position(
                    unit
                )

                message = get_unit_message(
                    unit
                )

                params = get_unit_params(
                    unit
                )

                full_rows.append(
                    {
                        "ID Wialon": safe_value(
                            unit,
                            "id"
                        ),
                        "Unidad": safe_value(
                            unit,
                            "nm"
                        ),
                        "Clase": safe_value(
                            unit,
                            "cls"
                        ),
                        "Sistema de Medición": safe_value(
                            unit,
                            "mu"
                        ),
                        "Hora Posición": safe_value(
                            position,
                            "t"
                        ),
                        "Latitud": safe_value(
                            position,
                            "y"
                        ),
                        "Longitud": safe_value(
                            position,
                            "x"
                        ),
                        "Rumbo": safe_value(
                            position,
                            "c"
                        ),
                        "Altitud": safe_value(
                            position,
                            "z"
                        ),
                        "Velocidad": safe_value(
                            position,
                            "s"
                        ),
                        "Satélites": safe_value(
                            position,
                            "sc"
                        ),
                        "Hora Último Mensaje": safe_value(
                            message,
                            "t"
                        ),
                        "Tipo Mensaje": safe_value(
                            message,
                            "tp"
                        ),
                        "Hora Registro Wialon": safe_value(
                            message,
                            "rt"
                        ),
                        "Entradas Digitales": safe_value(
                            message,
                            "i"
                        ),
                        "HDOP": safe_value(
                            params,
                            "hdop"
                        ),
                        "Señal GSM": safe_value(
                            params,
                            "gsm_signal"
                        ),
                        "Power": safe_value(
                            params,
                            "power"
                        ),
                        "Batería": safe_value(
                            params,
                            "battery"
                        ),
                        "Engine On": safe_value(
                            params,
                            "engine_on"
                        ),
                        "Tiempo Idle": safe_value(
                            params,
                            "idling_time"
                        ),
                        "Velocidad Máxima": safe_value(
                            params,
                            "max_speed"
                        ),
                        "Eventos Frenado": safe_value(
                            params,
                            "braking_events"
                        ),
                        "Frenado Severo": safe_value(
                            params,
                            "ext_hrsh_braking"
                        ),
                        "Frenado Brusco": safe_value(
                            params,
                            "harsh_braking"
                        ),
                        "Aceleración Brusca": safe_value(
                            params,
                            "harsh_acceleration"
                        ),
                        "Overspeed": safe_value(
                            params,
                            "overspeed"
                        ),
                        "Temp Sensor 0": safe_value(
                            params,
                            "temp_sens_0"
                        ),
                        "Temp Sensor 1": safe_value(
                            params,
                            "temp_sens_1"
                        ),
                        "UACL": safe_value(
                            unit,
                            "uacl"
                        )
                    }
                )

            full_unit_df = pd.DataFrame(
                full_rows
            )

            st.dataframe(
                full_unit_df,
                use_container_width=True,
                height=600,
                hide_index=True
            )

            full_buffer = io.BytesIO()

            with pd.ExcelWriter(
                full_buffer,
                engine="openpyxl"
            ) as writer:

                full_unit_df.to_excel(
                    writer,
                    index=False,
                    sheet_name="Wialon Unidades"
                )

            full_buffer.seek(0)

            st.download_button(
                label="💾 Descargar Tabla General Wialon",
                data=full_buffer,
                file_name="Wialon_Unidades.xlsx",
                mime=(
                    "application/"
                    "vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                ),
                use_container_width=True,
                key="wialon_full_table_download"
            )

        # =========================================================
        # LOGOUT
        # =========================================================

        try:

            wialon_request(
                "core/logout",
                {},
                sid=sid
            )

        except Exception:
            pass

    except Exception as e:

        st.error(
            f"❌ Error consultando Wialon: {e}"
        )