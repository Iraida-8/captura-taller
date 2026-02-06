import streamlit as st
import pandas as pd
from datetime import datetime, date

from auth import require_login, require_access

import gspread
from google.oauth2.service_account import Credentials
import os

from datetime import datetime

fecha_mod = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# =================================
# Page configuration
# =================================
st.set_page_config(
    page_title="Autorización y Actualización de Reporte",
    layout="wide"
)

# =================================
# Hide sidebar
# =================================
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] { display: none; }
    </style>
    """,
    unsafe_allow_html=True
)

# =================================
# Security
# =================================
require_login()
require_access("autorizacion")

# =================================
# Defensive reset on page entry
# =================================
if st.session_state.get("_reset_autorizacion_page", True):
    st.session_state.modal_reporte = None
    st.session_state.buscar_trigger = False
    st.session_state["_reset_autorizacion_page"] = False

# =================================
# Navigation
# =================================
if st.button("⬅ Volver al Dashboard"):
    st.session_state.modal_reporte = None
    st.session_state.buscar_trigger = False
    st.switch_page("pages/dashboard.py")

st.divider()

# =================================
# Google Sheets credentials
# =================================
def get_gsheets_credentials():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]

    try:
        if "gcp_service_account" in st.secrets:
            return Credentials.from_service_account_info(
                st.secrets["gcp_service_account"], scopes=scopes
            )
    except Exception:
        pass

    if os.path.exists("google_service_account.json"):
        return Credentials.from_service_account_file(
            "google_service_account.json", scopes=scopes
        )

    raise RuntimeError("Google Sheets credentials not found")

# =================================
# Update Estado
# =================================
def actualizar_estado_pase(empresa, folio, nuevo_estado):
    sheet_map = {
        "IGLOO TRANSPORT": "IGLOO",
        "LINCOLN FREIGHT": "LINCOLN",
        "PICUS": "PICUS",
        "SET FREIGHT INTERNATIONAL": "SFI",
        "SET LOGIS PLUS": "SLP",
    }

    hoja = sheet_map.get(empresa)
    if not hoja:
        return

    client = gspread.authorize(get_gsheets_credentials())
    ws = client.open_by_key(
        "1ca46k4PCbvNMvZjsgU_2MHJULADRJS5fnghLopSWGDA"
    ).worksheet(hoja)

    folios = ws.col_values(2)
    if folio not in folios:
        return

    row_idx = folios.index(folio) + 1
    headers = ws.row_values(1)
    estado_col = headers.index("Estado") + 1

    ws.update_cell(row_idx, estado_col, nuevo_estado)

# =================================
# Update OSTE
# =================================
def actualizar_oste_pase(empresa, folio, oste):
    sheet_map = {
        "IGLOO TRANSPORT": "IGLOO",
        "LINCOLN FREIGHT": "LINCOLN",
        "PICUS": "PICUS",
        "SET FREIGHT INTERNATIONAL": "SFI",
        "SET LOGIS PLUS": "SLP",
    }

    hoja = sheet_map.get(empresa)
    if not hoja:
        return

    client = gspread.authorize(get_gsheets_credentials())
    ws = client.open_by_key(
        "1ca46k4PCbvNMvZjsgU_2MHJULADRJS5fnghLopSWGDA"
    ).worksheet(hoja)

    folios = ws.col_values(2)
    if folio not in folios:
        return

    row_idx = folios.index(folio) + 1
    headers = ws.row_values(1)

    if "Oste" not in headers:
        return

    oste_col = headers.index("Oste") + 1
    ws.update_cell(row_idx, oste_col, oste)

# =================================
# Load Servicios for Folio
# =================================
def cargar_servicios_folio(folio):
    client = gspread.authorize(get_gsheets_credentials())
    ws = client.open_by_key(
        "1ca46k4PCbvNMvZjsgU_2MHJULADRJS5fnghLopSWGDA"
    ).worksheet("SERVICES")

    data = ws.get_all_records()
    if not data:
        return pd.DataFrame(columns=[
            "Parte","TipoCompra","Precio MXP","IVA","Cantidad","Total MXN"
        ])

    df = pd.DataFrame(data)

    # 🔹 PATCH: normalize headers
    df.columns = df.columns.str.strip()

    if "No. de Folio" in df.columns:
        df = df.rename(columns={"No. de Folio": "Folio"})

    # 🔴 THIS IS THE MISSING LINE
    if "Iva" in df.columns:
        df = df.rename(columns={"Iva": "IVA"})

    # 🔹 Ensure string comparison
    df["Folio"] = df["Folio"].astype(str)

    df = df[df["Folio"] == str(folio)]

    return df[
        ["Parte","TipoCompra","Precio MXP","IVA","Cantidad","Total MXN"]
    ]

# =================================
# UPSERT Servicios / Refacciones
# =================================
def guardar_servicios_refacciones(folio, usuario, servicios_df):
    from datetime import datetime

    client = gspread.authorize(get_gsheets_credentials())
    ws = client.open_by_key(
        "1ca46k4PCbvNMvZjsgU_2MHJULADRJS5fnghLopSWGDA"
    ).worksheet("SERVICES")

    fecha_mod = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # =====================================================
    # PHASE 1 — LOAD WITH REAL ROW NUMBERS
    # =====================================================
    all_values = ws.get_all_values()

    if len(all_values) < 2:
        headers = [
            "No. de Folio","Modifico","Parte","TipoCompra",
            "Precio MXP","IVA","Cantidad","Total MXN","Fecha Mod"
        ]
        df_db = pd.DataFrame(columns=headers + ["__rownum__"])
    else:
        headers = [h.strip() for h in all_values[0]]
        rows = all_values[1:]
        df_db = pd.DataFrame(rows, columns=headers)
        df_db["__rownum__"] = range(2, len(rows) + 2)

    # =====================================================
    # Normalize headers
    # =====================================================
    if "No. de Folio" in df_db.columns:
        df_db = df_db.rename(columns={"No. de Folio": "Folio"})
    if "Iva" in df_db.columns:
        df_db = df_db.rename(columns={"Iva": "IVA"})

    df_db["Folio"] = df_db["Folio"].astype(str)

    servicios_df = servicios_df.copy()
    servicios_df["Parte"] = servicios_df["Parte"].astype(str)

    df_folio = df_db[df_db["Folio"] == str(folio)]

    # =====================================================
    # PHASE 2 — DELETE REMOVED ITEMS
    # =====================================================
    partes_actuales = set(servicios_df["Parte"])

    rows_to_delete = df_folio[
        ~df_folio["Parte"].isin(partes_actuales)
    ]["__rownum__"].tolist()

    for rownum in sorted(rows_to_delete, reverse=True):
        ws.delete_rows(rownum)

    # =====================================================
    # PHASE 3 — RELOAD AFTER DELETE (CRITICAL)
    # =====================================================
    all_values = ws.get_all_values()

    if len(all_values) < 2:
        df_db = pd.DataFrame(columns=["Folio","Parte","__rownum__"])
    else:
        headers = [h.strip() for h in all_values[0]]
        rows = all_values[1:]
        df_db = pd.DataFrame(rows, columns=headers)
        df_db["__rownum__"] = range(2, len(rows) + 2)

    if "No. de Folio" in df_db.columns:
        df_db = df_db.rename(columns={"No. de Folio": "Folio"})
    if "Iva" in df_db.columns:
        df_db = df_db.rename(columns={"Iva": "IVA"})

    df_db["Folio"] = df_db["Folio"].astype(str)
    df_folio = df_db[df_db["Folio"] == str(folio)]

    # =====================================================
    # PHASE 4 — UPSERT (SAFE)
    # =====================================================
    for _, r in servicios_df.iterrows():
        match = df_folio[df_folio["Parte"] == r["Parte"]]

        row_data = [
            folio,                      # No. de Folio
            usuario,                    # Modifico
            r["Parte"],
            r["TipoCompra"],
            float(r["Precio MXP"] or 0),
            float(r["IVA"] or 0),
            int(r["Cantidad"] or 0),
            float(r["Total MXN"] or 0),
            fecha_mod,                  # Fecha Mod
        ]

        if not match.empty:
            rownum = int(match.iloc[0]["__rownum__"])
            ws.update(f"A{rownum}:I{rownum}", [row_data])
        else:
            ws.append_row(row_data, value_input_option="USER_ENTERED")

# =================================
# Load Pase de Taller
# =================================
@st.cache_data(ttl=300)
def cargar_pases_taller():
    SPREADSHEET_ID = "1ca46k4PCbvNMvZjsgU_2MHJULADRJS5fnghLopSWGDA"
    hojas = ["IGLOO", "LINCOLN", "PICUS", "SFI", "SLP"]

    client = gspread.authorize(get_gsheets_credentials())
    dfs = []

    for hoja in hojas:
        try:
            ws = client.open_by_key(SPREADSHEET_ID).worksheet(hoja)
            data = ws.get_all_records()
            if data:
                dfs.append(pd.DataFrame(data))
        except Exception:
            pass

    if not dfs:
        return pd.DataFrame()

    df = pd.concat(dfs, ignore_index=True)

    df.rename(columns={
        "No. de Folio": "NoFolio",
        "Fecha de Captura": "Fecha",
        "Tipo de Proveedor": "Proveedor",
    }, inplace=True)

    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    df["NoFolio"] = df["NoFolio"].astype(str)
    return df

pases_df = cargar_pases_taller()

# =================================
# Catalogs (READ ONLY)
# =================================

@st.cache_data(ttl=600)
def cargar_catalogo_igloo_simple():
    URL = (
        "https://docs.google.com/spreadsheets/d/"
        "18tFOA4prD-PWhtbc35cqKXxYcyuqGOC7"
        "/export?format=csv&gid=410297659"
    )

    df = pd.read_csv(URL)
    df.columns = df.columns.str.strip()
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    df = df[df["Fecha"] >= pd.Timestamp("2025-01-01")]
    df = df.sort_values("Fecha", ascending=False)
    df = df.drop_duplicates(subset=["Parte"], keep="first")

    def limpiar_num(v):
        try:
            return float(str(v).replace("$", "").replace(",", "").strip())
        except:
            return None

    df["PU"] = df["PrecioParte"].apply(limpiar_num)

    df["label"] = df.apply(
        lambda r: f"{r['Parte']} - ${r['PU']:,.2f}"
        if pd.notna(r["PU"]) else r["Parte"],
        axis=1
    )

    return df[["Parte", "PU", "label"]]


@st.cache_data(ttl=600)
def cargar_catalogo_lincoln():
    URL = (
        "https://docs.google.com/spreadsheets/d/"
        "1lcNr73nHrMpsqdYBNxtTQFqFmY1Ey9gp"
        "/export?format=csv&gid=41991257"
    )

    df = pd.read_csv(URL)
    df.columns = df.columns.str.strip()

    def limpiar_num(v):
        try:
            return float(str(v).replace("$", "").replace(",", "").strip())
        except:
            return None

    df["PU"] = df["PrecioParte"].apply(limpiar_num)

    df["label"] = df.apply(
        lambda r: f"{r['Parte']} - ${r['PU']:,.2f}"
        if pd.notna(r["PU"]) else r["Parte"],
        axis=1
    )

    return df[["Parte", "PU", "label"]]


@st.cache_data(ttl=600)
def cargar_catalogo_picus():
    URL = (
        "https://docs.google.com/spreadsheets/d/"
        "1tzt6tYG94oVt8YwK3u9gR-DHFcuadpNN"
        "/export?format=csv&gid=354598948"
    )

    df = pd.read_csv(URL)
    df.columns = df.columns.str.strip()

    def limpiar_num(v):
        try:
            return float(str(v).replace("$", "").replace(",", "").strip())
        except:
            return None

    df["PU"] = df["PrecioParte"].apply(limpiar_num)

    df["label"] = df.apply(
        lambda r: f"{r['Parte']} - ${r['PU']:,.2f}"
        if pd.notna(r["PU"]) else r["Parte"],
        axis=1
    )

    return df[["Parte", "PU", "label"]]

@st.cache_data(ttl=600)
def cargar_catalogo_sfi():
    URL = (
        "https://docs.google.com/spreadsheets/d/"
        "1Nqbhl8o5qaKhI4LNxreicPW5Ew8kqShS"
        "/export?format=csv&gid=849445619"
    )

    df = pd.read_csv(URL)
    df.columns = df.columns.str.strip()

    def limpiar_num(v):
        try:
            return float(str(v).replace("$", "").replace(",", "").strip())
        except:
            return None

    # Defensive price-column detection (same pattern we discussed)
    precio_col = next(
        (c for c in df.columns if c.lower() in ["precioparte", "precio", "pu", "costo"]),
        None
    )

    if precio_col:
        df["PU"] = df[precio_col].apply(limpiar_num)
    else:
        df["PU"] = None

    df["label"] = df.apply(
        lambda r: f"{r['Parte']} - ${r['PU']:,.2f}"
        if pd.notna(r["PU"]) else r["Parte"],
        axis=1
    )

    return df[["Parte", "PU", "label"]]

@st.cache_data(ttl=600)
def cargar_catalogo_slp():
    URL = (
        "https://docs.google.com/spreadsheets/d/"
        "1yrzwm5ixsaYNKwkZpfmFpDdvZnohFH61"
        "/export?format=csv&gid=1837946138"
    )

    df = pd.read_csv(URL)
    df.columns = df.columns.str.strip()

    def limpiar_num(v):
        try:
            return float(str(v).replace("$", "").replace(",", "").strip())
        except:
            return None

    # Defensive price-column detection
    precio_col = next(
        (c for c in df.columns if c.lower() in ["precioparte", "precio", "pu", "costo"]),
        None
    )

    if precio_col:
        df["PU"] = df[precio_col].apply(limpiar_num)
    else:
        df["PU"] = None

    df["label"] = df.apply(
        lambda r: f"{r['Parte']} - ${r['PU']:,.2f}"
        if pd.notna(r["PU"]) else r["Parte"],
        axis=1
    )

    return df[["Parte", "PU", "label"]]

# =================================
# Catalog dispatcher by Empresa
# =================================
def cargar_catalogo_por_empresa(empresa):
    if empresa == "IGLOO TRANSPORT":
        return cargar_catalogo_igloo_simple()

    if empresa == "LINCOLN FREIGHT":
        return cargar_catalogo_lincoln()

    if empresa == "PICUS":
        return cargar_catalogo_picus()

    if empresa == "SET FREIGHT INTERNATIONAL":
        return cargar_catalogo_sfi()

    if empresa == "SET LOGIS PLUS":
        return cargar_catalogo_slp()

    return None

# =================================
# Title
# =================================
st.title("📋 Autorización y Actualización de Reporte")

# =================================
# Session state defaults
# =================================
st.session_state.setdefault("buscar_trigger", False)
st.session_state.setdefault("modal_reporte", None)
st.session_state.setdefault("refaccion_seleccionada", None)
st.session_state.setdefault(
    "servicios_df",
    pd.DataFrame(columns=[
        "Parte","TipoCompra","Precio MXP","IVA","Cantidad","Total MXN"
    ])
)

# =================================
# TOP 10 EN CURSO
# =================================
st.subheader("Últimos 10 Pases de Taller (En Curso)")

if not pases_df.empty:
    top10 = (
        pases_df[pases_df["Estado"].str.startswith("En Curso", na=False)]
        .sort_values("Fecha", ascending=False)
        .head(10)
        [["NoFolio","Empresa","Fecha","Proveedor","Estado"]]
    )
    st.dataframe(top10, hide_index=True, width="stretch")
else:
    st.info("No hay pases registrados.")

# =================================
# BUSCAR
# =================================
st.divider()
st.subheader("Buscar Pase de Taller")

empresas = sorted(pases_df["Empresa"].dropna().unique()) if not pases_df.empty else []

f1, f2, f3, f4 = st.columns(4)

with f1:
    f_folio = st.text_input("No. de Folio")

with f2:
    f_empresa = st.selectbox("Empresa", ["Selecciona empresa"] + empresas)

with f3:
    f_estado = st.selectbox(
        "Estado",
        [
            "Selecciona estado",
            "En Curso / Nuevo",
            "En Curso / Autorizado",
            "En Curso / Sin Comenzar",
            "En Curso / Espera Refacciones",
            "Cerrado / Cancelado",
            "Cerrado / Completado",
        ]
    )

with f4:
    f_fecha = st.date_input("Fecha", value=None)

if st.button("Buscar"):
    st.session_state.buscar_trigger = True
    st.session_state.modal_reporte = None

# =================================
# RESULTADOS
# =================================
if st.session_state.buscar_trigger:
    resultados = pases_df.copy()

    if f_folio:
        resultados = resultados[resultados["NoFolio"].str.contains(f_folio)]

    if f_empresa != "Selecciona empresa":
        resultados = resultados[resultados["Empresa"] == f_empresa]

    if f_estado != "Selecciona estado":
        resultados = resultados[resultados["Estado"] == f_estado]

    if f_fecha:
        resultados = resultados[resultados["Fecha"].dt.date == f_fecha]

    st.divider()
    st.subheader("Resultados")

    for _, row in resultados.iterrows():
        c1, c2, c3, c4, c5, c6 = st.columns([1,2,2,2,2,1])

        editable = row["Estado"].startswith("En Curso")

        with c1:
            label = "Editar" if editable else "Ver"
            if st.button(label, key=f"accion_{row['NoFolio']}"):
                st.session_state.modal_reporte = row.to_dict()
                st.session_state.servicios_df = cargar_servicios_folio(row["NoFolio"])

        c2.write(row["NoFolio"])
        c3.write(row["Empresa"])
        c4.write(row["Proveedor"])
        c5.write(row["Estado"])
        c6.write(row["Fecha"].date() if pd.notna(row["Fecha"]) else "")

# =================================
# MODAL
# =================================
if st.session_state.modal_reporte:

    r = st.session_state.modal_reporte
    editable_estado = r["Estado"].startswith("En Curso")

    @st.dialog("Detalle del Pase de Taller")
    def modal():

        st.markdown(f"**No. de Folio:** {r['NoFolio']}")
        st.markdown(f"**Empresa:** {r['Empresa']}")
        st.markdown(f"**Fecha:** {r['Fecha']}")
        st.markdown(f"**Proveedor:** {r['Proveedor']}")
        st.markdown(f"**No. de Unidad:** {r.get('No. de Unidad', '')}")
        st.markdown(f"**Sucursal:** {r.get('Sucursal', '')}")


        st.divider()
        st.subheader("Información del Proveedor")

        oste_editable = r["Estado"] == "Cerrado / Facturado"

        proveedor = (r.get("Proveedor") or "").lower()

        # =========================
        # PROVEEDOR INTERNO
        # =========================
        if "interno" in proveedor:
            st.text_input(
                "No. de Reporte",
                value=r.get("No. de Reporte", ""),
                disabled=True
            )

        # =========================
        # PROVEEDOR EXTERNO
        # =========================
        else:
            oste_val = st.text_input(
                "OSTE",
                value=r.get("Oste", "") or "",
                disabled=not oste_editable
            )

        opciones_estado = [
            "En Curso / Autorizado",
            "En Curso / Sin Comenzar",
            "En Curso / Espera Refacciones",
            "Cerrado / Facturado",
            "Cerrado / Cancelado",
            "Cerrado / Completado",
        ]

        nuevo_estado = st.selectbox(
            "Estado",
            opciones_estado,
            index=opciones_estado.index(r["Estado"])
            if r["Estado"] in opciones_estado else 0,
            disabled=not editable_estado
        )

        editable_servicios = nuevo_estado in [
            "En Curso / Sin Comenzar",
            "En Curso / Espera Refacciones",
]

        st.divider()
        st.subheader("Servicios y Refacciones")

        catalogo = cargar_catalogo_por_empresa(r["Empresa"])

        if catalogo is not None and not catalogo.empty:
            st.session_state.refaccion_seleccionada = st.selectbox(
                "Refacción / Servicio",
                options=catalogo["label"].tolist(),
                index=None,
                disabled=not editable_servicios
            )
        else:
            st.info("Catálogo no disponible para esta empresa.")


        if st.button(
            "Agregar refacciones o servicios",
            disabled=not editable_servicios or not st.session_state.refaccion_seleccionada
        ):
            fila = catalogo[catalogo["label"] == st.session_state.refaccion_seleccionada].iloc[0]

            if fila["Parte"] not in st.session_state.servicios_df["Parte"].values:
                nueva = {
                    "Parte": fila["Parte"],
                    "TipoCompra": "Servicio",
                    "Precio MXP": fila["PU"],
                    "IVA": 0.0,
                    "Cantidad": 1,
                    "Total MXN": fila["PU"],
                }

                st.session_state.servicios_df = pd.concat(
                    [st.session_state.servicios_df, pd.DataFrame([nueva])],
                    ignore_index=True
                )

        edited_df = st.data_editor(
            st.session_state.servicios_df,
            num_rows="dynamic",
            hide_index=True,
            disabled=not editable_servicios,
            column_config={
                "Precio MXP": st.column_config.NumberColumn(format="$ %.2f"),
                "IVA": st.column_config.NumberColumn(format="%.2f"),
                "Cantidad": st.column_config.NumberColumn(min_value=1, step=1),
                "Total MXN": st.column_config.NumberColumn(format="$ %.2f"),
            },
        )

        if not edited_df.empty:
            edited_df["Total MXN"] = (
                edited_df["Precio MXP"].fillna(0)
                * edited_df["Cantidad"].fillna(0)
                * (1 + edited_df["IVA"].fillna(0))
            )

        st.session_state.servicios_df = edited_df

        st.metric(
            "Total MXN",
            f"$ {st.session_state.servicios_df['Total MXN'].fillna(0).sum():,.2f}"
        )

        st.divider()
        c1, c2 = st.columns(2)

        with c1:
            if st.button("Cancelar"):
                st.session_state.modal_reporte = None
                st.rerun()

        with c2:
            if st.button("Aceptar", type="primary") and editable_estado:

                if nuevo_estado != r["Estado"]:
                    actualizar_estado_pase(r["Empresa"], r["NoFolio"], nuevo_estado)

                # =========================
                # Guardar OSTE (solo externo y solo Facturado)
                # =========================
                if "interno" not in (r.get("Proveedor") or "").lower():
                    if nuevo_estado == "Cerrado / Facturado":
                        actualizar_oste_pase(
                            r["Empresa"],
                            r["NoFolio"],
                            oste_val
                        )

                guardar_servicios_refacciones(
                    r["NoFolio"],
                    st.session_state.user.get("name")
                    or st.session_state.user.get("email"),
                    st.session_state.servicios_df
                )

                st.session_state.modal_reporte = None
                st.cache_data.clear()
                st.rerun()

    modal()
    st.session_state.modal_reporte = None