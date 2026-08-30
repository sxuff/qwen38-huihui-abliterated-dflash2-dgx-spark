#!/usr/bin/env python3
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
data = json.loads((ROOT / "evidence/cross-study-comparison.json").read_text())
huihui = data["systems"]["huihui_radixark"]
no_spec = huihui["no_spec_followup"]
stock = data["systems"]["stock_radixark"]

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


def metric_panel(x1, x2, label, rate, quality, accent):
    d.rounded_rectangle((x1, 280, x2, 650), radius=18, fill=PANEL, outline=BORDER, width=2)
    d.rectangle((x1, 280, x2, 290), fill=accent)
    text(x1 + 40, 325, label, 29, accent, True)
    text(x1 + 40, 385, f"{rate:.2f}", 102, WHITE, True)
    text(x1 + 44, 495, "TOK/S", 27, MUTED, True)
    text(x1 + 40, 560, f"QUALITY  {quality}/27", 27, WHITE, True)
    text(x1 + 40, 605, "0 RUNTIME ERRORS", 23, MUTED, True)


d.rectangle((72, 70, 88, 830), fill=GREEN)
text(130, 80, "DFLASH2 MAKES ABLITERATED QWEN 4.71× FASTER", 43, WHITE, True)
text(130, 145, "Same Huihui-RadixArk target · 1× DGX Spark · whole-request rate", 28, MUTED)
text(130, 205, "Exact image and settings, speculative flags are the treatment", 23, GREEN, True)

metric_panel(
    130,
    720,
    "NO SPECULATION",
    no_spec["median_whole_request_tokens_per_second"],
    no_spec["quality_passes"],
    BLUE,
)
metric_panel(
    880,
    1470,
    "SGLANG + DFLASH2",
    huihui["median_whole_request_tokens_per_second"],
    huihui["quality_passes"],
    GREEN,
)

text(800, 455, f'{no_spec["dflash2_speedup_ratio"]:.2f}×', 48, WHITE, True, "mm")
text(800, 515, "SPEEDUP", 18, MUTED, True, "mm")

# Compact receipts.
d.rounded_rectangle((130, 690, 1470, 795), radius=14, fill="#101a28", outline=BORDER, width=2)
text(165, 713, "DFLASH RECEIPT", 22, AMBER, True)
text(415, 713, f'{huihui["spec_accept_rate"] * 100:.2f}% acceptance', 23, WHITE, True)
text(735, 713, f'{huihui["spec_accept_length_including_bonus"]:.2f} tokens / verify', 23, WHITE, True)
text(1080, 713, "0 bytes swap growth", 23, WHITE, True)
text(165, 755, f'Stock reference: 12.34 → {stock["median_whole_request_tokens_per_second"]:.2f} tok/s, 4.63×', 21, MUTED)

text(130, 825, "27 requests per arm · matched configuration · separate collection sessions · production restored", 21, MUTED)

out = ROOT / "assets/qwen38-huihui-radixark-result.png"
out.parent.mkdir(exist_ok=True)
img.save(out, optimize=True)
print(out, img.size)
