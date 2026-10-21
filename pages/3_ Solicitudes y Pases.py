import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime, date, timezone
from auth import require_login, require_access
from pages.css import load_css
import re
import resend  #type: ignore
from html import escape
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
# Security gates
# =================================
require_login()
# -------------------------------
# RELEASE GATE
# -------------------------------
user = st.session_state.user
access = user.get("access", [])
role = (user.get("role") or "").lower()
regular_pase_user = "regular_pase_user" in access
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

        def enviar_correo_nuevo_pase(folio: str, datos: dict) -> list[str]:
            """Envía el aviso del nuevo pase a los destinatarios configurados para CONTROL."""
            respuesta = (
                supabase.table("lista_correo_viaticos")
                .select("email")
                .eq("empresa", "CONTROL")
                .execute()
            )
            destinatarios = sorted({
                str(fila.get("email") or "").strip()
                for fila in (respuesta.data or [])
                if str(fila.get("email") or "").strip()
            }, key=str.lower)
            if not destinatarios:
                raise ValueError(
                    "No se encontraron destinatarios en lista_correo_viaticos con empresa CONTROL."
                )

            resend.api_key = st.secrets["RESEND_API_KEY"]

            def valor(campo):
                contenido = datos.get(campo)
                return escape(str(contenido).strip()).replace("\n", "<br>") if contenido not in (None, "") else "—"

            campos = [
                ("Empresa a cobrar", "Empresa"),
                ("Fecha de captura", "Fecha de Captura"),
                ("Estado", "Estado"),
                ("No. de Unidad", "No. de Unidad"),
                ("Tipo de Unidad", "Tipo de Unidad"),
                ("Tipo de Caja", "Tipo de Caja"),
                ("No. de Unidad Externo", "No. de Unidad Externo"),
                ("Nombre Línea Externa", "Nombre Linea Externa"),
            ]
            filas_html = "".join(
                f"<tr><td style='padding:8px;border-bottom:1px solid #e5e7eb;color:#555;width:38%'><b>{escape(etiqueta)}</b></td>"
                f"<td style='padding:8px;border-bottom:1px solid #e5e7eb'>{valor(campo)}</td></tr>"
                for etiqueta, campo in campos
            )
            correo_html = f"""
            <div style="font-family:Arial,sans-serif;color:#202124;max-width:680px;margin:auto">
              <div style="background:#151F6D;color:white;padding:22px 26px;border-radius:12px 12px 0 0">
                <div style="font-size:13px;opacity:.9">CAPTURA PASE DE TALLER</div>
                <h1 style="font-size:24px;margin:8px 0 0">Nuevo pase registrado</h1>
              </div>
              <div style="border:1px solid #e5e7eb;border-top:0;padding:24px;border-radius:0 0 12px 12px">
                <p>Se generó un nuevo folio al guardar un Pase de Taller.</p>
                <div style="background:#f3f5ff;border:1px solid #dbe2ff;border-radius:8px;padding:16px;margin:16px 0">
                  <div style="font-size:12px;color:#555">NO. DE FOLIO</div>
                  <div style="font-size:25px;font-weight:800;color:#151F6D;margin-top:4px">{escape(folio)}</div>
                </div>
                <table style="width:100%;border-collapse:collapse">{filas_html}</table>
                <h3 style="color:#151F6D;margin:22px 0 8px">Observaciones y comentarios</h3>
                <div style="background:#f8f9fa;border-radius:8px;padding:14px;white-space:normal">{valor('Descripcion Problema')}</div>
              </div>
            </div>
            """
            resend.Emails.send({
                "from": "PG Data Analyst <notificaciones@pgdataanalyst.com>",
                "to": destinatarios,
                "subject": f"Nuevo Pase de Taller: {folio}",
                "html": correo_html,
            })
            return destinatarios

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
        # =============================
        # CAPTURE VIEW IS CONTROLLED BY THE regular_pase_user PAGE PERMISSION
        # Any role can use the full form; the permission switches to simplified fields.
        # =============================
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
        can_view_ordenes = role_normalized in {"admin", "controlador"}
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
            ordenes_por_completar_info = {}
            current_user_name = str(
                st.session_state.user.get("name") or st.session_state.user.get("email") or "Usuario"
            ).strip()

            def reset_pase_form_values():
                """Restore the form's normal defaults when no order is loaded."""
                defaults = {
                    "tipo_orden_pase": "----",
                    "pase_proveedor": "Selecciona proveedor",
                    "pase_proveedor_otro": "",
                    "razones": "Selecciona razón",
                    "pase_capturo": current_user_name,
                    "pase_no_reporte": "",
                    "pase_tipo_reporte": "Selecciona tipo de mantenimiento",
                    "pase_operador": "",
                    "pase_no_unidad_global": "Selecciona Unidad",
                    "pase_tipo_unidad_display": "",
                    "pase_tipo_caja_externo": "Caja Seca",
                    "pase_tipo_caja_catalogo": "Caja Seca",
                    "pase_tipo_caja_na": "Caja no aplicable",
                    "pase_no_unidad_externo": "",
                    "pase_linea_externa": "",
                    "pase_aplica_cobro": "No",
                    "pase_responsable": "",
                    "pase_observaciones_regular": "",
                    "pase_observaciones": "",
                    "pase_genero_multa": False,
                    "pase_no_inspeccion": "",
                    "pase_reparacion_multa": "",
                }
                for field_key, default_value in defaults.items():
                    st.session_state[field_key] = default_value
                st.session_state["_pase_empresa_unidad_anterior"] = None
                st.session_state["pase_orden_cargada"] = None

            def cargar_orden_por_completar():
                seleccion = st.session_state.get("orden_por_completar")
                detalle = ordenes_por_completar_info.get(seleccion)
                if not detalle:
                    reset_pase_form_values()
                    return

                # PostgREST parses the period in "No. de Folio" as filter syntax.
                # Fetch the table rows and match the folio in Python instead.
                respuesta = supabase.table(detalle["tabla"]).select("*").execute()
                folio_buscado = str(detalle["folio"]).strip()
                registro = next(
                    (
                        fila for fila in (respuesta.data or [])
                        if str(fila.get("No. de Folio", "")).strip() == folio_buscado
                    ),
                    None,
                )
                if registro is None:
                    reset_pase_form_values()
                    st.session_state["pase_orden_error"] = (
                        f"No se encontró el folio {detalle['folio']} en {detalle['tabla']}."
                    )
                    return
                reset_pase_form_values()
                st.session_state["pase_orden_cargada"] = {
                    **detalle,
                    "registro": registro,
                }
                st.session_state.pop("pase_orden_error", None)

                tipo_proveedor_cargado = str(registro.get("Tipo de Proveedor") or "----").strip()
                if tipo_proveedor_cargado not in ("----", "Interno", "Externo"):
                    tipo_proveedor_cargado = "----"
                st.session_state["tipo_orden_pase"] = tipo_proveedor_cargado

                proveedor_guardado = str(registro.get("Proveedor") or "").strip()
                proveedor_otro_guardado = ""
                if proveedor_guardado.upper().startswith("OTRO,"):
                    proveedor_guardado, proveedor_otro_guardado = "OTRO", proveedor_guardado.split(",", 1)[1].strip()
                opciones_proveedor = (
                    ["WNC", "OTRO"] if tipo_proveedor_cargado == "Interno"
                    else ["Selecciona proveedor", "TALLER", "K9", "NAVARRO",
                          "KEVIN DANIEL RAUDALES MEDINA (RM)", "KINOS", "OTRO"]
                )
                if proveedor_guardado and proveedor_guardado not in opciones_proveedor:
                    opciones_proveedor.append(proveedor_guardado)
                st.session_state["pase_proveedor"] = proveedor_guardado or opciones_proveedor[0]
                st.session_state["pase_proveedor_otro"] = proveedor_otro_guardado

                razon_guardada = str(registro.get("Razones") or "Selecciona razón").strip()
                opciones_razones = [
                    "Selecciona razón", "Taller Saturado", "Caja fuera de Patio",
                    "Taller no Cuenta con las Refacciones", "Taller da Respuesta",
                    "Taller PG no va al RFE"
                ]
                if razon_guardada not in opciones_razones and razon_guardada != "Selecciona razón":
                    opciones_razones.append(razon_guardada)
                st.session_state["razones"] = razon_guardada

                capturo_guardado = str(registro.get("Capturo") or "").strip()
                st.session_state["pase_capturo"] = capturo_guardado or current_user_name
                st.session_state["pase_no_reporte"] = str(registro.get("No. de Reporte") or "")
                tipo_reporte_guardado = str(registro.get("Tipo de Reporte") or "Selecciona tipo de mantenimiento").strip()
                opciones_tipo_reporte = [
                    "Selecciona tipo de mantenimiento", "Orden Preventivo", "Orden Correctivo"
                ]
                st.session_state["pase_tipo_reporte"] = tipo_reporte_guardado
                st.session_state["pase_operador"] = str(registro.get("Operador") or "")

                unidad_guardada = str(registro.get("No. de Unidad") or "").strip()
                st.session_state["pase_no_unidad_global"] = unidad_guardada or "Selecciona Unidad"
                st.session_state["_pase_empresa_unidad_anterior"] = unidad_guardada or "Selecciona Unidad"
                empresa_guardada = str(registro.get("Empresa") or "").strip()
                empresas_usuario_cargadas = [
                    empresa for permiso, empresa in ACCESS_EMPRESA_MAP.items() if permiso in access
                ]
                if empresa_guardada in empresas_usuario_cargadas:
                    st.session_state["pase_empresa_cobrar"] = empresa_guardada
                elif not empresa_guardada:
                    # Keep the normal unit-based default for a blank saved field.
                    st.session_state["_pase_empresa_unidad_anterior"] = None
                elif detalle["empresa"]:
                    st.session_state["pase_empresa_cobrar"] = detalle["empresa"]

                tipo_caja_guardado = str(registro.get("Tipo de Caja") or "").strip()
                # Normalize legacy saved values so future edits save "Thermo".
                if tipo_caja_guardado.casefold() in {"caja refrigerada", "thermo"}:
                    tipo_caja_guardado = "Thermo"
                if tipo_caja_guardado:
                    st.session_state["pase_tipo_caja_externo"] = tipo_caja_guardado
                    st.session_state["pase_tipo_caja_catalogo"] = tipo_caja_guardado
                st.session_state["pase_no_unidad_externo"] = str(registro.get("No. de Unidad Externo") or "")
                st.session_state["pase_linea_externa"] = str(registro.get("Nombre Linea Externa") or "")
                cobro_guardado = str(registro.get("Cobro") or "No").strip()
                st.session_state["pase_aplica_cobro"] = cobro_guardado if cobro_guardado in ("No", "Sí") else "No"
                st.session_state["pase_responsable"] = str(registro.get("Responsable") or "")
                st.session_state["pase_observaciones_regular"] = str(registro.get("Descripcion Problema") or "")
                st.session_state["pase_observaciones"] = str(registro.get("Descripcion Problema") or "")
                multa_guardada = str(registro.get("Multa") or "No").strip().casefold()
                st.session_state["pase_genero_multa"] = multa_guardada in ("sí", "si", "true", "1")
                st.session_state["pase_no_inspeccion"] = str(registro.get("No. de Inspeccion") or "")
                st.session_state["pase_reparacion_multa"] = str(registro.get("Reparacion Multa") or "")

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
                            etiqueta_orden = f"{empresa_orden} — {folio}"
                            ordenes_por_completar.append(etiqueta_orden)
                            ordenes_por_completar_info[etiqueta_orden] = {
                                "tabla": tabla_ordenes,
                                "empresa": empresa_orden,
                                "folio": str(folio),
                            }
                except Exception as e:
                    st.error(f"No fue posible cargar las órdenes por completar de {empresa_orden}: {e}")

            if st.session_state.pop("_reset_pase_form_next_run", False):
                st.session_state["orden_por_completar"] = "Selecciona una orden por completar"
                reset_pase_form_values()
            st.session_state.setdefault("pase_orden_cargada", None)
            st.session_state.setdefault("orden_por_completar", "Selecciona una orden por completar")
            st.selectbox(
                "Órdenes por Completar",
                ["Selecciona una orden por completar"] + ordenes_por_completar,
                key="orden_por_completar",
                on_change=cargar_orden_por_completar,
            )
            if st.session_state.get("pase_orden_error"):
                st.warning(st.session_state.pop("pase_orden_error"))
        role_normalized = str(role or "").strip().lower()
        pase_orden_cargada = st.session_state.get("pase_orden_cargada") if role_normalized in {"admin", "controlador"} else None
        registro_orden_cargada = (pase_orden_cargada or {}).get("registro", {})
        current_user_name = str(
            st.session_state.user.get("name") or st.session_state.user.get("email") or "Usuario"
        ).strip()
        fecha_reporte = (
            registro_orden_cargada.get("Fecha de Reporte")
            if registro_orden_cargada.get("Fecha de Reporte") not in (None, "")
            else date.today()
        )

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
            unidad for unidad in unidades_catalogo["unidad"].dropna().unique().tolist()
            if unidad and unidad.upper() != "REMOLQUE EXTERNO"
        )
        unidad_cargada = str(registro_orden_cargada.get("No. de Unidad") or "").strip()
        if unidad_cargada and unidad_cargada not in unidad_options:
            unidad_options.append(unidad_cargada)
        empresas_usuario = [
            empresa for permiso, empresa in ACCESS_EMPRESA_MAP.items() if permiso in access
        ]
        empresas_disponibles = EMPRESAS if regular_pase_user else empresas_usuario
        if not empresas_disponibles:
            st.error("Tu usuario no tiene ninguna empresa asignada.")
            st.stop()

        if regular_pase_user:
            tipo_proveedor, proveedor, proveedor_otro = "Externo", "Selecciona proveedor", ""
            razones, tipo_reporte = "Selecciona razón", "Selecciona tipo de mantenimiento"
            operador, oste, no_reporte = "", "", ""
            st.subheader("Pase de Taller")
        else:
            st.subheader("Datos del Reporte")
            tp1, tp2, tp25, tp3 = st.columns(4)
            with tp1:
                tipo_proveedor = st.selectbox(
                    "Tipo de Orden", ["----", "Interno", "Externo"], key="tipo_orden_pase"
                )
            with tp2:
                if tipo_proveedor == "Interno":
                    opciones_proveedor = ["WNC", "OTRO"]
                else:
                    opciones_proveedor = [
                        "Selecciona proveedor", "TALLER", "K9", "NAVARRO",
                        "KEVIN DANIEL RAUDALES MEDINA (RM)", "KINOS", "OTRO"
                    ]
                proveedor_actual = st.session_state.get("pase_proveedor")
                registro_cargado = (st.session_state.get("pase_orden_cargada") or {}).get("registro", {})
                tipo_original_orden = str(registro_cargado.get("Tipo de Proveedor") or "----").strip()
                # Preserve a saved custom provider only while the loaded order keeps
                # its original Interno/Externo type. If the user changes the type,
                # restore the normal provider options for that type.
                if (
                    st.session_state.get("pase_orden_cargada")
                    and tipo_proveedor == tipo_original_orden
                    and proveedor_actual
                    and proveedor_actual not in opciones_proveedor
                ):
                    opciones_proveedor.append(proveedor_actual)
                if proveedor_actual not in opciones_proveedor:
                    st.session_state["pase_proveedor"] = opciones_proveedor[0]
                proveedor = st.selectbox(
                    "Proveedor / Taller", opciones_proveedor, key="pase_proveedor"
                )
            with tp25:
                proveedor_otro = st.text_input(
                    "Proveedor / Otro", disabled=proveedor != "OTRO",
                    placeholder="Especificar proveedor", key="pase_proveedor_otro"
                )
            with tp3:
                if "razones" not in st.session_state:
                    st.session_state.razones = "Selecciona razón"
                if tipo_proveedor == "Interno":
                    st.session_state.razones = "Selecciona razón"
                opciones_razones = [
                    "Selecciona razón", "Taller Saturado", "Caja fuera de Patio",
                    "Taller no Cuenta con las Refacciones", "Taller da Respuesta",
                    "Taller PG no va al RFE"
                ]
                razon_actual = st.session_state.get("razones")
                registro_cargado = (st.session_state.get("pase_orden_cargada") or {}).get("registro", {})
                tipo_original_orden = str(registro_cargado.get("Tipo de Proveedor") or "----").strip()
                if (
                    st.session_state.get("pase_orden_cargada")
                    and tipo_proveedor == tipo_original_orden == "Externo"
                    and razon_actual
                    and razon_actual not in opciones_razones
                ):
                    opciones_razones.append(razon_actual)
                if razon_actual not in opciones_razones:
                    st.session_state["razones"] = opciones_razones[0]
                razones = st.selectbox("Razones", opciones_razones, key="razones", disabled=tipo_proveedor != "Externo")
            st.session_state.setdefault("pase_capturo", current_user_name)
            st.text_input("Capturó", disabled=True, key="pase_capturo")
            oste = ""
            no_reporte = st.text_input("No. de Reporte", key="pase_no_reporte")
            opciones_tipo_reporte = [
                "Selecciona tipo de mantenimiento", "Orden Preventivo", "Orden Correctivo"
            ]
            tipo_reporte_actual = st.session_state.get("pase_tipo_reporte")
            if tipo_reporte_actual not in opciones_tipo_reporte:
                if st.session_state.get("pase_orden_cargada") and tipo_reporte_actual:
                    opciones_tipo_reporte.append(tipo_reporte_actual)
                else:
                    st.session_state["pase_tipo_reporte"] = opciones_tipo_reporte[0]
            tipo_reporte = st.selectbox(
                "Tipo de Mantenimiento", opciones_tipo_reporte, key="pase_tipo_reporte"
            )
            operador = st.text_input("Operador", key="pase_operador")
            st.divider()
            st.subheader(
                "Pase de Taller Interno" if tipo_proveedor == "Interno"
                else "Pase de Taller Externo" if tipo_proveedor == "Externo"
                else "Pase de Taller"
            )

        # La unidad se selecciona dentro de Pase de Taller; los datos dependientes se actualizan con ella.
        if regular_pase_user:
            col_unidad, col_tipo_unidad, col_tipo_caja = st.columns([2, 1, 1])
            with col_unidad:
                no_unidad = st.selectbox(
                    "No. de Unidad",
                    unidad_options,
                    help="Busca escribiendo en el campo. La lista incluye todas las empresas.",
                    key="pase_no_unidad_global",
                )
        else:
            no_unidad = st.selectbox(
                "No. de Unidad",
                unidad_options,
                help="Busca escribiendo en el campo. La lista incluye todas las empresas.",
                key="pase_no_unidad_global",
            )

        fila_match = unidades_catalogo[
            unidades_catalogo["unidad"].astype(str).eq(str(no_unidad))
        ] if no_unidad not in ("Selecciona Unidad", "REMOLQUE EXTERNO") else pd.DataFrame()

        # When completing an existing order, match the unit against the company
        # table from which that order was loaded. Unit numbers can repeat across
        # companies, so choosing the first global match can return blank/wrong data.
        orden_cargada_contexto = st.session_state.get("pase_orden_cargada") or {}
        empresa_unidad_codigo = EMPRESA_CODIGOS.get(orden_cargada_contexto.get("empresa"))
        if not fila_match.empty and empresa_unidad_codigo and "empresa" in fila_match.columns:
            fila_match_empresa = fila_match[
                fila_match["empresa"].astype(str).str.strip().str.upper().eq(empresa_unidad_codigo)
            ]
            if not fila_match_empresa.empty:
                fila_match = fila_match_empresa

        fila_unidad = fila_match.iloc[0] if not fila_match.empty else {}
        raw_tipo_unidad = str(fila_unidad.get("tipo_unidad", "") or "").strip().upper()
        tipo_normalizado = raw_tipo_unidad.replace("_", " ").replace("-", " ")
        if tipo_normalizado in ("TRACTOR", "TRACTORES", "TRACTOCAMION", "TRACTOCAMIONES", "CAMION", "CAMIONES"):
            tipo_unidad_auto = "Tractores"
        elif any(token in tipo_normalizado for token in ("REMOLQUE", "REMOLQUES", "CAJA", "TRAILER", "THERMO")):
            tipo_unidad_auto = "Remolques"
        else:
            tipo_unidad_auto = ""
        tipo_caja_auto = "Caja Seca" if "SECA" in tipo_normalizado else (
            "Thermo" if any(token in tipo_normalizado for token in ("THERMO", "REFRIGERADA", "REFRIGER", "FRIA", "FRÍO")) else ""
        )
        es_externo = no_unidad == "REMOLQUE EXTERNO"
        if es_externo:
            tipo_unidad_auto, tipo_caja_auto = "Remolques", ""

        # Update the keyed disabled widget on every rerun; otherwise Streamlit
        # retains its first (blank) value instead of the selected unit's type.
        tipo_unidad_guardado = str(registro_orden_cargada.get("Tipo de Unidad") or "").strip()
        if tipo_unidad_guardado:
            tipo_unidad_auto = tipo_unidad_guardado
        st.session_state["pase_tipo_unidad_display"] = tipo_unidad_auto
        if regular_pase_user:
            with col_tipo_unidad:
                st.text_input(
                    "Tipo de Unidad",
                    disabled=True,
                    key="pase_tipo_unidad_display",
                )
        else:
            st.text_input(
                "Tipo de Unidad",
                disabled=True,
                key="pase_tipo_unidad_display",
            )

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

        # Empresa a cobrar ocupa una fila independiente para la vista simplificada.
        empresa = st.selectbox("Empresa a Cobrar", empresas_disponibles, key="pase_empresa_cobrar")
        empresa_codigo = EMPRESA_CODIGOS.get(empresa)

        marca_valor = fila_unidad.get("marca", "")
        modelo_valor = fila_unidad.get("modelo", "")
        sucursal_valor = fila_unidad.get("SUCURSAL", fila_unidad.get("sucursal", ""))
        if es_externo:
            marca_valor, modelo_valor, sucursal_valor = "EXTERNO", "0000", "EXTERNO"

        if tipo_unidad_auto == "Remolques":
            opciones_caja = ["Caja Seca", "Thermo"]
            caja_guardada = str(registro_orden_cargada.get("Tipo de Caja") or "").strip()
            if caja_guardada.casefold() in {"caja refrigerada", "thermo"}:
                caja_guardada = "Thermo"
            if caja_guardada and caja_guardada not in opciones_caja:
                opciones_caja.append(caja_guardada)
            indice_caja = opciones_caja.index(tipo_caja_auto) if tipo_caja_auto in opciones_caja else 0
            if regular_pase_user:
                with col_tipo_caja:
                    tipo_caja = st.selectbox(
                        "Tipo de Caja", opciones_caja, index=indice_caja,
                        key="pase_tipo_caja_externo" if es_externo else "pase_tipo_caja_catalogo",
                    )
            else:
                tipo_caja = st.selectbox(
                    "Tipo de Caja", opciones_caja, index=indice_caja,
                    key="pase_tipo_caja_externo" if es_externo else "pase_tipo_caja_catalogo",
                )
        else:
            if regular_pase_user:
                with col_tipo_caja:
                    tipo_caja = st.selectbox(
                        "Tipo de Caja", ["Caja no aplicable"], disabled=True, key="pase_tipo_caja_na"
                    )
            else:
                tipo_caja = st.selectbox(
                    "Tipo de Caja", ["Caja no aplicable"], disabled=True, key="pase_tipo_caja_na"
                )

        if regular_pase_user:
            col_unidad_externa, col_linea_externa = st.columns(2)
            with col_unidad_externa:
                no_unidad_externo = st.text_input(
                    "No. de Unidad Externo", disabled=not es_externo,
                    placeholder="Escribe el número externo", key="pase_no_unidad_externo"
                )
            with col_linea_externa:
                linea_externa = st.text_input(
                    "Nombre Línea Externa", disabled=not es_externo,
                    placeholder="Escribe el nombre de la línea", key="pase_linea_externa"
                )
        else:
            no_unidad_externo = st.text_input(
                "No. de Unidad Externo", disabled=not es_externo,
                placeholder="Escribe el número externo", key="pase_no_unidad_externo"
            )
            linea_externa = st.text_input(
                "Nombre Línea Externa", disabled=not es_externo,
                placeholder="Escribe el nombre de la línea", key="pase_linea_externa"
            )

        if regular_pase_user:
            aplica_cobro, responsable, genero_multa, no_inspeccion, reparacion_multa = "No", "", False, "", ""
            descripcion_problema = st.text_area(
                "Observaciones y Comentarios",
                placeholder="Describe brevemente el problema o los comentarios relevantes",
                height=150, key="pase_observaciones_regular"
            )
        else:
            c1, c2 = st.columns([1, 3])
            with c1:
                aplica_cobro = st.radio(
                    "¿Aplica Cobro?", ["No", "Sí"], horizontal=True, index=0, key="pase_aplica_cobro"
                )
            with c2:
                responsable = st.text_input("Responsable", disabled=aplica_cobro != "Sí", key="pase_responsable")
            descripcion_problema = st.text_area("Observaciones y Comentarios", key="pase_observaciones")
            c1, c2 = st.columns([1, 3])
            with c1:
                genero_multa = st.checkbox("¿Generó multa?", key="pase_genero_multa")
            with c2:
                no_inspeccion = st.text_input("No. de Inspección", disabled=not genero_multa, key="pase_no_inspeccion")
            reparacion_multa = st.text_area(
                "Reparación que generó multa",
                placeholder="Por favor introducir # de reporte aplicable",
                disabled=not genero_multa,
                key="pase_reparacion_multa",
            )
        st.divider()
        if st.button("💾 Guardar Pase", type="primary", use_container_width=True):
            if not regular_pase_user and tipo_proveedor not in ["Interno", "Externo"]:
                st.error("Debes seleccionar Tipo de Orden: Interno o Externo.")
                st.stop()
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
            orden_cargada_ahora = pase_orden_cargada if not regular_pase_user else None
            if not orden_cargada_ahora:
                folio_existente = buscar_unidad_reciente(empresa, no_unidad, no_unidad_externo)
                if folio_existente and not st.session_state.forzar_guardado:
                    st.session_state.folio_duplicado = folio_existente
                    st.session_state.confirmar_guardado = True
                    st.rerun()
            proveedor_guardar = f"OTRO, {proveedor_otro.strip()}" if not regular_pase_user and proveedor == "OTRO" else (None if regular_pase_user else proveedor)
            capturo_actual = (
                current_user_name if regular_pase_user
                else str(st.session_state.get("pase_capturo") or current_user_name).strip()
            )
            marca_guardar = None if regular_pase_user else marca_valor
            modelo_guardar = None if regular_pase_user else modelo_valor
            sucursal_guardar = None if regular_pase_user else sucursal_valor
            oste_guardar = oste
            fecha_captura_guardar = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            if orden_cargada_ahora:
                registro_original = orden_cargada_ahora.get("registro", {})
                fecha_captura_original = registro_original.get("Fecha de Captura")
                if fecha_captura_original not in (None, ""):
                    fecha_captura_guardar = fecha_captura_original
                # Refresh vehicle metadata from vehicle_units when completing an
                # existing order. Fall back to the saved order only if the catalog
                # does not provide a value, so existing metadata is not erased.
                marca_catalogo = marca_valor
                modelo_catalogo = modelo_valor
                sucursal_catalogo = sucursal_valor
                marca_guardar = (
                    marca_catalogo if pd.notna(marca_catalogo) and str(marca_catalogo).strip()
                    else registro_original.get("Marca")
                )
                modelo_guardar = (
                    modelo_catalogo if pd.notna(modelo_catalogo) and str(modelo_catalogo).strip()
                    else registro_original.get("Modelo")
                )
                sucursal_guardar = (
                    sucursal_catalogo if pd.notna(sucursal_catalogo) and str(sucursal_catalogo).strip()
                    else registro_original.get("Sucursal")
                )
                oste_guardar = registro_original.get("Oste") if registro_original.get("Oste") not in (None, "") else oste
            payload = {
                "Fecha de Captura": fecha_captura_guardar,
                "Fecha de Reporte": str(fecha_reporte),
                "Tipo de Proveedor": None if regular_pase_user else tipo_proveedor,
                "Proveedor": proveedor_guardar,
                "Razones": None if regular_pase_user or tipo_proveedor == "Interno" else razones,
                "Estado": "Por Completar" if regular_pase_user else "Inicio / Nuevo",
                "Capturo": capturo_actual,
                "Oste": oste_guardar, "No. de Reporte": None if regular_pase_user else no_reporte,
                "Empresa": empresa, "Tipo de Reporte": None if regular_pase_user else tipo_reporte,
                "Tipo de Unidad": tipo_unidad_auto,
                "Operador": None if regular_pase_user else operador, "No. de Unidad": no_unidad,
                "Marca": marca_guardar,
                "Modelo": modelo_guardar,
                "Sucursal": sucursal_guardar,
                "Tipo de Caja": tipo_caja,
                "No. de Unidad Externo": no_unidad_externo if es_externo else None,
                "Nombre Linea Externa": linea_externa if es_externo else None,
                "Cobro": None if regular_pase_user else str(aplica_cobro),
                "Responsable": None if regular_pase_user else responsable,
                "Descripcion Problema": descripcion_problema,
                "Multa": None if regular_pase_user else ("Sí" if genero_multa else "No"),
                "No. de Inspeccion": None if regular_pase_user else no_inspeccion,
                "Reparacion Multa": None if regular_pase_user else reparacion_multa,
            }
            if orden_cargada_ahora:
                folio_real = str(orden_cargada_ahora["folio"])
                tabla_actualizar = orden_cargada_ahora["tabla"]
                payload_actualizar = {
                    k: None if (pd.isna(v) or v == "")
                    else v.item() if hasattr(v, "item")
                    else v
                    for k, v in payload.items()
                }
                id_registro = registro_original.get("id")
                if id_registro is None:
                    raise ValueError(
                        f"No se pudo actualizar el folio {folio_real}: falta el id del registro original."
                    )
                supabase.table(tabla_actualizar).update(payload_actualizar).eq("id", id_registro).execute()
                log_activity(f"Pase {folio_real} completado/actualizado", "Solicitudes y Pases")
            else:
                folio_real = append_pase_to_sheet(payload)
                log_activity(f"Pase {folio_real} creado", "Solicitudes y Pases")

            # Record a structured chat event for every creation or completion.
            chatlog_message = (
                f"Sistema: Orden {folio_real} creada"
                if regular_pase_user
                else f"Sistema: {current_user_name} ha completado la solicitud"
            )
            try:
                chatlog_response = (
                    supabase.table("pase_taller_chatlog")
                    .select("chatlog")
                    .eq("no_de_folio", folio_real)
                    .limit(1)
                    .execute()
                )
                chatlog_actual = (chatlog_response.data or [{}])[0].get("chatlog", [])
                if not isinstance(chatlog_actual, list):
                    chatlog_actual = [chatlog_actual] if chatlog_actual else []
                chatlog_actual.append({
                    "message": chatlog_message,
                    "user": current_user_name,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                supabase.table("pase_taller_chatlog").upsert({
                    "no_de_folio": folio_real,
                    "completado_por": current_user_name,
                    "chatlog": chatlog_actual,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }, on_conflict="no_de_folio").execute()
                st.session_state.pop("pase_chatlog_error", None)
            except Exception as chat_exc:
                st.session_state["pase_chatlog_error"] = str(chat_exc)

            st.session_state.forzar_guardado = False
            st.session_state.folio_generado = folio_real
            st.session_state.pase_orden_cargada = None
            if role_normalized in {"admin", "controlador"}:
                st.session_state["_reset_pase_form_next_run"] = True
            if regular_pase_user:
                try:
                    destinatarios_email = enviar_correo_nuevo_pase(folio_real, payload)
                    st.session_state.email_pase_estado = "enviado"
                    st.session_state.email_pase_destinatarios = destinatarios_email
                    st.session_state.pop("email_pase_error", None)
                except Exception as email_exc:
                    st.session_state.email_pase_estado = "error"
                    st.session_state.email_pase_error = str(email_exc)
                    st.session_state.pop("email_pase_destinatarios", None)
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
                if st.session_state.get("pase_chatlog_error"):
                    st.warning(
                        "El pase sí se guardó, pero no se pudo registrar en el chatlog: "
                        f"{st.session_state.get('pase_chatlog_error')}"
                    )
                if "regular_pase_user" in access and st.session_state.get("email_pase_estado") == "error":
                    st.warning(
                        "El pase sí se guardó, pero no se pudo enviar el correo: "
                        f"{st.session_state.get('email_pase_error', 'Error desconocido')}"
                    )
                if st.button("Aceptar"):
                    st.session_state.mostrar_confirmacion = False
                    st.session_state.folio_generado = ""
                    st.session_state.pop("pase_chatlog_error", None)
                    st.session_state.pop("email_pase_estado", None)
                    st.session_state.pop("email_pase_error", None)
                    st.session_state.pop("email_pase_destinatarios", None)
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
