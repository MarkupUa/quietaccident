#!/usr/bin/env python3
"""Configure canonical URLs and bilingual image/video sitemap with truthful lastmod."""
import argparse,hashlib,html,json,re,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlparse,urlunsplit
import xml.etree.ElementTree as ET

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('url',help='Public HTTPS base URL')
args=parser.parse_args();parsed=urlparse(args.url)
if parsed.scheme!='https' or not parsed.netloc or parsed.query or parsed.fragment:parser.error('Use a complete HTTPS base URL without query or fragment.')
BASE=args.url.rstrip('/')+'/';ROOT=Path(__file__).resolve().parent.parent
subprocess.run([sys.executable,str(ROOT/'scripts/optimize_images.py')],check=True)
PAGES=[ROOT/'index.html',ROOT/'about/index.html',ROOT/'releases/index.html',*sorted((ROOT/'releases').glob('*/index.html')),*sorted((ROOT/'ua').rglob('index.html'))]
SM='http://www.sitemaps.org/schemas/sitemap/0.9';IMAGE='http://www.google.com/schemas/sitemap-image/1.1';VIDEO='http://www.google.com/schemas/sitemap-video/1.1';XHTML='http://www.w3.org/1999/xhtml'
for prefix,uri in [('',SM),('image',IMAGE),('video',VIDEO),('xhtml',XHTML)]:ET.register_namespace(prefix,uri)
def write(path,text):
 if not path.exists() or path.read_text()!=text:path.write_text(text)
def internal_url(value):
 p=urlparse(value)
 if value.startswith('/') and not value.startswith('//'):return BASE+value.lstrip('/')
 if not p.scheme and 'assets/' in value:return BASE+'assets/'+value.split('assets/',1)[1]
 if p.hostname in {parsed.hostname,'quietaccident.com','www.quietaccident.com'}:
  result=BASE+p.path.lstrip('/')
  if p.query:result+='?'+p.query
  if p.fragment:result+='#'+p.fragment
  return result
 return value

def schema(value,key=None):
 if isinstance(value,dict):return {k:schema(v,k) for k,v in value.items()}
 if isinstance(value,list):return [schema(v,key) for v in value]
 if isinstance(value,str) and key in {'@id','url','image','thumbnailUrl','item'}:return internal_url(value)
 return value

def videos(value):
 if isinstance(value,dict):
  if value.get('@type')=='VideoObject':yield value
  for nested in value.values():yield from videos(nested)
 elif isinstance(value,list):
  for nested in value:yield from videos(nested)

def seconds(duration):
 m=re.fullmatch(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?',duration)
 if not m:raise ValueError('Invalid verified video duration: '+duration)
 return sum(int(v or 0)*factor for v,factor in zip(m.groups(),[3600,60,1]))

state_path=ROOT/'scripts/.seo-state.json'
state=json.loads(state_path.read_text()) if state_path.exists() else {}
next_state={};today=datetime.now(timezone.utc).date().isoformat();sitemap=ET.Element(f'{{{SM}}}urlset');video_count=0
for page in PAGES:
 relative=page.relative_to(ROOT).as_posix().removesuffix('index.html');canonical=BASE+relative;text=page.read_text()
 image_match=re.search(r'<meta property="og:image" content="([^"]+)">',text)
 if not image_match:raise ValueError('Missing social image: '+relative)
 image=internal_url(html.unescape(image_match[1]))
 for key in ['og:image','twitter:image']:
  text=re.sub(r'(<meta (?:property|name)="'+re.escape(key)+r'" content=")[^"]*(">)',lambda m:m[1]+html.escape(image,quote=True)+m[2],text,count=1)
 graphs=[]
 def update(match):
  data=schema(json.loads(match[1]));graphs.append(data)
  return '<script type="application/ld+json">'+json.dumps(data,ensure_ascii=False,separators=(',',':'))+'</script>'
 text=re.sub(r'<script type="application/ld\+json">(.*?)</script>',update,text,flags=re.S)
 found=list(videos(graphs));unique={v['embedUrl']:v for v in found};found=list(unique.values())
 text=re.sub(r'<link rel="canonical"[^>]*>\s*|<meta property="og:url"[^>]*>\s*|<meta property="og:video(?::[^"]+)?"[^>]*>\s*','',text)
 meta=f'<link rel="canonical" href="{html.escape(canonical,quote=True)}"><meta property="og:url" content="{html.escape(canonical,quote=True)}">'
 if found:
  embed=html.escape(found[0]['embedUrl'],quote=True)
  meta+=f'<meta property="og:video" content="{embed}"><meta property="og:video:secure_url" content="{embed}"><meta property="og:video:type" content="text/html"><meta property="og:video:width" content="1280"><meta property="og:video:height" content="720">'
 text=text.replace('</head>',meta+'\n</head>',1);write(page,text)
 # File mtimes and cache-only URL changes are not content updates.
 fingerprint=re.sub(r'(/assets/[^"\s?]+)\?v=[a-zA-Z0-9]+',r'\1',text)
 fingerprint=re.sub(r'\s+',' ',fingerprint).strip();digest=hashlib.sha256(fingerprint.encode()).hexdigest()
 previous=state.get(relative,{});lastmod=previous.get('lastmod',today) if previous.get('sha256')==digest else today
 next_state[relative]={'sha256':digest,'lastmod':lastmod}
 node=ET.SubElement(sitemap,f'{{{SM}}}url');ET.SubElement(node,f'{{{SM}}}loc').text=canonical;ET.SubElement(node,f'{{{SM}}}lastmod').text=lastmod
 english=relative.removeprefix('ua/')
 for lang,prefix in [('en',''),('uk','ua/'),('x-default','')]:ET.SubElement(node,f'{{{XHTML}}}link',{'rel':'alternate','hreflang':lang,'href':BASE+prefix+english})
 image_node=ET.SubElement(node,f'{{{IMAGE}}}image');ET.SubElement(image_node,f'{{{IMAGE}}}loc').text=image
 for v in found:
  for required in ['thumbnailUrl','name','description','embedUrl','duration','uploadDate']:
   if not v.get(required):raise ValueError(f'{relative}: missing verified video {required}')
  vn=ET.SubElement(node,f'{{{VIDEO}}}video')
  for key,value in [('thumbnail_loc',v['thumbnailUrl']),('title',v['name']),('description',v['description']),('player_loc',v['embedUrl']),('duration',str(seconds(v['duration']))),('publication_date',v['uploadDate'])]:ET.SubElement(vn,f'{{{VIDEO}}}{key}').text=value
  video_count+=1
ET.indent(sitemap,space='  ')
write(ROOT/'sitemap.xml','<?xml version="1.0" encoding="UTF-8"?>\n'+ET.tostring(sitemap,encoding='unicode')+'\n')
write(state_path,json.dumps(next_state,ensure_ascii=False,indent=2)+'\n')
write(ROOT/'robots.txt','User-agent: *\nAllow: /\n\nSitemap: '+BASE+'sitemap.xml\n')
print(f'Configured {len(PAGES)} pages, {video_count} localized video entries, bilingual/image sitemap and content-based lastmod.')
