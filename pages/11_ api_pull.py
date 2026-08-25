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
        "Rastreador y Seguimiento GPS de Unidades BETA"
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


st.title("🛰️ Rastreador y Seguimiento GPS de Unidades")


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

    response = requests.get(
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
# KPI DASHBOARD
# =========================================================

with tab_dashboard:

    if not df.empty:

        st.header("📊 Dashboard Operativo GPS")

        # =========================================
        # WORKING COPY
        # =========================================

        dashboard_df = df.copy()

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

            map_unit_options = sorted(
                map_df["label"]
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
                df["label"]
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

            start_str = start_date.strftime(
                "%m/%d/%Y"
            )

            end_str = end_date.strftime(
                "%m/%d/%Y"
            )

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

                trip_df = activity_df[
                    activity_df["trip_type"] == "T"
                ].copy()

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

                                if "trip_type" not in fleet_activity_df.columns:

                                    return {
                                        "unit": fleet_unit,
                                        "trip_df": pd.DataFrame(),
                                        "error": None
                                    }

                                fleet_trip_df = (
                                    fleet_activity_df[
                                        fleet_activity_df[
                                            "trip_type"
                                        ] == "T"
                                    ].copy()
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