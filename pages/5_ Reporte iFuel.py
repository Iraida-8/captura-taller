import streamlit as st
import pandas as pd
import json
import math
import numpy as np
from io import BytesIO
from auth import require_login

require_login()

st.title("Dashboard")
st.set_page_config(page_title="Fuel Solutions Parser", layout="wide")
st.title("Fuel Solutions → 3 Tablas + Comparativo + % Pilot/FlyingJ vs Otras + Export Excel")

uploaded = st.file_uploader("Sube tu archivo Excel", type=["xlsx"])

# -----------------------------
# Helpers
# -----------------------------
def safe_json_loads(x):
    try:
        if pd.isna(x):
            return None
        return json.loads(x)
    except Exception:
        return None

def haversine_miles(lat1, lon1, lat2, lon2):
    """
    Distancia en línea recta (Haversine) en millas.
    """
    r = 3958.7613  # Radio Tierra en millas
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))

def is_pilot_group(text: str) -> bool:
    """
    Considera Pilot + Flying J como el mismo grupo.
    """
    if text is None or pd.isna(text):
        return False
    t = str(text).lower()
    return ("pilot" in t) or ("flying j" in t) or ("flyingj" in t)

# -----------------------------
# Parse JSON -> 3 tablas
# -----------------------------
def build_tables(df_filtered: pd.DataFrame):
    trips_rows = []
    purchases_rows = []
    onroute_rows = []

    for _, row in df_filtered.iterrows():
        fsid = row["FSID"]
        created_at = row["FSCreatedAt"]
        payload = safe_json_loads(row["FSJSON"])
        if not payload:
            continue

        # 1) Trip (1 fila por FSID)
        origin = payload.get("origin", {}) or {}
        dest = payload.get("destination", {}) or {}

        trip = {
            "FSID": fsid,
            "FSCreatedAt": created_at,
            "customer": payload.get("customer"),
            "unitNumber": payload.get("unitNumber"),
            "origin_location": origin.get("location"),
            "origin_lat": origin.get("lat"),
            "origin_lng": origin.get("lng"),
            "destination_location": dest.get("location"),
            "destination_lat": dest.get("lat"),
            "destination_lng": dest.get("lng"),
            "totalTripDistanceMiles": payload.get("totalTripDistanceMiles"),
            "totalFuelNeededGallons": payload.get("totalFuelNeededGallons"),
            "totalPurchaseNeededGallons": payload.get("totalPurchaseNeededGallons"),
            "savings": payload.get("savings"),
        }
        trips_rows.append(trip)

        # 2) fuelPurchaseLocations (N filas por FSID)
        for p in payload.get("fuelPurchaseLocations", []) or []:
            purchases_rows.append({
                "FSID": fsid,
                "FSCreatedAt": created_at,
                "loc_id": p.get("loc_id"),
                "active": p.get("active"),
                "fuelToPurchase": p.get("fuelToPurchase"),
                "lat": p.get("lat"),
                "lng": p.get("lng"),
                "location": p.get("location"),
                "price": p.get("price"),
                "include": p.get("include"),
                "interstate_exit": p.get("interstate_exit"),
            })

        # 3) fuelStationOnRoute (N filas por FSID) viene como DataFrame serializado
        fsor = payload.get("fuelStationOnRoute")
        if isinstance(fsor, dict) and "columns" in fsor and "data" in fsor:
            cols = fsor["columns"]
            data = fsor["data"]
            tmp = pd.DataFrame(data, columns=cols)
            tmp.insert(0, "FSID", fsid)
            tmp.insert(1, "FSCreatedAt", created_at)
            onroute_rows.append(tmp)

    trips_df = pd.DataFrame(trips_rows)
    purchases_df = pd.DataFrame(purchases_rows)
    onroute_df = pd.concat(onroute_rows, ignore_index=True) if onroute_rows else pd.DataFrame()

    return trips_df, purchases_df, onroute_df

