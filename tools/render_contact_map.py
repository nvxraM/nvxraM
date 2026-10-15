#!/usr/bin/env python3
"""Draw an original, synthetic example of Hi-C fragment ordering.

    python tools/render_contact_map.py --output-dir assets

Both panels contain exactly the same symmetric contact matrix. The left panel
applies an explicit permutation of four-bin fragments to its rows and columns;
the right panel restores the original order. Nothing represents research data.
Requires NumPy and Pillow; no network access or downloaded assets are used.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


WIDTH, HEIGHT = 1600, 620
FRAMES = 80
BG = (9, 15, 26)
SURFACE = (13, 21, 34)
EDGE = (35, 50, 71)
TEXT = (225, 234, 245)
MUTED = (138, 157, 181)
TEAL = (102, 227, 196)
LAVENDER = (169, 164, 245)
FONT_ROOT = Path('/usr/share/fonts/truetype/dejavu')
FRAGMENT_ORDER = np.array([12, 5, 9, 1, 15, 7, 3, 10, 0, 13, 4, 14, 8, 2, 11, 6])
PERMUTATION = np.concatenate([np.arange(fragment * 4, fragment * 4 + 4)
                              for fragment in FRAGMENT_ORDER])


def font(size, mono=False, bold=False):
    family = 'DejaVuSansMono' if mono else 'DejaVuSans'
    return ImageFont.truetype(str(FONT_ROOT / f'{family}{"-Bold" if bold else ""}.ttf'), size)


def blend(a, b, amount):
    return tuple(round(x + (y - x) * amount) for x, y in zip(a, b))


def centered(draw, x, y, value, face, fill):
    draw.text((x - draw.textlength(value, font=face) / 2, y), value, font=face, fill=fill)


def spaced(draw, x, y, value, fill, size=20, spacing=3):
    face = font(size, bold=True)
    for char in value:
        draw.text((x, y), char, fill=fill, font=face)
        x += draw.textlength(char, font=face) + spacing


def contact_matrices():
    rng = np.random.default_rng(613)
    i, j = np.indices((64, 64))
    contacts = 0.63 * np.exp(-np.abs(i - j) / 4.4)
    for start, stop in [(0, 16), (16, 32), (32, 48), (48, 64)]:
        contacts += 0.24 * ((i >= start) & (i < stop) & (j >= start) & (j < stop))
    noise = rng.uniform(0.0, 0.065, (64, 64))
    contacts += (noise + noise.T) * 0.5
    contacts = np.clip(contacts, 0, 1)
    scrambled = contacts[np.ix_(PERMUTATION, PERMUTATION)]
    assert np.array_equal(np.sort(scrambled.ravel()), np.sort(contacts.ravel()))
    assert np.array_equal(scrambled, scrambled.T)
    return scrambled, contacts


UNORDERED, ORDERED = contact_matrices()


def heatmap(matrix):
    # Pixel interpolation is intentionally avoided: each cell is one contact bin.
    pixels = np.zeros((64, 64, 3), dtype=np.uint8)
    for row in range(64):
        for col in range(64):
            value = float(matrix[row, col])
            if value < 0.25:
                color = blend((13, 25, 40), (43, 89, 104), value / 0.25)
            elif value < 0.65:
                color = blend((43, 89, 104), (101, 195, 179), (value - 0.25) / 0.4)
            else:
                color = blend((101, 195, 179), LAVENDER, (value - 0.65) / 0.35)
            pixels[row, col] = color
    return Image.fromarray(pixels).resize((352, 352), Image.Resampling.NEAREST)


def static_image():
    image = Image.new('RGB', (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)
    spaced(draw, 42, 34, 'ILLUSTRATIVE HI-C CONTACT MAPS', MUTED)
    panels = [(42, 'UNORDERED FRAGMENTS', 'The same contacts, with fragment order shuffled.', UNORDERED),
              (829, 'ORDERED SCAFFOLD', 'Restoring order reveals a coherent diagonal.', ORDERED)]
    for index, (left, title, subtitle, matrix) in enumerate(panels):
        draw.rounded_rectangle((left, 95, left + 729, 561), radius=18,
                               fill=SURFACE, outline=EDGE)
        draw.text((left + 25, 117), f'0{index + 1} /', font=font(18, mono=True),
                  fill=TEAL if index == 0 else LAVENDER)
        draw.text((left + 102, 115), title, font=font(23, bold=True), fill=TEXT)
        draw.text((left + 25, 153), subtitle, font=font(18), fill=MUTED)
        mx, my = left + 188, 193
        image.paste(heatmap(matrix), (mx, my))
        draw.line([(mx - 9, my), (mx - 9, my + 351)], fill=EDGE, width=2)
        draw.line([(mx, my + 359), (mx + 351, my + 359)], fill=EDGE, width=2)
        for mark in range(0, 353, 88):
            draw.line([(mx - 12, my + mark), (mx - 7, my + mark)], fill=MUTED, width=1)
            draw.line([(mx + mark, my + 357), (mx + mark, my + 362)], fill=MUTED, width=1)
    draw.line([(42, 592), (78, 592)], fill=TEAL, width=2)
    draw.text((91, 580), 'Synthetic data · a visual explanation, not a research result',
              font=font(18), fill=MUTED)
    draw.text((1380, 580), 'nvxraM', font=font(18, mono=True), fill=MUTED)
    # A compact intensity key, deliberately without numerical research metrics.
    for step in range(42):
        x = 1314 + step * 3
        color = blend((24, 46, 63), TEAL, step / 41)
        draw.line([(x, 45), (x + 2, 45)], fill=color, width=5)
    draw.text((1451, 34), 'CONTACT', font=font(16, mono=True), fill=MUTED)
    return image


STATIC = static_image()


def render(phase):
    image = STATIC.copy()
    draw = ImageDraw.Draw(image)
    # The scan crosses both examples together. It fades completely before the
    # position wraps, creating a continuous loop while leaving the data fixed.
    gate = math.sin(math.pi * phase) ** 2
    offset = round(phase * 351)
    if gate > 0.001:
        for left in [42, 829]:
            x = left + 188 + offset
            color = blend(SURFACE, TEAL, 0.52 * gate)
            draw.line([(x, 193), (x, 544)], fill=color, width=1)
            # Small ruler markers let motion remain visible without obscuring cells.
            draw.polygon([(x - 4, 187), (x + 4, 187), (x, 191)], fill=color)
    return image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=Path('assets'))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    frames = [render(frame / FRAMES) for frame in range(FRAMES)]
    STATIC.save(args.output_dir / 'contact-map.png', optimize=True)
    palette = STATIC.quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    indexed = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in frames]
    indexed[0].save(args.output_dir / 'contact-map.gif', save_all=True,
                    append_images=indexed[1:], duration=50, loop=0, optimize=True, disposal=1)
    for filename in ['contact-map.png', 'contact-map.gif']:
        path = args.output_dir / filename
        with Image.open(path) as result:
            print(f'{path}: {result.width}x{result.height}, '
                  f'{getattr(result, "n_frames", 1)} frame(s), {path.stat().st_size:,} bytes')


if __name__ == '__main__':
    main()
