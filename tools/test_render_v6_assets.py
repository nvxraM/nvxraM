"""Fast regression checks for safe reuse of expensive rendered frames."""

from pathlib import Path
import tempfile
import unittest

from PIL import Image

from render_v6_assets import complete_png, prepare_work, render_specification


class RenderReuseTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
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
                    self.specification(pose_count=30)]
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


if __name__ == '__main__':
    unittest.main()
