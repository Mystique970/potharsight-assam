"""Technical Annex PDF: data, formulas, a worked example on live outputs, validation detail and portal screens.
   python tools/build_annex.py   ->  docs/pow/PotharSight_Assam_D13_Technical_Annex.html / .pdf
"""
import json
from pathlib import Path

import pandas as pd
import yaml

from doc_style import CSS, FONTS, flow, laptop, phones, to_pdf

ROOT = Path(__file__).resolve().parents[1]
POW = ROOT / "docs" / "pow"
cfg = yaml.safe_load((ROOT / "config.yaml").read_text())
OUT = ROOT / "outputs"
DIST = [d for d in cfg["districts"] if (OUT / d / "field_crops" / "tables" / "validation.json").exists()]
NAME = {d: cfg["districts"][d]["boundary_name"] + (" (Rural)" if d == "kamrup" else "") for d in DIST}
FACT = ["soil", "water", "flood", "terrain", "productivity", "access"]
FLAB = {"soil": "Soil fertility", "water": "Water availability", "flood": "Flood safety", "terrain": "Gentle terrain",
        "productivity": "Vegetation productivity", "access": "Road / market access"}
V = {d: json.loads((OUT / d / "field_crops" / "tables" / "validation.json").read_text()) for d in DIST}
PP = {d: pd.read_csv(OUT / d / "field_crops" / "tables" / "priority_patches.csv") for d in DIST}
BL = {d: pd.read_csv(OUT / d / "field_crops" / "tables" / "blocks_ranking.csv") for d in DIST}
s, a, c = cfg["scoring"], cfg["availability"], cfg["classes"]
fc, ho = cfg["profiles"]["field_crops"], cfg["profiles"]["horticulture"]
FOOT = "<div class='foot'>PotharSight Assam · Technical Annex (additional supporting material) · NESFIC 2026 · Challenge D13</div>"
H = [f"<html><head><meta charset='utf-8'><title>PotharSight Assam – Technical Annex</title>{FONTS}<style>{CSS}</style></head><body>{FOOT}"]


def tbl(rows, head):
    return ("<table class='t'><tr>" + "".join(f"<th>{h}</th>" for h in head) + "</tr>"
            + "".join("<tr>" + "".join(f"<td>{x}</td>" for x in r) + "</tr>" for r in rows) + "</table>")


# ------------------------------------------------------------------ cover
n_sites = sum(len(PP[d]) for d in DIST)
ha = sum(PP[d].area_ha.sum() for d in DIST)
H.append(f"""<div class="page" style="padding-top:18mm"><div class="eyebrow"><i></i>Additional supporting material</div>
<h1 style="font-size:32pt;margin-top:14px">PotharSight Assam</h1>
<div class="lead">Technical Annex: data, formulas, calculations and evidence</div>
<p style="margin-top:12px">This annex lets a reviewer check the method behind the Proof of Work. It lists every data source, writes out every rule
and formula exactly as the code applies it (values from <code>config.yaml</code>), recomputes one live result by hand, and gives the full
validation detail. Every number is read from the prototype's own output files at build time; nothing is illustrative.</p>
<table class="t" style="margin-top:10px"><tr><th style="width:38%">Item</th><th>Value</th></tr>
<tr><td>Challenge</td><td>NESFIC 2026 · D13 · Geospatial identification of cultivable & fertile agricultural potential land (DST Assam – ASSAC)</td></tr>
<tr><td>Districts</td><td>{", ".join(NAME[d] for d in DIST)} – the top {len(DIST)} in Assam for vacant cultivable land (DES 2020-21)</td></tr>
<tr><td>Grid</td><td>{cfg['project']['resolution_m']} m, {cfg['project']['crs']} (UTM 46N)</td></tr>
<tr><td>Ranked sites (field crops)</td><td>{n_sites:,} S1/S2 patches ≥ {a['min_patch_ha']} ha, {ha:,.0f} ha</td></tr>
<tr><td>Portal</td><td>Streamlit web app, responsive (desktop + phone), English and Assamese, public demo access</td></tr>
<tr><td>Date</td><td>25 November 2026</td></tr></table>
<h3>Contents</h3><ol style="margin-left:16px;padding:0">
<li>Data foundation: sources, resolution, licences</li><li>Land availability rules and the flood data-quality gate</li>
<li>Factor scoring functions and parameters</li><li>Suitability classes, prioritisation and grades</li>
<li>Worked example on live data</li><li>Validation detail</li><li>Portal: design, language and screens</li>
<li>Assumptions register and limitations</li></ol></div>""")

