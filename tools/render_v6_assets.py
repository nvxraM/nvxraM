#!/usr/bin/env python3
"""Render Cycles frames with explicit devices and package the PELAGIC artwork."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

import numpy as np
from PIL import Image

from cycles_devices import BACKENDS
from setup_oidn import VERSION as OIDN_VERSION, ensure_oidn


TOOLS = Path(__file__).resolve().parent
DEFAULT_FONT = Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
DEFAULT_STEM = 'panel-v6.2'
DENOISERS = ('builtin', 'external')
BUILTIN_OIDN_VERSION = '2.5.0'


def asset_stem(value: str) -> str:
    """Keep output names as names, never paths into other project files."""
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', value):
        raise argparse.ArgumentTypeError('Asset stem must be a filename stem without directories.')
    return value


def render_specification(scene: Path, count: int, samples: int, kind: str,
                         pose_count: int | None = None, font: Path = DEFAULT_FONT,
                         backend: str = 'CUDA', device: str | None = None,
                         resolved_device: str | None = None,
                         denoiser: str = 'builtin'):
    if not font.is_file():
        raise SystemExit(f'Required font is missing: {font}. Install fonts-dejavu-core or pass --font.')
    pose_count = count if pose_count is None else pose_count
    return {'generator': 'nvxram-v6',
            'processing_revision': 2, 'denoiser': denoiser,
            'oidn_version': BUILTIN_OIDN_VERSION if denoiser == 'builtin' else OIDN_VERSION,
            'font_sha256': hashlib.sha256(font.read_bytes()).hexdigest(),
            'scene_sha256': hashlib.sha256(scene.read_bytes()).hexdigest(),
            'device_selector_sha256': hashlib.sha256(
                (TOOLS / 'cycles_devices.py').read_bytes()).hexdigest(),
            'compute_backend': backend, 'compute_device': device,
            'compute_device_id': resolved_device,
            'frame_count': count, 'pose_count': pose_count,
            'motion': 'eased-pendulum' if pose_count < count else 'full-cycle',
            'samples': samples, 'kind': kind}


def preflight_cycles(backend: str, device: str | None = None) -> dict:
    """Validate a device without rendering or touching saved frame directories."""
    temporary_root = TOOLS.parent / '.local' / 'tmp'
    temporary_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='cycles-preflight-', dir=temporary_root) as temporary:
        env = os.environ.copy()
        env['TMPDIR'] = temporary
        env['BLENDER_TMPDIR'] = temporary
        command = [shutil.which('blender') or 'blender', '--background', '--factory-startup',
                   '--disable-autoexec', '--python-exit-code', '1', '--python',
                   str(TOOLS / 'cycles_devices.py'), '--', '--backend', backend]
        if device:
            command += ['--device', device]
        try:
            result = subprocess.run(command, check=True, capture_output=True, text=True,
                                    env=env, timeout=60)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as error:
            details = '\n'.join(str(value).strip() for value in
                                [getattr(error, 'stdout', ''), getattr(error, 'stderr', '')]
                                if value)
            raise SystemExit(
                f'Cycles {backend} preflight failed before changing saved frames. '
                f'Use --backend CPU for an explicit CPU run.\n{details or error}'
            ) from error
    prefix = 'CYCLES_DEVICE_SELECTION='
    records = [line[len(prefix):] for line in result.stdout.splitlines()
               if line.startswith(prefix)]
    try:
        if len(records) != 1:
            raise ValueError('Expected one device-selection record.')
        selection = json.loads(records[0])
        expected_scene_device = 'CPU' if backend == 'CPU' else 'GPU'
        devices = selection['devices']
        if (selection['backend'] != backend or
                selection['scene_device'] != expected_scene_device or
                not isinstance(devices, list) or len(devices) != 1 or
                devices[0]['type'] != backend):
            raise ValueError('Preflight returned a different compute device.')
        if backend != 'CPU':
            if not isinstance(devices[0]['id'], str) or not devices[0]['id']:
                raise ValueError('GPU preflight did not provide a persistent device ID.')
            if device and device not in (devices[0]['name'], devices[0]['id']):
                raise ValueError('GPU preflight did not select the requested device.')
    except (ValueError, KeyError, TypeError, IndexError) as error:
        raise SystemExit('Invalid Cycles preflight result; saved frames were not changed.') from error
    print(prefix + json.dumps(selection, sort_keys=True), flush=True)
    return selection


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
            if json.loads(manifest.read_text()).get('generator') != 'nvxram-v6':
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
    asset_stem(stem)
    files = [clean / f'frame-{index:04d}.png' for index in range(pose_count)]
    if any(not path.is_file() for path in files):
        raise SystemExit('The complete denoised frame sequence is required for packaging.')
    output.mkdir(parents=True, exist_ok=True)
    sequence = motion_sequence(clean, count, pose_count)
    filters = (f'[0:v]trim=end_frame={count},split[a][b];'
               f'[a]palettegen=max_colors={colors}:reserve_transparent=1:stats_mode=diff[p];'
               '[b][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle')
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
    parser.add_argument('--output-dir', type=Path, default=TOOLS.parent / 'assets')
    parser.add_argument('--stem', type=asset_stem, default=DEFAULT_STEM,
                        help='Output filename stem (default: panel-v6.2); preserves older assets')
    parser.add_argument('--work-dir', type=Path)
    parser.add_argument('--frame-count', type=int)
    parser.add_argument('--pose-count', type=int,
                        help='Native poses; defaults to the full native cycle; fewer poses enable cosine easing')
    parser.add_argument('--samples', type=int)
    parser.add_argument('--font', type=Path, default=DEFAULT_FONT)
    parser.add_argument('--threads', type=int, default=4)
    parser.add_argument('--debug-cycles', action='store_true',
                        help='Include Cycles tracing-device diagnostics in render logs')
    parser.add_argument('--denoiser', choices=DENOISERS, default='builtin',
                        help='Blender bundled CPU OIDN (default), or the optional external OIDN tool')
    parser.add_argument('--backend', choices=BACKENDS, default='CUDA',
                        help='Cycles backend (default: CUDA); CPU is an explicit fallback')
    parser.add_argument('--device', help='Exact GPU name or Cycles ID; required if more than one GPU matches')
    parser.add_argument('--oidn-cache-dir', type=Path,
                        default=TOOLS.parent / '.local' / 'tools' / 'oidn')
    parser.add_argument('--duration', type=int, default=50)
    parser.add_argument('--colors', type=int, choices=[96, 128, 192, 256], default=96)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--package-only', action='store_true')
    args = parser.parse_args()
    if args.backend == 'CPU' and args.device:
        parser.error('Omit --device when using --backend CPU.')
    count = 60 if args.frame_count is None else args.frame_count
    samples = 48 if args.samples is None else args.samples
    poses = count if args.pose_count is None else args.pose_count
    if min(count, samples, args.threads, args.duration) < 1:
        raise SystemExit('Frame count, samples, threads, and duration must be positive.')
    if not 1 <= poses <= count:
        raise SystemExit('Pose count must be between one and the output frame count.')
    scene_path = TOOLS / 'scene_v6.py'
    work = args.work_dir or TOOLS.parent / '.local' / 'render-v6.2'
    if args.package_only:
        # Packaging needs no GPU. Reuse only the recorded device identity;
        # prepare_work still verifies every other fingerprint field below.
        try:
            saved_specification = json.loads((work / 'render.json').read_text())
            resolved_device = saved_specification.get('compute_device_id')
        except (OSError, ValueError, AttributeError) as error:
            raise SystemExit('A valid saved render manifest is required for packaging.') from error
    else:
        selection = preflight_cycles(args.backend, args.device)
        resolved_device = (selection['devices'][0]['id']
                           if args.backend != 'CPU' else None)
    specification = render_specification(scene_path, count, samples, 'panel', poses,
                                         args.font, args.backend, args.device, resolved_device,
                                         args.denoiser)
    raw, clean = prepare_work(work, specification, args.resume or args.package_only)
    size = (1600, 900)
    invalid_raw = [index for index in range(poses)
                   if not complete_png(raw / f'frame-{index:04d}.png', size)]
    if args.package_only:
        if any(not complete_png(clean / f'frame-{index:04d}.png', size)
               for index in range(poses)):
            raise SystemExit('Complete denoised PNG poses are required for packaging.')
    if not args.package_only:
        binary = ensure_oidn(args.oidn_cache_dir) if args.denoiser == 'external' else None
        for index in invalid_raw:
            (clean / f'frame-{index:04d}.png').unlink(missing_ok=True)
        missing = invalid_raw
        selected = ','.join(map(str, missing if args.resume else range(poses)))
        if selected:
            env = os.environ.copy()
            temporary = work / 'tmp'
            temporary.mkdir(parents=True, exist_ok=True)
            env['TMPDIR'] = str(temporary.resolve())
            env['BLENDER_TMPDIR'] = env['TMPDIR']
            env['MESA_SHADER_CACHE_DIR'] = str((work / 'mesa-cache').resolve())
            env['XDG_CACHE_HOME'] = str((work / 'cache').resolve())
            device_args = ['--backend', args.backend, '--denoiser', args.denoiser]
            if resolved_device:
                device_args += ['--device', resolved_device]
            subprocess.run([shutil.which('blender') or 'blender', '--background', '--factory-startup',
                            *(['--debug-cycles'] if args.debug_cycles else []),
                            '--disable-autoexec', '--python-exit-code', '1', '--python', str(scene_path), '--',
                            '--output-dir', str(raw), '--frame-count', str(count),
                            '--frames', selected, '--samples', str(samples),
                            '--font', str(args.font.resolve()),
                            '--percent', '100', '--threads', str(args.threads),
                            *device_args], check=True, env=env)
        for index in range(poses):
            source, target = raw / f'frame-{index:04d}.png', clean / f'frame-{index:04d}.png'
            if not complete_png(source, size):
                raise SystemExit(f'Rendered pose is incomplete: {source}')
            if not args.resume or not complete_png(target, size):
                if args.denoiser == 'builtin':
                    # Cycles already applied its bundled CPU OIDN before saving.
                    # Preserve the packaging/reuse layout without a second pass.
                    shutil.copy2(source, target)
                else:
                    denoise_png(source, target, binary, args.threads)
            print(f'V6_DENOISED {index+1}/{poses}', flush=True)
    package(clean, args.output_dir, args.stem, count, args.duration, args.colors, poses)


if __name__ == '__main__':
    main()
