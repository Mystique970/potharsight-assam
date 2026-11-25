"""Pitch deck (16:9 PDF) from current outputs.   python tools/build_deck.py"""
import base64
import io
import json
import subprocess
from pathlib import Path

import pandas as pd
import yaml
from PIL import Image

from doc_style import FONTS, b64

ROOT = Path(__file__).resolve().parents[1]
POW = ROOT / "docs" / "pow"
cfg = yaml.safe_load((ROOT / "config.yaml").read_text())
OUT = ROOT / "outputs"
DIST = [d for d in cfg["districts"] if (OUT / d / "field_crops" / "tables" / "validation.json").exists()]
NAME = {d: cfg["districts"][d]["boundary_name"] + (" (R)" if d == "kamrup" else "") for d in DIST}


def img(p, h="100%", maxpx=1300):
    p = Path(p)
    if not p.exists():
        return ""
    im = Image.open(p).convert("RGB")
    if im.width > maxpx:
        im = im.resize((maxpx, int(im.height * maxpx / im.width)), Image.LANCZOS)
    b = io.BytesIO()
    im.save(b, "JPEG", quality=75)
    return f'<img src="data:image/jpeg;base64,{base64.b64encode(b.getvalue()).decode()}" style="max-height:{h};max-width:100%">'


def lap(p, h="138mm", maxpx=1500):
    return f"<div style='text-align:center'><div class='lap'>{img(p, h, maxpx)}</div></div>"


V = {d: json.loads((OUT / d / "field_crops" / "tables" / "validation.json").read_text()) for d in DIST}
PP = {d: pd.read_csv(OUT / d / "field_crops" / "tables" / "priority_patches.csv") for d in DIST}
BL = {d: pd.read_csv(OUT / d / "field_crops" / "tables" / "blocks_ranking.csv") for d in DIST}

css = """@page { size: 338mm 190mm; margin: 0; }
body { margin: 0; font-family: 'Manrope', 'Noto Sans Bengali', 'Segoe UI', Arial, sans-serif; color: #16231d; }
.s { width: 338mm; height: 190mm; box-sizing: border-box; padding: 14mm 17mm; page-break-after: always; position: relative; overflow: hidden; background: #f6f4ee; }
h1 { font-size: 46pt; font-weight: 800; letter-spacing: -0.03em; margin: 0; line-height: 1.05; }
h2 { font-size: 26pt; font-weight: 800; letter-spacing: -0.02em; margin: 0 0 7mm; }
.eb { display: inline-block; border: 1px solid #e4dfd2; background: #fbfaf6; border-radius: 999px; padding: 3px 12px; font-size: 10pt;
  font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: #3f4b44; margin-bottom: 5mm; }
.eb i { display: inline-block; width: 7px; height: 7px; border-radius: 50%; background: #1d6b3a; margin-right: 7px; vertical-align: 1px; }
p, li { font-size: 15pt; line-height: 1.45; } .big { font-size: 30pt; font-weight: 800; letter-spacing: -0.02em; } .lab { font-size: 12pt; color: #5d6a62; }
.cols { display: flex; gap: 10mm; } .c { flex: 1; }
.k { background: #fff; border: 1px solid #e4dfd2; border-radius: 16px; padding: 4mm 5mm; margin-bottom: 4mm; }
.foot { position: absolute; bottom: 6mm; right: 17mm; font-size: 9.5pt; color: #8a928c; }
.green { background: #f6f4ee; } .green h1 em { font-style: normal; color: #1d6b3a; }
table { border-collapse: collapse; font-size: 13pt; width: 100%; background: #fff; border-radius: 12px; }
th { text-align: left; color: #5d6a62; font-weight: 700; border-bottom: 2px solid #16231d; padding: 6px 8px; font-size: 11.5pt; }
td { border-bottom: 1px solid #e4dfd2; padding: 5px 8px; }
.flow { display: flex; gap: 6px; align-items: stretch; flex-wrap: nowrap; }
.b { flex: 1; border: 1px solid #e4dfd2; background: #fff; border-radius: 14px; padding: 10px 10px; font-size: 13pt; font-weight: 700; }
.b small { display: block; font-weight: 500; color: #5d6a62; font-size: 10.5pt; margin-top: 3px; }
.ar { color: #1d6b3a; font-size: 20pt; font-weight: 800; align-self: center; }
img { border-radius: 10px; }
.lap { background: #1d2420; border-radius: 12px 12px 0 0; padding: 7px; display: inline-block; } .lap img { display: block; border-radius: 3px; }
.ph { background: #18211c; border-radius: 20px; padding: 5px; } .ph img { display: block; width: 100%; border-radius: 15px; }
"""