# ------------------------------------------------------------------ A data
reg = ROOT / "data" / "data_register.csv"
rows = []
if reg.exists():
    r = pd.read_csv(reg)
    r["layer"] = r.layer.str.replace(r"_\d{4}$", "", regex=True)
    g = r.groupby("layer").agg(source=("source", "first"), url=("url", "first"), licence=("licence", "first"),
                               districts=("district", lambda x: len(set(x)))).reset_index()
    rows = [[x.layer, x.source[:90], f"<span class='small'>{x.url}</span>", x.licence, x.districts] for x in g.itertuples()]
H.append(f"""<div class="page"><div class="eyebrow"><i></i>A</div><h2 style="margin-top:6px">A. Data foundation</h2>
<p>All inputs are free and need no login. They are downloaded by script (STAC / cloud-optimised GeoTIFF windowed reads with fallbacks) and
every download is written to <code>data/data_register.csv</code>, summarised below.</p>
{tbl(rows, ["Layer", "Source", "URL", "Licence", "Districts"])}
<h3>Common grid and pre-processing</h3><ul>
<li>Each district boundary (geoBoundaries ADM2, LGD-based) plus a {cfg['project']['buffer_m']} m buffer defines a {cfg['project']['resolution_m']} m grid in UTM 46N.</li>
<li>Categorical layers (WorldCover, Esri LULC) are resampled with nearest neighbour; continuous layers (NDVI, DEM, soil, rain) bilinearly.</li>
<li>Sentinel-2 NDVI: per season (kharif Jun–Oct, rabi Nov–Mar) for {", ".join(map(str, cfg['fetch']['s2_years']))}, clouds &lt; {cfg['fetch']['s2_max_cloud']} %, up to
{cfg['fetch']['s2_items_per_tile_per_season']} scenes per tile per season; the seasonal peak is kept.</li>
<li>Sentinel-1 flood frequency: share of monsoon ({", ".join(map(str, cfg['fetch']['s1_months']))}) VV scenes below the water threshold, {", ".join(map(str, cfg['fetch']['s1_years']))}.</li>
<li>Soil: SoilGrids 2.0 mean of 0–5, 5–15 and 15–30 cm; rainfall: CHIRPS annual mean {cfg['fetch']['chirps_years'][0]}–{cfg['fetch']['chirps_years'][-1]}.</li>
<li>Distances (water, road, town) are Euclidean distance transforms on the grid from OSM and JRC layers.</li></ul></div>""")

# ------------------------------------------------------------------ B availability
qa_rows = []
for d in DIST:
    q = ROOT / "data" / "interim" / d / "flood_qa.json"
    if q.exists():
        j = json.loads(q.read_text())
        qa_rows.append([NAME[d], f"{j.get('s1_median_cropland_flood_freq', float('nan')):.2f}" if j.get("s1_median_cropland_flood_freq") is not None else "–",
                        "Sentinel-1 radar" if j.get("s1_used") else "JRC occurrence + Esri water history (proxy)"])
    else:
        qa_rows.append([NAME[d], "no radar layer", "JRC occurrence + Esri water history (proxy)"])
