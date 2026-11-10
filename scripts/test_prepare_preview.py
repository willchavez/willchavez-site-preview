import importlib.util
import unittest
import tempfile
import json
from pathlib import Path

spec = importlib.util.spec_from_file_location('prepare_preview', Path(__file__).with_name('prepare-preview.py'))
preview = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preview)


class AnalyticsPreviewTests(unittest.TestCase):
    def test_removes_legacy_tag_and_init_only(self):
        html = '''<head><script async src="https://www.googletagmanager.com/gtag/js?id=G-RPXX4TMRSH"></script>
        <script>window.dataLayer=[]; function gtag(){dataLayer.push(arguments)}; gtag('config','G-RPXX4TMRSH');</script>
        <script>window.applicationStillWorks = true;</script></head>'''
        result = preview.html_urls(html)
        self.assertNotIn('googletagmanager', result)
        self.assertNotIn("gtag('config'", result)
        self.assertIn('window.applicationStillWorks', result)
        self.assertIn('noindex, nofollow', result)

    def test_preserves_module_with_production_host_guard(self):
        module = '<script type="module">function gtag(){}; gtag("config", "G-test");</script>'
        self.assertIn(module, preview.remove_legacy_analytics(module))

    def test_rewrites_animation_lookup_and_video_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            mapping = {"/portfolio-media/w/1600/project/demo.webp": "/animation-media/abc.mp4"}
            (root / "animation-media.json").write_text(json.dumps(mapping))
            (root / "viewer.js").write_text('fetch("/animation-media.json")')
            preview.main(root)
            result = json.loads((root / "animation-media.json").read_text())
            self.assertEqual(result, {preview.BASE + key: preview.BASE + value for key, value in mapping.items()})
            self.assertIn('fetch("/willchavez-site-preview/animation-media.json")', (root / "viewer.js").read_text())
            preview.main(root)
            self.assertEqual(result, json.loads((root / "animation-media.json").read_text()))

    def test_keeps_normal_path_rewriting(self):
        result = preview.html_urls('<head></head><a href="/portfolio">Projects</a><img src="/img/will.webp">')
        self.assertIn('href="/willchavez-site-preview/portfolio"', result)
        self.assertIn('src="/willchavez-site-preview/img/will.webp"', result)


if __name__ == '__main__':
    unittest.main()
