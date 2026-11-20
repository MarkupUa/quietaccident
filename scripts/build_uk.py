#!/usr/bin/env python3
"""Generate crawlable Ukrainian pages from English pages and the shared dictionary."""
import html,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
from seo_content import prepare_english, finish_ukrainian
prepare_english(ROOT)
D=json.loads((ROOT/'assets/i18n/uk.json').read_text())
# Keep release descriptions next to catalogue data so a stale UI dictionary
# cannot overwrite Ukrainian page content with an English description.
catalogue_path=ROOT/'assets/js/releases.js'
catalogue_source=catalogue_path.read_text()
catalogue_match=re.search(r'window\.QA_RELEASES\s*=\s*(\[.*\]);',catalogue_source,re.S)
catalogue=json.loads(catalogue_match[1])
for release in catalogue:
 if release['description'] not in D:
  raise ValueError(f"Missing Ukrainian release description: {release['slug']}")
 release['descriptionUk']=D[release['description']]
 release['titleUk']=D.get(release['title'],release['title'])
catalogue_path.write_text(catalogue_source[:catalogue_match.start(1)]+'[\n'+',\n'.join('  '+json.dumps(release,ensure_ascii=False) for release in catalogue)+'\n]'+catalogue_source[catalogue_match.end(1):])
def translate(s):
 if s in D:return D[s]
 parts={' — official single artwork':' — офіційна обкладинка синглу','by Quiet Accident | Listen & Stream':'від Quiet Accident | Слухати онлайн','by Quiet Accident | Listen & Watch':'від Quiet Accident | Слухати та дивитися',' — official video by Quiet Accident':' — офіційне відео Quiet Accident',' (Official Visualizer)':' (Офіційний візуалайзер)',' — official artwork':' — офіційна обкладинка',' / Single':' / Сингл',' · Single · ':' · Сингл · ','SINGLE / ':'СИНГЛ / '}
 for a,b in sorted({**D,**parts}.items(),key=lambda x:-len(x[0])):
  if len(a)>3:s=s.replace(a,b)
 return s

def route(u):
 if u.startswith('https://quietaccident.com/'):
  path=u[len('https://quietaccident.com/'):]
  if not path.startswith('assets/') and not path.startswith('ua/'):return 'https://quietaccident.com/ua/'+path
 if u.startswith('/') and not u.startswith(('/assets/','/ua/')):return '/ua'+u
 return u

def schema(v,key=None):
 if key=='inLanguage' and isinstance(v,list):return v
 if isinstance(v,dict):return {k:schema(x,k) for k,x in v.items()}
 if isinstance(v,list):return [schema(x,key) for x in v]
 if isinstance(v,str):
  if key=='inLanguage':return 'uk'
  if key=='@id' and (v.endswith('#artist') or v.endswith('#website') or v.endswith('#recording')):return v
  if key in ['url','@id','item']:return route(v)
  if key in ['description','name']:return translate(v)
 return v

def switcher(path,uk):
 en='/'+path.removesuffix('index.html');ua='/ua'+en
 return '<nav class="language-switch" aria-label="'+('Мова сайту' if uk else 'Site language')+'">'+''.join(f'<a href="{u}" lang="{lang}" hreflang="{lang}" data-language="{lang}"'+(' aria-current="true"' if uk==(lang=='uk') else '')+f' aria-label="{label}">{text}</a>' for u,lang,label,text in [(en,'en','English','EN'),(ua,'uk','Українська','UA')])+'</nav>'

pages=[ROOT/'index.html',ROOT/'about/index.html',ROOT/'releases/index.html',*sorted((ROOT/'releases').glob('*/index.html'))]
for p in pages:
 rel=p.relative_to(ROOT).as_posix();s=p.read_text()
 s=re.sub(r'<nav class="language-switch".*?</nav>','',s,flags=re.S)
 s=re.sub(r'<link rel="alternate"[^>]*>\s*','',s)
 s=re.sub(r'<script src="/assets/js/language.js[^\"]*"></script>\s*','',s)
 s=s.replace('<head>','<head><script src="/assets/js/language.js?v=3"></script>',1)
 path=rel.removesuffix('index.html');en='https://quietaccident.com/'+path;uk='https://quietaccident.com/ua/'+path
 alternate=''.join(f'<link rel="alternate" hreflang="{lang}" href="{url}">' for lang,url in [('en',en),('uk',uk),('x-default',en)])
 s=s.replace('</head>',alternate+'\n</head>')
 s=s.replace('</nav></div></header>','</nav>'+switcher(rel,False)+'</div></header>',1)
 # Shared root-relative assets work at both language depths.
 s=re.sub(r'((?:src|href|srcset)=")(?:(?:\.\.?/)*)(assets/)',r'\1/\2',s)
 s=s.replace('<script defer src="/assets/js/main.js', '<script defer src="/assets/js/translations.js?v=10"></script><script defer src="/assets/js/main.js') if '/assets/js/translations.js' not in s else s
 for asset,version in [('translations.js',22),('main.js',14),('releases.js',30),('style.css',11)]:
  s=re.sub(re.escape(asset)+r'\?v=\d+',f'{asset}?v={version}',s)
 p.write_text(s)
 chunks=re.split(r'(<script\b.*?</script>)',s,flags=re.S)
 for i,c in enumerate(chunks):
  if c.startswith('<script'):
   if 'application/ld+json' in c:
    m=re.search(r'>(.*?)</script>',c,re.S);data=schema(json.loads(m[1]));chunks[i]=c[:m.start(1)]+json.dumps(data,ensure_ascii=False,separators=(',',':'))+c[m.end(1):]
   continue
  def tag(m):
   t=m[0]
   if t.startswith('<html'):t=t.replace('lang="en"','lang="uk"')
   if 'class="language-switch"' in t:return t
   if 'rel="alternate"' in t:return t
   def attr(a):
    key,val=a[1],html.unescape(a[2])
    if key in ['href'] and 'data-language=' not in t:val=route(val)
    elif key in ['alt','title','aria-label']:val=translate(val)
    elif key=='content':
     val=route(val) if 'property="og:url"' in t else ('uk_UA' if 'property="og:locale"' in t else translate(val))
    return key+'="'+html.escape(val,quote=True)+'"'
   return re.sub(r'(href|alt|title|aria-label|content)="([^"]*)"',attr,t)
  pieces=re.split(r'(<[^>]+>)',c)
  for j,part in enumerate(pieces):
   if part.startswith('<'):pieces[j]=tag(re.match(r'[\s\S]+',part))
   elif part.strip():
    stripped=html.unescape(part.strip());pieces[j]=part[:len(part)-len(part.lstrip())]+html.escape(translate(stripped),quote=False)+part[len(part.rstrip()):]
  chunks[i]=''.join(pieces)
 ua=''.join(chunks)
 ua=re.sub(r'<nav class="language-switch".*?</nav>',switcher(rel,True),ua,flags=re.S)
 ua=ua.replace('data-root="./"','data-root="/"').replace('data-root="../"','data-root="/"').replace('data-root="../../"','data-root="/"')
 out=ROOT/'ua'/rel;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(ua)
print(f'Generated {len(pages)} Ukrainian pages and bilingual headers.')
# Browser translation dictionary also covers dynamically rendered cards and status messages.
(ROOT/'assets/js/translations.js').write_text('window.QA_TRANSLATIONS = '+json.dumps(D,ensure_ascii=False,separators=(',',':'))+';\n')

finish_ukrainian(ROOT)
