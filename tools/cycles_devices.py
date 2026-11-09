"""Select a Cycles backend explicitly, without silently falling back to CPU."""

from __future__ import annotations

import json


BACKENDS = ('CPU', 'CUDA', 'OPTIX')


def configure_cycles(scene, backend: str = 'CUDA', device: str | None = None,
                     *, bpy_module=None) -> dict:
    """Configure one GPU, or the explicit CPU fallback, for this process only."""
    if backend not in BACKENDS:
        raise ValueError(f'Unsupported Cycles backend: {backend}')
    if backend == 'CPU' and device:
        raise ValueError('--device selects a GPU; omit it with --backend CPU.')
    scene.render.engine = 'CYCLES'
    if backend == 'CPU':
        scene.cycles.device = 'CPU'
        result = {'backend': 'CPU', 'scene_device': 'CPU',
                  'devices': [{'name': 'CPU', 'type': 'CPU'}]}
    else:
        if bpy_module is None:
            import bpy as bpy_module
        preferences = bpy_module.context.preferences.addons['cycles'].preferences
        try:
            preferences.compute_device_type = backend
            available = list(preferences.get_devices_for_type(backend))
        except (TypeError, ValueError, RuntimeError) as error:
            raise RuntimeError(
                f'Cycles {backend} initialization failed. Select --backend CPU '
                'for an explicit CPU run; no automatic fallback was performed.'
            ) from error
        candidates = [item for item in available if item.type == backend]
        if device:
            candidates = [item for item in candidates
                          if device in (item.name, item.id)]
        if len(candidates) != 1:
            names = [item.name for item in available if item.type == backend]
            raise RuntimeError(
                f'Expected one {backend} GPU matching {device!r}; found '
                f'{len(candidates)}. Available GPUs: {names}. Pass an exact '
                '--device name/ID, or --backend CPU. No render was started.'
            )
        selected = candidates[0]
        # Disable CPU and other GPUs, including entries left by earlier probes.
        for item in preferences.devices:
            item.use = item.type == backend and item.id == selected.id
        scene.cycles.device = 'GPU'
        result = {'backend': backend, 'scene_device': 'GPU',
                  'devices': [{'name': selected.name, 'id': selected.id,
                               'type': selected.type}]}
    print('CYCLES_DEVICE_SELECTION=' + json.dumps(result, sort_keys=True), flush=True)
    return result


def main():
    """Allow the wrapper to validate a backend before touching saved frames."""
    import argparse
    import sys
    import bpy

    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend', choices=BACKENDS, default='CUDA')
    parser.add_argument('--device')
    args = parser.parse_args(argv)
    configure_cycles(bpy.context.scene, args.backend, args.device)


if __name__ == '__main__':
    main()
