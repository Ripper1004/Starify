#!/usr/bin/env python3
"""Draws the built-in morph target (a Star of David), its weight map and the icons.

Outputs:
  src/app/calculate/target256.png   the picture every upload is morphed into
  src/app/calculate/weights256.png  how much colour matters per cell
                                    (white = match the target colour closely,
                                     dark = prefer keeping pixels where they were)
  assets/*                          favicon and app icons, drawn from the same star

Usage: python3 tools/make_target.py [--preview out.png]
Requires Pillow and numpy. After changing the target, re-bake the bundled
presets (see README) so their stored assignments match it.
"""
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

TARGET_SIZE = 256
SS = 4  # supersampling factor for smooth edges

# Geometry, as fractions of the canvas side.
RADIUS = 0.445  # centre to tip
BAND = 0.068  # thickness of each triangle's outline
CENTER = (0.5, 0.5)

STAR_INNER = np.array([0, 56, 184], dtype=np.float32)  # flag blue
STAR_OUTER = np.array([0, 30, 120], dtype=np.float32)  # darker towards the tips
BG_CENTER = np.array([255, 255, 255], dtype=np.float32)
BG_EDGE = np.array([176, 190, 222], dtype=np.float32)

WEIGHT_STAR = 255  # on and right around the star: colour match is everything
WEIGHT_BG = 70  # elsewhere: let the original picture show through a little
WEIGHT_HALO = 0.045  # how far the high-weight zone extends past the star


def triangle(radius, rotation, big):
    cx, cy = CENTER
    return [
        (
            (cx + radius * math.cos(rotation + k * 2 * math.pi / 3)) * big,
            (cy + radius * math.sin(rotation + k * 2 * math.pi / 3)) * big,
        )
        for k in range(3)
    ]


def star_mask(size):
    """Two outlined triangles, one pointing up and one down, supersampled."""
    big = size * SS
    mask = Image.new("L", (big, big), 0)
    # An outline of thickness BAND is an outer triangle minus an inner one whose
    # inradius is BAND smaller; for an equilateral triangle inradius = R / 2.
    inner_radius = RADIUS - 2 * BAND
    for rotation in (-math.pi / 2, math.pi / 2):
        ring = Image.new("L", (big, big), 0)
        ring_draw = ImageDraw.Draw(ring)
        ring_draw.polygon(triangle(RADIUS, rotation, big), fill=255)
        ring_draw.polygon(triangle(inner_radius, rotation, big), fill=0)
        mask.paste(255, (0, 0), ring)
    return mask


def build(size):
    """Returns (target, weights) as RGB images of the given side length."""
    mask_big = star_mask(size)
    mask = np.asarray(mask_big.resize((size, size), Image.LANCZOS), dtype=np.float32) / 255.0
    mask = mask.clip(0, 1)[..., None]

    ys, xs = np.mgrid[0:size, 0:size].astype(np.float32)
    dist = np.hypot((xs + 0.5) / size - CENTER[0], (ys + 0.5) / size - CENTER[1])

    # Background: bright in the middle, falling off to a soft blue-grey in the
    # corners, so mid-tones of the upload have somewhere smooth to go.
    t_bg = (dist / 0.7071).clip(0, 1)[..., None] ** 1.6
    background = BG_CENTER * (1 - t_bg) + BG_EDGE * t_bg

    t_star = (dist / RADIUS).clip(0, 1)[..., None] ** 2
    star = STAR_INNER * (1 - t_star) + STAR_OUTER * t_star

    target = background * (1 - mask) + star * mask
    target_img = Image.fromarray(target.round().clip(0, 255).astype(np.uint8), "RGB")

    # Grow the star a little (on the small image, where it is cheap) and soften it.
    halo_px = WEIGHT_HALO * size
    halo = mask_big.resize((size, size), Image.LANCZOS)
    halo = halo.filter(ImageFilter.MaxFilter(int(halo_px) * 2 + 1))
    halo = halo.filter(ImageFilter.GaussianBlur(halo_px / 2))
    halo = np.asarray(halo, dtype=np.float32) / 255.0
    weights = WEIGHT_BG + (WEIGHT_STAR - WEIGHT_BG) * halo.clip(0, 1)
    weights = weights.round().clip(1, 255).astype(np.uint8)
    weights_img = Image.fromarray(np.repeat(weights[..., None], 3, axis=2), "RGB")
    return target_img, weights_img


def write_icons(assets):
    """App icons: the target itself, with rounded corners where the format has alpha."""
    art, _ = build(1024)

    def sized(side):
        return art.resize((side, side), Image.LANCZOS)

    sized(512).save(assets / "android-chrome-512x512.png", optimize=True)
    sized(192).save(assets / "android-chrome-192x192.png", optimize=True)
    sized(180).save(assets / "apple-touch-icon.png", optimize=True)
    sized(128).save(assets / "icon128.png", optimize=True)
    sized(32).save(assets / "favicon-32x32.png", optimize=True)
    sized(16).save(assets / "favicon-16x16.png", optimize=True)
    sized(256).save(assets / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])

    corners = Image.new("L", (1024, 1024), 0)
    ImageDraw.Draw(corners).rounded_rectangle((0, 0, 1023, 1023), radius=180, fill=255)
    rounded = art.convert("RGBA")
    rounded.putalpha(corners)
    rounded.resize((256, 256), Image.LANCZOS).save(assets / "linux" / "icon.png", optimize=True)
    rounded.save(assets / "macos" / "icon.icns")


def main():
    root = Path(__file__).resolve().parent.parent
    out_dir = root / "src" / "app" / "calculate"
    target_img, weights_img = build(TARGET_SIZE)
    target_img.save(out_dir / "target256.png", optimize=True)
    weights_img.save(out_dir / "weights256.png", optimize=True)
    write_icons(root / "assets")
    if "--preview" in sys.argv:
        preview = Image.new("RGB", (TARGET_SIZE * 2, TARGET_SIZE))
        preview.paste(target_img, (0, 0))
        preview.paste(weights_img, (TARGET_SIZE, 0))
        preview.save(sys.argv[sys.argv.index("--preview") + 1])
    print(f"wrote target and weights to {out_dir}, icons to {root / 'assets'}")


if __name__ == "__main__":
    main()
