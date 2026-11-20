"""Apply the approved bilingual copy using existing HTML layouts (no runtime dependency)."""
import html,json,re
from pathlib import Path
BASE='https://quietaccident.com/'

def esc(value):return html.escape(value,quote=False)
def paras(values):return ''.join('<p>'+esc(value)+'</p>' for value in values)
def write(path,text):
 if not path.exists() or path.read_text()!=text:path.write_text(text)
def catalogue(root):
 text=(root/'assets/js/releases.js').read_text();match=re.search(r'window\.QA_RELEASES\s*=\s*(\[.*\]);',text,re.S)
 return text,match,json.loads(match[1])

def metadata(source,copy):
 source=re.sub(r'<title>.*?</title>','<title>'+esc(copy['title'])+'</title>',source,count=1,flags=re.S)
 for key,value in [('description',copy['description']),('og:title',copy['title']),('og:description',copy['description']),('twitter:title',copy['title']),('twitter:description',copy['description'])]:
  source=re.sub(r'(<meta (?:name|property)="'+re.escape(key)+r'" content=")[^"]*(")',lambda m:m[1]+html.escape(value,quote=True)+m[2],source)
 return source

def normalize_entities(source,path,copy,records,approved):
 match=re.search(r'<script type="application/ld\+json">(.*?)</script>',source,re.S);data=json.loads(match[1]);uk=path.startswith('/ua/');language='uk' if uk else 'en';pages={r['slug']:r for r in records}
 def visit(node):
  if isinstance(node,list):
   for value in node:visit(value)
  elif isinstance(node,dict):
   kind=node.get('@type')
   if kind=='MusicGroup' and node.get('@id')==BASE+'#artist':node['url']=BASE
   elif kind=='WebSite':node.update({'@id':BASE+'#website','url':BASE,'inLanguage':['en','uk'],'description':approved['/']['description']})
   elif kind in ['WebPage','AboutPage','CollectionPage']:
    node.update(url=BASE.rstrip('/')+path,name=copy['title'],description=copy['description'],inLanguage=language,isPartOf={'@id':BASE+'#website'})
   elif kind=='MusicRecording':
    recording_id=node.get('@id','');m=re.search(r'/releases/([^/]+)/#recording$',recording_id)
    if m and m[1] in pages:
     record=pages[m[1]];slug=record['slug'];node['name']=record['title'];node['url']=BASE+'releases/'+slug+'/'
     if record.get('titleUk') and record['titleUk']!=record['title']:node['alternateName']=record['titleUk']
     node['description']=record['descriptionUk'] if uk else record['description']
     node['mainEntityOfPage']=[{'@id':BASE+'releases/'+slug+'/#page'},{'@id':BASE+'ua/releases/'+slug+'/#page'}]
   for value in list(node.values()):visit(value)
 visit(data)
 return source[:match.start(1)]+json.dumps(data,ensure_ascii=False,separators=(',',':'))+source[match.end(1):]

