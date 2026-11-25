"""PotharSight Assam – advanced analysis page for GIS staff (opened from app/streamlit_app.py)."""
import base64
import io
import json
import sys
import zipfile
from pathlib import Path

import folium
import geopandas as gpd
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from d13.core import load_config  # noqa: E402
from d13.model import CLASS_NAMES, FACTOR_LABEL, FACTORS  # noqa: E402
from d13.report import CLASS_COL  # noqa: E402

cfg = load_config()
OUT = ROOT / cfg["project"]["output_dir"]

available = [d for d in cfg["districts"] if (OUT / d / "field_crops" / "tables" / "validation.json").exists()]
if not available:
    st.error("No outputs found. Run `python run_all.py` first.")
    st.stop()

from theme import banner  # noqa: E402

banner("🛠️ Advanced map analysis", "For GIS staff and planners: full suitability classes, adjustable criteria weights, "
       "factor scores, block & circle rankings, validation and GIS downloads.",
       ["S1 / S2 / S3 / N classes (FAO)", "Live weight sliders", "GeoTIFF · GeoPackage · Shapefile"])
with st.sidebar:
    st.markdown("**Analysis settings**")
    dkey = st.selectbox("District", available,
                        format_func=lambda k: cfg["districts"].get(k, {}).get("label",
                                                                              cfg["districts"].get(k, {}).get("boundary_name", k)))
    profs = [p for p in cfg["profiles"] if (OUT / dkey / p).exists()]
    prof = st.selectbox("Programme", profs, format_func=lambda p: cfg["profiles"][p]["label"])
    pc = cfg["profiles"][prof]
    st.caption(f"Hard limits: slope ≤ {pc['max_slope_pct']} %, monsoon flood frequency ≤ {pc['max_flood_freq']}")
    st.markdown("**Criteria weights** – move to re-rank patches live")
    w0 = pc["weights"]
    w = {f: st.slider(FACTOR_LABEL[f], 0.0, 0.5, float(w0[f]), 0.05) for f in FACTORS}
    top_n = st.slider("Patches drawn on map", 50, 3000, 500, 50)

P = OUT / dkey / prof
dname = cfg["districts"].get(dkey, {}).get("boundary_name", dkey)


@st.cache_data
def load(path):
    patches = gpd.read_file(path / "vectors" / "priority_patches.gpkg").to_crs(4326)
    blocks = gpd.read_file(path / "vectors" / "blocks_ranking.gpkg").to_crs(4326)
    circles = pd.read_csv(path / "tables" / "circles_ranking.csv")
    val = json.loads((path / "tables" / "validation.json").read_text())
    sens = pd.read_csv(path / "tables" / "sensitivity.csv") if (path / "tables" / "sensitivity.csv").exists() else None
    return patches, blocks, circles, val, sens


patches, blocks, circles, val, sens = load(P)
ws = sum(w.values()) or 1
patches["score_live"] = sum(patches[f"f_{f}"] * w[f] for f in FACTORS) / ws
patches["priority_live"] = 0.8 * patches.score_live + 20 * patches.area_ha.clip(upper=10) / 10
patches = patches.sort_values("priority_live", ascending=False)
patches["rank_live"] = range(1, len(patches) + 1)

st.markdown(f"### {dname} · {pc['label']}")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Priority land (S1+S2 patches)", f"{patches.area_ha.sum():,.0f} ha")
c2.metric("Priority patches ≥ 0.5 ha", f"{len(patches):,}")
c3.metric("of which S1 (highly suitable)", f"{patches.loc[patches['class'] == 1, 'area_ha'].sum():,.0f} ha")
c4.metric("Satellite: vacant + long fallow", f"{val['model_vacant_plus_long_fallow_ha']:,} ha")
c5.metric("Official vacant cultivable (DES 2020-21)", f"{val.get('official_vacant_cultivable_ha') or 0:,} ha")

tab_map, tab_why, tab_dl, tab_val, tab_method = st.tabs(
    ["🗺️ Map & ranking", "❓ Why this result", "⬇️ Downloads", "✅ Validation", "⚙️ Method & scalability"])

