#!/usr/bin/env python3
"""Validate profile links, accessibility text, and the committed media."""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

from PIL import Image, ImageChops


ROOT = Path(__file__).resolve().parents[1]
ERRORS = []


def require(condition, message):
    if not condition:
        ERRORS.append(message)


class ProfileHTML(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.path = path
        self.targets = []
        self.images = []
        self.still_sources = []
        self.webp_sources = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        require(tag not in {'script', 'style', 'iframe', 'video'},
                f'{self.path.name}: unsupported tag {tag}')
        require(not any(k == 'style' or k.startswith('on') for k in values),
                f'{self.path.name}: script or inline style attribute')
        for key in ('src', 'href', 'srcset'):
            if values.get(key):
                self.targets.append(values[key])
        if tag == 'img':
            require(bool(values.get('alt', '').strip()),
                    f'{self.path.name}: image has no alt text')
            self.images.append(values.get('src', ''))
        if tag == 'source' and values.get('media') == '(prefers-reduced-motion: reduce)':
            self.still_sources.append(values.get('srcset', ''))
        if tag == 'source' and values.get('type') == 'image/webp':
            self.webp_sources.append(values.get('srcset', ''))


def check_markdown(path):
    source = path.read_text()
    parser = ProfileHTML(path)
    parser.feed(source)
    targets = parser.targets + re.findall(r'\[[^\]]*\]\(([^)\s]+)\)', source)
    for target in targets:
        url = urlsplit(target)
        if url.scheme or url.netloc or not url.path:
            continue
        destination = (path.parent / unquote(url.path)).resolve()
        require(destination.is_relative_to(ROOT),
                f'{path.name}: link escapes repository: {target}')
        require(destination.is_file(), f'{path.name}: broken local link: {target}')
    if path.name == 'PROFILE_STATIC.md':
        require(len(parser.images) == 2, 'Static profile must contain both posters')
        require(all(name.endswith('.png') for name in parser.images),
                'Static profile contains an animated image')
    if path.name == 'README.md':
        require(len(parser.images) == 2, 'Profile must contain both illustrations')
        require(len(parser.still_sources) == 2 and
                all(name.endswith('.png') for name in parser.still_sources),
                'Both animations need static reduced-motion sources')
        require(len(parser.webp_sources) == 2 and
                all(name.endswith('.webp') for name in parser.webp_sources),
                'Both animations need full-color WebP sources')
        require(all(name.endswith('.gif') for name in parser.images),
                'Both animations need GIF fallbacks')
    print(f'OK links and image alt text: {path.relative_to(ROOT)}')


def check_media(name, height):
    with Image.open(ROOT / 'assets' / f'{name}.png') as poster:
        require(poster.size == (1600, height), f'{name}: unexpected poster dimensions')
        require(getattr(poster, 'n_frames', 1) == 1, f'{name}: poster is animated')
        poster.load()
    for extension in ['gif', 'webp']:
        check_animation(ROOT / 'assets' / f'{name}.{extension}', height)


def check_animation(path, height):
    name = path.name
    require(path.stat().st_size < 10_000_000, f'{name}: animation exceeds 10 MB')
    with Image.open(path) as animation:
        count = getattr(animation, 'n_frames', 1)
        require(count > 1, f'{name}: image has no animation')
        require(animation.size == (1600, height), f'{name}: animation dimensions differ')
        require(animation.info.get('loop') == 0, f'{name}: animation does not loop')
        first = animation.convert('RGB')
        total = 0
        changed = False
        for index in range(count):
            animation.seek(index)
            animation.load()
            duration = animation.info.get('duration', 0)
            require(duration > 0, f'{name}: frame {index} has no duration')
            total += duration
            changed |= ImageChops.difference(first, animation.convert('RGB')).getbbox() is not None
        require(changed, f'{name}: frames have no visible difference')
        require(3000 <= total <= 6000, f'{name}: unexpected loop duration {total} ms')
        print(f'OK {name}: 1600×{height}, {count} frames, {total} ms, '
              f'{path.stat().st_size / 1_000_000:.2f} MB')


def main():
    for path in sorted(ROOT.rglob('*.md')):
        check_markdown(path)
    for name, height in [('hero-v5', 800), ('field-v5', 220)]:
        check_media(name, height)
    if ERRORS:
        raise SystemExit('\n'.join(f'FAIL: {error}' for error in ERRORS))
    print('Profile validation passed.')


if __name__ == '__main__':
    main()