def prepare_english(root):
 approved=json.loads((root/'data/seo-content.json').read_text());dictionary=json.loads((root/'assets/i18n/uk.json').read_text())
 text,match,records=catalogue(root)
 # Synchronize all compact release text and localized names from the approved copy.
 for record in records:
  en=approved['/releases/'+record['slug']+'/'];uk=approved['/ua/releases/'+record['slug']+'/']
  record['description']=en['hero'];record['descriptionUk']=uk['hero']
  record['shortDescription']=approved['/releases/']['cardDescriptions'][record['title']]
  record['shortDescriptionUk']=approved['/ua/releases/']['cardDescriptions'][record['titleUk']]
  dictionary[record['title']]=record['titleUk']
 write(root/'assets/js/releases.js',text[:match.start(1)]+'[\n'+',\n'.join('  '+json.dumps(r,ensure_ascii=False) for r in records)+'\n]'+text[match.end(1):])
 for path,en in approved.items():
  if path.startswith('/ua/'):continue
  uk=approved['/ua'+path]
  for key in ['title','description','hero','contentHeading','cta','aboutHeading']:
   if key in en:dictionary[en[key]]=uk[key]
  for a,b in zip(en.get('paragraphs',[]),uk.get('paragraphs',[])):dictionary[a]=b
  for a,b in zip(en.get('sections',[]),uk.get('sections',[])):
   dictionary[a['heading']]=b['heading']
   for x,y in zip(a['paragraphs'],b['paragraphs']):dictionary[x]=y
 dictionary.update({'BUILT FOR':'СТВОРЕНО ДЛЯ','THE ROAD AHEAD.':'ДОРОГИ.'})
 for key in list(dictionary):
  if 'ARTWORK PENDING' in key or 'ОБКЛАДИНКА НЕЗАБАРОМ' in dictionary[key]:dictionary.pop(key)
 write(root/'assets/i18n/uk.json',json.dumps(dictionary,ensure_ascii=False,indent=2)+'\n')
 for path,copy in approved.items():
  if path.startswith('/ua/'):continue
  page=root/path.lstrip('/')/'index.html';source=page.read_text();source=metadata(source,copy)
  # Compact favicons replace the original multi-megabyte artwork favicon.
  source=re.sub(r'\s*<link rel="(?:icon|apple-touch-icon)"[^>]*>','',source)
  source=source.replace('</head>','<link rel="icon" href="/favicon.ico" sizes="any"><link rel="icon" type="image/png" sizes="32x32" href="/assets/icons/favicon-32.png"><link rel="apple-touch-icon" sizes="180x180" href="/assets/icons/apple-touch-icon.png">\n</head>',1)
  source=re.sub(r'<small class="art-label">.*?</small>',lambda m:re.sub(r'\s*·\s*(?:ARTWORK PENDING|ОБКЛАДИНКА НЕЗАБАРОМ)','',m[0]),source)
  if path=='/':
   start=source.index('<section class="hero wrap">');end=source.index('</section>',start);hero=source[start:end]
   hero=re.sub(r'<p class="lede">.*?</p>','<p class="lede">'+esc(copy['hero'])+'</p>',hero,count=1,flags=re.S);source=source[:start]+hero+source[end:]
   source=re.sub(r'<section class="section wrap music-intro".*?</section>','',source,flags=re.S)
   extra='<section class="section wrap music-intro" aria-labelledby="night-drive-heading"><div class="editorial-copy"><h2 id="night-drive-heading">'+esc(copy['contentHeading'])+'</h2>'+paras(copy['paragraphs'])+'<a class="text-link" href="/releases/">'+esc(copy['cta'])+'</a></div></section>'
   source=source.replace('</main>',extra+'</main>',1)
   newest=sorted((r for r in records if r['published']),key=lambda r:r['releaseDate'],reverse=True)[0]
   start=source.index('<div class="latest" data-latest>');end=source.index('</section>',start);latest=source[start:end];latest=re.sub(r'<p class="lede">.*?</p>','<p class="lede">'+esc(newest['description'])+'</p>',latest,count=1,flags=re.S);source=source[:start]+latest+source[end:]
  elif path=='/about/':
   source=re.sub(r'<h1>.*?</h1>','<h1>BUILT FOR<br>THE ROAD AHEAD.</h1>',source,count=1,flags=re.S)
   intro=copy['sections'][0]
   source=re.sub(r'(<div class="editorial-copy"><p class="eyebrow">Quiet Accident / The project</p>).*?(</div></section>)',lambda m:m[1]+'<h2>'+esc(intro['heading'])+'</h2>'+paras(intro['paragraphs'])+m[2],source,count=1,flags=re.S)
   count=[1]
   def article(m):
    section=copy['sections'][count[0]];count[0]+=1
    return m[1]+'<h2>'+esc(section['heading'])+'</h2>'+paras(section['paragraphs'])+'</article>'
   source=re.sub(r'(<article><span class="eyebrow red">[^<]+</span>).*?</article>',article,source,count=3,flags=re.S);assert count[0]==4
   final=copy['sections'][4]
   # Retain the actual official-profile links and existing social CTAs.
   start=source.index('<section class="section"><p class="eyebrow">Quiet Accident · Molotko Media Group');end=source.index('</section>',start);block=source[start:end]
   block=re.sub(r'<h2>.*?</h2>','<h2>'+esc(final['heading'])+'</h2>',block,count=1,flags=re.S)
   follow=re.search(r'<div class="follow-copy">(.*?)</div>',block,re.S);old_paras=re.findall(r'<p>.*?</p>',follow[1],re.S);social_para=next(p for p in old_paras if 'https://open.spotify.com/' in p)
   block=block[:follow.start(1)]+paras(final['paragraphs'])+social_para+block[follow.end(1):]
   block=re.sub(r'(<a class="text-link" href="/releases/">).*?(</a>)',lambda m:m[1]+esc(copy['cta'])+m[2],block,count=1,flags=re.S);source=source[:start]+block+source[end:]
  elif path=='/releases/':
   start=source.index('<section class="page-intro">');end=source.index('</section>',start)
   intro=source[start:end];intro=re.sub(r'<p class="lede">.*?</p>','<div class="catalog-intro">'+paras(copy['paragraphs'])+'</div>',intro,count=1,flags=re.S)
   if 'class="catalog-intro"' in intro:intro=re.sub(r'<div class="catalog-intro">.*?</div>','<div class="catalog-intro">'+paras(copy['paragraphs'])+'</div>',intro,count=1,flags=re.S)
   source=source[:start]+intro+source[end:]
  else:
   source=re.sub(r'<h1>.*?</h1>','<h1>'+esc(copy['h1'])+'</h1>',source,count=1,flags=re.S)
   source=re.sub(r'<p class="lede">.*?</p>','<p class="lede">'+esc(copy['hero'])+'</p>',source,count=1,flags=re.S)
   source=re.sub(r'<section class="release-editorial".*?</section>','',source,flags=re.S)
   extra='<section class="release-editorial" aria-labelledby="about-track-heading"><h2 id="about-track-heading">'+esc(copy['aboutHeading'])+'</h2>'+paras(copy['paragraphs'])+'</section>'
   marker='<section class="release-video"' if '<section class="release-video"' in source else '<section class="release-note"';source=source.replace(marker,extra+marker,1)
  source=normalize_entities(source,path,copy,records,approved);write(page,source)

def finish_ukrainian(root):
 approved=json.loads((root/'data/seo-content.json').read_text());records=catalogue(root)[2]
 for path,copy in approved.items():
  if not path.startswith('/ua/'):continue
  page=root/path.lstrip('/')/'index.html';source=metadata(page.read_text(),copy)
  source=normalize_entities(source,path,copy,records,approved)
  # The title is part of the local page; the official recording name stays stable.
  if '/releases/' in path and path!='/ua/releases/':source=re.sub(r'<h1>.*?</h1>','<h1>'+esc(copy['h1'])+'</h1>',source,count=1,flags=re.S)
  write(page,source)