S = []
foot = '<div class="foot">PotharSight Assam · NESFIC 2026 · D13</div>'
tot_pp = sum(PP[d].area_ha.sum() for d in DIST)
S.append(f"""<div class="s green"><div class="cols" style="align-items:center;height:100%"><div class="c" style="flex:1.15">
<div class="eb"><i></i>NESFIC 2026 · Challenge D13 · DST Assam – ASSAC</div>
<h1 style="font-size:52pt">Find land that can be farmed — <em>and know why.</em></h1>
<p style="font-size:19pt;color:#5d6a62;margin-top:6mm"><b style="color:#16231d">PotharSight Assam</b> · পথাৰছাইট – an open, explainable decision-support portal</p>
<p class="lab">Working prototype on real data · {", ".join(NAME.values())} · web + mobile · English + অসমীয়া</p></div>
<div class="c" style="flex:0.85">{img(POW / 'screens' / 'portal_1_home.png', '120mm', 1300)}</div></div></div>""")
S.append(f"""<div class="s"><h2>The problem</h2><div class="cols"><div class="c">
<p>Assam reports large areas of <b>culturable waste and fallow land</b> – but only as district totals in tables.</p>
<ul><li>Planners cannot see <b>where</b> it is, <b>how suitable</b> it is, or <b>why</b></li>
<li>Satellite, soil, flood and statistics sit with different offices</li><li>Site selection takes weeks and is hard to audit</li>
<li>Programmes are spread thinly instead of targeted</li></ul></div>
<div class="c">{''.join(f'<div class="k"><div class="big">{V[d]["official_vacant_cultivable_ha"]:,} ha</div><div class="lab">vacant cultivable land, {NAME[d]} (DES Assam 2020-21) – location unknown</div></div>' for d in DIST)}
<p class="lab">Users: agriculture & horticulture departments, district administration, land-use planners, KVKs, programme managers</p></div></div>{foot}</div>""")
S.append(f"""<div class="s"><h2>Our solution</h2><div class="flow">
<div class="b">Free satellite & GIS data<br><small>Sentinel-1/2, WorldCover, DEM, soil, rain, OSM</small></div><span class="ar">→</span>
<div class="b">Is it available?<br><small>vacant · long fallow · rabi fallow</small></div><span class="ar">→</span>
<div class="b">Is it suitable?<br><small>6 factors, hard limits, S1–N</small></div><span class="ar">→</span>
<div class="b">Why?<br><small>factor scores, limiting factor, reason</small></div><span class="ar">→</span>
<div class="b">Where first?<br><small>ranked patches, blocks, circles</small></div><span class="ar">→</span>
<div class="b">Dashboard + GIS downloads</div></div>
<div class="cols" style="margin-top:8mm"><div class="c"><ul><li><b>Integrates</b> 9 open layers on one 30 m grid</li>
<li><b>Ranks & classifies</b> against stated FAO-style criteria</li><li><b>Explains</b> every result in plain language</li></ul></div>
<div class="c"><ul><li><b>Downloads</b> GPKG, SHP, GeoJSON, GeoTIFF, CSV</li><li><b>Programme profiles</b>: field crops, horticulture (+ any crop)</li>
<li><b>Live weights</b> – each department asks its own question</li></ul></div></div>{foot}</div>""")
for d in DIST:
    P = OUT / d / "field_crops"
    b = BL[d].head(5)
    rows = "".join(f"<tr><td>{int(r['rank'])}</td><td>{r['name']}</td><td>{r.S1_ha:,.0f}</td><td>{r.S2_ha:,.0f}</td><td>{r.main_limitation}</td></tr>" for _, r in b.iterrows())
    S.append(f"""<div class="s"><h2>Results – {NAME[d]}</h2><div class="cols"><div class="c" style="flex:1.1">{img(P / 'figures' / 'suitability_class.png', '140mm', 1000)}</div>
<div class="c"><div class="k"><div class="big">{PP[d].area_ha.sum():,.0f} ha</div><div class="lab">S1/S2 priority land for field crops · {len(PP[d]):,} patches ≥ 0.5 ha</div></div>
<div class="k"><div class="big">{V[d]['model_vacant_plus_long_fallow_ha']:,} ha</div><div class="lab">satellite vacant + long fallow (official {V[d]['official_vacant_cultivable_ha']:,})</div></div>
<table><tr><th>#</th><th>Block</th><th>S1 ha</th><th>S2 ha</th><th>Main limitation</th></tr>{rows}</table></div></div>{foot}</div>""")
S.append(f"""<div class="s"><div class="eb"><i></i>Live prototype</div><h2>Guided search for officials – four taps to a ranked shortlist</h2>{lap(POW / 'screens' / 'portal_5_results.png', '128mm', 1600)}{foot}</div>""")
SC = POW / "screens"
ph = "".join(f"<div class='c'><div class='ph'><img src='{b64(SC / n, 520)}'></div><p class='lab' style='text-align:center;margin-top:2mm'>{c}</p></div>"
             for n, c in [("mobile_2_district.png", "Step 1 · district"), ("mobile_5_results_map.png", "Map of sites A–D"),
                          ("mobile_6_results_list.png", "Reasons per site"), ("as_mobile_1_home.png", "অসমীয়া · home"),
                          ("as_mobile_6_results_list.png", "অসমীয়া · reasons")] if (SC / n).exists())
