import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
from datetime import datetime, timezone
from io import BytesIO
from auth import require_login, require_access
from supabase import create_client
from pages.css import load_css
import html
import resend  #type: ignore

# =================================
# RELEASE CHANNEL
# =================================

APP_CHANNEL = "BETA"
# APP_CHANNEL = "RELEASE"

DASHBOARD_PAGE = (
    "pages/dashboard_beta.py"
    if APP_CHANNEL == "BETA"
    else "pages/dashboard.py"
)

def clean(val):
    import pandas as pd
    if pd.isna(val) or val is None:
        return ""
    return str(val).strip()

# =================================
# Page Cache and State Management
# =================================
@st.cache_resource
def get_supabase_client():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_SERVICE_KEY"]
    )

supabase = get_supabase_client()

# =================================
# Page configuration
# =================================
st.set_page_config(
    page_title="Gestión de Órdenes y Pases",
    layout="wide"
)

# -------------------------------
# PAGE STYLE
# -------------------------------
load_css()

# =================================
# Security
# =================================
require_login()

user_access = {
    access.lower()
    for access in st.session_state["user"].get("access", [])
}

has_autorizacion = "autorizacion" in user_access
has_viaticos = "gestion_viaticos" in user_access

if not (has_autorizacion or has_viaticos):
    st.error("No tienes permisos para acceder a este módulo.")
    st.stop()

# =================================
# Navigation
# =================================
st.write("")
if st.button("⬅ Volver al Dashboard"):
    st.session_state.modal_reporte = None
    st.session_state.modal_factura = None
    st.session_state.modal_factura_open = False
    st.session_state.buscar_trigger = False
    st.switch_page(DASHBOARD_PAGE)

st.divider()

# =================================
# MODULES
# =================================

if has_autorizacion and has_viaticos:

    tab_autorizacion, tab_viaticos = st.tabs([
        "📋 Autorización y Actualización de Pases de Taller",
        "💳 Gestión de Viáticos",
    ])

elif has_autorizacion:

    tab_autorizacion = st.container()

elif has_viaticos:

    tab_viaticos = st.container()

# =================================
# TAB 1 Autorización y Actualización de Pases de Taller
# =================================