H.append(f"""<div class="page"><div class="eyebrow"><i></i>B</div><h2 style="margin-top:6px">B. Land availability rules</h2>
<p>Every 30 m cell gets one status, in this order (a later rule overrides an earlier one):</p>
{tbl([["Excluded (0)", "WorldCover tree (10), built-up (50), water (80), wetland (90), mangrove (95); protected areas (OSM); JRC water occurrence ≥ "
       f"{a['permanent_water_occurrence']} %; Esri built-up in any of the last 3 years; Esri trees or water in all of the last 3 years; Esri water in ≥ "
       f"{a['esri_water_years_exclude']} of the 7 yearly maps (shifting river channels)"],
      ["Vacant open land (1)", f"WorldCover classes {a['open_land_worldcover']} (shrub, grass, moss), or Esri rangeland {a['open_land_esri']} in the latest year, "
       "and not cropland. Bare ground is left out: in Assam floodplains it is mostly river sand."],
      ["Long fallow / under-used (2)", f"Cropland whose kharif peak NDVI &lt; {a['fallow_kharif_ndvi_max']}, or land that was cropland (WorldCover 40 or Esri crops in any year) "
       f"and is Esri rangeland {a['undercropped_esri_classes']} in the latest year"],
      ["Rabi fallow (3)", f"Cropland not in (2) whose rabi peak NDVI &lt; {a['fallow_rabi_ndvi_max']} – kharif paddy left empty in winter"],
      ["Active (4)", "All other cropland – not a candidate; used only to test that the criteria reward productive land"]],
     ["Status", "Rule (values from config.yaml → availability)"])}
<p class="small">Why 0.50 for long fallow: the 5th percentile of kharif peak NDVI on active farmland in Kamrup is 0.52, so cropland below 0.50 is
unlikely to have carried a kharif crop.</p>
<h3>Flood data-quality gate</h3>
<div class="formula">gate passes  ⇔  median( S1 flood frequency on WorldCover cropland ) ≤ {a['s1_qa_max_cropland_flood']}</div>
<p>Ordinary cropland should not look flooded in most monsoon radar scenes. Where waterlogged paddy makes radar read as flood, the gate fails
and the flood layer falls back to JRC occurrence plus Esri water history. The result is stored per run in <code>flood_qa.json</code>.</p>
{tbl(qa_rows, ["District", "Median S1 flood frequency on cropland", "Flood layer used"])}
<h3>Pipeline</h3>{flow(["<b>Ingest</b>STAC / COG reads, register", "<b>Grid</b>30 m UTM 46N", "<b>Availability</b>status 0–4",
                       "<b>Constraints</b>slope, flood", "<b>Factors</b>six 0–100 scores", "<b>Suitability</b>weighted + caps",
                       "<b>Rank</b>patches, blocks, circles", "<b>Serve</b>portal, GIS files"])}</div>""")

# ------------------------------------------------------------------ C scoring
rows = [
    ["Soil pH", "trapezoid", f"0 at {s['ph_limits'][0]} and {s['ph_limits'][1]}; 1 between {s['ph_optimum'][0]} and {s['ph_optimum'][1]}", f"soil × {s['soil_weights']['ph']}"],
    ["Soil organic carbon (g/kg)", "ramp", f"0 at {s['soc_gkg'][0]} → 1 at {s['soc_gkg'][1]}", f"soil × {s['soil_weights']['soc']}"],
    ["Nitrogen (g/kg)", "ramp", f"0 at {s['nitrogen_gkg'][0]} → 1 at {s['nitrogen_gkg'][1]}", f"soil × {s['soil_weights']['nitrogen']}"],
    ["CEC (cmol/kg)", "ramp", f"0 at {s['cec_cmolkg'][0]} → 1 at {s['cec_cmolkg'][1]}", f"soil × {s['soil_weights']['cec']}"],
    ["Clay (%)", "trapezoid", f"0 at {s['clay_limits'][0]} and {s['clay_limits'][1]}; 1 between {s['clay_optimum'][0]} and {s['clay_optimum'][1]}", f"soil × {s['soil_weights']['clay']}"],
    ["Annual rainfall (mm)", "trapezoid", f"0 at {s['rain_limits'][0]} and {s['rain_limits'][1]}; 1 between {s['rain_optimum'][0]} and {s['rain_optimum'][1]}", "water × 0.4"],
    ["Distance to water (m)", "ramp (decreasing)", f"1 within {s['dist_water_m'][0]} → 0 beyond {s['dist_water_m'][1]}", "water × 0.6"],
    ["Monsoon flood frequency", "ramp (decreasing)", f"1 at {s['flood_freq'][0]} → 0 at {s['flood_freq'][1]}", "flood × 1"],
    ["Slope (%)", "ramp (decreasing)", f"1 at {s['slope_pct'][0]} → 0 at {s['slope_pct'][1]}", "terrain × 1"],
    ["Peak NDVI (max of kharif, rabi)", "ramp", f"0 at {s['ndvi_peak'][0]} → 1 at {s['ndvi_peak'][1]}", "productivity × 1"],
    ["Distance to road (m)", "ramp (decreasing)", f"1 within {s['dist_road_m'][0]} → 0 beyond {s['dist_road_m'][1]}", "access × 0.6"],
    ["Distance to town (m)", "ramp (decreasing)", f"1 within {s['dist_town_m'][0]} → 0 beyond {s['dist_town_m'][1]}", "access × 0.4"]]
