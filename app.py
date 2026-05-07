"""
app.py — India Air Pollution Dashboard
Streamlit + GeoPython  |  Production-ready
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit.components.v1 import html as st_html

# ── Must be first Streamlit call ──────────────────────────────────────────────
st.set_page_config(
    page_title="India Air Quality Dashboard",
    page_icon="🌫️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://github.com",
        "About": "India Air Pollution Dashboard — Built with Streamlit & GeoPython",
    },
)

# ── Imports that depend on project modules ────────────────────────────────────
from data_processing import (
    load_and_clean_data,
    aggregate_city_level,
    get_monthly_trend,
    get_national_stats,
    get_state_summary,
    AQI_CATEGORIES_PM25,
    AQI_CATEGORIES_NO2,
    classify_aqi,
)
from map_utils import build_bubble_map, build_heatmap


# ─────────────────────────────────────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* ── Google Fonts ── */
  @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&family=DM+Sans:wght@300;400;500&display=swap');

  html, body, [class*="css"] {
      font-family: 'DM Sans', sans-serif;
  }

  /* ── Sidebar ── */
  section[data-testid="stSidebar"] {
      background: linear-gradient(160deg, #0d1117 0%, #161b22 100%);
      border-right: 1px solid #21262d;
  }
  section[data-testid="stSidebar"] * {
      color: #e6edf3 !important;
  }
  section[data-testid="stSidebar"] .stSelectbox label,
  section[data-testid="stSidebar"] .stSlider label,
  section[data-testid="stSidebar"] .stMultiSelect label {
      font-weight: 500;
      font-size: 13px;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      color: #8b949e !important;
  }

  /* ── Metric cards ── */
  div[data-testid="metric-container"] {
      background: #0d1117;
      border: 1px solid #21262d;
      border-radius: 12px;
      padding: 16px 20px;
  }
  div[data-testid="metric-container"] label {
      color: #8b949e !important;
      font-size: 12px !important;
      font-weight: 500;
      text-transform: uppercase;
      letter-spacing: 0.06em;
  }
  div[data-testid="metric-container"] [data-testid="stMetricValue"] {
      color: #e6edf3 !important;
      font-size: 28px !important;
      font-family: 'Syne', sans-serif;
      font-weight: 700;
  }

  /* ── Headers ── */
  h1, h2, h3 {
      font-family: 'Syne', sans-serif !important;
  }

  /* ── Tabs ── */
  .stTabs [data-baseweb="tab-list"] {
      gap: 4px;
      border-bottom: 1px solid #21262d;
  }
  .stTabs [data-baseweb="tab"] {
      background: transparent;
      border-radius: 6px 6px 0 0;
      padding: 8px 20px;
      font-size: 13px;
      font-weight: 500;
      color: #8b949e;
  }
  .stTabs [aria-selected="true"] {
      background: #161b22 !important;
      color: #58a6ff !important;
      border-bottom: 2px solid #58a6ff !important;
  }

  /* ── Dividers ── */
  hr { border-color: #21262d; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# DATA LOADING  (cached)
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(show_spinner="Loading air quality data…")
def load_data():
    df        = load_and_clean_data("data/air_quality.csv")
    city_data = aggregate_city_level(df)
    return df, city_data


df_raw, city_data = load_data()


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div style="padding:12px 0 24px;">
      <div style="font-family:'Syne',sans-serif;font-size:22px;font-weight:800;
                  color:#e6edf3;line-height:1.2;">
        🌫️ India<br>Air Quality
      </div>
      <div style="font-size:11px;color:#8b949e;margin-top:4px;">
        POLLUTION MONITOR — v1.0
      </div>
    </div>
    <hr style="border-color:#21262d;margin-bottom:20px;">
    """, unsafe_allow_html=True)

    # Pollutant selector
    pollutant = st.selectbox(
        "Pollutant",
        options=["pm25", "no2"],
        format_func=lambda x: "PM2.5 — Particulate Matter" if x == "pm25" else "NO₂ — Nitrogen Dioxide",
    )

    # Map type
    map_type = st.radio(
        "Map Style",
        options=["Bubble Map", "Heat Map"],
        horizontal=True,
    )

    st.markdown("<hr style='border-color:#21262d;'>", unsafe_allow_html=True)

    # Date filter
    min_date = df_raw["date"].min().date()
    max_date = df_raw["date"].max().date()

    date_range = st.date_input(
        "Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    st.markdown("<hr style='border-color:#21262d;'>", unsafe_allow_html=True)

    # State filter
    all_states = sorted(df_raw["state"].dropna().unique())
    selected_states = st.multiselect(
        "Filter by State",
        options=all_states,
        default=[],
        placeholder="All states",
    )

    st.markdown("<hr style='border-color:#21262d;'>", unsafe_allow_html=True)

    # City selector for trend
    all_cities = sorted(city_data["city"].unique())
    selected_city = st.selectbox("City Trend Analysis", options=all_cities)

    st.markdown("""
    <div style="margin-top:24px;padding:12px;background:#161b22;border-radius:8px;
                border:1px solid #21262d;font-size:11px;color:#8b949e;line-height:1.6;">
      <strong style="color:#58a6ff;">Data Sources</strong><br>
      OpenAQ · CPCB<br>
      India NAQI Standards<br><br>
      <strong style="color:#58a6ff;">Built With</strong><br>
      Streamlit · GeoPandas<br>
      Folium · Plotly
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# FILTER DATA BY DATE & STATE
# ─────────────────────────────────────────────────────────────────────────────

try:
    d0, d1 = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
except Exception:
    d0, d1 = df_raw["date"].min(), df_raw["date"].max()

df_filtered = df_raw[(df_raw["date"] >= d0) & (df_raw["date"] <= d1)]

if selected_states:
    df_filtered = df_filtered[df_filtered["state"].isin(selected_states)]
    city_data_f = aggregate_city_level(df_filtered)
else:
    city_data_f = city_data.copy()


# ─────────────────────────────────────────────────────────────────────────────
# PAGE HEADER
# ─────────────────────────────────────────────────────────────────────────────

pol_label = "PM2.5" if pollutant == "pm25" else "NO₂"
pol_unit  = "µg/m³"

st.markdown(f"""
<div style="display:flex;align-items:flex-end;justify-content:space-between;
            padding:8px 0 20px;border-bottom:1px solid #21262d;margin-bottom:24px;">
  <div>
    <h1 style="margin:0;font-size:32px;color:#e6edf3;">
      India Air Quality Monitor
    </h1>
    <p style="margin:4px 0 0;color:#8b949e;font-size:14px;">
      Real-time pollution tracking · {pol_label} · {d0.strftime('%d %b %Y')} – {d1.strftime('%d %b %Y')}
    </p>
  </div>
  <div style="font-size:11px;color:#8b949e;text-align:right;">
    {city_data_f['city'].nunique()} cities monitored<br>
    {len(df_filtered):,} data points
  </div>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# KPI CARDS
# ─────────────────────────────────────────────────────────────────────────────

stats = get_national_stats(city_data_f, pollutant)

if stats:
    k1, k2, k3, k4, k5 = st.columns(5)

    with k1:
        val = stats["mean"]
        info = classify_aqi(val, pollutant)
        st.metric("🇮🇳 National Avg", f"{val} {pol_unit}")
    with k2:
        st.metric("📈 Median", f"{stats['median']} {pol_unit}")
    with k3:
        worst_val = stats["max"]
        info_w = classify_aqi(worst_val, pollutant)
        st.metric(
            f"⚠️ Most Polluted",
            f"{stats['worst_city']}",
            delta=f"{worst_val} {pol_unit}",
            delta_color="inverse",
        )
    with k4:
        best_val = stats["min"]
        st.metric(
            f"✅ Cleanest",
            f"{stats['best_city']}",
            delta=f"{best_val} {pol_unit}",
        )
    with k5:
        st.metric("🏙️ Cities Monitored", stats["n_cities"])

st.markdown("<br>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────────────────

tab_map, tab_trend, tab_ranking, tab_table, tab_about = st.tabs([
    "🗺️ Pollution Map",
    "📈 City Trends",
    "🏆 City Rankings",
    "📋 Data Table",
    "ℹ️ About & Guide",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — MAP
# ══════════════════════════════════════════════════════════════════════════════

with tab_map:
    col_map, col_info = st.columns([3, 1])

    with col_map:
        with st.spinner("Building map…"):
            if map_type == "Bubble Map":
                fmap = build_bubble_map(city_data_f, parameter=pollutant)
            else:
                fmap = build_heatmap(city_data_f, parameter=pollutant)

        st_html(fmap._repr_html_(), height=540)

    with col_info:
        st.markdown(f"#### {pol_label} — AQI Scale")
        cats = AQI_CATEGORIES_PM25 if pollutant == "pm25" else AQI_CATEGORIES_NO2

        for lo, hi, cat, color, desc in cats:
            hi_str = "+" if hi == 9999 else str(hi)
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:10px;padding:7px 10px;
                        margin:4px 0;border-radius:8px;background:{color}18;
                        border-left:3px solid {color};">
              <div style="width:10px;height:10px;border-radius:50%;
                          background:{color};flex-shrink:0;"></div>
              <div>
                <div style="font-weight:600;font-size:13px;color:#e6edf3;">{cat}</div>
                <div style="font-size:11px;color:#8b949e;">{lo}–{hi_str} {pol_unit}</div>
              </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
        <div style="padding:12px;background:#161b22;border-radius:8px;
                    border:1px solid #21262d;font-size:12px;color:#8b949e;">
          <b style="color:#e6edf3;">💡 How to use</b><br><br>
          • Click circles for detailed readings<br>
          • Bubble size = pollution level<br>
          • Hover for quick tooltip<br>
          • Use sidebar to filter by state / date
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — CITY TREND
# ══════════════════════════════════════════════════════════════════════════════

with tab_trend:
    c1, c2 = st.columns([1, 1])

    with c1:
        trend_pm25 = get_monthly_trend(df_filtered, selected_city, "pm25")
        if not trend_pm25.empty:
            fig = px.area(
                trend_pm25, x="label", y="value",
                title=f"{selected_city} — PM2.5 Monthly Trend",
                labels={"value": "PM2.5 (µg/m³)", "label": "Month"},
                color_discrete_sequence=["#f97316"],
            )
            fig.update_layout(
                paper_bgcolor="#0d1117", plot_bgcolor="#0d1117",
                font_color="#e6edf3",
                title_font_family="Syne",
                xaxis=dict(showgrid=False, tickangle=45),
                yaxis=dict(showgrid=True, gridcolor="#21262d"),
                margin=dict(l=10, r=10, t=40, b=10),
            )
            # WHO guideline line
            fig.add_hline(
                y=15, line_dash="dot", line_color="#58a6ff",
                annotation_text="WHO Guideline (15 µg/m³)",
                annotation_font_color="#58a6ff",
                annotation_font_size=11,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No PM2.5 data for selected filters.")

    with c2:
        trend_no2 = get_monthly_trend(df_filtered, selected_city, "no2")
        if not trend_no2.empty:
            fig2 = px.area(
                trend_no2, x="label", y="value",
                title=f"{selected_city} — NO₂ Monthly Trend",
                labels={"value": "NO₂ (µg/m³)", "label": "Month"},
                color_discrete_sequence=["#a78bfa"],
            )
            fig2.update_layout(
                paper_bgcolor="#0d1117", plot_bgcolor="#0d1117",
                font_color="#e6edf3",
                title_font_family="Syne",
                xaxis=dict(showgrid=False, tickangle=45),
                yaxis=dict(showgrid=True, gridcolor="#21262d"),
                margin=dict(l=10, r=10, t=40, b=10),
            )
            fig2.add_hline(
                y=10, line_dash="dot", line_color="#58a6ff",
                annotation_text="WHO Guideline (10 µg/m³)",
                annotation_font_color="#58a6ff",
                annotation_font_size=11,
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No NO₂ data for selected filters.")

    # Seasonal pattern (all cities)
    st.markdown("---")
    st.markdown("#### Seasonal Pattern (All Cities)")

    seasonal = (
        df_filtered[df_filtered["parameter"] == pollutant]
        .groupby("month")["value"]
        .agg(["mean", "std"])
        .reset_index()
    )
    month_names = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
                   7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}
    seasonal["month_name"] = seasonal["month"].map(month_names)

    if not seasonal.empty:
        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(
            x=seasonal["month_name"], y=seasonal["mean"],
            mode="lines+markers",
            name="Monthly Avg",
            line=dict(color="#f97316", width=2.5),
            marker=dict(size=8),
        ))
        fig3.add_trace(go.Scatter(
            x=pd.concat([seasonal["month_name"], seasonal["month_name"][::-1]]),
            y=pd.concat([seasonal["mean"] + seasonal["std"],
                         (seasonal["mean"] - seasonal["std"])[::-1]]),
            fill="toself",
            fillcolor="rgba(249,115,22,0.12)",
            line=dict(color="rgba(255,255,255,0)"),
            name="±1 Std Dev",
        ))
        fig3.update_layout(
            paper_bgcolor="#0d1117", plot_bgcolor="#0d1117",
            font_color="#e6edf3",
            title=f"National {pol_label} Seasonal Pattern",
            title_font_family="Syne",
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor="#21262d",
                       title=f"{pol_label} (µg/m³)"),
            legend=dict(bgcolor="#161b22", bordercolor="#21262d"),
            margin=dict(l=10, r=10, t=50, b=10),
            height=300,
        )
        st.plotly_chart(fig3, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — RANKINGS
# ══════════════════════════════════════════════════════════════════════════════

with tab_ranking:
    r1, r2 = st.columns(2)

    with r1:
        st.markdown("#### 🔴 Most Polluted Cities")
        if pollutant in city_data_f.columns:
            top_worst = city_data_f.nlargest(15, pollutant)[
                ["city", "state", pollutant, f"{pollutant}_category"]
            ].reset_index(drop=True)
            top_worst.index += 1

            fig_bar = px.bar(
                top_worst,
                x=pollutant, y="city",
                orientation="h",
                color=pollutant,
                color_continuous_scale=["#00c853","#ffd600","#ff6d00","#dd2c00","#6a0dad"],
                labels={pollutant: f"{pol_label} (µg/m³)", "city": ""},
                text=pollutant,
                hover_data=["state", f"{pollutant}_category"],
            )
            fig_bar.update_traces(texttemplate="%{text:.1f}", textposition="outside")
            fig_bar.update_layout(
                paper_bgcolor="#0d1117", plot_bgcolor="#0d1117",
                font_color="#e6edf3",
                coloraxis_showscale=False,
                yaxis=dict(autorange="reversed"),
                margin=dict(l=10, r=60, t=10, b=10),
                height=420,
            )
            st.plotly_chart(fig_bar, use_container_width=True)

    with r2:
        st.markdown("#### 🟢 Cleanest Cities")
        if pollutant in city_data_f.columns:
            top_best = city_data_f.dropna(subset=[pollutant]).nsmallest(15, pollutant)[
                ["city", "state", pollutant, f"{pollutant}_category"]
            ].reset_index(drop=True)
            top_best.index += 1

            fig_bar2 = px.bar(
                top_best,
                x=pollutant, y="city",
                orientation="h",
                color=pollutant,
                color_continuous_scale=["#00c853","#69f000","#ffd600"],
                labels={pollutant: f"{pol_label} (µg/m³)", "city": ""},
                text=pollutant,
                hover_data=["state", f"{pollutant}_category"],
            )
            fig_bar2.update_traces(texttemplate="%{text:.1f}", textposition="outside")
            fig_bar2.update_layout(
                paper_bgcolor="#0d1117", plot_bgcolor="#0d1117",
                font_color="#e6edf3",
                coloraxis_showscale=False,
                yaxis=dict(autorange="reversed"),
                margin=dict(l=10, r=60, t=10, b=10),
                height=420,
            )
            st.plotly_chart(fig_bar2, use_container_width=True)

    # State-level bar
    st.markdown("---")
    st.markdown("#### State-Level Comparison")
    state_df = get_state_summary(city_data_f)

    cols_avail = [c for c in ["pm25", "no2"] if c in state_df.columns]
    if cols_avail:
        fig_state = px.bar(
            state_df,
            x="state", y=cols_avail,
            barmode="group",
            color_discrete_sequence=["#f97316", "#a78bfa"],
            labels={"value": "µg/m³", "state": "State", "variable": "Pollutant"},
        )
        fig_state.update_layout(
            paper_bgcolor="#0d1117", plot_bgcolor="#0d1117",
            font_color="#e6edf3",
            xaxis=dict(showgrid=False, tickangle=45),
            yaxis=dict(showgrid=True, gridcolor="#21262d"),
            legend=dict(bgcolor="#161b22", bordercolor="#21262d"),
            margin=dict(l=10, r=10, t=20, b=80),
            height=380,
        )
        st.plotly_chart(fig_state, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — DATA TABLE
# ══════════════════════════════════════════════════════════════════════════════

with tab_table:
    st.markdown("#### City-Level Aggregated Data")

    disp_cols = ["city", "state", "latitude", "longitude"]
    for p in ["pm25", "no2"]:
        for suffix in ["", "_category"]:
            col = f"{p}{suffix}"
            if col in city_data_f.columns:
                disp_cols.append(col)

    disp = city_data_f[disp_cols].copy()
    disp.columns = [c.upper().replace("_", " ") for c in disp.columns]

    st.dataframe(
        disp.sort_values("PM25" if "PM25" in disp.columns else disp.columns[0],
                         ascending=False),
        use_container_width=True,
        height=450,
    )

    # Download
    csv_bytes = city_data_f.to_csv(index=False).encode()
    st.download_button(
        label="⬇️ Download as CSV",
        data=csv_bytes,
        file_name="india_air_quality_aggregated.csv",
        mime="text/csv",
    )

    st.markdown("---")
    st.markdown("#### Raw Data Sample (first 500 rows)")
    st.dataframe(
        df_filtered.head(500),
        use_container_width=True,
        height=300,
    )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — ABOUT
# ══════════════════════════════════════════════════════════════════════════════

with tab_about:
    c1, c2 = st.columns([3, 2])

    with c1:
        st.markdown("""
## 🌍 About This Dashboard

This dashboard visualises **ambient air quality** across Indian cities,
tracking two critical pollutants:

| Pollutant | Full Name | Health Significance |
|-----------|-----------|---------------------|
| **PM2.5** | Fine Particulate Matter (≤2.5 µm) | Penetrates deep into lungs; most harmful |
| **NO₂**   | Nitrogen Dioxide | Traffic & industrial combustion; respiratory irritant |

---

### 📊 Data Sources

| Source | Details |
|--------|---------|
| **OpenAQ** | Global open air quality data platform — [openaq.org](https://openaq.org) |
| **CPCB** | Central Pollution Control Board — [app.cpcbccr.com](https://app.cpcbccr.com) |

---

### 🏥 India NAQI Standards (PM2.5)

| Category | PM2.5 Range | Health Advisory |
|----------|-------------|-----------------|
| Good | 0–30 µg/m³ | Minimal impact |
| Satisfactory | 30–60 µg/m³ | Minor discomfort for sensitive |
| Moderate | 60–90 µg/m³ | Breathing discomfort possible |
| Poor | 90–120 µg/m³ | Avoid prolonged outdoor activity |
| Very Poor | 120–250 µg/m³ | Respiratory illness risk |
| Severe | >250 µg/m³ | Health emergency |

---

### 🔧 Tech Stack

```
streamlit     — web app framework
folium        — interactive Leaflet maps
geopandas     — spatial data processing
plotly        — interactive charts
pandas        — data wrangling
shapely       — geometry operations
```

---

### 🚀 How to Run Locally

```bash
git clone <your-repo>
cd air_pollution_app
pip install -r requirements.txt
streamlit run app.py
```
        """)

    with c2:
        st.markdown("""
### 📋 How to Use

**1. Select Pollutant**
Use the sidebar to switch between PM2.5 and NO₂.

**2. Filter by Date**
Narrow to a specific time period using the date picker.

**3. Filter by State**
Focus on specific states using the multi-select.

**4. Explore the Map**
- Click city markers for detailed readings
- Bubble size indicates pollution intensity
- Switch to Heat Map for density view

**5. Analyse Trends**
Select a city in the sidebar to see its monthly pollution trend in the City Trends tab.

**6. Download Data**
Go to Data Table → Download as CSV.

---

### ⚠️ Disclaimer

This dashboard is built for **educational and portfolio** purposes. The sample data included is **synthetic** but statistically representative. For official air quality data, refer to CPCB directly.

---

### 👨‍💻 Portfolio Note

This project demonstrates:
- **Data Engineering** (ETL pipeline, cleaning)
- **GIS / Spatial Analysis** (GeoPandas, Folium)
- **Python Automation** (modular, reusable code)
- **Web GIS Deployment** (Streamlit Cloud)

Relevant for: *Applied Geoinformatics (TU Wien), Urban Analytics, Environmental Data Science*
        """)
