import importlib.util
import unittest
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

    def test_keeps_normal_path_rewriting(self):
        result = preview.html_urls('<head></head><a href="/portfolio">Projects</a><img src="/img/will.webp">')
        self.assertIn('href="/willchavez-site-preview/portfolio"', result)
        self.assertIn('src="/willchavez-site-preview/img/will.webp"', result)


if __name__ == '__main__':
    unittest.main()
