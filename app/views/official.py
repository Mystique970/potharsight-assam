"""Find land for farming – guided, plain-language search for officials."""
import os
import tempfile

import folium
import geopandas as gpd
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from theme import (DESC, DISTRICTS, DNAME, GRADES, LAND_TYPE, PURPOSE, advice, banner, bars, factor_bars_html, footer,
                   legend_html, load_patches, reasons, validation)

ss = st.session_state
ss.setdefault("step", 1)

banner("🔍 Find land for farming", "Answer three questions. PotharSight shows where suitable unused land is, how much, and why.",
       ["No GIS knowledge needed", "Sites graded A–D", "Google Maps link for every site", "Download for field teams"])

labels = ["District", "What to grow", "Type of land", "Results"]
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


@st.cache_data(show_spinner=False, max_entries=32)
def select_sites(d, prof, types, block, min_ha, grades):
    patches, _ = load_patches(d, prof)
    sel = patches[patches.land_status.isin(types) & (patches.area_ha >= min_ha) & patches.grade.isin(grades)]
    if block != "All blocks":
        sel = sel[sel.block == block]
    sel = sel.sort_values("priority", ascending=False).reset_index(drop=True)
    sel["site_no"] = range(1, len(sel) + 1)
    return sel


@st.cache_data(show_spinner="Drawing the map…", max_entries=32)
def site_map(d, prof, types, block, min_ha, grades):
    """All selected sites in two layers (outlines + dots) – fast even with 4,000 sites, every grade colour shown."""
    import shapely
    sel = select_sites(d, prof, types, block, min_ha, grades)
    _, blocks = load_patches(d, prof)
    b = sel.total_bounds
    fm = folium.Map(location=[(b[1] + b[3]) / 2, (b[0] + b[2]) / 2], zoom_start=10, tiles=None, prefer_canvas=True)
    fm.fit_bounds([[b[1], b[0]], [b[3], b[2]]])
    folium.TileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                     attr="Esri World Imagery", name="Satellite photo").add_to(fm)
    folium.TileLayer("OpenStreetMap", name="Street map", show=False).add_to(fm)
    bl = blocks if block == "All blocks" else blocks[blocks.name == block]
    folium.GeoJson(bl[["name", "geometry"]], name="Blocks", style_function=lambda f: {"fill": False, "color": "#ffffff", "weight": 1.6},
                   tooltip=folium.GeoJsonTooltip(["name"], aliases=["Block"])).add_to(fm)
    s = sel.iloc[::-1].copy()  # best sites drawn last (on top)
    s["tip"] = [f"Site {n}: Grade {g} · {gn}, {a:.1f} ha – click for details"
                for n, g, gn, a in zip(s.site_no, s.grade, s.grade_name, s.area_ha)]
    pops = []
    for _, r in s.iterrows():
        good, watch = reasons(r)
        pops.append(f"<div style='min-width:260px'><b>Site {r.site_no}</b> · {r.block} block<br>"
                    f"<span style='background:{r.grade_col};color:#fff;padding:1px 6px;border-radius:6px'>Grade {r.grade} · {r.grade_name}</span> "
                    f"{r.area_ha:.1f} ha<br>{LAND_TYPE[int(r.land_status)][1]} · better than {100 * r.pct_rank:.0f}% of sites in the district<br>"
                    + (f"✅ {', '.join(good)}<br>" if good else "") + "".join(f"⚠️ {w}<br>" for w in watch)
                    + f"💡 {advice(r, prof)}<br><a href='https://www.google.com/maps?q={r.lat},{r.lon}' target='_blank'>Open in Google Maps</a></div>")
    s["popup"] = pops
    s["col"] = s.grade_col
    s["r"] = [7 if n <= 20 else 4.5 for n in s.site_no]
    poly = s[["tip", "col", "geometry"]].copy()
    poly["geometry"] = shapely.set_precision(poly.geometry.simplify(0.0003).values, 1e-5)
    folium.GeoJson(poly, name="Site outlines", tooltip=folium.GeoJsonTooltip(["tip"], labels=False),
                   style_function=lambda f: {"color": "#ffffff", "weight": 0.6, "fillColor": f["properties"]["col"], "fillOpacity": 0.85}
                   ).add_to(fm)
    pts = gpd.GeoDataFrame(s[["tip", "popup", "col", "r"]].copy(), geometry=gpd.points_from_xy(s.lon, s.lat), crs=4326)
    folium.GeoJson(pts, name="Site dots", marker=folium.CircleMarker(radius=4.5, weight=1.2, fill=True, fill_opacity=1),
                   style_function=lambda f: {"color": "#ffffff", "fillColor": f["properties"]["col"], "radius": f["properties"]["r"]},
                   tooltip=folium.GeoJsonTooltip(["tip"], labels=False),
                   popup=folium.GeoJsonPopup(["popup"], labels=False, max_width=360)).add_to(fm)
    folium.LayerControl().add_to(fm)
    return fm.get_root().render()


