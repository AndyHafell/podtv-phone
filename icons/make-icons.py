#!/usr/bin/env python3
"""Build the home-screen icons from the FunBun app icon.

Run from projects/funbun:   python3 phone/icons/make-icons.py

app/build/icon.icns is a macOS icon — artwork on a rounded tile inside a
transparent drop-shadow margin. iOS and Android both apply their OWN mask to
whatever you give them, so handing over the macOS tile means rounding it twice:
the mark ends up small inside a pale frame. This lifts the mark off the tile and
sets it on a flat square, which is what both platforms actually want.

Two traps, both hit on the way here and both commented where they bite.
"""
import subprocess, tempfile, pathlib
from PIL import Image
import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[2]
OUT = REPO / "phone" / "icons"
SIZES = [("apple-touch-icon", 180), ("icon-192", 192), ("icon-512", 512)]

with tempfile.TemporaryDirectory() as tmp:
    png = pathlib.Path(tmp) / "icon1024.png"
    subprocess.run(["sips", "-s", "format", "png", "--resampleHeightWidth", "1024", "1024",
                    str(REPO / "app" / "build" / "icon.icns"), "--out", str(png)],
                   check=True, capture_output=True)
    src = Image.open(png).convert("RGBA")

tile = src.crop(src.split()[3].getbbox())          # drop the macOS shadow margin
a = np.asarray(tile).astype(np.float32)
H, W = a.shape[:2]

# The mark is gold and its tile is neutral grey, so red-minus-blue separates
# them and the anti-aliased edge falls out as a soft alpha.
rb = a[:, :, 0] - a[:, :, 2]
alpha = np.clip((rb - 24) / 46.0, 0, 1) * (a[:, :, 3] / 255.0)

# TRAP 1: the tile's bevel is lit WARM, so red-minus-blue finds the rim as well
# as the mark — 8,792 border pixels at up to 0.39 alpha, which came through as a
# ghost rounded-rect outline, the exact frame this script exists to remove. The
# mark is central and the rim is not, so a radial cut is enough.
yy, xx = np.mgrid[0:H, 0:W]
r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
alpha[r > 0.78] = 0

glyph = Image.fromarray(np.dstack([a[:, :, :3], alpha * 255]).astype(np.uint8), "RGBA")
glyph = glyph.crop(glyph.split()[3].point(lambda v: 255 if v > 40 else 0).getbbox())

# TRAP 2: the background is a two-stop gradient sampled from the tile, NOT the
# tile's own pixels. Reading a column and stretching it turns the artwork's fine
# grain into horizontal scan lines; extending each row's edge pixel into the
# corners smears the lit rim into stripes. Two medians and a straight ramp.
def swatch(fy):
    y, x = int(H * fy), int(W * 0.11)
    return np.median(a[y - 14:y + 14, x - 14:x + 14, :3].reshape(-1, 3), axis=0)

S = 1024
ramp = np.linspace(0, 1, S)[:, None]
bg = np.repeat((swatch(0.16) * (1 - ramp) + swatch(0.86) * ramp)[:, None, :], S, axis=1)
out = Image.fromarray(bg.astype(np.uint8), "RGB")

gw, gh = glyph.size
s = int(S * 0.74) / max(gw, gh)
glyph = glyph.resize((int(gw * s), int(gh * s)), Image.LANCZOS)
out.paste(glyph, ((S - glyph.size[0]) // 2, (S - glyph.size[1]) // 2), glyph)

for name, size in SIZES:
    out.resize((size, size), Image.LANCZOS).save(OUT / f"{name}.png", optimize=True)
    print(f"  {name}.png  {size}x{size}")
print("icons rebuilt — deploy.sh publishes them; iOS needs the home-screen icon "
      "deleted and re-added, it caches forever")
