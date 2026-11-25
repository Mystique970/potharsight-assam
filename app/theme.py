"""Shared look-and-feel, language (English / Assamese), grades and plain-language helpers for the PotharSight portal."""
import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
import streamlit as st

from d13.core import load_config
from d13.model import FACTORS

ROOT = Path(__file__).resolve().parents[1]
cfg = load_config()
OUT = ROOT / cfg["project"]["output_dir"]
DISTRICTS = [d for d in cfg["districts"] if (OUT / d / "field_crops" / "tables" / "validation.json").exists()]
PILOT = ["kamrup", "cachar"]  # the first two districts run; the others were added by configuration only

# ------------------------------------------------------------------ language
LANGS = {"en": "English", "as": "অসমীয়া"}


def lang():
    return st.session_state.get("lang", "en")


def tr(en, as_):
    """Pick the English or Assamese text for the current language."""
    return as_ if lang() == "as" else en


def lang_switch(key="lang_switch"):
    """Language toggle with a flat 'translate' icon; keeps the choice in the session."""
    cur = lang()
    st.markdown(f"<div class='ps-langlab'>{icon('translate')} {tr('Language', 'ভাষা')}</div>", unsafe_allow_html=True)
    choice = st.segmented_control("Language", list(LANGS), default=cur, format_func=lambda k: LANGS[k],
                                  key=key, label_visibility="collapsed")
    if choice and choice != cur:
        st.session_state.lang = choice
        st.rerun()


_DNAME_EN = {d: cfg["districts"][d]["boundary_name"] + (" (Rural)" if d == "kamrup" else "") for d in cfg["districts"]}
_DNAME_AS = {"kamrup": "কামৰূপ (গ্ৰাম্য)", "cachar": "কাছাৰ", "lakhimpur": "লখিমপুৰ", "dibrugarh": "ডিব্ৰুগড়"}


class _Names(dict):
    """District names that follow the selected language (falls back to English)."""

    def __getitem__(self, k):
        return _DNAME_AS.get(k, _DNAME_EN[k]) if lang() == "as" else _DNAME_EN[k]

    def get(self, k, default=None):
        return self[k] if k in _DNAME_EN else default


DNAME = _Names(_DNAME_EN)
_DESC = {"kamrup": ("Brahmaputra valley · char lands · Meghalaya foothills", "ব্ৰহ্মপুত্ৰ উপত্যকা · চৰ অঞ্চল · মেঘালয়ৰ পাদদেশ"),
         "cachar": ("Barak valley · high rainfall · hills & tea gardens", "বৰাক উপত্যকা · অধিক বৰষুণ · পাহাৰ আৰু চাহ বাগিচা"),
         "lakhimpur": ("North bank · Subansiri floodplain", "উত্তৰ পাৰ · সোৱণশিৰিৰ বানপানী অঞ্চল"),
         "dibrugarh": ("Upper Assam · tea belt · Brahmaputra south bank", "উজনি অসম · চাহ অঞ্চল · ব্ৰহ্মপুত্ৰৰ দক্ষিণ পাৰ")}


def desc(d):
    e, a = _DESC.get(d, ("", ""))
    return tr(e, a)


# kept for older imports
DESC = {k: v[0] for k, v in _DESC.items()}

# ------------------------------------------------------------------ icons (flat Material Symbols, no emoji)


def icon(name, cls=""):
    return f"<span class='msr {cls}'>{name}</span>"


_PURPOSE = {"field_crops": ("grass", ("Field crops", "পথাৰ শস্য"),
                            ("Rice, mustard, pulses, maize and other seasonal crops", "ধান, সৰিয়হ, মাহ-দাইল, মাকৈ আদি ঋতুভিত্তিক শস্য")),
            "horticulture": ("nutrition", ("Fruits & vegetables", "ফল-মূল আৰু শাক-পাচলি"),
                             ("Citrus, banana, pineapple, vegetables – needs land safer from floods",
                              "নেমু-টেঙা, কল, আনাৰস, শাক-পাচলি — বানপানীৰ পৰা সুৰক্ষিত মাটি লাগে"))}
