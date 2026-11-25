"""Find land for farming – guided, plain-language search for officials (English / Assamese)."""
import os
import tempfile

import folium
import geopandas as gpd
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from theme import (DISTRICTS, DNAME, GRADES, LAND_TYPE, PURPOSE, advice, banner, bars, desc, factor_bars_html, footer,
                   grade_name, h2, icon, lang, legend_html, line, load_patches, problem, reasons, tr, validation)

ss = st.session_state
ss.setdefault("step", 1)
HA = tr("ha", "হেক্টৰ")
ALL = "All blocks"  # internal value; shown translated

banner(tr("Find land for farming", "খেতিৰ মাটি বিচাৰক"),
       tr("Answer three questions. PotharSight shows where suitable unused land is, how much, and why.",
          "তিনিটা প্ৰশ্নৰ উত্তৰ দিয়ক। PotharSight-এ উপযুক্ত অব্যৱহৃত মাটি ক'ত, কিমান আৰু কিয় দেখুৱায়।"),
       eyebrow=tr("Guided search", "নিৰ্দেশিত সন্ধান"))

labels = [tr("District", "জিলা"), tr("What to grow", "কি খেতি"), tr("Type of land", "মাটিৰ প্ৰকাৰ"), tr("Results", "ফলাফল")]
st.markdown("<div class='ps-steps'>" + "".join(
    f"<div class='ps-step {'on' if i + 1 == ss.step else 'done' if i + 1 < ss.step else ''}'>{i + 1} · {l}</div>"
    for i, l in enumerate(labels)) + "</div>", unsafe_allow_html=True)


def go(step):
    ss.step = step
    st.rerun()


def to_kml(gdf) -> bytes:
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, "sites.kml")
        gdf.to_file(p, driver="KML")
        return open(p, "rb").read()


def block_label(b):
    return tr("All blocks", "সকলো ব্লক") if b == ALL else b


@st.cache_data(show_spinner=False, max_entries=32)
def select_sites(d, prof, types, block, min_ha, grades):
    patches, _ = load_patches(d, prof)
    sel = patches[patches.land_status.isin(types) & (patches.area_ha >= min_ha) & patches.grade.isin(grades)]
    if block != ALL:
        sel = sel[sel.block == block]
    sel = sel.sort_values("priority", ascending=False).reset_index(drop=True)
    sel["site_no"] = range(1, len(sel) + 1)
    return sel