if ss.step == 1:
    st.markdown("### Which district are you planning for?")
    cols = st.columns(len(DISTRICTS))
    for col, d in zip(cols, DISTRICTS):
        v = validation(d)
        with col.container(border=True, height="stretch"):
            st.markdown(f"#### 📍 {DNAME[d]}")
            st.caption(DESC.get(d, ""))
            st.markdown(f"Official unused cultivable land:  \n**{v['official_vacant_cultivable_ha']:,} ha**")
            st.markdown("<div class='ps-card-end'></div>", unsafe_allow_html=True)
            if st.button("Choose", key=f"d_{d}", type="primary", use_container_width=True):
                ss.district = d
                go(2)

elif ss.step == 2:
    st.markdown(f"### What do you want to grow in {DNAME[ss.district]}?")
    cols = st.columns(len(PURPOSE))
    for col, (k, (ic, lab, desc)) in zip(cols, PURPOSE.items()):
        with col.container(border=True, height="stretch"):
            st.markdown(f"<div style='font-size:2.6rem'>{ic}</div>", unsafe_allow_html=True)
            st.markdown(f"#### {lab}")
            st.write(desc)
            st.markdown("<div class='ps-card-end'></div>", unsafe_allow_html=True)
            if st.button(f"Select {lab}", key=f"p_{k}", type="primary", use_container_width=True):
                ss.purpose = k
                go(3)
    if st.button("← Back"):
        go(1)

elif ss.step == 3:
    patches, blocks = load_patches(ss.district, ss.purpose)
    st.markdown("### What kind of land are you looking for?")
    cols = st.columns(3)
    picked = []
    for col, (k, (ic, lab, desc)) in zip(cols, LAND_TYPE.items()):
        with col.container(border=True, height="stretch"):
            n = int((patches.land_status == k).sum())
            if st.checkbox(f"{ic} **{lab}**", value=k in ss.get("types", [1, 2, 3]), key=f"t_{k}"):
                picked.append(k)
            st.caption(f"{desc} · {n:,} sites")
    c1, c2, c3 = st.columns(3)
    blk_opts = ["All blocks"] + sorted(b for b in patches.block.unique() if b != "outside block layer")
    blk = c1.selectbox("📍 In which block?", blk_opts, index=blk_opts.index(ss.block) if ss.get("block") in blk_opts else 0)
    size = c2.select_slider("📏 Smallest site", options=[0.5, 1, 2, 5, 10, 20], value=ss.get("min_ha", 1),
                            format_func=lambda x: f"{x} ha")
    gopts = [f"{g} · {n}" for _, g, n, _ in GRADES]
    gsel = c3.multiselect("🏷️ Grades to include", gopts, default=ss.get("grades", gopts))
    b1, b2 = st.columns([1, 4])
    if b1.button("← Back"):
        go(2)
    if b2.button("🔍 Show me the land", type="primary", disabled=not picked or not gsel):
        ss.types, ss.block, ss.min_ha, ss.grades = picked, blk, size, gsel
        go(4)

