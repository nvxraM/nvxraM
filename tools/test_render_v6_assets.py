"""Fast regression checks for safe reuse of expensive rendered frames."""

from pathlib import Path
import argparse
import json
import subprocess
import tempfile
import unittest
from unittest import mock

from PIL import Image

import render_v6_assets as renderer
from render_v6_assets import asset_stem, complete_png, preflight_cycles, prepare_work, render_specification


class RenderReuseTests(unittest.TestCase):
    def setUp(self):
        temporary_root = renderer.TOOLS.parent / '.local' / 'tmp'
        temporary_root.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=temporary_root)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.scene = self.root / 'scene.py'
        self.font = self.root / 'font.ttf'
        self.scene.write_text('scene v1')
        self.font.write_bytes(b'font v1')
        self.work = self.root / 'work'
        self.spec = self.specification()

    def specification(self, **changes):
        settings = dict(count=60, samples=48, kind='panel', font=self.font)
        settings.update(changes)
        return render_specification(self.scene, **settings)

    def test_matching_resume_preserves_frames(self):
        raw, clean = prepare_work(self.work, self.spec, False)
        for folder in (raw, clean):
            (folder / 'frame-0000.png').write_bytes(b'expensive frame')
        prepare_work(self.work, self.spec, True)
        for folder in (raw, clean):
            self.assertEqual((folder / 'frame-0000.png').read_bytes(), b'expensive frame')

    def test_changed_inputs_reject_resume_without_deleting_frames(self):
        raw, _ = prepare_work(self.work, self.spec, False)
        sentinel = raw / 'frame-0000.png'
        sentinel.write_bytes(b'expensive frame')
        variants = [self.specification(samples=49), self.specification(count=61),
                    self.specification(pose_count=30),
                    self.specification(backend='CPU'),
                    self.specification(device='another GPU'),
                    self.specification(resolved_device='another GPU ID'),
                    self.specification(denoiser='external')]
        self.scene.write_text('scene v2')
        variants.append(self.specification())
        self.scene.write_text('scene v1')
        self.font.write_bytes(b'font v2')
        variants.append(self.specification())
        for variant in variants:
            with self.subTest(spec=variant), self.assertRaises(SystemExit):
                prepare_work(self.work, variant, True)
            self.assertEqual(sentinel.read_bytes(), b'expensive frame')

    def test_refresh_removes_old_tail_but_preserves_unrelated_files(self):
        raw, clean = prepare_work(self.work, self.spec, False)
        for folder in (raw, clean):
            (folder / 'frame-0059.png').write_bytes(b'old tail')
            (folder / 'notes.txt').write_text('keep')
        prepare_work(self.work, self.specification(count=30), False)
        for folder in (raw, clean):
            self.assertFalse((folder / 'frame-0059.png').exists())
            self.assertEqual((folder / 'notes.txt').read_text(), 'keep')

    def test_unrecognized_frames_are_preserved_and_rejected(self):
        raw = self.work / 'raw'
        raw.mkdir(parents=True)
        frame = raw / 'frame-0000.png'
        frame.write_bytes(b'unowned')
        with self.assertRaises(SystemExit):
            prepare_work(self.work, self.spec, False)
        self.assertEqual(frame.read_bytes(), b'unowned')

    def test_foreign_manifest_is_preserved_and_rejected(self):
        self.work.mkdir()
        manifest = self.work / 'render.json'
        manifest.write_text('{"generator": "other"}')
        with self.assertRaises(SystemExit):
            prepare_work(self.work, self.spec, False)
        self.assertEqual(manifest.read_text(), '{"generator": "other"}')

    def test_resume_requires_manifest(self):
        with self.assertRaises(SystemExit):
            prepare_work(self.work, self.spec, True)

    def test_png_validation_rejects_missing_wrong_size_and_wrong_format(self):
        path = self.root / 'frame.png'
        self.assertFalse(complete_png(path, (16, 9)))
        Image.new('RGB', (16, 9)).save(path)
        self.assertTrue(complete_png(path, (16, 9)))
        self.assertFalse(complete_png(path, (1600, 900)))
        Image.new('RGB', (16, 9)).save(path, format='JPEG')
        self.assertFalse(complete_png(path, (16, 9)))

    def test_png_validation_rejects_truncated_data(self):
        path = self.root / 'frame.png'
        Image.new('RGB', (16, 9)).save(path)
        path.write_bytes(path.read_bytes()[:40])
        self.assertFalse(complete_png(path, (16, 9)))

    def test_failed_device_preflight_preserves_existing_frames_and_manifest(self):
        raw, clean = prepare_work(self.work, self.spec, False)
        for folder in (raw, clean):
            (folder / 'frame-0000.png').write_bytes(b'expensive frame')
        manifest_before = (self.work / 'render.json').read_bytes()
        argv = ['render_v6_assets.py', '--work-dir', str(self.work),
                '--font', str(self.font), '--backend', 'OPTIX']
        with mock.patch('sys.argv', argv), \
                mock.patch.object(renderer, 'preflight_cycles',
                                  side_effect=SystemExit('Unavailable OptiX')) as preflight, \
                mock.patch.object(renderer, 'prepare_work', wraps=prepare_work) as prepare, \
                mock.patch.object(renderer, 'ensure_oidn') as oidn:
            with self.assertRaisesRegex(SystemExit, 'Unavailable OptiX'):
                renderer.main()
        preflight.assert_called_once_with('OPTIX', None)
        prepare.assert_not_called()
        oidn.assert_not_called()
        self.assertEqual((self.work / 'render.json').read_bytes(), manifest_before)
        for folder in (raw, clean):
            self.assertEqual((folder / 'frame-0000.png').read_bytes(), b'expensive frame')

    def test_resolved_gpu_change_rejects_resume_and_preserves_frames(self):
        original = self.specification(resolved_device='CUDA_GPU_A')
        raw, _ = prepare_work(self.work, original, False)
        sentinel = raw / 'frame-0000.png'
        sentinel.write_bytes(b'expensive frame')
        with self.assertRaises(SystemExit):
            prepare_work(self.work, self.specification(resolved_device='CUDA_GPU_B'), True)
        self.assertEqual(sentinel.read_bytes(), b'expensive frame')

    def test_package_only_uses_saved_device_without_preflight_or_oidn(self):
        specification = render_specification(
            renderer.TOOLS / 'scene_v6.py', 1, 48, 'panel', 1, self.font,
            'CUDA', None, 'CUDA_saved_device')
        _, clean = prepare_work(self.work, specification, False)
        Image.new('RGB', (1600, 900), (64, 96, 128)).save(clean / 'frame-0000.png')
        argv = ['render_v6_assets.py', '--work-dir', str(self.work),
                '--font', str(self.font), '--frame-count', '1', '--package-only']
        with mock.patch('sys.argv', argv), \
                mock.patch.object(renderer, 'preflight_cycles') as preflight, \
                mock.patch.object(renderer, 'ensure_oidn') as oidn, \
                mock.patch.object(renderer, 'package') as package:
            renderer.main()
        preflight.assert_not_called()
        oidn.assert_not_called()
        self.assertEqual(package.call_args.args[1], renderer.TOOLS.parent / 'assets')
        self.assertEqual(package.call_args.args[2], 'panel-v6.2')
        self.assertTrue((clean / 'frame-0000.png').is_file())

    def test_output_stem_cannot_escape_the_output_directory(self):
        self.assertEqual(asset_stem('panel-v6.2'), 'panel-v6.2')
        for value in ['../README', '/tmp/output', 'nested/panel', '', '..', '.']:
            with self.subTest(stem=value), self.assertRaises(argparse.ArgumentTypeError):
                asset_stem(value)

    def test_builtin_denoiser_reuses_saved_png_without_download_or_second_pass(self):
        selection = {'backend': 'CUDA', 'scene_device': 'GPU',
                     'devices': [{'name': 'RTX test', 'id': 'CUDA_test', 'type': 'CUDA'}]}
        specification = render_specification(
            renderer.TOOLS / 'scene_v6.py', 1, 48, 'panel', 1, self.font,
            'CUDA', None, 'CUDA_test', 'builtin')
        raw, clean = prepare_work(self.work, specification, False)
        source = raw / 'frame-0000.png'
        Image.new('RGB', (1600, 900), (64, 96, 128)).save(source)
        argv = ['render_v6_assets.py', '--work-dir', str(self.work),
                '--font', str(self.font), '--frame-count', '1', '--resume']
        with mock.patch('sys.argv', argv), \
                mock.patch.object(renderer, 'preflight_cycles', return_value=selection), \
                mock.patch.object(renderer, 'ensure_oidn') as oidn, \
                mock.patch.object(renderer, 'denoise_png') as denoise, \
                mock.patch.object(renderer, 'package'):
            renderer.main()
        oidn.assert_not_called()
        denoise.assert_not_called()
        self.assertEqual(source.read_bytes(), (clean / 'frame-0000.png').read_bytes())

    def test_preflight_invokes_only_selector_with_scoped_temporary_directory(self):
        selection = {'backend': 'CUDA', 'scene_device': 'GPU',
                     'devices': [{'name': 'RTX test', 'id': 'CUDA_test', 'type': 'CUDA'}]}
        completed = subprocess.CompletedProcess(
            [], 0, 'Some Blender startup output\nCYCLES_DEVICE_SELECTION=' +
            json.dumps(selection) + '\n', '')
        with mock.patch.object(renderer.subprocess, 'run', return_value=completed) as run:
            self.assertEqual(preflight_cycles('CUDA', 'RTX test'), selection)
        command = run.call_args.args[0]
        self.assertEqual(command[command.index('--python') + 1],
                         str(renderer.TOOLS / 'cycles_devices.py'))
        self.assertEqual(command[command.index('--backend') + 1], 'CUDA')
        self.assertEqual(command[command.index('--device') + 1], 'RTX test')
        self.assertNotIn('--render-frame', command)
        env = run.call_args.kwargs['env']
        self.assertTrue(Path(env['TMPDIR']).is_relative_to(renderer.TOOLS.parent / '.local'))
        self.assertEqual(env['BLENDER_TMPDIR'], env['TMPDIR'])
        self.assertFalse(Path(env['TMPDIR']).exists())

    def test_preflight_rejects_cpu_fallback_for_requested_gpu(self):
        fallback = {'backend': 'CPU', 'scene_device': 'CPU',
                    'devices': [{'name': 'CPU', 'type': 'CPU'}]}
        completed = subprocess.CompletedProcess(
            [], 0, 'CYCLES_DEVICE_SELECTION=' + json.dumps(fallback) + '\n', '')
        with mock.patch.object(renderer.subprocess, 'run', return_value=completed):
            with self.assertRaisesRegex(SystemExit, 'Invalid Cycles preflight'):
                preflight_cycles('CUDA')


if __name__ == '__main__':
    unittest.main()
