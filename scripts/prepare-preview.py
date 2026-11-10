"""Adapt built static output to this repository's GitHub Pages subpath.

Production source and canonical URLs remain unchanged. Run on fresh build output.
"""
import re
import json
import sys
from pathlib import Path

BASE = "/willchavez-site-preview"


def prefix(url):
    if url.startswith("/") and not url.startswith(("//", BASE + "/")):
        return BASE + url
    return url


def css_urls(text):
    return re.sub(r"(url\(\s*['\"]?)(/[^\s)'\"]*)",
                  lambda m: m[1] + prefix(m[2]), text, flags=re.I)


def remove_legacy_analytics(text):
    """Old copied pages retain classic GA snippets; preview must not collect."""
    def script(match):
        attrs, body = match.group(1), match.group(2)
        # Modern module scripts perform their own production-host check and may
        # share application code. Never strip those modules.
        if re.search(r"\btype\s*=\s*['\"]module['\"]", attrs, re.I):
            return match.group(0)
        if re.search(r"\bsrc\s*=\s*['\"]https://www\.googletagmanager\.com/gtag/js", attrs, re.I):
            return ''
        if re.search(r"function\s+gtag\s*\(", body) and re.search(r"gtag\s*\(\s*['\"]config['\"]", body):
            return ''
        return match.group(0)
    return re.sub(r'<script\b([^>]*)>(.*?)</script\s*>', script, text, flags=re.I | re.S)


def html_urls(text):
    text = remove_legacy_analytics(text)
    def attribute(m):
        value = m[3]
        if m[1].strip().lower().startswith("srcset"):
            value = re.sub(r"(^|,\s*)(/\S+)", lambda s: s[1] + prefix(s[2]), value)
        else:
            value = prefix(value)
        return m[1] + m[2] + value + m[2]

    text = re.sub(r"(\b(?:href|src|srcset|poster|action)\s*=\s*)(['\"])(.*?)\2",
                  attribute, text, flags=re.I | re.S)
    text = re.sub(r'<meta\b[^>]*name=["\']robots["\'][^>]*>', '', text, flags=re.I)
    return re.sub(r"</head>", '<meta name="robots" content="noindex, nofollow"></head>',
                  css_urls(text), flags=re.I)


def main(root):
    # Only rewrite JavaScript string paths that identify files/routes in this build.
    names = {p.name for p in root.iterdir()}
    names.update(p.stem for p in root.glob("*.html"))
    paths = "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True))
    js_path = re.compile(r"(['\"`])(/(?:" + paths + r")(?=[/'\"`?#]))")
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in {".html", ".css", ".js", ".mjs"}:
            continue
        text = path.read_text()
        if path.suffix == ".html":
            text = html_urls(text)
        elif path.suffix == ".css":
            text = css_urls(text)
        if path.suffix in {".html", ".js", ".mjs"}:
            text = js_path.sub(lambda m: m[1] + prefix(m[2]), text)
        path.write_text(text)
    # The viewer looks up the prefixed image URL in this map and fetches its
    # video from the same project Pages base path.
    manifest = root / "animation-media.json"
    if manifest.exists():
        mapping = json.loads(manifest.read_text())
        manifest.write_text(json.dumps({prefix(key): prefix(value) for key, value in mapping.items()}))
    (root / "CNAME").unlink(missing_ok=True)
    (root / ".nojekyll").touch()


if __name__ == "__main__":
    main(Path(sys.argv[1]))
