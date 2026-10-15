#!/usr/bin/env python3
"""Render an original, seamless field of luminous cellular data. No text or assets."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


WIDTH, HEIGHT = 1600, 260
FRAMES, DURATION = 80, 50
SCALE = 2
BACKGROUND = (7, 10, 17)
CYAN = np.array((124, 231, 239), dtype=np.float32)
VIOLET = np.array((183, 160, 255), dtype=np.float32)
PEARL = np.array((228, 241, 255), dtype=np.float32)
NODES = 27


def backdrop() -> Image.Image:
    y, x = np.mgrid[:HEIGHT * SCALE, :WIDTH * SCALE].astype(np.float32)
    x, y = x / SCALE, y / SCALE
    atmosphere = np.exp(-((x - 800) / 430) ** 2 - ((y - 130) / 55) ** 2)
    pixels = np.empty((HEIGHT * SCALE, WIDTH * SCALE, 3), dtype=np.uint8)
    for channel, level in enumerate(BACKGROUND):
        pixels[:, :, channel] = level + np.rint(atmosphere * (1, 3, 6)[channel])
    return Image.fromarray(pixels)


def cell_position(u: float, phase: float, strand: int):
    envelope = math.sin(u * math.pi) ** .65
    angle = u * math.pi * 3.1 + phase + strand * math.pi
    depth = math.cos(angle)
    axis = 130 + math.sin(u * math.tau - phase) * 9 * envelope
    x = 260 + 1080 * u + math.cos(angle) * 7 * envelope
    y = axis + math.sin(angle) * 39 * envelope
    return x, y, depth, envelope


def paint_cell(pixels: np.ndarray, x: float, y: float, radius: float,
               color: np.ndarray, strength: float, seed: float) -> None:
    """A translucent, lit membrane surrounds a small floating bright nucleus."""
    x, y, radius = x * SCALE, y * SCALE, radius * SCALE
    margin = int(math.ceil(radius * 1.45))
    left, top = int(x) - margin, int(y) - margin
    right, bottom = int(x) + margin + 1, int(y) + margin + 1
    if left < 0 or top < 0 or right > pixels.shape[1] or bottom > pixels.shape[0]:
        return
    yy, xx = np.mgrid[top:bottom, left:right].astype(np.float32)
    nx, ny = (xx - x) / radius, (yy - y) / radius
    distance = np.sqrt(nx * nx + ny * ny)
    inside = distance < 1
    z = np.sqrt(np.maximum(0, 1 - distance * distance))
    # Fresnel light on the outer membrane, with a softer inner shell.
    membrane = np.exp(-((distance - .87) / .075) ** 2) * .4
    inner = np.exp(-((distance - .59) / .13) ** 2) * .095
    body = np.maximum(0, .26 - distance * .18) * inside
    diffuse = np.maximum(0, -.4 * nx - .6 * ny + .67 * z) ** 4 * .19 * inside
    nucleus_x = -.12 + .08 * math.sin(seed)
    nucleus_y = .08 * math.cos(seed)
    nucleus = np.exp(-(((nx - nucleus_x) / .2) ** 2
                       + ((ny - nucleus_y) / .2) ** 2)) * .8
    glint = np.exp(-(((nx + .38) / .16) ** 2 + ((ny + .49) / .11) ** 2)) * .9
    shoulder = np.exp(-(((nx - .43) / .25) ** 2 + ((ny - .55) / .09) ** 2)) * .22
    light = ((membrane + inner + body + diffuse)[..., None] * color
             + (nucleus + glint + shoulder)[..., None] * PEARL)
    pixels[top:bottom, left:right] += light * strength * 1.35


def render(frame: int) -> Image.Image:
    phase = (frame % FRAMES) * math.tau / FRAMES
    base = backdrop()
    strands = [[cell_position((index + .5) / NODES, phase, side)
                for index in range(NODES)] for side in (0, 1)]
    wire = Image.new('RGB', base.size)
    bloom = Image.new('RGB', base.size)
    draw, glow = ImageDraw.Draw(wire), ImageDraw.Draw(bloom)
    cells = []

    # Thin branched connections hint at a molecular ladder without drawing a
    # literal diagram. Depth controls the visibility of its far-side branches.
    for side, strand in enumerate(strands):
        for index, (x, y, depth, envelope) in enumerate(strand):
            u = (index + .5) / NODES
            mix = .21 + .58 * (math.sin(u * math.pi + side * 1.7) + 1) / 2
            color = CYAN * (1 - mix) + VIOLET * mix
            front = (depth + 1) / 2
            pulse = ((1 + math.cos(u * math.tau - phase)) / 2) ** 10
            strength = envelope * (.31 + .5 * front + .26 * pulse)
            radius = (3.1 + 3.3 * front + 1.1 * pulse) * (.64 + .36 * envelope)
            if index % 7 == 3:
                radius *= 1.26
            cells.append((depth, x, y, radius, color, strength, phase + u * math.tau))
            if index + 1 < NODES:
                other = strand[index + 1]
                shade = color * envelope * (.047 + .055 * front)
                draw.line((x * SCALE, y * SCALE, other[0] * SCALE,
                           other[1] * SCALE), fill=tuple(shade.astype(int)), width=SCALE)
            if side == 0 and index % 2 == 0:
                other = strands[1][index]
                midpoint = ((x + other[0]) / 2 + 3 * math.sin(phase + index),
                            (y + other[1]) / 2)
                shade = color * envelope * .075
                draw.line((x * SCALE, y * SCALE, midpoint[0] * SCALE,
                           midpoint[1] * SCALE, other[0] * SCALE, other[1] * SCALE),
                          fill=tuple(shade.astype(int)), width=SCALE)
                # Each bridge has a tiny, softly glowing data junction.
                cells.append((-.7, *midpoint, 1.05, color, .4 * envelope, phase))
            halo = radius * (2 + pulse)
            rgb = tuple((color * strength * .2).astype(int))
            glow.ellipse(((x - halo) * SCALE, (y - halo) * SCALE,
                          (x + halo) * SCALE, (y + halo) * SCALE), fill=rgb)

    # A sparse cloud of satellites creates a living volume around the helix.
    # All drift frequencies are integers of the loop phase, including twinkles.
    for index in range(30):
        u = (index + .5) / 30
        envelope = math.sin(u * math.pi) ** 1.4
        seed = index * 2.399963229728653
        x = 290 + u * 1020 + math.sin(phase + seed) * 6
        y = 130 + math.sin(seed) * 72 * envelope + math.cos(phase + seed * 2) * 5
        depth = math.sin(seed + phase)
        color = CYAN if index % 3 else VIOLET
        strength = envelope * (.14 + .14 * (depth + 1) / 2)
        radius = .65 + (index % 4) * .27
        cells.append((-1, x, y, radius, color, strength, phase + seed))

    pixels = (np.asarray(base, dtype=np.float32)
              + np.asarray(wire, dtype=np.float32)
              + np.asarray(bloom.filter(ImageFilter.GaussianBlur(7 * SCALE)),
                           dtype=np.float32))
    for _, x, y, radius, color, strength, seed in sorted(cells, key=lambda cell: cell[0]):
        paint_cell(pixels, x, y, radius, color, strength, seed)
    image = Image.fromarray(np.clip(pixels, 0, 255).astype(np.uint8))
    return image.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=Path('assets'))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    frames = [render(frame) for frame in range(FRAMES)]
    frames[0].save(args.output_dir / 'field-v2.png', optimize=True)
    # One palette for the entire loop prevents colour flicker. Build it from
    # the actual illuminated region so unused dark borders consume no colours.
    samples = Image.new('RGB', (1120, 150 * 8))
    for index in range(8):
        samples.paste(frames[index * FRAMES // 8].crop((240, 55, 1360, 205)),
                      (0, index * 150))
    palette = samples.quantize(colors=96, method=Image.Quantize.MEDIANCUT)
    encoded = [frame.quantize(palette=palette, dither=Image.Dither.NONE)
               for frame in frames]
    encoded[0].save(args.output_dir / 'field-v2.gif', save_all=True,
                    append_images=encoded[1:], duration=DURATION, loop=0,
                    optimize=True, disposal=1)
    for extension in ('gif', 'png'):
        path = args.output_dir / f'field-v2.{extension}'
        print(f'{path}: {path.stat().st_size:,} bytes')


if __name__ == '__main__':
    main()
