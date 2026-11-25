"""Home – overview of all districts and entry points to every part of the portal."""
import pandas as pd
import streamlit as st

from theme import DISTRICTS, DNAME, OUT, TONES, banner, bars, desc, footer, h2, icon, kpi, tile_html, tr, validation

banner(tr("Where can new land be <em>farmed</em> in Assam?", "অসমত নতুনকৈ ক'ত <em>খেতি</em> কৰিব পাৰি?"),
       tr("Satellite data shows where unused land is, how good it is and why. Pick a task or a district to begin.",
          "উপগ্ৰহৰ তথ্যই অব্যৱহৃত মাটি ক'ত, কিমান ভাল আৰু কিয় দেখুৱায়। আৰম্ভ কৰিবলৈ এটা কাম বা জিলা বাছক।"),
       eyebrow=tr("Overview · 4 districts", "এক নজৰত · ৪টা জিলা"))


@st.cache_data
def overview():
    rows = []
    for d in DISTRICTS:
        v = validation(d)
        pp = pd.read_csv(OUT / d / "field_crops" / "tables" / "priority_patches.csv", usecols=["area_ha"])
        top3 = pd.read_csv(OUT / d / "field_crops" / "tables" / "blocks_ranking.csv", usecols=["name"]).name.head(3).tolist()
        rows.append(dict(key=d, official=v["official_vacant_cultivable_ha"],
                         satellite=v["model_vacant_plus_long_fallow_ha"], incl_rabi=v["model_all_candidate_incl_rabi_fallow_ha"],
                         sites=len(pp), priority=pp.area_ha.sum(), top3=top3))
    return pd.DataFrame(rows)


T = overview()
HA = tr("ha", "হেক্টৰ")

c = st.columns(4)
kpi(c[0], f"{len(DISTRICTS)}", tone="green", ic="location_on", label=tr("districts — the top 4 in Assam for unused cultivable land", "জিলা — অব্যৱহৃত খেতিযোগ্য মাটিত অসমৰ শীৰ্ষ ৪"))
kpi(c[1], f"{T.satellite.sum():,.0f} {HA}", tone="amber", ic="satellite_alt", label=tr("unused land seen by satellite (empty or left for years)",
                                              "উপগ্ৰহে দেখা অব্যৱহৃত মাটি (খালী বা বহু বছৰ পতিত)"))
kpi(c[2], f"{T.priority.sum():,.0f} {HA}", tone="blue", ic="verified", label=tr(f"suitable land for field crops in {T.sites.sum():,} sites",
                                             f"{T.sites.sum():,}টা স্থানত পথাৰ শস্যৰ উপযুক্ত মাটি"))
kpi(c[3], f"{T.incl_rabi.sum() - T.satellite.sum():,.0f} {HA}", tone="clay", ic="ac_unit", label=tr("paddy land empty in winter — a second-crop chance",
                                                                  "শীতত খালী থকা ধাননি — দ্বিতীয় শস্যৰ সুযোগ"))

h2(tr("What would you like to do?", "আপুনি কি কৰিব বিচাৰে?"))
tiles = [("travel_explore", tr("Find land for farming", "খেতিৰ মাটি বিচাৰক"),
          tr("Answer 3 questions, get a map and a list of the best sites with reasons.", "৩টা প্ৰশ্নৰ উত্তৰ দিয়ক, কাৰণসহ শ্ৰেষ্ঠ স্থানৰ মানচিত্ৰ আৰু তালিকা পাওক।"),
          "views/official.py"),
         ("leaderboard", tr("Compare districts & blocks", "জিলা আৰু ব্লক তুলনা"),
          tr("See which blocks have the most suitable land and their main problem.", "কোনবোৰ ব্লকত বেছি উপযুক্ত মাটি আৰু মূল সমস্যা কি চাওক।"),
          "views/rankings.py"),
         ("layers", tr("Advanced map analysis", "উন্নত মানচিত্ৰ বিশ্লেষণ"),
          tr("Suitability classes, adjustable criteria, factor scores, GIS downloads.", "উপযুক্ততাৰ শ্ৰেণী, সলনি কৰিব পৰা মাপকাঠি, কাৰক নম্বৰ, GIS ডাউনলোড।"),
          "views/analyst.py"),
         ("fact_check", tr("How it works & validation", "কেনেকৈ কাম কৰে আৰু পৰীক্ষা"),
          tr("Data sources, criteria, accuracy checks and how to add new districts.", "তথ্যৰ উৎস, মাপকাঠি, সঠিকতা পৰীক্ষা আৰু নতুন জিলা যোগ কৰাৰ উপায়।"),
          "views/about.py")]
