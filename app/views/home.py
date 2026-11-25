"""Home – overview of all districts and entry points to every part of the portal."""
import pandas as pd
import streamlit as st

from theme import DESC, DISTRICTS, DNAME, OUT, PILOT, banner, footer, kpi, validation

banner("Welcome to PotharSight Assam",
       "Where is unused land that can be farmed, how good is it, and why? Choose a task below or open a district.",
       [f"🗺️ {len(DISTRICTS)} districts", "🌾 Field crops & 🍊 horticulture", "🛰️ Sentinel-1/2 + 7 open layers",
        "🔄 Re-run every season", "➕ New district = one config line"])

rows = []
for d in DISTRICTS:
    v = validation(d)
    pp = pd.read_csv(OUT / d / "field_crops" / "tables" / "priority_patches.csv")
    rows.append(dict(district=DNAME[d], key=d, official=v["official_vacant_cultivable_ha"],
                     satellite=v["model_vacant_plus_long_fallow_ha"], incl_rabi=v["model_all_candidate_incl_rabi_fallow_ha"],
                     sites=len(pp), priority=pp.area_ha.sum(), top=pp.mean_score.ge(85).sum()))
T = pd.DataFrame(rows)

c = st.columns(4)
kpi(c[0], f"{len(DISTRICTS)}", "districts covered (2 pilots + scale-out)" if len(DISTRICTS) > 2 else "pilot districts")
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
    with col.container(border=True):
        tag = "Pilot district" if r.key in PILOT else "Scale-out district"
        st.markdown(f"**{r.district}**  \n<span style='color:#6b7280;font-size:0.82rem'>{tag} · {DESC.get(r.key, '')}</span>",
                    unsafe_allow_html=True)
        img = OUT / r.key / "field_crops" / "figures" / "suitability_class.png"
        if img.exists():
            st.image(str(img), use_container_width=True)
        st.markdown(f"🟩 **{r.priority:,.0f} ha** suitable · **{r.sites:,}** sites  \n"
                    f"📊 Official unused cultivable: {r.official:,} ha")
        blocks = pd.read_csv(OUT / r.key / "field_crops" / "tables" / "blocks_ranking.csv").head(3)
        st.caption("Top blocks: " + ", ".join(blocks.name))
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
st.bar_chart(chart, stack=False, height=300, color=["#9ca3af", "#f2c80f", "#127a36"])
footer()
