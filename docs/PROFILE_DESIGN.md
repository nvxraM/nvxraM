# Version 3 · profile maintenance

The profile keeps only the handle, the existing short tagline, and two original
animations. Its footer links stay removed. The static version is in
[PROFILE_STATIC.md](PROFILE_STATIC.md); [VERSIONS.md](VERSIONS.md) records the
saved versions 1 and 2.

The main artwork is a fractured basalt specimen opening around a porcelain
core and an impossible titanium curl. It floats above a honed stone plinth.
The smaller animation is a macro still life of pearl and metal droplets on
carved charcoal stone. The physical staging grounds the surreal shapes without
adding a written biography.

Both scenes use Cycles path tracing, a dominant large softbox, receiving
surfaces for cast and contact shadows, and perspective 85 mm cameras with
optical depth of field. Foreground and background droplets fall out of focus;
the subject plane stays sharp. Surface grain, subtle roughness variation, and
beveled edges give the materials scale. Neither scene uses a painted shadow or
an image-wide blur to imitate these effects.

Both illustrations are 1600 pixels wide. GIFs provide animation on GitHub
without scripts or external services. PNG posters are selected by browsers
requesting reduced motion and used by the separate static page. Each image has
descriptive alt text. The dark canvas also works against GitHub's light theme.

## Regenerate

The committed images are ready to use. Regeneration is optional and requires
Blender 4.3.2, FFmpeg, Python 3.12+, Pillow, NumPy, and the DejaVu Sans system font
at `/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf`. CPU path tracing takes
several minutes. Opening the profile needs no renderer or running service.

Use the existing checkout; no Git worktree is needed. From its root:

```bash
python -m venv /tmp/nvxram-art-venv
/tmp/nvxram-art-venv/bin/python -m pip install -r tools/requirements.txt
/tmp/nvxram-art-venv/bin/python tools/setup_oidn.py
/tmp/nvxram-art-venv/bin/python tools/render_v3_assets.py --kind hero --output-dir assets
/tmp/nvxram-art-venv/bin/python tools/render_v3_assets.py --kind field --output-dir assets
/tmp/nvxram-art-venv/bin/python tools/check_profile.py
```

The installer downloads Open Image Denoise 2.5.1 from the official RenderKit
GitHub release and verifies its pinned SHA-256 before extraction. The Linux
x86_64 CPU tool is cached outside the checkout under `/workspace/.nvxram-tools`.
The renderer also installs it when missing. It preserves normal HTTPS
certificate checks and uses no credentials or external render service.

`tools/scene_v3.py` and `tools/scene_field_v3.py` define all geometry, materials,
lighting, lenses, and periodic motion. The wrapper stores raw frames, denoised
frames, and scene fingerprints under `/tmp/nvxram-v3`. Open Image Denoise cleans
the rendered display RGB with its supported LDR/sRGB route; it does not create
the shadows or depth of field. Those are already in the path-traced frames.
FFmpeg packages a shared palette with subtle ordered dithering. Each animation
also has a full-color PNG poster.

The main loop uses 33 rendered poses with 64 timed output frames (3.2 seconds).
The macro loop uses 31 poses with 60 timed frames (3 seconds). A cosine-timed
back-and-forth sequence creates a deliberate ease at each end. Each output
image is copied from a native rendered pose: no optical-flow interpolation or
blending changes the shadows, reflections, or lens blur. GIF encoders may merge
repeated holds while retaining the full duration. `--pose-count` equal to
`--frame-count` instead renders and plays the complete native cycle.

If the complete frames from the current scene are already present, repackage
them without rerendering:

```bash
/tmp/nvxram-art-venv/bin/python tools/render_v3_assets.py --kind hero --package-only
/tmp/nvxram-art-venv/bin/python tools/render_v3_assets.py --kind field --package-only
```

Use `--resume` to continue an interrupted render with the same scene and
settings. Scene fingerprints prevent reusing frames after changes. Render again
without `--resume` after editing a scene. Update the tagline in both Markdown
profiles together and keep personal details out of image text, alt text, and
source when maintaining this minimal design.

## Publish

Commit and push the files to the default branch of the public profile repository
`nvxraM/nvxraM`. The root `README.md` appears on the profile. GitHub may cache
updated image files briefly. Rendering scripts do not publish anything.
