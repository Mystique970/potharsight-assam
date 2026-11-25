"""How it works – method, data, criteria, validation evidence and scalability."""
import json

import pandas as pd
import streamlit as st

from theme import DISTRICTS, DNAME, OUT, PILOT, ROOT, banner, cfg, fname, footer, h2, tile_html, tr, validation

banner(tr("How PotharSight works", "PotharSight কেনেকৈ কাম কৰে"),
       tr("From free satellite data to a ranked, explained list of sites — and how we checked it.",
          "বিনামূলীয়া উপগ্ৰহ তথ্যৰ পৰা কাৰণসহ ক্ৰমবদ্ধ স্থানৰ তালিকালৈ — আৰু আমি কেনেকৈ পৰীক্ষা কৰিলোঁ।"),
       [tr("9 open data layers", "৯টা মুক্ত তথ্যৰ স্তৰ"), tr("30 m grid", "৩০ মিটাৰ গ্ৰিড"), tr("FAO-style land evaluation", "FAO পদ্ধতিৰ ভূমি মূল্যায়ন"),
        tr("4 validation checks", "৪টা পৰীক্ষা")], eyebrow=tr("Method & evidence", "পদ্ধতি আৰু প্ৰমাণ"))

t1, t2, t3, t4 = st.tabs([f":material/settings: {tr('Method', 'পদ্ধতি')}", f":material/database: {tr('Data sources', 'তথ্যৰ উৎস')}",
                         f":material/verified: {tr('Validation', 'পৰীক্ষা')}", f":material/trending_up: {tr('Scaling up', 'সম্প্ৰসাৰণ')}"])

with t1:
    steps = [("satellite_alt", tr("1 · Collect", "১ · সংগ্ৰহ"), tr("Satellite & open data downloaded automatically", "উপগ্ৰহ আৰু মুক্ত তথ্য স্বয়ংক্ৰিয়ভাৱে ডাউনলোড")),
             ("grid_on", tr("2 · Align", "২ · মিলোৱা"), tr("All layers on one 30 m grid", "সকলো স্তৰ এটা ৩০ মিটাৰ গ্ৰিডত")),
             ("search", tr("3 · Is it free?", "৩ · খালী নে?"), tr("Empty · unused for years · empty in winter", "খালী · বহু বছৰ পতিত · শীতত খালী")),
             ("block", tr("4 · Hard limits", "৪ · কঠোৰ সীমা"), tr("Too steep or floods too often → not suitable", "বেছি এঢলীয়া বা সঘনে বানপানী → উপযুক্ত নহয়")),
             ("tune", tr("5 · Score 6 factors", "৫ · ৬টা কাৰকৰ নম্বৰ"), tr("Soil · water · flood · slope · growth · access", "মাটি · পানী · বান · এঢাল · বৃদ্ধি · পথ")),
             ("label", tr("6 · Grade & explain", "৬ · গ্ৰেড আৰু কাৰণ"), tr("Grade A–D, strongest point and main problem", "গ্ৰেড A–D, সবল দিশ আৰু মূল সমস্যা")),
             ("leaderboard", tr("7 · Rank", "৭ · ক্ৰম"), tr("Sites, blocks and revenue circles", "স্থান, ব্লক আৰু ৰাজহ চক্ৰ"))]
    for row in (steps[:4], steps[4:]):
        cols = st.columns(4)
        for col, (ic, t, d), tone in zip(cols, row, ["green", "amber", "blue", "clay"]):
            col.markdown(tile_html(ic, t, d, tone), unsafe_allow_html=True)
    h2(tr("Criteria (editable in config.yaml, no code change)", "মাপকাঠি (config.yaml-ত সলনি কৰিব পাৰি, ক'ড সলনি নকৰাকৈ)"))
    fc, ho = cfg["profiles"]["field_crops"], cfg["profiles"]["horticulture"]
    st.dataframe(pd.DataFrame([
        ["Hard limit", "Slope; monsoon flood frequency", f"≤{fc['max_slope_pct']} %; ≤{fc['max_flood_freq']}", f"≤{ho['max_slope_pct']} %; ≤{ho['max_flood_freq']}"],
        [fname("soil"), "pH 6.0–7.5 best, organic carbon, nitrogen, CEC, clay (Soil Health Card / ICAR ratings)", fc["weights"]["soil"], ho["weights"]["soil"]],
        [fname("water"), "Rainfall 1500–2500 mm best; distance to river / permanent water", fc["weights"]["water"], ho["weights"]["water"]],
        [fname("flood"), "Share of monsoon radar images showing water (Sentinel-1)", fc["weights"]["flood"], ho["weights"]["flood"]],
        [fname("terrain"), "Slope from 30 m elevation model", fc["weights"]["terrain"], ho["weights"]["terrain"]],
        [fname("productivity"), "Peak greenness (NDVI) in kharif and rabi, 2022–24 (Sentinel-2)", fc["weights"]["productivity"], ho["weights"]["productivity"]],
        [fname("access"), "Distance to roads and towns (OpenStreetMap)", fc["weights"]["access"], ho["weights"]["access"]],
    ], columns=["Factor", "What is measured", "Weight – field crops", "Weight – horticulture"]).astype(str), hide_index=True, use_container_width=True)
    c = cfg["classes"]
    st.caption(f"Suitability classes: S1 ≥ {c['S1']}, S2 ≥ {c['S2']}, S3 ≥ {c['S3']}. A factor below {c['cap_S2_if_any_factor_below']} "
               f"caps a site at S2 (FAO most-limiting-factor rule). Sites shown to officials are S1/S2 land ≥ 0.5 ha, "
               "graded A (≥85), B (80–85), C (75–80), D (<75) by score.")

