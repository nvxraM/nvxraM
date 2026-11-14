"""Check publication pins and media agreement using small synthetic fixtures."""

from contextlib import redirect_stdout
from io import StringIO
import math
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from PIL import Image

import check_profile as checker


class ProfileValidationTests(unittest.TestCase):
    def setUp(self):
        temporary_root = checker.ROOT / '.local' / 'tmp'
        temporary_root.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=temporary_root)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.patch = mock.patch.object(checker, 'ROOT', self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        checker.ERRORS.clear()
        self.addCleanup(checker.ERRORS.clear)
        (self.root / 'docs').mkdir()
        (self.root / 'assets').mkdir()
        (self.root / 'docs' / 'DESIGN_HISTORY.md').write_text('Verified history')

    def check_page(self, source, path='README.md'):
        target = self.root / path
        target.write_text(source)
        with redirect_stdout(StringIO()):
            checker.check_markdown(target)
        return checker.ERRORS

    @staticmethod
    def readme(commit='a' * 40, stem='panel-v6.2', navigation=True):
        base = checker.RAW_REPOSITORY + commit + '/assets/' + stem
        source = ('<p><picture>'
                  f'<source media="(prefers-reduced-motion: reduce)" srcset="{base}.png" />'
                  f'<source type="image/webp" srcset="{base}.webp" />'
                  f'<img src="{base}.gif" alt="nvxraM carved underwater relic" />'
                  '</picture></p>')
        if navigation:
            source += '\n[Design history](docs/DESIGN_HISTORY.md)\n'
        return source

    def test_current_pinned_formats_allow_visible_history_navigation(self):
        self.assertEqual(self.check_page(self.readme()), [])

    def test_webp_before_reduced_motion_source_is_rejected(self):
        source = self.readme()
        start = source.index('<source')
        end = source.index('<img')
        sources = source[start:end].split('/>')
        swapped = source[:start] + sources[1] + '/>' + sources[0] + '/>' + source[end:]
        self.assertTrue(any('picture ordered' in error for error in self.check_page(swapped)))

    def test_sources_outside_picture_are_rejected(self):
        source = self.readme().replace('<picture>', '').replace('</picture>', '')
        self.assertTrue(any('picture ordered' in error for error in self.check_page(source)))

    def test_sources_in_separate_pictures_are_rejected(self):
        source = self.readme().replace('<img', '</picture><picture><img')
        self.assertTrue(any('picture ordered' in error for error in self.check_page(source)))

    def test_extra_preceding_source_is_rejected(self):
        source = self.readme().replace('<picture>', '<picture><source srcset="animation.gif" />')
        self.assertTrue(any('picture ordered' in error for error in self.check_page(source)))

    def test_reduced_motion_source_with_incompatible_type_is_rejected(self):
        source = self.readme().replace('<source media=', '<source type="image/webp" media=')
        self.assertTrue(any('picture ordered' in error for error in self.check_page(source)))

    def test_explicit_png_type_on_reduced_motion_source_is_allowed(self):
        source = self.readme().replace('<source media=', '<source type="image/png" media=')
        self.assertEqual(self.check_page(source), [])

    def test_mutable_main_and_tag_media_refs_are_rejected(self):
        for ref in ['main', 'v6.2']:
            with self.subTest(ref=ref):
                checker.ERRORS.clear()
                errors = self.check_page(self.readme(commit=ref))
                self.assertTrue(any('immutable' in error for error in errors))

    def test_old_asset_filenames_are_rejected_even_at_an_immutable_commit(self):
        errors = self.check_page(self.readme(stem='panel-v6'))
        self.assertTrue(any('newest artwork' in error for error in errors))

    def test_all_three_formats_must_use_one_asset_commit(self):
        source = self.readme().replace('a' * 40 + '/assets/panel-v6.2.webp',
                                       'b' * 40 + '/assets/panel-v6.2.webp')
        self.assertTrue(any('same immutable commit' in error for error in self.check_page(source)))

    def test_history_navigation_must_be_present_and_visible(self):
        source = self.readme(navigation=False) + '<a href="docs/DESIGN_HISTORY.md"></a>'
        self.assertTrue(any('visible design-history' in error for error in self.check_page(source)))

    def test_historical_raw_previews_must_also_use_immutable_commits(self):
        source = '<img src="' + checker.RAW_REPOSITORY + 'v1/assets/hero.png" alt="Orbital sculpture" />'
        errors = self.check_page(source, 'docs/DESIGN_HISTORY.md')
        self.assertTrue(any('full commit SHA' in error for error in errors))

    def test_static_page_must_use_current_png(self):
        for stem, expected_valid in [('panel-v6.2', True), ('panel-v6', False)]:
            with self.subTest(stem=stem):
                checker.ERRORS.clear()
                (self.root / 'assets' / f'{stem}.png').write_bytes(b'link fixture')
                source = f'<p><img src="../assets/{stem}.png" alt="nvxraM underwater relic" /></p>'
                errors = self.check_page(source, 'docs/PROFILE_STATIC.md')
                self.assertEqual(not errors, expected_valid)

    def media(self, *, different_webp=False, webp_duration=50, poster_color=None):
        colors = [round(20 + 60 * (.5 - .5 * math.cos(math.tau * index / 60)))
                  for index in range(60)]
        frames = [Image.new('RGB', (1600, 9), (value, value, value)) for value in colors]
        poster = frames[0] if poster_color is None else Image.new('RGB', (1600, 9), poster_color)
        poster.save(self.root / 'assets' / 'sample.png')
        frames[0].save(self.root / 'assets' / 'sample.gif', save_all=True,
                       append_images=frames[1:], duration=50, loop=0)
        other = ([Image.new('RGB', (1600, 9), (20, value, 20)) for value in colors]
                 if different_webp else frames)
        other[0].save(self.root / 'assets' / 'sample.webp', save_all=True,
                      append_images=other[1:], duration=webp_duration, loop=0,
                      lossless=True)
        for frame in frames + other:
            frame.close()
        if poster_color is not None:
            poster.close()

    def check_media(self):
        with redirect_stdout(StringIO()):
            return checker.check_media('sample', 9)

    def test_matching_media_reports_frame_counts_duration_and_image_error(self):
        self.media()
        report = self.check_media()
        self.assertEqual(checker.ERRORS, [])
        self.assertGreater(report['gif']['frame_count'], 1)
        self.assertEqual(report['gif']['duration_ms'], 3000)
        self.assertEqual(report['webp']['duration_ms'], 3000)
        self.assertEqual(report['max_cross_format_timeline_mae'], 0)
        self.assertLess(report['gif']['loop_seam_mae'], .005)

    def test_poster_mismatch_is_rejected(self):
        self.media(poster_color=(255, 255, 255))
        self.check_media()
        self.assertTrue(any('does not match the PNG poster' in error for error in checker.ERRORS))

    def test_divergent_gif_webp_playback_is_rejected(self):
        self.media(different_webp=True)
        self.check_media()
        self.assertTrue(any('GIF/WebP playback differs' in error for error in checker.ERRORS))

    def test_different_loop_durations_are_rejected(self):
        self.media(webp_duration=70)
        self.check_media()
        self.assertTrue(any('loop durations differ' in error for error in checker.ERRORS))

    def test_abrupt_loop_seam_is_rejected(self):
        frames = [Image.new('RGB', (1600, 9), (value,) * 3) for value in [0, 40, 80]]
        path = self.root / 'assets' / 'jump.gif'
        frames[0].save(path, save_all=True, append_images=frames[1:], duration=1000, loop=0)
        for frame in frames:
            frame.close()
        with redirect_stdout(StringIO()):
            checker.check_animation(path, 9)
        self.assertTrue(any('loop seam' in error for error in checker.ERRORS))


if __name__ == '__main__':
    unittest.main()
