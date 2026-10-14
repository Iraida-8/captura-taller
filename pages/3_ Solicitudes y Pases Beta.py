import streamlit as st

import pandas as pd

from supabase import create_client

from datetime import datetime, date, timezone

from auth import require_login, require_access

from pages.css import load_css

import re

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

# Security gates

# =================================

require_login()

# -------------------------------

# RELEASE GATE

# -------------------------------

user = st.session_state.user

access = user.get("access", [])

role = (user.get("role") or "").lower()

require_access("pase_taller")

# =================================

# Page configuration

# =================================

st.set_page_config(

    page_title=(

        "Solicitudes y Pases BETA"

        if APP_CHANNEL.upper() == "BETA"

        else "Solicitudes y Pases"

    ),

    layout="wide"

)

# -------------------------------

# PAGE STYLE

# -------------------------------

load_css()

# -------------------------------

# AUDIT

# -------------------------------

def log_activity(action, page):

    try:

        supabase.table("user_activity_log").insert({

            "user_id": user.get("id"),

            "user_name": user.get("name"),

            "login_counter": st.session_state.get("login_counter"),

            "action": action,

            "page": page,

        }).execute()

    except Exception as e:

        print(e)

# =================================

# Navigation

# =================================

st.write("")

if st.button("⬅ Volver al Dashboard"):

    st.switch_page(DASHBOARD_PAGE)

st.divider()

# =================================

# MODULES

# =================================

has_pases = "pase_taller" in access

has_bonos = "bonos_operador" in access

if has_pases and has_bonos:

    tab_pases, tab_bonos = st.tabs([

        "🛠️ Captura Pase de Taller",

        "💰 Bono de Operadores",

    ])

elif has_pases:

    tab_pases = st.container()

elif has_bonos:

    tab_bonos = st.container()

# =================================

# CAPTURA PASE DE TALLER

# =================================

