"""Build the Proof of Work PDF from current outputs.   python tools/build_pow.py
Writes docs/pow/PotharSight_Assam_D13_Proof_of_Work.html and .pdf (printed with headless Edge/Chrome).
"""
import base64
import io
import json
import subprocess
from pathlib import Path

import pandas as pd
import yaml
from PIL import Image

from doc_style import CSS as DOC_CSS, FONTS, laptop, phones, to_pdf

ROOT = Path(__file__).resolve().parents[1]
POW = ROOT / "docs" / "pow"
cfg = yaml.safe_load((ROOT / "config.yaml").read_text())
OUT = ROOT / "outputs"
DIST = [d for d in cfg["districts"] if (OUT / d / "field_crops" / "tables" / "validation.json").exists()]
PROFILES = list(cfg["profiles"])


def img(path, width="100%", maxpx=1400, q=72):
    p = Path(path)
    if not p.exists():
        return f'<p class="miss">[missing: {p.name}]</p>'
    im = Image.open(p).convert("RGB")
    if im.width > maxpx:
        im = im.resize((maxpx, int(im.height * maxpx / im.width)), Image.LANCZOS)
    b = io.BytesIO()
    im.save(b, "JPEG", quality=q, optimize=True)
    return f'<img src="data:image/jpeg;base64,{base64.b64encode(b.getvalue()).decode()}" style="width:{width}">'


def table(df, cols=None, n=None):
    d = df[cols] if cols else df
    if n:
        d = d.head(n)
    return d.to_html(index=False, border=0, classes="t", float_format=lambda x: f"{x:,.1f}")


def val(d, p):
    return json.loads((OUT / d / p / "tables" / "validation.json").read_text())


def flow(steps, cls="flow"):
    return f'<div class="{cls}">' + '<span class="arr">→</span>'.join(f'<div class="box">{s}</div>' for s in steps) + "</div>"


css = DOC_CSS + """
.cover { padding-top: 22mm; } .sub { font-size: 12pt; color: #5d6a62; margin: 6px 0 10px; }
.tag { display: inline-block; background: #eef4ec; color: #1d6b3a; padding: 2px 9px; border-radius: 999px; margin: 2px 4px 2px 0; font-size: 8pt; font-weight: 600; }
.reason { background: #f6f4ee; border: 1px solid #e4dfd2; border-radius: 12px; padding: 7px 10px; font-size: 8.8pt; }
h2 { border-bottom: none; }
"""

H = [f"<html><head><meta charset='utf-8'><title>PotharSight Assam – D13 Proof of Work</title>{FONTS}<style>{css}</style></head><body>"]

# ---------------------------------------------------------------- cover
tot = {d: val(d, "field_crops") for d in DIST}
PILOT = ["kamrup", "cachar"]
names = {d: cfg["districts"][d]["boundary_name"] + (" (Rural)" if d == "kamrup" else "") for d in DIST}
H.append(f"""<div class="page cover">
<div class="eyebrow"><i></i>NESFIC 2026 · Stream 1 · Challenge D13 · DST Assam – ASSAC</div>
<h1 style="font-size:34pt;margin-top:14px">PotharSight Assam <span style="color:#1d6b3a;font-weight:700;font-size:20pt">পথাৰছাইট</span></h1>
<div class="sub">Geospatial identification and prioritisation of cultivable & fertile agricultural potential land<br>
<b>Proof of Work</b> – working prototype on real data: {len(DIST)} districts – {", ".join(names[d] for d in DIST[:-1])} and {names[DIST[-1]]}, the top {len(DIST)} in Assam for vacant cultivable land</div><br>
<span class="tag">Suitability maps</span><span class="tag">Parcel (patch) & block prioritisation</span>
<span class="tag">Reasons for every result</span><span class="tag">Downloadable GIS layers</span><span class="tag">Decision-support dashboard</span>
<span class="tag">100 % free, open data</span><span class="tag">New district = one config line</span>
<span class="tag">Web + mobile</span><span class="tag">English + অসমীয়া</span>
<h3>Prototype at a glance</h3><div class="kpi">""")
for d in DIST:
    pp = pd.read_csv(OUT / d / "field_crops" / "tables" / "priority_patches.csv")
    H.append(f'<div class="k"><b>{pp.area_ha.sum():,.0f} ha</b><span>{names[d]}: S1/S2 priority land, {len(pp):,} patches ≥ 0.5 ha (field crops)</span></div>')
    H.append(f'<div class="k"><b>{tot[d]["model_vacant_plus_long_fallow_ha"]:,} ha</b><span>{names[d]}: satellite-observed vacant + long-fallow land '
             f'(official DES 2020-21: {tot[d]["official_vacant_cultivable_ha"]:,} ha)</span></div>')
