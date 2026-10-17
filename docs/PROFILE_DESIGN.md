# Version 5 · PELAGIC

The profile opens with a centered handle and “curiosity runs deep.” above two
original animations. The static version is in
[PROFILE_STATIC.md](PROFILE_STATIC.md); [VERSIONS.md](VERSIONS.md) links the
preserved designs.

PELAGIC is a deep-sea observatory inspired by luminous marine life. The main
scene places a cyan jellyfish with peach and violet inner filaments and trailing
tentacles in deep indigo water. The narrow footer studies luminous filament
fans and suspended plankton at a smaller scale. All geometry and materials are
procedural, with no downloaded assets or personal details.

Cycles renders the scenes with soft area lights, luminous surfaces, and 85 mm
perspective cameras with optical depth of field. The jellyfish's translucent
bell reveals its folded interior; layered particles and a distant organism
give the water depth.

The main illustration is 1600 × 800 pixels; the footer is 1600 × 220. Full-color
animated WebP images preserve photographic gradients, with GIF fallbacks for
compatibility. Both formats play without scripts or external services. PNG
posters serve browsers requesting reduced motion and the separate static page.
Both images have descriptive alt text and indigo canvases that also work
against GitHub's light theme.

## Regenerate

The committed images are ready to use. Regeneration is optional and requires
Blender 4.3.2, FFmpeg, Python 3.12+, Pillow, and NumPy. CPU path tracing can take
tens of minutes. Opening the profile needs no renderer or running service.

Use the existing checkout; no Git worktree is needed. From its root:

```bash
python -m venv /tmp/nvxram-art-venv
/tmp/nvxram-art-venv/bin/python -m pip install -r tools/requirements.txt
/tmp/nvxram-art-venv/bin/python tools/setup_oidn.py
/tmp/nvxram-art-venv/bin/python tools/render_v5_assets.py --kind hero --output-dir assets
/tmp/nvxram-art-venv/bin/python tools/render_v5_assets.py --kind field --output-dir assets
/tmp/nvxram-art-venv/bin/python tools/check_profile.py
```

The installer downloads Open Image Denoise 2.5.1 from the official RenderKit
GitHub release and verifies its pinned SHA-256 before extraction. The Linux
x86_64 CPU tool is cached outside the checkout under `/workspace/.nvxram-tools`.
The renderer also installs it when missing. It preserves normal HTTPS
certificate checks and uses no credentials or external render service.

`tools/scene_v5.py` and `tools/scene_field_v5.py` define the scenes. The wrapper
stores raw frames, denoised frames, and render fingerprints under
`/tmp/nvxram-v5`. Open Image Denoise cleans the rendered display RGB through its
supported LDR/sRGB route. Pillow packages full-color WebP animations at quality
90; FFmpeg packages GIF fallbacks with a shared palette and subtle ordered
dithering. Final assets use the names `hero-v5` and `field-v5`.

Both loops render a complete cycle of 60 native poses, played at 50 milliseconds
per frame for 3 seconds. The main scene uses up to 32 samples per pixel; the footer
uses 20. Each output frame is a native rendered pose, with no optical-flow
interpolation or frame blending. Setting `--pose-count` below `--frame-count`
optionally plays a cosine-timed back-and-forth sequence. Encoders may merge
repeated holds while retaining the full duration.

If the complete frames from the current scene are already present, repackage
them without rerendering:

```bash
/tmp/nvxram-art-venv/bin/python tools/render_v5_assets.py --kind hero --package-only
/tmp/nvxram-art-venv/bin/python tools/render_v5_assets.py --kind field --package-only
```

Use `--resume` to continue an interrupted render with the same scene and
settings. The wrapper checks that saved PNGs are complete; its fingerprints
include the scene, render settings, processing revision, and denoiser version.
Render again without `--resume` after editing a scene. Keep the text in both
Markdown profiles consistent when maintaining the design.

## Publish

Commit and push the files to the default branch of the public profile repository
`nvxraM/nvxraM`. The root `README.md` appears on the profile. GitHub may cache
updated image files briefly. Rendering scripts do not publish anything.
