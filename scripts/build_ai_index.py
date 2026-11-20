#!/usr/bin/env python3
"""Build the optional public plain-text site index from canonical English pages."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://quietaccident.com/"
home = (ROOT / "index.html").read_text()
pattern = r'<script type="application/ld\+json">(.*?)</script>'
artist = next(node for node in json.loads(re.search(pattern, home, re.S)[1])["@graph"] if node["@type"] == "MusicGroup")
lines = [
    "# Quiet Accident", "", 
    "> Official website of Quiet Accident, an independent electronic music project combining Dark Techno, deep bass, hypnotic rhythms and cinematic atmosphere.",
    "", "This index summarizes public information from the official site. English pages are at the root; Ukrainian pages are under /ua/. Follow the release pages for current streaming links and available official videos.",
    "", "## Official pages", "",
    f"- [Home]({BASE})", f"- [About the project]({BASE}about/)",
    f"- [Release catalogue]({BASE}releases/)",
    f"- [Українська версія]({BASE}ua/)", f"- [Про проєкт]({BASE}ua/about/)",
    f"- [Релізи]({BASE}ua/releases/)", "", "## Singles", "",
]
recordings = []
for page in (ROOT / "releases").glob("*/index.html"):
    data = json.loads(re.search(pattern, page.read_text(), re.S)[1])
    recording = next(node for node in data["@graph"] if node["@type"] == "MusicRecording")
    recordings.append(recording)
for recording in sorted(recordings, key=lambda node: node["datePublished"], reverse=True):
    lines.append(f'- [{recording["name"]}]({recording["url"]}): single by Quiet Accident. Release date: {recording["datePublished"]}; duration {recording["duration"]}.')
    lines.append(f'  - [Українською]({recording["url"].replace(BASE, BASE + "ua/")})')
    video = recording.get('subjectOf', {})
    if video.get('embedUrl'):
        video_id = video['embedUrl'].rstrip('/').rsplit('/', 1)[-1]
        lines.append('  - [Official video](https://www.youtube.com/watch?v=' + video_id + ')')
lines += ["", "## Official artist profiles", ""]
for url in artist["sameAs"]:
    lines.append(f'- [{url.split("/")[2]}]({url})')
lines += ["", "## Site index", "", f"- [XML sitemap]({BASE}sitemap.xml)"]
(ROOT / "llms.txt").write_text("\n".join(lines) + "\n")
print(f"Built llms.txt from {len(recordings)} official release pages.")
