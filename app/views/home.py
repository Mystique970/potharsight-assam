"""Home – overview of all districts and entry points to every part of the portal."""
import pandas as pd
import streamlit as st

from theme import DESC, DISTRICTS, DNAME, OUT, banner, bars, footer, kpi, validation

banner("Welcome to PotharSight Assam",
       "Where is unused land that can be farmed, how good is it, and why? Choose a task below or open a district.",
       [f"🗺️ {len(DISTRICTS)} districts", "🌾 Field crops & 🍊 horticulture", "🛰️ Sentinel-1/2 + 7 open layers",
        "🔄 Re-run every season", "➕ New district = one config line"])



@st.cache_data
def overview():
    rows = []
    for d in DISTRICTS:
        v = validation(d)
        pp = pd.read_csv(OUT / d / "field_crops" / "tables" / "priority_patches.csv", usecols=["area_ha"])
        top3 = pd.read_csv(OUT / d / "field_crops" / "tables" / "blocks_ranking.csv", usecols=["name"]).name.head(3).tolist()
        rows.append(dict(district=DNAME[d], key=d, official=v["official_vacant_cultivable_ha"],
                         satellite=v["model_vacant_plus_long_fallow_ha"], incl_rabi=v["model_all_candidate_incl_rabi_fallow_ha"],
                         sites=len(pp), priority=pp.area_ha.sum(), top3=top3))
    return pd.DataFrame(rows)


T = overview()

c = st.columns(4)
kpi(c[0], f"{len(DISTRICTS)}", "districts covered – the top 4 in Assam for unused cultivable land")
kpi(c[1], f"{T.satellite.sum():,.0f} ha", "unused land seen by satellite (empty + left for years)")
kpi(c[2], f"{T.priority.sum():,.0f} ha", f"suitable land for field crops in {T.sites.sum():,} sites")
kpi(c[3], f"{T.incl_rabi.sum() - T.satellite.sum():,.0f} ha", "paddy land empty in winter – second-crop chance")

st.markdown("#### What would you like to do?")
tiles = [("🔍", "Find land for farming", "Answer 3 questions, get a map and list of the best sites with reasons.", "views/official.py"),
         ("🏆", "Compare districts & blocks", "See which blocks have the most suitable land and their main problem.", "views/rankings.py"),
         ("🛠️", "Advanced map analysis", "Suitability classes, adjustable criteria, factor scores, GIS downloads.", "views/analyst.py"),
         ("📘", "How it works & validation", "Data sources, criteria, accuracy checks and how to scale to new districts.", "views/about.py")]
cols = st.columns(4)
for col, (ic, t, d, page) in zip(cols, tiles):
    with col:
        st.markdown(f"<div class='ps-tile'><div class='ic'>{ic}</div><div class='t'>{t}</div><div class='d'>{d}</div></div>",
                    unsafe_allow_html=True)
        st.page_link(page, label=f"Open: {t}", icon="➡️")

st.markdown("#### Districts")
cols = st.columns(len(DISTRICTS))
for col, r in zip(cols, T.itertuples()):
    with col.container(border=True, height="stretch", key=f"dcard_{r.key}"):
        tag = f"#{DISTRICTS.index(r.key) + 1} in Assam for unused cultivable land"
        st.markdown(f"**{r.district}**  \n<span style='color:#6b7280;font-size:0.82rem'>{tag} · {DESC.get(r.key, '')}</span>",
                    unsafe_allow_html=True)
        img = OUT / r.key / "field_crops" / "figures" / "suitability_class.png"
        if img.exists():
            st.image(str(img), use_container_width=True)
        st.markdown(f"🟩 **{r.priority:,.0f} ha** suitable · **{r.sites:,}** sites  \n"
                    f"📊 Official unused cultivable: {r.official:,} ha")
        st.caption("Top blocks: " + ", ".join(r.top3))
        st.markdown("<div class='ps-card-end'></div>", unsafe_allow_html=True)
        if st.button("🔍 Find land here", key=f"go_{r.key}", use_container_width=True):
            st.session_state.district, st.session_state.step = r.key, 2
            st.switch_page("views/official.py")

st.markdown("#### Satellite findings vs official statistics")
st.caption("Official figure = culturable waste + fallow land (DES Assam, Land Utilisation Statistics 2020-21), available only as a "
           "district total. PotharSight locates this land on the map; satellite figures are lower because scrubland counted "
           "officially often appears as tree cover.")
chart = T.set_index("district")[["official", "satellite", "priority"]].rename(columns={
    "official": "Official unused cultivable (ha)", "satellite": "Unused land seen by satellite (ha)",
    "priority": "Suitable sites for field crops (ha)"})
chart.index.name = "District"
bars(chart, ["#9ca3af", "#f2c80f", "#127a36"], stack=False, height=320)
footer()