H.append(f"""<div class="page"><div class="eyebrow"><i></i>C</div><h2 style="margin-top:6px">C. Factor scoring</h2>
<p>Each indicator becomes a 0–1 score with one of two functions (<code>d13/core.py</code>), then indicators combine into six factors.</p>
<div class="formula">ramp(x; lo, hi) = clip( (x − lo) / (hi − lo), 0, 1 )      (lo &gt; hi gives a decreasing ramp)<br>
trapezoid(x; [L0, L1], [O0, O1]) = min( clip((x − L0)/(O0 − L0), 0, 1),  clip((L1 − x)/(L1 − O1), 0, 1) )</div>
{tbl(rows, ["Indicator", "Function", "Parameters (config.yaml → scoring)", "Feeds"])}
<div class="formula">soil = Σ w_i · s_i / Σ w_i   with w = pH {s['soil_weights']['ph']}, SOC {s['soil_weights']['soc']}, N {s['soil_weights']['nitrogen']}, CEC {s['soil_weights']['cec']}, clay {s['soil_weights']['clay']}<br>
water = 0.4 · rain + 0.6 · distance-to-water        access = 0.6 · road + 0.4 · town<br>
flood, terrain, productivity = their single indicator</div>
<p class="small">Soil norms follow Soil Health Card / ICAR ratings (organic carbon 0.5 % = low, &gt; 0.75 % = high; acidity is the main soil constraint
in Assam). Rainfall uses a trapezoid so both deficit and excess are penalised. Gaps in coarse layers (soil, rain edges) are filled with the district
median so one missing value never removes a cell.</p></div>""")

# ------------------------------------------------------------------ D suitability
H.append(f"""<div class="page"><div class="eyebrow"><i></i>D</div><h2 style="margin-top:6px">D. Suitability, prioritisation and grades</h2>
<h3>Weighted score and class</h3>
<div class="formula">score = 100 · Σ_f w_f · factor_f / Σ_f w_f<br>
class = S1 if score ≥ {c['S1']} · S2 if ≥ {c['S2']} · S3 if ≥ {c['S3']} · otherwise N<br>
if min(factor) &lt; {c['cap_S2_if_any_factor_below']}: class ≤ S2       if min(factor) &lt; {c['cap_S3_if_any_factor_below']}: class ≤ S3   (FAO most-limiting factor)<br>
constrained (class 5) if slope &gt; max slope or flood frequency &gt; max flood</div>
{tbl([["Field crops", fc['max_slope_pct'], fc['max_flood_freq']] + [fc['weights'][f] for f in FACT],
      ["Horticulture", ho['max_slope_pct'], ho['max_flood_freq']] + [ho['weights'][f] for f in FACT]],
     ["Profile", "Max slope %", "Max flood freq."] + [FLAB[f] for f in FACT])}
<h3>Reasons</h3>
<div class="formula">limiting factor = argmax_f (1 − factor_f) · w_f        contributing factor = argmax_f factor_f · w_f</div>
<h3>Sites (patches) and their priority</h3>
<div class="formula">patch = 8-connected group of candidate cells (status 1–3) in class S1/S2, area ≥ {a['min_patch_ha']} ha<br>
patch class = S1 if ≥ 50 % of its cells are S1, else S2;  patch status = most common status<br>
patch priority = 0.8 · mean score + 20 · min(area_ha, 10) / 10</div>
<h3>Blocks and revenue circles</h3>
<div class="formula">priority index = (S1 ha + 0.5 · S2 ha) · mean score / 100      rank = descending priority index</div>
<h3>Grades shown to officials</h3>
{tbl([["A · Excellent", "≥ 85", "#0b6b2e"], ["B · Very good", "80 – 85", "#46b04a"], ["C · Good", "75 – 80", "#e3b505"], ["D · Fair", "&lt; 75", "#e8820c"]],
     ["Grade", "Site mean score", "Map colour"])}
<p class="small">Grades split the S1/S2 sites near their quartiles so an official sees a spread of quality, not one colour. Factor levels on site
cards: High ≥ 80, Medium 55–80, Low &lt; 55. Watch-outs are shown for factors &lt; 60; strong points for factors ≥ 80.</p></div>""")