if has_pases:

    with tab_pases:

        # =================================

        # SUPABASE CONFIGURATION

        # =================================

        @st.cache_resource

        def get_supabase():

            return create_client(

                st.secrets["SUPABASE_URL"],

                st.secrets["SUPABASE_SERVICE_KEY"]

            )

        supabase = get_supabase()

        @st.cache_data(ttl=3600)

        def cargar_unidades_supabase(empresa_codigo):

            response = (

                supabase.table("vehicle_units")

                .select("*")

                .eq("empresa", empresa_codigo)

                .execute()

            )

            df = pd.DataFrame(response.data)

            if df.empty:

                return df

            df["unidad"] = df["unidad"].astype(str).str.strip()

            df["tipo_unidad"] = df["tipo_unidad"].astype(str).str.upper().str.strip()

            return df

        # =================================

        # SUPABASE TABLE MAP

        # =================================

        TABLE_MAP = {

            "IGLOO TRANSPORT": "IGLOO",

            "LINCOLN FREIGHT": "LINCOLN",

            "PICUS": "PICUS",

            "SET FREIGHT INTERNATIONAL": "SFI",

            "SET LOGIS PLUS": "SLP"

        }

        EMPRESA_CODIGOS = {

            "IGLOO TRANSPORT": "IGT",

            "LINCOLN FREIGHT": "LIN",

            "PICUS": "PIC",

            "SET FREIGHT INTERNATIONAL": "SET",

            "SET LOGIS PLUS": "SLP"

        }

        EMPRESAS = list(TABLE_MAP.keys())

        ACCESS_EMPRESA_MAP = {

            "igloo": "IGLOO TRANSPORT",

            "lincoln": "LINCOLN FREIGHT",

            "picus": "PICUS",

            "setfreight": "SET FREIGHT INTERNATIONAL",

            "setlogis": "SET LOGIS PLUS",

        }

        # =================================

        # Check duplicate unit in last 24h (SUPABASE)

        # =================================

        def buscar_unidad_reciente(empresa, no_unidad, no_unidad_externo):

            table_name = TABLE_MAP[empresa]

            unidad = no_unidad_externo if no_unidad == "REMOLQUE EXTERNO" else no_unidad

            limite = (datetime.now() - pd.Timedelta(hours=24)).isoformat()

            response = (

                supabase.table(table_name)

                .select('"No. de Folio", "Fecha de Captura"')

                .eq('"No. de Unidad"', unidad)

                .gte('"Fecha de Captura"', limite)

                .order('"Fecha de Captura"', desc=True)

                .limit(1)

                .execute()

            )

            data = response.data

            if not data:

                return None

            return data[0]["No. de Folio"]

        # =================================

        # Append Pase de Taller to Supabase

        # =================================

        def append_pase_to_sheet(data: dict):

            empresa = data["Empresa"]

            table_name = TABLE_MAP[empresa]

            prefix_map = {

                "IGLOO TRANSPORT": "IG",

                "LINCOLN FREIGHT": "LF",

                "PICUS": "PI",

                "SET FREIGHT INTERNATIONAL": "SFI",

                "SET LOGIS PLUS": "SLP",

            }

            prefix = prefix_map.get(data["Empresa"])

            # ---- GET LAST FOLIO ----

            response = (

                supabase.table(table_name)

                .select('"No. de Folio"')

                .ilike('"No. de Folio"', f"{prefix}%")

                .order('"No. de Folio"', desc=True)

                .limit(1)

                .execute()

            )

            last = response.data

            if last:

                num = int(last[0]["No. de Folio"].replace(prefix, ""))

                next_num = num + 1

            else:

                next_num = 1

            folio = f"{prefix}{str(next_num).zfill(5)}"

            # ---- INSERT INTO SUPABASE ----

            payload = data.copy()

            payload["No. de Folio"] = folio

            payload = {

                k: None if (pd.isna(v) or v == "")

                else v.item() if hasattr(v, "item")

                else v

                for k, v in payload.items()

            }

            try:

                response = supabase.table(table_name).insert(payload).execute()

                return folio

            except Exception as e:

                st.error(f"Supabase error: {e.args}")

                raise

        # =================================

        # Session state

        # =================================

        if "folio_generado" not in st.session_state:

            st.session_state.folio_generado = ""

        if "mostrar_confirmacion" not in st.session_state:

            st.session_state.mostrar_confirmacion = False

        if "folio_duplicado" not in st.session_state:

            st.session_state.folio_duplicado = None

        if "confirmar_guardado" not in st.session_state:

            st.session_state.confirmar_guardado = False

        if "forzar_guardado" not in st.session_state:

            st.session_state.forzar_guardado = False

        # =============================

        # FIELD USER VIEW

        # =============================

        if role == "field_user":

            # =================================

            # Page title

            # =================================

            st.title("🛠️ Captura Pase de Taller")

            # =================================

            # SECCIÓN 1 — DATOS DEL REPORTE

            # =================================

            st.subheader("WIP MY GUY")

        # =============================

        # ADMIN, MANAGER, REGULAR USER VIEW

        # =============================

        else:

            # =================================

            # Page title

            # =================================

            st.title("🛠️ Captura Pase de Taller")

            # =================================

            # SECCIÓN 1 — DATOS DEL REPORTE

            # =================================

            # =================================

            # =================================

            # ORDENES POR COMPLETAR — SOLO ADMIN / CONTROL_USER

            # FILTRADAS POR EMPRESA EN profiles.Empresas O PERMISOS profiles.access

            # =================================

            role_normalized = str(role or "").strip().lower()

            can_view_ordenes = role_normalized in {"admin", "control_user"}

            if can_view_ordenes:

                # Current profiles schema stores company permissions in access.

                # Use Empresas/empresas when present; otherwise fall back to access.

                empresas_permitidas = user.get("Empresas", user.get("empresas"))

                if isinstance(empresas_permitidas, str):

                    empresas_permitidas = [

                        empresa.strip() for empresa in re.split(r"[,;]", empresas_permitidas)

                        if empresa.strip()

                    ]

                elif not isinstance(empresas_permitidas, (list, tuple, set)):

                    empresas_permitidas = []

                if not empresas_permitidas:

                    empresas_permitidas = [

                        empresa for permiso, empresa in ACCESS_EMPRESA_MAP.items()

                        if permiso in access

                    ]

                empresas_permitidas = {

                    str(empresa).strip().casefold()

                    for empresa in empresas_permitidas

                    if str(empresa).strip()

                }

                alias_empresa = {

                    "igloo": "IGLOO TRANSPORT", "igloo transport": "IGLOO TRANSPORT", "igt": "IGLOO TRANSPORT",

                    "lincoln": "LINCOLN FREIGHT", "lincoln freight": "LINCOLN FREIGHT", "lin": "LINCOLN FREIGHT",

                    "picus": "PICUS", "pic": "PICUS",

                    "setfreight": "SET FREIGHT INTERNATIONAL", "set freight international": "SET FREIGHT INTERNATIONAL", "sfi": "SET FREIGHT INTERNATIONAL",

                    "setlogis": "SET LOGIS PLUS", "set logis plus": "SET LOGIS PLUS", "slp": "SET LOGIS PLUS",

                }

                empresas_permitidas_canonicas = {

                    alias_empresa.get(empresa, empresa.upper()) for empresa in empresas_permitidas

                }

                ordenes_por_completar = []

                for permiso, empresa_orden in ACCESS_EMPRESA_MAP.items():

                    if permiso not in access or empresa_orden not in empresas_permitidas_canonicas:

                        continue

                    tabla_ordenes = TABLE_MAP[empresa_orden]

                    try:

                        response_ordenes = (

                            supabase.table(tabla_ordenes)

                            .select('"No. de Folio", "Fecha de Captura"')

                            .eq("Estado", "Por Completar")

                            .order('"Fecha de Captura"', desc=True)

                            .execute()

                        )

                        for orden in (response_ordenes.data or []):

                            folio = orden.get("No. de Folio")

                            if folio:

                                ordenes_por_completar.append(f"{empresa_orden} — {folio}")

                    except Exception as e:

                        st.error(f"No fue posible cargar las órdenes por completar de {empresa_orden}: {e}")

                st.selectbox(

                    "Órdenes por Completar",

                    ["Selecciona una orden por completar"] + ordenes_por_completar,

                    key="orden_por_completar"

                )

            role_normalized = str(role or "").strip().lower()
            regular_pase_user = role_normalized == "regular_pase_user"
            fecha_reporte = date.today()

            @st.cache_data(ttl=3600)
            def cargar_todas_unidades_supabase():
                response = supabase.table("vehicle_units").select("*").execute()
                df = pd.DataFrame(response.data or [])
                if not df.empty:
                    df["unidad"] = df["unidad"].astype(str).str.strip()
                    df["tipo_unidad"] = df["tipo_unidad"].astype(str).str.upper().str.strip()
                return df

            unidades_catalogo = cargar_todas_unidades_supabase()
            if unidades_catalogo.empty:
                st.warning("No fue posible cargar el catálogo de unidades.")
                st.stop()
            unidad_options = ["Selecciona Unidad", "REMOLQUE EXTERNO"] + sorted(
                u for u in unidades_catalogo["unidad"].dropna().unique().tolist()
                if u and u.upper() != "REMOLQUE EXTERNO"
            )
            no_unidad = st.selectbox(
                "No. de Unidad", unidad_options, index=0,
                help="Busca escribiendo en el campo. La lista incluye todas las empresas.",
                key="pase_no_unidad_global",
            )
            fila_match = unidades_catalogo[
                unidades_catalogo["unidad"].astype(str).eq(str(no_unidad))
            ] if no_unidad not in ("Selecciona Unidad", "REMOLQUE EXTERNO") else pd.DataFrame()
            fila_unidad = fila_match.iloc[0] if not fila_match.empty else {}
            raw_tipo_unidad = str(fila_unidad.get("tipo_unidad", "") or "").strip().upper()
            tipo_unidad_auto = "Tractores" if raw_tipo_unidad == "TRACTOR" else (
                "Remolques" if raw_tipo_unidad in ("CAJA SECA", "CAJA REFRIGERADA") else ""
            )
            tipo_caja_auto = "Caja Seca" if "SECA" in raw_tipo_unidad else (
                "Caja Refrigerada" if "REFRIGERADA" in raw_tipo_unidad or "REFRIGER" in raw_tipo_unidad else ""
            )
            es_externo = no_unidad == "REMOLQUE EXTERNO"
            if es_externo:
                tipo_unidad_auto, tipo_caja_auto = "Remolques", ""

            empresas_usuario = [
                empresa for permiso, empresa in ACCESS_EMPRESA_MAP.items() if permiso in access
            ]
            empresas_disponibles = EMPRESAS if regular_pase_user else empresas_usuario
            if not empresas_disponibles:
                st.error("Tu usuario no tiene ninguna empresa asignada.")
                st.stop()
            empresa_por_codigo = {
                "IGT": "IGLOO TRANSPORT", "LIN": "LINCOLN FREIGHT", "PIC": "PICUS",
                "SET": "SET FREIGHT INTERNATIONAL", "SLP": "SET LOGIS PLUS",
            }
            codigo_catalogo = str(fila_unidad.get("empresa", "") or "").strip().upper()
            empresa_sugerida = empresa_por_codigo.get(codigo_catalogo, codigo_catalogo)
            if empresa_sugerida not in empresas_disponibles:
                empresa_sugerida = empresas_disponibles[0]
            if st.session_state.get("_pase_empresa_unidad_anterior") != no_unidad:
                st.session_state["pase_empresa_cobrar"] = empresa_sugerida
                st.session_state["_pase_empresa_unidad_anterior"] = no_unidad

            if regular_pase_user:
                tipo_proveedor, proveedor, proveedor_otro = "Externo", "Selecciona proveedor", ""
                razones, tipo_reporte = "Selecciona razón", "Selecciona tipo de mantenimiento"
                tipo_unidad_operador, operador, oste, no_reporte = tipo_unidad_auto, "", "", ""
                st.title("🛠️ Captura Pase de Taller")
                st.subheader("Pase de Taller")
            else:
                st.subheader("Datos del Reporte")
                tp1, tp2, tp25, tp3 = st.columns(4)
                with tp1:
                    tipo_proveedor = st.selectbox("Tipo de Orden", ["----", "Interno", "Externo"], key="tipo_orden_pase")
                with tp2:
                    if tipo_proveedor == "Interno":
                        proveedor = st.selectbox("Proveedor / Taller", ["WNC", "OTRO"], index=0)
                    else:
                        proveedor = st.selectbox("Proveedor / Taller", [
                            "Selecciona proveedor", "TALLER", "K9", "NAVARRO",
                            "KEVIN DANIEL RAUDALES MEDINA (RM)", "KINOS", "OTRO"
                        ])
                with tp25:
                    proveedor_otro = st.text_input("Proveedor / Otro", disabled=proveedor != "OTRO", placeholder="Especificar proveedor")
                with tp3:
                    if "razones" not in st.session_state:
                        st.session_state.razones = "Selecciona razón"
                    if tipo_proveedor == "Interno":
                        st.session_state.razones = "Selecciona razón"
                    razones = st.selectbox("Razones", [
                        "Selecciona razón", "Taller Saturado", "Caja fuera de Patio",
                        "Taller no Cuenta con las Refacciones", "Taller da Respuesta",
                        "Taller PG no va al RFE"
                    ], key="razones", disabled=tipo_proveedor != "Externo")
                st.text_input("Capturó", value=st.session_state.user.get("name") or st.session_state.user.get("email"), disabled=True)
                oste = ""
                no_reporte = st.text_input("No. de Reporte")
                tipo_reporte = st.selectbox("Tipo de Mantenimiento", [
                    "Selecciona tipo de mantenimiento", "Orden Preventivo", "Orden Correctivo"
                ])
                tipo_unidad_operador = st.selectbox(
                    "Tipo de Unidad", ["Seleccionar tipo de unidad", "Tractores", "Remolques"],
                    index=(["Seleccionar tipo de unidad", "Tractores", "Remolques"].index(tipo_unidad_auto)
                           if tipo_unidad_auto in ("Tractores", "Remolques") else 0)
                )
                operador = st.text_input("Operador")
                st.divider()
                st.subheader(
                    "Pase de Taller Interno" if tipo_proveedor == "Interno"
                    else "Pase de Taller Externo" if tipo_proveedor == "Externo"
                    else "Pase de Taller"
                )

            empresa = st.selectbox("Empresa a Cobrar", empresas_disponibles, key="pase_empresa_cobrar")
            empresa_codigo = EMPRESA_CODIGOS.get(empresa)
            marca_valor = fila_unidad.get("marca", "")
            modelo_valor = fila_unidad.get("modelo", "")
            sucursal_valor = fila_unidad.get("SUCURSAL", fila_unidad.get("sucursal", ""))
            if es_externo:
                marca_valor, modelo_valor, sucursal_valor = "EXTERNO", "0000", "EXTERNO"

            if es_externo:
                tipo_caja = st.selectbox("Tipo de Caja", ["Caja Seca", "Caja Refrigerada"], key="pase_tipo_caja_externo")
            elif tipo_caja_auto:
                opciones_caja = ["Caja Seca", "Caja Refrigerada"]
                tipo_caja = st.selectbox("Tipo de Caja", opciones_caja, index=opciones_caja.index(tipo_caja_auto), key="pase_tipo_caja_catalogo")
            else:
                tipo_caja = st.selectbox("Tipo de Caja", ["Caja no aplicable"], disabled=True, key="pase_tipo_caja_na")
            no_unidad_externo = st.text_input("No. de Unidad Externo", disabled=not es_externo, placeholder="Escribe el número externo", key="pase_no_unidad_externo")
            linea_externa = st.text_input("Nombre Línea Externa", disabled=not es_externo, placeholder="Escribe el nombre de la línea", key="pase_linea_externa")

            if regular_pase_user:
                st.text_input("Tipo de Unidad", value=tipo_unidad_auto, disabled=True, key="pase_tipo_unidad_display")
                aplica_cobro, responsable, genero_multa, no_inspeccion, reparacion_multa = "No", "", False, "", ""
                descripcion_problema = st.text_area(
                    "Observaciones y Comentarios",
                    placeholder="Describe brevemente el problema o los comentarios relevantes",
                    height=150, key="pase_observaciones_regular"
                )
            else:
                c1, c2 = st.columns([1, 3])
                with c1:
                    aplica_cobro = st.radio("¿Aplica Cobro?", ["No", "Sí"], horizontal=True, index=0, key="pase_aplica_cobro")
                with c2:
                    responsable = st.text_input("Responsable", disabled=aplica_cobro != "Sí")
                descripcion_problema = st.text_area("Observaciones y Comentarios", key="pase_observaciones")
                c1, c2 = st.columns([1, 3])
                with c1:
                    genero_multa = st.checkbox("¿Generó multa?", key="pase_genero_multa")
                with c2:
                    no_inspeccion = st.text_input("No. de Inspección", disabled=not genero_multa)
                reparacion_multa = st.text_area(
                    "Reparación que generó multa",
                    placeholder="Por favor introducir # de reporte aplicable",
                    disabled=not genero_multa,
                )
            st.divider()

            mostrar_guardar = regular_pase_user or tipo_proveedor in ["Interno", "Externo"]
            if mostrar_guardar and st.button("💾 Guardar Pase", type="primary", use_container_width=True):
                if no_unidad == "Selecciona Unidad":
                    st.error("Debes seleccionar un No. de Unidad válido antes de guardar.")
                    st.stop()
                if es_externo and not (no_unidad_externo and no_unidad_externo.strip()):
                    st.error("Debes capturar el No. de Unidad Externo.")
                    st.stop()
                if not regular_pase_user and aplica_cobro == "Sí" and not (responsable and responsable.strip()):
                    st.error("Debes capturar el Responsable cuando aplica cobro.")
                    st.stop()
                if not regular_pase_user and genero_multa and not (no_inspeccion and no_inspeccion.strip()):
                    st.error("Debes capturar el No. de Inspección cuando se genera multa.")
                    st.stop()
                if not regular_pase_user and genero_multa and not (reparacion_multa and reparacion_multa.strip()):
                    st.error("Debes capturar la Reparación que generó multa cuando se genera multa.")
                    st.stop()
                if not regular_pase_user and proveedor == "OTRO" and not proveedor_otro.strip():
                    st.error("Debes capturar el nombre del proveedor.")
                    st.stop()
                st.session_state.setdefault("forzar_guardado", False)
                st.session_state.setdefault("confirmar_guardado", False)
                st.session_state.setdefault("folio_duplicado", "")
                folio_existente = buscar_unidad_reciente(empresa, no_unidad, no_unidad_externo)
                if folio_existente and not st.session_state.forzar_guardado:
                    st.session_state.folio_duplicado = folio_existente
                    st.session_state.confirmar_guardado = True
                    st.rerun()
                proveedor_guardar = f"OTRO, {proveedor_otro.strip()}" if not regular_pase_user and proveedor == "OTRO" else (None if regular_pase_user else proveedor)
                payload = {
                    "Fecha de Captura": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                    "Fecha de Reporte": str(fecha_reporte),
                    "Tipo de Proveedor": None if regular_pase_user else tipo_proveedor,
                    "Proveedor": proveedor_guardar,
                    "Razones": None if regular_pase_user or tipo_proveedor == "Interno" else razones,
                    "Estado": "Por Completar" if regular_pase_user else "Inicio / Nuevo",
                    "Capturo": None if regular_pase_user else (st.session_state.user.get("name") or st.session_state.user.get("email")),
                    "Oste": oste, "No. de Reporte": None if regular_pase_user else no_reporte,
                    "Empresa": empresa, "Tipo de Reporte": None if regular_pase_user else tipo_reporte,
                    "Tipo de Unidad": tipo_unidad_auto if regular_pase_user else tipo_unidad_operador,
                    "Operador": None if regular_pase_user else operador, "No. de Unidad": no_unidad,
                    "Marca": marca_valor, "Modelo": modelo_valor, "Sucursal": sucursal_valor,
                    "Tipo de Caja": tipo_caja, "No. de Unidad Externo": no_unidad_externo if es_externo else None,
                    "Nombre Linea Externa": linea_externa if es_externo else None,
                    "Cobro": None if regular_pase_user else str(aplica_cobro),
                    "Responsable": None if regular_pase_user else responsable,
                    "Descripcion Problema": descripcion_problema,
                    "Multa": None if regular_pase_user else ("Sí" if genero_multa else "No"),
                    "No. de Inspeccion": None if regular_pase_user else no_inspeccion,
                    "Reparacion Multa": None if regular_pase_user else reparacion_multa,
                }
                folio_real = append_pase_to_sheet(payload)
                log_activity(f"Pase {folio_real} creado", "Solicitudes y Pases")
                st.session_state.forzar_guardado = False
                st.session_state.folio_generado = folio_real
                st.session_state.mostrar_confirmacion = True
                st.rerun()

        # =================================

        # DUPLICATE CONFIRMATION DIALOG

        # =================================

        if st.session_state.get("confirmar_guardado", False):

            @st.dialog("Registro duplicado detectado")

            def confirmar():

                st.warning(

                    f"Ya existe un pase para esta unidad en las últimas 24 horas.\n\n"

                    f"**Folio existente:** {st.session_state.folio_duplicado}"

                )

                c1, c2 = st.columns(2)

                # YES → CREATE NEW

                with c1:

                    if st.button("Sí, crear nuevo"):

                        st.session_state.forzar_guardado = True

                        st.session_state.confirmar_guardado = False

                        st.rerun()

                # NO → USE OLD

                with c2:

                    if st.button("No, usar existente"):

                        st.session_state.folio_generado = st.session_state.folio_duplicado

                        st.session_state.confirmar_guardado = False

                        st.session_state.mostrar_confirmacion = True

                        st.rerun()

            confirmar()

        # =================================

        # SUCCESS DIALOG

        # =================================

        if st.session_state.mostrar_confirmacion:

            @st.dialog("Pase guardado")

            def confirmacion():

                st.success("Pase guardado con éxito")

                st.markdown(

                    f"**No. de Folio:** \`{st.session_state.folio_generado}\`"

                )

                if st.button("Aceptar"):

                    st.session_state.mostrar_confirmacion = False

                    st.session_state.folio_generado = ""

                    st.switch_page(DASHBOARD_PAGE)

            confirmacion()

