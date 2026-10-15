#!/usr/bin/env python3
"""Render an original looping light sculpture and a minimal wordmark."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


WIDTH, HEIGHT = 1600, 760
FRAMES, DURATION = 120, 40
BG = (7, 10, 17)
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'


def mix(a, b, amount):
    return tuple(round(x + (y-x)*amount) for x, y in zip(a, b))


def colors(position):
    colors = [(112, 231, 234), (126, 170, 255), (181, 148, 247),
              (137, 205, 248), (112, 231, 234)]
    position = position % 1 * 4
    index = int(position)
    return mix(colors[index], colors[index + 1], position - index)


def base_image():
    yy, xx = np.mgrid[0:HEIGHT, 0:WIDTH]
    halo = np.exp(-(((xx-800)/360)**2 + ((yy-300)/260)**2))
    pixels = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    for i, component in enumerate(BG):
        pixels[:, :, i] = component + (halo * [3, 4, 11][i]).astype('uint8')
    image = Image.fromarray(pixels)
    draw = ImageDraw.Draw(image)
    rng = np.random.default_rng(127)
    for _ in range(75):
        x, y = rng.integers(100, 1500), rng.integers(55, 515)
        if abs(x-800) > 345 or abs(y-280) > 205:
            color = (28, 38, 55) if x % 3 else (48, 61, 81)
            draw.ellipse((int(x), int(y), int(x+1), int(y+1)), fill=color)
    face = ImageFont.truetype(FONT, 120)
    draw.text((800, 545), 'nvxraM', font=face, fill=(235, 241, 250), anchor='mt')
    return image


T = np.linspace(0, math.tau, 721)


def points(phase, offset):
    radius = 177 + 62 * np.cos(3*T) + offset
    x = radius * np.cos(2*T)
    y = radius * np.sin(2*T)
    z = 91 * np.sin(3*T)
    yaw = phase
    xx = x * math.cos(yaw) + z * math.sin(yaw)
    zz = -x * math.sin(yaw) + z * math.cos(yaw)
    pitch = .72 + .18 * math.sin(phase)
    yy = y * math.cos(pitch) - zz * math.sin(pitch)
    depth = y * math.sin(pitch) + zz * math.cos(pitch)
    lean = .2 * math.sin(phase)
    xxx = xx * math.cos(lean) - yy * math.sin(lean)
    yyy = xx * math.sin(lean) + yy * math.cos(lean)
    perspective = 850 / (850-depth)
    return np.column_stack((800+xxx*perspective, 285+yyy*perspective,
                            depth, perspective))


def render(base, index):
    phase = math.tau * index / FRAMES
    # Render the fine geometry at twice the output size for clean moving edges.
    scale = 2
    fine = Image.new('RGB', (WIDTH*scale, HEIGHT*scale))
    draw = ImageDraw.Draw(fine)
    glow = Image.new('RGB', (WIDTH, HEIGHT))
    gd = ImageDraw.Draw(glow)
    segments = []
    for filament, offset in enumerate([-8, -4, 0, 4, 8]):
        curve = points(phase, offset)
        for k in range(len(T)-1):
            a, b = curve[k], curve[k+1]
            color = colors(k/(len(T)-1) + filament*.015)
            level = .42 + .72 * (a[2]+270)/540
            color = tuple(min(255, round(c*level)) for c in color)
            segments.append((a[2], a, b, color, filament))
    for depth, a, b, color, filament in sorted(segments, key=lambda x:x[0]):
        line = (a[0], a[1], b[0], b[1])
        draw.line(tuple(value*scale for value in line), fill=color,
                  width=max(2, round((2.2 if filament == 2 else 1.2)*a[3]*scale)))
        gd.line(line, fill=tuple(c//3 for c in color), width=9)
    curve = points(phase, 0)
    for particle in range(7):
        head = (index/FRAMES + particle/7) % 1
        for trail in range(17):
            t = (head-trail*.0017) % 1
            x, y, z, perspective = curve[int(t*(len(T)-1))]
            r = max(1.0, (3.8-trail*.15)*perspective)
            color = mix(BG, (214, 248, 255), (1-trail/18)*(.65+(z+270)/1600))
            draw.ellipse(((x-r)*scale,(y-r)*scale,(x+r)*scale,(y+r)*scale), fill=color)
            gd.ellipse((x-r*2,y-r*2,x+r*2,y+r*2), fill=tuple(c//2 for c in color))
    bloom = np.asarray(glow.filter(ImageFilter.GaussianBlur(12)), dtype=np.uint16)
    core = np.asarray(fine.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS),
                      dtype=np.uint16)
    image = Image.fromarray(np.clip(np.asarray(base, dtype=np.uint16)+core+bloom,
                                    0,255).astype('uint8'))
    return image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=Path('assets'))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    base = base_image()
    frames = [render(base, i) for i in range(FRAMES)]
    frames[0].save(args.output_dir/'hero.png', optimize=True)
    swatches = Image.new('RGB',(400*6,190))
    for k in range(6):
        swatches.paste(frames[k*(FRAMES//6)].resize((400,190)),(400*k,0))
    palette = swatches.quantize(colors=256,method=Image.Quantize.MEDIANCUT)
    indexed = [frame.quantize(palette=palette,dither=Image.Dither.NONE) for frame in frames]
    indexed[0].save(args.output_dir/'hero.gif',save_all=True,append_images=indexed[1:],
                    duration=DURATION,loop=0,disposal=1,optimize=True)
    for name in ['hero.png','hero.gif']:
        path=args.output_dir/name
        print(f'{path}: {path.stat().st_size:,} bytes')


if __name__ == '__main__':
    main()