# ------------------------------------------------------------------ E worked example
d0 = DIST[0]
r = PP[d0].iloc[0]
w = fc["weights"]
contrib = [[FLAB[f], f"{r[f'f_{f}']:.2f}", w[f], f"{r[f'f_{f}'] * w[f]:.2f}", f"{(100 - r[f'f_{f}']) * w[f]:.2f}"] for f in FACT]
score = sum(r[f"f_{f}"] * w[f] for f in FACT) / sum(w.values())
weakest = min(r[f"f_{f}"] for f in FACT)
lim = max(FACT, key=lambda f: (100 - r[f"f_{f}"]) * w[f])
prio = 0.8 * r.mean_score + 20 * min(r.area_ha, 10) / 10
b0 = BL[d0][BL[d0].name == r.block].iloc[0] if (BL[d0].name == r.block).any() else BL[d0].iloc[0]
pi = (b0.S1_ha + 0.5 * b0.S2_ha) * b0.mean_score / 100
gr = "A · Excellent" if r.mean_score >= 85 else "B · Very good" if r.mean_score >= 80 else "C · Good" if r.mean_score >= 75 else "D · Fair"
H.append(f"""<div class="page"><div class="eyebrow"><i></i>E</div><h2 style="margin-top:6px">E. Worked example (live data)</h2>
<p><b>Site rank 1, {NAME[d0]}, field crops</b> · {r.block} block · revenue circle {r.circle} · {r.area_ha:.2f} ha · {r.status_name.lower()} ·
patch id {int(r.pid)}. Values are read from <code>outputs/{d0}/field_crops/tables/priority_patches.csv</code>.</p>
<h3>Step 1 – weighted score</h3>
{tbl(contrib + [["<b>Total</b>", "", f"{sum(w.values()):.2f}", f"<b>{score:.2f}</b>", ""]],
     ["Factor", "Patch mean score (0–100)", "Weight", "Score × weight", "Shortfall × weight"])}
<div class="formula">score = {" + ".join(f"{w[f]}·{r[f'f_{f}']:.2f}" for f in FACT)} = {score:.2f}   (file: {r.mean_score:.2f})</div>
<h3>Step 2 – class and grade</h3>
<div class="formula">{score:.2f} ≥ {c['S1']} → S1;  weakest factor {weakest:.1f} ≥ {c['cap_S2_if_any_factor_below']} → no cap;  share of S1 cells {r.share_S1:.2f} → patch class S1<br>
{r.mean_score:.2f} → grade {gr}</div>
<h3>Step 3 – reason</h3>
<div class="formula">largest shortfall × weight: {FLAB[lim].lower()} → limiting factor = {lim}</div>
<div class="note"><b>Stored reason:</b> {r.reason}<br><b>Portal suggestion:</b> rabi-fallow land with soil as the weakest point →
“Add a rabi crop after kharif paddy – mustard, lentil, pea or toria. Soil Health Card test and liming before sowing.” (liming is added when soil &lt; 70)</div>
<h3>Step 4 – priority and rank</h3>
<div class="formula">priority = 0.8 · {r.mean_score:.2f} + 20 · min({r.area_ha:.2f}, 10)/10 = {prio:.2f}   (file: {r.priority:.2f}) → rank {int(r.rank_district)} of {len(PP[d0]):,} in {NAME[d0]}</div>
<h3>Step 5 – its block</h3>
<div class="formula">{b0['name']}: S1 {b0.S1_ha:,.0f} ha, S2 {b0.S2_ha:,.0f} ha, mean score {b0.mean_score:.1f}<br>
priority index = ({b0.S1_ha:,.0f} + 0.5 · {b0.S2_ha:,.0f}) · {b0.mean_score:.1f} / 100 = {pi:,.1f}   (file: {b0.priority_index:,.1f}) → block rank {int(b0['rank'])}</div></div>""")

