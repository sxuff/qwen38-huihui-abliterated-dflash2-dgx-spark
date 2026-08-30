#!/usr/bin/env python3
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
data = json.loads((ROOT / "evidence/cross-study-comparison.json").read_text())
parity = json.loads((ROOT / "evidence/huihui-cross-arm-parity.json").read_text())
huihui = data["systems"]["huihui_radixark"]
no_spec = huihui["no_spec_followup"]
stock = data["systems"]["stock_radixark"]
REPO_URL = "github.com/sxuff/qwen38-huihui-abliterated-dflash2-dgx-spark"

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


d.rectangle((72, 70, 88, 845), fill=GREEN)
text(130, 72, "DFLASH2 MAKES ABLITERATED QWEN 4.71× FASTER", 43, WHITE, True)
text(130, 132, "Same target · 1× DGX Spark · whole-request rate", 27, MUTED)
text(
    130,
    184,
    f'Target: {huihui["target"]}@{huihui["target_revision"]}',
    20,
    GREEN,
    True,
)

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
text(165, 710, "DFLASH RECEIPT", 21, AMBER, True)
text(410, 710, f'{huihui["spec_accept_rate"] * 100:.2f}% acceptance', 22, WHITE, True)
text(715, 710, f'{huihui["spec_accept_length_including_bonus"]:.2f} tokens / verify', 22, WHITE, True)
text(1060, 710, f'BYTE PARITY  {parity["assembled_assistant_envelope_byte_matches"]}/27', 22, WHITE, True)
text(165, 752, f'Stock DFlash2: {stock["median_whole_request_tokens_per_second"]:.2f} tok/s · token-ID parity not captured', 20, MUTED)

text(130, 813, "27 requests per arm · matched configuration · separate sessions · 24/27 quality in both arms", 19, MUTED)
text(130, 850, REPO_URL, 18, GREEN, True)

out = ROOT / "assets/qwen38-huihui-radixark-result.png"
out.parent.mkdir(exist_ok=True)
img.save(out, optimize=True)
print(out, img.size)