_LAND = {1: ("landscape", ("Empty land", "খালী মাটি"), ("Grassland or scrub that is not being farmed", "খেতি নকৰা তৃণভূমি বা জোপোহা মাটি")),
         2: ("grass", ("Unused farmland", "পতিত পথাৰ"), ("Fields that have not been cropped in recent years", "যোৱা কেইবছৰমান খেতি নোহোৱা পথাৰ")),
         3: ("ac_unit", ("Empty in winter", "শীতত খালী"),
             ("Kharif paddy land left empty in rabi – a second crop can be added", "খৰিফ ধানৰ পিছত ৰবি বতৰত খালী থকা মাটি — দ্বিতীয় শস্য কৰিব পাৰি"))}


class _Lookup(dict):
    """(icon, label, description) in the current language."""

    def __init__(self, src):
        super().__init__({k: None for k in src})
        self._src = src

    def __getitem__(self, k):
        ic, lab, d = self._src[k]
        return ic, tr(*lab), tr(*d)

    def items(self):
        return [(k, self[k]) for k in self._src]


PURPOSE = _Lookup(_PURPOSE)
LAND_TYPE = _Lookup(_LAND)

# four grades from the site score (cut-offs near the quartiles of real sites), clearly different colours
GRADES_BASE = [(85, "A", ("Excellent", "অতি উত্তম"), "#0b6b2e"), (80, "B", ("Very good", "বৰ ভাল"), "#46b04a"),
               (75, "C", ("Good", "ভাল"), "#e3b505"), (0, "D", ("Fair", "মধ্যমীয়া"), "#e8820c")]


class _Grades(list):
    def __iter__(self):
        return iter([(c, g, tr(*n), col) for c, g, n, col in GRADES_BASE])

    def __getitem__(self, i):
        return list(iter(self))[i]

    def __len__(self):
        return len(GRADES_BASE)


GRADES = _Grades()


def grade(score):
    for cut, g, name, col in GRADES_BASE:
        if score >= cut:
            return g, name[0], col
    return GRADES_BASE[-1][1], GRADES_BASE[-1][2][0], GRADES_BASE[-1][3]


def grade_name(g):
    return next(tr(*n) for _, gg, n, _ in GRADES_BASE if gg == g)


_FNAME = {"soil": ("Soil", "মাটি"), "water": ("Water", "পানী"), "flood": ("Flood safety", "বানপানী সুৰক্ষা"),
          "terrain": ("Flat land", "সমতল মাটি"), "productivity": ("Plant growth", "উদ্ভিদৰ বৃদ্ধি"),
          "access": ("Road access", "পথৰ সুবিধা")}
FICON = {"soil": "layers", "water": "water_drop", "flood": "flood", "terrain": "terrain", "productivity": "eco",
         "access": "add_road"}
_GOOD = {"soil": ("fertile soil", "উৰ্বৰ মাটি"), "water": ("water close by", "ওচৰতে পানী"),
         "flood": ("safe from floods", "বানপানীৰ পৰা সুৰক্ষিত"), "terrain": ("flat land", "সমতল মাটি"),
         "productivity": ("crops and plants grow well here", "ইয়াত শস্য আৰু গছ-গছনি ভালদৰে বাঢ়ে"),
         "access": ("near roads and markets", "পথ আৰু বজাৰৰ ওচৰত")}
_WATCH = {"soil": ("soil is acidic or low in nutrients – get a soil test; lime and organic manure will help",
                   "মাটি অম্লীয় বা পুষ্টি কম — মাটি পৰীক্ষা কৰক; চূণ আৰু জৈৱিক সাৰে সহায় কৰিব"),
          "water": ("water source is far – plan a tube well, pump or farm pond", "পানীৰ উৎস দূৰত — নলকূপ, পাম্প বা পুখুৰীৰ পৰিকল্পনা কৰক"),
          "flood": ("can flood in monsoon – flood-tolerant varieties or raised beds", "বাৰিষা বানপানী হ'ব পাৰে — বান সহনশীল জাত বা ওখ ভেটি"),
          "terrain": ("land slopes – terracing or contour bunds needed", "মাটি এঢলীয়া — থাক-থাককৈ খেতি বা আলি বান্ধিব লাগিব"),
          "productivity": ("vegetation has been weak – visit the field before planning",
                           "উদ্ভিদৰ বৃদ্ধি দুৰ্বল — পৰিকল্পনাৰ আগতে পথাৰ চাওক"),
          "access": ("far from roads or markets – transport will cost more", "পথ বা বজাৰৰ পৰা দূৰত — পৰিবহণ খৰচ বেছি হ'ব")}