cols = st.columns(4)
for col, (ic, t, d, page), tone in zip(cols, tiles, TONES):
    with col:
        st.markdown(tile_html(ic, t, d, tone), unsafe_allow_html=True)
        st.page_link(page, label=tr("Open", "খোলক"), icon=":material/arrow_forward:")

h2(tr("Districts", "জিলাসমূহ"))
cols = st.columns(len(DISTRICTS))
for col, r in zip(cols, T.itertuples()):
    with col.container(border=True, height="stretch", key=f"dcard_{r.key}"):
        n = DISTRICTS.index(r.key) + 1
        st.markdown(f"<div style='font-weight:800;font-size:1.1rem;color:#16231d'>{DNAME[r.key]}</div>"
                    f"<div style='color:#5d6a62;font-size:0.82rem;line-height:1.45;margin-top:2px'>"
                    + tr(f"#{n} in Assam for unused cultivable land", f"অব্যৱহৃত খেতিযোগ্য মাটিত অসমত {n} নম্বৰ")
                    + f" · {desc(r.key)}</div>", unsafe_allow_html=True)
        img = OUT / r.key / "field_crops" / "figures" / "suitability_class.png"
        if img.exists():
            st.image(str(img), use_container_width=True)
        st.markdown(f"<div style='font-size:0.9rem;line-height:1.6'>{icon('check_circle', 'sm')} <b>{r.priority:,.0f} {HA}</b> "
                    + tr("suitable", "উপযুক্ত") + f" · <b>{r.sites:,}</b> " + tr("sites", "টা স্থান") + "<br>"
                    + f"{icon('description', 'sm')} " + tr("Official unused", "চৰকাৰী হিচাপত অব্যৱহৃত") + f": {r.official:,} {HA}<br>"
                    + f"<span style='color:#5d6a62;font-size:0.82rem'>" + tr("Top blocks", "শীৰ্ষ ব্লক") + ": " + ", ".join(r.top3) + "</span></div>",
                    unsafe_allow_html=True)
        st.markdown("<div class='ps-card-end'></div>", unsafe_allow_html=True)
        if st.button(tr("Find land here", "ইয়াত মাটি বিচাৰক"), icon=":material/travel_explore:", key=f"go_{r.key}", use_container_width=True):
            st.session_state.district, st.session_state.step = r.key, 2
            st.switch_page("views/official.py")

h2(tr("Satellite findings vs official statistics", "উপগ্ৰহৰ তথ্য বনাম চৰকাৰী পৰিসংখ্যা"))
st.caption(tr("Official figure = culturable waste + fallow land (DES Assam, Land Utilisation Statistics 2020-21), available only as a "
              "district total. PotharSight puts this land on the map; satellite figures are lower because scrub counted "
              "officially often appears as tree cover.",
              "চৰকাৰী হিচাপ = খেতিযোগ্য পতিত + পতিত মাটি (DES অসম, ভূমি ব্যৱহাৰ পৰিসংখ্যা ২০২০-২১), কেৱল জিলাৰ মুঠ হিচাপে উপলব্ধ। "
              "PotharSight-এ এই মাটি মানচিত্ৰত দেখুৱায়; চৰকাৰী হিচাপৰ জোপোহা মাটি উপগ্ৰহত গছ-গছনি যেন দেখা যায়, সেয়ে উপগ্ৰহৰ সংখ্যা কম।"))
chart = pd.DataFrame({tr("Official unused cultivable (ha)", "চৰকাৰী অব্যৱহৃত খেতিযোগ্য (হেক্টৰ)"): T.official.values,
                      tr("Unused land seen by satellite (ha)", "উপগ্ৰহে দেখা অব্যৱহৃত মাটি (হেক্টৰ)"): T.satellite.values,
                      tr("Suitable sites for field crops (ha)", "পথাৰ শস্যৰ উপযুক্ত স্থান (হেক্টৰ)"): T.priority.values},
                     index=pd.Index([DNAME[k] for k in T.key], name=tr("District", "জিলা")))
bars(chart, ["#c9c3b3", "#e3b505", "#1d6b3a"], stack=False, height=320)
footer()
