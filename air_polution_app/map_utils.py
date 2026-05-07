"""
map_utils.py
Folium map building helpers — India Air Pollution Dashboard
"""

import folium
import pandas as pd
from folium.plugins import MarkerCluster, HeatMap
from data_processing import classify_aqi


POLLUTANT_LABEL = {"pm25": "PM2.5", "no2": "NO₂"}
UNIT = "µg/m³"


def _circle_color(value: float, parameter: str) -> str:
    return classify_aqi(value, parameter)["color"]


def _aqi_badge(category: str, color: str) -> str:
    return (
        f'<span style="background:{color};color:#fff;padding:2px 8px;'
        f'border-radius:4px;font-weight:bold;font-size:11px;">{category}</span>'
    )


def build_bubble_map(
    city_data: pd.DataFrame,
    parameter: str = "pm25",
) -> folium.Map:
    """
    Proportional circle map — circle radius ∝ pollutant value.
    Each marker has a rich popup with both PM2.5 and NO2 readings.
    """
    m = folium.Map(
        location=[22.5, 80.0],
        zoom_start=5,
        tiles="CartoDB dark_matter",
    )

    col = parameter
    if col not in city_data.columns:
        return m

    label = POLLUTANT_LABEL[parameter]

    for _, row in city_data.iterrows():
        val = row.get(col)
        if pd.isnull(val):
            continue

        info    = classify_aqi(val, parameter)
        pm25_v  = row.get("pm25", "N/A")
        no2_v   = row.get("no2",  "N/A")
        pm25_i  = classify_aqi(pm25_v, "pm25") if pd.notnull(pm25_v) else {"category": "N/A", "color": "#999"}
        no2_i   = classify_aqi(no2_v,  "no2")  if pd.notnull(no2_v)  else {"category": "N/A", "color": "#999"}

        popup_html = f"""
        <div style="font-family:'Segoe UI',sans-serif;min-width:220px;padding:4px;">
          <h4 style="margin:0 0 6px;font-size:15px;color:#222;">{row['city']}</h4>
          <div style="color:#555;font-size:12px;margin-bottom:8px;">📍 {row.get('state','')}</div>
          <table style="width:100%;border-collapse:collapse;font-size:12px;">
            <tr style="background:#f5f5f5;">
              <th style="padding:4px 8px;text-align:left;">Pollutant</th>
              <th style="padding:4px 8px;text-align:right;">Value</th>
              <th style="padding:4px 8px;text-align:right;">AQI</th>
            </tr>
            <tr>
              <td style="padding:4px 8px;">PM2.5</td>
              <td style="padding:4px 8px;text-align:right;font-weight:bold;">{pm25_v if isinstance(pm25_v,str) else f"{pm25_v:.1f}"} {UNIT}</td>
              <td style="padding:4px 8px;text-align:right;">{_aqi_badge(pm25_i['category'], pm25_i['color'])}</td>
            </tr>
            <tr style="background:#f9f9f9;">
              <td style="padding:4px 8px;">NO₂</td>
              <td style="padding:4px 8px;text-align:right;font-weight:bold;">{no2_v if isinstance(no2_v,str) else f"{no2_v:.1f}"} {UNIT}</td>
              <td style="padding:4px 8px;text-align:right;">{_aqi_badge(no2_i['category'], no2_i['color'])}</td>
            </tr>
          </table>
          <div style="margin-top:8px;padding:6px;background:{info['color']}20;border-left:3px solid {info['color']};font-size:11px;color:#333;">
            {info['description']}
          </div>
        </div>
        """

        radius = max(6, min(35, val / 5))

        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=radius,
            color=info["color"],
            fill=True,
            fill_color=info["color"],
            fill_opacity=0.65,
            weight=1.5,
            popup=folium.Popup(popup_html, max_width=280),
            tooltip=f"{row['city']}: {val:.1f} {UNIT}",
        ).add_to(m)

    # Legend
    legend_html = _build_legend(parameter, label)
    m.get_root().html.add_child(folium.Element(legend_html))

    return m


def build_heatmap(city_data: pd.DataFrame, parameter: str = "pm25") -> folium.Map:
    """Kernel density heat map of pollution values."""
    m = folium.Map(
        location=[22.5, 80.0],
        zoom_start=5,
        tiles="CartoDB positron",
    )

    col = parameter
    heat_data = []
    for _, row in city_data.iterrows():
        val = row.get(col)
        if pd.notnull(val):
            heat_data.append([row["latitude"], row["longitude"], float(val)])

    if heat_data:
        HeatMap(
            heat_data,
            min_opacity=0.35,
            radius=30,
            blur=20,
            gradient={
                "0.2": "#00c853",
                "0.4": "#ffd600",
                "0.6": "#ff6d00",
                "0.8": "#dd2c00",
                "1.0": "#6a0dad",
            },
        ).add_to(m)

    return m


def _build_legend(parameter: str, label: str) -> str:
    cats = [
        ("Good",        "#00c853"),
        ("Satisfactory","#69f000"),
        ("Moderate",    "#ffd600"),
        ("Poor",        "#ff6d00"),
        ("Very Poor",   "#dd2c00"),
        ("Severe",      "#6a0dad"),
    ]
    items = "".join(
        f'<div style="display:flex;align-items:center;gap:6px;margin:3px 0;">'
        f'<div style="width:14px;height:14px;border-radius:50%;background:{c};flex-shrink:0;"></div>'
        f'<span style="font-size:11px;">{cat}</span></div>'
        for cat, c in cats
    )
    return f"""
    <div style="
        position: fixed;
        bottom: 40px; right: 20px;
        z-index: 1000;
        background: rgba(255,255,255,0.95);
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 12px 16px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.15);
        font-family: 'Segoe UI', sans-serif;
    ">
        <div style="font-weight:700;font-size:12px;margin-bottom:8px;color:#333;">
            {label} — India NAQI
        </div>
        {items}
    </div>
    """