H.append(f"""</div>
<p><b>What it does.</b> PotharSight Assam combines satellite land cover, Sentinel-2 crop seasons, Sentinel-1 monsoon flooding, soil, terrain,
rainfall, water and road access into one 30 m decision-support layer. It finds land that is <i>available</i> (vacant, long fallow or
rabi fallow), scores how <i>suitable</i> it is for a programme, explains <i>why</i>, and ranks patches, blocks and revenue circles.</p>
<p><b>Contents.</b> 1 Problem and workflow with screens · 2 Architecture and data · 3 Suitability criteria · 4 District results ·
5 Portal screens: desktop, mobile and Assamese · 6 Validation evidence · 7 Scalability, roadmap and limitations.
Formulas, worked example and the full data register are in the separate <b>Technical Annex</b>.</p>
<p class="small">All maps and numbers in this document are produced by the prototype code (Python; outputs/ folder) from open data;
nothing is mocked. Boundaries: geoBoundaries (LGD-based), not authoritative.</p></div>""")

# ---------------------------------------------------------------- 1 problem & journey
H.append("""<div class="page"><h2>1 · Problem and user journey</h2>
<p>Assam's Land Utilisation Statistics report tens of thousands of hectares of culturable waste and fallow land per district, but only
as tables. Programme managers cannot see <b>where</b> that land is, <b>how suitable</b> it is or <b>why</b>; satellite, soil, flood and
statistical data sit with different offices. Site selection is slow, experience-based and hard to audit.</p>
<h3>Users</h3><ul><li>District agriculture and horticulture officers and programme managers (RKVY, MIDH, PMKSY, APART)</li>
<li>District administration, land-use planners, ASSAC GIS analysts</li><li>KVKs and extension agencies (field verification)</li></ul>
<h3>Current vs proposed workflow</h3>""")
H.append("<b>Today</b>" + flow(["Programme target", "Letters to offices for stats, soil, flood info", "Block officers propose sites from experience",
                               "Field visits to many sites", "Weeks; criteria not recorded"]))
H.append("<b>With PotharSight</b>" + flow(["Select district + programme", "See suitability map, ranked blocks & patches", "Read reasons; adjust weights",
                                         "Download shortlist (GPKG/SHP/CSV)", "Field + Revenue check only for shortlist", "Feedback improves model"]))
H.append("<h3>Workflow with screens (phone, 390 × 844)</h3><p>An officer gets from a district to a ranked, explained shortlist in four taps. "
         "The same pages work on desktop and phone, in English or Assamese.</p>")
H.append(phones([("mobile_0_login_signin.png", "<span class='step'>0</span> Sign in", "demo access shown for evaluators"),
                 ("mobile_2_district.png", "<span class='step'>1</span> District", "official unused land shown"),
                 ("mobile_3_purpose.png", "<span class='step'>2</span> What to grow", "field crops or fruits & vegetables"),
                 ("mobile_4_land.png", "<span class='step'>3</span> Type of land", "block, size and grade filters"),
                 ("mobile_5_results_map.png", "<span class='step'>4</span> Map of sites", "all sites coloured A–D"),
                 ("mobile_6_results_list.png", "<span class='step'>5</span> Reasons", "6 factors, watch-outs, suggestion")], cols=6, maxpx=460))
H.append("""<p class="small" style="margin-top:6px">After step 5 the officer downloads the shortlist (Excel, Google Earth KML or GeoJSON) for the field team and the
circle office; field and Revenue checks feed back into the model in the pilot.</p>
<div class="note"><b>Decision support, not decision-making:</b> "available" means vacant or under-used in satellite data. Ownership and legal
status are always verified by the Revenue Department before any allocation.</div></div>""")

