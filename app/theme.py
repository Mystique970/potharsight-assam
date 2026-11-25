"""Shared look-and-feel, grades and plain-language helpers for the PotharSight portal."""
import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
import streamlit as st

from d13.core import load_config
from d13.model import FACTORS

ROOT = Path(__file__).resolve().parents[1]
cfg = load_config()
OUT = ROOT / cfg["project"]["output_dir"]
DISTRICTS = [d for d in cfg["districts"] if (OUT / d / "field_crops" / "tables" / "validation.json").exists()]
PILOT = ["kamrup", "cachar"]
DNAME = {d: cfg["districts"][d]["boundary_name"] + (" (Rural)" if d == "kamrup" else "") for d in cfg["districts"]}
DESC = {"kamrup": "Brahmaputra valley · char lands · Meghalaya foothills",
        "cachar": "Barak valley · high rainfall · hills & tea gardens",
        "lakhimpur": "North bank · Subansiri floodplain",
        "dibrugarh": "Upper Assam · tea belt · Brahmaputra south bank"}

PURPOSE = {"field_crops": ("🌾", "Field crops", "Rice, mustard, pulses, maize and other seasonal crops"),
           "horticulture": ("🍊", "Fruits & vegetables", "Citrus, banana, pineapple, vegetables – needs land safer from floods")}
LAND_TYPE = {1: ("🟫", "Empty land", "Grassland, scrub or bare land that is not being farmed"),
             2: ("🌱", "Unused farmland", "Fields that have not been cropped in recent years"),
             3: ("❄️", "Empty in winter", "Kharif paddy land left empty in rabi – a second crop can be added")}

# four grades from the site score (cut-offs near the quartiles of real sites), clearly different colours
GRADES = [(85, "A", "Excellent", "#0b6b2e"), (80, "B", "Very good", "#46b04a"),
          (75, "C", "Good", "#f2c80f"), (0, "D", "Fair", "#f08c00")]


def grade(score):
    for cut, g, name, col in GRADES:
        if score >= cut:
            return g, name, col
    return GRADES[-1][1:]


FNAME = {"soil": "Soil", "water": "Water", "flood": "Flood safety", "terrain": "Flat land",
         "productivity": "Plant growth", "access": "Road access"}
FICON = {"soil": "🧪", "water": "💧", "flood": "🌊", "terrain": "⛰️", "productivity": "🌿", "access": "🛣️"}
GOOD = {"soil": "fertile soil", "water": "water close by", "flood": "safe from floods", "terrain": "flat land",
        "productivity": "crops and plants grow well here", "access": "near roads and markets"}
WATCH = {"soil": "soil is acidic or low in nutrients – get a soil test; lime and organic manure will help",
         "water": "water source is far – plan a tube well, pump or farm pond",
         "flood": "can flood in monsoon – flood-tolerant varieties or raised beds",
         "terrain": "land slopes – terracing or contour bunds needed",
         "productivity": "vegetation has been weak – visit the field before planning",
         "access": "far from roads or markets – transport will cost more"}


def level(v):
    return ("High", "#0b6b2e") if v >= 80 else ("Medium", "#c79100") if v >= 55 else ("Low", "#c0392b")


def advice(r, purpose):
    """Site-specific suggestion from land type, purpose and its own strengths/weaknesses."""
    s = int(r.land_status)
    f = {k: r[f"f_{k}"] for k in FACTORS}
    if purpose == "field_crops":
        base = {3: "Add a rabi crop after kharif paddy – mustard, lentil, pea or toria.",
                2: "Bring back into kharif cultivation; first check why it was left (water, flooding or ownership).",
                1: "New land: needs clearing and levelling before the first crop."}[s]
    else:
        base = {3: "Winter vegetables (potato, cabbage, tomato) on residual moisture after paddy.",
                2: "Good for a new orchard or banana plantation after land preparation.",
                1: "Suited to a horticulture cluster (citrus, pineapple, arecanut) after land development."}[s]
    extra = []
    if f["flood"] < 60:
        extra.append("Prefer flood-tolerant varieties (e.g. Swarna-Sub1 rice) or raised beds.")
    if f["water"] < 60:
        extra.append("Irrigation needed – link with PMKSY / farm pond scheme.")
    if f["soil"] < 70:
        extra.append("Soil Health Card test and liming before sowing.")
    return " ".join([base] + extra[:2])


def reasons(r):
    f = {k: r[f"f_{k}"] for k in FACTORS}
    good = [GOOD[k] for k, v in sorted(f.items(), key=lambda x: -x[1]) if v >= 80][:3]
    watch = [WATCH[k] for k, v in sorted(f.items(), key=lambda x: x[1]) if v < 60][:2]
    return good, watch