if has_autorizacion:
    with tab_autorizacion:
        # =================================
        # Defensive reset on page entry
        # =================================
        if st.session_state.get("_reset_autorizacion_page", True):
            st.session_state.modal_reporte = None
            st.session_state.modal_factura = None
            st.session_state.modal_factura_open = False
            st.session_state.buscar_trigger = False
            st.session_state["_reset_autorizacion_page"] = False

        # =================================
        # Update Estado
        # =================================
        VALID_ESTADOS = [
            "Inicio / Nuevo",
            "En Curso / Proceso",
            "Cerrado / Terminado",
            "Cerrado / Cancelado",
        ]

        ACCESS_TABLE_MAP = {
            "igloo": "IGLOO",
            "lincoln": "LINCOLN",
            "picus": "PICUS",
            "setlogis": "SLP",
            "setfreight": "SFI",
        }

        ACCESS_COMPANY_MAP = {
            "igloo": "IGLOO TRANSPORT",
            "lincoln": "LINCOLN FREIGHT",
            "picus": "PICUS",
            "setlogis": "SET LOGIS PLUS",
            "setfreight": "SET FREIGHT INTERNATIONAL",
        }

        def actualizar_estado_pase(empresa, folio, nuevo_estado):

            if nuevo_estado not in VALID_ESTADOS:
                return

            table_map = {
                "IGLOO TRANSPORT": "IGLOO",
                "LINCOLN FREIGHT": "LINCOLN",
                "PICUS": "PICUS",
                "SET FREIGHT INTERNATIONAL": "SFI",
                "SET LOGIS PLUS": "SLP",
            }

            table_name = table_map.get(empresa)
            if not table_name:
                return

            supabase = get_supabase_client()

            supabase.table(table_name)\
                .update({"Estado": nuevo_estado})\
                .eq('"No. de Folio"', folio)\
                .execute()

        # =================================
        # Update OSTE (SUPABASE)
        # =================================
        def actualizar_oste_pase(empresa, folio, oste):

            table_map = {
                "IGLOO TRANSPORT": "IGLOO",
                "LINCOLN FREIGHT": "LINCOLN",
                "PICUS": "PICUS",
                "SET FREIGHT INTERNATIONAL": "SFI",
                "SET LOGIS PLUS": "SLP",
            }

            table_name = table_map.get(empresa)

            if not table_name:
                return

            supabase = get_supabase_client()

            supabase.table(table_name)\
                .update({"Oste": oste})\
                .eq('"No. de Folio"', folio)\
                .execute()

        # =================================
        # Update No. de Orden (SUPABASE)
        # =================================

        def actualizar_no_reporte_pase(empresa, folio, nuevo_no_reporte):

            table_map = {
                "IGLOO TRANSPORT": "IGLOO",
                "LINCOLN FREIGHT": "LINCOLN",
                "PICUS": "PICUS",
                "SET FREIGHT INTERNATIONAL": "SFI",
                "SET LOGIS PLUS": "SLP",
            }

            table_name = table_map.get(empresa)

            if not table_name:
                return

            supabase = get_supabase_client()

            valor_final = str(nuevo_no_reporte).strip()

            if valor_final == "":
                valor_final = None

            supabase.table(table_name)\
                .update({
                    "No. de Reporte": valor_final
                })\
                .eq('"No. de Folio"', folio)\
                .execute()
            
        # =================================
        # Update Descripcion Problema
        # =================================
        def actualizar_descripcion_pase(empresa, folio, nueva_descripcion):

            table_map = {
                "IGLOO TRANSPORT": "IGLOO",
                "LINCOLN FREIGHT": "LINCOLN",
                "PICUS": "PICUS",
                "SET FREIGHT INTERNATIONAL": "SFI",
                "SET LOGIS PLUS": "SLP",
            }

            table_name = table_map.get(empresa)
            if not table_name:
                return

            supabase = get_supabase_client()

            supabase.table(table_name)\
                .update({"Descripcion Problema": nueva_descripcion})\
                .eq('"No. de Folio"', folio)\
                .execute()

        # =================================
        # GUARDAR FACTURA
        # =================================
        def guardar_factura(folio, numero_factura):

            supabase = get_supabase_client()

            response = (
                supabase
                .table("INVOICES")
                .select("*")
                .eq('"No. de Folio"', folio)
                .execute()
            )

            data = response.data

            if data:
                supabase.table("INVOICES")\
                    .update({"No. de Factura": numero_factura})\
                    .eq('"No. de Folio"', folio)\
                    .execute()
            else:
                supabase.table("INVOICES")\
                    .insert({
                        "No. de Folio": folio,
                        "No. de Factura": numero_factura
                    })\
                    .execute()

        # =================================
        # Registrar Cambio en CHANGELOG
        # =================================
        def registrar_cambio_log(
            usuario,
            empresa,
            folio,
            tipo_cambio,
            estado_anterior=None,
            estado_nuevo=None,
            oste_anterior=None,
            oste_nuevo=None,
            comentario=""
        ):

            supabase = get_supabase_client()

            response = supabase.table("AUDIT").insert({
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Usuario": clean(usuario),
                "Empresa": clean(empresa),
                "No. de Folio": clean(folio),
                "Tipo Cambio": clean(tipo_cambio),
                "Estado Anterior": clean(estado_anterior),
                "Estado Nuevo": clean(estado_nuevo),
                "OSTE Anterior": clean(oste_anterior),
                "OSTE Nuevo": clean(oste_nuevo),
                "Comentario": clean(comentario)
            }).execute()

            if getattr(response, "error", None):
                st.error(f"Audit log error: {response.error}")

        # =================================
        # Log estado sin refacciones
        # =================================
        def registrar_cambio_estado_sin_servicios(folio, usuario, nuevo_estado):

            supabase = get_supabase_client()

            estado_fecha_map = {
                "En Curso / Proceso": "Fecha En Proceso",
                "Cerrado / Terminado": "Fecha Terminado",
                "Cerrado / Cancelado": "Fecha Cancelado",
            }

            fecha_col = estado_fecha_map.get(nuevo_estado)

            if not fecha_col:
                return

            fecha_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            payload = {
                "No. de Folio": folio,
                "Modifico": usuario,
                "Fecha Mod": fecha_now,
                fecha_col: fecha_now
            }

            supabase.table("SERVICES").insert(payload).execute()

        # =================================
        # Load Servicios for Folio (SUPABASE)
        # =================================
        def cargar_servicios_folio(folio):

            supabase = get_supabase_client()

            response = (
                supabase
                .table("SERVICES")
                .select("*")
                .eq('"No. de Folio"', folio)
                .execute()
            )

            data = response.data

            if not data:
                return pd.DataFrame(columns=[
                    "Parte",
                    "Tipo De Parte",
                    "Posicion",
                    "Cantidad"
                ])

            df = pd.DataFrame(data)

            # remove status rows
            if "Parte" in df.columns:
                df = df[df["Parte"].notna() & (df["Parte"].astype(str).str.strip() != "")]

            return df[
                ["Parte", "Tipo De Parte", "Posicion", "Cantidad"]
            ]

        # =================================
        # UPSERT Servicios / Refacciones (SUPABASE)
        # =================================
        def guardar_servicios_refacciones(folio, usuario, servicios_df, nuevo_estado=None):

            supabase = get_supabase_client()

            if servicios_df is None or servicios_df.empty:
                return

            fecha_mod = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            estado_fecha_map = {
                "En Curso / Proceso": "Fecha En Proceso",
                "Cerrado / Terminado": "Fecha Terminado",
                "Cerrado / Cancelado": "Fecha Cancelado",
            }

            fecha_col = estado_fecha_map.get(nuevo_estado)

            for _, r in servicios_df.iterrows():

                cantidad = r.get("Cantidad", 0)

                if pd.isna(cantidad) or cantidad == "":
                    cantidad = 0

                payload = {
                    "No. de Folio": folio,
                    "Modifico": usuario,
                    "Parte": str(r.get("Parte", "")).strip(),
                    "Tipo De Parte": str(r.get("Tipo De Parte", "")).strip(),
                    "Posicion": str(r.get("Posicion", "")).strip(),
                    "Cantidad": int(float(cantidad)),
                    "Fecha Mod": fecha_mod,
                }

                if fecha_col:
                    payload[fecha_col] = fecha_mod

                supabase.table("SERVICES").insert(payload).execute()

        # =================================
        # Load Pase de Taller (SUPABASE)
        # =================================
        @st.cache_data(ttl=300)
        def cargar_pases_taller(user_access):

            supabase = get_supabase_client()

            tablas = [
                tabla
                for permiso, tabla in ACCESS_TABLE_MAP.items()
                if permiso in user_access
            ]

            dfs = []

            for tabla in tablas:

                response = (
                    supabase
                    .table(tabla)
                    .select("*")
                    .execute()
                )

                data = response.data

                if data:
                    dfs.append(pd.DataFrame(data))

            if not dfs:
                return pd.DataFrame()

            df = pd.concat(dfs, ignore_index=True)

            df.rename(columns={
                "No. de Folio": "NoFolio",
                "Fecha de Captura": "Fecha",
                #"Tipo de Proveedor": "Proveedor",
            }, inplace=True)

            df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce", utc=True).dt.tz_localize(None)
            df["NoFolio"] = df["NoFolio"].astype(str)

            return df

        # =================================
        # Load FACTURAS (SUPABASE)
        # =================================
        @st.cache_data(ttl=300)
        def cargar_facturas():

            supabase = get_supabase_client()

            response = (
                supabase
                .table("INVOICES")
                .select("*")
                .execute()
            )

            data = response.data

            if not data:
                return pd.DataFrame()

            df = pd.DataFrame(data)

            df.columns = df.columns.str.strip()

            if "No. de Factura" in df.columns:
                df["No. de Factura"] = (
                    df["No. de Factura"]
                    .astype(str)
                    .str.replace(".0", "", regex=False)
                    .str.strip()
                )

            if "No. de Folio" in df.columns:
                df["No. de Folio"] = df["No. de Folio"].astype(str).str.strip()

            return df

        # =================================
        # Load Audit Log
        # =================================
        @st.cache_data(ttl=120)
        def cargar_audit():

            supabase = get_supabase_client()

            response = (
                supabase
                .table("AUDIT")
                .select("*")
                .order("Timestamp", desc=True)
                .limit(200)
                .execute()
            )

            data = response.data

            if not data:
                return pd.DataFrame()

            df = pd.DataFrame(data)

            if "Timestamp" in df.columns:
                df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")

            return df

        # =================================
        # REFRESH CACHED DATA
        # =================================
        def refresh_cached_data():
            cargar_pases_taller.clear()
            cargar_facturas.clear()
            cargar_audit.clear()

        # =================================
        # LOADERS
        # =================================
        #cache
        refresh_cached_data()

        user_access = tuple(
            access.lower()
            for access in st.session_state["user"].get("access", [])
        )

        allowed_companies = {
            ACCESS_COMPANY_MAP[perm]
            for perm in user_access
            if perm in ACCESS_COMPANY_MAP
        }

        pases_df = cargar_pases_taller(user_access)
        facturas_df = cargar_facturas()
        audit_df = cargar_audit()

        if not facturas_df.empty:
            facturas_df.columns = facturas_df.columns.str.strip()

            if "No. de Folio" in facturas_df.columns:
                facturas_df = facturas_df.rename(columns={"No. de Folio": "NoFolio"})

            facturas_df["NoFolio"] = facturas_df["NoFolio"].astype(str)

        # =================================
        # Load Refacciones (Supabase)
        # =================================
        @st.cache_data(ttl=300)
        def cargar_refacciones():
            supabase = get_supabase_client()

            page_size = 1000
            start = 0
            all_rows = []

            while True:
                response = (
                    supabase
                    .table("parts")
                    .select("*")
                    .range(start, start + page_size - 1)
                    .execute()
                )

                data = response.data
                if not data:
                    break

                all_rows.extend(data)
                start += page_size

            if not all_rows:
                return pd.DataFrame(columns=["Parte", "Tipo"])

            df = pd.DataFrame(all_rows)

            df.columns = df.columns.str.strip().str.lower()

            df = df.rename(columns={
                "parte": "Parte",
                "tipo": "Tipo"
            })

            return df

        # =================================
        # Title
        # =================================
        st.title("📋 Autorización y Actualización de Pases de Taller")

        # =================================
        # KPI STRIP
        # =================================
        st.markdown("### Resumen general")

        total_ordenes = len(pases_df)

        def porcentaje(n):
            if total_ordenes == 0:
                return 0
            return round((n / total_ordenes) * 100, 1)

        pendientes = len(
            pases_df[pases_df["Estado"] == "Inicio / Nuevo"]
        )

        en_proceso = len(
            pases_df[pases_df["Estado"] == "En Curso / Proceso"]
        )

        completadas = len(
            pases_df[pases_df["Estado"] == "Cerrado / Terminado"]
        )

        canceladas = len(
            pases_df[pases_df["Estado"] == "Cerrado / Cancelado"]
        )

        k1, k2, k3, k4 = st.columns(4)

        def postit(col, titulo, valor, pct, color):
            with col:
                st.markdown(
                    f"""
                    <div style="
                        background:{color};
                        padding:18px;
                        border-radius:14px;
                        text-align:center;
                        box-shadow:0 4px 10px rgba(0,0,0,0.08);
                        color:#111;
                    ">
                        <div style="font-size:0.9rem; font-weight:700;">{titulo}</div>
                        <div style="font-size:2rem; font-weight:900; margin-top:6px;">{valor}</div>
                        <div style="font-size:0.8rem; opacity:0.8;">{pct}% del total</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        postit(k1, "Solicitudes Pendientes", pendientes, porcentaje(pendientes), "#FFF3CD")
        postit(k2, "Órdenes en Proceso", en_proceso, porcentaje(en_proceso), "#E2E3FF")
        postit(k3, "Órdenes Terminadas", completadas, porcentaje(completadas), "#D4EDDA")
        postit(k4, "Canceladas", canceladas, porcentaje(canceladas), "#F8D7DA")

        # =================================
        # COMPANY DISTRIBUTION and LOG
        # =================================
        st.divider()

        left, right = st.columns([2, 1])

        # =============================
        # LEFT → COMPANY SUMMARY
        # =============================
        with left:

            tab_empresa, tab_distribucion, tab_facturacion = st.tabs([
                "🏢 Órdenes por Empresa",
                "📊 Distribución de Órdenes",
                "🧾 Facturación"
            ])

            # ====================================================
            # TAB 1 - ÓRDENES POR EMPRESA
            # ====================================================
            with tab_empresa:

                if not pases_df.empty:

                    empresas = sorted(pases_df["Empresa"].dropna().unique())
                    total_global = len(pases_df)

                    for empresa in empresas:

                        df_emp = pases_df[pases_df["Empresa"] == empresa]
                        total_emp = len(df_emp)
                        pct = (total_emp / total_global * 100) if total_global else 0

                        pendientes = len(
                            df_emp[df_emp["Estado"] == "Inicio / Nuevo"]
                        )

                        proceso = len(
                            df_emp[df_emp["Estado"] == "En Curso / Proceso"]
                        )

                        completadas = len(
                            df_emp[df_emp["Estado"] == "Cerrado / Terminado"]
                        )

                        canceladas = len(
                            df_emp[df_emp["Estado"] == "Cerrado / Cancelado"]
                        )

                        with st.container(border=True):

                            st.markdown(f"**{empresa}**")
                            st.caption(f"Total: {total_emp} ({pct:.1f}%)")

                            c1, c2, c3, c4 = st.columns(4)

                            c1.metric("Pendientes", pendientes)
                            c2.metric("Proceso", proceso)
                            c3.metric("Completadas", completadas)
                            c4.metric("Canceladas", canceladas)

                else:
                    st.info("No hay datos.")

            # ====================================================
            # TAB 2 - DISTRIBUCIÓN
            # ====================================================
            with tab_distribucion:

                @st.cache_data(ttl=300)
                def cargar_tipos_parte():

                    supabase = get_supabase_client()

                    page_size = 1000
                    start = 0
                    all_rows = []

                    while True:
                        response = (
                            supabase
                            .table("SERVICES")
                            .select('"Tipo De Parte"')
                            .range(start, start + page_size - 1)
                            .execute()
                        )

                        data = response.data

                        if not data:
                            break

                        all_rows.extend(data)
                        start += page_size

                    if not all_rows:
                        return pd.DataFrame(columns=["Tipo De Parte"])

                    df = pd.DataFrame(all_rows)

                    if "Tipo De Parte" not in df.columns:
                        return pd.DataFrame(columns=["Tipo De Parte"])

                    df["Tipo De Parte"] = (
                        df["Tipo De Parte"]
                        .fillna("")
                        .astype(str)
                        .str.strip()
                    )

                    df = df[
                        (df["Tipo De Parte"] != "")
                        & (df["Tipo De Parte"].str.lower() != "nan")
                        & (df["Tipo De Parte"].str.lower() != "none")
                        & (df["Tipo De Parte"].str.lower() != "null")
                    ]

                    return df


                tipos_df = cargar_tipos_parte()

                if tipos_df.empty:
                    st.info("No hay datos disponibles en Tipo De Parte.")
                else:

                    conteo_tipos = (
                        tipos_df["Tipo De Parte"]
                        .value_counts()
                        .reset_index()
                    )

                    conteo_tipos.columns = ["Tipo De Parte", "Cantidad"]

                    total_tipos = conteo_tipos["Cantidad"].sum()

                    rows_html = ""

                    for _, row in conteo_tipos.iterrows():

                        tipo = row["Tipo De Parte"]
                        cantidad = int(row["Cantidad"])
                        porcentaje = round((cantidad / total_tipos) * 100, 1) if total_tipos else 0
                        progress_width = int((cantidad / total_tipos) * 100) if total_tipos else 0

                        rows_html += f"""
                        <div style="margin-bottom:14px;">

                            <div style="
                                display:flex;
                                justify-content:space-between;
                                font-size:0.85rem;
                                font-weight:700;
                                margin-bottom:6px;
                                color:#111;
                            ">
                                <span>{tipo}</span>
                                <span>{cantidad} ({porcentaje}%)</span>
                            </div>

                            <div style="
                                width:100%;
                                height:12px;
                                background:#f1ead0;
                                border-radius:999px;
                                overflow:hidden;
                            ">
                                <div style="
                                    width:{progress_width}%;
                                    height:100%;
                                    background:#BFA75F;
                                    border-radius:999px;
                                "></div>
                            </div>

                        </div>
                        """

                    distribution_html = f"""
                    <div style="padding:12px;">
                        <div style="
                            background:#fff7d6;
                            padding:22px;
                            border-radius:16px;
                            box-shadow:0 4px 10px rgba(0,0,0,0.08);
                            color:#111;
                            font-family:sans-serif;
                        ">

                            <div style="
                                font-size:1rem;
                                font-weight:900;
                                margin-bottom:18px;
                                color:#111;
                            ">
                                Distribución por Actividad
                            </div>

                            {rows_html}

                        </div>
                    </div>
                    """

                    # ====================================================
                    # TAB 2 - ESTATUS
                    # ====================================================
                    conteo_estados = (
                        pases_df["Estado"]
                        .fillna("Sin Estado")
                        .astype(str)
                        .value_counts()
                        .reset_index()
                    )

                    conteo_estados.columns = ["Estado", "Cantidad"]

                    total_estados = conteo_estados["Cantidad"].sum()

                    rows_estado = ""

                    for _, row in conteo_estados.iterrows():

                        estado = row["Estado"]
                        cantidad = int(row["Cantidad"])

                        porcentaje = round((cantidad / total_estados) * 100, 1) if total_estados else 0
                        progress_width = int((cantidad / total_estados) * 100) if total_estados else 0

                        rows_estado += f"""
                        <div style="margin-bottom:14px;">

                            <div style="
                                display:flex;
                                justify-content:space-between;
                                font-size:0.85rem;
                                font-weight:700;
                                margin-bottom:6px;
                                color:#111;
                            ">
                                <span>{estado}</span>
                                <span>{cantidad} ({porcentaje}%)</span>
                            </div>

                            <div style="
                                width:100%;
                                height:12px;
                                background:#f1ead0;
                                border-radius:999px;
                                overflow:hidden;
                            ">
                                <div style="
                                    width:{progress_width}%;
                                    height:100%;
                                    background:#BFA75F;
                                    border-radius:999px;
                                "></div>
                            </div>

                        </div>
                        """

                    estado_html = f"""
                    <div style="padding:12px;">
                        <div style="
                            background:#fff7d6;
                            padding:22px;
                            border-radius:16px;
                            box-shadow:0 4px 10px rgba(0,0,0,0.08);
                            color:#111;
                            font-family:sans-serif;
                        ">

                            <div style="
                                font-size:1rem;
                                font-weight:900;
                                margin-bottom:18px;
                                color:#111;
                            ">
                                Distribución por Estado
                            </div>

                            {rows_estado}

                        </div>
                    </div>
                    """
            
                    # ====================================================
                    # TAB 2 - TIPO DE PROVEEDOR
                    # ====================================================

                    conteo_proveedor = (
                        pases_df["Tipo de Proveedor"]
                        .fillna("Sin Tipo")
                        .astype(str)
                        .str.strip()
                        .value_counts()
                        .reset_index()
                    )

                    conteo_proveedor.columns = ["Tipo", "Cantidad"]

                    total_proveedor = conteo_proveedor["Cantidad"].sum()

                    rows_proveedor = ""

                    for _, row in conteo_proveedor.iterrows():

                        tipo = row["Tipo"]
                        cantidad = int(row["Cantidad"])

                        porcentaje = (
                            round((cantidad / total_proveedor) * 100, 1)
                            if total_proveedor else 0
                        )

                        progress_width = (
                            int((cantidad / total_proveedor) * 100)
                            if total_proveedor else 0
                        )

                        rows_proveedor += f"""
                        <div style="margin-bottom:14px;">

                            <div style="
                                display:flex;
                                justify-content:space-between;
                                font-size:0.85rem;
                                font-weight:700;
                                margin-bottom:6px;
                                color:#111;
                            ">
                                <span>{tipo}</span>
                                <span>{cantidad} ({porcentaje}%)</span>
                            </div>

                            <div style="
                                width:100%;
                                height:12px;
                                background:#f1ead0;
                                border-radius:999px;
                                overflow:hidden;
                            ">
                                <div style="
                                    width:{progress_width}%;
                                    height:100%;
                                    background:#BFA75F;
                                    border-radius:999px;
                                "></div>
                            </div>

                        </div>
                        """

                    proveedor_html = f"""
                    <div style="padding:12px;">
                        <div style="
                            background:#fff7d6;
                            padding:22px;
                            border-radius:16px;
                            box-shadow:0 4px 10px rgba(0,0,0,0.08);
                            color:#111;
                            font-family:sans-serif;
                        ">

                            <div style="
                                font-size:1rem;
                                font-weight:900;
                                margin-bottom:18px;
                                color:#111;
                            ">
                                Distribución por Tipo de Proveedor
                            </div>

                            {rows_proveedor}

                        </div>
                    </div>
                    """
                    dashboard_html = (
                        distribution_html
                        + estado_html
                        + proveedor_html
                    )

                    components.html(dashboard_html, height=1050)

            # ====================================================
            # TAB 3 - FACTURACIÓN
            # ====================================================
            with tab_facturacion:

                if not pases_df.empty:

                    # =============================================
                    # FILTER INPUTS
                    # =============================================
                    fcol1, fcol2 = st.columns(2)

                    with fcol1:
                        filtro_folio_fact = st.text_input("Filtrar por No. de Folio")

                    with fcol2:
                        filtro_factura_fact = st.text_input("Filtrar por No. de Factura")

                    # CLOSE FACTURA MODAL IF USER STARTS FILTERING
                    if filtro_folio_fact or filtro_factura_fact:
                        st.session_state.modal_factura = None

                    # =============================================
                    # MERGE ALL ORDERS WITH FACTURAS
                    # =============================================
                    base = pases_df.copy()

                    if not facturas_df.empty:
                        merged = base.merge(
                            facturas_df[["NoFolio", "No. de Factura"]],
                            on="NoFolio",
                            how="left"
                        )
                    else:
                        merged = base.copy()
                        merged["No. de Factura"] = None

                    # =============================================
                    # APPLY FILTERS
                    # =============================================
                    if filtro_folio_fact:
                        merged = merged[
                            merged["NoFolio"]
                            .astype(str)
                            .str.contains(filtro_folio_fact, case=False, na=False)
                        ]

                    if filtro_factura_fact:
                        merged = merged[
                            merged["No. de Factura"]
                            .astype(str)
                            .str.contains(filtro_factura_fact, case=False, na=False)
                        ]

                    # =============================================
                    # LIMIT TO 5 POST-ITS PER ROW
                    # =============================================
                    merged = merged.head(15)

                    if merged.empty:
                        st.info("No hay resultados con los filtros aplicados.")
                    else:
                        for row_start in range(0, len(merged), 5):

                            cols = st.columns(5)

                            for col, (_, r) in zip(cols, merged.iloc[row_start:row_start + 5].iterrows()):

                                with col:
                                    folio = r.get("NoFolio", "")
                                    estado = r.get("Estado", "")
                                    factura_raw = r.get("No. de Factura")

                                    factura_vacia = (
                                        pd.isna(factura_raw)
                                        or str(factura_raw).strip() == ""
                                    )

                                    if factura_vacia:
                                        factura = "-"
                                        label_btn = "Agregar Factura"
                                    else:
                                        factura = str(factura_raw)
                                        label_btn = "Ver"

                                    factura_html = f"""
                                    <div style="padding:6px;">
                                        <div style="
                                            background:#ffe2e2;
                                            padding:14px;
                                            border-radius:16px;
                                            box-shadow:0 4px 10px rgba(0,0,0,0.08);
                                            color:#111;
                                            min-height:120px;
                                            font-family:sans-serif;
                                        ">
                                            <div style="font-weight:900;">{folio}</div>

                                            <hr style="margin:6px 0">

                                            <div style="
                                                font-size:0.8rem;
                                                font-weight:700;
                                                color:#721c24;
                                            ">
                                                {estado}
                                            </div>

                                            <div style="
                                                margin-top:8px;
                                                font-size:0.75rem;
                                            ">
                                                No. de Factura: {factura}
                                            </div>
                                        </div>
                                    </div>
                                    """
                                    components.html(factura_html, height=160)

                                    # View facturas
                                    if st.button(
                                        label_btn,
                                        key=f"fact_btn_{folio}",
                                        use_container_width=True
                                    ):
                                        st.session_state.modal_factura = {
                                            "NoFolio": folio,
                                            "NoFactura": None if factura_vacia else factura
                                        }
                                        st.session_state.modal_factura_open = True

                        else:
                            st.info("No hay datos disponibles.")

        # =============================
        # LATEST ACTIVITY
        # =============================
        with right:
            st.markdown("### Última actividad")

            if audit_df.empty:
                st.info("Sin actividad registrada.")
            else:

                audit_sorted = (
                    audit_df[
                        audit_df["Empresa"].isin(allowed_companies)
                    ]
                    .head(9)
                )

                rows_html = ""

                for _, row in audit_sorted.iterrows():

                    timestamp = row.get("Timestamp")
                    usuario = html.escape(str(row.get("Usuario", "")))
                    empresa = html.escape(str(row.get("Empresa", "")))
                    folio = html.escape(str(row.get("No. de Folio", "")))
                    tipo = html.escape(str(row.get("Tipo Cambio", "")))
                    estado_nuevo = html.escape(str(row.get("Estado Nuevo", "")))
                    oste_nuevo = html.escape(str(row.get("OSTE Nuevo", "")))
                    comentario = html.escape(str(row.get("Comentario", "")))

                    fecha_txt = (
                        timestamp.strftime("%Y-%m-%d %H:%M")
                        if pd.notna(timestamp)
                        else ""
                    )

                    detalle = tipo

                    if estado_nuevo:
                        detalle += f" → {estado_nuevo}"

                    if oste_nuevo:
                        detalle += f" (OSTE: {oste_nuevo})"

                    if comentario:
                        comentario_safe = html.escape(str(comentario))
                        detalle += f" — {comentario_safe}"

                    rows_html += f"""
                    <div style="
                        margin-bottom:10px;
                        padding-bottom:8px;
                        border-bottom:1px solid #eee;
                    ">
                        <div style="font-size:0.75rem; opacity:0.7;">
                            {fecha_txt}
                        </div>
                        <div style="font-weight:700;">
                            {folio} — {empresa}
                        </div>
                        <div style="font-size:0.8rem;">
                            {detalle}
                        </div>
                        <div style="font-size:0.75rem; opacity:0.6;">
                            por {usuario}
                        </div>
                    </div>
                    """

                st.markdown(
                    f"""
                    <div style="
                        background:#ffffff;
                        padding:18px;
                        border-radius:14px;
                        box-shadow:0 3px 8px rgba(0,0,0,0.06);
                        color:#111;
                    ">
                        {rows_html}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        # =================================
        # Session state defaults
        # =================================
        st.session_state.setdefault("buscar_trigger", False)
        st.session_state.setdefault("modal_reporte", None)
        st.session_state.setdefault("modal_factura", None)
        st.session_state.setdefault("modal_factura_open", False)
        st.session_state.setdefault("refaccion_seleccionada", None)
        st.session_state.setdefault(
            "servicios_df",
            pd.DataFrame(columns=[
                "Parte",
                "Tipo De Parte",
                "Posicion",
                "Cantidad"
            ])
        )

        # =================================
        # PASES DE TALLER
        # =================================
        def safe(x):
            if pd.isna(x) or x is None:
                return ""
            return str(x)

        def render_pases_tab(
            source_df,
            estado_label,
            session_key,
            button_prefix,
        ):
            source_df = source_df.sort_values(
                "Fecha",
                ascending=False
            )

            if source_df.empty:
                st.info(f"No hay pases en estado {estado_label}.")
                return

            CARDS_PER_PAGE = 10

            st.session_state.setdefault(session_key, 0)

            total_pages = max(
                1,
                (len(source_df) + CARDS_PER_PAGE - 1) // CARDS_PER_PAGE
            )

            st.session_state[session_key] = min(
                st.session_state[session_key],
                total_pages - 1
            )

            start = st.session_state[session_key] * CARDS_PER_PAGE
            end = start + CARDS_PER_PAGE

            page_df = source_df.iloc[start:end]

            # ============================
            # CARDS
            # ============================

            for row_start in range(0, len(page_df), 5):

                cols = st.columns(5)

                for col, (_, r) in zip(
                    cols,
                    page_df.iloc[row_start:row_start + 5].iterrows()
                ):

                    with col:

                        folio = safe(r.get("NoFolio"))
                        tipo_unidad = safe(r.get("Tipo de Unidad"))
                        fecha = r.get("Fecha")
                        fecha = fecha.date() if pd.notna(fecha) else ""
                        unidad = safe(r.get("No. de Unidad"))
                        capturo = safe(r.get("Capturo"))
                        descripcion = safe(r.get("Descripcion Problema"))

                        if len(descripcion) > 120:
                            descripcion = descripcion[:120] + "..."

                        html = f"""
                        <div style="padding:6px;">
                            <div style="
                                background:#fff7d6;
                                padding:14px;
                                border-radius:16px;
                                box-shadow:0 4px 10px rgba(0,0,0,0.08);
                                color:#111;
                                min-height:160px;
                                font-family:sans-serif;
                            ">

                                <div style="font-weight:900;">{folio}</div>
                                <div style="font-size:0.8rem;">{tipo_unidad}</div>
                                <div style="font-size:0.8rem;">{fecha}</div>

                                <hr style="margin:6px 0">

                                <div style="font-size:0.8rem;">{unidad}</div>

                                <div style="
                                    font-size:0.75rem;
                                    margin-top:6px;
                                    padding:6px;
                                    background:#fff;
                                    border-radius:8px;
                                    box-shadow: inset 0 0 3px rgba(0,0,0,0.05);
                                ">
                                    {descripcion}
                                </div>

                                <div style="
                                    margin-top:6px;
                                    font-size:0.75rem;
                                    font-weight:700;
                                    color:#856404;
                                ">
                                    {estado_label}
                                </div>

                                <div style="
                                    font-size:0.75rem;
                                    margin-top:4px;
                                    opacity:0.8;
                                ">
                                    Capturó: {capturo}
                                </div>

                            </div>
                        </div>
                        """

                        components.html(html, height=220)

                        editable = r.get("Estado") in [
                            "Inicio / Nuevo",
                            "En Curso / Proceso"
                        ]

                        button_text = "✏ Editar" if editable else "👁 Ver"

                        if st.button(
                            button_text,
                            key=f"{button_prefix}_{folio}",
                            use_container_width=True,
                        ):

                            st.session_state.modal_factura = None
                            st.session_state.modal_factura_open = False

                            st.session_state.modal_reporte = r.to_dict()

                            st.session_state.servicios_df = cargar_servicios_folio(
                                r["NoFolio"]
                            )

            # ============================
            # PAGINATION
            # ============================

            st.divider()

            c1, c2, c3 = st.columns([1, 2, 1])

            with c1:
                if st.button(
                    "⬅ Anterior",
                    key=f"prev_{button_prefix}",
                    disabled=st.session_state[session_key] == 0,
                    use_container_width=True,
                ):
                    st.session_state[session_key] -= 1
                    st.rerun()

            with c2:
                st.markdown(
                    f"<div style='text-align:center;font-weight:700;'>"
                    f"Página {st.session_state[session_key] + 1} de {total_pages}"
                    f"</div>",
                    unsafe_allow_html=True,
                )

            with c3:
                if st.button(
                    "Siguiente ➡",
                    key=f"next_{button_prefix}",
                    disabled=st.session_state[session_key] >= total_pages - 1,
                    use_container_width=True,
                ):
                    st.session_state[session_key] += 1
                    st.rerun()

        st.subheader("Pases de Taller")

        tab_nuevos, tab_proceso, tab_terminados = st.tabs([
            "🆕 Pases Nuevos",
            "🔧 En Curso / Proceso",
            "✅ Pases Terminados"
        ])

        with tab_nuevos:
            render_pases_tab(
                pases_df[pases_df["Estado"] == "Inicio / Nuevo"],
                "Inicio / Nuevo",
                "page_nuevos",
                "nuevo",
            )

        with tab_proceso:
            render_pases_tab(
                pases_df[pases_df["Estado"] == "En Curso / Proceso"],
                "En Curso / Proceso",
                "page_proceso",
                "proceso",
            )

        with tab_terminados:
            render_pases_tab(
                pases_df[
                    pases_df["Estado"].isin([
                        "Cerrado / Terminado",
                        "Cerrado / Cancelado",
                    ])
                ],
                "Cerrado",
                "page_terminados",
                "terminado",
            )


        # =================================
        # FACTURA MODAL
        # =================================
        if st.session_state.get("modal_factura") and st.session_state.get("modal_factura_open"):

            data_fact = st.session_state.modal_factura

            @st.dialog("Factura")
            def modal_factura():

                folio = data_fact["NoFolio"]
                factura_actual = data_fact["NoFactura"]

                st.markdown(f"**No. de Folio:** {folio}")

                factura_vacia = (
                    factura_actual is None
                    or str(factura_actual).strip() == ""
                )

                nueva_factura = st.text_input(
                    "No. de Factura",
                    value="" if factura_vacia else factura_actual,
                    disabled=not factura_vacia
                )

                st.divider()

                # =================================
                # BUTTON LOGIC
                # =================================
                if factura_vacia:
                    label_btn = "Aceptar / Guardar"
                else:
                    label_btn = "Aceptar / Cerrar"

                if st.button(label_btn, type="primary"):

                    # If editable and user typed something → save
                    if factura_vacia and nueva_factura.strip() != "":
                        guardar_factura(folio, nueva_factura.strip())
                        refresh_cached_data()

                    st.session_state.modal_factura = None
                    st.session_state.modal_factura_open = False
                    st.rerun()

            modal_factura()

        # =================================
        # BUSCAR
        # =================================
        st.divider()

        tab_buscar, tab_reportes = st.tabs([
            "🔍 Buscar Pase de Taller",
            "📄 Descarga y Consulta de Reportes"
        ])

        with tab_buscar:

            st.divider()
            st.subheader("Buscar Pase de Taller")

            empresas = sorted(pases_df["Empresa"].dropna().unique()) if not pases_df.empty else []

            # =================================
            # ROW 1
            # =================================
            f1, f2, f3, f4, f5 = st.columns(5)

            with f1:
                f_folio = st.text_input("No. de Folio")

            with f2:
                f_factura = st.text_input("No. de Factura")

            with f3:
                f_oste = st.text_input("OSTE")

            with f4:
                tipos_proveedor = sorted(
                    pases_df["Tipo de Proveedor"]
                    .dropna()
                    .astype(str)
                    .unique()
                )

                f_tipo_proveedor = st.selectbox(
                    "Tipo de Proveedor",
                    ["Todos"] + tipos_proveedor,
                )

            with f5:
                f_empresa = st.selectbox(
                    "Empresa",
                    ["Selecciona empresa"] + empresas,
                )

            # =================================
            # ROW 2
            # =================================
            f6, f7, f8, f9, f10 = st.columns(5)

            with f6:

                unidades = (
                    sorted(
                        pases_df["No. de Unidad"]
                        .dropna()
                        .astype(str)
                        .unique()
                    )
                    if not pases_df.empty and "No. de Unidad" in pases_df.columns
                    else []
                )

                f_unidad = st.selectbox(
                    "No. de Unidad",
                    ["Selecciona unidad"] + unidades,
                )

            with f7:

                f_estado = st.selectbox(
                    "Estado",
                    [
                        "Selecciona estado",
                        "Inicio / Nuevo",
                        "En Curso / Proceso",
                        "Cerrado / Terminado",
                        "Cerrado / Cancelado",
                    ],
                )

            with f8:
                f_fecha = st.date_input(
                    "Fecha de Captura",
                    value=None,
                )

            with f9:
                buscar = st.button(
                    "🔍 Buscar",
                    use_container_width=True,
                )

            with f10:
                limpiar = st.button(
                    "🧹 Limpiar",
                    use_container_width=True,
                )

            # =================================
            # BUTTONS
            # =================================
            if buscar:
                st.session_state.buscar_trigger = True
                st.session_state.modal_reporte = None
                st.session_state.modal_factura = None
                st.session_state.modal_factura_open = False

            if limpiar:
                st.session_state.buscar_trigger = False
                st.session_state.modal_reporte = None
                st.session_state.modal_factura = None
                st.session_state.modal_factura_open = False
                st.rerun()

            # =================================
            # RESULTADOS
            # =================================
            if st.session_state.buscar_trigger:

                resultados = pases_df.copy()

                if not facturas_df.empty:

                    resultados = resultados.merge(
                        facturas_df[
                            ["NoFolio", "No. de Factura"]
                        ],
                        on="NoFolio",
                        how="left",
                    )
                # FOLIO
                if f_folio:
                    resultados = resultados[resultados["NoFolio"].str.contains(f_folio)]
                # NO. FACTURA
                if f_factura:
                    resultados = resultados[
                        resultados["No. de Factura"]
                        .fillna("")
                        .astype(str)
                        .str.contains(
                            f_factura,
                            case=False,
                            na=False,
                        )
                    ]
                # OSTE
                if f_oste:
                    resultados = resultados[
                        resultados["Oste"]
                        .fillna("")
                        .astype(str)
                        .str.contains(
                            f_oste,
                            case=False,
                            na=False,
                        )
                    ]
                # TIPO PROVEEDOR
                if f_tipo_proveedor != "Todos":
                    resultados = resultados[
                        resultados["Tipo de Proveedor"] == f_tipo_proveedor
                    ]

                if f_empresa != "Selecciona empresa":
                    resultados = resultados[resultados["Empresa"] == f_empresa]

                if f_estado != "Selecciona estado":
                    resultados = resultados[resultados["Estado"] == f_estado]

                if f_unidad != "Selecciona unidad":
                    resultados = resultados[
                        resultados["No. de Unidad"].astype(str) == f_unidad]

                if f_fecha:
                    resultados = resultados[resultados["Fecha"].dt.date == f_fecha]

                st.divider()
                st.subheader("Resultados")

                h1, h2, h3, h4, h5, h6, h7, h8, h9, h10 = st.columns(
                    [1, 2, 2, 2, 2, 2, 2, 2, 3, 2]
                )

                h1.markdown("**Acción**")
                h2.markdown("**Folio**")
                h3.markdown("**Factura**")
                h4.markdown("**OSTE**")
                h5.markdown("**Tipo Prov.**")
                h6.markdown("**Empresa**")
                h7.markdown("**Unidad**")
                h8.markdown("**Estado**")
                h9.markdown("**Descripción**")
                h10.markdown("**Fecha**")

                st.divider()

                for _, row in resultados.iterrows():
                    c1, c2, c3, c4, c5, c6, c7, c8, c9, c10 = st.columns(
                        [1, 2, 2, 2, 2, 2, 2, 2, 3, 2]
                    )

                    editable = row["Estado"] in [
                        "Inicio / Nuevo",
                        "En Curso / Proceso"
                    ]

                    # ======================================================
                    # BUTTON COLUMN
                    # ======================================================
                    with c1:
                        label = "Editar" if editable else "Ver"
                        if st.button(label, key=f"accion_{row['NoFolio']}"):

                            st.session_state.modal_factura = None
                            st.session_state.modal_factura_open = False

                            st.session_state.modal_reporte = row.to_dict()

                            df = cargar_servicios_folio(row["NoFolio"])

                            st.session_state.servicios_df = df

                    # ======================================================
                    # INFO COLUMNS
                    # ======================================================
                    c2.write(row["NoFolio"])

                    c3.write("" if pd.isna(row.get("No. de Factura")) else row.get("No. de Factura"))

                    c4.write("" if pd.isna(row.get("Oste")) else row.get("Oste"))

                    c5.write(row.get("Tipo de Proveedor", ""))

                    c6.write(row["Empresa"])

                    c7.write(row.get("No. de Unidad", ""))

                    c8.write(row["Estado"])

                    descripcion = row.get("Descripcion Problema", "")
                    if isinstance(descripcion, str) and len(descripcion) > 80:
                        descripcion = descripcion[:80] + "..."

                    c9.write(descripcion)

                    c10.write(
                        row["Fecha"].date()
                        if pd.notna(row["Fecha"])
                        else ""
                    )


        with tab_reportes:

            st.info("🚧 Este módulo se encuentra en construcción.")

            st.markdown("""
        ### Descarga y Consulta de Reportes

        Esta sección permitirá consultar y descargar reportes consolidados de Pases de Taller.

        **Próximamente disponible.**
        """)

        # =================================
        # MODAL
        # =================================
        if st.session_state.modal_reporte:

            r = st.session_state.modal_reporte
            editable_estado = r["Estado"] in [
                "Inicio / Nuevo",
                "En Curso / Proceso"
            ]

            @st.dialog(
                "Detalle del Pase de Taller",
                width="large",
            )
            def modal():

                st.markdown(f"**No. de Folio:** {r.get('NoFolio', r.get('No. de Folio',''))}")
                st.markdown(f"**Empresa:** {r['Empresa']}")
                fecha_modal = r.get("Fecha")
                if pd.notna(fecha_modal):
                    try:
                        fecha_modal = pd.to_datetime(fecha_modal).strftime("%Y-%m-%d %H:%M")
                    except:
                        fecha_modal = str(fecha_modal)
                else:
                    fecha_modal = "-"

                st.markdown(f"**Fecha:** {fecha_modal}")
                st.markdown(f"**Capturó:** {r.get('Capturo', '')}")
                st.markdown(
                    f"**Tipo de Proveedor:** {clean(r.get('Tipo de Proveedor', ''))}"
                )

                st.markdown(
                    f"**Proveedor:** {clean(r.get('Proveedor', ''))}"
                )

                st.markdown(
                    f"**Razones:** {clean(r.get('Razones', ''))}"
                )
                st.markdown(f"**No. de Unidad:** {r.get('No. de Unidad', '')}")
                descripcion_actual = r.get("Descripcion Problema", "") or ""
                es_cerrado = r["Estado"].startswith("Cerrado")
                descripcion_editada = st.text_area(
                    "Descripción del Problema",
                    value=descripcion_actual,
                    height=120,
                    disabled=es_cerrado
                )

                st.divider()
                st.subheader("Información del Proveedor")

                es_cerrado = "Cerrado" in str(r.get("Estado", ""))

                tipo_proveedor = clean(r.get("Tipo de Proveedor", "")).lower()

                # ==========================================
                # NO. DE ORDEN (editable + no decimals)
                # ==========================================
                reporte_actual = r.get("No. de Reporte", "")

                if pd.notna(reporte_actual) and str(reporte_actual).strip() != "":
                    try:
                        reporte_actual = str(int(float(reporte_actual)))
                    except:
                        reporte_actual = str(reporte_actual).strip()
                else:
                    reporte_actual = ""

                reporte_editado = st.text_input(
                    "No. de Reporte",
                    value=reporte_actual,
                    disabled=es_cerrado
                )

                # ==========================================
                # OSTE (externo only)
                # editable until order is Cerrado
                # ==========================================
                if "interno" not in tipo_proveedor:
                    oste_val = st.text_input(
                        "OSTE",
                        value=clean(r.get("Oste", "")),
                        disabled=es_cerrado
                    )

                # ==========================================
                # SMART STATE VISIBILITY
                # ==========================================
                estado_actual = r["Estado"]

                transiciones = {
                    "Inicio / Nuevo": [
                        "En Curso / Proceso",
                        "Cerrado / Cancelado",
                    ],
                    "En Curso / Proceso": [
                        "Cerrado / Terminado",
                        "Cerrado / Cancelado",
                    ],
                }

                opciones_estado = [estado_actual] + transiciones.get(estado_actual, [])
                opciones_estado = list(dict.fromkeys(opciones_estado))

                nuevo_estado = st.selectbox(
                    "Estado",
                    opciones_estado,
                    index=0,
                    disabled=not editable_estado
                )

                editable_servicios = nuevo_estado == "En Curso / Proceso"

                st.divider()
                st.subheader("Servicios y Refacciones")

                catalogo = cargar_refacciones()

                # ==========================================
                # BUILD TIPO FILTER
                # ==========================================
                tipos_disponibles = []

                if catalogo is not None and not catalogo.empty:
                    tipos_disponibles = (
                        sorted(
                            catalogo["Tipo"]
                            .dropna()
                            .astype(str)
                            .unique()
                        )
                    )

                if catalogo is not None and not catalogo.empty:
                    # ==========================================
                    # TIPO FILTER SELECTBOX
                    # ==========================================
                    tipo_seleccionado = st.selectbox(
                        "Tipo",
                        ["Selecciona tipo"] + tipos_disponibles,
                        disabled=not editable_servicios
                    )

                    # ==========================================
                    # FILTER PARTES BASED ON TIPO
                    # ==========================================
                    if tipo_seleccionado != "Selecciona tipo":
                        catalogo_filtrado = catalogo[
                            catalogo["Tipo"] == tipo_seleccionado
                        ]
                    else:
                        catalogo_filtrado = catalogo

                    partes_opciones = (
                        catalogo_filtrado["Parte"]
                        .dropna()
                        .astype(str)
                        .tolist()
                    )

                    tipo_elegido = tipo_seleccionado != "Selecciona tipo"

                    st.session_state.refaccion_seleccionada = st.selectbox(
                        "Refacción / Servicio",
                        options=partes_opciones if tipo_elegido else [],
                        index=None,
                        disabled=(not editable_servicios or not tipo_elegido)
                    )

                else:
                    st.info("Catálogo no disponible para esta empresa.")

                # =====================================================
                # ADD ITEM
                # =====================================================
                if st.button(
                    "Agregar refacción",
                    disabled=not editable_servicios or not st.session_state.refaccion_seleccionada
                ):

                    parte_seleccionada = st.session_state.refaccion_seleccionada

                    fila = catalogo[
                        catalogo["Parte"] == parte_seleccionada
                    ].iloc[0]

                    if fila["Parte"] not in st.session_state.servicios_df["Parte"].values:

                        nueva = {
                            "Parte": fila["Parte"],
                            "Tipo De Parte": fila["Tipo"],
                            "Posicion": "",
                            "Cantidad": 1,
                        }

                        st.session_state.servicios_df = pd.concat(
                            [st.session_state.servicios_df, pd.DataFrame([nueva])],
                            ignore_index=True
                        )

                # =====================================================
                # EDITOR
                # =====================================================
                column_config = {
                    "Parte": st.column_config.TextColumn(required=False),
                    "Tipo De Parte": st.column_config.TextColumn(required=False),
                    "Posicion": st.column_config.TextColumn(),
                    "Cantidad": st.column_config.NumberColumn(min_value=1, step=1),
                }

                edited_df = st.data_editor(
                    st.session_state.servicios_df,
                    num_rows="dynamic",
                    hide_index=True,
                    disabled=not editable_servicios,
                    column_config=column_config,
                )

                # =====================================================
                # METRIC
                # =====================================================
                st.divider()
                c1, c2 = st.columns(2)

                with c1:
                    if st.button("Cancelar"):
                        st.session_state.modal_reporte = None
                        st.rerun()

                with c2:

                    mostrar_aceptar = True

                    label_btn = "Guardar cambios" if editable_estado else "Cerrar"

                    if mostrar_aceptar and st.button(label_btn, type="primary"):

                        usuario = (
                            st.session_state.user.get("name")
                            or st.session_state.user.get("email")
                        )
        
                        # =================================
                        # UPDATE DESCRIPCION IF CHANGED
                        # =================================
                        descripcion_original = descripcion_actual or ""
                        descripcion_nueva = descripcion_editada or ""

                        if descripcion_nueva.strip() != descripcion_original.strip():

                            actualizar_descripcion_pase(
                                r["Empresa"],
                                r["NoFolio"],
                                descripcion_nueva.strip()
                            )

                            registrar_cambio_log(
                                usuario=usuario,
                                empresa=r["Empresa"],
                                folio=r["NoFolio"],
                                tipo_cambio="Edición Descripción",
                                estado_anterior=r["Estado"],
                                estado_nuevo=r["Estado"],
                                comentario="Descripción modificada"
                            )

                        estado_actual = r["Estado"]

                        if nuevo_estado != estado_actual:

                            actualizar_estado_pase(
                                r["Empresa"],
                                r["NoFolio"],
                                nuevo_estado
                            )

                            registrar_cambio_log(
                                usuario=usuario,
                                empresa=r["Empresa"],
                                folio=r["NoFolio"],
                                tipo_cambio="Cambio Estado",
                                estado_anterior=estado_actual,
                                estado_nuevo=nuevo_estado,
                                oste_anterior=clean(r.get("Oste")),
                                oste_nuevo=clean(r.get("Oste"))
                            )

                        if "interno" not in tipo_proveedor:
                            if oste_val.strip() != clean(r.get("Oste")):

                                oste_anterior = clean(r.get("Oste"))
                                oste_nuevo = clean(oste_val)

                                actualizar_oste_pase(
                                    r["Empresa"],
                                    r["NoFolio"],
                                    oste_nuevo
                                )

                                registrar_cambio_log(
                                    usuario=usuario,
                                    empresa=r["Empresa"],
                                    folio=r["NoFolio"],
                                    tipo_cambio="Actualización OSTE",
                                    estado_anterior=nuevo_estado,
                                    estado_nuevo=nuevo_estado,
                                    oste_anterior=oste_anterior,
                                    oste_nuevo=oste_nuevo
                                )
                            
                        # =================================
                        # UPDATE NO. DE REPORTE IF CHANGED
                        # =================================
                        reporte_original = clean(
                            r.get("No. de Reporte", "")
                        )

                        try:
                            reporte_original = str(int(float(reporte_original))) if reporte_original else ""
                        except:
                            reporte_original = str(reporte_original).strip()

                        reporte_nuevo = clean(reporte_editado)

                        try:
                            reporte_nuevo = str(int(float(reporte_nuevo))) if reporte_nuevo else ""
                        except:
                            reporte_nuevo = str(reporte_nuevo).strip()

                        if reporte_nuevo != reporte_original:

                            actualizar_no_reporte_pase(
                                r["Empresa"],
                                r["NoFolio"],
                                reporte_nuevo
                            )

                            registrar_cambio_log(
                                usuario=usuario,
                                empresa=r["Empresa"],
                                folio=r["NoFolio"],
                                tipo_cambio="Actualización No. de Reporte",
                                estado_anterior=r["Estado"],
                                estado_nuevo=r["Estado"],
                                comentario=f"No. de Reporte actualizado: {reporte_original} → {reporte_nuevo}"
                            )

                        # =====================================================
                        # CREATE MILESTONE ROW IF NO REAL SERVICES
                        # =====================================================
                        df_serv = st.session_state.servicios_df

                        sin_partes = (
                            df_serv.empty
                            or "Parte" not in df_serv.columns
                            or df_serv["Parte"].astype(str).str.strip().eq("").all()
                        )

                        if sin_partes:
                            registrar_cambio_estado_sin_servicios(
                                r["NoFolio"],
                                usuario,
                                nuevo_estado
                            )

                        # Normalize edited dataframe
                        df_final = edited_df.copy()

                        # Ensure columns exist
                        if "Tipo De Parte" in df_final.columns:
                            df_final["Tipo De Parte"] = (
                                df_final["Tipo De Parte"]
                                .fillna("")
                                .astype(str)
                                .str.strip()
                            )

                            # If empty → default to Mano de Obra
                            df_final.loc[
                                df_final["Tipo De Parte"] == "",
                                "Tipo De Parte"
                            ] = "Mano de Obra"

                        # Clean Parte column as well
                        if "Parte" in df_final.columns:
                            df_final["Parte"] = (
                                df_final["Parte"]
                                .fillna("")
                                .astype(str)
                                .str.strip()
                            )

                        st.session_state.servicios_df = df_final

                        guardar_servicios_refacciones(
                            r["NoFolio"],
                            usuario,
                            st.session_state.servicios_df,
                            nuevo_estado
                        )
                        
                        refresh_cached_data()
                        st.session_state.modal_reporte = None
                        st.rerun()

            modal()
            st.session_state.modal_reporte = None

# =================================
# TAB 2 GESTION DE VIATICOS
# =================================
if has_viaticos:
    with tab_viaticos:

        if "gestion_viaticos" not in user_access:

            st.info("No tienes permisos para acceder a este módulo.")

        else:

            st.title("💳 Gestión de Viáticos")

            # =================================
            # RESEND CONFIG
            # =================================

            resend.api_key = (
                st.secrets["RESEND_API_KEY"]
            )

            # =================================
            # USER DATA
            # =================================
            user = st.session_state.user

            nombre_usuario = (
                user.get("name")
                or user.get("email")
                or ""
            )

            email_usuario = (
                user.get("email")
                or ""
            )

            # =================================
            # EMAIL CONFIG
            # =================================

            EMAILS_FIJOS = [

                "Maria.garcia@palosgarza.com",

                "cristobal.ochoa@set-freight.com",

                "practicas.auditoria@palosgarzalogistics.com"
            ]

            EMAILS_EMPRESA = {

                "SET FREIGHT": [

                    "karina.colina@palosgarza.com",

                    "cindy.gonzalez@palosgarza.com"
                ],

                "LINCOLN": [

                    "karina.colina@palosgarza.com",

                    "corina@palosgarza.com",

                    "ivonne.hernandez@palosgarza.com"
                ],

                "PICUS": [

                    "argelia.salinas@palosgarza.com"
                ],

                "IGLOO": [

                    "agustin.rodriguez@palosgarza.com"
                ],

                "SET LOGIS PLUS": [

                    "juan.santos@palosgarza.com"
                ]
            }

            # =================================
            # GET EMAIL FROM PROFILE
            # =================================

            def obtener_email_usuario(nombre_completo):

                try:

                    response = (
                        supabase
                        .table("profiles")
                        .select("email")
                        .eq(
                            "full_name",
                            nombre_completo
                        )
                        .limit(1)
                        .execute()
                    )

                    if (
                        response.data
                        and len(response.data) > 0
                    ):

                        return (
                            response
                            .data[0]
                            .get("email")
                        )

                except Exception as e:

                    st.warning(
                        f"Error obteniendo email: {e}"
                    )

                return None

            # =================================
            # EMAIL TEST MODE
            # =================================

            EMAIL_TEST_MODE = True
            EMAIL_TEST_RECIPIENT = (
                "aldo.sanchez@palosgarzalogistics.com"
            )

            def construir_destinatarios(
                empresa,
                email_usuario_actual,
                correo_creador=None
            ):

                if EMAIL_TEST_MODE:
                    return [EMAIL_TEST_RECIPIENT]

                destinatarios = []


                # =================================
                # LOGGED USER
                # =================================

                if (
                    email_usuario_actual
                    and email_usuario_actual not in destinatarios
                ):

                    destinatarios.append(
                        email_usuario_actual
                    )

                # =================================
                # CREATOR EMAIL
                # =================================

                if (
                    correo_creador
                    and correo_creador not in destinatarios
                ):

                    destinatarios.append(
                        correo_creador
                    )

                # =================================
                # FIXED EMAILS
                # =================================

                for correo in EMAILS_FIJOS:

                    if correo not in destinatarios:

                        destinatarios.append(correo)

                # =================================
                # CONDITIONAL EMAILS
                # =================================

                empresa = str(
                    empresa or ""
                ).strip().upper()

                correos_empresa = (
                    EMAILS_EMPRESA.get(
                        empresa,
                        []
                    )
                )

                for correo in correos_empresa:

                    if correo not in destinatarios:

                        destinatarios.append(correo)

                return destinatarios

            # =================================
            # EMAIL APROBACION / RECHAZO
            # =================================

            def enviar_correo_estatus_solicitud(

                destinatarios,
                folio,
                estatus,
                fecha_inicio,
                fecha_fin,
                motivo_viaje,
                observaciones,
                conceptos

            ):

                total_aprobado = 0.0

                conceptos_html = ""

                for item in conceptos:

                    tipo = item.get("Tipo", "")

                    descripcion = item.get(
                        "Descripcion",
                        ""
                    )

                    monto = float(
                        item.get(
                            "Monto",
                            0
                        ) or 0
                    )

                    moneda = item.get(
                        "Moneda",
                        "MXN"
                    )

                    aprobado = str(
                        item.get(
                            "Aprobado",
                            "Si"
                        )
                    )

                    razon = item.get(
                        "Razon",
                        ""
                    )

                    aprobado_texto = (
                        "🟢 APROBADO"
                        if aprobado in [
                            "Si",
                            "🟢 Si"
                        ]
                        else "🔴 RECHAZADO"
                    )

                    if aprobado in [
                        "Si",
                        "🟢 Si"
                    ]:

                        total_aprobado += monto

                    conceptos_html += f"""

                    <tr>

                        <td style="
                            border:1px solid #ccc;
                            padding:8px;
                        ">
                            {tipo}
                        </td>

                        <td style="
                            border:1px solid #ccc;
                            padding:8px;
                        ">
                            {descripcion}
                        </td>

                        <td style="
                            border:1px solid #ccc;
                            padding:8px;
                        ">
                            {moneda}
                        </td>

                        <td style="
                            border:1px solid #ccc;
                            padding:8px;
                        ">
                            ${monto:,.2f}
                        </td>

                        <td style="
                            border:1px solid #ccc;
                            padding:8px;
                            font-weight:700;
                        ">
                            {aprobado_texto}
                        </td>

                        <td style="
                            border:1px solid #ccc;
                            padding:8px;
                        ">
                            {razon}
                        </td>

                    </tr>
                    """

                if estatus in ["Aprobado", "Concluido"]:

                    color_estatus = "#10B981"

                elif estatus == "Rechazado":

                    color_estatus = "#EF4444"

                else:

                    color_estatus = "#38BDF8"

                html = f"""

                <div style="
                    font-family:Arial;
                    max-width:900px;
                    margin:auto;
                ">

                    <h2 style="
                        color:#151F6D;
                    ">
                        Actualización de Solicitud
                    </h2>

                    <h2 style="
                        color:{color_estatus};
                    ">
                        {estatus}
                    </h2>

                    <hr>

                    <p>
                        <b>Folio:</b>
                        {folio}
                    </p>

                    <p>
                        <b>Fecha Inicio:</b>
                        {fecha_inicio}
                    </p>

                    <p>
                        <b>Fecha Fin:</b>
                        {fecha_fin}
                    </p>

                    <p>
                        <b>Motivo del Viaje:</b>
                        {motivo_viaje}
                    </p>

                    <hr>

                    <h3>
                        Conceptos
                    </h3>

                    <table style="
                        width:100%;
                        border-collapse:collapse;
                    ">

                        <tr style="
                            background:#151F6D;
                            color:white;
                        ">

                            <th style="padding:10px;">
                                Tipo
                            </th>

                            <th style="padding:10px;">
                                Descripción
                            </th>

                            <th style="padding:10px;">
                                Moneda
                            </th>

                            <th style="padding:10px;">
                                Monto
                            </th>

                            <th style="padding:10px;">
                                Estatus
                            </th>

                            <th style="padding:10px;">
                                Razón
                            </th>

                        </tr>

                        {conceptos_html}

                    </table>

                    <h2 style="
                        margin-top:30px;
                        color:#BFA75F;
                    ">
                        TOTAL APROBADO:
                        ${total_aprobado:,.2f}
                    </h2>

                </div>
                """

                resend.Emails.send({

                    "from":
                        "onboarding@resend.dev",

                    "to":
                        destinatarios,

                    "subject":
                        folio,

                    "html":
                        html
                })

            # =================================
            # LOAD DATA
            # =================================

            @st.cache_data(ttl=30)
            def cargar_solicitudes():

                all_rows = []

                page_size = 1000
                start = 0

                while True:

                    response = (
                        supabase
                        .table("solicitud_viaje")
                        .select("*")
                        .order("created_at", desc=True)
                        .range(
                            start,
                            start + page_size - 1
                        )
                        .execute()
                    )

                    data = response.data or []

                    if len(data) == 0:
                        break

                    all_rows.extend(data)

                    if len(data) < page_size:
                        break

                    start += page_size

                return pd.DataFrame(all_rows)


            @st.cache_data(ttl=30)
            def cargar_comprobaciones():

                all_rows = []

                page_size = 1000
                start = 0

                while True:

                    response = (
                        supabase
                        .table("comprobacion_viaje")
                        .select("*")
                        .order("created_at", desc=True)
                        .range(
                            start,
                            start + page_size - 1
                        )
                        .execute()
                    )

                    data = response.data or []

                    if len(data) == 0:
                        break

                    all_rows.extend(data)

                    if len(data) < page_size:
                        break

                    start += page_size

                return pd.DataFrame(all_rows)


            df_solicitudes = cargar_solicitudes()
            df_comprobaciones = cargar_comprobaciones()

            # =================================
            # EMPTY DATAFRAME SAFETY
            # =================================

            if df_solicitudes.empty:

                df_solicitudes = pd.DataFrame(columns=[

                    "folio_solicitud",
                    "estatus",
                    "nombre_empleado_solicita",
                    "fecha_solicitud",
                    "total_estimado",
                    "created_at"
                ])

            if df_comprobaciones.empty:

                df_comprobaciones = pd.DataFrame(columns=[

                    "folio_solicitud",
                    "folio_comprobacion",
                    "estatus",
                    "nombre_empleado_solicita",
                    "conceptos",
                    "observaciones",
                    "total_comprobado",
                    "anticipo_viaje",
                    "diferencia_cargo_favor",
                    "created_at"
                ])

            # =================================
            # GLOBAL TOAST
            # =================================

            if "toast_actualizado" in st.session_state:

                st.toast(
                    st.session_state.toast_actualizado
                )

                del st.session_state[
                    "toast_actualizado"
                ]

            # =================================
            # KPI VALUES
            # =================================
            if "estatus" not in df_solicitudes.columns:
                df_solicitudes["estatus"] = "Pendiente"

            df_solicitudes["estatus"] = (
                df_solicitudes["estatus"]
                .fillna("Pendiente")
                .astype(str)
                .str.strip()
            )

            if "estatus" not in df_comprobaciones.columns:
                df_comprobaciones["estatus"] = "Pendiente"

            df_comprobaciones["estatus"] = (
                df_comprobaciones["estatus"]
                .fillna("Pendiente")
                .astype(str)
                .str.strip()
            )

            # =================================
            # KPI COUNTS
            # =================================
            total_registros = (
                df_solicitudes["folio_solicitud"]
                .astype(str)
                .str.strip()
                .nunique()
            )

            # PENDIENTES
            pendientes = len(
                df_solicitudes[
                    df_solicitudes["estatus"] == "Pendiente"
                ]
            )

            # AUTORIZADAS
            autorizados = len(
                df_solicitudes[
                    df_solicitudes["estatus"] == "Aprobado"
                ]
            )

            # VERIFICANDO
            verificando = len(
                df_solicitudes[
                    df_solicitudes["estatus"] == "Verificar"
                ]
            )

            # RECHAZADAS
            rechazados = len(
                df_solicitudes[
                    df_solicitudes["estatus"] == "Rechazado"
                ]
            )

            # =================================
            # CONCLUIDOS
            # =================================
            concluidos = len(
                df_solicitudes[
                    df_solicitudes["estatus"] == "Concluido"
                ]
            )

            # =================================
            # HEADER
            # =================================
            st.title("⚙ Gestión de Viáticos")

            # =================================
            # KPI CARDS
            # =================================
            kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)

            import streamlit.components.v1 as components

            def render_kpi_card(
                title,
                value,
                emoji,
                color,
            ):

                html = f"""
                <div style="padding:6px;">
                    <div style="
                        background:#FFF7D6;
                        padding:20px;
                        border-radius:18px;
                        box-shadow:0 4px 10px rgba(0,0,0,.10);
                        min-height:170px;
                        color:#111;
                        font-family:sans-serif;
                    ">

                        <div style="
                            color:#666666;
                            font-size:15px;
                            font-weight:600;
                        ">
                            {emoji} {title}
                        </div>

                        <div style="
                            text-align:center;
                            color:{color};
                            font-size:58px;
                            font-weight:800;
                            margin-top:40px;
                        ">
                            {value}
                        </div>

                    </div>
                </div>
                """

                components.html(html, height=240)

            with kpi1:

                render_kpi_card(
                    "Total",
                    total_registros,
                    "📊",
                    "#BFA75F"
                )

            with kpi2:

                render_kpi_card(
                    "Pendientes",
                    pendientes,
                    "⏳",
                    "#F59E0B"
                )

            with kpi3:

                render_kpi_card(
                    "Autorizadas",
                    autorizados,
                    "✅",
                    "#10B981"
                )

            with kpi4:

                render_kpi_card(
                    "Verificando",
                    verificando,
                    "🔎",
                    "#38BDF8"
                )

            with kpi5:

                render_kpi_card(
                    "Rechazadas",
                    rechazados,
                    "❌",
                    "#EF4444"
                )

            with kpi6:

                render_kpi_card(
                    "Concluidos",
                    concluidos,
                    "🏁",
                    "#8B5CF6"
                )

            st.markdown("<br><br>", unsafe_allow_html=True)

            # =================================
            # PENDIENTES SECTION
            # =================================
            st.header("📋 Solicitudes Pendientes")

            # Only pendientes
            df_pendientes = df_solicitudes[
                df_solicitudes["estatus"] == "Pendiente"
            ].copy()

            # Sort newest first
            if "created_at" in df_pendientes.columns:

                df_pendientes = df_pendientes.sort_values(
                    by="created_at",
                    ascending=False
                )

            # =================================
            # PAGINATION
            # =================================

            ENTRADAS_POR_PAGINA = 5

            total_entries = len(df_pendientes)

            total_paginas = max(
                1,
                (total_entries + ENTRADAS_POR_PAGINA - 1)
                // ENTRADAS_POR_PAGINA
            )

            if "pagina_viaticos" not in st.session_state:
                st.session_state.pagina_viaticos = 1

            pagina_actual = st.session_state.pagina_viaticos

            inicio = (
                (pagina_actual - 1)
                * ENTRADAS_POR_PAGINA
            )

            fin = inicio + ENTRADAS_POR_PAGINA

            df_pagina = df_pendientes.iloc[inicio:fin]

            # =================================
            # MODAL
            # =================================
            @st.dialog("Detalle de Solicitud")

            def modal_ver_solicitud(row):

                st.markdown(
                    "<h2 style='color:#151F6D;'>📋 Información General</h2>",
                    unsafe_allow_html=True
                )

                col1, col2 = st.columns(2)

                with col1:

                    st.markdown(
                        f"<span style='color:black;'><b>Folio:</b> {row.get('folio_solicitud', '')}</span>",
                        unsafe_allow_html=True
                    )

                    st.markdown(
                        f"<span style='color:black;'><b>Estatus:</b> {row.get('estatus', '')}</span>",
                        unsafe_allow_html=True
                    )

                    st.markdown(
                        f"<span style='color:black;'><b>Empresa Brinda Servicio:</b> {row.get('empresa_brinda_servicio', '')}</span>",
                        unsafe_allow_html=True
                    )

                    st.markdown(
                        f"<span style='color:black;'><b>Empleado Solicita:</b> {row.get('nombre_empleado_solicita', '')}</span>",
                        unsafe_allow_html=True
                    )

                    st.markdown(
                        f"<span style='color:black;'><b>Fecha Solicitud:</b> {row.get('fecha_solicitud', '')}</span>",
                        unsafe_allow_html=True
                    )

                    st.markdown(
                        f"<span style='color:black;'><b>Fecha Inicio:</b> {row.get('fecha_inicio', '')}</span>",
                        unsafe_allow_html=True
                    )

                    st.markdown(
                        f"<span style='color:black;'><b>Fecha Fin:</b> {row.get('fecha_fin', '')}</span>",
                        unsafe_allow_html=True
                    )

                with col2:

                    st.markdown(
                        f"<span style='color:black;'><b>Empresa Cargo Gastos:</b> {row.get('empresa_cargo_gastos', '')}</span>",
                        unsafe_allow_html=True
                    )

                    st.markdown(
                        f"<span style='color:black;'><b>Unidad Negocio:</b> {row.get('unidad_negocio', '')}</span>",
                        unsafe_allow_html=True
                    )

                    st.markdown(
                        f"<span style='color:black;'><b>Sucursal:</b> {row.get('sucursal', '')}</span>",
                        unsafe_allow_html=True
                    )

                    st.markdown(
                        f"<span style='color:black;'><b>Sucursal Especificar:</b> {row.get('sucursal_especificar', '')}</span>",
                        unsafe_allow_html=True
                    )

                    label_cliente = (
                        "Motivo del Viaje"
                        if str(
                            row.get(
                                "motivo_viaje",
                                ""
                            )
                        ).strip().upper() == "OTROS"
                        else "Nombre del Cliente"
                    )

                    st.markdown(
                        f"<span style='color:black;'><b>{label_cliente}:</b> {row.get('nombre_cliente', '')}</span>",
                        unsafe_allow_html=True
                    )

                    st.markdown(
                        f"<span style='color:black;'><b>Registro SAC Ventas?:</b> {row.get('folio_sac', '')}</span>",
                        unsafe_allow_html=True
                    )

                # =================================
                # MOTIVO VIAJE
                # =================================
                st.markdown("---")

                st.markdown("## ✈️ Motivo del Viaje")

                st.markdown(
                    f"""
                    <div style='
                        background-color:#F3F4F6;
                        padding:16px;
                        border-radius:12px;
                        border:1px solid rgba(191,167,95,0.25);
                        margin-bottom:20px;
                        white-space:pre-wrap;
                    '>
                        {row.get('motivo_viaje', '')}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                # =================================
                # OBSERVACIONES
                # =================================

                st.markdown(
                    "<h2 style='color:#151F6D;'>📝 Observaciones</h2>",
                    unsafe_allow_html=True
                )

                observaciones_edit = st.text_area(
                    label="",
                    value=row.get(
                        "observaciones",
                        ""
                    ),
                    height=150,
                    key=f"obs_edit_{row.get('id')}",
                    label_visibility="collapsed"
                )

                # =================================
                # CONCEPTOS
                # =================================

                st.markdown("---")

                st.markdown("## 💰 Conceptos")

                total_value = row.get(
                    "total_estimado",
                    0
                )

                try:
                    total_value = float(total_value)
                except:
                    total_value = 0

                st.markdown(
                    f"""
                    <div style='
                        font-size:24px;
                        font-weight:700;
                        color:#BFA75F;
                        margin-bottom:15px;
                    '>
                        Total Estimado: ${total_value:,.2f}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                conceptos = row.get(
                    "conceptos",
                    []
                )

                if conceptos:

                    try:

                        conceptos_final = []

                        for concepto in conceptos:

                            conceptos_final.append({

                                "Tipo":
                                    concepto.get(
                                        "Tipo",
                                        ""
                                    ),

                                "Descripcion":
                                    concepto.get(
                                        "Descripcion",
                                        ""
                                    ),

                                "Monto":
                                    concepto.get(
                                        "Monto",
                                        0
                                    ),
                                
                                "Tipo Cambio":
                                    concepto.get(
                                        "Tipo Cambio",
                                        ""
                                    ),

                                "Aprobado":
                                    "🟢 Si"
                                    if concepto.get(
                                        "Aprobado",
                                        "Si"
                                    ) in ["Si", "🟢 Si"]
                                    else "🔴 No",

                                "Razon":
                                    concepto.get(
                                        "Razon",
                                        ""
                                    )
                            })

                        df_conceptos = pd.DataFrame(
                            conceptos_final
                        )

                        edited_df = st.data_editor(

                            df_conceptos,

                            use_container_width=True,

                            hide_index=True,

                            num_rows="fixed",

                            column_config={

                                "Tipo":
                                    st.column_config.TextColumn(
                                        "Tipo",
                                        disabled=True
                                    ),

                                "Descripcion":
                                    st.column_config.TextColumn(
                                        "Descripcion",
                                        disabled=True
                                    ),

                                "Monto":
                                    st.column_config.NumberColumn(
                                        "Monto",
                                        disabled=True,
                                        format="$ %.2f"
                                    ),

                                "Aprobado":
                                    st.column_config.SelectboxColumn(
                                        "Aprobado",
                                        options=[
                                            "🟢 Si",
                                            "🔴 No"
                                        ],
                                        required=True
                                    ),

                                "Razon":
                                    st.column_config.TextColumn(
                                        "Razon"
                                    )
                            },

                            key=f"editor_conceptos_{row.get('id')}"
                        )

                        st.markdown("<br>", unsafe_allow_html=True)

                        if st.button(
                            "💾 Actualizar Solicitud",
                            use_container_width=True,
                            key=f"actualizar_sol_{row.get('id')}"
                        ):

                            conceptos_actualizados = (
                                edited_df.to_dict(
                                    orient="records"
                                )
                            )

                            # =================================
                            # RECALCULAR TOTAL ESTIMADO
                            # =================================

                            nuevo_total_estimado = 0.0

                            for item in conceptos_actualizados:

                                aprobado = str(
                                    item.get(
                                        "Aprobado",
                                        "🟢 Si"
                                    )
                                ).strip()

                                if aprobado in [
                                    "Si",
                                    "🟢 Si"
                                ]:

                                    try:

                                        nuevo_total_estimado += float(
                                            item.get(
                                                "Monto",
                                                0
                                            ) or 0
                                        )

                                    except:

                                        pass

                            supabase.table(
                                "solicitud_viaje"
                            ).update(
                                {
                                    "observaciones":
                                        observaciones_edit,

                                    "conceptos":
                                        conceptos_actualizados,

                                    "total_estimado":
                                        float(
                                            nuevo_total_estimado
                                        ),

                                    "fecha_actualizacion":
                                        datetime.now(
                                            timezone.utc
                                        ).isoformat()
                                }
                            ).eq(
                                "id",
                                row["id"]
                            ).execute()

                            st.cache_data.clear()

                            st.session_state.toast_actualizado = (
                                f"Folio "
                                f"{row.get('folio_solicitud', '')} "
                                f"actualizado con éxito"
                            )

                            st.rerun()

                    except Exception as e:

                        st.error(
                            f"Error leyendo conceptos: {e}"
                        )

                else:

                    st.info(
                        "No hay conceptos registrados."
                    )

            # =================================
            # GRID ENTRIES
            # =================================

            for idx, row in df_pagina.iterrows():

                with st.container(border=True):

                    col1, col2, col3, col4, col5, col6, col7 = st.columns(
                        [1, 2, 2, 2, 2, 1.2, 1.2]
                    )

                    # VER BUTTON
                    with col1:

                        if st.button(
                            "Ver",
                            key=f"ver_{idx}",
                            use_container_width=True
                        ):
                            modal_ver_solicitud(row)

                    # FOLIO
                    with col2:

                        st.caption("Folio")
                        st.write(f"**{row.get('folio_solicitud', '')}**")

                    # EMPLEADO
                    with col3:

                        st.caption("Empleado")
                        st.write(f"**{row.get('nombre_empleado_solicita', '')}**")

                    # FECHA
                    with col4:

                        st.caption("Fecha Solicitud")
                        st.write(f"**{row.get('fecha_solicitud', '')}**")

                    # TOTAL
                    with col5:

                        total_value = row.get("total_estimado", 0)

                        try:
                            total_value = float(total_value)
                        except Exception:
                            total_value = 0

                        st.caption("Total")
                        st.write(f"**${total_value:,.2f}**")

                    # APROBAR
                    with col6:

                        if st.button(
                            "Aprobar",
                            key=f"aprobar_{idx}",
                            use_container_width=True
                        ):

                            supabase.table(
                                "solicitud_viaje"
                            ).update(
                                {
                                    "estatus": "Aprobado",
                                    "fecha_actualizacion": datetime.now(
                                        timezone.utc
                                    ).isoformat()
                                }
                            ).eq(
                                "id",
                                row["id"]
                            ).execute()

                            # =================================
                            # GET CREATOR EMAIL
                            # =================================

                            correo_creador = (
                                obtener_email_usuario(
                                    row.get(
                                        "nombre_empleado_solicita",
                                        ""
                                    )
                                )
                            )

                            destinatarios = construir_destinatarios(

                                empresa=row.get(
                                    "empresa_brinda_servicio",
                                    ""
                                ),

                                email_usuario_actual=email_usuario,

                                correo_creador=correo_creador
                            )

                            # =================================
                            # SEND EMAIL
                            # =================================

                            try:

                                enviar_correo_estatus_solicitud(

                                    destinatarios=destinatarios,

                                    folio=row.get(
                                        "folio_solicitud",
                                        ""
                                    ),

                                    estatus="Aprobado",

                                    fecha_inicio=row.get(
                                        "fecha_inicio",
                                        ""
                                    ),

                                    fecha_fin=row.get(
                                        "fecha_fin",
                                        ""
                                    ),

                                    motivo_viaje=row.get(
                                        "motivo_viaje",
                                        ""
                                    ),

                                    observaciones=row.get(
                                        "observaciones",
                                        ""
                                    ),

                                    conceptos=row.get(
                                        "conceptos",
                                        []
                                    )
                                )

                            except Exception as e:

                                st.warning(
                                    f"No se pudo enviar correo: {e}"
                                )



                            st.success("Solicitud aprobada")
                            st.cache_data.clear()
                            st.rerun()

                    # RECHAZAR
                    with col7:

                        if st.button(
                            "Rechazar",
                            key=f"rechazar_{idx}",
                            use_container_width=True
                        ):

                            supabase.table(
                                "solicitud_viaje"
                            ).update(
                                {
                                    "estatus": "Rechazado",
                                    "fecha_actualizacion": datetime.now(
                                        timezone.utc
                                    ).isoformat()
                                }
                            ).eq(
                                "id",
                                row["id"]
                            ).execute()

                            # =================================
                            # GET CREATOR EMAIL
                            # =================================

                            correo_creador = (
                                obtener_email_usuario(
                                    row.get(
                                        "nombre_empleado_solicita",
                                        ""
                                    )
                                )
                            )

                            destinatarios = construir_destinatarios(

                                empresa=row.get(
                                    "empresa_brinda_servicio",
                                    ""
                                ),

                                email_usuario_actual=email_usuario,

                                correo_creador=correo_creador
                            )

                            # =================================
                            # SEND EMAIL
                            # =================================

                            try:

                                enviar_correo_estatus_solicitud(

                                    destinatarios=destinatarios,

                                    folio=row.get(
                                        "folio_solicitud",
                                        ""
                                    ),

                                    estatus="Rechazado",

                                    fecha_inicio=row.get(
                                        "fecha_inicio",
                                        ""
                                    ),

                                    fecha_fin=row.get(
                                        "fecha_fin",
                                        ""
                                    ),

                                    motivo_viaje=row.get(
                                        "motivo_viaje",
                                        ""
                                    ),

                                    observaciones=row.get(
                                        "observaciones",
                                        ""
                                    ),

                                    conceptos=row.get(
                                        "conceptos",
                                        []
                                    )
                                )

                            except Exception as e:

                                st.warning(
                                    f"No se pudo enviar correo: {e}"
                                )

                            st.error("Solicitud rechazada")
                            st.cache_data.clear()
                            st.rerun()

            # =================================
            # PAGINATION CONTROLS
            # =================================

            st.divider()

            p1, p2, p3 = st.columns([1,2,1])

            with p1:

                if st.button(
                    "⬅ Anterior",
                    disabled=st.session_state.pagina_viaticos <= 1,
                    use_container_width=True,
                    key="prev_pendientes"
                ):

                    st.session_state.pagina_viaticos -= 1
                    st.rerun()

            with p2:

                st.markdown(
                    f"""
                    <div style="
                        text-align:center;
                        padding-top:8px;
                        font-weight:700;
                        color:#151F6D;
                    ">
                        Página {st.session_state.pagina_viaticos} de {total_paginas}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            with p3:

                if st.button(
                    "Siguiente ➡",
                    disabled=(
                        st.session_state.pagina_viaticos
                        >= total_paginas
                    ),
                    use_container_width=True,
                    key="next_pendientes"
                ):

                    st.session_state.pagina_viaticos += 1
                    st.rerun()

            # =================================
            # COMPROBACIONES POR VERIFICAR
            # =================================

            st.header("🔎 Comprobaciones por Verificar")

            df_verificar = df_comprobaciones[
                df_comprobaciones["estatus"] == "Verificar"
            ].copy()

            # =================================
            # FILTERS
            # =================================

            filtro_col1, filtro_col2 = st.columns([2, 5])

            with filtro_col1:

                folios_disponibles = ["Todos"]

                if not df_verificar.empty:

                    folios_disponibles += sorted(
                        df_verificar["folio_solicitud"]
                        .dropna()
                        .astype(str)
                        .unique()
                        .tolist()
                    )

                filtro_folio_verificar = st.selectbox(
                    "Filtrar por Folio",
                    folios_disponibles,
                    key="filtro_folio_verificar"
                )

            # APPLY FILTER
            if filtro_folio_verificar != "Todos":

                df_verificar = df_verificar[
                    df_verificar["folio_solicitud"]
                    .astype(str)
                    == str(filtro_folio_verificar)
                ]

            # =================================
            # SORT
            # =================================

            if "created_at" in df_verificar.columns:

                df_verificar = df_verificar.sort_values(
                    by="created_at",
                    ascending=False
                )

            # =================================
            # PAGINATION
            # =================================

            POSTITS_POR_PAGINA = 5

            total_verificar = len(df_verificar)

            total_paginas_verificar = max(
                1,
                (
                    total_verificar
                    + POSTITS_POR_PAGINA
                    - 1
                )
                // POSTITS_POR_PAGINA
            )

            if "pagina_verificar" not in st.session_state:
                st.session_state.pagina_verificar = 1

            pagina_actual_verificar = (
                st.session_state.pagina_verificar
            )

            inicio_verificar = (
                (pagina_actual_verificar - 1)
                * POSTITS_POR_PAGINA
            )

            fin_verificar = (
                inicio_verificar
                + POSTITS_POR_PAGINA
            )

            df_verificar_pagina = (
                df_verificar.iloc[
                    inicio_verificar:fin_verificar
                ]
            )

            # =================================
            # POSTITS
            # =================================

            if df_verificar_pagina.empty:

                st.info(
                    "No hay comprobaciones pendientes por verificar."
                )

            else:

                cols = st.columns(5)

                for i, (_, row) in enumerate(
                    df_verificar_pagina.iterrows()
                ):

                    col = cols[i % 5]

                    with col:

                        folio = str(
                            row.get(
                                "folio_solicitud",
                                ""
                            )
                        )

                        empleado = str(
                            row.get(
                                "nombre_empleado_solicita",
                                ""
                            )
                        )

                        fecha = str(
                            row.get(
                                "created_at",
                                ""
                            )
                        )[:10]

                        total = row.get(
                            "total_comprobado",
                            0
                        )

                        try:
                            total = float(total)
                        except:
                            total = 0

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

                                <div style="
                                    font-weight:900;
                                    font-size:1rem;
                                ">
                                    {folio}
                                </div>

                                <div style="
                                    font-size:0.8rem;
                                    margin-top:4px;
                                ">
                                    {empleado}
                                </div>

                                <hr style="margin:8px 0">

                                <div style="
                                    font-size:0.8rem;
                                ">
                                    <b>Fecha:</b> {fecha}
                                </div>

                                <div style="
                                    font-size:0.9rem;
                                    margin-top:10px;
                                    font-weight:700;
                                    color:#151F6D;
                                ">
                                    ${total:,.2f}
                                </div>

                            </div>
                        </div>
                        """

                        components.html(
                            html,
                            height=230
                        )

                        if st.button(
                            "👁 Ver",
                            key=f"verificar_ver_{i}",
                            use_container_width=True
                        ):
                            #right here
                            folio_actual = row.get(
                                "folio_solicitud",
                                ""
                            )

                            solicitud_match = df_solicitudes[
                                df_solicitudes["folio_solicitud"]
                                .astype(str)
                                ==
                                str(folio_actual)
                            ]

                            if not solicitud_match.empty:

                                solicitud_row = (
                                    solicitud_match
                                    .iloc[0]
                                    .to_dict()
                                )

                            else:

                                solicitud_row = {}

                            comprobacion_row = row.to_dict()

                            # =================================
                            # MODAL
                            # =================================
                            @st.dialog("Detalle de Comprobación")
                            def modal_verificacion():

                                # =================================
                                # INFO GENERAL
                                # =================================

                                st.markdown(
                                    "<h2 style='color:#151F6D;'>📋 Información General</h2>",
                                    unsafe_allow_html=True
                                )

                                col1, col2 = st.columns(2)

                                with col1:

                                    st.markdown(
                                        f"<span style='color:black;'><b>Folio Solicitud:</b> {solicitud_row.get('folio_solicitud', '')}</span>",
                                        unsafe_allow_html=True
                                    )

                                    st.markdown(
                                        f"<span style='color:black;'><b>Folio Comprobación:</b> {comprobacion_row.get('folio_comprobacion', '')}</span>",
                                        unsafe_allow_html=True
                                    )

                                    st.markdown(
                                        f"<span style='color:black;'><b>Estatus:</b> {comprobacion_row.get('estatus', '')}</span>",
                                        unsafe_allow_html=True
                                    )

                                    st.markdown(
                                        f"<span style='color:black;'><b>Empleado Solicita:</b> {solicitud_row.get('nombre_empleado_solicita', '')}</span>",
                                        unsafe_allow_html=True
                                    )

                                    st.markdown(
                                        f"<span style='color:black;'><b>Fecha Solicitud:</b> {solicitud_row.get('fecha_solicitud', '')}</span>",
                                        unsafe_allow_html=True
                                    )

                                    st.markdown(
                                        f"<span style='color:black;'><b>Fecha Comprobación:</b> {comprobacion_row.get('created_at', '')}</span>",
                                        unsafe_allow_html=True
                                    )

                                    st.markdown(
                                        f"<span style='color:black;'><b>Fecha Inicio:</b> {solicitud_row.get('fecha_inicio', '')}</span>",
                                        unsafe_allow_html=True
                                    )

                                    st.markdown(
                                        f"<span style='color:black;'><b>Fecha Fin:</b> {solicitud_row.get('fecha_fin', '')}</span>",
                                        unsafe_allow_html=True
                                    )

                                with col2:

                                    st.markdown(
                                        f"<span style='color:black;'><b>Empresa Brinda Servicio:</b> {solicitud_row.get('empresa_brinda_servicio', '')}</span>",
                                        unsafe_allow_html=True
                                    )

                                    st.markdown(
                                        f"<span style='color:black;'><b>Empresa Cargo Gastos:</b> {solicitud_row.get('empresa_cargo_gastos', '')}</span>",
                                        unsafe_allow_html=True
                                    )

                                    st.markdown(
                                        f"<span style='color:black;'><b>Unidad Negocio:</b> {solicitud_row.get('unidad_negocio', '')}</span>",
                                        unsafe_allow_html=True
                                    )

                                    st.markdown(
                                        f"<span style='color:black;'><b>Sucursal:</b> {solicitud_row.get('sucursal', '')}</span>",
                                        unsafe_allow_html=True
                                    )

                                    st.markdown(
                                        f"<span style='color:black;'><b>Sucursal Especificar:</b> {solicitud_row.get('sucursal_especificar', '')}</span>",
                                        unsafe_allow_html=True
                                    )

                                    label_cliente = (
                                        "Motivo del Viaje"
                                        if str(
                                            solicitud_row.get(
                                                "motivo_viaje",
                                                ""
                                            )
                                        ).strip().upper() == "OTROS"
                                        else "Nombre del Cliente"
                                    )

                                    st.markdown(
                                        f"<span style='color:black;'><b>{label_cliente}:</b> {solicitud_row.get('nombre_cliente', '')}</span>",
                                        unsafe_allow_html=True
                                    )

                                    st.markdown(
                                        f"<span style='color:black;'><b>Registro SAC Ventas?:</b> {solicitud_row.get('folio_sac', '')}</span>",
                                        unsafe_allow_html=True
                                    )

                                # =================================
                                # MOTIVO
                                # =================================

                                st.markdown("---")

                                st.markdown(
                                    "<h2 style='color:#151F6D;'>✈️ Motivo del Viaje</h2>",
                                    unsafe_allow_html=True
                                )

                                st.markdown(
                                    f"""
                                    <div style='
                                        background-color:#F3F4F6;
                                        padding:16px;
                                        border-radius:12px;
                                        border:1px solid rgba(191,167,95,0.25);
                                        margin-bottom:20px;
                                        white-space:pre-wrap;
                                        color:white;
                                    '>
                                        {solicitud_row.get('motivo_viaje', '')}
                                    </div>
                                    """,
                                    unsafe_allow_html=True
                                )

                                # =================================
                                # OBSERVACIONES
                                # =================================

                                st.markdown(
                                    "<h2 style='color:#151F6D;'>📝 Observaciones Solicitud</h2>",
                                    unsafe_allow_html=True
                                )

                                st.markdown(
                                    f"""
                                    <div style='
                                        background-color:#F3F4F6;
                                        padding:16px;
                                        border-radius:12px;
                                        border:1px solid rgba(191,167,95,0.25);
                                        margin-bottom:20px;
                                        white-space:pre-wrap;
                                        color:white;
                                    '>
                                        {solicitud_row.get('observaciones', '')}
                                    </div>
                                    """,
                                    unsafe_allow_html=True
                                )

                                st.markdown(
                                    "<h2 style='color:#151F6D;'>👤 Empleado que metió comprobación</h2>",
                                    unsafe_allow_html=True
                                )

                                st.markdown(
                                    f"""
                                    <div style='
                                        background-color:#F3F4F6;
                                        padding:16px;
                                        border-radius:12px;
                                        border:1px solid rgba(191,167,95,0.25);
                                        margin-bottom:20px;
                                        white-space:pre-wrap;
                                        font-size:18px;
                                        font-weight:600;
                                        color:white;
                                    '>
                                        {comprobacion_row.get('nombre_empleado_solicita', '')}
                                    </div>
                                    """,
                                    unsafe_allow_html=True
                                )

                                st.markdown(
                                    "<h2 style='color:#151F6D;'>📝 Observaciones Comprobación</h2>",
                                    unsafe_allow_html=True
                                )

                                st.markdown(
                                    f"""
                                    <div style='
                                        background-color:#F3F4F6;
                                        padding:16px;
                                        border-radius:12px;
                                        border:1px solid rgba(191,167,95,0.25);
                                        margin-bottom:20px;
                                        white-space:pre-wrap;
                                        color:white;
                                    '>
                                        {comprobacion_row.get('observaciones', '')}
                                    </div>
                                    """,
                                    unsafe_allow_html=True
                                )

                                # =================================
                                # CONCEPTOS COMPROBACION
                                # =================================

                                st.markdown("---")

                                st.markdown(
                                    "## 🧾 Conceptos Comprobación"
                                )

                                conceptos_comprobacion = (
                                    comprobacion_row.get(
                                        "conceptos",
                                        []
                                    )
                                )

                                total_comprobado = (
                                    comprobacion_row.get(
                                        "total_comprobado",
                                        0
                                    )
                                )

                                try:
                                    total_comprobado = float(
                                        total_comprobado
                                    )
                                except:
                                    total_comprobado = 0

                                st.markdown(
                                    f"""
                                    <div style='
                                        font-size:22px;
                                        font-weight:700;
                                        color:#38BDF8;
                                        margin-bottom:15px;
                                    '>
                                        Comprobación:
                                        ${total_comprobado:,.2f}
                                    </div>
                                    """,
                                    unsafe_allow_html=True
                                )

                                if conceptos_comprobacion:

                                    df_comp = pd.DataFrame(
                                        conceptos_comprobacion
                                    )

                                    if "Eliminar" in df_comp.columns:

                                        df_comp = df_comp.drop(
                                            columns=["Eliminar"]
                                        )

                                    columnas_comprobacion = [

                                        "Tipo",
                                        "Descripcion",
                                        "Fecha Factura",
                                        "Folio",
                                        "Proveedor",
                                        "Moneda",
                                        "Monto",
                                        "Comprobante",
                                        "Aplica IVA",
                                        "IVA %",
                                        "Aplica Retencion",
                                        "Impuesto Acreditable",
                                        "Total Comprobado"
                                    ]

                                    for col_name in columnas_comprobacion:

                                        if col_name not in df_comp.columns:

                                            df_comp[col_name] = ""

                                    df_comp = df_comp[
                                        columnas_comprobacion
                                    ]

                                    currency_columns = [
                                        "Monto",
                                        "Impuesto Acreditable",
                                        "Total Comprobado"
                                    ]

                                    for col_name in currency_columns:

                                        if col_name in df_comp.columns:

                                            df_comp[col_name] = (
                                                pd.to_numeric(
                                                    df_comp[col_name],
                                                    errors="coerce"
                                                )
                                                .fillna(0)
                                                .apply(
                                                    lambda x: f"${x:,.2f}"
                                                )
                                            )

                                    st.data_editor(
                                        df_comp,
                                        use_container_width=True,
                                        hide_index=True,
                                        disabled=True,
                                        height=350
                                    )

                                else:

                                    st.info(
                                        "No hay conceptos comprobados."
                                    )

                                # =================================
                                # TOTALES COMPROBACION
                                # =================================

                                st.markdown("---")

                                total_comp = comprobacion_row.get(
                                    "total_comprobado",
                                    0
                                )

                                anticipo = comprobacion_row.get(
                                    "anticipo_viaje",
                                    0
                                )

                                diferencia = comprobacion_row.get(
                                    "diferencia_cargo_favor",
                                    0
                                )

                                try:
                                    total_comp = float(total_comp)
                                except:
                                    total_comp = 0

                                try:
                                    anticipo = float(anticipo)
                                except:
                                    anticipo = 0

                                try:
                                    diferencia = float(diferencia)
                                except:
                                    diferencia = 0

                                col_tot1, col_tot2, col_tot3 = st.columns(3)

                                with col_tot1:

                                    st.markdown(
                                        f"""
                                        ### Total Comprobado

                                        ## ${total_comp:,.2f}
                                        """
                                    )

                                with col_tot2:

                                    st.markdown(
                                        f"""
                                        ### Anticipo Viaje

                                        ## ${anticipo:,.2f}
                                        """
                                    )

                                with col_tot3:

                                    st.markdown(
                                        f"""
                                        ### Diferencia Cargo/Favor

                                        ## ${diferencia:,.2f}
                                        """
                                    )

                                st.markdown("---")

                                btn1, btn2 = st.columns(2)

                                with btn1:

                                    if st.button(
                                        "✅ Aprobar Solicitud",
                                        use_container_width=True
                                    ):

                                        supabase.table(
                                            "solicitud_viaje"
                                        ).update(
                                            {
                                                "estatus": "Concluido",
                                            }
                                        ).eq(
                                            "folio_solicitud",
                                            folio_actual
                                        ).execute()

                                        supabase.table(
                                            "comprobacion_viaje"
                                        ).update(
                                            {
                                                "estatus": "Concluido",
                                            }
                                        ).eq(
                                            "folio_solicitud",
                                            folio_actual
                                        ).execute()

                                        # =================================
                                        # GET CREATOR EMAIL
                                        # =================================

                                        correo_creador = (
                                            obtener_email_usuario(
                                                solicitud_row.get(
                                                    "nombre_empleado_solicita",
                                                    ""
                                                )
                                            )
                                        )

                                        destinatarios = construir_destinatarios(

                                            empresa=row.get(
                                                "empresa_brinda_servicio",
                                                ""
                                            ),

                                            email_usuario_actual=email_usuario,

                                            correo_creador=correo_creador
                                        )

                                        # =================================
                                        # SEND EMAIL
                                        # =================================

                                        try:

                                            enviar_correo_estatus_solicitud(

                                                destinatarios=destinatarios,

                                                folio=solicitud_row.get(
                                                    "folio_solicitud",
                                                    ""
                                                ),

                                                estatus="Concluido",

                                                fecha_inicio=solicitud_row.get(
                                                    "fecha_inicio",
                                                    ""
                                                ),

                                                fecha_fin=solicitud_row.get(
                                                    "fecha_fin",
                                                    ""
                                                ),

                                                motivo_viaje=solicitud_row.get(
                                                    "motivo_viaje",
                                                    ""
                                                ),

                                                observaciones=row.get(
                                                    "observaciones",
                                                    ""
                                                ),

                                                conceptos=solicitud_row.get(
                                                    "conceptos",
                                                    []
                                                )
                                            )

                                        except Exception as e:

                                            st.warning(
                                                f"No se pudo enviar correo: {e}"
                                            )

                                        st.success(
                                            "Solicitud concluida"
                                        )

                                        st.cache_data.clear()
                                        st.rerun()

                                with btn2:

                                    if st.button(
                                        "❌ Rechazar Solicitud",
                                        use_container_width=True
                                    ):

                                        supabase.table(
                                            "solicitud_viaje"
                                        ).update(
                                            {
                                                "estatus": "Rechazado",
                                            }
                                        ).eq(
                                            "folio_solicitud",
                                            folio_actual
                                        ).execute()

                                        supabase.table(
                                            "comprobacion_viaje"
                                        ).update(
                                            {
                                                "estatus": "Rechazado",
                                            }
                                        ).eq(
                                            "folio_solicitud",
                                            folio_actual
                                        ).execute()

                                        # =================================
                                        # GET CREATOR EMAIL
                                        # =================================

                                        correo_creador = (
                                            obtener_email_usuario(
                                                solicitud_row.get(
                                                    "nombre_empleado_solicita",
                                                    ""
                                                )
                                            )
                                        )

                                        destinatarios = construir_destinatarios(

                                            empresa=row.get(
                                                "empresa_brinda_servicio",
                                                ""
                                            ),

                                            email_usuario_actual=email_usuario,

                                            correo_creador=correo_creador
                                        )

                                        # =================================
                                        # SEND EMAIL
                                        # =================================

                                        try:

                                            enviar_correo_estatus_solicitud(

                                                destinatarios=destinatarios,

                                                folio=solicitud_row.get(
                                                    "folio_solicitud",
                                                    ""
                                                ),

                                                estatus="Rechazado",

                                                fecha_inicio=solicitud_row.get(
                                                    "fecha_inicio",
                                                    ""
                                                ),

                                                fecha_fin=solicitud_row.get(
                                                    "fecha_fin",
                                                    ""
                                                ),

                                                motivo_viaje=solicitud_row.get(
                                                    "motivo_viaje",
                                                    ""
                                                ),

                                                observaciones=row.get(
                                                    "observaciones",
                                                    ""
                                                ),

                                                conceptos=solicitud_row.get(
                                                    "conceptos",
                                                    []
                                                )
                                            )

                                        except Exception as e:

                                            st.warning(
                                                f"No se pudo enviar correo: {e}"
                                            )

                                        st.error(
                                            "Solicitud rechazada"
                                        )

                                        st.cache_data.clear()
                                        st.rerun()    


                            modal_verificacion()

            # =================================
            # PAGINATION CONTROLS
            # =================================

            st.divider()

            p1, p2, p3 = st.columns([1,2,1])

            with p1:

                if st.button(
                    "⬅ Anterior",
                    disabled=(
                        st.session_state.pagina_verificar <= 1
                    ),
                    use_container_width=True,
                    key="prev_verificar"
                ):

                    st.session_state.pagina_verificar -= 1
                    st.rerun()

            with p2:

                st.markdown(
                    f"""
                    <div style="
                        text-align:center;
                        padding-top:8px;
                        font-weight:700;
                        color:#151F6D;
                    ">
                        Página {st.session_state.pagina_verificar} de {total_paginas_verificar}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            with p3:

                if st.button(
                    "Siguiente ➡",
                    disabled=(
                        st.session_state.pagina_verificar
                        >= total_paginas_verificar
                    ),
                    use_container_width=True,
                    key="next_verificar"
                ):

                    st.session_state.pagina_verificar += 1
                    st.rerun()

            # =================================
            # SOLICITUDES FINALIZADAS
            # =================================

            st.header("🏁 Solicitudes Finalizadas")

            # =================================
            # BASE DATA
            # =================================

            df_comp_final = (
                df_comprobaciones
                .sort_values(
                    by="created_at",
                    ascending=False
                )
                .drop_duplicates(
                    subset=["folio_solicitud"]
                )
            )

            df_finalizadas = pd.merge(

                df_solicitudes[
                    df_solicitudes["estatus"].isin(
                        [
                            "Concluido",
                            "Rechazado"
                        ]
                    )
                ],

                df_comp_final[
                    [
                        "folio_solicitud",
                        "folio_comprobacion",
                        "conceptos",
                        "total_comprobado",
                        "anticipo_viaje",
                        "diferencia_cargo_favor",
                        "observaciones",
                        "created_at"
                    ]
                ],

                on="folio_solicitud",

                how="left",

                suffixes=(
                    "_solicitud",
                    ""
                )
            )

            # =================================
            # FILTERS
            # =================================

            f1, f2, f3 = st.columns(3)

            with f1:

                folios_finalizados = ["Todos"]

                if not df_finalizadas.empty:

                    folios_finalizados += sorted(
                        df_finalizadas["folio_solicitud"]
                        .dropna()
                        .astype(str)
                        .unique()
                        .tolist()
                    )

                filtro_folio_finalizado = st.selectbox(
                    "Filtrar por Folio",
                    folios_finalizados,
                    key="filtro_folio_finalizado"
                )

            with f2:

                estatus_finalizados = ["Todos"]

                if not df_finalizadas.empty:

                    estatus_finalizados += sorted(
                        df_finalizadas["estatus"]
                        .dropna()
                        .astype(str)
                        .unique()
                        .tolist()
                    )

                filtro_estatus_finalizado = st.selectbox(
                    "Filtrar por Estatus",
                    estatus_finalizados,
                    key="filtro_estatus_finalizado"
                )

            with f3:

                empleados_finalizados = ["Todos"]

                if not df_finalizadas.empty:

                    empleados_finalizados += sorted(
                        df_finalizadas["nombre_empleado_solicita"]
                        .dropna()
                        .astype(str)
                        .unique()
                        .tolist()
                    )

                filtro_empleado_finalizado = st.selectbox(
                    "Filtrar por Empleado",
                    empleados_finalizados,
                    key="filtro_empleado_finalizado"
                )

            # =================================
            # APPLY FILTERS
            # =================================

            if filtro_folio_finalizado != "Todos":

                df_finalizadas = df_finalizadas[
                    df_finalizadas["folio_solicitud"]
                    .astype(str)
                    ==
                    str(filtro_folio_finalizado)
                ]

            if filtro_estatus_finalizado != "Todos":

                df_finalizadas = df_finalizadas[
                    df_finalizadas["estatus"]
                    .astype(str)
                    ==
                    str(filtro_estatus_finalizado)
                ]

            if filtro_empleado_finalizado != "Todos":

                df_finalizadas = df_finalizadas[
                    df_finalizadas["nombre_empleado_solicita"]
                    .astype(str)
                    ==
                    str(filtro_empleado_finalizado)
                ]

            # =================================
            # SORT
            # =================================

            if "created_at" in df_finalizadas.columns:

                df_finalizadas = df_finalizadas.sort_values(
                    by="created_at",
                    ascending=False
                )

            # =================================
            # DESCARGAR REPORTE
            # =================================

            reporte_rows = []

            for _, row in df_finalizadas.iterrows():

                solicitud_match = df_solicitudes[
                    df_solicitudes["folio_solicitud"]
                    .astype(str)
                    ==
                    str(row.get("folio_solicitud", ""))
                ]

                if not solicitud_match.empty:

                    solicitud_row = (
                        solicitud_match
                        .iloc[0]
                        .to_dict()
                    )

                else:

                    solicitud_row = {}

                # =================================
                # CONCEPTOS SOLICITUD
                # =================================

                conceptos_solicitud = solicitud_row.get("conceptos")

                if not isinstance(conceptos_solicitud, list):
                    conceptos_solicitud = []

                if len(conceptos_solicitud) == 0:
                    conceptos_solicitud = [{}]

                # =================================
                # CONCEPTOS COMPROBACION
                # =================================

                conceptos_comprobacion = row.get("conceptos")

                if not isinstance(conceptos_comprobacion, list):
                    conceptos_comprobacion = []

                if len(conceptos_comprobacion) == 0:
                    conceptos_comprobacion = [{}]

                max_len = max(
                    len(conceptos_solicitud),
                    len(conceptos_comprobacion)
                )

                for i in range(max_len):

                    concepto_sol = (
                        conceptos_solicitud[i]
                        if i < len(conceptos_solicitud)
                        else {}
                    )

                    concepto_comp = (
                        conceptos_comprobacion[i]
                        if i < len(conceptos_comprobacion)
                        else {}
                    )

                    reporte_rows.append({

                        # =================================
                        # GENERAL
                        # =================================

                        "Folio Solicitud":
                            solicitud_row.get(
                                "folio_solicitud",
                                ""
                            ),

                        "Folio Comprobacion":
                            row.get(
                                "folio_comprobacion",
                                ""
                            ),

                        "Estatus":
                            row.get(
                                "estatus",
                                ""
                            ),

                        "Empleado Solicita":
                            solicitud_row.get(
                                "nombre_empleado_solicita",
                                ""
                            ),

                        "Fecha Solicitud":
                            solicitud_row.get(
                                "fecha_solicitud",
                                ""
                            ),

                        "Fecha Comprobacion":
                            row.get(
                                "created_at",
                                ""
                            ),

                        "Fecha Inicio":
                            solicitud_row.get(
                                "fecha_inicio",
                                ""
                            ),

                        "Fecha Fin":
                            solicitud_row.get(
                                "fecha_fin",
                                ""
                            ),

                        "Empresa Brinda Servicio":
                            solicitud_row.get(
                                "empresa_brinda_servicio",
                                ""
                            ),

                        "Empresa Cargo Gastos":
                            solicitud_row.get(
                                "empresa_cargo_gastos",
                                ""
                            ),

                        "Unidad Negocio":
                            solicitud_row.get(
                                "unidad_negocio",
                                ""
                            ),

                        "Sucursal":
                            solicitud_row.get(
                                "sucursal",
                                ""
                            ),

                        "Sucursal Especificar":
                            solicitud_row.get(
                                "sucursal_especificar",
                                ""
                            ),

                        "Nombre Cliente":
                            solicitud_row.get(
                                "nombre_cliente",
                                ""
                            ),

                        "Registro SAC Ventas":
                            solicitud_row.get(
                                "folio_sac",
                                ""
                            ),

                        "Motivo Viaje":
                            solicitud_row.get(
                                "motivo_viaje",
                                ""
                            ),

                        "Observaciones Solicitud":
                            solicitud_row.get(
                                "observaciones",
                                ""
                            ),

                        "Observaciones Comprobacion":
                            row.get(
                                "observaciones",
                                ""
                            ),

                        # =================================
                        # TOTALES
                        # =================================

                        "Monto Solicitado":
                            solicitud_row.get(
                                "total_estimado",
                                0
                            ),

                        "Total Comprobado":
                            row.get(
                                "total_comprobado",
                                0
                            ),

                        "Anticipo Viaje":
                            row.get(
                                "anticipo_viaje",
                                0
                            ),

                        "Diferencia Cargo Favor":
                            row.get(
                                "diferencia_cargo_favor",
                                0
                            ),

                        # =================================
                        # CONCEPTOS SOLICITUD
                        # =================================

                        "Solicitud Tipo":
                            concepto_sol.get(
                                "Tipo",
                                ""
                            ),

                        "Solicitud Descripcion":
                            concepto_sol.get(
                                "Descripcion",
                                ""
                            ),

                        "Solicitud Monto":
                            concepto_sol.get(
                                "Monto",
                                ""
                            ),

                        "Solicitud Tipo Cambio":
                            concepto_sol.get(
                                "Tipo Cambio",
                                ""
                            ),

                        "Solicitud Aprobado":
                            concepto_sol.get(
                                "Aprobado",
                                ""
                            ),

                        "Solicitud Razon":
                            concepto_sol.get(
                                "Razon",
                                ""
                            ),

                        # =================================
                        # CONCEPTOS COMPROBACION
                        # =================================

                        "Comprobacion Tipo":
                            concepto_comp.get(
                                "Tipo",
                                ""
                            ),

                        "Comprobacion Descripcion":
                            concepto_comp.get(
                                "Descripcion",
                                ""
                            ),

                        "Comprobacion Fecha Factura":
                            concepto_comp.get(
                                "Fecha Factura",
                                ""
                            ),

                        "Comprobacion Folio":
                            concepto_comp.get(
                                "Folio",
                                ""
                            ),

                        "Comprobacion Proveedor":
                            concepto_comp.get(
                                "Proveedor",
                                ""
                            ),

                        "Comprobacion Moneda":
                            concepto_comp.get(
                                "Moneda",
                                ""
                            ),

                        "Comprobacion Monto":
                            concepto_comp.get(
                                "Monto",
                                ""
                            ),

                        "Comprobacion Comprobante":
                            concepto_comp.get(
                                "Comprobante",
                                ""
                            ),

                        "Comprobacion Aplica IVA":
                            concepto_comp.get(
                                "Aplica IVA",
                                ""
                            ),

                        "Comprobacion IVA %":
                            concepto_comp.get(
                                "IVA %",
                                ""
                            ),

                        "Comprobacion Aplica Retencion":
                            concepto_comp.get(
                                "Aplica Retencion",
                                ""
                            ),

                        "Comprobacion Impuesto Acreditable":
                            concepto_comp.get(
                                "Impuesto Acreditable",
                                ""
                            ),

                        "Comprobacion Total Comprobado":
                            concepto_comp.get(
                                "Total Comprobado",
                                ""
                            )
                    })

            df_reporte = pd.DataFrame(
                reporte_rows
            )

            output = BytesIO()

            with pd.ExcelWriter(
                output,
                engine="openpyxl"
            ) as writer:

                df_reporte.to_excel(
                    writer,
                    index=False,
                    sheet_name="Solicitudes"
                )

            output.seek(0)

            st.download_button(
                label="📥 Descargar reporte de Solicitudes",
                data=output.getvalue(),
                file_name="Reporte_Solicitudes_Finalizadas.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=False,
                key="descargar_reporte_final"
            )

            # =================================
            # PAGINATION
            # =================================

            FINALIZADAS_POR_PAGINA = 5

            total_finalizadas = len(df_finalizadas)

            total_paginas_finalizadas = max(
                1,
                (
                    total_finalizadas
                    + FINALIZADAS_POR_PAGINA
                    - 1
                )
                // FINALIZADAS_POR_PAGINA
            )

            if "pagina_finalizadas" not in st.session_state:

                st.session_state.pagina_finalizadas = 1

            pagina_actual_finalizadas = (
                st.session_state.pagina_finalizadas
            )

            inicio_finalizadas = (
                (pagina_actual_finalizadas - 1)
                * FINALIZADAS_POR_PAGINA
            )

            fin_finalizadas = (
                inicio_finalizadas
                + FINALIZADAS_POR_PAGINA
            )

            df_finalizadas_pagina = (
                df_finalizadas.iloc[
                    inicio_finalizadas:fin_finalizadas
                ]
            )

            # =================================
            # POSTITS
            # =================================

            if df_finalizadas_pagina.empty:

                st.info(
                    "No hay solicitudes finalizadas."
                )

            else:

                cols = st.columns(5)

                for i, (_, row) in enumerate(
                    df_finalizadas_pagina.iterrows()
                ):

                    col = cols[i % 5]

                    with col:

                        folio = str(
                            row.get(
                                "folio_solicitud",
                                ""
                            )
                        )

                        empleado = str(
                            row.get(
                                "nombre_empleado_solicita",
                                ""
                            )
                        )

                        fecha = str(
                            row.get(
                                "created_at",
                                ""
                            )
                        )[:10]

                        total = row.get(
                            "total_comprobado",
                            0
                        )

                        try:
                            total = float(total)
                        except:
                            total = 0

                        estatus = str(
                            row.get(
                                "estatus",
                                ""
                            )
                        )

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

                                <div style="
                                    font-weight:900;
                                    font-size:1rem;
                                ">
                                    {folio}
                                </div>

                                <div style="
                                    font-size:0.8rem;
                                    margin-top:4px;
                                ">
                                    {empleado}
                                </div>

                                <hr style="margin:8px 0">

                                <div style="
                                    font-size:0.8rem;
                                ">
                                    <b>Fecha:</b> {fecha}
                                </div>

                                <div style="
                                    font-size:0.8rem;
                                    margin-top:6px;
                                ">
                                    <b>Estatus:</b> {estatus}
                                </div>

                                <div style="
                                    font-size:0.9rem;
                                    margin-top:10px;
                                    font-weight:700;
                                    color:#151F6D;
                                ">
                                    ${total:,.2f}
                                </div>

                            </div>
                        </div>
                        """

                        components.html(
                            html,
                            height=230
                        )

                        if st.button(
                            "👁 Ver",
                            key=f"finalizada_ver_{i}",
                            use_container_width=True
                        ):

                            folio_actual = row.get(
                                "folio_solicitud",
                                ""
                            )

                            solicitud_match = df_solicitudes[
                                df_solicitudes["folio_solicitud"]
                                .astype(str)
                                ==
                                str(folio_actual)
                            ]

                            if not solicitud_match.empty:

                                solicitud_row = (
                                    solicitud_match
                                    .iloc[0]
                                    .to_dict()
                                )

                            else:

                                solicitud_row = {}

                            # =================================
                            # MODAL
                            # =================================
                            @st.dialog("Detalle de Comprobación")
                            def modal_verificacion_finalizada():

                                # =================================
                                # INFO GENERAL
                                # =================================

                                st.markdown(
                                    "<h2 style='color:#151F6D;'>📋 Información General</h2>",
                                    unsafe_allow_html=True
                                )

                                col1, col2 = st.columns(2)

                                with col1:

                                    st.markdown(
                                        f"<span style='color:black;'><b>Folio Solicitud:</b> {solicitud_row.get('folio_solicitud', '')}</span>",
                                        unsafe_allow_html=True
                                    )

                                    st.markdown(
                                        f"<span style='color:black;'><b>Folio Comprobación:</b> {row.get('folio_comprobacion', '')}</span>",
                                        unsafe_allow_html=True
                                    )

                                    st.markdown(
                                        f"<span style='color:black;'><b>Estatus:</b> {row.get('estatus', '')}</span>",
                                        unsafe_allow_html=True
                                    )

                                    st.markdown(
                                        f"<span style='color:black;'><b>Empleado Solicita:</b> {solicitud_row.get('nombre_empleado_solicita', '')}</span>",
                                        unsafe_allow_html=True
                                    )

                                    st.markdown(
                                        f"<span style='color:black;'><b>Fecha Solicitud:</b> {solicitud_row.get('fecha_solicitud', '')}</span>",
                                        unsafe_allow_html=True
                                    )

                                    st.markdown(
                                        f"<span style='color:black;'><b>Fecha Comprobación:</b> {row.get('created_at', '')}</span>",
                                        unsafe_allow_html=True
                                    )

                                    st.markdown(
                                        f"<span style='color:black;'><b>Fecha Inicio:</b> {solicitud_row.get('fecha_inicio', '')}</span>",
                                        unsafe_allow_html=True
                                    )

                                    st.markdown(
                                        f"<span style='color:black;'><b>Fecha Fin:</b> {solicitud_row.get('fecha_fin', '')}</span>",
                                        unsafe_allow_html=True
                                    )

                                with col2:

                                    st.markdown(
                                        f"<span style='color:black;'><b>Empresa Brinda Servicio:</b> {solicitud_row.get('empresa_brinda_servicio', '')}</span>",
                                        unsafe_allow_html=True
                                    )

                                    st.markdown(
                                        f"<span style='color:black;'><b>Empresa Cargo Gastos:</b> {solicitud_row.get('empresa_cargo_gastos', '')}</span>",
                                        unsafe_allow_html=True
                                    )

                                    st.markdown(
                                        f"<span style='color:black;'><b>Unidad Negocio:</b> {solicitud_row.get('unidad_negocio', '')}</span>",
                                        unsafe_allow_html=True
                                    )

                                    st.markdown(
                                        f"<span style='color:black;'><b>Sucursal:</b> {solicitud_row.get('sucursal', '')}</span>",
                                        unsafe_allow_html=True
                                    )

                                    st.markdown(
                                        f"<span style='color:black;'><b>Sucursal Especificar:</b> {solicitud_row.get('sucursal_especificar', '')}</span>",
                                        unsafe_allow_html=True
                                    )

                                    label_cliente = (
                                        "Motivo del Viaje"
                                        if str(
                                            solicitud_row.get(
                                                "motivo_viaje",
                                                ""
                                            )
                                        ).strip().upper() == "OTROS"
                                        else "Nombre del Cliente"
                                    )

                                    st.markdown(
                                        f"<span style='color:black;'><b>{label_cliente}:</b> {solicitud_row.get('nombre_cliente', '')}</span>",
                                        unsafe_allow_html=True
                                    )

                                    st.markdown(
                                        f"<span style='color:black;'><b>Registro SAC Ventas?:</b> {solicitud_row.get('folio_sac', '')}</span>",
                                        unsafe_allow_html=True
                                    )

                                # =================================
                                # MOTIVO
                                # =================================

                                st.markdown("---")

                                st.markdown(
                                    "## ✈️ Motivo del Viaje"
                                )

                                st.markdown(
                                    f"""
                                    <div style='
                                        background-color:#F3F4F6;
                                        padding:16px;
                                        border-radius:12px;
                                        border:1px solid rgba(191,167,95,0.25);
                                        margin-bottom:20px;
                                        white-space:pre-wrap;
                                    '>
                                        {solicitud_row.get('motivo_viaje', '')}
                                    </div>
                                    """,
                                    unsafe_allow_html=True
                                )

                                # =================================
                                # OBSERVACIONES
                                # =================================

                                st.markdown(
                                    "## 📝 Observaciones Solicitud"
                                )

                                st.markdown(
                                    f"""
                                    <div style='
                                        background-color:#F3F4F6;
                                        padding:16px;
                                        border-radius:12px;
                                        border:1px solid rgba(191,167,95,0.25);
                                        margin-bottom:20px;
                                        white-space:pre-wrap;
                                    '>
                                        {solicitud_row.get('observaciones', '')}
                                    </div>
                                    """,
                                    unsafe_allow_html=True
                                )

                                st.markdown(
                                    "## 👤 Empleado que metió comprobación"
                                )

                                st.markdown(
                                    f"""
                                    <div style='
                                        background-color:#F3F4F6;
                                        padding:16px;
                                        border-radius:12px;
                                        border:1px solid rgba(191,167,95,0.25);
                                        margin-bottom:20px;
                                        white-space:pre-wrap;
                                        font-size:18px;
                                        font-weight:600;
                                    '>
                                        {row.get('nombre_empleado_solicita', '')}
                                    </div>
                                    """,
                                    unsafe_allow_html=True
                                )

                                st.markdown(
                                    "## 📝 Observaciones Comprobación"
                                )

                                st.markdown(
                                    f"""
                                    <div style='
                                        background-color:#F3F4F6;
                                        padding:16px;
                                        border-radius:12px;
                                        border:1px solid rgba(191,167,95,0.25);
                                        margin-bottom:20px;
                                        white-space:pre-wrap;
                                    '>
                                        {row.get('observaciones', '')}
                                    </div>
                                    """,
                                    unsafe_allow_html=True
                                )

                                # =================================
                                # MONTO SOLICITADO
                                # =================================
                                # =================================
                                # MONTO SOLICITADO
                                # =================================

                                st.markdown("---")

                                conceptos_solicitud = (
                                    solicitud_row.get(
                                        "conceptos",
                                        []
                                    )
                                )

                                monto_solicitado = 0.0

                                for item in conceptos_solicitud:

                                    try:

                                        monto_solicitado += float(
                                            item.get(
                                                "Monto",
                                                0
                                            ) or 0
                                        )

                                    except:

                                        pass

                                st.markdown(
                                    f"""
                                    <div style='
                                        font-size:26px;
                                        font-weight:800;
                                        color:#BFA75F;
                                        margin-top:10px;
                                        margin-bottom:10px;
                                    '>
                                        Monto Solicitado:
                                        ${monto_solicitado:,.2f}
                                    </div>
                                    """,
                                    unsafe_allow_html=True
                                )

                                st.markdown(
                                    "<h3 style='color:black;'>👁 Ver Detalles Solicitud</h3>",
                                    unsafe_allow_html=True
                                )

                                with st.expander(
                                    "",
                                    expanded=False
                                ):

                                    if conceptos_solicitud:

                                        df_sol = pd.DataFrame(
                                            conceptos_solicitud
                                        )

                                        columnas_solicitud = [
                                            "Tipo",
                                            "Descripcion",
                                            "Monto",
                                            "Tipo Cambio",
                                            "Aprobado",
                                            "Razon"
                                        ]

                                        for col_name in columnas_solicitud:

                                            if col_name not in df_sol.columns:

                                                df_sol[col_name] = ""

                                        df_sol = df_sol[
                                            columnas_solicitud
                                        ]

                                        if "Monto" in df_sol.columns:

                                            df_sol["Monto"] = (
                                                pd.to_numeric(
                                                    df_sol["Monto"],
                                                    errors="coerce"
                                                )
                                                .fillna(0)
                                                .apply(
                                                    lambda x:
                                                    f"${x:,.2f}"
                                                )
                                            )

                                        st.data_editor(
                                            df_sol,
                                            use_container_width=True,
                                            hide_index=True,
                                            disabled=True,
                                            height=350
                                        )

                                    else:

                                        st.info(
                                            "No hay conceptos."
                                        )

                                # =================================
                                # CONCEPTOS COMPROBACION
                                # =================================

                                st.markdown("---")

                                st.markdown(
                                    "## 🧾 Conceptos Comprobación"
                                )

                                conceptos_comprobacion = (
                                    row.get(
                                        "conceptos",
                                        []
                                    )
                                )

                                total_comprobado = (
                                    row.get(
                                        "total_comprobado",
                                        0
                                    )
                                )

                                try:
                                    total_comprobado = float(
                                        total_comprobado
                                    )
                                except:
                                    total_comprobado = 0

                                st.markdown(
                                    f"""
                                    <div style='
                                        font-size:22px;
                                        font-weight:700;
                                        color:#38BDF8;
                                        margin-bottom:15px;
                                    '>
                                        Comprobación:
                                        ${total_comprobado:,.2f}
                                    </div>
                                    """,
                                    unsafe_allow_html=True
                                )

                                if conceptos_comprobacion:

                                    df_comp = pd.DataFrame(
                                        conceptos_comprobacion
                                    )

                                    if "Eliminar" in df_comp.columns:

                                        df_comp = df_comp.drop(
                                            columns=["Eliminar"]
                                        )

                                    columnas_comprobacion = [

                                        "Tipo",

                                        "Descripcion",

                                        "Fecha Factura",

                                        "Folio",

                                        "Proveedor",

                                        "Moneda",

                                        "Monto",

                                        "Comprobante",

                                        "Aplica IVA",

                                        "IVA %",

                                        "Aplica Retencion",

                                        "Impuesto Acreditable",

                                        "Total Comprobado"
                                    ]

                                    for col_name in columnas_comprobacion:

                                        if col_name not in df_comp.columns:

                                            df_comp[col_name] = ""

                                    df_comp = df_comp[
                                        columnas_comprobacion
                                    ]

                                    currency_columns = [
                                        "Monto",
                                        "Impuesto Acreditable",
                                        "Total Comprobado"
                                    ]

                                    for col_name in currency_columns:

                                        if col_name in df_comp.columns:

                                            df_comp[col_name] = (
                                                pd.to_numeric(
                                                    df_comp[col_name],
                                                    errors="coerce"
                                                )
                                                .fillna(0)
                                                .apply(
                                                    lambda x:
                                                    f"${x:,.2f}"
                                                )
                                            )

                                    st.data_editor(
                                        df_comp,
                                        use_container_width=True,
                                        hide_index=True,
                                        disabled=True,
                                        height=350
                                    )

                                else:

                                    st.info(
                                        "No hay conceptos comprobados."
                                    )
                                # =================================
                                # TOTALES COMPROBACION
                                # =================================

                                st.markdown("---")

                                total_comp = row.get(
                                    "total_comprobado",
                                    0
                                )

                                anticipo = row.get(
                                    "anticipo_viaje",
                                    0
                                )

                                diferencia = row.get(
                                    "diferencia_cargo_favor",
                                    0
                                )

                                try:
                                    total_comp = float(total_comp)
                                except:
                                    total_comp = 0

                                try:
                                    anticipo = float(anticipo)
                                except:
                                    anticipo = 0

                                try:
                                    diferencia = float(diferencia)
                                except:
                                    diferencia = 0

                                col_tot1, col_tot2, col_tot3 = st.columns(3)

                                with col_tot1:

                                    st.markdown(
                                        f"""
                                        ### Total Comprobado

                                        ## ${total_comp:,.2f}
                                        """
                                    )

                                with col_tot2:

                                    st.markdown(
                                        f"""
                                        ### Anticipo Viaje

                                        ## ${anticipo:,.2f}
                                        """
                                    )

                                with col_tot3:

                                    st.markdown(
                                        f"""
                                        ### Diferencia Cargo/Favor

                                        ## ${diferencia:,.2f}
                                        """
                                    )

                            modal_verificacion_finalizada()
                            
            # =================================
            # PAGINATION CONTROLS
            # =================================

            st.divider()

            p1, p2, p3 = st.columns([1,2,1])

            with p1:

                if st.button(
                    "⬅ Anterior",
                    disabled=(
                        st.session_state.pagina_finalizadas <= 1
                    ),
                    use_container_width=True,
                    key="prev_finalizadas"
                ):

                    st.session_state.pagina_finalizadas -= 1
                    st.rerun()

            with p2:

                st.markdown(
                    f"""
                    <div style="
                        text-align:center;
                        padding-top:8px;
                        font-weight:700;
                        color:#151F6D;
                    ">
                        Página {st.session_state.pagina_finalizadas} de {total_paginas_finalizadas}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            with p3:

                if st.button(
                    "Siguiente ➡",
                    disabled=(
                        st.session_state.pagina_finalizadas
                        >= total_paginas_finalizadas
                    ),
                    use_container_width=True,
                    key="next_finalizadas"
                ):

                    st.session_state.pagina_finalizadas += 1
                    st.rerun()