# ---------------------------------------------------------------- 2 architecture & data
reg = ROOT / "data" / "data_register.csv"
H.append("<div class='page'><h2>2 · Architecture and data</h2>")
H.append(flow(["<b>Ingest</b><br>STAC / COG windowed reads, fallbacks, data register", "<b>Harmonise</b><br>30 m grid, UTM 46N",
               "<b>Availability</b><br>excluded · vacant · long fallow · rabi fallow · active", "<b>Constraints</b><br>slope, flood",
               "<b>Six factor scores</b><br>0–100", "<b>Suitability</b><br>weighted + limiting-factor cap",
               "<b>Explain & rank</b><br>reasons, patches, blocks, circles", "<b>Validate & serve</b><br>dashboard, GIS exports"]))
H.append("""<p><b>Stack:</b> Python, GDAL/rasterio, geopandas, numpy/scipy, pystac-client; Streamlit + Leaflet (Folium) dashboard; OGC outputs.
Runs on a laptop per district; configuration (districts, thresholds, weights, profiles) is in one YAML file.</p>
<h3>Open data used (all free, no login, scripted download)</h3>
<table class="t"><tr><th>Layer</th><th>Source</th><th>Resolution</th><th>Used for</th></tr>
<tr><td>Land cover 2021</td><td>ESA WorldCover v200</td><td>10 m</td><td>Availability, exclusions</td></tr>
<tr><td>Land use 2017–2023</td><td>Esri / Impact Observatory</td><td>10 m</td><td>Stability, abandonment, built-up</td></tr>
<tr><td>Seasonal NDVI 2022–24 (kharif, rabi)</td><td>Sentinel-2 L2A (Planetary Computer)</td><td>10 m → 30 m</td><td>Fallow detection, productivity</td></tr>
<tr><td>Monsoon flood frequency 2022–24</td><td>Sentinel-1 GRD radar</td><td>10 m → 30 m</td><td>Flood constraint and score</td></tr>
<tr><td>Elevation / slope</td><td>Copernicus GLO-30 DEM</td><td>30 m</td><td>Terrain</td></tr>
<tr><td>Surface water occurrence</td><td>JRC Global Surface Water</td><td>30 m</td><td>Permanent water, distance to water</td></tr>
<tr><td>Annual rainfall 2014–23</td><td>CHIRPS</td><td>~5 km</td><td>Water availability</td></tr>
<tr><td>Soil pH, SOC, N, CEC, clay (0–30 cm)</td><td>ISRIC SoilGrids 2.0</td><td>250 m</td><td>Soil fertility</td></tr>
<tr><td>Roads, towns, rivers, protected areas</td><td>OpenStreetMap</td><td>vector</td><td>Access, water, exclusions</td></tr>
<tr><td>Districts, revenue circles, blocks</td><td>geoBoundaries (LGD-based)</td><td>vector</td><td>AOI and ranking units</td></tr>
<tr><td>Land Utilisation Statistics 2020-21</td><td>DES Assam</td><td>district table</td><td>District selection, validation</td></tr></table>""")
H.append("""<h3>Department data that plugs in for the pilot (requested, not assumed)</h3>
<ul><li>ASSAC: LULC 1:50K, wasteland atlas, high-resolution imagery → replace land-cover and verification layers</li>
<li>Agriculture: Soil Health Card points → calibrate the soil factor · ASDMA: flood hazard zones → flood factor</li>
<li>Revenue: cadastral parcels → patches become parcels; ownership filter · LGD / Survey of India boundaries</li></ul>
<h3>Why these four districts</h3><table class="t"><tr><th>Rank</th><th>District</th><th>Culturable waste</th><th>Current fallow</th><th>Other fallow</th><th>Vacant cultivable (ha)</th></tr>
<tr><td>1</td><td><b>Kamrup (R)</b></td><td>16,231</td><td>7,688</td><td>7,534</td><td><b>31,453</b></td></tr>
<tr><td>2</td><td><b>Cachar</b></td><td>19,165</td><td>2,706</td><td>4,193</td><td><b>26,064</b></td></tr>
<tr><td>3</td><td><b>Lakhimpur</b></td><td>8,670</td><td>7,463</td><td>6,929</td><td><b>23,062</b></td></tr>
<tr><td>4</td><td><b>Dibrugarh</b></td><td>11,064</td><td>6,828</td><td>4,654</td><td><b>22,546</b></td></tr>
<tr><td>5</td><td>Barpeta</td><td>6,503</td><td>9,603</td><td>5,240</td><td>21,346</td></tr></table>
<p class="small">Source: DES Assam Land Utilisation Statistics 2020-21. The four largest pools of vacant cultivable land, full statistics for
validation, and contrasting landscapes: lower Brahmaputra valley with char land (Kamrup), Barak valley with high rainfall and hills (Cachar), and the flood-prone north bank and upper Assam tea belt (Lakhimpur, Dibrugarh). Lakhimpur and Dibrugarh were added after the first two with one config entry each and no code change.</p></div>""")

