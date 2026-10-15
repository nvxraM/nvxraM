#!/usr/bin/env python3
"""Draw the original profile header. No network services or external imagery."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


WIDTH, HEIGHT = 1600, 640
FRAMES, DURATION = 96, 50
BG = (9, 15, 26)
INK = (235, 243, 248)
MUTED = (140, 161, 181)
TEAL = (102, 227, 196)
LILAC = (169, 164, 245)
FONT_ROOT = Path('/usr/share/fonts/truetype/dejavu')


def font(size: int, weight: str = 'regular') -> ImageFont.FreeTypeFont:
    name = {'regular': 'DejaVuSans.ttf', 'bold': 'DejaVuSans-Bold.ttf',
            'mono': 'DejaVuSansMono.ttf'}[weight]
    return ImageFont.truetype(str(FONT_ROOT / name), size)


def spaced(draw: ImageDraw.ImageDraw, xy, text, face, fill, spacing=3):
    x, y = xy
    for char in text:
        draw.text((x, y), char, font=face, fill=fill)
        x += draw.textlength(char, font=face) + spacing


def base_image() -> Image.Image:
    y, x = np.mgrid[0:HEIGHT, 0:WIDTH]
    halo = np.exp(-(((x - 1200) / 350) ** 2 + ((y - 300) / 300) ** 2))
    pixels = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    for i, level in enumerate(BG):
        pixels[:, :, i] = np.clip(level + halo * [1, 8, 13][i], 0, 255)
    image = Image.fromarray(pixels)
    draw = ImageDraw.Draw(image)
    # Quiet plotting grid behind the scientific illustration.
    for xx in range(840, WIDTH - 40, 56):
        draw.line((xx, 90, xx, 550), fill=(19, 33, 46), width=1)
    for yy in range(102, 550, 56):
        draw.line((820, yy, WIDTH - 50, yy), fill=(19, 33, 46), width=1)
    draw.rounded_rectangle((1, 1, WIDTH - 2, HEIGHT - 2), radius=28,
                           outline=(38, 52, 69), width=2)
    spaced(draw, (76, 54), 'MATTHEW JOHN FREEMAN', font(19, 'mono'), MUTED, 2)
    draw.text((76, 90), '@nvxraM', font=font(22, 'mono'), fill=TEAL)
    # A strong, restrained typographic lockup.
    draw.text((70, 165), 'Curiosity,', font=font(105, 'bold'), fill=INK,
              stroke_width=0)
    draw.text((70, 282), 'in code.', font=font(105, 'bold'), fill=TEAL)
    draw.text((78, 432), 'Exploring genomes. Connecting patterns.',
              font=font(27), fill=(165, 184, 201))
    draw.line((78, 535, 1520, 535), fill=(37, 53, 70), width=1)
    spaced(draw, (78, 575), 'GENOMICS  /  CODE  /  DISCOVERY',
           font(19, 'mono'), MUTED, 1)
    draw.text((1250, 575), 'STAY CURIOUS', font=font(19, 'mono'), fill=TEAL)
    return image


def strand_point(t: float, phase: float, opposite=False):
    angle = t * math.pi * 4 + phase + (math.pi if opposite else 0)
    # Tilt the molecular axis, while rotation changes depth and rung perspective.
    axis_x = 1180 + (t - .5) * 150
    xx = axis_x + math.cos(angle) * 149
    yy = 110 + t * 374 + math.sin(angle) * 20
    return xx, yy, math.sin(angle)


def render(base: Image.Image, frame: int) -> Image.Image:
    phase = frame * math.tau / FRAMES
    image = base.copy()
    draw = ImageDraw.Draw(image)
    glow = Image.new('RGB', image.size)
    gd = ImageDraw.Draw(glow)
    # Small, stationary orbital references make the movement easy to follow.
    draw.ellipse((967, 84, 1438, 504), outline=(31, 53, 67), width=1)
    draw.line((954, 296, 977, 296), fill=(65, 92, 106), width=2)
    draw.line((1424, 296, 1447, 296), fill=(65, 92, 106), width=2)
    draw.text((982, 62), 'A / T / C / G', font=font(17, 'mono'), fill=MUTED)
    # Sort molecular segments by depth so the near strand occludes its rungs.
    parts = []
    for k in range(27):
        t = k / 26
        a = strand_point(t, phase)
        b = strand_point(t, phase, True)
        parts.append((-0.1, 'rung', a, b))
    for side in (False, True):
        for k in range(240):
            a = strand_point(k / 240, phase, side)
            b = strand_point((k + 1) / 240, phase, side)
            parts.append(((a[2] + b[2]) / 2, 'strand', a, b, side))
    for part in sorted(parts, key=lambda p: p[0]):
        _, kind, a, b, *side = part
        if kind == 'rung':
            mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            draw.line((a[0], a[1], *mid), fill=(63, 127, 125), width=3)
            draw.line((*mid, b[0], b[1]), fill=(97, 95, 150), width=3)
        else:
            color = LILAC if side[0] else TEAL
            brightness = .44 + (a[2] + 1) * .28
            color = tuple(round(v * brightness) for v in color)
            coords = (a[0], a[1], b[0], b[1])
            draw.line(coords, fill=color, width=6)
            gd.line(coords, fill=tuple(v // 3 for v in color), width=9)
    # Add a very light bloom, preserving crisp center lines and readable type.
    image = Image.fromarray(np.clip(np.asarray(image, dtype=np.uint16) +
                            np.asarray(glow.filter(ImageFilter.GaussianBlur(12)),
                                       dtype=np.uint16), 0, 255).astype('uint8'))
    draw = ImageDraw.Draw(image)
    for side in (False, True):
        for k in range(27):
            x, y, z = strand_point(k / 26, phase, side)
            r = 3 + (z + 1) * 1.3
            color = LILAC if side else TEAL
            brightness = .6 + (z + 1) * .2
            fill = tuple(round(v * brightness) for v in color)
            draw.ellipse((x-r, y-r, x+r, y+r), fill=fill)
    return image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=Path('assets'))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    base = base_image()
    frames = [render(base, i) for i in range(FRAMES)]
    frames[0].save(args.output_dir / 'hero.png', optimize=True)
    # One palette across the whole loop prevents color flicker between frames.
    contact = Image.new('RGB', (400 * 6, 160))
    for i in range(6):
        contact.paste(frames[i * (FRAMES // 6)].resize((400, 160)), (i * 400, 0))
    palette = contact.quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    encoded = [f.quantize(palette=palette, dither=Image.Dither.NONE) for f in frames]
    encoded[0].save(args.output_dir / 'hero.gif', save_all=True,
                    append_images=encoded[1:], duration=DURATION, loop=0,
                    optimize=True, disposal=1)
    for suffix in ('png', 'gif'):
        target = args.output_dir / f'hero.{suffix}'
        print(f'{target}: {target.stat().st_size:,} bytes')


if __name__ == '__main__':
    main()