PROBLEM = {"soil fertility": ("soil needs improvement", "মাটিৰ উন্নতি লাগে"), "flood safety": ("flooding", "বানপানী"),
           "water availability": ("water is far", "পানী দূৰত"), "gentle terrain": ("slopes", "এঢলীয়া মাটি"),
           "vegetation productivity": ("weak vegetation", "দুৰ্বল উদ্ভিদ"), "road/market access": ("far from roads", "পথৰ পৰা দূৰত")}


def fname(k):
    return tr(*_FNAME[k])


def problem(x):
    return tr(*PROBLEM[x]) if x in PROBLEM else x


def level(v):
    return (tr("High", "উচ্চ"), "#0b6b2e") if v >= 80 else (tr("Medium", "মধ্যম"), "#b07d00") if v >= 55 else (tr("Low", "নিম্ন"), "#c0392b")


def advice(r, purpose):
    """Site-specific suggestion from land type, purpose and its own strengths/weaknesses."""
    s = int(r.land_status)
    f = {k: r[f"f_{k}"] for k in FACTORS}
    if purpose == "field_crops":
        base = {3: ("Add a rabi crop after kharif paddy – mustard, lentil, pea or toria.",
                    "খৰিফ ধানৰ পিছত এটা ৰবি শস্য কৰক — সৰিয়হ, মচুৰ, মটৰ বা তৰিয়া।"),
                2: ("Bring back into kharif cultivation; first check why it was left (water, flooding or ownership).",
                    "পুনৰ খৰিফ খেতিলৈ আনক; প্ৰথমে কিয় এৰা হৈছিল চাওক (পানী, বানপানী বা মালিকীস্বত্ব)।"),
                1: ("New land: needs clearing and levelling before the first crop.",
                    "নতুন মাটি: প্ৰথম খেতিৰ আগতে চাফ কৰি সমান কৰিব লাগিব।")}[s]
    else:
        base = {3: ("Winter vegetables (potato, cabbage, tomato) on residual moisture after paddy.",
                    "ধানৰ পিছত মাটিৰ সেমেকাৰে শীতকালীন শাক-পাচলি (আলু, বন্ধাকবি, বিলাহী)।"),
                2: ("Good for a new orchard or banana plantation after land preparation.",
                    "মাটি প্ৰস্তুত কৰাৰ পিছত নতুন ফলৰ বাগিচা বা কলৰ খেতিৰ বাবে ভাল।"),
                1: ("Suited to a horticulture cluster (citrus, pineapple, arecanut) after land development.",
                    "মাটি উন্নয়নৰ পিছত উদ্যান গুচ্ছৰ (নেমু-টেঙা, আনাৰস, তামোল) বাবে উপযুক্ত।")}[s]
    extra = []
    if f["flood"] < 60:
        extra.append(tr("Prefer flood-tolerant varieties (e.g. Swarna-Sub1 rice) or raised beds.",
                        "বান সহনশীল জাত (যেনে স্বৰ্ণ-সাব১ ধান) বা ওখ ভেটি বাছক।"))
    if f["water"] < 60:
        extra.append(tr("Irrigation needed – link with PMKSY / farm pond scheme.", "জলসিঞ্চন লাগিব — PMKSY / পুখুৰী আঁচনিৰ সৈতে সংযোগ কৰক।"))
    if f["soil"] < 70:
        extra.append(tr("Soil Health Card test and liming before sowing.", "সিঁচাৰ আগতে মাটি স্বাস্থ্য কাৰ্ড পৰীক্ষা আৰু চূণ প্ৰয়োগ।"))
    return " ".join([tr(*base)] + extra[:2])


def reasons(r):
    f = {k: r[f"f_{k}"] for k in FACTORS}
    good = [tr(*_GOOD[k]) for k, v in sorted(f.items(), key=lambda x: -x[1]) if v >= 80][:3]
    watch = [tr(*_WATCH[k]) for k, v in sorted(f.items(), key=lambda x: x[1]) if v < 60][:2]
    return good, watch