with tab_map:
    left, right = st.columns([3, 2])
    with left:
        b = blocks.total_bounds
        m = folium.Map(location=[(b[1] + b[3]) / 2, (b[0] + b[2]) / 2], zoom_start=10, tiles=None)
        folium.TileLayer("OpenStreetMap", name="OpenStreetMap", show=False).add_to(m)
        folium.TileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                         attr="Esri World Imagery", name="Satellite (Esri)", show=True).add_to(m)
        ov = P / "figures" / "overlay_class_4326.png"
        if ov.exists():
            uri = "data:image/png;base64," + base64.b64encode(ov.read_bytes()).decode()
            folium.raster_layers.ImageOverlay(uri, bounds=json.loads((P / "figures" / "overlay_bounds.json").read_text()),
                                              name="Suitability class (30 m)", opacity=0.75).add_to(m)
        folium.GeoJson(blocks[["name", "rank", "S1_ha", "S2_ha", "mean_score", "main_limitation", "geometry"]],
                       name="Development blocks", style_function=lambda f: {"fill": False, "color": "#ffffff", "weight": 1.5},
                       tooltip=folium.GeoJsonTooltip(["name", "rank", "S1_ha", "S2_ha", "mean_score", "main_limitation"],
                                                     aliases=["Block", "Rank", "S1 ha", "S2 ha", "Mean score", "Main limitation"])
                       ).add_to(m)
        show = patches.head(top_n).copy()
        show["geometry"] = show.geometry.simplify(0.0002)
        cols = ["rank_live", "block", "circle", "area_ha", "score_live", "class_name", "status_name", "reason"] + [f"f_{f}" for f in FACTORS]
        cols = [c for c in cols if c in show.columns]
        folium.GeoJson(show[cols + ["class", "geometry"]].round(1), name=f"Top {top_n} priority patches",
                       style_function=lambda f: {"color": "#ff00ff", "weight": 0.8,
                                                 "fillColor": CLASS_COL[int(f["properties"]["class"])], "fillOpacity": 0.85},
                       popup=folium.GeoJsonPopup(cols, labels=True, max_width=400)).add_to(m)
        folium.LayerControl(collapsed=False).add_to(m)
        legend = "".join(f'<div><span style="background:{CLASS_COL[k]};width:14px;height:14px;display:inline-block;'
                         f'margin-right:6px;border:1px solid #555"></span>{CLASS_NAMES[k]}</div>' for k in [1, 2, 3, 5])
        m.get_root().html.add_child(folium.Element(
            f'<div style="position:fixed;bottom:18px;left:18px;z-index:9999;background:white;padding:8px 10px;'
            f'font:12px sans-serif;border-radius:6px;box-shadow:0 1px 4px #0006">{legend}'
            f'<div><span style="border:2px solid #ff00ff;width:12px;height:12px;display:inline-block;margin-right:6px"></span>'
            f'Priority patch (click for reasons)</div></div>'))
        components.html(m.get_root().render(), height=620)
        st.caption("Click a magenta-outlined patch for its rank, factor scores and reason. Hover a block for its rank.")
    with right:
        st.markdown("**Block prioritisation** (priority index = (S1 ha + ½·S2 ha) × mean score)")
        st.dataframe(blocks.drop(columns="geometry")[["rank", "name", "S1_ha", "S2_ha", "candidate_ha",
                                                       "mean_score", "main_limitation"]],
                     hide_index=True, height=280)
        st.markdown("**Top patches** (re-ranked with your weights)")
        blk = st.selectbox("Filter by block", ["All"] + sorted(patches.block.unique()))
        t = patches if blk == "All" else patches[patches.block == blk]
        st.dataframe(t[["rank_live", "block", "area_ha", "score_live", "class_name", "status_name"]].head(200).round(1),
                     hide_index=True, height=260)
    with st.expander("Revenue-circle prioritisation"):
        st.dataframe(circles[["rank", "name", "S1_ha", "S2_ha", "candidate_ha", "mean_score", "main_limitation"]],
                     hide_index=True)

with tab_why:
    st.markdown("Every patch carries six 0–100 factor scores, its strongest and most limiting factor and a plain-language reason.")
    pid = st.selectbox("Patch (by live rank)", patches.rank_live.head(500))
    r = patches[patches.rank_live == pid].iloc[0]
    a, bcol = st.columns([2, 3])
    with a:
        st.metric("Live suitability score", f"{r.score_live:.1f} / 100")
        st.write(f"**Class:** {r.class_name}")
        st.write(f"**Land status:** {r.status_name}")
        st.write(f"**Area:** {r.area_ha:.1f} ha · **Block:** {r.block}" + (f" · **Circle:** {r.circle}" if "circle" in r else ""))
        c = r.geometry.representative_point()
        st.write(f"**Location:** {c.y:.5f} N, {c.x:.5f} E  "
                 f"([satellite view](https://www.google.com/maps/@{c.y:.5f},{c.x:.5f},800m/data=!3m1!1e3))")
        st.info(r.reason)
    with bcol:
        st.bar_chart(pd.DataFrame({"factor score (0-100)": [r[f"f_{f}"] for f in FACTORS]},
                                  index=[FACTOR_LABEL[f] for f in FACTORS]), horizontal=True)
    st.warning("Decision support only: verify land use in the field and ownership/legal status with the Revenue "
               "Department before any allocation.")

