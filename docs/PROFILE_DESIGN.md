# Profile maintenance

The profile uses only a handle, a short tagline, and two original abstract
animations. The static version is in [PROFILE_STATIC.md](PROFILE_STATIC.md).

Both illustrations are 1600 pixels wide. GIFs provide animation on GitHub
without scripts or external services. PNG posters are selected by browsers
requesting reduced motion and used by the separate static page. Each image has
descriptive alt text. The dark canvas also works against GitHub's light theme.

## Regenerate

The committed images are ready to use. Regeneration is optional and requires
Python 3.11+, Pillow, NumPy, and the DejaVu Sans system font at
`/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf`.

Use the existing checkout; no Git worktree is needed. From its root:

```bash
python -m venv /tmp/nvxram-art-venv
/tmp/nvxram-art-venv/bin/python -m pip install -r tools/requirements.txt
/tmp/nvxram-art-venv/bin/python tools/render_hero.py --output-dir assets
/tmp/nvxram-art-venv/bin/python tools/render_ribbon.py --output-dir assets
/tmp/nvxram-art-venv/bin/python tools/check_profile.py
```

The renderers are deterministic and use a shared palette per GIF to avoid color
flicker. Each writes a GIF and a still PNG. Update the tagline in both Markdown
profiles together. Keep personal details out of image text, alt text, and source
when maintaining this minimal design.

## Publish

Commit and push the files to the default branch of the public profile repository
`nvxraM/nvxraM`. The root `README.md` appears on the profile. GitHub may cache
updated image files briefly. Rendering scripts do not publish anything.