def factor_bars_html(r):
    cells = []
    for k in FACTORS:
        v = float(r[f"f_{k}"])
        lab, col = level(v)
        cells.append(f"<div class='fb'><div class='fbl'>{icon(FICON[k], 'sm')} {fname(k)}</div>"
                     f"<div class='fbt'><div style='width:{v:.0f}%;background:{col}'></div></div>"
                     f"<div class='fbv' style='color:{col}'>{lab}</div></div>")
    return "<div class='fgrid'>" + "".join(cells) + "</div>"


@st.cache_data
def load_patches(dkey, prof):
    P = OUT / dkey / prof
    p = gpd.read_file(P / "vectors" / "priority_patches.gpkg").to_crs(4326)
    c = p.geometry.representative_point()
    p["lat"], p["lon"] = c.y.round(5), c.x.round(5)
    g = p.mean_score.apply(grade)
    p["grade"], p["grade_name"], p["grade_col"] = [x[0] for x in g], [x[1] for x in g], [x[2] for x in g]
    p["pct_rank"] = p.mean_score.rank(pct=True)
    b = gpd.read_file(P / "vectors" / "blocks_ranking.gpkg").to_crs(4326)
    return p, b


@st.cache_data
def validation(dkey, prof="field_crops"):
    return json.loads((OUT / dkey / prof / "tables" / "validation.json").read_text())


