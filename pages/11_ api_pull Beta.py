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

APP_CHANNEL = "BETA"
#APP_CHANNEL = "RELEASE"

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

    # ---------------------------------------------------------
    # WIALON TOKEN
    # ---------------------------------------------------------

    WIALON_TOKEN = (
        "80116688b2812ec4b012e91c4783618122D6783187118B551FDD06B30949543E37B40683"
    )

    # ---------------------------------------------------------
    # WIALON API REQUEST
    # ---------------------------------------------------------

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

    # =========================================================
    # WIALON CONNECTION
    # =========================================================

    try:

        # -----------------------------------------------------
        # LOGIN
        # -----------------------------------------------------

        login_response = wialon_request(
            "token/login",
            {
                "token": WIALON_TOKEN,
                "fl": 15
            }
        )

        sid = login_response.get(
            "eid"
        )

        if not sid:

            st.error(
                "❌ Wialon no devolvió un session ID."
            )

            st.stop()

        # -----------------------------------------------------
        # USER INFORMATION
        # -----------------------------------------------------

        user_response = wialon_request(
            "core/get_user_data",
            {},
            sid=sid
        )

        # -----------------------------------------------------
        # GET ALL ACCESSIBLE UNITS
        # -----------------------------------------------------

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

        # =====================================================
        # BUILD UNITS TABLE
        # =====================================================

        units = units_response.get(
            "items",
            []
        )

        if units:

            rows = []

            for unit in units:

                # -------------------------------------------------
                # LAST POSITION
                # -------------------------------------------------

                position = (
                    unit.get(
                        "pos",
                        {}
                    )
                    or {}
                )

                # -------------------------------------------------
                # LAST MESSAGE
                # -------------------------------------------------

                last_message = (
                    unit.get(
                        "lmsg",
                        {}
                    )
                    or {}
                )

                # -------------------------------------------------
                # DEVICE PARAMETERS
                # -------------------------------------------------

                params = (
                    last_message.get(
                        "p",
                        {}
                    )
                    or {}
                )

                # -------------------------------------------------
                # TABLE ROW
                # -------------------------------------------------

                rows.append(
                    {

                        # -----------------------------------------
                        # UNIT
                        # -----------------------------------------

                        "ID Wialon": unit.get(
                            "id",
                            ""
                        ),

                        "Unidad": unit.get(
                            "nm",
                            ""
                        ),

                        "Clase": unit.get(
                            "cls",
                            ""
                        ),

                        "Sistema de Medición": unit.get(
                            "mu",
                            ""
                        ),

                        # -----------------------------------------
                        # POSITION
                        # -----------------------------------------

                        "Hora Posición": position.get(
                            "t",
                            ""
                        ),

                        "Latitud": position.get(
                            "y",
                            ""
                        ),

                        "Longitud": position.get(
                            "x",
                            ""
                        ),

                        "Rumbo": position.get(
                            "c",
                            ""
                        ),

                        "Altitud": position.get(
                            "z",
                            ""
                        ),

                        "Velocidad": position.get(
                            "s",
                            ""
                        ),

                        "Satélites": position.get(
                            "sc",
                            ""
                        ),

                        # -----------------------------------------
                        # LAST MESSAGE
                        # -----------------------------------------

                        "Hora Último Mensaje": last_message.get(
                            "t",
                            ""
                        ),

                        "Tipo Mensaje": last_message.get(
                            "tp",
                            ""
                        ),

                        "Hora Registro Wialon": last_message.get(
                            "rt",
                            ""
                        ),

                        "Entradas Digitales": last_message.get(
                            "i",
                            ""
                        ),

                        # -----------------------------------------
                        # TELEMETRY
                        # -----------------------------------------

                        "HDOP": params.get(
                            "hdop",
                            ""
                        ),

                        "Señal GSM": params.get(
                            "gsm_signal",
                            ""
                        ),

                        "Power": params.get(
                            "power",
                            ""
                        ),

                        "Batería": params.get(
                            "battery",
                            ""
                        ),

                        "Engine On": params.get(
                            "engine_on",
                            ""
                        ),

                        "Tiempo Idle": params.get(
                            "idling_time",
                            ""
                        ),

                        "Velocidad Máxima": params.get(
                            "max_speed",
                            ""
                        ),

                        "Eventos Frenado": params.get(
                            "braking_events",
                            ""
                        ),

                        "Frenado Severo": params.get(
                            "ext_hrsh_braking",
                            ""
                        ),

                        "Frenado Brusco": params.get(
                            "harsh_braking",
                            ""
                        ),

                        "Aceleración Brusca": params.get(
                            "harsh_acceleration",
                            ""
                        ),

                        "Overspeed": params.get(
                            "overspeed",
                            ""
                        ),

                        "Temp Sensor 0": params.get(
                            "temp_sens_0",
                            ""
                        ),

                        "Temp Sensor 1": params.get(
                            "temp_sens_1",
                            ""
                        ),

                        # -----------------------------------------
                        # ACCESS
                        # -----------------------------------------

                        "UACL": unit.get(
                            "uacl",
                            ""
                        ),
                    }
                )

            # =====================================================
            # MAIN DATAFRAME
            # =====================================================

            units_df = pd.DataFrame(
                rows
            )

            st.dataframe(
                units_df,
                use_container_width=True,
                height=600,
                hide_index=True
            )

            # =====================================================
            # DOWNLOAD MAIN WIALON TABLE
            # =====================================================

            wialon_main_excel = io.BytesIO()

            with pd.ExcelWriter(
                wialon_main_excel,
                engine="openpyxl"
            ) as writer:

                units_df.to_excel(
                    writer,
                    index=False,
                    sheet_name="Wialon Unidades"
                )

            wialon_main_excel.seek(0)

            st.download_button(
                label="📥 Descargar tabla Wialon",
                data=wialon_main_excel,
                file_name="wialon_unidades.xlsx",
                mime=(
                    "application/vnd.openxmlformats-"
                    "officedocument.spreadsheetml.sheet"
                ),
                use_container_width=True,
                key="download_wialon_main"
            )

            # =====================================================
            # DETAILED UNIT INFORMATION
            # =====================================================

            st.divider()

            st.subheader(
                "🔎 Información detallada de unidad"
            )

            # -----------------------------------------------------
            # UNIT SELECTOR
            # -----------------------------------------------------

            unit_options = [
                unit.get(
                    "nm",
                    ""
                )
                for unit in units
                if unit.get("nm")
            ]

            selected_unit_name = st.selectbox(
                "Selecciona una unidad",
                unit_options,
                index=0,
                key="wialon_selected_unit"
            )

            # -----------------------------------------------------
            # FIND SELECTED UNIT
            # -----------------------------------------------------

            selected_unit = next(
                (
                    unit
                    for unit in units
                    if unit.get("nm") == selected_unit_name
                ),
                None
            )

            if selected_unit:

                selected_unit_id = selected_unit.get(
                    "id"
                )

                st.caption(
                    f"ID Wialon: {selected_unit_id}"
                )

                # =================================================
                # REQUEST ALL AVAILABLE UNIT INFORMATION
                # =================================================

                detailed_unit_response = wialon_request(
                    "core/search_item",
                    {
                        "id": selected_unit_id,
                        "flags": 4611686018427387903
                    },
                    sid=sid
                )

                # -------------------------------------------------
                # DETAIL DOWNLOAD STORAGE
                # -------------------------------------------------

                detail_download_tables = {}

                # -------------------------------------------------
                # RESPONSE DATA
                # -------------------------------------------------

                if detailed_unit_response:

                    detailed_unit = (
                        detailed_unit_response
                        if isinstance(
                            detailed_unit_response,
                            dict
                        )
                        else {}
                    )

                    # =================================================
                    # 1. IDENTIFICACIÓN GENERAL
                    # =================================================

                    st.markdown(
                        "### 🆔 Identificación general"
                    )

                    general_rows = [
                        {
                            "Campo": "Nombre",
                            "Valor": detailed_unit.get(
                                "nm",
                                ""
                            )
                        },
                        {
                            "Campo": "ID Wialon",
                            "Valor": detailed_unit.get(
                                "id",
                                ""
                            )
                        },
                        {
                            "Campo": "Clase",
                            "Valor": detailed_unit.get(
                                "cls",
                                ""
                            )
                        },
                        {
                            "Campo": "Sistema de medición",
                            "Valor": detailed_unit.get(
                                "mu",
                                ""
                            )
                        },
                        {
                            "Campo": "Creación",
                            "Valor": detailed_unit.get(
                                "crt",
                                ""
                            )
                        },
                        {
                            "Campo": "Activación",
                            "Valor": detailed_unit.get(
                                "bact",
                                ""
                            )
                        },
                        {
                            "Campo": "Grupo / Cuenta",
                            "Valor": detailed_unit.get(
                                "gd",
                                ""
                            )
                        },
                        {
                            "Campo": "UACL",
                            "Valor": detailed_unit.get(
                                "uacl",
                                ""
                            )
                        },
                    ]

                    general_df = pd.DataFrame(
                        general_rows
                    )

                    st.dataframe(
                        general_df,
                        use_container_width=True,
                        hide_index=True
                    )

                    detail_download_tables[
                        "Identificacion General"
                    ] = general_df

                    # =================================================
                    # 2. INFORMACIÓN DEL VEHÍCULO
                    # =================================================

                    st.markdown(
                        "### 🚛 Información del vehículo"
                    )

                    vehicle_fields = (
                        detailed_unit.get(
                            "flds",
                            {}
                        )
                        or {}
                    )

                    vehicle_profile = (
                        detailed_unit.get(
                            "pflds",
                            {}
                        )
                        or {}
                    )

                    vehicle_rows = [
                        {
                            "Campo": "Placa",
                            "Valor": vehicle_fields.get(
                                "PLACA",
                                vehicle_profile.get(
                                    "registration_plate",
                                    ""
                                )
                            )
                        },
                        {
                            "Campo": "VIN",
                            "Valor": vehicle_fields.get(
                                "VIN",
                                vehicle_profile.get(
                                    "vin",
                                    ""
                                )
                            )
                        },
                        {
                            "Campo": "Modelo",
                            "Valor": vehicle_fields.get(
                                "MODELO",
                                vehicle_profile.get(
                                    "model",
                                    ""
                                )
                            )
                        },
                        {
                            "Campo": "Unidad",
                            "Valor": vehicle_fields.get(
                                "UNIDAD",
                                vehicle_profile.get(
                                    "vehicle_type",
                                    ""
                                )
                            )
                        },
                        {
                            "Campo": "Año",
                            "Valor": vehicle_profile.get(
                                "year",
                                ""
                            )
                        },
                        {
                            "Campo": "Marca",
                            "Valor": vehicle_profile.get(
                                "brand",
                                ""
                            )
                        },
                        {
                            "Campo": "Tipo de vehículo",
                            "Valor": vehicle_profile.get(
                                "vehicle_type",
                                ""
                            )
                        },
                        {
                            "Campo": "Clase de vehículo",
                            "Valor": vehicle_profile.get(
                                "vehicle_class",
                                ""
                            )
                        },
                    ]

                    vehicle_df = pd.DataFrame(
                        vehicle_rows
                    )

                    st.dataframe(
                        vehicle_df,
                        use_container_width=True,
                        hide_index=True
                    )

                    detail_download_tables[
                        "Informacion Vehiculo"
                    ] = vehicle_df

                    # =================================================
                    # 3. POSICIÓN ACTUAL
                    # =================================================

                    st.markdown(
                        "### 📍 Posición actual"
                    )

                    current_position = (
                        detailed_unit.get(
                            "pos",
                            {}
                        )
                        or {}
                    )

                    position_rows = [
                        {
                            "Campo": "Timestamp",
                            "Valor": current_position.get(
                                "t",
                                ""
                            )
                        },
                        {
                            "Campo": "Latitud",
                            "Valor": current_position.get(
                                "y",
                                ""
                            )
                        },
                        {
                            "Campo": "Longitud",
                            "Valor": current_position.get(
                                "x",
                                ""
                            )
                        },
                        {
                            "Campo": "Rumbo",
                            "Valor": current_position.get(
                                "c",
                                ""
                            )
                        },
                        {
                            "Campo": "Altitud",
                            "Valor": current_position.get(
                                "z",
                                ""
                            )
                        },
                        {
                            "Campo": "Velocidad",
                            "Valor": current_position.get(
                                "s",
                                ""
                            )
                        },
                        {
                            "Campo": "Satélites",
                            "Valor": current_position.get(
                                "sc",
                                ""
                            )
                        },
                        {
                            "Campo": "Flags",
                            "Valor": current_position.get(
                                "f",
                                ""
                            )
                        },
                        {
                            "Campo": "Localización",
                            "Valor": current_position.get(
                                "lc",
                                ""
                            )
                        },
                    ]

                    position_df = pd.DataFrame(
                        position_rows
                    )

                    st.dataframe(
                        position_df,
                        use_container_width=True,
                        hide_index=True
                    )

                    detail_download_tables[
                        "Posicion Actual"
                    ] = position_df

                    # =================================================
                    # 4. ESTADO DE CONEXIÓN
                    # =================================================

                    st.markdown(
                        "### 📡 Estado de conexión"
                    )

                    network_status = (
                        detailed_unit.get(
                            "netconn",
                            {}
                        )
                        or {}
                    )

                    connection_rows = [
                        {
                            "Campo": "Conexión activa",
                            "Valor": network_status.get(
                                "1",
                                network_status.get(
                                    "netconn",
                                    ""
                                )
                            )
                        },
                        {
                            "Campo": "Activa",
                            "Valor": detailed_unit.get(
                                "act",
                                ""
                            )
                        },
                        {
                            "Campo": "Razón de desactivación",
                            "Valor": detailed_unit.get(
                                "act_reason",
                                ""
                            )
                        },
                        {
                            "Campo": "Tiempo de desactivación",
                            "Valor": detailed_unit.get(
                                "dactt",
                                ""
                            )
                        },
                    ]

                    connection_df = pd.DataFrame(
                        connection_rows
                    )

                    st.dataframe(
                        connection_df,
                        use_container_width=True,
                        hide_index=True
                    )

                    detail_download_tables[
                        "Estado Conexion"
                    ] = connection_df

                    # =================================================
                    # 5. SENSORES CONFIGURADOS
                    # =================================================

                    st.markdown(
                        "### 🌡️ Sensores configurados"
                    )

                    sensors = (
                        detailed_unit.get(
                            "sens",
                            []
                        )
                        or []
                    )

                    sensor_rows = []

                    for sensor in sensors:

                        sensor_rows.append(
                            {
                                "ID": sensor.get(
                                    "id",
                                    ""
                                ),
                                "Nombre": sensor.get(
                                    "n",
                                    sensor.get(
                                        "name",
                                        ""
                                    )
                                ),
                                "Tipo": sensor.get(
                                    "t",
                                    ""
                                ),
                                "Parámetro": sensor.get(
                                    "p",
                                    ""
                                ),
                                "Unidad": sensor.get(
                                    "m",
                                    ""
                                ),
                                "Posición": sensor.get(
                                    "pos",
                                    ""
                                ),
                                "Modo": sensor.get(
                                    "f",
                                    ""
                                ),
                                "Configuración": json.dumps(
                                    sensor.get(
                                        "config",
                                        {}
                                    ),
                                    ensure_ascii=False
                                )
                            }
                        )

                    if sensor_rows:

                        sensors_df = pd.DataFrame(
                            sensor_rows
                        )

                        st.dataframe(
                            sensors_df,
                            use_container_width=True,
                            hide_index=True
                        )

                        detail_download_tables[
                            "Sensores"
                        ] = sensors_df

                    else:

                        st.info(
                            "No hay sensores configurados."
                        )

                    # =================================================
                    # 6. CONTADORES
                    # =================================================

                    st.markdown(
                        "### 📊 Contadores"
                    )

                    counter_rows = [
                        {
                            "Contador": "Kilometraje",
                            "Valor": detailed_unit.get(
                                "cnm_km",
                                detailed_unit.get(
                                    "cnm",
                                    ""
                                )
                            )
                        },
                        {
                            "Contador": "Horas de motor",
                            "Valor": detailed_unit.get(
                                "cneh",
                                ""
                            )
                        },
                        {
                            "Contador": "Kilobytes",
                            "Valor": detailed_unit.get(
                                "cnkb",
                                ""
                            )
                        },
                        {
                            "Contador": "cfl",
                            "Valor": detailed_unit.get(
                                "cfl",
                                ""
                            )
                        },
                    ]

                    counter_df = pd.DataFrame(
                        counter_rows
                    )

                    st.dataframe(
                        counter_df,
                        use_container_width=True,
                        hide_index=True
                    )

                    detail_download_tables[
                        "Contadores"
                    ] = counter_df

                    # =================================================
                    # 7. CONFIGURACIÓN DEL DETECTOR DE VIAJES
                    # =================================================

                    st.markdown(
                        "### 🛣️ Configuración del detector de viajes"
                    )

                    trip_detector = (
                        detailed_unit.get(
                            "rtd",
                            {}
                        )
                        or {}
                    )

                    trip_rows = [
                        {
                            "Parámetro": "Tipo",
                            "Valor": trip_detector.get(
                                "type",
                                ""
                            )
                        },
                        {
                            "Parámetro": "GPS Correction",
                            "Valor": trip_detector.get(
                                "gpsCorrection",
                                ""
                            )
                        },
                        {
                            "Parámetro": "Satélites mínimos",
                            "Valor": trip_detector.get(
                                "minSat",
                                ""
                            )
                        },
                        {
                            "Parámetro": "Velocidad mínima movimiento",
                            "Valor": trip_detector.get(
                                "minMovingSpeed",
                                ""
                            )
                        },
                        {
                            "Parámetro": "Tiempo mínimo de estancia",
                            "Valor": trip_detector.get(
                                "minStayTime",
                                ""
                            )
                        },
                        {
                            "Parámetro": "Distancia máxima entre mensajes",
                            "Valor": trip_detector.get(
                                "maxMessagesDistance",
                                ""
                            )
                        },
                        {
                            "Parámetro": "Tiempo mínimo de viaje",
                            "Valor": trip_detector.get(
                                "minTripTime",
                                ""
                            )
                        },
                        {
                            "Parámetro": "Distancia mínima de viaje",
                            "Valor": trip_detector.get(
                                "minTripDistance",
                                ""
                            )
                        },
                    ]

                    trip_df = pd.DataFrame(
                        trip_rows
                    )

                    st.dataframe(
                        trip_df,
                        use_container_width=True,
                        hide_index=True
                    )

                    detail_download_tables[
                        "Detector Viajes"
                    ] = trip_df

                    # =================================================
                    # 8. CONFIGURACIÓN DE COMBUSTIBLE
                    # =================================================

                    st.markdown(
                        "### ⛽ Configuración de combustible"
                    )

                    fuel_config = (
                        detailed_unit.get(
                            "rfc",
                            {}
                        )
                        or {}
                    )

                    fuel_rows = []

                    for section_name, section_data in fuel_config.items():

                        if isinstance(
                            section_data,
                            dict
                        ):

                            for parameter, value in section_data.items():

                                fuel_rows.append(
                                    {
                                        "Sección": section_name,
                                        "Parámetro": parameter,
                                        "Valor": value
                                    }
                                )

                        else:

                            fuel_rows.append(
                                {
                                    "Sección": "",
                                    "Parámetro": section_name,
                                    "Valor": section_data
                                }
                            )

                    if fuel_rows:

                        fuel_df = pd.DataFrame(
                            fuel_rows
                        )

                        st.dataframe(
                            fuel_df,
                            use_container_width=True,
                            hide_index=True
                        )

                        detail_download_tables[
                            "Combustible"
                        ] = fuel_df

                    else:

                        st.info(
                            "No hay configuración de combustible disponible."
                        )

                    # =================================================
                    # 9. HEALTH CHECK
                    # =================================================

                    st.markdown(
                        "### 🩺 Health Check"
                    )

                    health_check = (
                        detailed_unit.get(
                            "hch",
                            {}
                        )
                        or {}
                    )

                    health_rows = []

                    for condition, condition_data in health_check.items():

                        if isinstance(
                            condition_data,
                            dict
                        ):

                            health_rows.append(
                                {
                                    "Condición": condition,
                                    "Periodo": condition_data.get(
                                        "period",
                                        ""
                                    ),
                                    "Valor": condition_data.get(
                                        "value",
                                        condition_data.get(
                                            "threshold",
                                            ""
                                        )
                                    ),
                                    "Estado": condition_data.get(
                                        "status",
                                        ""
                                    )
                                }
                            )

                        else:

                            health_rows.append(
                                {
                                    "Condición": condition,
                                    "Periodo": "",
                                    "Valor": condition_data,
                                    "Estado": ""
                                }
                            )

                    if health_rows:

                        health_df = pd.DataFrame(
                            health_rows
                        )

                        st.dataframe(
                            health_df,
                            use_container_width=True,
                            hide_index=True
                        )

                        detail_download_tables[
                            "Health Check"
                        ] = health_df

                    else:

                        st.info(
                            "No hay configuración de Health Check disponible."
                        )

                    # =================================================
                    # 10. VIDEO / RETRANSMISIÓN / IMAGEN
                    # =================================================

                    st.markdown(
                        "### 🎥 Video, retransmisión e imagen"
                    )

                    media_rows = [
                        {
                            "Campo": "Video",
                            "Valor": json.dumps(
                                detailed_unit.get(
                                    "si",
                                    {}
                                ),
                                ensure_ascii=False
                            )
                        },
                        {
                            "Campo": "Retransmisión",
                            "Valor": json.dumps(
                                detailed_unit.get(
                                    "retr",
                                    {},
                                ),
                                ensure_ascii=False
                            )
                        },
                        {
                            "Campo": "URI imagen",
                            "Valor": detailed_unit.get(
                                "uri",
                                ""
                            )
                        },
                        {
                            "Campo": "UGI",
                            "Valor": detailed_unit.get(
                                "ugi",
                                ""
                            )
                        },
                    ]

                    media_df = pd.DataFrame(
                        media_rows
                    )

                    st.dataframe(
                        media_df,
                        use_container_width=True,
                        hide_index=True
                    )

                    detail_download_tables[
                        "Media"
                    ] = media_df

                    # =================================================
                    # DOWNLOAD DETAILED INFORMATION
                    # =================================================

                    st.divider()

                    safe_unit_name = re.sub(
                        r'[\\/*?:"<>|]',
                        "_",
                        str(selected_unit_name)
                    ).strip()

                    if not safe_unit_name:

                        safe_unit_name = str(
                            selected_unit_id
                        )

                    detailed_excel = io.BytesIO()

                    with pd.ExcelWriter(
                        detailed_excel,
                        engine="openpyxl"
                    ) as writer:

                        for (
                            sheet_name,
                            dataframe
                        ) in detail_download_tables.items():

                            safe_sheet_name = re.sub(
                                r'[\[\]:*?/\\]',
                                "_",
                                str(sheet_name)
                            )[:31]

                            dataframe.to_excel(
                                writer,
                                index=False,
                                sheet_name=safe_sheet_name
                            )

                    detailed_excel.seek(0)

                    st.download_button(
                        label="📥 Descargar información detallada",
                        data=detailed_excel,
                        file_name=(
                            f"wialon_detalle_{safe_unit_name}.xlsx"
                        ),
                        mime=(
                            "application/vnd.openxmlformats-"
                            "officedocument.spreadsheetml.sheet"
                        ),
                        use_container_width=True,
                        key=(
                            f"download_wialon_detail_"
                            f"{selected_unit_id}"
                        )
                    )

                else:

                    st.warning(
                        "Wialon no devolvió información detallada "
                        "para la unidad seleccionada."
                    )

        else:

            st.warning(
                "Wialon respondió correctamente, "
                "pero no devolvió unidades."
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