with tab_dl:
    st.markdown("Standard GIS formats – open in QGIS, ArcGIS, Bhuvan or any web GIS. CRS: WGS84 (GeoJSON) / UTM 46N (others).")
    files = [("Priority patches – GeoPackage", "vectors/priority_patches.gpkg"),
             ("Priority patches – GeoJSON", "vectors/priority_patches.geojson"),
             ("Priority patches – CSV (with reasons)", "tables/priority_patches.csv"),
             ("Block ranking – GeoPackage", "vectors/blocks_ranking.gpkg"),
             ("Block ranking – CSV", "tables/blocks_ranking.csv"),
             ("Revenue-circle ranking – CSV", "tables/circles_ranking.csv"),
             ("Suitability score – GeoTIFF (30 m)", "maps/suitability_score.tif"),
             ("Suitability class – GeoTIFF (30 m)", "maps/suitability_class.tif"),
             ("Land status – GeoTIFF (30 m)", "maps/land_status.tif"),
             ("Limiting factor – GeoTIFF (30 m)", "maps/limiting_factor.tif"),
             ("Factor scores – 6-band GeoTIFF", "maps/factor_scores.tif")]
    cols = st.columns(3)
    for i, (lbl, f) in enumerate(files):
        p = P / f
        if p.exists():
            cols[i % 3].download_button(lbl, p.read_bytes(), file_name=f"{dkey}_{prof}_{p.name}", key=f)
    shp = P / "vectors" / "shp"
    if shp.exists():
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for f in shp.iterdir():
                z.write(f, f.name)
        cols[len(files) % 3].download_button("Priority patches – Shapefile (zip)", buf.getvalue(),
                                             file_name=f"{dkey}_{prof}_priority_patches_shp.zip")
    st.caption("Raster codes – class: 1 S1, 2 S2, 3 S3, 4 N, 5 constrained · land status: 0 excluded, 1 vacant, "
               "2 long fallow, 3 rabi fallow, 4 active · limiting factor: 1 soil, 2 water, 3 flood, 4 terrain, "
               "5 productivity, 6 access.")

with tab_val:
    v1, v2, v3 = st.columns(3)
    v1.metric("Model ÷ official vacant land", val.get("ratio_model_to_official", "–"),
              help="Satellite-observed vacant + long-fallow land vs DES culturable waste + fallows")
    v2.metric("Active farmland rated S1/S2", f"{100 * val['active_farmland_share_scoring_S1_S2']:.0f} %",
              help="Land that is actually double-cropped should score well on biophysical criteria")
    v3.metric("Ranking stability (min Spearman ρ, ±20 % weights)", val["sensitivity_min_rho"])
    if sens is not None:
        st.dataframe(sens, hide_index=True)
    st.json(val, expanded=False)
    spot = ROOT / "docs" / "spot_check.csv"
    if spot.exists():
        sc = pd.read_csv(spot)
        sc = sc[(sc.district == dkey)]
        if len(sc):
            st.markdown("**Visual spot-check against high-resolution imagery**")
            st.dataframe(sc, hide_index=True)
    st.markdown("""
**Limitations (stated openly)**
- Soil is modelled (ISRIC SoilGrids, 250 m), not field-tested; Soil Health Card / NBSS&LUP data replace it when shared.
- "Available" means vacant or under-used in satellite data; **ownership and legal status must be verified by the Revenue Department**.
- Flood frequency is from Sentinel-1 monsoon radar 2022-24; char and riverine land changes year to year.
- Boundaries are geoBoundaries (LGD-based) and are not authoritative; official LGD/Survey of India layers replace them in the pilot.
""")

with tab_method:
    st.markdown(f"""
**Pipeline:** free satellite & GIS layers → common 30 m grid → land availability → hard constraints → six factor scores →
weighted suitability (S1/S2/S3/N) with a most-limiting-factor cap → reasons → patches, block & circle ranking → validation.

| Factor | Indicators | Source | Weight ({pc['label'].split(' (')[0]}) |
|---|---|---|---|
| Soil fertility | pH, organic carbon, nitrogen, CEC, clay (0-30 cm) | ISRIC SoilGrids 2.0 | {w0['soil']} |
| Water availability | annual rainfall, distance to river / permanent water | CHIRPS, JRC, OSM | {w0['water']} |
| Flood safety | monsoon flood frequency 2022-24 | Sentinel-1 radar | {w0['flood']} |
| Gentle terrain | slope | Copernicus DEM 30 m | {w0['terrain']} |
| Vegetation productivity | seasonal peak NDVI 2022-24 | Sentinel-2 | {w0['productivity']} |
| Road / market access | distance to road, town | OpenStreetMap | {w0['access']} |

**Land availability:** ESA WorldCover 2021 + Esri land use 2017-2023 + JRC water + Sentinel-2 kharif/rabi NDVI
→ excluded (forest, water, built-up, wetland, protected) · vacant open land · long fallow / under-used cropland ·
seasonal (rabi) fallow · active double-cropped.

**Classes:** S1 ≥ {cfg['classes']['S1']}, S2 ≥ {cfg['classes']['S2']}, S3 ≥ {cfg['classes']['S3']}; a factor below
{cfg['classes'].get('cap_S2_if_any_factor_below', '–')} caps the class at S2, below {cfg['classes'].get('cap_S3_if_any_factor_below', '–')} at S3.

**Scalable by configuration – no code change:**
- *New district:* add one entry under `districts` in `config.yaml` and run `python run_all.py --district <name>`.
- *New state:* point `boundaries` to that state's district/block layers.
- *New crop or programme:* add a profile with its own slope/flood limits and weights.
- *Department data:* ASSAC LULC, Soil Health Card, ASDMA flood or cadastral layers replace the open layer file.
""")
    st.caption("All inputs are free and open (CC BY 4.0 / ODbL / Copernicus licence). Source register: data/data_register.csv")