with t2:
    st.dataframe(pd.DataFrame([
        ["Land cover 2021", "ESA WorldCover", "10 m", "What the land is: crop, grass, forest, water, built-up"],
        ["Land use 2017–2023", "Esri / Impact Observatory", "10 m", "Change over time – land left unused"],
        ["Crop seasons 2022–24", "Sentinel-2 (ESA Copernicus)", "10 m", "Kharif / rabi greenness → fallow land, plant growth"],
        ["Monsoon flooding 2022–24", "Sentinel-1 radar (sees through clouds)", "10 m", "How often land is under water"],
        ["Elevation", "Copernicus DEM", "30 m", "Slope"],
        ["Surface water", "JRC Global Surface Water", "30 m", "Rivers, beels, permanent water"],
        ["Rainfall 2014–23", "CHIRPS", "~5 km", "Water availability"],
        ["Soil (0–30 cm)", "ISRIC SoilGrids 2.0", "250 m", "pH, organic carbon, nitrogen, CEC, clay"],
        ["Roads, towns, rivers, protected areas", "OpenStreetMap", "vector", "Access and exclusions"],
        ["Districts, circles, blocks", "geoBoundaries (LGD-based)", "vector", "Ranking units"],
        ["Land Utilisation Statistics 2020-21", "DES Assam", "district table", "District choice and validation"],
    ], columns=["Layer", "Source (free, no login)", "Detail", "Used for"]), hide_index=True, use_container_width=True)
    st.info("Department data plugs in by replacing a file: ASSAC land-use / wasteland maps, Soil Health Card points, "
            "ASDMA flood zones, Revenue cadastral parcels.")

with t3:
    rows = []
    for d in DISTRICTS:
        v = validation(d)
        q = ROOT / "data" / "interim" / d / "flood_qa.json"
        fq = json.loads(q.read_text()) if q.exists() else {}
        rows.append([DNAME[d], f"{v['model_vacant_plus_long_fallow_ha']:,} / {v['official_vacant_cultivable_ha']:,} ha",
                     v["ratio_model_to_official"], f"{100 * v['active_farmland_share_scoring_S1_S2']:.0f} %",
                     v["sensitivity_min_rho"], "Sentinel-1 radar" if fq.get("s1_used") else "JRC / Esri water history (radar failed QA or not used)"])
    st.dataframe(pd.DataFrame(rows, columns=["District", "Satellite vs official unused land", "Ratio",
                                             "Active farmland rated suitable", "Ranking stability (ρ, ±20 % weights)", "Flood layer used"]),
                 hide_index=True, use_container_width=True)
    st.caption("Ratio below 1 is expected: official culturable waste includes scrub that satellites see as tree cover. "
               "Active farmland rated suitable checks the criteria reward productive land. ρ close to 1 = block ranking does not "
               "depend on exact weights.")
    sc = ROOT / "docs" / "spot_check.csv"
    if sc.exists():
        s = pd.read_csv(sc)
        h2(tr("Spot-check against high-resolution satellite photos", "উচ্চ বিভেদনৰ উপগ্ৰহ চিত্ৰৰ সৈতে নমুনা পৰীক্ষা"))
        cols = st.columns(len(s.district.unique()))
        for col, (d, g) in zip(cols, s.groupby("district", sort=False)):
            vc = g.verdict.value_counts()
            col.metric(f"{DNAME.get(d, d)}: " + tr("sites that look right", "শুদ্ধ যেন লগা স্থান"), f"{vc.get('consistent', 0)} / {len(g)}")
            img = OUT / d / "field_crops" / "spot_check" / "contact_sheet.png"
            if img.exists():
                with col.expander(tr("See all sampled sites", "সকলো নমুনা স্থান চাওক")):
                    st.image(str(img))

with t4:
    st.markdown("""
| To add… | What to do | Code change? |
|---|---|---|
| **A new district** | One entry in `config.yaml`, then `python run_all.py --district <name>` | No |
| **Another state** | Point the boundary files to that state's districts and blocks | No |
| **A new crop or scheme** | Add a profile with its own limits and weights | No |
| **Department data** | Replace a layer file (ASSAC LULC, Soil Health Card, ASDMA flood, cadastre) | No |
""")
    extra = [DNAME[d] for d in DISTRICTS if d not in PILOT]
    if extra:
        st.success(f"Demonstrated: {', '.join(extra)} were added after the first two districts with one configuration line each – same code, no changes.")
    st.markdown("**Limitations stated openly:** soil is modelled at 250 m, not field-tested · 'unused' means satellite-observed, "
                "ownership must be checked by the Revenue Department · sites are a parcel proxy until cadastral maps are shared · "
                "char land changes every year, so the model is re-run each season.")
footer()