@st.cache_data(show_spinner=False, max_entries=32)
def site_map(d, prof, types, block, min_ha, grades, ui_lang):
    """All selected sites in two layers (outlines + dots) – fast even with 4,000 sites, every grade colour shown."""
    import shapely
    sel = select_sites(d, prof, types, block, min_ha, grades)
    _, blocks = load_patches(d, prof)
    b = sel.total_bounds
    fm = folium.Map(location=[(b[1] + b[3]) / 2, (b[0] + b[2]) / 2], zoom_start=10, tiles=None, prefer_canvas=True)
    fm.fit_bounds([[b[1], b[0]], [b[3], b[2]]])
    folium.TileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                     attr="Esri World Imagery", name=tr("Satellite photo", "উপগ্ৰহ চিত্ৰ")).add_to(fm)
    folium.TileLayer("OpenStreetMap", name=tr("Street map", "পথৰ মানচিত্ৰ"), show=False).add_to(fm)
    bl = blocks if block == ALL else blocks[blocks.name == block]
    folium.GeoJson(bl[["name", "geometry"]], name=tr("Blocks", "ব্লক"),
                   style_function=lambda f: {"fill": False, "color": "#ffffff", "weight": 1.6},
                   tooltip=folium.GeoJsonTooltip(["name"], aliases=[tr("Block", "ব্লক")])).add_to(fm)
    s = sel.iloc[::-1].copy()  # best sites drawn last (on top)
    site, grd = tr("Site", "স্থান"), tr("Grade", "গ্ৰেড")
    s["tip"] = [f"{site} {n}: {grd} {g} · {grade_name(g)}, {a:.1f} {HA} – " + tr("click for details", "বিৱৰণৰ বাবে ক্লিক কৰক")
                for n, g, a in zip(s.site_no, s.grade, s.area_ha)]
    pops = []
    for _, r in s.iterrows():
        good, watch = reasons(r)
        pops.append(f"<div style='min-width:260px;font-family:Manrope,Nirmala UI,sans-serif'><b>{site} {r.site_no}</b> · {r.block} {tr('block', 'ব্লক')}<br>"
                    f"<span style='background:{r.grade_col};color:#fff;padding:1px 8px;border-radius:9px'>{grd} {r.grade} · {grade_name(r.grade)}</span> "
                    f"{r.area_ha:.1f} {HA}<br>{LAND_TYPE[int(r.land_status)][1]} · "
                    + tr(f"better than {100 * r.pct_rank:.0f}% of sites in the district", f"জিলাৰ {100 * r.pct_rank:.0f}% স্থানতকৈ ভাল") + "<br>"
                    + (f"✓ {', '.join(good)}<br>" if good else "") + "".join(f"! {w}<br>" for w in watch)
                    + f"→ {advice(r, prof)}<br><a href='https://www.google.com/maps?q={r.lat},{r.lon}' target='_blank'>"
                    + tr("Open in Google Maps", "Google Mapsত খোলক") + "</a></div>")
    s["popup"] = pops
    s["col"] = s.grade_col
    s["r"] = [7 if n <= 20 else 4.5 for n in s.site_no]
    poly = s[["tip", "col", "geometry"]].copy()
    poly["geometry"] = shapely.set_precision(poly.geometry.simplify(0.0003).values, 1e-5)
    folium.GeoJson(poly, name=tr("Site outlines", "স্থানৰ সীমা"), tooltip=folium.GeoJsonTooltip(["tip"], labels=False),
                   style_function=lambda f: {"color": "#ffffff", "weight": 0.6, "fillColor": f["properties"]["col"], "fillOpacity": 0.85}
                   ).add_to(fm)
    pts = gpd.GeoDataFrame(s[["tip", "popup", "col", "r"]].copy(), geometry=gpd.points_from_xy(s.lon, s.lat), crs=4326)
    folium.GeoJson(pts, name=tr("Site dots", "স্থানৰ বিন্দু"), marker=folium.CircleMarker(radius=4.5, weight=1.2, fill=True, fill_opacity=1),
                   style_function=lambda f: {"color": "#ffffff", "fillColor": f["properties"]["col"], "radius": f["properties"]["r"]},
                   tooltip=folium.GeoJsonTooltip(["tip"], labels=False),
                   popup=folium.GeoJsonPopup(["popup"], labels=False, max_width=360)).add_to(fm)
    folium.LayerControl().add_to(fm)
    return fm.get_root().render()


if ss.step == 1:
    h2(tr("Which district are you planning for?", "কোন জিলাৰ বাবে পৰিকল্পনা কৰিছে?"))
    cols = st.columns(len(DISTRICTS))
    for col, d in zip(cols, DISTRICTS):
        v = validation(d)
        with col.container(border=True, height="stretch"):
            st.markdown(f"<div class='ps-ic'>{icon('location_on')}</div><div style='font-weight:800;font-size:1.15rem'>{DNAME[d]}</div>"
                        f"<div style='color:#5d6a62;font-size:0.84rem;margin:3px 0 10px 0;line-height:1.45'>{desc(d)}</div>"
                        f"<div style='font-size:0.86rem;color:#45524a'>" + tr("Official unused cultivable land", "চৰকাৰী হিচাপত অব্যৱহৃত খেতিযোগ্য মাটি")
                        + f"</div><div style='font-weight:800;font-size:1.3rem'>{v['official_vacant_cultivable_ha']:,} {HA}</div>",
                        unsafe_allow_html=True)
            st.markdown("<div class='ps-card-end'></div>", unsafe_allow_html=True)
            if st.button(tr("Choose", "বাছক"), key=f"d_{d}", type="primary", use_container_width=True):
                ss.district = d
                go(2)

