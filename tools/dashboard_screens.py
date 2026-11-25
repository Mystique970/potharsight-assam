"""Capture dashboard screenshots for the Proof of Work (dashboard must be running on :8501).

python tools/dashboard_screens.py [district_label] [programme_label]
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parents[1] / "docs" / "pow" / "screens"
OUT.mkdir(parents=True, exist_ok=True)
district = sys.argv[1] if len(sys.argv) > 1 else None
programme = sys.argv[2] if len(sys.argv) > 2 else None
tag = (district or "default").lower().replace(" ", "_") + ("_" + programme.split()[0].lower() if programme else "")

with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge")
    pg = b.new_page(viewport={"width": 1500, "height": 950}, device_scale_factor=1.5)
    pg.goto("http://localhost:8501", wait_until="networkidle")
    pg.wait_for_selector("text=Map & ranking", timeout=90000)

    def pick(label_text, option):
        box = pg.locator(f'[data-testid="stSelectbox"]:has-text("{label_text}")').first
        box.click()
        pg.get_by_role("option", name=option).first.click()
        pg.wait_for_timeout(6000)

    if district:
        pick("District", district)
    if programme:
        pick("Programme", programme)
    pg.wait_for_timeout(8000)
    pg.screenshot(path=OUT / f"{tag}_1_map.png")
    for i, t in enumerate(["Why this result", "Downloads", "Validation", "Method & scalability"], 2):
        pg.get_by_role("tab", name=t).click()
        pg.wait_for_timeout(2500)
        pg.screenshot(path=OUT / f"{tag}_{i}_{t.split()[0].lower()}.png", full_page=False)
    b.close()
print("screens in", OUT)
