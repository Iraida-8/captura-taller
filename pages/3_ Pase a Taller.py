import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime, date, timezone
from auth import require_login, require_access

# =================================
# Page configuration
# =================================
st.set_page_config(
    page_title="Captura Pase de Taller",
    layout="wide"
)

# =================================
# Styled CSS
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

    /* Main content spacing */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    /* General text */
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

    p, label, span {
        color: #F5F5F5 !important;
    }

    /* Divider */
    hr {
        border-color: rgba(191, 167, 95, 0.25);
    }

    /* Input containers */
    div[data-baseweb="input"] > div,
    div[data-baseweb="select"] > div,
    textarea {
        background-color: #1B267A !important;
        border: 1px solid rgba(191, 167, 95, 0.25) !important;
        border-radius: 10px !important;
        color: white !important;
    }

    /* Input text */
    input, textarea {
        color: white !important;
    }

    /* Placeholder */
    input::placeholder,
    textarea::placeholder {
        color: #d0d0d0 !important;
    }

    /* Selectbox dropdown */
    div[data-baseweb="select"] * {
        color: white !important;
    }

    /* Radio buttons labels */
    div[role="radiogroup"] label {
        color: white !important;
    }

    /* Checkbox */
    .stCheckbox label {
        color: white !important;
    }

    /* Main buttons */
    div.stButton > button,
    div[data-testid="stFormSubmitButton"] > button {
        width: 100%;
        border-radius: 12px;
        padding: 0.75rem 1rem;
        font-weight: 600;
        border: none;
        transition: all 0.2s ease;
        font-size: 15px;
    }

    /* Primary action buttons */
    div.stButton > button[kind="primary"],
    button[kind="primary"] {
        background-color: #BFA75F !important;
        color: #151F6D !important;
        box-shadow: 0 4px 12px rgba(191, 167, 95, 0.25);
    }

    div.stButton > button[kind="primary"]:hover,
    button[kind="primary"]:hover {
        background-color: #d4bc73 !important;
        color: #151F6D !important;
        transform: translateY(-1px);
    }

    /* Secondary buttons */
    div.stButton > button {
        background-color: #1B267A;
        color: white;
        border: 1px solid rgba(191, 167, 95, 0.25);
    }

    div.stButton > button:hover {
        border-color: #BFA75F;
        color: #BFA75F;
        background-color: #24338C;
        transform: translateY(-1px);
    }

    /* Info / warning / success boxes */
    div[data-baseweb="notification"] {
        border-radius: 12px;
    }

    /* Back button */
    button[kind="secondary"] {
        background-color: transparent !important;
        color: #BFA75F !important;
        border: 1px solid #BFA75F !important;
        font-weight: 600;
    }

    button[kind="secondary"]:hover {
        background-color: #BFA75F !important;
        color: #151F6D !important;
    }

    </style>
    """,
    unsafe_allow_html=True
)

# =================================
# Security gates
# =================================
require_login()
require_access("pase_taller")

# =================================
# Top navigation
# =================================
if st.button("⬅ Volver al Dashboard"):
    st.switch_page("pages/dashboard.py")

st.divider()

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

# =================================
# Page title
# =================================
st.title("🛠️ Captura Pase de Taller")

# =================================
# SECCIÓN 1 — DATOS DEL REPORTE
# =================================
st.divider()
st.subheader("Datos del Reporte")

fecha_reporte = st.date_input(
    "Fecha de Reporte",
    value=date.today()
)

tp1, tp2 = st.columns(2)
with tp1:
    tipo_proveedor = st.selectbox(
        "Tipo de Proveedor",
        ["----", "Interno", "Externo"]
    )
with tp2:
    estado = st.selectbox(
        "Estado",
        ["Inicio / Nuevo"],
        index=0,
        disabled=True
    )

st.text_input(
    "Capturó",
    value=st.session_state.user.get("name") or st.session_state.user.get("email"),
    disabled=True
)

folio_display = (
    st.session_state.folio_generado
    if st.session_state.folio_generado
    else "Folio generado al guardar"
)

c1, c2, c3 = st.columns(3)
with c1:
    oste = st.text_input("OSTE", value="", disabled=True)
with c2:
    no_reporte = st.text_input(
        "No. de Reporte"
    )
with c3:
    st.text_input(
        "No. de Folio",
        value=folio_display,
        disabled=True
    )

# =================================
# SECCIÓN 2 — INFORMACIÓN DEL OPERADOR
# =================================
if tipo_proveedor in ["Interno", "Externo"]:

    st.divider()
    st.subheader(
        "Pase de Taller Interno"
        if tipo_proveedor == "Interno"
        else "Pase de Taller Externo"
    )

    empresa = st.selectbox(
        "Empresa",
        ["Selecciona Empresa"] + EMPRESAS
    )

    if empresa == "Selecciona Empresa":
        st.info("Selecciona una empresa para continuar con la captura del pase.")
        st.stop()

    empresa_codigo = EMPRESA_CODIGOS.get(empresa)
    unidades_df = cargar_unidades_supabase(empresa_codigo)

    # Split dataset
    tractores_df = unidades_df[
        unidades_df["tipo_unidad"] == "TRACTOR"
    ]

    remolques_df = unidades_df[
        unidades_df["tipo_unidad"].isin(["CAJA SECA", "CAJA REFRIGERADA"])
    ]

    tr1, tr2 = st.columns(2)
    with tr1:
        tipo_reporte = st.selectbox(
            "Tipo de Reporte",
            [
                "Selecciona tipo de reporte",
                "Orden Preventivo",
                "Orden Correctivo"
            ]
        )
    with tr2:
        tipo_unidad_operador = st.selectbox(
            "Tipo de Unidad",
            ["Seleccionar tipo de unidad", "Tractores", "Remolques"]
        )

    operador = st.text_input("Operador")

    c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 3])

    if tipo_unidad_operador == "Tractores":

        unidades = ["Selecciona Unidad"] + sorted(
            tractores_df["unidad"]
            .dropna()
            .unique()
            .tolist()
        )

    elif tipo_unidad_operador == "Remolques":

        unidades = ["Selecciona Unidad", "REMOLQUE EXTERNO"] + sorted(
            remolques_df["unidad"]
            .dropna()
            .unique()
            .tolist()
        )

    else:
        unidades = ["Selecciona Unidad"]

    with c1:
        no_unidad = st.selectbox(
            "No. de Unidad",
            unidades,
            disabled=tipo_unidad_operador == "Seleccionar tipo de unidad"
        )

    marca_valor = ""
    modelo_valor = ""
    sucursal_valor = ""
    tipo_caja_auto = ""
    tipo_unidad_valor = ""

    if tipo_unidad_operador == "Tractores" and no_unidad != "Selecciona Unidad":
        fila_match = tractores_df[
            tractores_df["unidad"] == str(no_unidad)
        ]

        if not fila_match.empty:
            fila = fila_match.iloc[0]
        else:
            fila = {}
        marca_valor = fila.get("marca", "")
        modelo_valor = fila.get("modelo", "")
        if pd.notna(modelo_valor):
            try:
                modelo_valor = int(float(modelo_valor))
            except:
                modelo_valor = None
        sucursal_valor = fila.get("SUCURSAL", "")

    elif tipo_unidad_operador == "Remolques":
        if no_unidad == "REMOLQUE EXTERNO":
            marca_valor = "EXTERNO"
            modelo_valor = "0000"
            sucursal_valor = "EXTERNO"
            tipo_caja_auto = ""

        elif no_unidad != "Selecciona Unidad":
            fila_match = remolques_df[
                remolques_df["unidad"].astype(str) == str(no_unidad)
            ]

            if not fila_match.empty:
                fila = fila_match.iloc[0]
            else:
                fila = {}

            marca_valor = fila.get("marca", "")
            modelo_valor = fila.get("modelo", "")
            sucursal_valor = fila.get("sucursal", "")
            tipo_unidad_valor = fila.get("tipo_unidad", "")

    with c2:
        st.text_input("Marca", value=marca_valor, disabled=True)

    with c3:
        st.text_input("Modelo", value=modelo_valor, disabled=True)

    with c4:
        st.text_input("Sucursal", value=sucursal_valor, disabled=True)

    with c5:

        opciones_caja = ["Selecciona Caja", "Caja Seca", "Caja Refrigerada"]

        if tipo_unidad_operador == "Remolques":
            tipo_lower = str(tipo_unidad_valor).lower()

            if "seca" in tipo_lower:
                index_default = 1
            elif "refriger" in tipo_lower or "fria" in tipo_lower or "frío" in tipo_lower:
                index_default = 2
            else:
                index_default = 0
        else:
            index_default = 0

        tipo_caja = st.selectbox(
            "Tipo de Caja",
            opciones_caja if tipo_unidad_operador == "Remolques" else ["Caja no aplicable"],
            index=index_default,
            disabled=tipo_unidad_operador != "Remolques"
        )

    e1, e2 = st.columns(2)
    with e1:
        no_unidad_externo = st.text_input(
            "No. de Unidad Externo",
            disabled=no_unidad != "REMOLQUE EXTERNO"
        )
    with e2:
        linea_externa = st.text_input(
            "Nombre Línea Externa",
            disabled=no_unidad != "REMOLQUE EXTERNO"
        )

    aplica_cobro = st.radio(
        "¿Aplica Cobro?",
        ["No", "Sí"],
        horizontal=True,
        index=0
    )

    responsable = st.text_input(
        "Responsable",
        disabled=aplica_cobro != "Sí"
    )

    descripcion_problema = st.text_area("Descripción del problema")

    genero_multa = st.checkbox("¿Generó multa?")

    no_inspeccion = st.text_input(
        "No. de Inspección",
        disabled=not genero_multa
    )

    reparacion_multa = st.text_area(
        "Reparación que generó multa",
        placeholder="Por favor introducir # de reporte aplicable",
        disabled=not genero_multa
    )

    st.divider()
    st.markdown("###")

    # =================================
    # GUARDAR
    # =================================
    if st.button("💾 Guardar Pase", type="primary", use_container_width=True):

        # ==========================================
        # HARD VALIDATIONS (LOCK)
        # ==========================================
        if no_unidad == "Selecciona Unidad":
            st.error("Debes seleccionar un No. de Unidad válido antes de guardar.")
            st.stop()

        if no_unidad == "REMOLQUE EXTERNO" and not (no_unidad_externo and str(no_unidad_externo).strip()):
            st.error("Debes capturar el No. de Unidad Externo.")
            st.stop()

        if aplica_cobro == "Sí" and not (responsable and str(responsable).strip()):
            st.error("Debes capturar el Responsable cuando aplica cobro.")
            st.stop()

        if genero_multa and not (no_inspeccion and str(no_inspeccion).strip()):
            st.error("Debes capturar el No. de Inspección cuando se genera multa.")
            st.stop()

        if genero_multa and not (reparacion_multa and str(reparacion_multa).strip()):
            st.error("Debes capturar la Reparación que generó multa cuando se genera multa.")
            st.stop()

        # make sure flags exist
        st.session_state.setdefault("forzar_guardado", False)
        st.session_state.setdefault("confirmar_guardado", False)
        st.session_state.setdefault("folio_duplicado", "")

        # ==========================================
        # DUPLICATE CHECK — LAST 24 HOURS
        # ==========================================
        unidad_a_buscar = (
            no_unidad_externo if no_unidad == "REMOLQUE EXTERNO" else no_unidad
        )

        folio_existente = buscar_unidad_reciente(
            empresa,
            no_unidad,
            no_unidad_externo
        )

        # If duplicate AND not forcing → ask confirmation
        if folio_existente and not st.session_state.forzar_guardado:
            st.session_state.folio_duplicado = folio_existente
            st.session_state.confirmar_guardado = True
            st.rerun()

        # ==========================================
        # NORMAL SAVE
        # ==========================================
        payload = {
            "Fecha de Captura": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "Fecha de Reporte": str(fecha_reporte),
            "Tipo de Proveedor": tipo_proveedor,
            "Estado": "Inicio / Nuevo",
            "Capturo": st.session_state.user.get("name") or st.session_state.user.get("email"),
            "Oste": oste,
            "No. de Reporte": no_reporte,
            "Empresa": empresa,
            "Tipo de Reporte": tipo_reporte,
            "Tipo de Unidad": tipo_unidad_operador,
            "Operador": operador,
            "No. de Unidad": no_unidad,
            "Marca": marca_valor,
            "Modelo": modelo_valor,
            "Sucursal": sucursal_valor,
            "Tipo de Caja": tipo_caja,
            "No. de Unidad Externo": no_unidad_externo,
            "Nombre Linea Externa": linea_externa,
            "Cobro": str(aplica_cobro),
            "Responsable": responsable,
            "Descripcion Problema": descripcion_problema,
            "Multa": "Sí" if genero_multa else "No",
            "No. de Inspeccion": no_inspeccion,
            "Reparacion Multa": reparacion_multa,
        }

        folio_real = append_pase_to_sheet(payload)

        # important → clear force flag after using it
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
                f"**No. de Folio:** `{st.session_state.folio_generado}`"
            )

            if st.button("Aceptar"):
                st.session_state.mostrar_confirmacion = False
                st.session_state.folio_generado = ""
                st.switch_page("pages/dashboard.py")

        confirmacion()