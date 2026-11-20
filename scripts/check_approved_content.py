#!/usr/bin/env python3
"""Verify the approved bilingual editorial copy and metadata in generated HTML."""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
approved = json.loads((ROOT / 'data/seo-content.json').read_text())

def text(value):
    return ' '.join(html.unescape(re.sub(r'<[^>]*>', ' ', value)).split())

for route, copy in approved.items():
    source = (ROOT / route.lstrip('/') / 'index.html').read_text()
    assert text(re.search(r'<title>(.*?)</title>', source, re.S)[1]) == copy['title'], route
    for attribute in ['name="description"', 'property="og:description"', 'name="twitter:description"']:
        assert html.unescape(re.search('<meta ' + attribute + r' content="([^"]*)"', source)[1]) == copy['description'], route
    headings = re.findall(r'<h1[^>]*>(.*?)</h1>', source, re.S)
    assert len(headings) == 1 and text(re.sub(r'</?span[^>]*>', '', headings[0])) == copy['h1'], route
    visible = re.sub(r'<(?:script|style)\b.*?</(?:script|style)>', '', source, flags=re.S)
    visible = text(visible)
    strings = [copy[k] for k in ['hero','contentHeading','aboutHeading','cta'] if k in copy]
    strings.extend(copy.get('paragraphs', []))
    for section in copy.get('sections', []):
        strings.extend([section['heading'], *section['paragraphs']])
    for value in strings:
        assert text(value) in visible, (route, value)
    assert not re.search(r'ARTWORK PENDING|ОБКЛАДИНКА НЕЗАБАРОМ|Link to `', source), route
assert len(approved) == 24
print('PASS: approved metadata, H1 and visible editorial copy on all 24 EN/UA pages.')
