#!/usr/bin/env python3
"""Render a local, original animated Python terminal panel.

    python tools/render_terminal.py --output-dir assets

Requires Pillow. Artwork uses the local DejaVu font and no network assets.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


WIDTH, HEIGHT = 1600, 420
FRAME_COUNT = 60
BG = (9, 15, 26)
HEADER = (13, 21, 34)
EDGE = (38, 52, 69)
TEXT = (225, 234, 245)
MUTED = (138, 157, 181)
QUIET = (72, 93, 117)
TEAL = (102, 227, 196)
LAVENDER = (169, 164, 245)
FONT_ROOT = Path('/usr/share/fonts/truetype/dejavu')


def font(size: int):
    return ImageFont.truetype(str(FONT_ROOT / 'DejaVuSansMono.ttf'), size)


CODE_FONT = font(30)
SMALL_FONT = font(20)
TITLE_FONT = font(23)
LINE_HEIGHT = 36
CODE_X, CODE_Y = 88, 77

# Each token retains a color as it is gradually revealed. The complete program
# is valid Python; the final line below the program is its actual output.
LINES = [
    [('interests', TEXT), (' = (', MUTED)],
    [('    ', TEXT), ('"genome assembly"', TEAL), (',', MUTED)],
    [('    ', TEXT), ('"Hi-C"', TEAL), (',', MUTED)],
    [('    ', TEXT), ('"population genetics"', TEAL), (',', MUTED)],
    [(')', MUTED)],
    [('approach', TEXT), (' = ', MUTED), ('"question → build → understand"', TEAL)],
    [('print', LAVENDER), ('(', MUTED), ('"Stay curious. Keep building."', TEAL), (')', MUTED)],
]
PROGRAM = '\n'.join(''.join(value for value, _ in tokens) for tokens in LINES)
OUTPUT = 'Stay curious. Keep building.'


def render(visible: int, *, show_output: bool, cursor_on: bool):
    image = Image.new('RGB', (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((1, 1, WIDTH - 2, HEIGHT - 2), radius=20,
                           fill=BG, outline=EDGE, width=2)
    # A rounded header with a flat lower edge stays inside the outer border.
    draw.rounded_rectangle((3, 3, WIDTH - 4, 61), radius=18, fill=HEADER)
    draw.rectangle((3, 32, WIDTH - 4, 61), fill=HEADER)
    draw.line((3, 62, WIDTH - 4, 62), fill=EDGE, width=1)
    for x, color in [(35, (220, 116, 126)), (61, (220, 186, 119)), (87, TEAL)]:
        draw.ellipse((x, 26, x + 12, 38), fill=color)
    draw.text((WIDTH // 2, 17), 'profile.py', fill=MUTED, font=TITLE_FONT, anchor='mt')
    draw.text((WIDTH - 34, 22), 'Python', fill=QUIET, font=SMALL_FONT, anchor='rt')

    remaining = visible
    cursor = (CODE_X, CODE_Y)
    for index, tokens in enumerate(LINES):
        y = CODE_Y + LINE_HEIGHT * index
        draw.text((45, y + 8), str(index + 1), fill=QUIET, font=SMALL_FONT, anchor='rt')
        x = CODE_X
        line_started = remaining >= 0
        for value, color in tokens:
            portion = value[:max(0, remaining)]
            if portion:
                draw.text((x, y), portion, fill=color, font=CODE_FONT)
                x += draw.textlength(portion, font=CODE_FONT)
            remaining -= len(value)
        if line_started:
            cursor = (x, y)
        # Account for the newline while retaining the cursor at the last
        # revealed character until the next line starts appearing.
        if remaining > 0 and index < len(LINES) - 1:
            cursor = (CODE_X, y + LINE_HEIGHT)
        remaining -= 1

    if show_output:
        y = CODE_Y + LINE_HEIGHT * len(LINES) + 5
        draw.text((45, y + 6), '›', fill=TEAL, font=TITLE_FONT, anchor='rt')
        draw.text((CODE_X, y), OUTPUT, fill=TEXT, font=CODE_FONT)
    elif cursor_on:
        x, y = cursor
        draw.rounded_rectangle((x + 3, y + 6, x + 7, y + 32), radius=1, fill=TEAL)
    return image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=Path('assets'))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    compile(PROGRAM, 'profile.py', 'exec')
    frames = []
    for index in range(FRAME_COUNT):
        # Three introductory frames, 36 typing frames, and a 21-frame hold.
        progress = min(1.0, max(0.0, (index - 3) / 35))
        visible = round(progress * len(PROGRAM))
        frames.append(render(visible, show_output=index >= 39,
                             cursor_on=(index // 5) % 2 == 0))

    # The poster always contains the completed code and output.
    frames[-1].save(args.output_dir / 'terminal.png', optimize=True)
    # Fixed shared palette avoids temporal color shifts. Every token and
    # interface color is present in the finished frame.
    palette = frames[-1].quantize(colors=192, method=Image.Quantize.MEDIANCUT)
    indexed = [frame.quantize(palette=palette, dither=Image.Dither.NONE)
               for frame in frames]
    durations = [90 if index % 3 == 0 else 80 for index in range(FRAME_COUNT)]
    indexed[0].save(args.output_dir / 'terminal.gif', save_all=True,
                    append_images=indexed[1:], duration=durations,
                    loop=0, optimize=True, disposal=1)
    for name in ['terminal.png', 'terminal.gif']:
        path = args.output_dir / name
        with Image.open(path) as result:
            duration = 0
            for index in range(getattr(result, 'n_frames', 1)):
                result.seek(index)
                duration += result.info.get('duration', 0)
            print(f'{path}: {result.size[0]}x{result.size[1]}, '
                  f'{getattr(result, "n_frames", 1)} frame(s), '
                  f'{duration} ms, {path.stat().st_size:,} bytes')


if __name__ == '__main__':
    main()
