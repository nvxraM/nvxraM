#!/usr/bin/env python3
"""Render and package the procedural v2 Blender sculpture for a GitHub README.

Blender 4.3+, FFmpeg and Pillow are required. Frames and Mesa shader caches stay
outside the checkout. Use --resume to reuse frames from an interrupted render
made with the same settings, or --package-only to rebuild without rendering.
A shared full-frame palette and subtle ordered dithering preserve the smooth
pearlescent gradients without introducing random noise or color flicker.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path

from PIL import Image


def package(frames_dir, output_dir, frame_count, duration, colors=256):
    files=[frames_dir/f'frame-{i:04d}.png' for i in range(frame_count)]
    missing=[str(path) for path in files if not path.exists()]
    if missing: raise SystemExit('Missing frames: '+', '.join(missing[:5]))
    output_dir.mkdir(parents=True,exist_ok=True)
    with Image.open(files[0]) as image:
        image.convert('RGB').save(output_dir/'hero-v2.png',optimize=True)
    ffmpeg=shutil.which('ffmpeg')
    if not ffmpeg:
        raise SystemExit('FFmpeg is required to package the animation.')
    filters=(f'[0:v]trim=end_frame={frame_count},split[a][b];'
             f'[a]palettegen=max_colors={colors}:reserve_transparent=1:stats_mode=diff[p];'
             '[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle')
    subprocess.run([ffmpeg,'-v','warning','-threads','3','-filter_complex_threads','3',
                    '-framerate',f'{1000/duration:g}','-i',str(frames_dir/'frame-%04d.png'),
                    '-filter_complex',filters,'-loop','0','-y',
                    str(output_dir/'hero-v2.gif')],check=True)
    for name in ('hero-v2.png','hero-v2.gif'):
        path=output_dir/name
        print(f'{path}: {path.stat().st_size:,} bytes')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--frames-dir',type=Path,default=Path('/tmp/nvxram-v2-frames'))
    p.add_argument('--output-dir',type=Path,default=Path('assets'))
    p.add_argument('--frame-count',type=int,default=80)
    p.add_argument('--duration',type=int,default=50)
    p.add_argument('--colors',type=int,choices=[64,96,128,192,256],default=256)
    p.add_argument('--samples',type=int,default=8)
    p.add_argument('--threads',type=int,default=4)
    p.add_argument('--engine',choices=['CYCLES','BLENDER_EEVEE_NEXT'],default='BLENDER_EEVEE_NEXT')
    p.add_argument('--package-only',action='store_true')
    p.add_argument('--resume',action='store_true',help='Reuse existing rendered frames')
    args=p.parse_args()
    if not args.package_only:
        env=os.environ.copy()
        env['MESA_SHADER_CACHE_DIR']='/tmp/nvxram-mesa-cache'
        env['XDG_CACHE_HOME']='/tmp/nvxram-cache'
        missing=[i for i in range(args.frame_count)
                 if not (args.frames_dir/f'frame-{i:04d}.png').exists()]
        frame_indices=','.join(map(str,missing)) if args.resume else 'all'
        if frame_indices:
            subprocess.run([shutil.which('blender') or 'blender','--background',
                        '--python-exit-code','1','--python',
                        str(Path(__file__).with_name('scene_v2.py')),'--',
                        '--output-dir',str(args.frames_dir),'--frame-count',str(args.frame_count),
                        '--frames',frame_indices,
                        '--samples',str(args.samples),'--threads',str(args.threads),
                        '--engine',args.engine],check=True,env=env)
    package(args.frames_dir,args.output_dir,args.frame_count,args.duration,args.colors)


if __name__=='__main__':
    main()
