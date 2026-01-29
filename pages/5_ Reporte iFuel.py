import streamlit as st
import pandas as pd
import json
import math
import numpy as np
from io import BytesIO

from auth import require_login, require_access

# =================================
# Page configuration (MUST BE FIRST)
# =================================
st.set_page_config(
    page_title="Fuel Solutions Parser",
    layout="wide"
)

# =================================
# Hide sidebar completely
# =================================
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        display: none;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# =================================
# Security gates
# =================================
require_login()
require_access("ifuel")

# =================================
# Top navigation
# =================================
if st.button("⬅ Volver al Dashboard"):
    st.switch_page("pages/dashboard.py")

st.divider()

# =================================
# Page title
# =================================
st.title("Fuel Solutions → Análisis y Comparativos")

uploaded = st.file_uploader(
    "Sube tu archivo Excel",
    type=["xlsx"]
)

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
    r = 3958.7613  # Radio Tierra en millas
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def is_pilot_group(text: str) -> bool:
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

        origin = payload.get("origin", {}) or {}
        dest = payload.get("destination", {}) or {}

        trips_rows.append({
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
        })

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

        fsor = payload.get("fuelStationOnRoute")
        if isinstance(fsor, dict) and "columns" in fsor and "data" in fsor:
            tmp = pd.DataFrame(fsor["data"], columns=fsor["columns"])
            tmp.insert(0, "FSID", fsid)
            tmp.insert(1, "FSCreatedAt", created_at)
            onroute_rows.append(tmp)

    trips_df = pd.DataFrame(trips_rows)
    purchases_df = pd.DataFrame(purchases_rows)
    onroute_df = pd.concat(onroute_rows, ignore_index=True) if onroute_rows else pd.DataFrame()

    return trips_df, purchases_df, onroute_df

# -----------------------------
# Comparativo
# -----------------------------
def build_comparativo(purchases_df: pd.DataFrame, onroute_df: pd.DataFrame) -> pd.DataFrame:
    if purchases_df.empty or onroute_df.empty:
        return pd.DataFrame()

    needed = {"Address", "Price", "h_lat", "h_lon", "FSID"}
    if not needed.issubset(onroute_df.columns):
        return pd.DataFrame()

    mask = (
        onroute_df["Address"].str.contains("Pilot", case=False, na=False)
        | onroute_df["Address"].str.contains("Flying J", case=False, na=False)
        | onroute_df["Address"].str.contains("FlyingJ", case=False, na=False)
    )
    stations_group = onroute_df[mask].copy()

    grouped = {
        fsid: grp.reset_index(drop=True)
        for fsid, grp in stations_group.groupby("FSID")
    }

    df = purchases_df.copy()
    df["is_pilot_group_purchase"] = df["location"].apply(is_pilot_group)
    df = df[~df["is_pilot_group_purchase"]].copy()

    if df.empty:
        return pd.DataFrame()

    def nearest_station(row):
        grp = grouped.get(row["FSID"])
        if grp is None or grp.empty or pd.isna(row["lat"]) or pd.isna(row["lng"]):
            return pd.Series({
                "nearest_pilotgroup_address": np.nan,
                "nearest_pilotgroup_price": np.nan,
                "distance_to_nearest_pilotgroup_miles": np.nan
            })

        dists = np.array([
            haversine_miles(row["lat"], row["lng"], la, lo)
            for la, lo in zip(grp["h_lat"], grp["h_lon"])
        ])
        i = int(dists.argmin())

        return pd.Series({
            "nearest_pilotgroup_address": grp.loc[i, "Address"],
            "nearest_pilotgroup_price": grp.loc[i, "Price"],
            "distance_to_nearest_pilotgroup_miles": float(dists[i])
        })

    nearest = df.apply(nearest_station, axis=1)
    comp = pd.concat([df.reset_index(drop=True), nearest], axis=1)
    comp["price_diff_per_gallon_vs_pilotgroup"] = comp["price"] - comp["nearest_pilotgroup_price"]
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

    base = pd.read_excel(
        uploaded,
        sheet_name="Fuel Solutions",
        usecols=["FSID", "FSJSON", "FSCreatedAt"]
    )

    base["FSCreatedAt"] = pd.to_datetime(base["FSCreatedAt"], errors="coerce")
    base = base.dropna(subset=["FSCreatedAt"])
    base["Year"] = base["FSCreatedAt"].dt.year
    base["Month"] = base["FSCreatedAt"].dt.month

    years = sorted(base["Year"].unique().tolist())
    year = st.selectbox("Año", years, index=len(years) - 1 if years else 0)

    months = sorted(base.loc[base["Year"] == year, "Month"].unique().tolist())
    month = st.selectbox("Mes", months, index=len(months) - 1 if months else 0)

    filtered = base[(base["Year"] == year) & (base["Month"] == month)]
    st.caption(f"Registros filtrados: {len(filtered):,} (Año={year}, Mes={month})")

    trips_df, purchases_df, onroute_df = build_tables(filtered)

    if not purchases_df.empty:
        purchases_df["is_pilot_group_purchase"] = purchases_df["location"].apply(is_pilot_group)
        total = len(purchases_df)
        group_count = int(purchases_df["is_pilot_group_purchase"].sum())
        other_count = total - group_count

        c1, c2, c3 = st.columns(3)
        c1.metric("Cargas (total)", f"{total:,}")
        c2.metric("Cargas Pilot/Flying J", f"{group_count / total * 100:.1f}%")
        c3.metric("Cargas en otras", f"{other_count / total * 100:.1f}%")

    comparativo_df = build_comparativo(purchases_df, onroute_df)

    st.subheader("Tabla 1: Trip")
    st.dataframe(trips_df, use_container_width=True)

    st.subheader("Tabla 2: Fuel Purchases")
    st.dataframe(purchases_df, use_container_width=True)

    st.subheader("Tabla 3: Stations On Route")
    st.dataframe(onroute_df, use_container_width=True)

    st.subheader("Tabla 4: Comparativo Non-Pilot")
    if comparativo_df.empty:
        st.info("No se generó comparativo.")
    else:
        st.dataframe(comparativo_df, use_container_width=True)

    excel_bytes = to_excel_bytes(
        trips_df,
        purchases_df,
        onroute_df,
        comparativo_df
    )

    st.download_button(
        "⬇️ Descargar Excel (4 hojas)",
        data=excel_bytes,
        file_name=f"fuel_solutions_{year}_{month:02d}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

else:
    st.info("Sube el Excel para comenzar.")