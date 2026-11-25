"""End-to-end portal test + screenshots (portal must run on :8501).   python tools/portal_test.py [desktop|mobile|assamese|all]
Signs in with the public demo button, walks the guided search and every page, reports Streamlit exceptions and saves
screenshots to docs/pow/screens/:  portal_*.png (desktop 1440x900), mobile_*.png (phone 390x844), as_*.png (Assamese).
"""
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "pow" / "screens"
OUT.mkdir(parents=True, exist_ok=True)
mode = sys.argv[1] if len(sys.argv) > 1 else "all"
errors = []


def shot(pg, name, wait=2500, full=False):
    pg.wait_for_timeout(wait)
    if pg.locator('[data-testid="stException"]').count():
        errors.append(f"{name}: " + pg.locator('[data-testid="stException"]').first.inner_text()[:600])
    pg.screenshot(path=OUT / f"{name}.png", full_page=full)


def text(pg, s, timeout=90000):
    pg.get_by_text(s).first.wait_for(timeout=timeout)


def sign_in(pg, assamese=False):
    pg.goto("http://localhost:8501", wait_until="networkidle")
    text(pg, "Demo access for evaluators")
    if assamese:
        pg.get_by_text("অসমীয়া", exact=True).first.click()
        text(pg, "মূল্যায়নকাৰীৰ বাবে ডেমো প্ৰৱেশ")


def walk(pg, prefix, assamese=False, mobile=False):
    T = (lambda en, as_: as_) if assamese else (lambda en, as_: en)
    sign_in(pg, assamese)
    shot(pg, f"{prefix}0_login", 1500)
    if mobile:
        pg.locator(".st-key-signin").scroll_into_view_if_needed()
        shot(pg, f"{prefix}0_login_signin", 800)
    pg.get_by_role("button", name=re.compile(T("Enter with demo access", "ডেমো প্ৰৱেশেৰে সোমাওক"))).click()
    text(pg, T("What would you like to do?", "আপুনি কি কৰিব বিচাৰে?"))
    shot(pg, f"{prefix}1_home", 4500, )
    pg.get_by_role("link", name=re.compile(T("Open", "খোলক"))).first.click()                 # Find land
    text(pg, T("Which district are you planning for?", "কোন জিলাৰ বাবে পৰিকল্পনা কৰিছে?"))
    shot(pg, f"{prefix}2_district", )
    pg.locator(".st-key-d_cachar button" if not mobile else ".st-key-d_kamrup button").click()
    text(pg, T("What do you want to grow", "কি খেতি কৰিব বিচাৰে"))
    shot(pg, f"{prefix}3_purpose", )
    pg.locator(".st-key-p_field_crops button").click()
    text(pg, T("What kind of land are you looking for?", "কেনেধৰণৰ মাটি বিচাৰিছে?"))
    shot(pg, f"{prefix}4_land", 3000, )
    pg.get_by_role("button", name=re.compile(T("Show me the land", "মাটি দেখুৱাওক"))).click()
    text(pg, T("Sites found", "পোৱা স্থান"))
    pg.frame_locator("iframe").first.locator(".leaflet-container").wait_for(timeout=90000)
    shot(pg, f"{prefix}5_results", 5000)
    pg.locator("iframe").first.scroll_into_view_if_needed()
    shot(pg, f"{prefix}5_results_map", 3000)
    pg.get_by_role("tab").nth(1).click()
    pg.get_by_role("tab").nth(1).scroll_into_view_if_needed()
    shot(pg, f"{prefix}6_results_list", 2000)
    pg.get_by_role("tab").nth(2).click()
    pg.get_by_role("tab").nth(2).scroll_into_view_if_needed()
    shot(pg, f"{prefix}7_results_blocks", 2500)
    if mobile or assamese:
        return
    nav = pg.locator('[data-testid="stSidebarNav"]')
    nav.get_by_text("Compare districts & blocks", exact=True).click()
    text(pg, "Top blocks across all districts")
    shot(pg, f"{prefix}8_rankings", 4000)
    nav.get_by_text("Advanced map analysis", exact=True).click()
    text(pg, "Map & ranking")
    shot(pg, f"{prefix}9_analyst", 7000)
    nav.get_by_text("How it works & validation", exact=True).click()
    text(pg, "Criteria (editable")
    shot(pg, f"{prefix}10_about", 2500)
    pg.get_by_role("tab").nth(2).click()
    shot(pg, f"{prefix}11_validation", 2500)


with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge")
    if mode in ("desktop", "all"):
        pg = b.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1.5)
        walk(pg, "portal_")
        pg.close()
    if mode in ("mobile", "all"):
        ctx = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        walk(ctx.new_page(), "mobile_", mobile=True)
        ctx.close()
    if mode in ("assamese", "all"):
        pg = b.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1.5)
        walk(pg, "as_", assamese=True)
        pg.close()
        ctx = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        pg = ctx.new_page()
        sign_in(pg, True)
        shot(pg, "as_mobile_0_login", 1500)
        pg.get_by_role("button", name=re.compile("ডেমো প্ৰৱেশেৰে সোমাওক")).click()
        text(pg, "আপুনি কি কৰিব বিচাৰে?")
        shot(pg, "as_mobile_1_home", 4500)
        pg.get_by_role("link", name=re.compile("খোলক")).first.click()
        text(pg, "কোন জিলাৰ বাবে পৰিকল্পনা কৰিছে?")
        pg.locator(".st-key-d_kamrup button").click()
        text(pg, "কি খেতি কৰিব বিচাৰে")
        pg.locator(".st-key-p_field_crops button").click()
        text(pg, "কেনেধৰণৰ মাটি বিচাৰিছে?")
        pg.get_by_role("button", name=re.compile("মাটি দেখুৱাওক")).click()
        text(pg, "পোৱা স্থান")
        pg.get_by_role("tab").nth(1).click()
        pg.get_by_role("tab").nth(1).scroll_into_view_if_needed()
        shot(pg, "as_mobile_6_results_list", 6000)
        ctx.close()
    b.close()
print("ERRORS:\n" + "\n".join(errors) if errors else "OK - no exceptions")