def factor_bars_html(r):
    cells = []
    for k in FACTORS:
        v = float(r[f"f_{k}"])
        lab, col = level(v)
        cells.append(f"<div class='fb'><div class='fbl'>{FICON[k]} {FNAME[k]}</div>"
                     f"<div class='fbt'><div style='width:{v:.0f}%;background:{col}'></div></div>"
                     f"<div class='fbv' style='color:{col}'>{lab}</div></div>")
    return "<div class='fgrid'>" + "".join(cells) + "</div>"


@st.cache_data
def load_patches(dkey, prof):
    P = OUT / dkey / prof
    p = gpd.read_file(P / "vectors" / "priority_patches.gpkg").to_crs(4326)
    c = p.geometry.representative_point()
    p["lat"], p["lon"] = c.y.round(5), c.x.round(5)
    g = p.mean_score.apply(grade)
    p["grade"], p["grade_name"], p["grade_col"] = [x[0] for x in g], [x[1] for x in g], [x[2] for x in g]
    p["pct_rank"] = p.mean_score.rank(pct=True)
    b = gpd.read_file(P / "vectors" / "blocks_ranking.gpkg").to_crs(4326)
    return p, b


@st.cache_data
def validation(dkey, prof="field_crops"):
    return json.loads((OUT / dkey / prof / "tables" / "validation.json").read_text())


CSS = """
<style>
.block-container {padding-top: 1.1rem !important; padding-bottom: 2rem; max-width: 1400px;}
header[data-testid="stHeader"] {height: 2.4rem; background: transparent;}
[data-testid="stSidebarHeader"] {padding: 0.8rem 1rem 0.2rem 1rem;}
[data-testid="stSidebarUserContent"] {padding-top: 0.3rem;}
[data-testid="stSidebar"] {background: linear-gradient(180deg, #eef7ee 0%, #f7faf5 60%);}
[data-testid="stSidebarNav"] span {font-size: 0.97rem;}
.ps-banner {background: linear-gradient(110deg, #0b4d24 0%, #127a36 55%, #2f9e44 100%); color: #fff;
  border-radius: 14px; padding: 16px 22px; margin-bottom: 14px; position: relative; overflow: hidden;}
.ps-banner:after {content: ""; position: absolute; right: -40px; top: -40px; width: 220px; height: 220px;
  background: radial-gradient(circle, rgba(255,255,255,0.18) 0%, rgba(255,255,255,0) 70%);}
.ps-banner h1 {color: #fff; font-size: 1.85rem; margin: 0; padding: 0;}
.ps-banner .sub {color: #dff3e3; font-size: 1.0rem; margin-top: 2px;}
.ps-banner .chips {margin-top: 9px;}
.ps-chip {display: inline-block; background: rgba(255,255,255,0.16); border: 1px solid rgba(255,255,255,0.35);
  color: #fff; border-radius: 999px; padding: 2px 10px; margin: 2px 6px 2px 0; font-size: 0.8rem;}
.ps-kpi {background: #fff; border: 1px solid #e3ece3; border-left: 6px solid #2f9e44; border-radius: 10px;
  padding: 10px 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); height: 100%; min-height: 104px; box-sizing: border-box;}
.ps-kpi .v {font-size: 1.6rem; font-weight: 700; color: #0b4d24; line-height: 1.2;}
.ps-kpi .l {font-size: 0.83rem; color: #4b5563;}
.ps-tile {background: #fff; border: 1px solid #dfe9df; border-radius: 12px; padding: 14px 16px; height: 100%; min-height: 168px; box-sizing: border-box;
  box-shadow: 0 1px 4px rgba(0,0,0,0.05);}
.ps-tile .ic {font-size: 1.8rem;} .ps-tile .t {font-weight: 700; font-size: 1.05rem; color: #0b4d24;}
.ps-tile .d {font-size: 0.88rem; color: #4b5563; margin-top: 3px;}
.ps-steps {display: flex; gap: 6px; margin: 2px 0 10px 0; flex-wrap: wrap;}
.ps-step {padding: 5px 14px; border-radius: 999px; background: #eef2ee; color: #6b7280; font-size: 0.88rem; font-weight: 600;}
.ps-step.on {background: #127a36; color: #fff;} .ps-step.done {background: #cfe9d4; color: #0b4d24;}
.ps-badge {display: inline-block; color: #fff; border-radius: 8px; padding: 2px 9px; font-size: 0.82rem; font-weight: 700;}
.fgrid {display: grid; grid-template-columns: repeat(3, 1fr); gap: 4px 14px; margin: 6px 0 4px 0;}
.fb {display: grid; grid-template-columns: 112px 1fr 58px; align-items: center; gap: 6px; font-size: 0.82rem;}
.fbt {background: #eef0ee; border-radius: 4px; height: 8px; overflow: hidden;} .fbt div {height: 8px; border-radius: 4px;}
.fbv {font-weight: 700; font-size: 0.78rem;}
.ps-legend span {display: inline-block; width: 13px; height: 13px; border-radius: 3px; margin: 0 5px -2px 12px;}
/* equal-height cards in a row: columns stretch to the tallest, cards fill their column */
[data-testid="stColumn"] > [data-testid="stVerticalBlock"] {height: 100%;}
[data-testid="stElementContainer"]:has(.ps-tile), [data-testid="stElementContainer"]:has(.ps-kpi) {flex: 1 1 auto;}
[data-testid="stElementContainer"]:has(.ps-tile) *:has(.ps-tile), [data-testid="stElementContainer"]:has(.ps-kpi) *:has(.ps-kpi) {height: 100%;}
.ps-card-end {margin-top: auto;}
[class*="st-key-dcard_"] [data-testid="stImage"] img {height: 300px; width: 100%; object-fit: contain;}
[data-testid="stMetricValue"] > div {font-size: 1.75rem; overflow: visible; text-overflow: clip;}
[data-testid="stElementContainer"]:has(.ps-card-end) {margin-top: auto;}
.ps-foot {color: #6b7280; font-size: 0.78rem; margin-top: 18px; border-top: 1px solid #e5e7eb; padding-top: 8px;}
</style>
"""


