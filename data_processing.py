"""
data_processing.py
Air Quality Data Processing Pipeline — India Air Pollution Dashboard
"""

import pandas as pd
import numpy as np


# ──────────────────────────────────────────────
# AQI CLASSIFICATION (India NAQI standard)
# ──────────────────────────────────────────────

AQI_CATEGORIES_PM25 = [
    (0,   30,   "Good",           "#00c853", "😊 Air quality is satisfactory."),
    (30,  60,   "Satisfactory",   "#69f000", "🙂 Minor discomfort for sensitive people."),
    (60,  90,   "Moderate",       "#ffd600", "😐 May cause breathing discomfort."),
    (90,  120,  "Poor",           "#ff6d00", "😷 Breathing discomfort on prolonged exposure."),
    (120, 250,  "Very Poor",      "#dd2c00", "🤧 Respiratory illness on prolonged exposure."),
    (250, 9999, "Severe",         "#6a0dad", "☠️ Affects healthy people; serious risk."),
]

AQI_CATEGORIES_NO2 = [
    (0,   40,   "Good",           "#00c853", "😊 Air quality is satisfactory."),
    (40,  80,   "Satisfactory",   "#69f000", "🙂 Minor discomfort for sensitive people."),
    (80,  180,  "Moderate",       "#ffd600", "😐 May cause breathing discomfort."),
    (180, 280,  "Poor",           "#ff6d00", "😷 Breathing discomfort on prolonged exposure."),
    (280, 400,  "Very Poor",      "#dd2c00", "🤧 Respiratory illness on prolonged exposure."),
    (400, 9999, "Severe",         "#6a0dad", "☠️ Affects healthy people; serious risk."),
]


def classify_aqi(value: float, parameter: str) -> dict:
    """Return AQI category dict for a given pollutant value."""
    table = AQI_CATEGORIES_PM25 if parameter == "pm25" else AQI_CATEGORIES_NO2
    for lo, hi, cat, color, desc in table:
        if lo <= value < hi:
            return {"category": cat, "color": color, "description": desc}
    return {"category": "Unknown", "color": "#999", "description": "No data"}


# ──────────────────────────────────────────────
# DATA LOADING & CLEANING
# ──────────────────────────────────────────────

def load_and_clean_data(path: str = "data/air_quality.csv") -> pd.DataFrame:
    """Load CSV, filter relevant pollutants, clean types."""
    df = pd.read_csv(path)

    # Keep only our two pollutants
    df = df[df["parameter"].isin(["pm25", "no2"])].copy()

    # Drop rows missing spatial info
    df = df.dropna(subset=["latitude", "longitude", "value"])

    # Remove physically impossible values
    df = df[(df["value"] >= 0) & (df["value"] < 2000)]

    # Parse dates
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])

    # Derived columns
    df["month"] = df["date"].dt.month
    df["month_name"] = df["date"].dt.strftime("%b %Y")
    df["year"] = df["date"].dt.year

    return df.reset_index(drop=True)


def aggregate_city_level(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate per city → mean PM2.5, NO2, + AQI category columns.
    Returns one row per city with lat/lon (centroid), state, and pollutant means.
    """
    agg = (
        df.groupby(["city", "state", "parameter"])
        .agg(
            value=("value", "mean"),
            latitude=("latitude", "mean"),
            longitude=("longitude", "mean"),
            count=("value", "count"),
        )
        .reset_index()
    )

    pivot = agg.pivot_table(
        index=["city", "state", "latitude", "longitude"],
        columns="parameter",
        values=["value", "count"],
    ).reset_index()

    # Flatten multi-level columns
    pivot.columns = ["_".join(c).strip("_") for c in pivot.columns]

    # Rename for clarity
    rename = {
        "city": "city",
        "state": "state",
        "latitude": "latitude",
        "longitude": "longitude",
        "value_pm25": "pm25",
        "value_no2": "no2",
        "count_pm25": "pm25_count",
        "count_no2": "no2_count",
    }
    pivot = pivot.rename(columns=rename)

    # Round pollutant values
    for col in ["pm25", "no2"]:
        if col in pivot.columns:
            pivot[col] = pivot[col].round(1)

    # AQI category for each pollutant
    for param in ["pm25", "no2"]:
        if param in pivot.columns:
            pivot[f"{param}_category"] = pivot[param].apply(
                lambda v: classify_aqi(v, param)["category"] if pd.notnull(v) else "No Data"
            )
            pivot[f"{param}_color"] = pivot[param].apply(
                lambda v: classify_aqi(v, param)["color"] if pd.notnull(v) else "#999"
            )

    return pivot


def get_monthly_trend(df: pd.DataFrame, city: str, parameter: str) -> pd.DataFrame:
    """Return monthly average for a specific city + pollutant."""
    subset = df[(df["city"] == city) & (df["parameter"] == parameter)]
    trend = (
        subset.groupby(["year", "month"])["value"]
        .mean()
        .reset_index()
        .sort_values(["year", "month"])
    )
    trend["label"] = trend.apply(
        lambda r: pd.Timestamp(year=int(r["year"]), month=int(r["month"]), day=1).strftime("%b %Y"),
        axis=1,
    )
    trend["value"] = trend["value"].round(1)
    return trend


def get_national_stats(city_data: pd.DataFrame, parameter: str) -> dict:
    """Return national summary statistics for a given pollutant."""
    col = parameter
    if col not in city_data.columns:
        return {}
    vals = city_data[col].dropna()
    if vals.empty:
        return {}
    worst = city_data.loc[city_data[col].idxmax()]
    best  = city_data.loc[city_data[col].idxmin()]
    return {
        "mean":    round(float(vals.mean()), 1),
        "median":  round(float(vals.median()), 1),
        "max":     round(float(vals.max()), 1),
        "min":     round(float(vals.min()), 1),
        "std":     round(float(vals.std()), 1),
        "worst_city": worst["city"],
        "best_city":  best["city"],
        "n_cities":   int(vals.count()),
    }


def get_state_summary(city_data: pd.DataFrame) -> pd.DataFrame:
    """Aggregate city-level data up to state level."""
    cols = [c for c in ["pm25", "no2"] if c in city_data.columns]
    return (
        city_data.groupby("state")[cols]
        .mean()
        .round(1)
        .reset_index()
        .sort_values("pm25" if "pm25" in cols else cols[0], ascending=False)
    )