# ---------------------------------------------------------------- 3 criteria
fc, ho = cfg["profiles"]["field_crops"], cfg["profiles"]["horticulture"]
c = cfg["classes"]
H.append(f"""<div class="page"><h2>3 · Suitability criteria (FAO land-evaluation style, fully configurable)</h2>
<h3>Land availability classes</h3><table class="t"><tr><th>Status</th><th>Rule</th></tr>
<tr><td>Excluded</td><td>Forest, built-up (any of last 3 years), water (JRC ≥ 40 % of time, or water in any yearly Esri map = shifting river channel), wetland, mangrove, protected areas (never proposed)</td></tr>
<tr><td>Vacant open land</td><td>WorldCover grass / shrub, or Esri rangeland, not cropland (bare ground left out: in Assam floodplains it is mostly river sand)</td></tr>
<tr><td>Long fallow / under-used cropland</td><td>Cropland with kharif peak NDVI &lt; {cfg['availability']['fallow_kharif_ndvi_max']}, or cropland now mapped as rangeland</td></tr>
<tr><td>Seasonal (rabi) fallow</td><td>Kharif-cropped land with rabi peak NDVI &lt; {cfg['availability']['fallow_rabi_ndvi_max']} – second-crop opportunity</td></tr>
<tr><td>Active double-cropped</td><td>Not a candidate; used to check that the criteria reward productive land</td></tr></table>
<h3>Hard constraints and weights per programme</h3><table class="t"><tr><th>Factor</th><th>Indicators and scoring (0 → 100)</th><th>Field crops</th><th>Horticulture</th></tr>
<tr><td>Hard limit</td><td>Slope; monsoon flood frequency</td><td>≤ {fc['max_slope_pct']} %; ≤ {fc['max_flood_freq']}</td><td>≤ {ho['max_slope_pct']} %; ≤ {ho['max_flood_freq']}</td></tr>
<tr><td>Soil fertility</td><td>pH optimum 6.0–7.5 (0 at 4.5/8.5), SOC 5→15 g/kg, N 0.5→2.5 g/kg, CEC 5→25, clay optimum 15–35 % (Soil Health Card / ICAR ratings)</td><td>{fc['weights']['soil']}</td><td>{ho['weights']['soil']}</td></tr>
<tr><td>Water availability</td><td>Rainfall optimum 1500–2500 mm; distance to river / permanent water 3 km → 250 m</td><td>{fc['weights']['water']}</td><td>{ho['weights']['water']}</td></tr>
<tr><td>Flood safety</td><td>Share of monsoon radar scenes flooded 0.4 → 0</td><td>{fc['weights']['flood']}</td><td>{ho['weights']['flood']}</td></tr>
<tr><td>Gentle terrain</td><td>Slope 15 % → 2 %</td><td>{fc['weights']['terrain']}</td><td>{ho['weights']['terrain']}</td></tr>
<tr><td>Vegetation productivity</td><td>Seasonal peak NDVI 0.3 → 0.85</td><td>{fc['weights']['productivity']}</td><td>{ho['weights']['productivity']}</td></tr>
<tr><td>Road / market access</td><td>Distance to road 5 km → 250 m; to town 25 km → 3 km</td><td>{fc['weights']['access']}</td><td>{ho['weights']['access']}</td></tr></table>
<p><b>Classes:</b> S1 ≥ {c['S1']} · S2 ≥ {c['S2']} · S3 ≥ {c['S3']} · N below, or failing a hard limit.
<b>Most-limiting-factor rule:</b> any factor below {c['cap_S2_if_any_factor_below']} caps the class at S2, below {c['cap_S3_if_any_factor_below']} at S3.</p>
<p><b>Reasons:</b> for every cell the model stores the six factor scores, the <i>limiting</i> factor (largest weighted shortfall) and the
<i>contributing</i> factor (largest weighted strength); every patch gets a plain-language reason.</p>
<p><b>Prioritisation:</b> contiguous S1/S2 candidate land ≥ {cfg['availability']['min_patch_ha']} ha = priority patch (parcel proxy until cadastral data);
patch priority = 0.8 × mean score + up to 20 points for size; block / circle priority index = (S1 ha + ½ S2 ha) × mean score / 100.</p>
<div class="note">All thresholds, weights and class limits live in <code>config.yaml</code>. Departments can set their own in a workshop
(AHP pair-wise weights) without touching code; the dashboard also lets users test weights live.</div></div>""")

