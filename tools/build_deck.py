"""Pitch deck (16:9 PDF) from current outputs.   python tools/build_deck.py"""
import base64
import io
import json
import subprocess
from pathlib import Path

import pandas as pd
import yaml
from PIL import Image

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


V = {d: json.loads((OUT / d / "field_crops" / "tables" / "validation.json").read_text()) for d in DIST}
PP = {d: pd.read_csv(OUT / d / "field_crops" / "tables" / "priority_patches.csv") for d in DIST}
BL = {d: pd.read_csv(OUT / d / "field_crops" / "tables" / "blocks_ranking.csv") for d in DIST}

css = """@page { size: 338mm 190mm; margin: 0; } body { margin: 0; font-family: 'Segoe UI', Arial, sans-serif; color: #1d2a22; }
.s { width: 338mm; height: 190mm; box-sizing: border-box; padding: 13mm 16mm; page-break-after: always; position: relative; overflow: hidden; }
h1 { font-size: 40pt; color: #14532d; margin: 0; } h2 { font-size: 25pt; color: #14532d; margin: 0 0 7mm; border-left: 8px solid #1a9850; padding-left: 10px; }
p, li { font-size: 15pt; line-height: 1.4; } .big { font-size: 34pt; font-weight: 700; color: #14532d; } .lab { font-size: 12.5pt; color: #4b5563; }
.cols { display: flex; gap: 10mm; } .c { flex: 1; } .k { background: #f0fdf4; border-left: 6px solid #1a9850; padding: 4mm 5mm; margin-bottom: 4mm; }
.foot { position: absolute; bottom: 6mm; right: 16mm; font-size: 10pt; color: #6b7280; } .green { background: #14532d; color: white; }
.green h1, .green h2, .green .big { color: white; } .green .lab { color: #d1fae5; } table { border-collapse: collapse; font-size: 13pt; width: 100%; }
th { background: #14532d; color: white; text-align: left; padding: 5px 8px; } td { border-bottom: 1px solid #e5e7eb; padding: 4px 8px; }
.flow { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; } .b { border: 2px solid #1a9850; background: #f0fdf4; border-radius: 8px;
padding: 8px 10px; font-size: 13pt; text-align: center; } .ar { color: #1a9850; font-size: 20pt; font-weight: bold; }"""

S = []
foot = '<div class="foot">PotharSight Assam · NESFIC 2026 · D13</div>'
tot_pp = sum(PP[d].area_ha.sum() for d in DIST)
S.append(f"""<div class="s green"><div style="margin-top:28mm"><div class="lab">NESFIC 2026 · Challenge D13 · DST Assam – ASSAC</div>
<h1 style="font-size:54pt">PotharSight Assam</h1><p style="font-size:21pt">Find, rank and explain cultivable & fertile land –<br>
an open, explainable spatial decision-support layer</p><p class="lab">Working prototype on real data · {", ".join(NAME.values())}</p></div></div>""")
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
S.append(f"""<div class="s"><h2>PotharSight portal – guided search for officials (working)</h2>{img(POW / 'screens' / 'portal_5_results_map.png', '150mm', 1600)}{foot}</div>""")
r0 = PP[DIST[0]].iloc[0]
S.append(f"""<div class="s"><h2>Every result explains itself</h2><div class="cols"><div class="c">{img(POW / 'screens' / 'portal_6_results_list.png', '130mm', 1100)}</div>
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
<tr><td>Done</td><td>{len(DIST)}-district prototype, guided portal, GIS exports, validation</td></tr><tr><td>Dec 2026</td><td>Criteria workshop with ASSAC & departments</td></tr>
<tr><td>Jan 2027</td><td>Department data; crop profiles; ML fallow classifier</td></tr><tr><td>Feb 2027</td><td>Demo Day – hosted, field-verification module</td></tr>
<tr><td>Mar 2027</td><td>Ready for field validation</td></tr><tr><td>May 2027</td><td>MVP: 4–6 districts, roles, audit log</td></tr></table></div>
<div class="c"><p><b>We need from the department</b></p><ul><li>ASSAC LULC / wasteland layers and imagery</li><li>Soil Health Card points</li>
<li>Block/circle boundaries, cadastral access</li><li>Field staff to verify a sample of patches</li></ul>
<p class="lab">Decision support only – ownership verified by the Revenue Department before any allocation.</p></div></div>{foot}</div>""")

html = POW / "PotharSight_Assam_D13_Pitch_Deck.html"
html.write_text(f"<html><head><meta charset='utf-8'><style>{css}</style></head><body>{''.join(S)}</body></html>", encoding="utf-8")
pdf = POW / "PotharSight_Assam_D13_Pitch_Deck.pdf"
subprocess.run([r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", "--headless", "--disable-gpu", "--no-pdf-header-footer",
                f"--print-to-pdf={pdf}", html.as_uri()], check=False, timeout=180)
print(pdf, f"{pdf.stat().st_size / 1e6:.1f} MB" if pdf.exists() else "NOT CREATED")
