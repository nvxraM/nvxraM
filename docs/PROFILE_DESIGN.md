# Version 2 · profile maintenance

The profile keeps only the handle, the existing short tagline, and two original
animations. Its footer links stay removed. The static version is in
[PROFILE_STATIC.md](PROFILE_STATIC.md); [VERSIONS.md](VERSIONS.md) records the
saved version 1.

The main artwork is a procedural 3D sculpture: a folded, pearlescent membrane
surrounds a luminous molecular strand, with an orbital halo and drifting beads.
The smaller animation uses translucent cell-like particles and a traveling
pulse. These forms connect biology and computation through the artwork without
adding a written biography.

Both illustrations are 1600 pixels wide. GIFs provide animation on GitHub
without scripts or external services. PNG posters are selected by browsers
requesting reduced motion and used by the separate static page. Each image has
descriptive alt text. The dark canvas also works against GitHub's light theme.

## Regenerate

The committed images are ready to use. Regeneration is optional and requires
Blender 4.3.2, FFmpeg, Python 3.11+, Pillow, NumPy, and the DejaVu Sans system font at
`/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf`. The main scene uses Blender's
Eevee renderer. CPU rendering takes several minutes; opening the profile needs
no Blender installation or running service.

Use the existing checkout; no Git worktree is needed. From its root:

```bash
python -m venv /tmp/nvxram-art-venv
/tmp/nvxram-art-venv/bin/python -m pip install -r tools/requirements.txt
/tmp/nvxram-art-venv/bin/python tools/render_v2_hero.py --output-dir assets --samples 8 --threads 4
/tmp/nvxram-art-venv/bin/python tools/render_field_v2.py --output-dir assets
/tmp/nvxram-art-venv/bin/python tools/check_profile.py
```

The main renderer writes its intermediate frames and shader caches under `/tmp`.
`tools/scene_v2.py` defines its geometry, lighting, materials, and periodic motion.
`tools/render_field_v2.py` draws the particle field directly. Both animations use
a shared palette across frames to avoid color flicker and have still PNG
posters. The hero also uses ordered dithering to preserve its smooth surface
gradients within the GIF palette. Update the tagline in both Markdown profiles
together.

If the complete frames from the current scene are already present, repackage
them without rerendering:

```bash
/tmp/nvxram-art-venv/bin/python tools/render_v2_hero.py --package-only --output-dir assets
```

Render again after changing the scene. Keep personal details out of image text,
alt text, and source when maintaining this minimal design.

## Publish

Commit and push the files to the default branch of the public profile repository
`nvxraM/nvxraM`. The root `README.md` appears on the profile. GitHub may cache
updated image files briefly. Rendering scripts do not publish anything.