# ---------------------------------------------------------------- 4/5 district results
for i, d in enumerate(DIST):
    P = OUT / d / "field_crops"
    v = val(d, "field_crops")
    vh = val(d, "horticulture") if (OUT / d / "horticulture").exists() else None
    bl = pd.read_csv(P / "tables" / "blocks_ranking.csv")
    pp = pd.read_csv(P / "tables" / "priority_patches.csv")
    H.append(f"<div class='page'><h2>4.{i + 1} · Results – {names[d]}</h2><div class='kpi'>"
             f"<div class='k'><b>{v['model_vacant_plus_long_fallow_ha']:,} ha</b><span>vacant + long fallow (official {v['official_vacant_cultivable_ha']:,})</span></div>"
             f"<div class='k'><b>{v['model_all_candidate_incl_rabi_fallow_ha']:,} ha</b><span>all candidate land incl. rabi fallow</span></div>"
             f"<div class='k'><b>{pp.area_ha.sum():,.0f} ha</b><span>S1/S2 priority patches – field crops ({len(pp):,})</span></div>")
    if vh:
        ph = pd.read_csv(OUT / d / "horticulture" / "tables" / "priority_patches.csv")
        H.append(f"<div class='k'><b>{ph.area_ha.sum():,.0f} ha</b><span>S1/S2 priority patches – horticulture ({len(ph):,})</span></div>")
    H.append("</div><div class='grid2'>" + img(P / "figures" / "land_status.png", maxpx=900) + img(P / "figures" / "suitability_class.png", maxpx=900) + "</div>")
    H.append("<h3>Block prioritisation – field crops (top 8)</h3>" +
             table(bl, ["rank", "name", "candidate_ha", "S1_ha", "S2_ha", "mean_score", "main_limitation", "priority_index"], 8))
    r0 = pp.iloc[0]
    H.append("<h3>Example: top-ranked patch and its reason</h3>"
             f"<div class='reason'><b>Rank 1 · {r0.block} block · {r0.area_ha:.1f} ha · {r0.status_name} · score {r0.mean_score:.1f}</b><br>{r0.reason}<br>"
             f"Factor scores – soil {r0.f_soil:.0f}, water {r0.f_water:.0f}, flood safety {r0.f_flood:.0f}, terrain {r0.f_terrain:.0f}, "
             f"productivity {r0.f_productivity:.0f}, access {r0.f_access:.0f}</div>")
    H.append("</div>")

# ---------------------------------------------------------------- 5 portal screens
H.append("<div class='page'><div class='eyebrow'><i></i>Live prototype</div><h2 style='margin-top:6px'>5 · Portal screens – desktop</h2>"
         "<p>Clean, plain-language pages for officials; flat icons; English / Assamese switch on every page. Sign-in shows demo access for "
         "evaluators. Captured at 1440 × 900.</p>"
         + laptop("portal_0_login.png", "<b>Figure 5.1</b> Sign-in with public demo access, headline numbers and the language switch.", width="86%")
         + laptop("portal_1_home.png", "<b>Figure 5.2</b> Home: totals for the four districts, one tile per task and one card per district.", width="86%")
         + "</div>")
H.append("<div class='page'><h2>5 · Portal screens – desktop (continued)</h2>"
         + laptop("portal_5_results.png", "<b>Figure 5.3</b> Results for Cachar, field crops: area by grade A–D and the map of all sites, coloured by grade.", width="86%")
         + laptop("portal_6_results_list.png", "<b>Figure 5.4</b> Best sites with reasons: six-factor profile, strong points, watch-outs, a site-specific "
                  "suggestion and a Google Maps link.", width="86%") + "</div>")
