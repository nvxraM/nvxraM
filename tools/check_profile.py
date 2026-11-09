#!/usr/bin/env python3
"""Validate profile links, accessibility text, and the committed media."""

from __future__ import annotations

import argparse
from bisect import bisect_right
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

from PIL import Image, ImageChops, ImageStat


ROOT = Path(__file__).resolve().parents[1]
ERRORS = []
CURRENT_STEM = 'panel-v6.2'
RAW_REPOSITORY = 'https://raw.githubusercontent.com/nvxraM/nvxraM/'


def require(condition, message):
    if not condition:
        ERRORS.append(message)


def pinned_asset(target: str, suffix: str) -> str | None:
    """Return the immutable asset commit, or reject mutable/stale profile URLs."""
    match = re.fullmatch(
        re.escape(RAW_REPOSITORY) + r'([0-9a-f]{40})/assets/' +
        re.escape(CURRENT_STEM) + re.escape(suffix), target)
    return match.group(1) if match else None


class ProfileHTML(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.path = path
        self.targets = []
        self.images = []
        self.still_sources = []
        self.webp_sources = []
        self.alt_text = []
        self.visible_text = []
        self.visible_links = []
        self._anchor = None

    def handle_data(self, data):
        if data.strip():
            self.visible_text.append(data.strip())
            if self._anchor is not None:
                self._anchor[1].append(data.strip())

    def handle_endtag(self, tag):
        if tag == 'a' and self._anchor is not None:
            self.visible_links.append((self._anchor[0], ' '.join(self._anchor[1])))
            self._anchor = None

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == 'a':
            self._anchor = (values.get('href', ''), [])
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
            self.alt_text.append(values.get('alt', ''))
        if tag == 'source' and values.get('media') == '(prefers-reduced-motion: reduce)':
            self.still_sources.append(values.get('srcset', ''))
        if tag == 'source' and values.get('type') == 'image/webp':
            self.webp_sources.append(values.get('srcset', ''))


def check_markdown(path):
    source = path.read_text()
    parser = ProfileHTML(path)
    parser.feed(source)
    markdown_links = re.findall(r'\[([^\]]*)\]\(([^)\s]+)\)', source)
    targets = parser.targets + [target for _label, target in markdown_links]
    for target in targets:
        url = urlsplit(target)
        if target.startswith(RAW_REPOSITORY):
            require(bool(re.match(re.escape(RAW_REPOSITORY) + r'[0-9a-f]{40}/', target)),
                    f'{path.name}: repository media must use an immutable full commit SHA: {target}')
        if url.scheme or url.netloc or not url.path:
            continue
        destination = (path.parent / unquote(url.path)).resolve()
        require(destination.is_relative_to(ROOT),
                f'{path.name}: link escapes repository: {target}')
        require(destination.is_file(), f'{path.name}: broken local link: {target}')
    if path.name == 'PROFILE_STATIC.md':
        require(len(parser.images) == 1, 'Static profile must contain one panel')
        require(all(urlsplit(name).path.endswith(f'/assets/{CURRENT_STEM}.png') or
                    name == f'../assets/{CURRENT_STEM}.png' for name in parser.images),
                'Static profile must show the current reduced-motion PNG')
    if path.name == 'README.md':
        require(len(parser.images) == 1, 'Profile must contain one integrated panel')
        require(len(parser.still_sources) == 1 and
                all(name.endswith('.png') for name in parser.still_sources),
                'The panel needs a static reduced-motion source')
        require(len(parser.webp_sources) == 1 and
                all(name.endswith('.webp') for name in parser.webp_sources),
                'The panel needs a full-color WebP source')
        require(all(name.endswith('.gif') for name in parser.images),
                'The panel needs a GIF fallback')
        commits = [pinned_asset(target, suffix)
                   for sources, suffix in [(parser.still_sources, '.png'),
                                            (parser.webp_sources, '.webp'),
                                            (parser.images, '.gif')]
                   for target in sources]
        require(len(commits) == 3 and all(commits) and len(set(commits)) == 1,
                'README must pin all three newest artwork formats to the same immutable commit')
        navigation = parser.visible_links + [(target, label) for label, target in markdown_links]
        require(any(label.strip() and
                    urlsplit(target).path.rstrip('/').endswith('docs/DESIGN_HISTORY.md')
                    for target, label in navigation), 'README needs visible design-history navigation')
    if path.name == 'PROFILE_STATIC.md':
        require(not parser.visible_text, 'The profile must keep its name inside the panel')
    if path.name in {'README.md', 'PROFILE_STATIC.md'}:
        require(any('nvxraM' in alt for alt in parser.alt_text),
                'Image alt text must include the embedded handle nvxraM')
    print(f'OK links and image alt text: {path.relative_to(ROOT)}')


def image_mae(first, second):
    """Mean absolute RGB error in [0,1], independent of image bit depth."""
    difference = ImageChops.difference(first.convert('RGB'), second.convert('RGB'))
    return sum(ImageStat.Stat(difference).mean) / (3 * 255)


def check_media(name, height):
    with Image.open(ROOT / 'assets' / f'{name}.png') as poster:
        require(poster.size == (1600, height), f'{name}: unexpected poster dimensions')
        require(getattr(poster, 'n_frames', 1) == 1, f'{name}: poster is animated')
        poster.load()
        reference = poster.convert('RGB')
    reports = {}
    for extension in ['gif', 'webp']:
        reports[extension] = check_animation(
            ROOT / 'assets' / f'{name}.{extension}', height, reference)
    require(reports['gif']['duration_ms'] == reports['webp']['duration_ms'],
            f'{name}: GIF and WebP loop durations differ')
    # Encoders may merge identical held frames. Compare the image displayed at
    # the same playback times rather than assuming equal encoded frame counts.
    duration = min(reports['gif']['duration_ms'], reports['webp']['duration_ms'])
    errors = []
    if duration > 0:
        for tick in range(12):
            when = tick * duration / 12
            displayed = []
            for extension in ['gif', 'webp']:
                report = reports[extension]
                index = min(bisect_right(report['_ends_ms'], when),
                            len(report['_thumbnails']) - 1)
                displayed.append(report['_thumbnails'][index])
            errors.append(image_mae(*displayed))
        require(max(errors) < .05,
                f'{name}: GIF/WebP playback differs by more than the image tolerance')
    public = {extension: {key: value for key, value in report.items()
                          if not key.startswith('_')}
              for extension, report in reports.items()}
    public['max_cross_format_timeline_mae'] = max(errors, default=0)
    return public


def check_animation(path, height, poster=None):
    name = path.name
    require(path.stat().st_size < 10_000_000, f'{name}: animation exceeds 10 MB')
    with Image.open(path) as animation:
        count = getattr(animation, 'n_frames', 1)
        require(count > 1, f'{name}: image has no animation')
        require(animation.size == (1600, height), f'{name}: animation dimensions differ')
        require(animation.info.get('loop') == 0, f'{name}: animation does not loop')
        first = animation.convert('RGB')
        poster_error = image_mae(poster, first) if poster else None
        if poster is not None:
            require(poster_error < .04,
                    f'{name}: first animation frame does not match the PNG poster')
        total = 0
        changed = False
        thumbnails = []
        ends = []
        for index in range(count):
            animation.seek(index)
            animation.load()
            duration = animation.info.get('duration', 0)
            require(duration > 0, f'{name}: frame {index} has no duration')
            total += duration
            ends.append(total)
            changed |= ImageChops.difference(first, animation.convert('RGB')).getbbox() is not None
            thumbnails.append(animation.convert('RGB').resize((128, 72), Image.Resampling.BOX))
        require(changed, f'{name}: frames have no visible difference')
        require(3000 <= total <= 6000, f'{name}: unexpected loop duration {total} ms')
        adjacent = [image_mae(a, b) for a, b in zip(thumbnails, thumbnails[1:])]
        seam = image_mae(thumbnails[-1], thumbnails[0])
        require(seam <= max(max(adjacent, default=0) * 1.75, .005),
                f'{name}: loop seam is substantially larger than adjacent-frame motion')
        print(f'OK {name}: 1600×{height}, {count} frames, {total} ms, '
              f'{path.stat().st_size / 1_000_000:.2f} MB, seam MAE {seam:.6f}')
        return {'frame_count': count, 'duration_ms': total,
                'bytes': path.stat().st_size, 'poster_first_frame_mae': poster_error,
                'loop_seam_mae': seam, 'max_adjacent_mae': max(adjacent, default=0),
                '_thumbnails': thumbnails, '_ends_ms': ends}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, help='Write numeric media-check evidence as JSON')
    args = parser.parse_args()
    ERRORS.clear()
    for path in sorted(ROOT.rglob('*.md')):
        # Local environments, diagnostics and preserved migration snapshots are
        # not published profile pages.
        if any(part.startswith('.') for part in path.relative_to(ROOT).parts):
            continue
        check_markdown(path)
    reports = {}
    require(all((ROOT / 'assets' / f'{CURRENT_STEM}.{suffix}').is_file()
                for suffix in ['png', 'gif', 'webp']), 'Current version media is missing')
    if all((ROOT / 'assets' / f'{CURRENT_STEM}.{suffix}').is_file()
           for suffix in ['png', 'gif', 'webp']):
        reports[CURRENT_STEM] = check_media(CURRENT_STEM, 900)
    # Previously published assets remain checked while retained in this tree.
    if all((ROOT / 'assets' / f'panel-v6.{suffix}').is_file()
           for suffix in ['png', 'gif', 'webp']):
        reports['panel-v6'] = check_media('panel-v6', 900)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps({'current_stem': CURRENT_STEM,
                                          'media': reports, 'errors': ERRORS}, indent=2) + '\n')
    if ERRORS:
        raise SystemExit('\n'.join(f'FAIL: {error}' for error in ERRORS))
    print('Profile validation passed.')


if __name__ == '__main__':
    main()
