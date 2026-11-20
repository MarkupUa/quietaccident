#!/usr/bin/env python3
"""Check crawlable facts, stable entity identifiers and the optional AI index."""
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
ARTIST = "https://quietaccident.com/#artist"
WEBSITE = "https://quietaccident.com/#website"
catalogue_source = (ROOT / "assets/js/releases.js").read_text()
catalogue = json.loads(re.search(r'window\.QA_RELEASES\s*=\s*(\[.*\]);', catalogue_source, re.S)[1])
translations = json.loads((ROOT / "assets/i18n/uk.json").read_text())
for release in catalogue:
    assert release.get("descriptionUk") == translations[release["description"]], release["slug"]
APPROVED_PRESAVES = {}

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = set()
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and attrs.get("href"):
            self.urls.add(attrs["href"])

robots = RobotFileParser()
robots.parse((ROOT / "robots.txt").read_text().splitlines())
pages = [ROOT / "index.html", ROOT / "about/index.html", ROOT / "releases/index.html", *sorted((ROOT / "releases").glob("*/index.html")), *sorted((ROOT / "ua").rglob("index.html"))]
for page in pages:
    relative = page.relative_to(ROOT).as_posix()
    source = page.read_text()
    data = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', source, re.S)[1])
    graph = data["@graph"]
    artist = next(node for node in graph if node["@type"] == "MusicGroup")
    assert artist["@id"] == ARTIST, relative
    assert any(node.get("@id") == WEBSITE for node in graph), relative
    webpage = next(node for node in graph if node["@type"] in ("WebPage", "AboutPage", "CollectionPage"))
    assert webpage["about"]["@id"] == ARTIST, relative
    assert webpage["inLanguage"] == ("uk" if relative.startswith("ua/") else "en"), relative
    for bot in ("Googlebot", "bingbot", "OAI-SearchBot", "PerplexityBot"):
        assert robots.can_fetch(bot, webpage["url"]), (relative, bot)
    recording = next((node for node in graph if node["@type"] == "MusicRecording"), None)
    if recording:
        assert "/ua/" not in recording["@id"], relative
        assert recording["byArtist"]["@id"] == ARTIST, relative
        assert webpage["mainEntity"]["@id"] == recording["@id"], relative
        assert 'class="release-facts"' in source, relative
        assert f'datetime="{recording["duration"]}"' in source, relative
        assert f'datetime="{recording["datePublished"]}"' in source, relative
        links = Links()
        # Check the raw HTML before scripts, not JSON-LD or generated DOM.
        links.feed(source.split('<script type="application/ld+json">')[0])
        streaming_urls = set(recording.get("sameAs", []))
        if streaming_urls:
            assert streaming_urls <= links.urls, relative
        else:
            assert APPROVED_PRESAVES.get(recording["@id"]) in links.urls, relative
            notice = "Незабаром" if relative.startswith("ua/") else "Coming Soon"
            assert f'<p class="eyebrow red">{notice}</p><div class="platforms" data-platforms>' in source, relative
    all_links = Links()
    all_links.feed(source)
    for url in all_links.urls:
        if urlparse(url).hostname in ("distrokid.com", "www.distrokid.com"):
            assert recording and APPROVED_PRESAVES.get(recording["@id"]) == url, (relative, "Unapproved DistroKid link", url)

index = (ROOT / "llms.txt").read_text()
for url in re.findall(r'\]\((https://quietaccident.com/[^)]*)\)', index):
    path = ROOT / urlparse(url).path.lstrip("/")
    assert path.exists(), url
assert "distrokid.com" not in index.lower()
print(f"AI search checks passed for {len(pages)} pages: stable entities, readable facts, static streaming links, crawler access and llms.txt.")
