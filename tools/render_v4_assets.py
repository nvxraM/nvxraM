#!/usr/bin/env python3
"""Render Cycles frames, denoise with OIDN, and package the original V4 artwork."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess

import numpy as np
from PIL import Image

from setup_oidn import VERSION as OIDN_VERSION, ensure_oidn


TOOLS = Path(__file__).resolve().parent


def render_specification(scene: Path, count: int, samples: int, kind: str,
                         pose_count: int | None = None):
    pose_count = count if pose_count is None else pose_count
    return {'generator': 'nvxram-v4',
            'processing_revision': 1, 'oidn_version': OIDN_VERSION,
            'scene_sha256': hashlib.sha256(scene.read_bytes()).hexdigest(),
            'frame_count': count, 'pose_count': pose_count,
            'motion': 'eased-pendulum' if pose_count < count else 'full-cycle',
            'samples': samples, 'kind': kind}


def prepare_work(work: Path, specification: dict, reuse: bool):
    raw, clean = work / 'raw', work / 'clean'
    raw.mkdir(parents=True, exist_ok=True)
    clean.mkdir(parents=True, exist_ok=True)
    manifest = work / 'render.json'
    if reuse:
        if not manifest.is_file() or json.loads(manifest.read_text()) != specification:
            raise SystemExit('Saved frames do not match this scene/settings. Render again without --resume.')
    else:
        # Remove only this renderer's old frames before recording a new run.
        # Otherwise an interrupted refresh could leave an old tail that a later
        # --resume would incorrectly accept as frames from the new scene.
        frames = [path for folder in [raw, clean] for path in folder.glob('frame-*.png')]
        if manifest.is_file():
            if json.loads(manifest.read_text()).get('generator') != 'nvxram-v4':
                raise SystemExit('This work directory belongs to another renderer; choose an empty one.')
        elif frames:
            raise SystemExit('Unrecognized frames in the work directory; choose an empty one.')
        for path in frames:
            path.unlink()
        manifest.write_text(json.dumps(specification, indent=2) + '\n')
    return raw, clean


def write_pfm(path: Path, pixels: np.ndarray):
    height, width, channels = pixels.shape
    if channels != 3 or not np.isfinite(pixels).all():
        raise ValueError('PFM input must contain finite RGB pixels.')
    with path.open('wb') as target:
        target.write(f'PF\n{width} {height}\n-1.0\n'.encode('ascii'))
        target.write(np.flipud(pixels).astype('<f4').tobytes())


def read_pfm(path: Path) -> np.ndarray:
    with path.open('rb') as source:
        if source.readline().strip() != b'PF':
            raise ValueError('Expected an RGB PFM output from OIDN.')
        width, height = map(int, source.readline().split())
        scale = float(source.readline())
        pixels = np.frombuffer(source.read(), dtype='<f4' if scale < 0 else '>f4')
    if pixels.size != width * height * 3 or not np.isfinite(pixels).all():
        raise ValueError('Incomplete or non-finite OIDN output.')
    return np.flipud(pixels.reshape(height, width, 3)).copy()


def complete_png(path: Path, size: tuple[int, int]) -> bool:
    try:
        with Image.open(path) as image:
            if image.format != 'PNG' or image.size != size:
                return False
            image.verify()
        return True
    except (OSError, ValueError, SyntaxError):
        return False


def denoise_png(source: Path, target: Path, binary: Path | None = None, threads: int = 4):
    binary = binary or ensure_oidn()
    target.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as image:
        pixels = np.asarray(image.convert('RGB'), dtype=np.float32) / 255
    raw_pfm = target.with_suffix('.input.pfm')
    clean_pfm = target.with_suffix('.output.pfm')
    temporary = target.with_suffix('.pending.png')
    try:
        write_pfm(raw_pfm, pixels)
        subprocess.run([str(binary), '--device', 'cpu', '--ldr', str(raw_pfm),
                        '--srgb', '--output', str(clean_pfm), '--quality', 'high',
                        '--threads', str(threads)], check=True,
                       stdout=subprocess.DEVNULL)
        output = read_pfm(clean_pfm)
        if output.shape != pixels.shape:
            raise ValueError('Denoising changed the image dimensions.')
        Image.fromarray(np.rint(np.clip(output, 0, 1) * 255).astype('uint8')).save(
            temporary, optimize=True)
        temporary.replace(target)
    finally:
        raw_pfm.unlink(missing_ok=True)
        clean_pfm.unlink(missing_ok=True)
        temporary.unlink(missing_ok=True)


def motion_sequence(clean: Path, count: int, pose_count: int) -> Path:
    if pose_count == count:
        return clean
    loop = clean.parent / 'loop'
    loop.mkdir(parents=True, exist_ok=True)
    for index in range(count):
        pose = round((pose_count-1) * (.5-.5*math.cos(math.tau*index/count)))
        # Every output is an exact native render. Only the pose timing changes;
        # no blending or estimated pixels alter shadows, reflections, or DOF.
        shutil.copy2(clean / f'frame-{pose:04d}.png', loop / f'frame-{index:04d}.png')
    return loop


def package_webp(sequence: Path, output: Path, stem: str, count: int, duration: int):
    """Keep full-color gradients for modern browsers, alongside the GIF fallback."""
    frames = []
    temporary = output / f'.{stem}.pending.webp'
    try:
        for index in range(count):
            with Image.open(sequence / f'frame-{index:04d}.png') as frame:
                frames.append(frame.convert('RGB'))
        frames[0].save(temporary, format='WEBP', save_all=True,
                       append_images=frames[1:], duration=duration, loop=0,
                       quality=90, method=4, allow_mixed=True)
        temporary.replace(output / f'{stem}.webp')
    finally:
        for frame in frames:
            frame.close()
        temporary.unlink(missing_ok=True)


def package(clean: Path, output: Path, stem: str, count: int, duration: int,
            colors: int, pose_count: int):
    files = [clean / f'frame-{index:04d}.png' for index in range(pose_count)]
    if any(not path.is_file() for path in files):
        raise SystemExit('The complete denoised frame sequence is required for packaging.')
    output.mkdir(parents=True, exist_ok=True)
    sequence = motion_sequence(clean, count, pose_count)
    filters = (f'[0:v]trim=end_frame={count},split[a][b];'
               f'[a]palettegen=max_colors={colors}:reserve_transparent=1:stats_mode=diff[p];'
               '[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle')
    poster_temp = output / f'.{stem}.pending.png'
    gif_temp = output / f'.{stem}.pending.gif'
    try:
        with Image.open(files[0]) as poster:
            poster.save(poster_temp, optimize=True)
        subprocess.run(['ffmpeg', '-v', 'warning', '-threads', '3',
                        '-filter_complex_threads', '3', '-framerate', f'{1000/duration:g}',
                        '-i', str(sequence / 'frame-%04d.png'), '-filter_complex', filters,
                        '-loop', '0', '-y', str(gif_temp)], check=True)
        gif_temp.replace(output / f'{stem}.gif')
        poster_temp.replace(output / f'{stem}.png')
    finally:
        poster_temp.unlink(missing_ok=True)
        gif_temp.unlink(missing_ok=True)
    package_webp(sequence, output, stem, count, duration)
    for suffix in ['gif', 'png', 'webp']:
        path = output / f'{stem}.{suffix}'
        print(f'{path}: {path.stat().st_size:,} bytes', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind', choices=['hero', 'field'], default='hero')
    parser.add_argument('--output-dir', type=Path, default=Path('assets'))
    parser.add_argument('--work-dir', type=Path)
    parser.add_argument('--frame-count', type=int)
    parser.add_argument('--pose-count', type=int,
                        help='Native poses; defaults to half-cycle plus one, played with cosine easing')
    parser.add_argument('--samples', type=int)
    parser.add_argument('--threads', type=int, default=4)
    parser.add_argument('--duration', type=int, default=50)
    parser.add_argument('--colors', type=int, choices=[96, 128, 192, 256], default=256)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--package-only', action='store_true')
    args = parser.parse_args()
    count = (80 if args.kind == 'hero' else 60) if args.frame_count is None else args.frame_count
    samples = (32 if args.kind == 'hero' else 20) if args.samples is None else args.samples
    poses = (count//2+1) if args.pose_count is None else args.pose_count
    if min(count, samples, args.threads, args.duration) < 1:
        raise SystemExit('Frame count, samples, threads, and duration must be positive.')
    if not 1 <= poses <= count:
        raise SystemExit('Pose count must be between one and the output frame count.')
    scene_path = TOOLS / ('scene_v4.py' if args.kind == 'hero' else 'scene_field_v4.py')
    work = args.work_dir or Path('/tmp/nvxram-v4') / args.kind
    specification = render_specification(scene_path, count, samples, args.kind, poses)
    raw, clean = prepare_work(work, specification, args.resume or args.package_only)
    size = (1600, 800 if args.kind == 'hero' else 240)
    invalid_raw = [index for index in range(poses)
                   if not complete_png(raw / f'frame-{index:04d}.png', size)]
    if args.package_only:
        if any(not complete_png(clean / f'frame-{index:04d}.png', size)
               for index in range(poses)):
            raise SystemExit('Complete denoised PNG poses are required for packaging.')
    if not args.package_only:
        binary = ensure_oidn()
        for index in invalid_raw:
            (clean / f'frame-{index:04d}.png').unlink(missing_ok=True)
        missing = invalid_raw
        selected = ','.join(map(str, missing if args.resume else range(poses)))
        if selected:
            env = os.environ.copy()
            env['MESA_SHADER_CACHE_DIR'] = '/tmp/nvxram-mesa-cache'
            env['XDG_CACHE_HOME'] = '/tmp/nvxram-cache'
            subprocess.run([shutil.which('blender') or 'blender', '--background', '--factory-startup',
                            '--python-exit-code', '1', '--python', str(scene_path), '--',
                            '--output-dir', str(raw), '--frame-count', str(count),
                            '--frames', selected, '--samples', str(samples),
                            '--percent', '100', '--threads', str(args.threads)], check=True, env=env)
        for index in range(poses):
            source, target = raw / f'frame-{index:04d}.png', clean / f'frame-{index:04d}.png'
            if not complete_png(source, size):
                raise SystemExit(f'Rendered pose is incomplete: {source}')
            if not args.resume or not complete_png(target, size):
                denoise_png(source, target, binary, args.threads)
            print(f'V4_DENOISED {args.kind} {index+1}/{poses}', flush=True)
    package(clean, args.output_dir, f'{args.kind}-v4', count, args.duration, args.colors, poses)


if __name__ == '__main__':
    main()