H.append("<div class='page'><h2>5 · Portal screens – desktop (continued)</h2><div class='grid2'>"
         + "<div>" + laptop("portal_7_results_blocks.png", "<b>Figure 5.5</b> Compare blocks inside the search: area by grade and main problem.") + "</div>"
         + "<div>" + laptop("portal_8_rankings.png", "<b>Figure 5.6</b> Cross-district block ranking with downloads.") + "</div>"
         + "<div>" + laptop("portal_9_analyst.png", "<b>Figure 5.7</b> Advanced map analysis for GIS staff: S1–N classes, live weights, GIS exports.") + "</div>"
         + "<div>" + laptop("portal_11_validation.png", "<b>Figure 5.8</b> How it works & validation: method, data, accuracy checks.") + "</div>"
         + "</div><h3>Assamese (অসমীয়া)</h3><div class='grid2'>"
         + "<div>" + laptop("as_1_home.png", "<b>Figure 5.9</b> Home in Assamese.") + "</div>"
         + "<div>" + laptop("as_6_results_list.png", "<b>Figure 5.10</b> Site reasons and suggestions in Assamese.") + "</div></div></div>")
H.append("<div class='page'><h2>5 · Portal screens – mobile</h2><p>The portal is responsive: on a phone the menu folds away, cards stack and numbers "
         "sit two per row. Captured at 390 × 844 (a common Android / iPhone size).</p>"
         + phones([("mobile_0_login.png", "Sign-in", "headline and numbers"), ("mobile_1_home.png", "Home", "tasks and districts"),
                   ("mobile_2_district.png", "Step 1", "choose district"), ("mobile_5_results.png", "Results", "area by grade"),
                   ("mobile_5_results_map.png", "Map", "all sites, A–D"), ("mobile_6_results_list.png", "Reasons", "per-site profile"),
                   ("as_mobile_1_home.png", "অসমীয়া", "home in Assamese"), ("as_mobile_6_results_list.png", "অসমীয়া", "reasons in Assamese")],
                  cols=4, maxpx=520)
         + "<p class='cap'><b>Figure 5.11</b> Mobile screens of the prototype (English and Assamese).</p></div>")

# ---------------------------------------------------------------- 7 validation
H.append("<div class='page'><h2>6 · Validation evidence</h2><table class='t'><tr><th>Check</th>" +
         "".join(f"<th>{names[d]} – field crops</th>" for d in DIST) + "<th>Interpretation</th></tr>")
rows = [("Satellite vacant + long fallow vs DES 2020-21", lambda v: f"{v['model_vacant_plus_long_fallow_ha']:,} vs {v['official_vacant_cultivable_ha']:,} ha (ratio {v['ratio_model_to_official']})",
         "Same order of magnitude. Lower than DES because DES culturable waste includes scrub that satellite maps as tree cover, and current fallow varies by year."),
        ("Incl. rabi fallow (second-crop opportunity)", lambda v: f"{v['model_all_candidate_incl_rabi_fallow_ha']:,} ha", "Additional seasonal opportunity not in DES totals"),
        ("Active double-cropped land rated S1/S2", lambda v: f"{100 * v['active_farmland_share_scoring_S1_S2']:.0f} %", "Criteria reward land that is actually productive"),
        ("Block ranking under ±20 % weight change", lambda v: f"min Spearman ρ {v['sensitivity_min_rho']}; top-5 overlap {v['sensitivity_mean_top5_overlap']}/5", "Priorities are robust to the exact weights")]
for lab, fn, interp in rows:
    H.append(f"<tr><td>{lab}</td>" + "".join(f"<td>{fn(tot[d])}</td>" for d in DIST) + f"<td>{interp}</td></tr>")
H.append("</table>")
qa = []
for d in DIST:
    q = ROOT / "data" / "interim" / d / "flood_qa.json"
    if q.exists():
        j = json.loads(q.read_text())
        qa.append(f"{names[d]}: median radar flood frequency on cropland {j['s1_median_cropland_flood_freq']:.2f} → "
                  + ("Sentinel-1 layer used" if j["s1_used"] else "failed the gate (waterlogged paddy read as flood) → JRC/Esri flood proxy used"))
if qa:
    H.append("<div class='note'><b>Automatic data-quality gate (flood layer).</b> Ordinary cropland should not look flooded in most monsoon "
             "radar scenes. " + " · ".join(qa) + ". Each run records which source was used.</div>")