# =================================

# CAPTURA DE BONOS

# =================================

if has_bonos:

    with tab_bonos:

        if "bonos_operador" in access:

            st.title("💰 Captura Bono de Operadores")

            # ==========================================

            # CATALOGO DE UNIDADES

            # ==========================================

            try:

                unidades_response = (

                    supabase

                    .table("catalogo_unidades_bonos")

                    .select("*")

                    .order("unidad")

                    .execute()

                )

                unidades_df = pd.DataFrame(

                    unidades_response.data

                )

            except Exception as e:

                st.error(

                    f"Error cargando catálogo de unidades: {e}"

                )

                st.stop()

            if unidades_df.empty:

                st.warning(

                    "No existen unidades en el catálogo."

                )

                st.stop()

            # ==========================================

            # VEHICLE UNITS TABLE

            # ==========================================

            vehicle_response = (

                supabase

                .table("vehicle_units")

                .select("*")

                .order("unidad")

                .execute()

            )

            vehicle_df = pd.DataFrame(

                vehicle_response.data

            )

            # ==========================================

            # MERGE BOTH TABLES

            # ==========================================

            def normalize_unit(unit):

                if pd.isna(unit):

                    return ""

                unit = str(unit).strip().upper()

                # Extract only the numeric part

                numbers = re.findall(r"\d+", unit)

                if not numbers:

                    return unit

                number = int(numbers[0])

                if unit.startswith("IG-"):

                    return f"G{number:05d}"

                if unit.startswith("G"):

                    return f"G{number:05d}"

                if unit.startswith("P"):

                    return f"P{number:05d}"

                if unit.startswith("A"):

                    return f"A{number:05d}"

                return unit

            vehicle_df["join_key"] = vehicle_df["unidad"].apply(normalize_unit)

            unidades_df["join_key"] = unidades_df["unidad"].apply(normalize_unit)

            unidades_df = vehicle_df.merge(

                unidades_df,

                on="join_key",

                how="left",

                suffixes=("", "_bono")

            )

            # ==========================================

            # FORMULARIO

            # ==========================================

            st.subheader("📋 Formulario")

            # ==========================================

            # COMPANY ACCESS

            # ==========================================

            permissions = access

            available_companies = []

            if "igloo" in permissions:

                available_companies.append(("Igloo", "IGT"))

            if "picus" in permissions:

                available_companies.append(("Picus", "PIC"))

            if not available_companies:

                st.error("No tienes acceso a ninguna empresa.")

                st.stop()

            # Only one company -> hide dropdown

            if len(available_companies) == 1:

                empresa, empresa_codigo = available_companies[0]

            # More than one company -> show dropdown

            else:

                empresa = st.selectbox(

                    "Empresa",

                    [c[0] for c in available_companies]

                )

                empresa_codigo = dict(available_companies)[empresa]

            # Filter units

            unidades_filtradas = unidades_df[

                unidades_df["empresa"] == empresa_codigo

            ]

            unidad = st.selectbox(

                "Unidad",

                unidades_filtradas["unidad"].tolist()

                if not unidades_filtradas.empty

                else [],

                index=None,

                placeholder="Seleccione una Unidad primero"

            )

            if unidad is None:

                st.stop()

            unidad_info = unidades_filtradas[

                unidades_filtradas["unidad"] == unidad

            ].iloc[0]

            # ==========================================

            # Unidad Info (Hidden)

            # ==========================================

            def clean_value(value):

                return "" if pd.isna(value) else str(value)

            vin = clean_value(unidad_info["vin"])

            placa_mex = clean_value(unidad_info["placa_mex"])

            marca = clean_value(unidad_info["marca"])

            modelo = clean_value(unidad_info["modelo"])

            motor = clean_value(unidad_info["motor"])

            anio = clean_value(unidad_info["anio"])

            rendimiento_esperado_txt = clean_value(unidad_info["rendimiento_esperado"])

            rendimiento_minimo_txt = clean_value(unidad_info["rendimiento_minimo"])

            with st.container(border=True, key="bono_form"):

                col_form, col_calc = st.columns([1, 1])

                # ==========================================

                # LEFT COLUMN - FORM

                # ==========================================

                with col_form:

                    st.subheader("📝 Información del Viaje")

                    ruta = st.text_input(

                        "Ruta: Origen - Destino"

                    )

                    # Always initialize so the variable exists

                    trafico = ""

                    if empresa == "Picus":

                        tipo_ruta = st.selectbox(

                            "Tipo Ruta",

                            ["Corta", "Larga"]

                        )

                    else:

                        # Igloo doesn't use Tipo Ruta

                        tipo_ruta = "No Aplica"

                        trafico = st.text_input(

                            "Número de Tráfico"

                        )

                    kilometros = st.number_input(

                        "Kilómetros",

                        min_value=0.0,

                        step=1.0

                    )

                    litros_cargados = st.number_input(

                        "Litros Cargados",

                        min_value=0.0,

                        step=1.0

                    )

                    rendimiento_minimo = pd.to_numeric(

                        unidad_info["rendimiento_minimo"],

                        errors="coerce"

                    )

                    rendimiento_esperado = pd.to_numeric(

                        unidad_info["rendimiento_esperado"],

                        errors="coerce"

                    )

                    if pd.isna(rendimiento_minimo):

                        rendimiento_minimo = 0.0

                    if pd.isna(rendimiento_esperado):

                        rendimiento_esperado = 0.0

                    param1, param2 = st.columns(2)

                    with param1:

                        st.metric(

                            "Rendimiento Mínimo",

                            f"{rendimiento_minimo:.2f} km/l"

                        )

                    with param2:

                        PRECIO_DIESEL = st.number_input(

                            "Precio Diesel ($)",

                            min_value=0.0,

                            value=10.50,

                            step=0.01,

                            format="%.2f",

                            key="precio_diesel"

                        )

                    calcular = st.button(

                        "🧮 Calcular",

                        use_container_width=True

                    )

                # ==========================================

                # RIGHT COLUMN - RESULTADO

                # ==========================================

                with col_calc:

                    if calcular:

                        # -----------------------------

                        # Required field validation

                        # -----------------------------

                        errores = []

                        if not ruta.strip():

                            errores.append("Debes capturar la Ruta.")

                        if empresa == "Picus" and not tipo_ruta:

                            errores.append("Debes seleccionar el Tipo de Ruta.")

                        if empresa == "Igloo" and not trafico.strip():

                            errores.append("Debes capturar el Número de Tráfico.")

                        if kilometros <= 0:

                            errores.append("Los Kilómetros deben ser mayores a 0.")

                        if litros_cargados <= 0:

                            errores.append("Los Litros Cargados deben ser mayores a 0.")

                        if PRECIO_DIESEL <= 0:

                            errores.append("El Precio Diesel debe ser mayor a 0.")

                        if errores:

                            st.session_state["validacion_ok"] = False

                            st.error("No es posible realizar el cálculo.")

                            for e in errores:

                                st.warning(e)

                            st.stop()

                        # -----------------------------

                        # Calculate

                        # -----------------------------

                        rendimiento_real = (

                            kilometros / litros_cargados

                            if litros_cargados > 0

                            else 0

                        )

                        litros_permitidos = (

                            kilometros / rendimiento_minimo

                            if rendimiento_minimo > 0

                            else 0

                        )

                        diferencia_litros = (

                            litros_permitidos - litros_cargados

                        )

                        monto = (

                            diferencia_litros * PRECIO_DIESEL

                        )

                        # -----------------------------

                        # Business validation

                        # -----------------------------

                        errores = []

                        if rendimiento_real < rendimiento_minimo:

                            errores.append(

                                f"El rendimiento real ({rendimiento_real:.2f}) "

                                f"está por debajo del mínimo permitido "

                                f"({rendimiento_minimo:.2f})."

                            )

                        if rendimiento_real > (rendimiento_esperado * 1.20):

                            errores.append(

                                "El rendimiento es muy superior al esperado. "

                                "Verifica kilómetros y litros capturados."

                            )

                        if litros_cargados > (litros_permitidos * 1.20):

                            errores.append(

                                "Los litros cargados exceden considerablemente "

                                "los litros permitidos."

                            )

                        # If the calculated performance is below the minimum allowed

                        if rendimiento_real < rendimiento_minimo:

                            errores.append(

                                f"El rendimiento real ({rendimiento_real:.2f} km/l) "

                                f"está por debajo del mínimo permitido "

                                f"({rendimiento_minimo:.2f} km/l)."

                            )

                        # If it's unrealistically better than expected

                        if rendimiento_real > (rendimiento_esperado * 1.20):

                            errores.append(

                                f"El rendimiento real ({rendimiento_real:.2f} km/l) "

                                f"es más de un 20% superior al esperado "

                                f"({rendimiento_esperado:.2f} km/l). "

                                "Verifica los kilómetros y los litros capturados."

                            )

                        # If the amount of fuel is inconsistent

                        if litros_cargados > (litros_permitidos * 1.20):

                            errores.append(

                                "Los litros cargados exceden significativamente "

                                "los litros permitidos para este recorrido."

                            )

                        st.session_state["resultado_bono"] = {

                            "rendimiento_real": rendimiento_real,

                            "litros_permitidos": litros_permitidos,

                            "diferencia_litros": diferencia_litros,

                            "monto": monto

                        }

                        st.session_state["validacion_ok"] = len(errores) == 0

                        st.subheader("📊 Resultado")

                        st.text_input(

                            "Rendimiento Real",

                            value=f"{rendimiento_real:.2f}",

                            disabled=True

                        )

                        st.text_input(

                            "Dif. a Favor o en Contra del Rendimiento",

                            value=f"{rendimiento_real - rendimiento_minimo:.2f}",

                            disabled=True

                        )

                        st.text_input(

                            "Litros Permitidos",

                            value=f"{litros_permitidos:.2f}",

                            disabled=True

                        )

                        st.text_input(

                            "Litros Ahorrados / Excedidos",

                            value=f"{diferencia_litros:.2f}",

                            disabled=True

                        )

                        if monto >= 0:

                            st.success(

                                f"💰 BONO A PAGAR: ${monto:,.2f}"

                            )

                        else:

                            st.error(

                                f"🚨 DESCUENTO: ${abs(monto):,.2f}"

                            )

                        st.info(

                            f"Precio Diesel Utilizado: ${PRECIO_DIESEL:,.2f}"

                        )

                        st.info(

                            f"Rendimiento Esperado: {rendimiento_esperado:.2f} km/l"

                        )

                        if errores:

                            st.error(

                                "⚠ Se detectaron inconsistencias. "

                                "Corrige la información y vuelve a calcular."

                            )

                            for e in errores:

                                st.warning(e)

                        else:

                            st.success(

                                "✅ Validación completada correctamente."

                            )

                if st.button(

                    "📨 Enviar Formulario",

                    use_container_width=True,

                    key="btn_enviar_formulario"

                ):

                    resultado = st.session_state.get("resultado_bono")

                    if resultado is None:

                        st.error("Primero debes calcular el bono.")

                        st.stop()

                    if not st.session_state.get("validacion_ok", False):

                        st.error(

                            "Debes corregir las inconsistencias y volver a calcular antes de enviar."

                        )

                        st.stop()

                    rendimiento_real = resultado["rendimiento_real"]

                    litros_permitidos = resultado["litros_permitidos"]

                    diferencia_litros = resultado["diferencia_litros"]

                    monto = resultado["monto"]

                    try:

                        supabase.table("bonos_operadores").insert({

                            "usuario": st.session_state["user"]["name"],

                            "empresa": empresa,

                            "unidad": unidad,

                            "vin": clean_value(unidad_info["vin"]),

                            "placa_mex": clean_value(unidad_info["placa_mex"]),

                            "marca": clean_value(unidad_info["marca"]),

                            "modelo": clean_value(unidad_info["modelos"]),

                            "anio": (

                                int(float(unidad_info["anio"]))

                                if pd.notna(unidad_info["anio"])

                                else None

                            ),

                            "motor": clean_value(unidad_info["motor"]),

                            "rendimiento_esperado": rendimiento_esperado,

                            "rendimiento_minimo": rendimiento_minimo,

                            "ruta": ruta,

                            "tipo_ruta": tipo_ruta,

                            "numero_trafico": trafico,

                            "kilometros": kilometros,

                            "litros_cargados": litros_cargados,

                            "precio_diesel": PRECIO_DIESEL,

                            "rendimiento_real": rendimiento_real,

                            "diferencia_rendimiento": (

                                rendimiento_real - rendimiento_minimo

                            ),

                            "litros_permitidos": litros_permitidos,

                            "diferencia_litros": diferencia_litros,

                            "monto": monto

                        }).execute()

                        log_activity(

                            "Nuevo formulario bono",

                            "Solicitudes y Pases"

                        )

                        st.session_state["mostrar_popup_envio"] = True

                        st.rerun()

                    except Exception as e:

                        st.error(f"Error guardando formulario: {e}")

                # ==========================================

                # SUCCESS POPUP

                # ==========================================

                if st.session_state.get("mostrar_popup_envio", False):

                    @st.dialog("Formulario Enviado")

                    def popup_envio():

                        st.success("✅ Formulario enviado correctamente.")

                        if st.button(

                            "OK",

                            use_container_width=True,

                            key="btn_ok_popup"

                        ):

                            st.session_state["mostrar_popup_envio"] = False

                            st.switch_page(DASHBOARD_PAGE)

                    popup_envio()
