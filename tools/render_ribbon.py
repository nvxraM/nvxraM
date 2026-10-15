#!/usr/bin/env python3
"""Render original, seamless light ribbons with no external images or services."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


WIDTH, HEIGHT = 1600, 200
FRAMES, DURATION = 80, 50
BACKGROUND = (7, 10, 17)
CYAN = (124, 231, 239)
VIOLET = (183, 160, 255)
BLUE = (125, 159, 255)
SUPERSAMPLE = 2
RIBBON_LEFT, RIBBON_SPAN = 240, 1120


def base_image() -> Image.Image:
    """A nearly black backdrop with a quiet, stationary atmospheric glow."""
    y, x = np.mgrid[:HEIGHT, :WIDTH]
    illumination = np.exp(-((x - WIDTH / 2) / 460) ** 2 - ((y - 100) / 65) ** 2)
    rgb = np.empty((HEIGHT, WIDTH, 3), dtype=np.uint8)
    for channel, value in enumerate(BACKGROUND):
        rgb[:, :, channel] = value + np.rint(illumination * (1, 3, 7)[channel])
    return Image.fromarray(rgb)


def curve(u: np.ndarray | float, phase: float, band: int, filament: float = 0):
    """Every time component is periodic, including the breathing ribbon widths."""
    angle = np.asarray(u) * math.tau
    envelope = np.sin(np.asarray(u) * math.pi) ** 0.8
    offset = band * math.tau / 3
    centre = (100 + envelope * (32 * np.sin(angle * 1.35 + phase + offset)
              + 10 * np.sin(angle * 2.2 - phase + offset)))
    spread = (5 + 4 * np.sin(angle + phase + offset) ** 2) * envelope
    return centre + filament * spread


def render(frame: int) -> Image.Image:
    phase = (frame % FRAMES) * math.tau / FRAMES
    scale = SUPERSAMPLE
    size = (WIDTH * scale, HEIGHT * scale)
    fine = Image.new('RGB', size)
    bloom = Image.new('RGB', size)
    draw, glow = ImageDraw.Draw(fine), ImageDraw.Draw(bloom)
    u = np.linspace(0, 1, 401)
    xs = RIBBON_LEFT + u * RIBBON_SPAN
    # Twelve fine filaments weave into three soft, luminous bands. Dark gaps and
    # gradual edge falloff preserve the empty space around the central motion.
    for band, color in enumerate((CYAN, VIOLET, BLUE)):
        for filament in (-1.15, -0.4, 0.4, 1.15):
            ys = curve(u, phase, band, filament)
            for i in range(len(u) - 1):
                fade = math.sin(float(u[i]) * math.pi) ** 1.5
                shimmer = .72 + .22 * math.sin(float(u[i]) * math.tau - phase + band)
                strength = fade * shimmer * (.72 if abs(filament) > 1 else .96)
                rgb = tuple(round(component * strength) for component in color)
                points = (xs[i] * scale, ys[i] * scale,
                          xs[i + 1] * scale, ys[i + 1] * scale)
                draw.line(points, fill=rgb, width=scale)
                glow.line(points, fill=tuple(round(c * .32) for c in rgb), width=scale * 5)

    # Particles move along the curves and fade completely before wrapping.
    for index, (band, shift) in enumerate(((0, .04), (1, .29), (2, .51), (0, .76))):
        progress = ((frame % FRAMES) / FRAMES + shift) % 1
        x = RIBBON_LEFT + progress * RIBBON_SPAN
        y = float(curve(progress, phase, band))
        strength = math.sin(progress * math.pi) ** 2
        color = (CYAN, VIOLET, BLUE)[band]
        for trail in range(15, -1, -1):
            trail_u = progress - trail / 600
            if trail_u < 0:
                continue
            tx = (RIBBON_LEFT + trail_u * RIBBON_SPAN) * scale
            ty = float(curve(trail_u, phase, band)) * scale
            luminosity = strength * ((16 - trail) / 16) ** 2
            radius = (.45 + .8 * luminosity) * scale
            rgb = tuple(round(c * luminosity) for c in color)
            draw.ellipse((tx - radius, ty - radius, tx + radius, ty + radius), fill=rgb)
        radius = 1.65 * scale
        rgb = tuple(round(c * strength) for c in color)
        draw.ellipse((x * scale - radius, y * scale - radius,
                      x * scale + radius, y * scale + radius), fill=rgb)
        glow.ellipse((x * scale - 6 * scale, y * scale - 6 * scale,
                      x * scale + 6 * scale, y * scale + 6 * scale), fill=rgb)

    fine = fine.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    bloom = bloom.filter(ImageFilter.GaussianBlur(6 * scale)).resize(
        (WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    pixels = (np.asarray(base_image(), dtype=np.uint16)
              + np.asarray(fine, dtype=np.uint16)
              + np.asarray(bloom, dtype=np.uint16))
    return Image.fromarray(np.minimum(pixels, 255).astype('uint8'))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=Path('assets'))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    frames = [render(frame) for frame in range(FRAMES)]
    frames[0].save(args.output_dir / 'ribbon.png', optimize=True)
    # A global palette avoids per-frame colour flicker. Reserve equal ramps for
    # each accent so a large dark backdrop cannot crowd the colours out. GIF
    # delta rectangles retain that backdrop and keep the download compact.
    colors = [BACKGROUND, (8, 12, 22), (9, 14, 26), (10, 15, 28)]
    for accent in (CYAN, VIOLET, BLUE):
        for step in range(1, 9):
            strength = (step / 8) ** 1.7
            colors.append(tuple(round(a + (b - a) * strength)
                                for a, b in zip(BACKGROUND, accent)))
    palette = Image.new('P', (1, 1))
    palette.putpalette([channel for color in colors for channel in color]
                       + [0] * (768 - len(colors) * 3))
    encoded = [frame.quantize(palette=palette, dither=Image.Dither.NONE)
               for frame in frames]
    encoded[0].save(args.output_dir / 'ribbon.gif', save_all=True,
                    append_images=encoded[1:], loop=0, duration=DURATION,
                    optimize=True, disposal=1)
    for extension in ('gif', 'png'):
        path = args.output_dir / f'ribbon.{extension}'
        print(f'{path}: {path.stat().st_size:,} bytes')


if __name__ == '__main__':
    main()
