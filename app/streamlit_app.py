"""PotharSight Assam – portal entry: sign-in, then Home, Find land, Rankings, Advanced analysis and How it works.

Run:  streamlit run app/streamlit_app.py
Accounts: app/users.yaml holds user names with salted PBKDF2 password hashes (never plain passwords).
Create or reset an account:  python tools/make_user.py <username> "<Display name>" [role] [password]
"""
import hashlib
import hmac
import sys
from pathlib import Path

import streamlit as st
import yaml

APP = Path(__file__).resolve().parent
sys.path.insert(0, str(APP.parent))
sys.path.insert(0, str(APP))

st.set_page_config(page_title="PotharSight Assam – land for farming", page_icon=str(APP / "assets" / "icon.svg"), layout="wide")
from theme import CSS, DISTRICTS, DNAME, OUT, icon, lang_switch, tile_html, tr  # noqa: E402
import pandas as pd  # noqa: E402

# Public demo account shown on the sign-in page so evaluators can enter directly (prototype only).
DEMO_USER, DEMO_PASS = "evaluator", "pothar2026"


def users():
    try:
        if "users" in st.secrets:
            return {k: dict(v) for k, v in st.secrets["users"].items()}
    except Exception:
        pass
    f = APP / "users.yaml"
    return yaml.safe_load(f.read_text())["users"] if f.exists() else {}


def check(username, password):
    u = users().get(username.strip().lower())
    if not u:
        return None
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(u["salt"]), 200_000).hex()
    return u if hmac.compare_digest(h, u["hash"]) else None


def sign_in(uid, password):
    """Button callback: runs before the next script run, so the portal draws straight away (no second rerun)."""
    u = check(uid, password)
    if u:
        st.session_state.user = {"id": uid.strip().lower(), "name": u.get("name", uid), "role": u.get("role", "official")}
        st.session_state.pop("login_error", None)
    else:
        st.session_state.login_error = ("User ID or password is not correct.", "ব্যৱহাৰকাৰী আইডি বা পাছৱৰ্ড শুদ্ধ নহয়।")


def sign_in_form():
    sign_in(st.session_state.get("login_uid", ""), st.session_state.get("login_pw", ""))


@st.cache_data
def headline_numbers():
    sites = ha = 0
    for d in DISTRICTS:
        a = pd.read_csv(OUT / d / "field_crops" / "tables" / "priority_patches.csv", usecols=["area_ha"]).area_ha
        sites, ha = sites + len(a), ha + a.sum()
    return sites, ha


