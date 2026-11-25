"""End-to-end portal test + screenshots (portal must run on :8501).   python tools/portal_test.py [district label]
Uses the public demo button on the sign-in page, visits every page, reports Streamlit exceptions,
saves screenshots to docs/pow/screens/portal_*.png.
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "pow" / "screens"
OUT.mkdir(parents=True, exist_ok=True)
district = sys.argv[1] if len(sys.argv) > 1 else "Kamrup (Rural)"
errors = []


def shot(pg, name, wait=2500, full=False):
    pg.wait_for_timeout(wait)
    if pg.locator('[data-testid="stException"]').count():
        errors.append(f"{name}: " + pg.locator('[data-testid="stException"]').first.inner_text()[:600])
    pg.screenshot(path=OUT / f"portal_{name}.png", full_page=full)


def nav(pg, label):
    pg.locator('[data-testid="stSidebarNav"]').get_by_text(label, exact=True).click()


with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge")
    pg = b.new_page(viewport={"width": 1500, "height": 950}, device_scale_factor=1.5)
    pg.goto("http://localhost:8501", wait_until="networkidle")
    pg.get_by_role("button", name="Enter with demo access").wait_for(timeout=60000)
    shot(pg, "0_login", 1500)
    pg.get_by_role("button", name="Enter with demo access").click()
    pg.get_by_text("What would you like to do?").wait_for(timeout=60000)
    shot(pg, "1_home", 5000)
    nav(pg, "Find land for farming")
    pg.get_by_text("Which district are you planning for?").wait_for(timeout=60000)
    shot(pg, "2_district")
    key = {"Kamrup (Rural)": "kamrup"}.get(district, district.lower())
    pg.locator(f".st-key-d_{key} button").click()
    pg.get_by_text("What do you want to grow").wait_for(timeout=30000)
    shot(pg, "3_purpose")
    pg.get_by_role("button", name="Select Field crops").click()
    pg.get_by_text("What kind of land are you looking for?").wait_for(timeout=60000)
    pg.wait_for_timeout(3000)
    shot(pg, "4_land")
    pg.get_by_role("button", name="Show me the land").click()
    pg.get_by_text("Sites found").wait_for(timeout=90000)
    pg.wait_for_timeout(4000)
    pg.locator("iframe").first.scroll_into_view_if_needed()
    shot(pg, "5_results_map", 7000)
    pg.get_by_role("tab", name="Best sites, with reasons").click()
    pg.wait_for_timeout(1500)
    pg.get_by_role("tab", name="Best sites, with reasons").scroll_into_view_if_needed()
    shot(pg, "6_results_list")
    pg.get_by_role("tab", name="Compare blocks").click()
    shot(pg, "7_results_blocks")
    nav(pg, "Compare districts & blocks")
    pg.get_by_text("Top blocks across all districts").wait_for(timeout=60000)
    shot(pg, "8_rankings", 4000)
    nav(pg, "Advanced map analysis")
    pg.get_by_text("Map & ranking").wait_for(timeout=90000)
    shot(pg, "9_analyst", 7000)
    nav(pg, "How it works & validation")
    pg.get_by_text("Criteria (editable").wait_for(timeout=60000)
    shot(pg, "10_about", 2500)
    pg.get_by_role("tab", name="Validation").click()
    shot(pg, "11_validation", 2500)
    b.close()
print("ERRORS:\n" + "\n".join(errors) if errors else "OK - no exceptions")