elif ss.step == 2:
    h2(tr(f"What do you want to grow in {DNAME[ss.district]}?", f"{DNAME[ss.district]}ত কি খেতি কৰিব বিচাৰে?"))
    cols = st.columns(len(PURPOSE))
    for col, (k, (ic, lab, dsc)) in zip(cols, PURPOSE.items()):
        with col.container(border=True, height="stretch"):
            st.markdown(f"<div class='ps-ic'>{icon(ic)}</div><div style='font-weight:800;font-size:1.2rem'>{lab}</div>"
                        f"<div style='color:#5d6a62;font-size:0.92rem;margin-top:4px'>{dsc}</div>", unsafe_allow_html=True)
            st.markdown("<div class='ps-card-end'></div>", unsafe_allow_html=True)
            if st.button(tr(f"Select {lab}", f"{lab} বাছক"), key=f"p_{k}", type="primary", use_container_width=True):
                ss.purpose = k
                go(3)
    if st.button(tr("Back", "উভতি যাওক"), icon=":material/arrow_back:"):
        go(1)

elif ss.step == 3:
    patches, blocks = load_patches(ss.district, ss.purpose)
    h2(tr("What kind of land are you looking for?", "কেনেধৰণৰ মাটি বিচাৰিছে?"))
    cols = st.columns(3)
    picked = []
    for col, (k, (ic, lab, dsc)) in zip(cols, LAND_TYPE.items()):
        with col.container(border=True, height="stretch"):
            n = int((patches.land_status == k).sum())
            st.markdown(f"<div class='ps-ic'>{icon(ic)}</div>", unsafe_allow_html=True)
            if st.checkbox(f"**{lab}**", value=k in ss.get("types", [1, 2, 3]), key=f"t_{k}"):
                picked.append(k)
            st.caption(f"{dsc} · {n:,} " + tr("sites", "টা স্থান"))
    c1, c2, c3 = st.columns(3)
    blk_opts = [ALL] + sorted(b for b in patches.block.unique() if b != "outside block layer")
    blk = c1.selectbox(tr("In which block?", "কোন ব্লকত?"), blk_opts, format_func=block_label,
                       index=blk_opts.index(ss.block) if ss.get("block") in blk_opts else 0)
    size = c2.select_slider(tr("Smallest site", "আটাইতকৈ সৰু স্থান"), options=[0.5, 1, 2, 5, 10, 20], value=ss.get("min_ha", 1),
                            format_func=lambda x: f"{x} {HA}")
    gkeys = [g for _, g, _, _ in GRADES]
    gsel = c3.multiselect(tr("Grades to include", "কোন গ্ৰেড লাগে"), gkeys, default=ss.get("grades", gkeys),
                          format_func=lambda g: f"{g} · {grade_name(g)}")
    b1, b2 = st.columns([1, 4])
    if b1.button(tr("Back", "উভতি যাওক"), icon=":material/arrow_back:"):
        go(2)
    if b2.button(tr("Show me the land", "মাটি দেখুৱাওক"), icon=":material/travel_explore:", type="primary",
                 disabled=not picked or not gsel):
        ss.types, ss.block, ss.min_ha, ss.grades = picked, blk, size, gsel
        go(4)