# ------------------------------------------------------------------ styles
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Bengali:wght@400;500;600;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,300..500,0,0&display=block');
:root {--bg:#f6f4ee; --card:#ffffff; --ink:#16231d; --muted:#5d6a62; --line:#e7e2d5; --brand:#1d6b3a; --soft:#e8f1e7; --ochre:#a8701a;}
.stApp, .stApp p, .stApp li, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp button, .stApp input {
  font-family: 'Manrope', 'Noto Sans Bengali', 'Nirmala UI', system-ui, sans-serif;}
.msr {font-family: 'Material Symbols Rounded'; font-weight: 400; font-style: normal; font-size: 22px; line-height: 1;
  letter-spacing: normal; text-transform: none; display: inline-block; white-space: nowrap; vertical-align: -5px;
  font-variation-settings: 'FILL' 0, 'wght' 350, 'GRAD' 0, 'opsz' 24; -webkit-font-smoothing: antialiased;}
.msr.sm {font-size: 17px; vertical-align: -3px;} .msr.lg {font-size: 26px;}
.block-container {padding-top: 1.4rem !important; padding-bottom: 2.5rem; max-width: 1240px;}
header[data-testid="stHeader"] {height: 2.4rem; background: transparent;}
[data-testid="stSidebarHeader"] {padding: 1rem 1rem 0.4rem 1.1rem;}
[data-testid="stSidebarUserContent"] {padding-top: 0.2rem;}
[data-testid="stSidebar"] {border-right: 1px solid var(--line);}
[data-testid="stSidebarNav"] a span {font-size: 0.95rem;}
[data-testid="stSidebarNavSeparator"] {display: none;}
.stApp h1, .stApp h2, .stApp h3, .stApp h4 {color: var(--ink); letter-spacing: -0.02em;}

/* page header */
.ps-eyebrow {display: inline-flex; align-items: center; gap: 7px; border: 1px solid var(--line); background: #fbfaf6;
  border-radius: 999px; padding: 3px 12px; font-size: 0.72rem; font-weight: 700; letter-spacing: 0.08em; color: #3f4b44;
  text-transform: uppercase;}
.ps-eyebrow i {width: 7px; height: 7px; border-radius: 50%; background: var(--brand); display: inline-block;}
.ps-h1 {font-size: 2.35rem; line-height: 1.12; font-weight: 800; color: var(--ink); letter-spacing: -0.03em; margin: 12px 0 6px 0;}
.ps-h1 em {font-style: normal; color: var(--brand);}
.ps-sub {font-size: 1.04rem; color: var(--muted); max-width: 760px; line-height: 1.55; margin-bottom: 6px;}
.ps-meta {margin: 6px 0 4px 0; display: flex; gap: 8px; flex-wrap: wrap;}
.ps-meta span {font-size: 0.8rem; color: #45524a; background: #efece3; border-radius: 999px; padding: 3px 10px;}
.ps-h2 {font-size: 1.35rem; font-weight: 800; color: var(--ink); letter-spacing: -0.02em; margin: 22px 0 10px 0;}

/* cards */
.ps-kpi {background: var(--card); border: 1px solid var(--line); border-radius: 18px; padding: 16px 18px;
  height: 100%; min-height: 112px; box-sizing: border-box; box-shadow: 0 1px 2px rgba(22,35,29,0.04);}
.ps-kpi .v {font-size: 1.85rem; font-weight: 800; color: var(--ink); line-height: 1.15; letter-spacing: -0.02em;}
.ps-kpi .l {font-size: 0.84rem; color: var(--muted); margin-top: 4px; line-height: 1.4;}
.ps-tile {background: var(--card); border: 1px solid var(--line); border-radius: 18px; padding: 18px 18px 14px 18px;
  height: 100%; min-height: 176px; box-sizing: border-box; box-shadow: 0 1px 2px rgba(22,35,29,0.04);}
.ps-ic {width: 40px; height: 40px; border-radius: 12px; background: var(--soft); color: var(--brand);
  display: flex; align-items: center; justify-content: center; margin-bottom: 12px;}
.ps-ic .msr {vertical-align: 0;}
.ps-tile .t {font-weight: 750; font-size: 1.04rem; color: var(--ink);}
.ps-tile .d {font-size: 0.88rem; color: var(--muted); margin-top: 4px; line-height: 1.45;}
[data-testid="stVerticalBlockBorderWrapper"], [data-testid="stLayoutWrapper"] > [data-testid="stVerticalBlock"][class*="border"] {background: var(--card);}
div[data-testid="stVerticalBlock"]:has(> div > .ps-cardmark) {background: var(--card);}

/* steps */
.ps-steps {display: flex; gap: 6px; margin: 6px 0 14px 0; flex-wrap: wrap;}
.ps-step {padding: 6px 14px; border-radius: 999px; background: #efece3; color: #6b746e; font-size: 0.85rem; font-weight: 650;}
.ps-step.on {background: var(--ink); color: #fff;} .ps-step.done {background: var(--soft); color: var(--brand);}

.ps-badge {display: inline-block; color: #fff; border-radius: 999px; padding: 2px 10px; font-size: 0.78rem; font-weight: 700;}
.fgrid {display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px 18px; margin: 8px 0 6px 0;}
.fb {display: grid; grid-template-columns: 128px 1fr 62px; align-items: center; gap: 8px; font-size: 0.82rem; color: #2f3a34;}
.fbt {background: #eeebe3; border-radius: 4px; height: 7px; overflow: hidden;} .fbt div {height: 7px; border-radius: 4px;}
.fbv {font-weight: 700; font-size: 0.78rem;}
.ps-legend {font-size: 0.86rem; color: #2f3a34;}
.ps-legend span {display: inline-block; width: 11px; height: 11px; border-radius: 50%; margin: 0 6px -1px 14px;}
.ps-legend span:first-child {margin-left: 0;}
.ps-line {display: flex; gap: 8px; align-items: flex-start; margin: 3px 0; font-size: 0.92rem; color: #26322b;}
.ps-line .msr {color: var(--brand); margin-top: 3px;}
.ps-line.warn .msr {color: #b4561f;} .ps-line.tip .msr {color: var(--ochre);}
.ps-langlab {font-size: 0.75rem; font-weight: 700; color: #5d6a62; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: -6px;}
.ps-brand {display: flex; align-items: center; gap: 10px;}
.ps-stats {display: flex; gap: 34px; margin-top: 18px; flex-wrap: wrap;}
.ps-stats .v {font-size: 1.7rem; font-weight: 800; color: var(--ink); letter-spacing: -0.02em;}
.ps-stats .l {font-size: 0.8rem; color: var(--muted); max-width: 150px; line-height: 1.35;}
.ps-note {background: #fbfaf6; border: 1px solid var(--line); border-radius: 14px; padding: 12px 14px; font-size: 0.9rem; color: #2f3a34;}

/* buttons, tabs, metrics */
.stButton > button, .stDownloadButton > button, .stLinkButton > a {font-weight: 650;}
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {background: var(--ink); border-color: var(--ink);}
.stButton > button[kind="primary"]:hover, .stDownloadButton > button[kind="primary"]:hover {background: #2b3b33; border-color: #2b3b33;}
[data-testid="stPageLink"] a {padding-left: 2px;}
[data-testid="stPageLink"] p {color: var(--brand); font-weight: 650; font-size: 0.9rem;}
[data-testid="stMetric"] {background: var(--card); border: 1px solid var(--line); border-radius: 16px; padding: 10px 14px;}
[data-testid="stMetricValue"] > div {font-size: 1.55rem; font-weight: 800; overflow: visible; text-overflow: clip;}
[data-testid="stMetricLabel"] p {font-size: 0.8rem; color: var(--muted);}
.stTabs [data-baseweb="tab"] p {font-weight: 650;}

/* equal-height cards in a row: columns stretch to the tallest, cards fill their column */
[data-testid="stColumn"] > [data-testid="stVerticalBlock"] {height: 100%;}
[data-testid="stElementContainer"]:has(.ps-tile), [data-testid="stElementContainer"]:has(.ps-kpi) {flex: 1 1 auto;}
[data-testid="stElementContainer"]:has(.ps-tile) *:has(.ps-tile), [data-testid="stElementContainer"]:has(.ps-kpi) *:has(.ps-kpi) {height: 100%;}
.ps-card-end {margin-top: auto;}
[data-testid="stElementContainer"]:has(.ps-card-end) {margin-top: auto;}
[class*="st-key-dcard_"] [data-testid="stImage"] img {height: 260px; width: 100%; object-fit: contain;}
.ps-foot {color: #7a837d; font-size: 0.76rem; margin-top: 28px; border-top: 1px solid var(--line); padding-top: 10px; line-height: 1.5;}

/* phones */
@media (max-width: 640px) {
  .block-container {padding-left: 1rem; padding-right: 1rem; padding-top: 3.6rem !important;}
  header[data-testid="stHeader"] {background: rgba(246,244,238,0.94); backdrop-filter: blur(6px); border-bottom: 1px solid var(--line);}
  .ps-h1 {font-size: 1.75rem;} .ps-sub {font-size: 0.96rem;}
  [data-testid="stHorizontalBlock"]:has(.ps-kpi) {flex-wrap: wrap; gap: 10px;}
  [data-testid="stHorizontalBlock"]:has(.ps-kpi) > [data-testid="stColumn"] {flex: 1 1 calc(50% - 10px) !important; min-width: calc(50% - 10px) !important;}
  [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) {flex-wrap: wrap; gap: 8px;}
  [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) > [data-testid="stColumn"] {flex: 1 1 calc(50% - 8px) !important; min-width: calc(50% - 8px) !important;}
  .ps-kpi {min-height: 0; padding: 12px 14px;} .ps-kpi .v {font-size: 1.35rem;}
  [data-testid="stMetricValue"] > div {font-size: 1.15rem;}
  .ps-tile {min-height: 0;}
  .fgrid {grid-template-columns: 1fr;}
  .fb {grid-template-columns: 120px 1fr 56px;}
  .ps-stats {gap: 18px;}
  [class*="st-key-dcard_"] [data-testid="stImage"] img {height: 220px;}
}
</style>
"""


def banner(title, sub, chips=(), eyebrow=None):
    """Clean page header: small label, large title, muted subtitle, optional meta pills."""
    st.markdown(CSS, unsafe_allow_html=True)
    eb = f"<div class='ps-eyebrow'><i></i>{eyebrow}</div>" if eyebrow else ""
    ch = ("<div class='ps-meta'>" + "".join(f"<span>{c}</span>" for c in chips) + "</div>") if chips else ""
    st.markdown(f"{eb}<div class='ps-h1'>{title}</div><div class='ps-sub'>{sub}</div>{ch}", unsafe_allow_html=True)


def h2(text):
    st.markdown(f"<div class='ps-h2'>{text}</div>", unsafe_allow_html=True)


def kpi(col, value, label):
    col.markdown(f"<div class='ps-kpi'><div class='v'>{value}</div><div class='l'>{label}</div></div>", unsafe_allow_html=True)


def tile_html(ic, title, d):
    return f"<div class='ps-tile'><div class='ps-ic'>{icon(ic)}</div><div class='t'>{title}</div><div class='d'>{d}</div></div>"


def line(ic, text, cls=""):
    return f"<div class='ps-line {cls}'>{icon(ic, 'sm')}<div>{text}</div></div>"


def footer():
    st.markdown("<div class='ps-foot'>" + tr(
        "PotharSight Assam · prototype for NESFIC 2026 challenge D13 (DST Assam – ASSAC) · built only on free, open data "
        "(Sentinel-1/2, ESA WorldCover, Esri LULC, Copernicus DEM, JRC, CHIRPS, ISRIC SoilGrids, OpenStreetMap, DES Assam) · "
        "decision support only – land ownership must be verified by the Revenue Department.",
        "PotharSight Assam · NESFIC 2026 প্ৰত্যাহ্বান D13 (DST অসম – ASSAC)ৰ বাবে প্ৰ'ট'টাইপ · কেৱল বিনামূলীয়া মুক্ত তথ্যৰ ওপৰত "
        "নিৰ্মিত (Sentinel-1/2, ESA WorldCover, Esri LULC, Copernicus DEM, JRC, CHIRPS, ISRIC SoilGrids, OpenStreetMap, DES অসম) · "
        "কেৱল সিদ্ধান্তৰ সহায় — মাটিৰ মালিকীস্বত্ব ৰাজহ বিভাগে নিশ্চিত কৰিব লাগিব।") + "</div>", unsafe_allow_html=True)


def legend_html():
    return "<div class='ps-legend'>" + "".join(
        f"<span style='background:{c}'></span>{g} · {n}" for _, g, n, c in GRADES) + "</div>"


def bars(wide, colors, horizontal=False, stack=True, height=320, unit=None, pct=False):
    """Bar chart with a full, untruncated legend under the chart; keeps the row and series order of `wide`."""
    import altair as alt
    unit = unit or tr("hectares", "হেক্টৰ")
    cat = wide.index.name or "item"
    w = wide.copy()
    w.index.name = cat
    series = [str(c) for c in w.columns]
    w.columns = series
    long = w.reset_index().melt(id_vars=cat, var_name="Series", value_name="value")
    long["order"] = long.Series.map({s: i for i, s in enumerate(series)})
    fmt = ".0f" if pct else ",.0f"
    val = alt.X if horizontal else alt.Y
    key = alt.Y if horizontal else alt.X
    v = val("value:Q", title=("% " if pct else "") + unit, stack="zero" if stack else None,
            axis=alt.Axis(format=",.0f", gridColor="#ebe7dc", domain=False, tickColor="#ebe7dc"))
    k = key(f"{cat}:N", sort=list(w.index), title=None, axis=alt.Axis(labelAngle=0, labelLimit=260, labelOverlap=False, domainColor="#d9d4c6"))
    enc = dict(color=alt.Color("Series:N", sort=series, scale=alt.Scale(domain=series, range=list(colors)[:len(series)]),
                               legend=alt.Legend(orient="bottom", title=None, labelLimit=0, symbolType="circle",
                                                 direction="horizontal", columns=min(len(series), 4), offset=6)),
               order=alt.Order("order:Q"),
               tooltip=[alt.Tooltip(f"{cat}:N", title=cat), alt.Tooltip("Series:N", title=" "),
                        alt.Tooltip("value:Q", title="%" if pct else unit, format=fmt)])
    if not stack:
        enc["yOffset" if horizontal else "xOffset"] = alt.YOffset("Series:N", sort=series) if horizontal else alt.XOffset("Series:N", sort=series)
    ch = alt.Chart(long).mark_bar(cornerRadiusEnd=3).encode(x=v if horizontal else k, y=k if horizontal else v, **enc)
    if horizontal:
        height = max(height, 30 * len(w))
    ch = ch.properties(height=height, background="transparent").configure_view(stroke=None).configure_axis(
        labelFont="Manrope", titleFont="Manrope", labelColor="#45524a", titleColor="#5d6a62").configure_legend(labelFont="Manrope", labelColor="#2f3a34")
    st.altair_chart(ch, use_container_width=True)
