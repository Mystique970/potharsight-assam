"""Compare districts and blocks – where to place programme targets first."""
import pandas as pd
import streamlit as st

from theme import DISTRICTS, DNAME, OUT, PURPOSE, banner, bars, footer, h2, problem, tr

banner(tr("Compare districts & blocks", "জিলা আৰু ব্লক তুলনা"),
       tr("Which blocks have the most suitable unused land — and what holds each one back?",
          "কোনবোৰ ব্লকত আটাইতকৈ বেছি উপযুক্ত অব্যৱহৃত মাটি — আৰু প্ৰতিটোৰ বাধা কি?"),
       [tr("Ranked by suitable area × quality", "উপযুক্ত মাটি × মান অনুসৰি ক্ৰম"), tr("Main problem per block", "প্ৰতি ব্লকৰ মূল সমস্যা"),
        tr("Download as Excel", "Excel হিচাপে ডাউনলোড")], eyebrow=tr("Compare", "তুলনা"))

c1, c2 = st.columns(2)
prof = c1.radio(tr("Programme", "আঁচনি"), list(PURPOSE), horizontal=True, format_func=lambda p: PURPOSE[p][1])
level = c2.radio(tr("Compare", "তুলনা কৰক"), ["Blocks", "Revenue circles"], horizontal=True,
                 format_func=lambda x: tr(x, {"Blocks": "ব্লক", "Revenue circles": "ৰাজহ চক্ৰ"}[x]))
unit = tr("Block", "ব্লক") if level == "Blocks" else tr("Revenue circle", "ৰাজহ চক্ৰ")

frames = []
for d in DISTRICTS:
    f = pd.read_csv(OUT / d / prof / "tables" / ("blocks_ranking.csv" if level == "Blocks" else "circles_ranking.csv"))
    f["District"] = DNAME[d]
    frames.append(f)
A = pd.concat(frames)
A = A[A.candidate_ha > 0].copy()
BEST, GOOD, UNUSED = tr("Best land (ha)", "শ্ৰেষ্ঠ মাটি (হেক্টৰ)"), tr("Good land (ha)", "ভাল মাটি (হেক্টৰ)"), tr("Unused land (ha)", "অব্যৱহৃত মাটি (হেক্টৰ)")
PROB = tr("Main problem", "মূল সমস্যা")
A[PROB] = A.main_limitation.map(problem)
A[BEST], A[GOOD], A[UNUSED] = A.S1_ha, A.S2_ha, A.candidate_ha
A = A.sort_values("priority_index", ascending=False)
A.insert(0, tr("Assam rank", "অসমত ক্ৰম"), range(1, len(A) + 1))

h2(tr(f"Top {level.lower()} across all districts", f"সকলো জিলাৰ শীৰ্ষ {unit}"))
top = A.head(15)
tb = top.assign(label=top.name + " (" + top.District + ")").set_index("label")[[BEST, GOOD]]
tb.index.name = unit
bars(tb, ["#0b6b2e", "#46b04a"], horizontal=True, height=440)
show = A[[tr("Assam rank", "অসমত ক্ৰম"), "District", "name", BEST, GOOD, UNUSED, "mean_score", PROB]]
show = show.rename(columns={"name": unit, "District": tr("District", "জিলা"), "mean_score": tr("Average score", "গড় নম্বৰ")})
st.dataframe(show.round(0), hide_index=True, use_container_width=True, height=420)
st.download_button(tr("Download this ranking (Excel / CSV)", "এই ক্ৰম ডাউনলোড কৰক (Excel / CSV)"), show.to_csv(index=False).encode("utf-8-sig"),
                   file_name=f"PotharSight_{level.lower().replace(' ', '_')}_{prof}.csv", icon=":material/download:")

h2(tr("Main problems across districts", "জিলাসমূহৰ মূল সমস্যা"))
st.caption(tr("Share of each district's unused land where this is the biggest weakness — tells departments which support to bundle "
              "(liming, irrigation, flood-tolerant seed, roads).",
              "প্ৰতিটো জিলাৰ অব্যৱহৃত মাটিৰ কিমান অংশত এইটো আটাইতকৈ ডাঙৰ দুৰ্বলতা — বিভাগে কি সহায় একেলগে দিব লাগে (চূণ, জলসিঞ্চন, "
              "বান সহনশীল বীজ, পথ) জনায়।"))
pv = A.groupby(["District", PROB])[UNUSED].sum().unstack(fill_value=0)
pv.index.name = tr("District", "জিলা")
bars(pv.div(pv.sum(1), axis=0) * 100, ["#8c510a", "#2166ac", "#5aae61", "#d6604d", "#9970ab", "#9e9e9e"], height=320,
     unit=tr("of unused land", "অব্যৱহৃত মাটিৰ"), pct=True)
footer()