else:
    d, prof = ss.district, ss.purpose
    patches, blocks = load_patches(d, prof)
    gl = tuple(g.split(" · ")[0] for g in ss.get("grades", [f"{g} · {n}" for _, g, n, _ in GRADES]))
    key = (d, prof, tuple(ss.types), ss.block, ss.min_ha, gl)
    sel = select_sites(*key)
    where = ss.block + " block" if ss.block != "All blocks" else DNAME[d]
    ic, plab, _ = PURPOSE[prof]

    h1, h2 = st.columns([5, 1])
    h1.markdown(f"### {ic} {plab} in {where}")
    if h2.button("🔄 New search", use_container_width=True):
        go(1)
    if sel.empty:
        st.warning("No sites match. Try a smaller minimum size, another block, or more land types / grades.")
        st.stop()

    m = st.columns(6)
    m[0].metric("Sites found", f"{len(sel):,}")
    m[1].metric("Total area", f"{sel.area_ha.sum():,.0f} ha")
    for i, (_, g, n, col) in enumerate(GRADES):
        m[2 + i].metric(f"Grade {g} · {n}", f"{sel.loc[sel.grade == g, 'area_ha'].sum():,.0f} ha")
    st.markdown(legend_html(), unsafe_allow_html=True)

    tab_map, tab_list, tab_blocks = st.tabs(["🗺️ Map of sites", "📋 Best sites, with reasons", "🏘️ Compare blocks"])
    with tab_map:
        components.html(site_map(*key), height=600)
        st.caption(f"All {len(sel):,} sites, coloured by grade (the top 20 have bigger dots). Zoom in to see site outlines; "
                   "click a dot for details. Use the layer button (top right) to switch to a street map.")

    with tab_list:
        n = st.select_slider("Sites to show", [10, 25, 50, 100], value=10)
        for _, r in sel.head(n).iterrows():
            good, watch = reasons(r)
            with st.container(border=True):
                a, b2 = st.columns([4, 1])
                a.markdown(f"#### Site {r.site_no} · {r.block} block &nbsp;<span class='ps-badge' style='background:{r.grade_col}'>"
                           f"Grade {r.grade} · {r.grade_name}</span>", unsafe_allow_html=True)
                a.markdown(f"**{r.area_ha:.1f} ha** · {LAND_TYPE[int(r.land_status)][0]} {LAND_TYPE[int(r.land_status)][1]}"
                           + (f" · Revenue circle: {r.circle}" if isinstance(r.get("circle"), str) else "")
                           + f" · score {r.mean_score:.0f}/100 – better than **{100 * r.pct_rank:.0f}%** of sites in {DNAME[d]}")
                a.markdown(factor_bars_html(r), unsafe_allow_html=True)
                if good:
                    a.markdown("✅ **Strong points:** " + ", ".join(good))
                for w in watch:
                    a.markdown("⚠️ **Watch out:** " + w)
                a.markdown(f"💡 **Suggestion:** {advice(r, prof)}")
                b2.link_button("📍 Google Maps", f"https://www.google.com/maps?q={r.lat},{r.lon}", use_container_width=True)
                b2.caption(f"{r.lat:.5f} N  \n{r.lon:.5f} E")

    with tab_blocks:
        base = patches[patches.land_status.isin(ss.types) & (patches.area_ha >= ss.min_ha) & patches.grade.isin(gl)]
        g = base.pivot_table(index="block", columns="grade", values="area_ha", aggfunc="sum", fill_value=0)
        g = g.reindex(columns=[x[1] for x in GRADES], fill_value=0)
        g = g[g.index != "outside block layer"]
        g["total"] = g.sum(1)
        g = g.sort_values("total", ascending=False)
        top = g.head(12)[[x[1] for x in GRADES]].rename(columns={x[1]: f"Grade {x[1]} · {x[2]}" for x in GRADES})
        top.index.name = "Block"
        bars(top, [x[3] for x in GRADES], horizontal=True, height=400)
        lim = blocks.set_index("name")["main_limitation"].to_dict()
        plain = {"soil fertility": "🧪 soil needs improvement", "flood safety": "🌊 flooding", "water availability": "💧 water is far",
                 "gentle terrain": "⛰️ slopes", "vegetation productivity": "🌿 weak vegetation", "road/market access": "🛣️ far from roads"}
        t = g.reset_index().rename(columns={"block": "Block", "total": "Suitable land (ha)"})
        t["Main problem"] = t.Block.map(lambda x: plain.get(lim.get(x, ""), ""))
        t.insert(0, "Rank", range(1, len(t) + 1))
        st.dataframe(t.round(0), hide_index=True, use_container_width=True)

    st.markdown("#### ⬇️ Take the list with you")
    out = sel[["site_no", "block", "circle", "area_ha", "grade", "grade_name", "land_status", "mean_score", "lat", "lon"]].copy()
    out["land_type"] = out.land_status.map(lambda s: LAND_TYPE[int(s)][1])
    rs = sel.apply(reasons, axis=1)
    out["strong_points"] = [", ".join(g) for g, _ in rs]
    out["watch_out"] = [" | ".join(w) for _, w in rs]
    out["suggestion"] = sel.apply(lambda r: advice(r, prof), axis=1)
    out["google_maps"] = [f"https://www.google.com/maps?q={a},{b}" for a, b in zip(out.lat, out.lon)]
    out = out.drop(columns=["land_status"]).rename(columns={"area_ha": "area_hectares", "mean_score": "score"})
    c1, c2, c3 = st.columns(3)
    c1.download_button("📊 Site list (Excel / CSV)", out.to_csv(index=False).encode("utf-8-sig"),
                       file_name=f"PotharSight_{d}_{prof}_sites.csv", type="primary", use_container_width=True)
    gj = sel[["site_no", "block", "area_ha", "grade", "geometry"]].copy()
    gj["Name"] = [f"Site {s} – {b} – Grade {g} – {a:.1f} ha" for s, b, g, a in zip(gj.site_no, gj.block, gj.grade, gj.area_ha)]
    c2.download_button("🌍 Sites for Google Earth (KML)", to_kml(gj[["Name", "geometry"]]),
                       file_name=f"PotharSight_{d}_{prof}_sites.kml", use_container_width=True)
    c3.download_button("🗺️ Sites for GIS (GeoJSON)", gj.to_json(), file_name=f"PotharSight_{d}_{prof}_sites.geojson",
                       use_container_width=True)
    st.info("ℹ️ Land that looks unused in satellite data may still be owned or in use. Before allotting any site, "
            "confirm ownership with the circle office (Revenue Department) and visit the field.")
footer()
