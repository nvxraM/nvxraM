#!/usr/bin/env python3
"""Render the profile's original, synthetic genomics workflow illustration.

    python tools/render_workflow.py --output-dir assets

Requires Pillow and NumPy. The artwork uses local fonts and no network assets.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


WIDTH, HEIGHT = 1600, 560
FRAME_COUNT = 48
BG = (9, 15, 26)
SURFACE = (13, 21, 34)
EDGE = (35, 50, 71)
TEXT = (225, 234, 245)
MUTED = (138, 157, 181)
TEAL = (102, 227, 196)
LAVENDER = (169, 164, 245)
BLUE = (109, 166, 208)
FONT_ROOT = Path('/usr/share/fonts/truetype/dejavu')


def font(size: int, *, mono: bool = False, bold: bool = False):
    family = 'DejaVuSansMono' if mono else 'DejaVuSans'
    return ImageFont.truetype(str(FONT_ROOT / f'{family}{"-Bold" if bold else ""}.ttf'), size)


def blend(a, b, amount):
    return tuple(round(x + (y - x) * amount) for x, y in zip(a, b))


def spaced(draw, xy, value, fill, size=19, spacing=3):
    x, y = xy
    face = font(size, bold=True)
    for char in value:
        draw.text((x, y), char, fill=fill, font=face)
        x += draw.textlength(char, font=face) + spacing


def line(draw, points, fill, width=2):
    draw.line(points, fill=fill, width=width, joint='curve')


def pulse(phase, offset):
    """A smooth cyclic emphasis, with no jump at the loop boundary."""
    return (0.5 + 0.5 * math.cos(2 * math.pi * (phase - offset))) ** 4


def make_data():
    rng = np.random.default_rng(26)
    # A small, strictly symmetric contact matrix with four synthetic domains.
    n = 30
    i, j = np.indices((n, n))
    contact = 0.62 * np.exp(-np.abs(i - j) / 1.9)
    for start, stop in [(0, 7), (7, 15), (15, 23), (23, 30)]:
        contact += 0.23 * ((i >= start) & (i < stop) & (j >= start) & (j < stop))
    noise = rng.uniform(0, 0.07, (n, n))
    contact += (noise + noise.T) * 0.5
    contact = np.clip(contact, 0, 1)
    points = []
    for group, (cx, cy) in enumerate([(82, 80), (192, 63), (163, 149)]):
        for _ in range(24):
            dx, dy = rng.normal(0, 21, 2)
            points.append((float(cx + dx), float(cy + dy), group))
    return contact, points


CONTACT, POINTS = make_data()


def reads(draw, left, top, phase):
    patterns = [
        [(10, 70), (86, 139), (170, 223)],
        [(35, 103), (125, 183), (213, 257)],
        [(3, 53), (75, 146), (167, 237)],
        [(23, 91), (112, 168), (194, 267)],
        [(8, 64), (87, 155), (180, 243)],
        [(40, 104), (128, 192), (218, 264)],
        [(14, 78), (102, 157), (183, 253)],
        [(34, 91), (118, 177), (202, 269)],
    ]
    for row, segments in enumerate(patterns):
        y = top + 22 + row * 22
        for k, (a, b) in enumerate(segments):
            highlight = pulse(phase, (row * 0.061 + k * 0.12) % 1)
            color = blend((54, 105, 113), TEAL, 0.42 + 0.58 * highlight)
            draw.rounded_rectangle((left + a, y, left + b, y + 7), radius=3, fill=color)
            for tick in range(a + 11, b - 4, 14):
                line(draw, [(left + tick, y + 2), (left + tick, y + 5)], SURFACE, 1)


def assemble(draw, left, top, phase):
    patterns = [
        [(0, 83, TEAL), (87, 164, BLUE), (168, 272, LAVENDER)],
        [(13, 106, BLUE), (110, 191, TEAL), (195, 263, LAVENDER)],
        [(0, 112, LAVENDER), (116, 204, TEAL), (208, 272, BLUE)],
        [(18, 88, TEAL), (92, 165, LAVENDER), (169, 255, BLUE)],
        [(0, 73, BLUE), (77, 176, LAVENDER), (180, 272, TEAL)],
    ]
    for row, segments in enumerate(patterns):
        y = top + 30 + row * 31
        line(draw, [(left, y + 6), (left + 272, y + 6)], EDGE, 1)
        for a, b, color in segments:
            strength = 0.55 + 0.32 * pulse(phase, 0.2 + row * 0.1)
            draw.rounded_rectangle((left + a, y, left + b, y + 12), radius=3,
                                   fill=blend(SURFACE, color, strength))
    line(draw, [(left + 1, top + 204), (left + 271, top + 204)], EDGE, 2)
    for x in [0, 68, 136, 204, 272]:
        line(draw, [(left + x, top + 201), (left + x, top + 208)], MUTED, 1)


def contact_map(draw, left, top, phase):
    x0, y0 = left + 46, top + 11
    cell, gap = 6, 1
    for row in range(30):
        for col in range(30):
            value = float(CONTACT[row, col])
            if value < 0.25:
                color = blend((17, 31, 47), (48, 86, 100), value / 0.25)
            elif value < 0.65:
                color = blend((48, 86, 100), (96, 184, 173), (value - 0.25) / 0.4)
            else:
                color = blend((96, 184, 173), LAVENDER, (value - 0.65) / 0.35)
            # The diagonal subtly brightens in a traveling, symmetric wave.
            strength = pulse(phase, 0.4 + (row + col) / 85)
            color = blend(color, (181, 234, 222), 0.12 * strength * value)
            x, y = x0 + col * cell, y0 + row * cell
            draw.rectangle((x, y, x + cell - gap, y + cell - gap), fill=color)
    line(draw, [(x0 - 8, y0), (x0 - 8, y0 + 179)], EDGE, 2)
    line(draw, [(x0, y0 + 188), (x0 + 179, y0 + 188)], EDGE, 2)
    # Domain corner marks make the synthetic diagonal blocks easy to read.
    for pos in [0, 42, 90, 138, 180]:
        line(draw, [(x0 - 11, y0 + pos), (x0 - 6, y0 + pos)], MUTED, 1)
        line(draw, [(x0 + pos, y0 + 186), (x0 + pos, y0 + 191)], MUTED, 1)


def populations(draw, left, top, phase):
    x0, y0 = left + 4, top + 5
    line(draw, [(x0 + 15, y0 + 10), (x0 + 15, y0 + 200),
                (x0 + 278, y0 + 200)], EDGE, 2)
    colors = [TEAL, LAVENDER, BLUE]
    # Very faint local connections suggest relationships without cluttering dots.
    for group in range(3):
        selected = [(x0 + x, y0 + y) for x, y, g in POINTS if g == group]
        center = (sum(x for x, _ in selected) / len(selected),
                  sum(y for _, y in selected) / len(selected))
        for index, point in enumerate(selected):
            if index % 4 == 0:
                line(draw, [point, center], blend(SURFACE, colors[group], 0.16), 1)
    for index, (x, y, group) in enumerate(POINTS):
        strength = pulse(phase, 0.62 + group * 0.13 + index * 0.005)
        color = blend(SURFACE, colors[group], 0.55 + strength * 0.4)
        r = 3 if index % 5 else 4
        draw.ellipse((x0 + x - r, y0 + y - r, x0 + x + r, y0 + y + r), fill=color)


def render(phase):
    image = Image.new('RGB', (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)
    spaced(draw, (42, 39), 'FROM READS TO RELATIONSHIPS', MUTED, 20, 3)
    draw.rounded_rectangle((1364, 37, 1558, 70), radius=16, fill=SURFACE, outline=EDGE)
    draw.ellipse((1381, 49, 1388, 56), fill=TEAL)
    draw.text((1400, 44), 'GENOMICS', fill=MUTED, font=font(15, mono=True))
    cards = [
        ('01', 'SEQUENCE', 'Raw reads', 'Small fragments. Rich signals.', reads),
        ('02', 'ASSEMBLE', 'Genome assembly', 'Reconstruct the larger picture.', assemble),
        ('03', 'CONNECT', 'Hi-C structure', 'Explore spatial relationships.', contact_map),
        ('04', 'UNDERSTAND', 'Population patterns', 'Find structure in variation.', populations),
    ]
    for index, (number, name, title, description, diagram) in enumerate(cards):
        x = 42 + index * 385
        draw.rounded_rectangle((x, 103, x + 361, 471), radius=17, fill=SURFACE, outline=EDGE, width=1)
        draw.text((x + 25, 125), f'{number} /', fill=TEAL if index % 2 == 0 else LAVENDER,
                  font=font(17, mono=True))
        spaced(draw, (x + 86, 125), name, MUTED, 16, 1)
        diagram(draw, x + 43, 163, phase)
        draw.text((x + 25, 395), title, fill=TEXT, font=font(24, bold=True))
        draw.text((x + 25, 433), description, fill=MUTED, font=font(16))
    line(draw, [(42, 509), (78, 509)], TEAL, 2)
    draw.text((91, 498), 'An illustrated workflow · synthetic data', fill=MUTED, font=font(17))
    draw.text((1381, 498), 'nvxraM', fill=MUTED, font=font(17, mono=True))
    return image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=Path('assets'))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    frames = [render(frame / FRAME_COUNT) for frame in range(FRAME_COUNT)]
    frames[0].save(args.output_dir / 'workflow.png', optimize=True)
    # All frames use one fixed palette, avoiding temporal color flicker.
    sample = Image.new('RGB', (WIDTH, HEIGHT * 4))
    for index, frame_index in enumerate([0, 12, 24, 36]):
        sample.paste(frames[frame_index], (0, HEIGHT * index))
    palette = sample.quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    indexed = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in frames]
    # Alternating 80/90 ms durations total exactly 4 seconds (12 frames/sec).
    durations = [90 if frame % 3 == 0 else 80 for frame in range(FRAME_COUNT)]
    indexed[0].save(args.output_dir / 'workflow.gif', save_all=True, append_images=indexed[1:],
                    duration=durations, loop=0, optimize=True, disposal=1)
    for name in ['workflow.png', 'workflow.gif']:
        path = args.output_dir / name
        with Image.open(path) as result:
            print(f'{path}: {result.size[0]}x{result.size[1]}, '
                  f'{getattr(result, "n_frames", 1)} frame(s), {path.stat().st_size:,} bytes')


if __name__ == '__main__':
    main()
