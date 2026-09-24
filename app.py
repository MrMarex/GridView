import json
from pathlib import Path

import pandas as pd
import streamlit as st
import folium
from folium.plugins import Fullscreen
from branca.colormap import linear
from streamlit_folium import st_folium

st.set_page_config(
    page_title="Rīgas cilvēku plūsmas karte",
    page_icon="🗺️",
    layout="wide",
)

BASE_DIR = Path(__file__).resolve().parent
GEOJSON_FILE = BASE_DIR / "Riga_grid_1km.geojson"
CSV_FILE = BASE_DIR / "updated_load_static.csv"


@st.cache_data
def load_geojson():
    with open(GEOJSON_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def load_data():
    df = pd.read_csv(CSV_FILE)

    required = {
        "area_id",
        "date",
        "time_slice",
        "passers_by",
        "unique_passers_by",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV trūkst kolonnas: {', '.join(sorted(missing))}")

    df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")
    df["unique_passers_by"] = pd.to_numeric(
        df["unique_passers_by"], errors="coerce"
    ).fillna(0)
    df["passers_by"] = pd.to_numeric(
        df["passers_by"], errors="coerce"
    ).fillna(0)

    return df


def hour_start(time_slice):
    # Expected format: [02:00,03:00)
    try:
        return time_slice.split("[", 1)[1].split(":", 1)[0].zfill(2)
    except Exception:
        return ""


def hour_label(time_slice):
    try:
        value = time_slice.split("[", 1)[1].split(")", 1)[0]
        return value
    except Exception:
        return str(time_slice)


def make_popup(row, metric_label):
    return folium.Popup(
        f"""
        <div style="font-family: Arial; min-width: 190px;">
            <b>{row['area_id']}</b><br><br>
            <b>Datums:</b> {row['date'].strftime('%d.%m.%Y')}<br>
            <b>Laiks:</b> {hour_label(row['time_slice'])}<br>
            <b>{metric_label}:</b> {row['metric_value']:,.0f}<br>
            <b>Passers:</b> {row['passers_by']:,.0f}<br>
            <b>Unique passers:</b> {row['unique_passers_by']:,.0f}
        </div>
        """,
        max_width=320,
    )


def build_map(geo, selected, metric_col, metric_label, show_labels):
    # Merge selected data into GeoJSON properties
    values = selected.set_index("area_id").to_dict("index")

    features = []
    for feature in geo["features"]:
        grid_id = feature.get("properties", {}).get("grid_id")
        props = dict(feature.get("properties", {}))

        row = values.get(grid_id)
        if row is None:
            props["metric_value"] = 0
            props["passers_by"] = 0
            props["unique_passers_by"] = 0
            props["date"] = (
                selected["date"].iloc[0].strftime("%Y-%m-%d")
                if len(selected) else ""
            )
            props["time_slice"] = ""
        else:
            props["metric_value"] = float(row["metric_value"])
            props["passers_by"] = float(row["passers_by"])
            props["unique_passers_by"] = float(row["unique_passers_by"])
            props["date"] = (
                row["date"].strftime("%Y-%m-%d")
                if hasattr(row["date"], "strftime") else str(row["date"])
            )
            props["time_slice"] = str(row["time_slice"])

        new_feature = dict(feature)
        new_feature["properties"] = props
        features.append(new_feature)

    map_geo = {"type": "FeatureCollection", "features": features}

    max_value = max(
        [f["properties"]["metric_value"] for f in features] or [1]
    )
    if max_value <= 0:
        max_value = 1

    # Quantile-like visual scaling using fixed percentiles from displayed data.
    nonzero = selected.loc[selected["metric_value"] > 0, "metric_value"]
    if len(nonzero):
        scale_max = float(nonzero.quantile(0.95))
        scale_max = max(scale_max, float(nonzero.max()) * 0.5, 1)
    else:
        scale_max = max_value

    cmap = linear.YlOrRd_09.scale(0, scale_max)
    cmap.caption = metric_label

    m = folium.Map(
        location=[56.9496, 24.1052],
        zoom_start=10,
        tiles="CartoDB positron",
        control_scale=True,
    )
    Fullscreen(position="topright").add_to(m)

    def style_function(feature):
        value = float(feature["properties"].get("metric_value", 0))
        return {
            "fillColor": cmap(value),
            "color": "#555555",
            "weight": 0.7,
            "fillOpacity": 0.70 if value > 0 else 0.18,
        }

    def highlight_function(feature):
        return {
            "weight": 2.5,
            "color": "#111111",
            "fillOpacity": 0.85,
        }

    tooltip_fields = ["grid_id", "metric_value"]
    tooltip_aliases = ["Grid:", f"{metric_label}:"]

    tooltip = folium.GeoJsonTooltip(
        fields=tooltip_fields,
        aliases=tooltip_aliases,
        localize=True,
        sticky=False,
        labels=True,
        style=(
            "background-color: white; color: #222; "
            "font-family: Arial; font-size: 13px; padding: 8px;"
        ),
    )

    geo_layer = folium.GeoJson(
        map_geo,
        name="Rīgas režģis",
        style_function=style_function,
        highlight_function=highlight_function,
        tooltip=tooltip,
        smooth_factor=0.5,
    )
    geo_layer.add_to(m)

    # Optional numbers inside grid cells
    if show_labels:
        for feature in features:
            props = feature["properties"]
            value = props["metric_value"]
            if value <= 0:
                continue

            coords = feature["geometry"]["coordinates"][0]
            lon = sum(p[0] for p in coords[:-1]) / (len(coords) - 1)
            lat = sum(p[1] for p in coords[:-1]) / (len(coords) - 1)

            folium.Marker(
                [lat, lon],
                icon=folium.DivIcon(
                    html=f"""
                    <div style="
                        font-family: Arial;
                        font-size: 10px;
                        font-weight: 700;
                        color: #111;
                        text-align: center;
                        width: 60px;
                        margin-left: -30px;
                        margin-top: -7px;
                        text-shadow: 0 0 2px white, 0 0 2px white;
                    ">
                        {value:,.0f}
                    </div>
                    """
                ),
            ).add_to(m)

    cmap.add_to(m)
    return m


st.title("Rīgas cilvēku plūsmas karte")
st.caption("Interaktīva 1 km režģa analīze pēc atrašanās vietas datiem")

try:
    geo = load_geojson()
    df = load_data()
except Exception as e:
    st.error(f"Neizdevās ielādēt datus: {e}")
    st.stop()

# Sidebar
with st.sidebar:
    st.header("Filtri")

    dates = sorted(df["date"].dropna().dt.date.unique())
    if not dates:
        st.error("CSV failā nav derīgu datumu.")
        st.stop()

    selected_date = st.selectbox(
        "Datums",
        dates,
        format_func=lambda x: x.strftime("%d.%m.%Y"),
    )

    day_df = df[df["date"].dt.date == selected_date].copy()

    time_slices = list(
        day_df[["time_slice"]]
        .drop_duplicates()
        ["time_slice"]
    )

    # Sort by hour where possible
    time_slices = sorted(
        time_slices,
        key=lambda x: int(hour_start(x)) if hour_start(x).isdigit() else 99,
    )

    if not time_slices:
        st.warning("Izvēlētajam datumam nav laika datu.")
        st.stop()

    time_options = [hour_label(x) for x in time_slices]

    selected_time_label = st.select_slider(
        "Stunda",
        options=time_options,
        value=time_options[0],
    )

    selected_time_slice = time_slices[time_options.index(selected_time_label)]

    metric = st.radio(
        "Rādīt kartē",
        options=["unique_passers_by", "passers_by"],
        format_func=lambda x: (
            "Unique passers" if x == "unique_passers_by" else "Passers"
        ),
    )

    show_labels = st.checkbox(
        "Rādīt skaitļus kvadrantos",
        value=True,
    )

    st.divider()

# Filter selected hour
selected = day_df[day_df["time_slice"] == selected_time_slice].copy()

# One row per area_id. If duplicates exist, aggregate them.
selected = (
    selected.groupby("area_id", as_index=False)
    .agg(
        date=("date", "first"),
        time_slice=("time_slice", "first"),
        passers_by=("passers_by", "sum"),
        unique_passers_by=("unique_passers_by", "sum"),
    )
)

selected["metric_value"] = selected[metric]

metric_label = "Unique passers" if metric == "unique_passers_by" else "Passers"

# KPI row
total = selected["metric_value"].sum()
maximum = selected["metric_value"].max() if len(selected) else 0
active_cells = int((selected["metric_value"] > 0).sum())

c1, c2, c3, c4 = st.columns(4)
c1.metric("Kopā", f"{total:,.0f}")
c2.metric("Maks. kvadrantā", f"{maximum:,.0f}")
c3.metric("Aktīvi kvadranti", f"{active_cells:,}")
c4.metric("Laiks", selected_time_label)

# Map
m = build_map(
    geo,
    selected,
    metric,
    metric_label,
    show_labels,
)

st_folium(
    m,
    width=None,
    height=700,
    returned_objects=[],
)

st.caption(
    "Krāsa tiek pielāgota izvēlētā laika perioda datu diapazonam. "
    "Uzvedot peli uz kvadranta, redzama tā vērtība; uzklikšķinot, "
    "pieejama detalizētāka informācija."
)

with st.expander("Par datiem"):
    st.write(
        f"GeoJSON kvadranti: **{len(geo.get('features', []))}**"
    )
    st.write(f"CSV ieraksti: **{len(df):,}**")
    st.write(f"Pieejamie datumi: **{len(dates)}**")
    st.write(f"Pieejamie laika intervāli izvēlētajā dienā: **{len(time_slices)}**")
