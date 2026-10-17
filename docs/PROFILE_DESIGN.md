# Version 4 · profile maintenance

The profile pairs minimal text with two original animations. The static version
is in [PROFILE_STATIC.md](PROFILE_STATIC.md); [VERSIONS.md](VERSIONS.md) links
the preserved designs.

The main artwork is a continuous champagne titanium knot, with deep teal
enamel and a porcelain seed, floating above an obsidian pedestal. The smaller
animation studies the same materials through curled titanium ribbons and
scattered beads on a dark stone surface. All geometry and materials are
procedural; the scenes contain no downloaded assets or personal details.

Both scenes use Cycles path tracing, softbox lighting, physical receiving
surfaces for shadows and reflections, and 85 mm perspective cameras with
optical depth of field. Fine surface grain, roughness variation, and beveled
edges give the materials scale.

The main illustration is 1600 × 800 pixels; the footer is 1600 × 240. Full-color
animated WebP images preserve photographic gradients, with GIF fallbacks for
compatibility. Both formats play without scripts or external services. PNG
posters serve browsers requesting reduced motion and the separate static page. Both images
have descriptive alt text and dark canvases that also work against GitHub's
light theme.

## Regenerate

The committed images are ready to use. Regeneration is optional and requires
Blender 4.3.2, FFmpeg, Python 3.12+, Pillow, and NumPy. CPU path tracing can take
tens of minutes. Opening the profile needs no renderer or running service.

Use the existing checkout; no Git worktree is needed. From its root:

```bash
python -m venv /tmp/nvxram-art-venv
/tmp/nvxram-art-venv/bin/python -m pip install -r tools/requirements.txt
/tmp/nvxram-art-venv/bin/python tools/setup_oidn.py
/tmp/nvxram-art-venv/bin/python tools/render_v4_assets.py --kind hero --output-dir assets
/tmp/nvxram-art-venv/bin/python tools/render_v4_assets.py --kind field --output-dir assets
/tmp/nvxram-art-venv/bin/python tools/check_profile.py
```

The installer downloads Open Image Denoise 2.5.1 from the official RenderKit
GitHub release and verifies its pinned SHA-256 before extraction. The Linux
x86_64 CPU tool is cached outside the checkout under `/workspace/.nvxram-tools`.
The renderer also installs it when missing. It preserves normal HTTPS
certificate checks and uses no credentials or external render service.

`tools/scene_v4.py` and `tools/scene_field_v4.py` define the scenes. The wrapper
stores raw frames, denoised frames, and render fingerprints under
`/tmp/nvxram-v4`. Open Image Denoise cleans the rendered display RGB through its
supported LDR/sRGB route. Pillow packages full-color WebP animations at quality
90; FFmpeg packages GIF fallbacks with a shared palette and subtle ordered
dithering. Final assets use the names `hero-v4` and `field-v4`.

The main loop uses 41 rendered poses with 80 timed output frames (4 seconds).
The macro loop uses 31 poses with 60 timed frames (3 seconds). A cosine-timed
back-and-forth sequence eases at each end. Each output frame copies a native
rendered pose; there is no optical-flow interpolation or frame blending. GIF
encoders may merge repeated holds while retaining the full duration.
`--pose-count` equal to `--frame-count` instead renders and plays the complete
native cycle.

If the complete frames from the current scene are already present, repackage
them without rerendering:

```bash
/tmp/nvxram-art-venv/bin/python tools/render_v4_assets.py --kind hero --package-only
/tmp/nvxram-art-venv/bin/python tools/render_v4_assets.py --kind field --package-only
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
