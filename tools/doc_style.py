"""Shared look for the Proof of Work and Technical Annex PDFs (clean, light, flat) + device frames for screenshots."""
import base64
import io
import subprocess
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SCREENS = ROOT / "docs" / "pow" / "screens"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

FONTS = ("<link href='https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800"
         "&family=Noto+Sans+Bengali:wght@400;600&display=swap' rel='stylesheet'>")

CSS = """
@page { size: A4; margin: 13mm 13mm 14mm 13mm; }
:root { --ink:#16231d; --muted:#5d6a62; --line:#e4dfd2; --brand:#1d6b3a; --soft:#eef4ec; --cream:#f6f4ee; --ochre:#a8701a; }
body { font-family: 'Manrope', 'Noto Sans Bengali', 'Segoe UI', Arial, sans-serif; font-size: 9.6pt; color: var(--ink); line-height: 1.45; margin: 0; }
h1 { font-size: 26pt; font-weight: 800; letter-spacing: -0.03em; margin: 6px 0 4px; line-height: 1.1; }
h2 { font-size: 15pt; font-weight: 800; letter-spacing: -0.02em; margin: 0 0 8px; page-break-after: avoid; }
h3 { font-size: 10.8pt; font-weight: 750; margin: 12px 0 4px; page-break-after: avoid; }
p { margin: 3px 0 6px; }
.page { page-break-after: always; position: relative; }
.eyebrow { display: inline-block; border: 1px solid var(--line); background: #fbfaf6; border-radius: 999px; padding: 2px 10px;
  font-size: 7.4pt; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: #3f4b44; }
.eyebrow i { display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: var(--brand); margin-right: 6px; vertical-align: 1px; }
.lead { font-size: 11.5pt; color: var(--muted); max-width: 165mm; }
.small { font-size: 8pt; color: var(--muted); }
.cap { font-size: 7.8pt; color: var(--muted); margin: 3px 0 8px; } .cap b { color: var(--ink); }
table.t { border-collapse: collapse; width: 100%; font-size: 8.2pt; margin: 4px 0 8px; }
table.t th { text-align: left; font-weight: 700; color: var(--muted); border-bottom: 1.5px solid var(--ink); padding: 3px 5px; font-size: 7.8pt; }
table.t td { border-bottom: 1px solid var(--line); padding: 3px 5px; vertical-align: top; }
.kpi { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; margin: 8px 0; }
.k { border: 1px solid var(--line); border-radius: 12px; padding: 7px 9px; background: #fff; }
.k b { display: block; font-size: 14pt; font-weight: 800; letter-spacing: -0.02em; } .k span { font-size: 7.6pt; color: var(--muted); }
.card { border: 1px solid var(--line); border-radius: 12px; padding: 8px 10px; background: #fff; margin: 6px 0; }
.note { background: var(--cream); border: 1px solid var(--line); border-radius: 12px; padding: 7px 10px; font-size: 8.6pt; margin: 6px 0; }
.formula { background: var(--soft); border-radius: 10px; padding: 7px 10px; font-family: Consolas, 'Courier New', monospace; font-size: 8.6pt; margin: 5px 0; }
.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; } .grid3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.flow { display: flex; align-items: stretch; gap: 4px; margin: 6px 0 10px; }
.flow .box { flex: 1; border: 1px solid var(--line); border-radius: 10px; padding: 6px 7px; font-size: 7.8pt; background: #fff; }
.flow .box b { display: block; font-size: 8.4pt; } .flow .arr { color: var(--brand); font-weight: 800; align-self: center; }
img { max-width: 100%; }
.fig img { border: 1px solid var(--line); border-radius: 6px; }
ul { margin: 2px 0 6px 16px; padding: 0; } li { margin: 1px 0; }
.foot { position: fixed; bottom: -8mm; left: 0; right: 0; font-size: 7pt; color: #8a928c; border-top: 1px solid var(--line); padding-top: 3px; }
/* device frames */
.laptop { margin: 4px auto 2px; } .laptop .scr { background: #1d2420; border-radius: 9px 9px 0 0; padding: 6px 6px 7px; }
.laptop .scr img { display: block; width: 100%; border-radius: 2px; }
.laptop .base { height: 7px; background: linear-gradient(#d9d5ca, #bdb8ac); border-radius: 0 0 10px 10px; margin: 0 -12px; }
.phone { background: #18211c; border-radius: 18px; padding: 5px; box-shadow: 0 1px 3px rgba(0,0,0,0.12); }
.phone img { display: block; width: 100%; border-radius: 13px; }
.phones { display: grid; gap: 8px; } .phones .c { font-size: 7.4pt; color: var(--muted); text-align: center; margin-top: 3px; line-height: 1.3; }
.phones .c b { color: var(--ink); display: block; font-size: 7.8pt; }
.step { display: inline-block; background: var(--ink); color: #fff; border-radius: 999px; padding: 0 6px; font-size: 7pt; font-weight: 700; margin-bottom: 2px; }
"""


def b64(path, maxpx=1400, q=74, crop=None):
    p = Path(path)
    if not p.exists():
        return None
    im = Image.open(p).convert("RGB")
    if crop:
        w, h = im.size
        im = im.crop((int(crop[0] * w), int(crop[1] * h), int(crop[2] * w), int(crop[3] * h)))
    if im.width > maxpx:
        im = im.resize((maxpx, int(im.height * maxpx / im.width)), Image.LANCZOS)
    b = io.BytesIO()
    im.save(b, "JPEG", quality=q, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()


def img(path, maxpx=1400, width="100%", crop=None):
    s = b64(path, maxpx, crop=crop)
    return f"<div class='fig'><img src='{s}' style='width:{width}'></div>" if s else f"<p class='small'>[missing {Path(path).name}]</p>"


def laptop(name, caption="", width="100%", maxpx=1500, crop=None):
    s = b64(SCREENS / name, maxpx, crop=crop)
    if not s:
        return f"<p class='small'>[missing {name}]</p>"
    return (f"<div class='laptop' style='width:{width}'><div class='scr'><img src='{s}'></div><div class='base'></div></div>"
            + (f"<div class='cap'>{caption}</div>" if caption else ""))


def phones(items, cols=4, maxpx=520):
    """items: list of (screenshot name, title, caption)."""
    cells = []
    for name, title, cap in items:
        s = b64(SCREENS / name, maxpx)
        inner = f"<div class='phone'><img src='{s}'></div>" if s else f"<p class='small'>[missing {name}]</p>"
        cells.append(f"<div>{inner}<div class='c'><b>{title}</b>{cap}</div></div>")
    return f"<div class='phones' style='grid-template-columns:repeat({cols},1fr)'>" + "".join(cells) + "</div>"


def flow(steps):
    return "<div class='flow'>" + "<span class='arr'>›</span>".join(f"<div class='box'>{s}</div>" for s in steps) + "</div>"


def page(title, body, eyebrow=None):
    eb = f"<div class='eyebrow'><i></i>{eyebrow}</div>" if eyebrow else ""
    return f"<div class='page'>{eb}<h2 style='margin-top:6px'>{title}</h2>{body}</div>"


def to_pdf(html_path: Path, pdf_path: Path):
    subprocess.run([EDGE, "--headless", "--disable-gpu", "--no-pdf-header-footer", "--virtual-time-budget=15000",
                    f"--print-to-pdf={pdf_path}", html_path.as_uri()], check=False, timeout=240)
    return pdf_path
