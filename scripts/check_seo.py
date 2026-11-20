#!/usr/bin/env python3
"""Validate the static SEO contract for the Quiet Accident website."""

from __future__ import annotations

import argparse
import runpy
import json
import re
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PAGES = [
    ROOT / "index.html",
    ROOT / "about/index.html",
    ROOT / "releases/index.html",
    *sorted((ROOT / "releases").glob("*/index.html")),
    *sorted((ROOT / "ua").rglob("index.html")),
]
REQUIRED_META = {
    "description",
    "robots",
    "twitter:card",
    "twitter:title",
    "twitter:description",
    "twitter:image",
    "twitter:image:alt",
}
REQUIRED_OG = {
    "og:type",
    "og:locale",
    "og:site_name",
    "og:title",
    "og:description",
    "og:image",
    "og:image:alt",
    "og:image:type",
    "og:image:width",
    "og:image:height",
}


class Document(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_title = False
        self.title = ""
        self.h1 = 0
        self.meta = {}
        self.og = {}
        self.images = []
        self.canonical = None

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "title":
            self.in_title = True
        elif tag == "h1":
            self.h1 += 1
        elif tag == "meta":
            if values.get("name"):
                self.meta[values["name"]] = values.get("content", "")
            if values.get("property"):
                self.og[values["property"]] = values.get("content", "")
        elif tag == "link" and values.get("rel") == "canonical":
            self.canonical = values.get("href")
        elif tag == "img":
            self.images.append(values)

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title += data


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    "--production",
    action="store_true",
    help="Require canonical, og:url, sitemap and absolute social images",
)
args = parser.parse_args()
errors = []
titles = {}
descriptions = {}

for page in PAGES:
    relative = page.relative_to(ROOT).as_posix()
    source = page.read_text()
    document = Document()
    document.feed(source)
    title = document.title.strip()
    description = document.meta.get("description", "").strip()

    if not title:
        errors.append(f"{relative}: missing title")
    if not 70 <= len(description) <= 170:
        errors.append(f"{relative}: description length is {len(description)}")
    if document.h1 != 1:
        errors.append(f"{relative}: expected one h1, found {document.h1}")
    for key in REQUIRED_META - document.meta.keys():
        errors.append(f"{relative}: missing meta name={key}")
    for key in REQUIRED_OG - document.og.keys():
        errors.append(f"{relative}: missing meta property={key}")
    if document.meta.get("robots") != "index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1":
        errors.append(f"{relative}: unexpected robots directive")
    for image in document.images:
        if "alt" not in image or "width" not in image or "height" not in image:
            errors.append(f"{relative}: image is missing alt or dimensions: {image.get('src', '')}")
    scripts = re.findall(r'<script type="application/ld\+json">(.*?)</script>', source, flags=re.S)
    if len(scripts) != 1:
        errors.append(f"{relative}: expected one JSON-LD block, found {len(scripts)}")
    else:
        try:
            json.loads(scripts[0])
        except json.JSONDecodeError as exc:
            errors.append(f"{relative}: invalid JSON-LD: {exc}")
    if args.production:
        if not document.canonical or not document.canonical.startswith("https://"):
            errors.append(f"{relative}: missing absolute canonical")
        if not document.og.get("og:url", "").startswith("https://"):
            errors.append(f"{relative}: missing absolute og:url")
        if not document.og.get("og:image", "").startswith("https://"):
            errors.append(f"{relative}: og:image is not absolute")
        is_uk = relative.startswith("ua/")
        expected_lang = "uk" if is_uk else "en"
        if f'<html lang="{expected_lang}">' not in source:
            errors.append(f"{relative}: incorrect document language")
        english_path = relative.removeprefix("ua/").removesuffix("index.html")
        for lang, prefix in (("en", ""), ("uk", "ua/"), ("x-default", "")):
            alternate = f'<link rel="alternate" hreflang="{lang}" href="https://quietaccident.com/{prefix}{english_path}">'
            if alternate not in source:
                errors.append(f"{relative}: missing alternate language {lang}")
        expected_canonical = f'https://quietaccident.com/{"ua/" if is_uk else ""}{english_path}'
        if document.canonical != expected_canonical:
            errors.append(f"{relative}: canonical points to the wrong language version")
        if source.count('class="language-switch"') != 1:
            errors.append(f"{relative}: expected one language switcher")
    titles.setdefault(title, []).append(relative)
    descriptions.setdefault(description, []).append(relative)

for value, paths in titles.items():
    if len(paths) > 1:
        errors.append(f"duplicate title on: {', '.join(paths)}")
for value, paths in descriptions.items():
    if len(paths) > 1:
        errors.append(f"duplicate description on: {', '.join(paths)}")

catalogue = []
for release_page in (ROOT / "releases").glob("*/index.html"):
    block = re.search(r'<script type="application/ld\+json">(.*?)</script>', release_page.read_text(), re.S)
    if block:
        graph = json.loads(block[1])["@graph"]
        recording = next(node for node in graph if node.get("@type") == "MusicRecording")
        catalogue.append((recording["datePublished"], release_page.parent.name))
catalogue.sort(reverse=True)
for prefix in ("", "ua/"):
    for relative_path, expected in (("index.html", catalogue[1:4]), ("releases/index.html", catalogue)):
        path = ROOT / prefix / relative_path
        source = path.read_text()
        cards = re.findall(r'<a class="release-card" href="([^"]+)"', source)
        expected_urls = [f'/{prefix}releases/{slug}/' for _, slug in expected]
        if cards != expected_urls:
            errors.append(f"{path.relative_to(ROOT)}: incorrect crawlable catalogue cards")

if args.production:
    sitemap = ROOT / "sitemap.xml"
    robots = ROOT / "robots.txt"
    if not sitemap.is_file() or "<urlset" not in sitemap.read_text():
        errors.append("missing sitemap.xml")
    if not robots.is_file() or "Sitemap: https://" not in robots.read_text():
        errors.append("robots.txt does not reference the production sitemap")

if errors:
    raise SystemExit("SEO validation failed:\n- " + "\n- ".join(errors))
if args.production:
    runpy.run_path(str(ROOT / 'scripts/check_crawl.py'), run_name='__main__')
print(f"SEO validation passed for {len(PAGES)} pages" + (" in production mode." if args.production else "."))