def banner(title, sub, chips=()):
    st.markdown(CSS, unsafe_allow_html=True)
    ch = "".join(f"<span class='ps-chip'>{c}</span>" for c in chips)
    st.markdown(f"<div class='ps-banner'><h1>{title}</h1><div class='sub'>{sub}</div>"
                f"<div class='chips'>{ch}</div></div>", unsafe_allow_html=True)


def kpi(col, value, label):
    col.markdown(f"<div class='ps-kpi'><div class='v'>{value}</div><div class='l'>{label}</div></div>", unsafe_allow_html=True)


def footer():
    st.markdown("<div class='ps-foot'>PotharSight Assam · prototype for NESFIC 2026 challenge D13 (DST Assam – ASSAC) · "
                "built only on free, open data (Sentinel-1/2, ESA WorldCover, Esri LULC, Copernicus DEM, JRC, CHIRPS, "
                "ISRIC SoilGrids, OpenStreetMap, DES Assam) · decision support only – land ownership must be verified by "
                "the Revenue Department.</div>", unsafe_allow_html=True)


def legend_html():
    return "<div class='ps-legend'>" + "".join(
        f"<span style='background:{c}'></span>{g} · {n}" for _, g, n, c in GRADES) + "</div>"


def bars(wide, colors, horizontal=False, stack=True, height=320, unit="hectares", pct=False):
    """Bar chart with a full, untruncated legend under the chart; keeps the row and series order of `wide`."""
    import altair as alt
    cat = wide.index.name or "item"
    w = wide.copy()
    w.index.name = cat
    series = [str(c) for c in w.columns]
    w.columns = series
    long = w.reset_index().melt(id_vars=cat, var_name="Series", value_name="value")
    long["order"] = long.Series.map({s: i for i, s in enumerate(series)})
    fmt = ".0f" if pct else ",.0f"
    val = alt.X if horizontal else alt.Y
    key = alt.Y if horizontal else alt.X
    v = val("value:Q", title=("% " if pct else "") + unit, stack="zero" if stack else None, axis=alt.Axis(format=",.0f"))
    k = key(f"{cat}:N", sort=list(w.index), title=None, axis=alt.Axis(labelAngle=0, labelLimit=260, labelOverlap=False))
    enc = dict(color=alt.Color("Series:N", sort=series, scale=alt.Scale(domain=series, range=list(colors)[:len(series)]),
                               legend=alt.Legend(orient="bottom", title=None, labelLimit=0, symbolType="square",
                                                 direction="horizontal", columns=min(len(series), 4), offset=6)),
               order=alt.Order("order:Q"),
               tooltip=[alt.Tooltip(f"{cat}:N", title=cat.title()), alt.Tooltip("Series:N", title=" "),
                        alt.Tooltip("value:Q", title="%" if pct else unit, format=fmt)])
    if not stack:
        enc["yOffset" if horizontal else "xOffset"] = alt.YOffset("Series:N", sort=series) if horizontal else alt.XOffset("Series:N", sort=series)
    ch = alt.Chart(long).mark_bar(cornerRadiusEnd=2).encode(x=v if horizontal else k, y=k if horizontal else v, **enc)
    if horizontal:
        height = max(height, 30 * len(w))
    st.altair_chart(ch.properties(height=height), use_container_width=True)
