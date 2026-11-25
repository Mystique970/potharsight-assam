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
from theme import CSS, DISTRICTS, DNAME  # noqa: E402

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
        st.session_state.login_error = "User ID or password is not correct."


def sign_in_form():
    sign_in(st.session_state.get("login_uid", ""), st.session_state.get("login_pw", ""))


def login_page():
    # One top-level block: after sign-in the first element of the portal replaces it whole,
    # so no leftover sign-in boxes linger on screen while the portal loads.
    with st.container():
        st.markdown(CSS, unsafe_allow_html=True)
        st.markdown("<style>[data-testid='stSidebar']{display:none}</style>", unsafe_allow_html=True)
        left, right = st.columns([1.25, 1], gap="large")
        with left:
            st.image(str(APP / "assets" / "logo.svg"), width=380)
            st.markdown(
                "<div class='ps-banner' style='margin-top:10px'><h1>Find land for farming – faster, with reasons</h1>"
                "<div class='sub'>A decision-support portal for Agriculture & Horticulture departments, district administration "
                "and planners in Assam. It shows where unused land is, how suitable it is, and why.</div>"
                f"<div class='chips'><span class='ps-chip'>🗺️ {len(DISTRICTS)} districts</span><span class='ps-chip'>🛰️ 9 satellite & open data layers</span>"
                "<span class='ps-chip'>📐 30 m detail</span><span class='ps-chip'>📍 site, block & circle ranking</span>"
                "<span class='ps-chip'>⬇️ Excel · Google Earth · GIS downloads</span></div></div>", unsafe_allow_html=True)
            c = st.columns(3)
            for col, (ic, t, d) in zip(c, [("🔍", "Find land", "Guided search in plain language – no GIS skills needed"),
                                           ("🏆", "Rank blocks", "Where to place programme targets first"),
                                           ("❓", "See why", "Every site explains its strengths and problems")]):
                col.markdown(f"<div class='ps-tile'><div class='ic'>{ic}</div><div class='t'>{t}</div><div class='d'>{d}</div></div>",
                             unsafe_allow_html=True)
            st.caption("Districts: " + " · ".join(DNAME[d] for d in DISTRICTS))
        with right:
            st.markdown("### Sign in")
            with st.container(border=True):
                st.info(f"**Demo access for evaluators**  \nUser ID: `{DEMO_USER}`  \nPassword: `{DEMO_PASS}`")
                st.button("➡️ Enter with demo access", type="primary", use_container_width=True,
                          on_click=sign_in, args=(DEMO_USER, DEMO_PASS))
                st.markdown("<div style='text-align:center;color:#6b7280;margin:6px 0'>or sign in with your own account</div>",
                            unsafe_allow_html=True)
                with st.form("login"):
                    st.text_input("User ID", key="login_uid")
                    st.text_input("Password", type="password", key="login_pw")
                    st.form_submit_button("Sign in", use_container_width=True, on_click=sign_in_form)
                if st.session_state.get("login_error"):
                    st.error(st.session_state.login_error)
            st.caption("Prototype for NESFIC 2026 · Challenge D13 (DST Assam – ASSAC). Built on free, open data. "
                       "Production version: department log-ins with roles and an audit log.")


if "user" not in st.session_state:
    login_page()
    st.stop()

st.logo(str(APP / "assets" / "logo.svg"), size="large", icon_image=str(APP / "assets" / "icon.svg"))
pg = st.navigation({
    "Start here": [st.Page("views/home.py", title="Home – overview", icon="🏠", default=True)],
    "For officials": [st.Page("views/official.py", title="Find land for farming", icon="🔍"),
                      st.Page("views/rankings.py", title="Compare districts & blocks", icon="🏆")],
    "For GIS staff & planners": [st.Page("views/analyst.py", title="Advanced map analysis", icon="🛠️"),
                                 st.Page("views/about.py", title="How it works & validation", icon="📘")],
})
with st.sidebar:
    st.markdown("---")
    st.markdown(f"👤 **{st.session_state.user['name']}**")
    st.button("Sign out", use_container_width=True, on_click=lambda: st.session_state.clear())
    st.caption("Prototype · NESFIC 2026 · D13")
pg.run()