S.append(f"""<div class="s"><div class="eb"><i></i>Web + mobile · English + অসমীয়া</div><h2>Works on a field officer's phone, in Assamese</h2>
<div class="cols" style="gap:7mm">{ph}</div>{foot}</div>""")
r0 = PP[DIST[0]].iloc[0]
S.append(f"""<div class="s"><h2>Every result explains itself</h2><div class="cols"><div class="c">{img(POW / 'screens' / 'portal_6_results_list.png', '125mm', 1100)}</div>
<div class="c"><div class="k"><b>Rank 1 · {r0.block} · {r0.area_ha:.1f} ha · {r0.status_name}</b><p>{r0.reason}</p></div>
<ul><li>Six 0–100 factor scores per cell and patch</li><li>Limiting and strongest factor stored as GIS layers</li>
<li>Criteria and data sources recorded → auditable, challengeable decisions</li></ul></div></div>{foot}</div>""")
vrows = "".join(f"<tr><td>{NAME[d]}</td><td>{V[d]['model_vacant_plus_long_fallow_ha']:,} / {V[d]['official_vacant_cultivable_ha']:,} ha</td>"
                f"<td>{100 * V[d]['active_farmland_share_scoring_S1_S2']:.0f} %</td><td>{V[d]['sensitivity_min_rho']}</td></tr>" for d in DIST)
sp = ROOT / "docs" / "spot_check.csv"
spot = ""
if sp.exists():
    s = pd.read_csv(sp)
    per = ", ".join(f"{NAME.get(d, d)} {(g.verdict == 'consistent').sum()}/{len(g)}" for d, g in s.groupby("district", sort=False))
    spot = (f"<p><b>Imagery spot-check:</b> {(s.verdict == 'consistent').sum()} of {len(s)} random priority sites consistent with open / fallow / "
            f"cultivable land ({per}); doubtful cases are mostly shifting river channels – field verification in the pilot.</p>")
S.append(f"""<div class="s"><h2>Validated against evidence</h2><table><tr><th>District</th><th>Satellite vacant + long fallow / official</th>
<th>Active farmland rated S1/S2</th><th>Ranking stability (±20 % weights, min ρ)</th></tr>{vrows}</table>{spot}
<p class="lab">Synthetic end-to-end test, data register and validation report on every run. Pilot: field verification of ~100 stratified patches per district.</p>{foot}</div>""")
S.append(f"""<div class="s"><h2>Built to scale across Assam and beyond</h2><table><tr><th>To add…</th><th>Effort</th></tr>
<tr><td>A new district</td><td>1 line in config.yaml → run</td></tr><tr><td>A new state</td><td>Swap boundary layers (all satellite data is national/global)</td></tr>
<tr><td>A new crop / programme</td><td>New profile: limits + weights</td></tr><tr><td>ASSAC / department data (LULC, Soil Health Card, ASDMA flood, cadastre)</td><td>Replace a layer file – no code change</td></tr></table>
<p><b>Open & low-cost:</b> 100 % free data, open-source stack, runs on a laptop; outputs load into Bhuvan, QGIS, ArcGIS.</p>{foot}</div>""")
S.append(f"""<div class="s"><h2>Roadmap & ask</h2><div class="cols"><div class="c"><table><tr><th>When</th><th>Milestone</th></tr>
<tr><td>Done</td><td>{len(DIST)}-district prototype, guided portal (web + mobile, English + Assamese), GIS exports, validation</td></tr><tr><td>Dec 2026</td><td>Criteria workshop with ASSAC & departments</td></tr>
<tr><td>Jan 2027</td><td>Department data; crop profiles; ML fallow classifier</td></tr><tr><td>Feb 2027</td><td>Demo Day – hosted, field-verification module</td></tr>
<tr><td>Mar 2027</td><td>Ready for field validation</td></tr><tr><td>May 2027</td><td>MVP: 4–6 districts, roles, audit log</td></tr></table></div>
<div class="c"><p><b>We need from the department</b></p><ul><li>ASSAC LULC / wasteland layers and imagery</li><li>Soil Health Card points</li>
<li>Block/circle boundaries, cadastral access</li><li>Field staff to verify a sample of patches</li></ul>
<p class="lab">Decision support only – ownership verified by the Revenue Department before any allocation.</p></div></div>{foot}</div>""")

html = POW / "PotharSight_Assam_D13_Pitch_Deck.html"
html.write_text(f"<html><head><meta charset='utf-8'>{FONTS}<style>{css}</style></head><body>{''.join(S)}</body></html>", encoding="utf-8")
pdf = POW / "PotharSight_Assam_D13_Pitch_Deck.pdf"
subprocess.run([r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", "--headless", "--disable-gpu", "--no-pdf-header-footer", "--virtual-time-budget=15000",
                f"--print-to-pdf={pdf}", html.as_uri()], check=False, timeout=180)
print(pdf, f"{pdf.stat().st_size / 1e6:.1f} MB" if pdf.exists() else "NOT CREATED")
