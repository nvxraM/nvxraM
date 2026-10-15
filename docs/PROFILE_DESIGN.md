# Profile design & maintenance

This is the special profile repository for [@nvxraM](https://github.com/nvxraM).
GitHub displays the root `README.md` on the profile when this repository is
public and the file is on its default branch.

## Design

A dark background, quiet teal and lavender accents, and original scientific
illustrations connect genomics and software. The header, workflow, Hi-C
comparison, and terminal are animated GIFs. Their PNG counterparts power the
[static profile](PROFILE_STATIC.md).

All assets are **1600 pixels wide**, so they stay crisp at typical GitHub profile
widths and on high-density displays. The diagrams are synthetic illustrations,
not experimental results. The Hi-C comparison uses a single synthetic matrix
with different fragment orderings.

GitHub removes scripts and inline styles from READMEs. Animation is baked into
the GIFs, so no JavaScript, external animation service, API token, scheduled
workflow, or live server is needed. The profile also works in GitHub's light
theme: each illustration has its own dark canvas. Images include descriptive
alt text. Browsers requesting reduced motion receive the PNG posters through
`<picture>` sources; the first link also opens a version without animated images.

The name follows the public GitHub profile. The interests follow the supplied
brief; no institution, job title, skill certification, or research achievement
is implied. Edit the copy in both profile Markdown files when your bio changes.

## Publish

1. Review `README.md` and `docs/PROFILE_STATIC.md`.
2. Commit and push these files, including `assets/`, to `nvxraM/nvxraM`.
3. Ensure the repository is public and `README.md` is on its default branch.
4. Visit [your profile](https://github.com/nvxraM) to see the result. GitHub may
   cache images briefly after an update.

No push or publication is performed by the local rendering scripts.

## Regenerate the assets

The committed images are ready to use. Regeneration is optional. Use the
existing checkout; there is no need to create a Git worktree.

Requirements: Python 3.11+, Pillow, NumPy, and DejaVu Sans/DejaVu Sans Mono
fonts. The scripts use the system fonts at
`/usr/share/fonts/truetype/dejavu/` and deterministic drawing instructions.

From the repository root:

```bash
python -m venv /tmp/nvxram-art-venv
/tmp/nvxram-art-venv/bin/python -m pip install -r tools/requirements.txt
/tmp/nvxram-art-venv/bin/python tools/render_hero.py --output-dir assets
/tmp/nvxram-art-venv/bin/python tools/render_workflow.py --output-dir assets
/tmp/nvxram-art-venv/bin/python tools/render_contact_map.py --output-dir assets
/tmp/nvxram-art-venv/bin/python tools/render_terminal.py --output-dir assets
```

Each script writes its own GIF and PNG. The GIFs loop and share a stable color
palette across their frames to avoid color flicker. Keep individual images below
10 MB, and prefer fewer frames over reducing image dimensions if size grows.

To change the hero name, tagline, colors, or illustration, edit
`tools/render_hero.py` and rerun it. The other renderers control their respective
illustrations. The generated PNGs remain the static alternatives.

## Verification

```bash
python tools/check_profile.py
```

This checks local Markdown links, alt text, image dimensions, animation frames,
loop settings, size, and that static-profile images are still images. It checks
the authored content and media; it cannot establish that the files have been
pushed or that GitHub's profile cache has refreshed.

GitHub's [profile README documentation](https://docs.github.com/en/account-and-profile/how-tos/profile-customization/managing-your-profile-readme)
explains the publication requirements.
