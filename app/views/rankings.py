"""Compare districts and blocks – where to place programme targets first."""
import pandas as pd
import streamlit as st

from theme import DISTRICTS, DNAME, OUT, PURPOSE, banner, footer

banner("Compare districts & blocks", "Which blocks have the most suitable unused land – and what holds each one back?",
       ["🏆 Ranked by suitable area × quality", "🧭 Main problem per block", "⬇️ Download as Excel"])

c1, c2 = st.columns(2)
prof = c1.radio("Programme", list(PURPOSE), horizontal=True, format_func=lambda p: f"{PURPOSE[p][0]} {PURPOSE[p][1]}")
level = c2.radio("Compare", ["Blocks", "Revenue circles"], horizontal=True)
plain = {"soil fertility": "🧪 soil needs improvement", "flood safety": "🌊 flooding", "water availability": "💧 water is far",
         "gentle terrain": "⛰️ slopes", "vegetation productivity": "🌿 weak vegetation", "road/market access": "🛣️ far from roads"}

frames = []
for d in DISTRICTS:
    f = pd.read_csv(OUT / d / prof / "tables" / ("blocks_ranking.csv" if level == "Blocks" else "circles_ranking.csv"))
    f["District"] = DNAME[d]
    frames.append(f)
A = pd.concat(frames)
A = A[A.candidate_ha > 0].copy()
A["Main problem"] = A.main_limitation.map(lambda x: plain.get(x, x))
A["Best land (ha)"] = A.S1_ha
A["Good land (ha)"] = A.S2_ha
A["Unused land (ha)"] = A.candidate_ha
A = A.sort_values("priority_index", ascending=False)
A.insert(0, "Assam rank", range(1, len(A) + 1))

st.markdown(f"#### Top {level.lower()} across all districts")
top = A.head(15)
st.bar_chart(top.set_index("name")[["Best land (ha)", "Good land (ha)"]], horizontal=True, height=420, sort=False,
             color=["#0b6b2e", "#46b04a"])
show = A[["Assam rank", "District", "name", "Best land (ha)", "Good land (ha)", "Unused land (ha)", "mean_score", "Main problem"]]
show = show.rename(columns={"name": level[:-1], "mean_score": "Average score"})
st.dataframe(show.round(0), hide_index=True, use_container_width=True, height=420)
st.download_button("⬇️ Download this ranking (Excel / CSV)", show.to_csv(index=False).encode("utf-8-sig"),
                   file_name=f"PotharSight_{level.lower().replace(' ', '_')}_{prof}.csv")

st.markdown("#### Main problems across districts")
st.caption("Share of each district's unused land where this is the biggest weakness – tells departments which support to bundle "
           "(liming, irrigation, flood-tolerant seed, roads).")
pv = A.groupby(["District", "Main problem"])["Unused land (ha)"].sum().unstack(fill_value=0)
st.bar_chart(pv.div(pv.sum(1), axis=0) * 100, height=300)
footer()
