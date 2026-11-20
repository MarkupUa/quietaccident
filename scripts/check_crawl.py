#!/usr/bin/env python3
"""Audit raw HTML crawlability, related links, responsive images and video sitemap."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,urljoin
from collections import deque
import json,re,struct,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parent.parent;BASE='https://quietaccident.com/'
class Document(HTMLParser):
 def __init__(self):super().__init__();self.links=[];self.images=[];self.frames=[];self.heading=[]
 def handle_starttag(self,t,a):
  a=dict(a)
  if t=='a' and a.get('href'):self.links.append(a['href'])
  if t=='img':self.images.append(a)
  if t=='iframe':self.frames.append(a)
  if t in ['h1','h2','h3']:self.heading.append(t)
pages=[ROOT/'index.html',ROOT/'about/index.html',ROOT/'releases/index.html',*sorted((ROOT/'releases').glob('*/index.html')),*sorted((ROOT/'ua').rglob('index.html'))]
expected={BASE+p.relative_to(ROOT).as_posix().removesuffix('index.html'):p for p in pages}
SM='http://www.sitemaps.org/schemas/sitemap/0.9';XHTML='http://www.w3.org/1999/xhtml';VIDEO='http://www.google.com/schemas/sitemap-video/1.1'
sitemap=ET.parse(ROOT/'sitemap.xml').getroot();entries={n.findtext(f'{{{SM}}}loc'):n for n in sitemap};assert set(entries)==set(expected)
graph={};video_count=0
for url,p in expected.items():
 source=p.read_text();doc=Document();doc.feed(source);graph[url]=set()
 for href in doc.links:
  dest=urlsplit(urljoin(url,href));clean=dest._replace(query='',fragment='').geturl()
  if clean in expected:graph[url].add(clean)
 for attrs in doc.images:
  src=attrs.get('src','')
  if '/assets/images/releases/' not in src:continue
  assert 'srcset' in attrs and 'sizes' in attrs,(p,src)
  for candidate in attrs['srcset'].split(','):
   image_url,width=candidate.strip().rsplit(' ',1);asset=ROOT/urlsplit(image_url).path.lstrip('/');assert asset.exists(),asset
   data=asset.read_bytes();assert data.startswith(b'\x89PNG\r\n\x1a\n'),asset
   real_width=struct.unpack('>II',data[16:24])[0];assert real_width==int(width[:-1]),asset
 node=entries[url];relative=p.relative_to(ROOT).as_posix();english=relative.removeprefix('ua/').removesuffix('index.html')
 alternates={n.attrib['hreflang']:n.attrib['href'] for n in node.findall(f'{{{XHTML}}}link')};assert alternates=={'en':BASE+english,'uk':BASE+'ua/'+english,'x-default':BASE+english}
 schema=json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>',source,re.S)[1]);recording=next((n for n in schema['@graph'] if n['@type']=='MusicRecording'),None)
 video=recording.get('subjectOf') if recording else None;sitemap_videos=node.findall(f'{{{VIDEO}}}video')
 if video:
  assert len(sitemap_videos)==len(doc.frames)==1,p
  vn=sitemap_videos[0];assert vn.findtext(f'{{{VIDEO}}}player_loc')==video['embedUrl']==doc.frames[0]['src']
  assert vn.findtext(f'{{{VIDEO}}}publication_date')==video['uploadDate']
  assert vn.findtext(f'{{{VIDEO}}}thumbnail_loc')==video['thumbnailUrl']
  assert re.search(r'<meta property="og:video" content="'+re.escape(video['embedUrl'])+'"',source)
  video_count+=1
 else:assert not sitemap_videos and not doc.frames,p
 if recording:
  assert 'aria-label="Breadcrumb"' in source or 'aria-label="Навігаційний ланцюжок"' in source,p
  assert 'class="release-siblings"' in source,p
  other_releases=[x for x in graph[url] if '/releases/' in x and x.rstrip('/') not in [BASE.rstrip('/')+'/releases',BASE.rstrip('/')+'/ua/releases'] and x!=url]
  assert other_releases,p
 if p in [ROOT/'releases/index.html',ROOT/'ua/releases/index.html']:
  assert 'h2' in doc.heading and 'h3' not in doc.heading,p
for start in [BASE,BASE+'ua/']:
 distance={start:0};queue=deque([start])
 while queue:
  current=queue.popleft()
  for dest in graph[current]:
   if dest not in distance:distance[dest]=distance[current]+1;queue.append(dest)
 assert set(distance)==set(expected),(start,set(expected)-set(distance))
 # Each locale's entire catalogue is reachable within two internal links.
 locale='uk' if start.endswith('/ua/') else 'en'
 relevant=[u for u in expected if ('/ua/' in u)==(locale=='uk')]
 assert max(distance[u] for u in relevant)<=2
print(f'PASS: {len(pages)} crawlable pages, depth <=2 per locale, responsive PNGs, breadcrumbs, related releases and {video_count} video sitemap entries.')