def login_page():
    # One top-level block: after sign-in the first element of the portal replaces it whole,
    # so no leftover sign-in boxes linger on screen while the portal loads.
    with st.container():
        st.markdown(CSS, unsafe_allow_html=True)
        st.markdown("<style>[data-testid='stSidebar'],[data-testid='stSidebarCollapsedControl']{display:none}</style>",
                    unsafe_allow_html=True)
        top_l, top_r = st.columns([3, 1.1], vertical_alignment="center")
        top_l.image(str(APP / "assets" / "logo.svg"), width=300)
        with top_r:
            lang_switch("lang_login")
        left, right = st.columns([1.35, 1], gap="large")
        sites, ha = headline_numbers()
        with left:
            st.markdown(
                "<div class='ps-eyebrow' style='margin-top:18px'><i></i>NESFIC 2026 · DST Assam – ASSAC · Challenge D13</div>"
                + "<div class='ps-h1' style='font-size:2.9rem'>" + tr("Find land that can be farmed — <em>and know why.</em>",
                                                                   "খেতি কৰিব পৰা মাটি বিচাৰক — <em>কাৰণসহ।</em>") + "</div>"
                + "<div class='ps-sub'>" + tr(
                    "A decision-support portal for agriculture and horticulture departments, district administration and planners "
                    "in Assam. It shows where unused land is, how suitable it is, and why — from free satellite data.",
                    "অসমৰ কৃষি আৰু উদ্যান বিভাগ, জিলা প্ৰশাসন আৰু পৰিকল্পনাকাৰীৰ বাবে এটা সিদ্ধান্ত-সহায়ক প'ৰ্টেল। অব্যৱহৃত মাটি ক'ত আছে, "
                    "কিমান উপযুক্ত আৰু কিয় — বিনামূলীয়া উপগ্ৰহ তথ্যৰ পৰা দেখুৱায়।") + "</div>"
                + "<div class='ps-stats'>"
                + f"<div><div class='v'>{len(DISTRICTS)}</div><div class='l'>" + tr("districts, the top 4 in Assam for unused cultivable land",
                                                                                  "জিলা — অব্যৱহৃত খেতিযোগ্য মাটিত অসমৰ শীৰ্ষ ৪") + "</div></div>"
                + f"<div><div class='v'>{sites:,}</div><div class='l'>" + tr("ranked sites, each with its reasons", "কাৰণসহ ক্ৰমবদ্ধ স্থান") + "</div></div>"
                + f"<div><div class='v'>{ha:,.0f}</div><div class='l'>" + tr("hectares of suitable unused land for field crops",
                                                                           "হেক্টৰ পথাৰ শস্যৰ উপযুক্ত অব্যৱহৃত মাটি") + "</div></div>"
                + "</div>", unsafe_allow_html=True)
        with right:
            with st.container(border=True, key="signin"):
                st.markdown(f"#### {tr('Sign in', 'ছাইন ইন')}")
                st.markdown(f"<div class='ps-note'>{icon('key', 'sm')} <b>{tr('Demo access for evaluators', 'মূল্যায়নকাৰীৰ বাবে ডেমো প্ৰৱেশ')}</b><br>"
                            f"{tr('User ID', 'ব্যৱহাৰকাৰী আইডি')}: <code>{DEMO_USER}</code> &nbsp; {tr('Password', 'পাছৱৰ্ড')}: <code>{DEMO_PASS}</code></div>",
                            unsafe_allow_html=True)
                st.button(tr("Enter with demo access", "ডেমো প্ৰৱেশেৰে সোমাওক"), icon=":material/arrow_forward:", type="primary",
                          use_container_width=True, on_click=sign_in, args=(DEMO_USER, DEMO_PASS))
                st.markdown("<div style='text-align:center;color:#7a837d;margin:4px 0;font-size:0.88rem'>"
                            + tr("or sign in with your own account", "অথবা নিজৰ একাউণ্টেৰে ছাইন ইন কৰক") + "</div>", unsafe_allow_html=True)
                with st.form("login", border=False):
                    st.text_input(tr("User ID", "ব্যৱহাৰকাৰী আইডি"), key="login_uid")
                    st.text_input(tr("Password", "পাছৱৰ্ড"), type="password", key="login_pw")
                    st.form_submit_button(tr("Sign in", "ছাইন ইন"), use_container_width=True, on_click=sign_in_form)
                if st.session_state.get("login_error"):
                    st.error(tr(*st.session_state.login_error))
        st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
        c = st.columns(3)
        for col, (ic, t1, d1) in zip(c, [
                ("travel_explore", tr("Find land", "মাটি বিচাৰক"), tr("Guided search in plain language — no GIS skills needed.",
                                                                  "সহজ ভাষাত নিৰ্দেশিত সন্ধান — GIS জ্ঞানৰ প্ৰয়োজন নাই।")),
                ("leaderboard", tr("Rank blocks", "ব্লকৰ ক্ৰম"), tr("See where to place programme targets first.",
                                                                 "আঁচনিৰ লক্ষ্য প্ৰথমে ক'ত দিব চাওক।")),
                ("fact_check", tr("See why", "কাৰণ চাওক"), tr("Every site explains its strengths and problems.",
                                                           "প্ৰতিটো স্থানে নিজৰ সবল দিশ আৰু সমস্যা দেখুৱায়।"))]):
            col.markdown(tile_html(ic, t1, d1), unsafe_allow_html=True)
        st.markdown("<div class='ps-foot'>" + tr(
            "Prototype for NESFIC 2026 · Challenge D13 (DST Assam – ASSAC). Built on free, open data. "
            "Production version: department log-ins with roles and an audit log.",
            "NESFIC 2026 · প্ৰত্যাহ্বান D13 (DST অসম – ASSAC)ৰ বাবে প্ৰ'ট'টাইপ। বিনামূলীয়া মুক্ত তথ্যৰ ওপৰত নিৰ্মিত। "
            "চূড়ান্ত সংস্কৰণত বিভাগীয় লগ-ইন, ভূমিকা আৰু অডিট লগ থাকিব।") + "</div>", unsafe_allow_html=True)


if "user" not in st.session_state:
    login_page()
    st.stop()

st.logo(str(APP / "assets" / "logo.svg"), size="large", icon_image=str(APP / "assets" / "icon.svg"))
pg = st.navigation({
    tr("Start here", "ইয়াৰ পৰা আৰম্ভ কৰক"): [
        st.Page("views/home.py", title=tr("Home", "মূল পৃষ্ঠা"), icon=":material/home:", default=True)],
    tr("For officials", "বিষয়াসকলৰ বাবে"): [
        st.Page("views/official.py", title=tr("Find land for farming", "খেতিৰ মাটি বিচাৰক"), icon=":material/travel_explore:"),
        st.Page("views/rankings.py", title=tr("Compare districts & blocks", "জিলা আৰু ব্লক তুলনা"), icon=":material/leaderboard:")],
    tr("For GIS staff & planners", "GIS কৰ্মী আৰু পৰিকল্পনাকাৰীৰ বাবে"): [
        st.Page("views/analyst.py", title=tr("Advanced map analysis", "উন্নত মানচিত্ৰ বিশ্লেষণ"), icon=":material/layers:"),
        st.Page("views/about.py", title=tr("How it works & validation", "কেনেকৈ কাম কৰে আৰু পৰীক্ষা"), icon=":material/fact_check:")],
})
with st.sidebar:
    st.divider()
    lang_switch("lang_sidebar")
    st.markdown(f"<div style='margin-top:10px'>{icon('account_circle')} <b>{st.session_state.user['name']}</b></div>",
                unsafe_allow_html=True)
    st.button(tr("Sign out", "লগ আউট"), icon=":material/logout:", use_container_width=True,
              on_click=lambda: [st.session_state.pop(k) for k in list(st.session_state) if k != "lang"])
    st.caption(tr("Prototype · NESFIC 2026 · D13", "প্ৰ'ট'টাইপ · NESFIC 2026 · D13"))
pg.run()
