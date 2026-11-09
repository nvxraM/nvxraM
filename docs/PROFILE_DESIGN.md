# Version 6.2 · PELAGIC realism

[Design history](DESIGN_HISTORY.md) compares the current scene with every
verifiable earlier design. [PROFILE_STATIC.md](PROFILE_STATIC.md) shows the
reduced-motion still; [VERSIONS.md](VERSIONS.md) indexes the preserved versions.

The profile keeps one integrated underwater composition: nvxraM is physical
bas-relief on a partly buried stone relic, with a translucent jellyfish,
folded inner tissue, trailing tentacles, distant marine life and suspended
particles. The camera, carved lettering and existing organism geometry are
retained. Materials, lights and a bounded region of distant water change the
appearance without replacing that identity.

The bell uses restrained coat and emission, higher transmission, subtle
subsurface scattering, fine normal variation and linked surface roughness.
Its inner tissue is visible through the membrane. Canals and tentacles retain
the cyan character with less self-lighting. The stone and lettering share
world-space mineral color and layered surface relief, variable roughness and
a low coat weight. Their contact shadows and bevels remain actual geometry.

A broader, less saturated cyan key and weaker violet/warm fills give surfaces
more natural variation. The lettering-only rim preserves readability.
Scattering and absorption are confined to water behind the foreground, so
the distant organism recedes while the handle stays clear. The static 85 mm
camera retains optical depth of field. Geometry and materials are procedural;
no downloaded artwork, textures or private biographical details are used.

## Media

The versioned outputs are `assets/panel-v6.2.png`, `.webp` and `.gif`, all
1600 × 900. The PNG is the first rendered pose. Animated WebP preserves
full-color gradients; the GIF is a compatible fallback. The root README pins
all three paths to the same immutable asset commit and visibly links the
history page. Browsers requesting reduced motion receive the PNG.

The loop uses 60 native poses at 50 milliseconds per pose, for three seconds.
No estimated frames, optical-flow interpolation or frame blending is used.
WebP is encoded at quality 90; GIF uses a shared 96-color palette and ordered
Bayer dithering. The previous `panel-v6` files remain preserved alongside the
new version, and older designs are linked through immutable Git commits.

## Regenerate

Install Blender 5.2.3 LTS, FFmpeg and Python 3.12+, then install the pinned
`tools/requirements.txt` in a project virtual environment. DejaVu Sans must be
available at `/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf`, or passed with
`--font`. Ensure the Blender and FFmpeg executables are on the command PATH.
The Ubuntu checkout already has the software and `.venv`; its local environment
can be loaded with `source .local/environment.sh`.

From the checkout root:

```bash
.venv/bin/python tools/render_v6_assets.py --stem panel-v6.2 --samples 96 --frame-count 60 --threads 4 --backend CUDA --device "NVIDIA GeForce RTX 4090" --denoiser builtin --debug-cycles
.venv/bin/python tools/check_profile.py --report .local/media-validation.json
```

Blender's bundled Open Image Denoise 2.5.0 denoises the linear render with
surface guides on the CPU before each PNG is saved. CUDA performs path tracing;
four CPU support threads handle scene preparation and denoising. This route
needs no separate denoiser download or second denoising pass. The optional
`--denoiser external` route retains the pinned OIDN 2.5.1 CPU tool and its
SHA-256 verification for users who deliberately choose it.

Raw output, packaging input, temporary files and resume fingerprints default
to `.local/render-v6.2`; optional external tools are cached in `.local/tools`.
Final assets default to this checkout's `assets` directory independently of
the caller's directory. `--work-dir`, `--output-dir` and `--stem` allow explicit
alternatives. Use a new visual tag and versioned asset stem for each published
visual change.

### Devices and safe reuse

`--backend CUDA` is the default. `--device` accepts an exact GPU name or Cycles
ID; otherwise exactly one GPU must be available. The selector enables that
GPU and prints `CYCLES_DEVICE_SELECTION`. Device preflight runs before existing
frames can be cleared or optional tools downloaded. `--backend CPU` without
`--device` selects the explicit CPU fallback. There is no automatic fallback.
`--backend OPTIX` remains available for environments with a supported runtime;
this work uses CUDA and makes no driver or system-library changes.

`--resume` verifies the scene, font bytes, sample settings, device selector,
requested backend, resolved GPU ID and denoiser before reusing complete PNGs.
Changing these inputs rejects reuse without deleting saved frames. Do not
substitute new fingerprints into older render manifests to force reuse.
`--package-only` verifies saved fingerprints and complete denoised inputs,
then repackages without requiring a GPU or downloading tools. Pass the same
sample, frame-count, backend, device and denoiser options as the original run.

## Measured representative frame

Two full-resolution first-pose renders of the selected scene were measured
on an RTX 4090 through CUDA, using Blender 5.2.3, adaptive sampling, built-in
CPU OIDN and four CPU support threads. Whole-process wall times, including
startup and scene preparation, were **8.164 seconds at 48 samples** and
**8.353 seconds at 96 samples**. The 96-sample ceiling was selected because
this measured cost remained close while allowing extra sampling where needed.
The images look similar at profile scale; no general performance gain or
CPU-versus-GPU speedup is claimed from these measurements.

## Completed animation run

The full run completed 60 native CUDA poses and packaging in **393.544 seconds**
(6 minutes 34 seconds), including startup, CPU denoising and encoding. Every
pose logged RTX 4090 CUDA path tracing. Three successful representative-frame
renders preceded this run; none of those measurements compares CPU and GPU
performance. A built-scene comparison preserved all 200 existing non-light
objects, camera settings and transforms; only the bounded distant-water
object was added.

The PNG is 1,161,060 bytes. The GIF is 7,785,269 bytes and WebP is 3,262,618
bytes; both encoded animations contain 60 frames over 3,000 milliseconds.
Poster and cross-format checks pass. Loop-seam mean absolute RGB error on
128 × 72 thumbnails is 0.000919 for GIF and 0.001360 for WebP, comparable to
adjacent-frame motion. These are measured checks, not a guarantee of
scientific physical accuracy or universal browser rendering.

## Validation

```bash
.venv/bin/python -m unittest discover -s tools -p 'test_*.py' -v
.venv/bin/python tools/check_profile.py --report .local/media-validation.json
```

Regression checks cover strict device selection, frame preservation, resume
fingerprints, output naming, denoiser choice, immutable README media paths and
visible history navigation. Media validation checks dimensions, actual encoded
frame counts, duration, looping, poster agreement, GIF/WebP playback agreement
and the loop seam relative to adjacent-frame motion. Numeric checks accompany
visual inspection of the full-size poster, lettering, bell and representative
animation poses; they do not prove scientific realism.

The history records eight earlier published designs with 16 still panels.
Every historical preview is pinned to its full commit hash and was verified
against the corresponding Git object. Initial untagged work and missing
unpublished experiments are identified explicitly rather than invented.