else:
    d, prof = ss.district, ss.purpose
    patches, blocks = load_patches(d, prof)
    gl = tuple(g.split(" · ")[0] for g in ss.get("grades", [g for _, g, _, _ in GRADES]))
    key = (d, prof, tuple(ss.types), ss.block, ss.min_ha, gl)
    sel = select_sites(*key)
    where = (ss.block + " " + tr("block", "ব্লক")) if ss.block != ALL else DNAME[d]
    ic, plab, _ = PURPOSE[prof]

    h1, h2c = st.columns([5, 1.3], vertical_alignment="center")
    h1.markdown(f"<div style='font-weight:800;font-size:1.45rem'>{icon(ic, 'lg')} " + tr(f"{plab} in {where}", f"{where}ত {plab}") + "</div>",
                unsafe_allow_html=True)
    if h2c.button(tr("New search", "নতুন সন্ধান"), icon=":material/refresh:", use_container_width=True):
        go(1)
    if sel.empty:
        st.warning(tr("No sites match. Try a smaller minimum size, another block, or more land types / grades.",
                      "কোনো স্থান মিলা নাই। সৰু আকাৰ, বেলেগ ব্লক বা অধিক মাটিৰ প্ৰকাৰ / গ্ৰেড বাছি চাওক।"))
        st.stop()

    m = st.columns(6)
    m[0].metric(tr("Sites found", "পোৱা স্থান"), f"{len(sel):,}")
    m[1].metric(tr("Total area", "মুঠ মাটি"), f"{sel.area_ha.sum():,.0f} {HA}")
    for i, (_, g, n, col) in enumerate(GRADES):
        m[2 + i].metric(f"{tr('Grade', 'গ্ৰেড')} {g} · {n}", f"{sel.loc[sel.grade == g, 'area_ha'].sum():,.0f} {HA}")
    st.markdown(legend_html(), unsafe_allow_html=True)

    tab_map, tab_list, tab_blocks = st.tabs([f":material/map: {tr('Map of sites', 'স্থানৰ মানচিত্ৰ')}",
                                             f":material/format_list_bulleted: {tr('Best sites, with reasons', 'শ্ৰেষ্ঠ স্থান, কাৰণসহ')}",
                                             f":material/bar_chart: {tr('Compare blocks', 'ব্লক তুলনা')}"])
    with tab_map:
        with st.spinner(tr("Drawing the map…", "মানচিত্ৰ অঁকা হৈছে…")):
            components.html(site_map(*key, lang()), height=600)
        st.caption(tr(f"All {len(sel):,} sites, coloured by grade (the top 20 have bigger dots). Zoom in to see site outlines; "
                      "click a dot for details. Use the layer button (top right) to switch to a street map.",
                      f"গ্ৰেড অনুসৰি ৰং দিয়া সকলো {len(sel):,}টা স্থান (শীৰ্ষ ২০টাৰ বিন্দু ডাঙৰ)। সীমা চাবলৈ জুম কৰক; বিৱৰণৰ বাবে বিন্দুত "
                      "ক্লিক কৰক। ওপৰৰ সোঁফালৰ বুটামেৰে পথৰ মানচিত্ৰলৈ সলনি কৰিব পাৰি।"))

    with tab_list:
        n = st.select_slider(tr("Sites to show", "দেখুৱাবলগীয়া স্থান"), [10, 25, 50, 100], value=10)
        for _, r in sel.head(n).iterrows():
            good, watch = reasons(r)
            with st.container(border=True):
                a, b2 = st.columns([4, 1])
                a.markdown(f"<div style='font-weight:800;font-size:1.12rem'>{tr('Site', 'স্থান')} {r.site_no} · {r.block} {tr('block', 'ব্লক')} "
                           f"&nbsp;<span class='ps-badge' style='background:{r.grade_col}'>{tr('Grade', 'গ্ৰেড')} {r.grade} · {grade_name(r.grade)}</span></div>",
                           unsafe_allow_html=True)
                lt = LAND_TYPE[int(r.land_status)]
                a.markdown(f"<div style='color:#45524a;font-size:0.9rem;margin-top:2px'><b>{r.area_ha:.1f} {HA}</b> · {lt[1]}"
                           + (f" · {tr('Revenue circle', 'ৰাজহ চক্ৰ')}: {r.circle}" if isinstance(r.get("circle"), str) else "")
                           + " · " + tr(f"score {r.mean_score:.0f}/100 – better than <b>{100 * r.pct_rank:.0f}%</b> of sites in {DNAME[d]}",
                                        f"নম্বৰ {r.mean_score:.0f}/100 — {DNAME[d]}ৰ <b>{100 * r.pct_rank:.0f}%</b> স্থানতকৈ ভাল") + "</div>",
                           unsafe_allow_html=True)
                a.markdown(factor_bars_html(r), unsafe_allow_html=True)
                html = ""
                if good:
                    html += line("check_circle", f"<b>{tr('Strong points', 'সবল দিশ')}:</b> " + ", ".join(good))
                for w in watch:
                    html += line("warning", f"<b>{tr('Watch out', 'সাৱধান')}:</b> {w}", "warn")
                html += line("lightbulb", f"<b>{tr('Suggestion', 'পৰামৰ্শ')}:</b> {advice(r, prof)}", "tip")
                a.markdown(html, unsafe_allow_html=True)
                b2.link_button("Google Maps", f"https://www.google.com/maps?q={r.lat},{r.lon}", icon=":material/map:", use_container_width=True)
                b2.caption(f"{r.lat:.5f} N  \n{r.lon:.5f} E")

    with tab_blocks:
        base = patches[patches.land_status.isin(ss.types) & (patches.area_ha >= ss.min_ha) & patches.grade.isin(gl)]
        g = base.pivot_table(index="block", columns="grade", values="area_ha", aggfunc="sum", fill_value=0)
        g = g.reindex(columns=[x[1] for x in GRADES], fill_value=0)
        g = g[g.index != "outside block layer"]
        g["total"] = g.sum(1)
        g = g.sort_values("total", ascending=False)
        top = g.head(12)[[x[1] for x in GRADES]].rename(columns={x[1]: f"{tr('Grade', 'গ্ৰেড')} {x[1]} · {x[2]}" for x in GRADES})
        top.index.name = tr("Block", "ব্লক")
        bars(top, [x[3] for x in GRADES], horizontal=True, height=400)
        lim = blocks.set_index("name")["main_limitation"].to_dict()
        t = g.reset_index().rename(columns={"block": tr("Block", "ব্লক"), "total": tr("Suitable land (ha)", "উপযুক্ত মাটি (হেক্টৰ)")})
        t[tr("Main problem", "মূল সমস্যা")] = t[tr("Block", "ব্লক")].map(lambda x: problem(lim.get(x, "")))
        t.insert(0, tr("Rank", "ক্ৰম"), range(1, len(t) + 1))
        st.dataframe(t.round(0), hide_index=True, use_container_width=True)

    h2(tr("Take the list with you", "তালিকাখন লৈ যাওক"))
    out = sel[["site_no", "block", "circle", "area_ha", "grade", "grade_name", "land_status", "mean_score", "lat", "lon"]].copy()
    out["land_type"] = out.land_status.map(lambda s: LAND_TYPE[int(s)][1])
    rs = sel.apply(reasons, axis=1)
    out["strong_points"] = [", ".join(g) for g, _ in rs]
    out["watch_out"] = [" | ".join(w) for _, w in rs]
    out["suggestion"] = sel.apply(lambda r: advice(r, prof), axis=1)
    out["google_maps"] = [f"https://www.google.com/maps?q={a},{b}" for a, b in zip(out.lat, out.lon)]
    out = out.drop(columns=["land_status"]).rename(columns={"area_ha": "area_hectares", "mean_score": "score"})
    c1, c2, c3 = st.columns(3)
    c1.download_button(tr("Site list (Excel / CSV)", "স্থানৰ তালিকা (Excel / CSV)"), out.to_csv(index=False).encode("utf-8-sig"),
                       file_name=f"PotharSight_{d}_{prof}_sites.csv", type="primary", icon=":material/table_view:", use_container_width=True)
    gj = sel[["site_no", "block", "area_ha", "grade", "geometry"]].copy()
    gj["Name"] = [f"Site {s} – {b} – Grade {g} – {a:.1f} ha" for s, b, g, a in zip(gj.site_no, gj.block, gj.grade, gj.area_ha)]
    c2.download_button(tr("Sites for Google Earth (KML)", "Google Earthৰ বাবে (KML)"), to_kml(gj[["Name", "geometry"]]),
                       file_name=f"PotharSight_{d}_{prof}_sites.kml", icon=":material/public:", use_container_width=True)
    c3.download_button(tr("Sites for GIS (GeoJSON)", "GISৰ বাবে (GeoJSON)"), gj.to_json(), file_name=f"PotharSight_{d}_{prof}_sites.geojson",
                       icon=":material/download:", use_container_width=True)
    st.markdown("<div class='ps-note' style='margin-top:12px'>" + icon("info", "sm") + " " + tr(
        "Land that looks unused in satellite data may still be owned or in use. Before allotting any site, confirm ownership with "
        "the circle office (Revenue Department) and visit the field.",
        "উপগ্ৰহৰ তথ্যত অব্যৱহৃত যেন লগা মাটিৰো গৰাকী থাকিব পাৰে বা ব্যৱহাৰ হৈ থাকিব পাৰে। কোনো স্থান আবণ্টনৰ আগতে চক্ৰ কাৰ্যালয়ত "
        "(ৰাজহ বিভাগ) মালিকীস্বত্ব নিশ্চিত কৰক আৰু পথাৰ পৰিদৰ্শন কৰক।") + "</div>", unsafe_allow_html=True)
footer()