for d in DIST:
    sp = OUT / d / "field_crops" / "spot_check"
    if (sp / "sample.csv").exists():
        s = pd.read_csv(sp / "sample.csv")
        vc = s.verdict.value_counts()
        H.append(f"<h3>Visual spot-check – {names[d]}: {len(s)} stratified random priority patches over high-resolution imagery</h3>"
                 f"<p><b>{vc.get('consistent', 0)}</b> consistent with open / fallow / cultivable land, <b>{vc.get('uncertain', 0)}</b> uncertain "
                 f"({'; '.join(sorted(set(s.loc[s.verdict == 'uncertain', 'note'])))}), <b>{vc.get('doubtful', 0)}</b> doubtful "
                 f"({'; '.join(sorted(set(s.loc[s.verdict == 'doubtful', 'note'])))}). "
                 f"Field verification in the pilot replaces this desk check; doubtful cases guide the next calibration.</p>"
                 + img(sp / "contact_sheet.png", maxpx=1100, q=65))
H.append("<p class='small'>Development testing: an automated synthetic end-to-end test (tests/test_pipeline_synthetic.py), per-layer "
         "fetch-status logs, a data register and a validation report on every run.</p></div>")

# ---------------------------------------------------------------- 8 scalability, roadmap, limitations
H.append("""<div class="page"><h2>7 · Scalability, roadmap and limitations</h2>
<h3>Replicable by configuration</h3><table class="t"><tr><th>To add…</th><th>Do this</th><th>Code change?</th></tr>
<tr><td>A district in Assam</td><td>Add one entry under <code>districts</code> in config.yaml; <code>python run_all.py --district &lt;name&gt;</code></td><td>No</td></tr>
<tr><td>Another state</td><td>Point <code>boundaries</code> to that state's district/block layers (all satellite sources are national/global)</td><td>No</td></tr>
<tr><td>A crop or programme</td><td>Add a profile: slope/flood limits, weights (e.g. tea, citrus, banana, rabi mustard, pulses)</td><td>No</td></tr>
<tr><td>Department data</td><td>Replace a layer file (ASSAC LULC, Soil Health Card, ASDMA flood, cadastral parcels)</td><td>No</td></tr>
<tr><td>Statewide service</td><td>Scheduled seasonal re-run on SDC/ASSAC server; GeoServer WMS/WFS</td><td>Deployment only</td></tr></table>
<h3>Roadmap (NESFIC timeline)</h3><table class="t"><tr><th>When</th><th>Milestone</th></tr>
<tr><td>Done (Nov 2026)</td><td>Four-district working prototype; guided portal (web + mobile, English + Assamese); GIS exports; validation</td></tr>
<tr><td>Dec 2026</td><td>Criteria and weights workshop with ASSAC and agriculture/horticulture officers</td></tr>
<tr><td>Dec 2026 – Jan 2027</td><td>Integrate ASSAC / department layers; crop-specific profiles; ML fallow classifier on verified samples</td></tr>
<tr><td>Feb 2027 – Demo Day</td><td>Hosted dashboard, field-verification module</td></tr>
<tr><td>Mar 2027 – ready for validation</td><td>Field verification of ~100 stratified patches in each of the four districts</td></tr>
<tr><td>Apr – May 2027 (MVP)</td><td>Accuracy report, re-calibration, 4–6 districts, user roles and audit log</td></tr></table>
<h3>Limitations stated openly</h3><ul>
<li>Soil is modelled (SoilGrids, 250 m), not field-tested – a screening layer until Soil Health Card / NBSS&LUP data are shared.</li>
<li>"Available" = satellite-observed vacant or under-used; ownership and legal status need Revenue Department verification.</li>
<li>Patches are a parcel proxy; cadastral parcels (Dharitree/Bhunaksha) are not public.</li>
<li>Char and riverine land changes every year; flood frequency uses 2022–24 radar and should be re-run each season.</li>
<li>geoBoundaries are LGD-based but not authoritative; official boundaries replace them in the pilot.</li></ul>
<p class="small">Open-source stack (GDAL, rasterio, geopandas, Streamlit, Leaflet). Data licences: ESA WorldCover CC BY 4.0, Esri LULC CC BY 4.0,
Copernicus DEM and Sentinel (Copernicus licence), JRC GSW, ISRIC SoilGrids CC BY 4.0, CHIRPS, OpenStreetMap ODbL, geoBoundaries ODbL.</p></div>""")
H.append("</body></html>")

POW.mkdir(parents=True, exist_ok=True)
html = POW / "PotharSight_Assam_D13_Proof_of_Work.html"
html.write_text("\n".join(H), encoding="utf-8")
pdf = POW / "PotharSight_Assam_D13_Proof_of_Work.pdf"
to_pdf(html, pdf)
print(pdf, f"{pdf.stat().st_size / 1e6:.1f} MB" if pdf.exists() else "NOT CREATED")