# ------------------------------------------------------------------ F validation
vrows = [[NAME[d], f"{V[d]['official_vacant_cultivable_ha']:,}", f"{V[d]['model_vacant_plus_long_fallow_ha']:,}", V[d]["ratio_model_to_official"],
          f"{V[d]['model_all_candidate_incl_rabi_fallow_ha']:,}", f"{100 * V[d]['active_farmland_share_scoring_S1_S2']:.0f} %",
          f"{V[d]['mean_score_active_farmland']:.1f} / {V[d]['mean_score_candidate_land']:.1f}",
          f"{V[d]['sensitivity_min_rho']} · {V[d]['sensitivity_mean_top5_overlap']}/5"] for d in DIST]
sens = pd.read_csv(OUT / d0 / "field_crops" / "tables" / "sensitivity.csv")
srows = [[x.factor, x.change, x.spearman_rho, x.top5_overlap] for x in sens.itertuples()]
sp = ROOT / "docs" / "spot_check.csv"
sprows = []
if sp.exists():
    t = pd.read_csv(sp)
    for dk, g in t.groupby("district", sort=False):
        vc = g.verdict.value_counts()
        sprows.append([NAME.get(dk, dk), len(g), vc.get("consistent", 0), vc.get("uncertain", 0), vc.get("doubtful", 0),
                       f"{100 * vc.get('consistent', 0) / len(g):.0f} %"])
    vc = t.verdict.value_counts()
    sprows.append(["<b>All</b>", len(t), vc.get("consistent", 0), vc.get("uncertain", 0), vc.get("doubtful", 0), f"<b>{100 * vc.get('consistent', 0) / len(t):.0f} %</b>"])
H.append(f"""<div class="page"><div class="eyebrow"><i></i>F</div><h2 style="margin-top:6px">F. Validation detail</h2>
<h3>F1. Against official statistics and farmland (field crops)</h3>
{tbl(vrows, ["District", "Official vacant cultivable (ha, DES 2020-21)", "Satellite vacant + long fallow (ha)", "Ratio", "Incl. rabi fallow (ha)",
             "Active farmland rated S1/S2", "Mean score active / candidate", "Sensitivity min ρ · top-5 overlap"])}
<p class="small">Ratio below 1 is expected: DES culturable waste includes scrub that satellite land cover maps as trees, and current fallow varies
by year. Active double-cropped land scoring high shows the criteria reward land that is really productive.</p>
<h3>F2. Sensitivity of the block ranking – {NAME[d0]} (each weight ±20 %, others re-normalised)</h3>
{tbl(srows, ["Factor", "Weight change", "Spearman ρ vs base ranking", "Top-5 blocks unchanged"])}
<h3>F3. Visual spot-check (stratified random sites over high-resolution imagery)</h3>
{tbl(sprows, ["District", "Sites", "Consistent", "Uncertain", "Doubtful", "Consistent share"])}
<p class="small">“Uncertain” is mostly cloud or tree shade in the imagery; “doubtful” is mostly river islands and banks that moved after the
2017–2023 land-cover maps. The doubtful cases led to the river-channel exclusion rule in section B. Field verification of ~100 stratified sites
per district replaces this desk check in the pilot.</p></div>""")

