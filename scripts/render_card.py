#!/usr/bin/env python3
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
data = json.loads((ROOT / "evidence/cross-study-comparison.json").read_text())
stock = data["systems"]["stock_radixark"]
huihui = data["systems"]["huihui_radixark"]
ara = data["systems"]["aday_ara"]
delta = data["derived"]["huihui_vs_stock_rate_percent"]

W, H = 1600, 900
BG = "#08111f"
PANEL = "#0d192b"
BORDER = "#223550"
WHITE = "#f5f8fc"
MUTED = "#9fb0c6"
GREEN = "#55e6a5"
BLUE = "#6eb8ff"
AMBER = "#f4c26b"

img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)


def font(size, bold=False):
    path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    return ImageFont.truetype(path, size)


def text(x, y, value, size, color=WHITE, bold=False, anchor=None):
    d.text((x, y), value, font=font(size, bold), fill=color, anchor=anchor)


def metric_panel(x1, x2, label, system, accent):
    d.rounded_rectangle((x1, 270, x2, 650), radius=18, fill=PANEL, outline=BORDER, width=2)
    d.rectangle((x1, 270, x2, 280), fill=accent)
    text(x1 + 40, 315, label, 28, accent, True)
    text(x1 + 40, 370, f'{system["median_whole_request_tokens_per_second"]:.2f}', 100, WHITE, True)
    text(x1 + 44, 480, "TOK/S", 27, MUTED, True)
    text(x1 + 40, 545, f'{system["spec_accept_rate"] * 100:.2f}% ACCEPTANCE', 27, WHITE, True)
    text(x1 + 40, 590, f'{system["spec_accept_length_including_bonus"]:.2f} TOKENS / VERIFY', 25, MUTED, True)


d.rectangle((72, 70, 88, 830), fill=GREEN)
text(130, 82, "STOCK-LEVEL SPEED. ABLITERATED.", 48, WHITE, True)
text(130, 150, "Qwen3.8-27B on 1× DGX Spark · SGLang + DFlash2", 29, MUTED)
text(130, 205, "Primary public comparison", 24, GREEN, True)

metric_panel(130, 720, "STOCK RADIXARK", stock, BLUE)
metric_panel(880, 1470, "HUIHUI-RADIXARK", huihui, GREEN)

text(800, 465, f"+{delta:.2f}%", 42, WHITE, True, "mm")
text(800, 515, "MEASURED", 18, MUTED, True, "mm")

# Secondary ARA reference strip.
d.rounded_rectangle((130, 690, 1470, 790), radius=14, fill="#101a28", outline=BORDER, width=2)
text(165, 716, "ARA REFERENCE", 23, AMBER, True)
text(410, 716, f'{ara["median_whole_request_tokens_per_second"]:.2f} tok/s', 24, WHITE, True)
text(700, 716, f'{ara["spec_accept_rate"] * 100:.2f}% acceptance', 24, WHITE, True)
text(1040, 716, f'{ara["spec_accept_length_including_bonus"]:.2f} tokens / verify', 24, WHITE, True)
text(165, 755, "Higher acceptance, lower end-to-end speed", 20, MUTED)

text(130, 825, "Separate study sessions · identical fixture bytes and DFlash2 draft · whole-request completion rate", 21, MUTED)

out = ROOT / "assets/qwen38-huihui-radixark-result.png"
out.parent.mkdir(exist_ok=True)
img.save(out, optimize=True)
print(out, img.size)