# -----------------------------
# Comparativo: compra NO PilotGroup vs Pilot/FlyingJ más cercano en ruta
# -----------------------------
def build_comparativo(purchases_df: pd.DataFrame, onroute_df: pd.DataFrame) -> pd.DataFrame:
    if purchases_df.empty or onroute_df.empty:
        return pd.DataFrame()

    # Asegurar columnas esperadas en onroute
    needed = {"Address", "Price", "h_lat", "h_lon", "FSID"}
    if not needed.issubset(set(onroute_df.columns)):
        return pd.DataFrame()

    # Solo estaciones Pilot/FlyingJ en Stations On Route
    mask = (
        onroute_df["Address"].astype(str).str.contains("Pilot", case=False, na=False)
        | onroute_df["Address"].astype(str).str.contains("Flying J", case=False, na=False)
        | onroute_df["Address"].astype(str).str.contains("FlyingJ", case=False, na=False)
    )
    stations_group = onroute_df[mask].copy()

    # Agrupar por FSID para que el comparativo sea dentro del mismo viaje
    group_by_fsid = {fsid: grp.reset_index(drop=True) for fsid, grp in stations_group.groupby("FSID")}

    df = purchases_df.copy()
    df["is_pilot_group_purchase"] = df["location"].apply(is_pilot_group)

    # Solo compras NO PilotGroup
    df = df[~df["is_pilot_group_purchase"]].copy()
    if df.empty:
        return pd.DataFrame()

    def nearest_station_in_group(row):
        fsid = row["FSID"]
        grp = group_by_fsid.get(fsid)

        if grp is None or grp.empty:
            return pd.Series({
                "nearest_pilotgroup_address": np.nan,
                "nearest_pilotgroup_price": np.nan,
                "distance_to_nearest_pilotgroup_miles": np.nan
            })

        if pd.isna(row.get("lat")) or pd.isna(row.get("lng")):
            return pd.Series({
                "nearest_pilotgroup_address": np.nan,
                "nearest_pilotgroup_price": np.nan,
                "distance_to_nearest_pilotgroup_miles": np.nan
            })

        lat1 = float(row["lat"])
        lon1 = float(row["lng"])

        dists = np.array([
            haversine_miles(lat1, lon1, float(la), float(lo))
            for la, lo in zip(grp["h_lat"], grp["h_lon"])
        ])

        i = int(dists.argmin())
        return pd.Series({
            "nearest_pilotgroup_address": grp.loc[i, "Address"],
            "nearest_pilotgroup_price": grp.loc[i, "Price"],
            "distance_to_nearest_pilotgroup_miles": float(dists[i]),
        })

    nearest_cols = df.apply(nearest_station_in_group, axis=1)
    comp = pd.concat([df.reset_index(drop=True), nearest_cols.reset_index(drop=True)], axis=1)

    # Diferencias de precio (tu carga - la mejor alternativa del grupo cercana)
    comp["price_diff_per_gallon_vs_pilotgroup"] = comp["price"] - comp["nearest_pilotgroup_price"]

    # (Opcional) diferencia estimada en costo si fuelToPurchase son galones reales
    comp["est_cost_diff"] = comp["price_diff_per_gallon_vs_pilotgroup"] * comp["fuelToPurchase"]

    return comp

# -----------------------------
# Excel export
# -----------------------------
def to_excel_bytes(trips_df, purchases_df, onroute_df, comparativo_df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        trips_df.to_excel(writer, index=False, sheet_name="Trip")
        purchases_df.to_excel(writer, index=False, sheet_name="Fuel Purchases")
        onroute_df.to_excel(writer, index=False, sheet_name="Stations On Route")
        comparativo_df.to_excel(writer, index=False, sheet_name="Comparativo Non-Pilot")
    output.seek(0)
    return output

# -----------------------------
# App flow
# -----------------------------
if uploaded:
    base = pd.read_excel(uploaded, sheet_name="Fuel Solutions", usecols=["FSID", "FSJSON", "FSCreatedAt"])
    base["FSCreatedAt"] = pd.to_datetime(base["FSCreatedAt"], errors="coerce")

    base = base.dropna(subset=["FSCreatedAt"])
    base["Year"] = base["FSCreatedAt"].dt.year
    base["Month"] = base["FSCreatedAt"].dt.month

    years = sorted(base["Year"].dropna().unique().tolist())
    year = st.sidebar.selectbox("Año", years, index=len(years)-1 if years else 0)

    months = sorted(base.loc[base["Year"] == year, "Month"].dropna().unique().tolist())
    month = st.sidebar.selectbox("Mes", months, index=len(months)-1 if months else 0)

    filtered = base[(base["Year"] == year) & (base["Month"] == month)].copy()
    st.caption(f"Registros filtrados: {len(filtered):,} (Año={year}, Mes={month})")

    trips_df, purchases_df, onroute_df = build_tables(filtered)

    # % Pilot/FlyingJ vs otras (sobre Fuel Purchases)
    if not purchases_df.empty:
        purchases_df["is_pilot_group_purchase"] = purchases_df["location"].apply(is_pilot_group)
        total = len(purchases_df)
        group_count = int(purchases_df["is_pilot_group_purchase"].sum())
        other_count = total - group_count

        group_pct = (group_count / total) * 100 if total else 0
        other_pct = (other_count / total) * 100 if total else 0

        c1, c2, c3 = st.columns(3)
        c1.metric("Cargas (total)", f"{total:,}")
        c2.metric("Cargas Pilot/Flying J", f"{group_pct:.1f}%", f"{group_count:,}")
        c3.metric("Cargas en otras", f"{other_pct:.1f}%", f"{other_count:,}")
    else:
        st.info("No hay compras para calcular porcentajes.")

    # Comparativo
    comparativo_df = build_comparativo(purchases_df, onroute_df)

    st.subheader("Tabla 1: Trip (1 fila por FSID)")
    st.dataframe(trips_df, use_container_width=True)

    st.subheader("Tabla 2: Fuel Purchases (paradas de compra)")
    st.dataframe(purchases_df, use_container_width=True)

    st.subheader("Tabla 3: Stations On Route (todas las estaciones en ruta)")
    st.dataframe(onroute_df, use_container_width=True)

    st.subheader("Tabla 4: Comparativo Non-Pilot (carga NO Pilot/FlyingJ vs opción más cercana Pilot/FlyingJ)")
    if comparativo_df.empty:
        st.info("No se generó comparativo (o todas las cargas fueron Pilot/FlyingJ, o faltan datos).")
    else:
        st.caption("Distancia calculada en línea recta (haversine).")
        st.dataframe(comparativo_df, use_container_width=True)

    excel_bytes = to_excel_bytes(trips_df, purchases_df, onroute_df, comparativo_df)

    st.download_button(
        label="⬇️ Descargar Excel (4 hojas)",
        data=excel_bytes,
        file_name=f"fuel_solutions_{year}_{month:02d}_con_comparativo.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
else:
    st.info("Sube el Excel para empezar.")