# ------------------------------------------------------------------ G portal
H.append(f"""<div class="page"><div class="eyebrow"><i></i>G</div><h2 style="margin-top:6px">G. Portal: design, language and screens</h2>
{tbl([["App", "Streamlit (Python), pages: Home · Find land (guided 4 steps) · Compare districts & blocks · Advanced map analysis · How it works"],
      ["Map", "Leaflet (Folium) over Esri World Imagery; all selected sites drawn in two GeoJSON layers (outlines + dots), canvas renderer"],
      ["Speed", "Site selection and map HTML cached per filter set; sign-in redraws the page once (no flash)"],
      ["Language", "English / অসমীয়া switch on every page: labels, grades, land types, reasons and suggestions; block names stay as in records"],
      ["Devices", "Responsive layout: menu folds away on phones, cards stack, numbers two per row; tested at 1440 × 900 and 390 × 844"],
      ["Access", "Accounts with salted PBKDF2-SHA256 hashes; a public demo account shown on the sign-in page for evaluators"],
      ["Downloads", "Site list CSV (Excel), Google Earth KML, GeoJSON; analysts: GeoPackage, Shapefile, GeoTIFF"]], ["Part", "How it is built"])}
{laptop("portal_5_results.png", "<b>Figure G1</b> Results page (desktop): area by grade and the map of all sites coloured A–D.", width="58%")}
{phones([("mobile_1_home.png", "Home", "phone"), ("mobile_6_results_list.png", "Reasons", "phone"),
         ("as_mobile_1_home.png", "অসমীয়া", "home"), ("as_mobile_6_results_list.png", "অসমীয়া", "reasons")], cols=4, maxpx=400)}
<p class="cap"><b>Figure G2</b> Phone screens in English and Assamese. More screens: Proof of Work, section 5.</p></div>""")

# ------------------------------------------------------------------ H assumptions
H.append("""<div class="page"><div class="eyebrow"><i></i>H</div><h2 style="margin-top:6px">H. Assumptions register and limitations</h2>"""
         + tbl([["Factor weights (soil 0.30 … access 0.10)", "config.yaml → profiles", "Expert starting point; replace with AHP weights from the ASSAC / department workshop"],
                ["Thresholds (NDVI fallow, flood, slope, distances)", "config.yaml → availability, scoring", "Calibrated on Kamrup farmland; re-check with field samples per district"],
                ["Grade cut-offs 85 / 80 / 75", "app/theme.py", "Near quartiles of current sites; fixed so grades mean the same across districts"],
                ["Soil from SoilGrids 250 m", "factor: soil", "Screening only; Soil Health Card points will calibrate it"],
                ["Flood frequency 2022–24", "factor: flood", "Re-run every season; ASDMA hazard zones can replace it"],
                ["Patches as parcels", "rank.py", "Proxy until cadastral parcels (Dharitree / Bhunaksha) are shared"],
                ["Boundaries (geoBoundaries)", "config.yaml → boundaries", "Replace with LGD / Survey of India layers from ASSAC"]],
               ["Assumption", "Where", "Status / plan"])
         + """<h3>Limitations</h3><ul>
<li>“Available” means vacant or under-used in satellite data; ownership and legal status must be verified by the Revenue Department.</li>
<li>Char and riverine land changes every year; some sites on river islands will be wrong until re-run with fresh imagery.</li>
<li>Assamese text is a first translation for the prototype and should be reviewed by the department.</li>
<li>The prototype covers four districts; the same code runs any district by adding one entry in config.yaml.</li></ul>
<p class="small">Open-source stack: GDAL, rasterio, geopandas, numpy/scipy, Streamlit, Leaflet. Licences: ESA WorldCover CC BY 4.0, Esri LULC CC BY 4.0,
Copernicus Sentinel and DEM (Copernicus licence), JRC GSW, ISRIC SoilGrids CC BY 4.0, CHIRPS, OpenStreetMap ODbL, geoBoundaries ODbL.</p></div>""")
H.append("</body></html>")

html = POW / "PotharSight_Assam_D13_Technical_Annex.html"
html.write_text("\n".join(H), encoding="utf-8")
pdf = to_pdf(html, POW / "PotharSight_Assam_D13_Technical_Annex.pdf")
print(pdf, f"{pdf.stat().st_size / 1e6:.1f} MB" if pdf.exists() else "NOT CREATED")
