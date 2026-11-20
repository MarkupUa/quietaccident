#!/usr/bin/env python3
"""Create responsive PNG covers; preserve original PNG artwork and aspect ratios."""
from pathlib import Path
from PIL import Image
import re
ROOT=Path(__file__).resolve().parent.parent
ART=ROOT/'assets/images/releases'
originals=[p for p in ART.glob('*.png') if not re.search(r'-\d+\.png$',p.name)]
for source in originals:
 with Image.open(source) as image:
  for width in [480,800]:
   if image.width<=width:continue
   target=source.with_name(source.stem+f'-{width}.png')
   if target.exists() and target.stat().st_mtime>=source.stat().st_mtime:continue
   height=round(image.height*width/image.width)
   resized=image.resize((width,height),Image.Resampling.LANCZOS)
   opts={'icc_profile':image.info['icc_profile']} if image.info.get('icc_profile') else {}
   resized.save(target,format='PNG',optimize=True,**opts)

def sizes(page,index):
 if page.parent.name=='releases' and page.name=='index.html':return '(max-width: 479px) calc(100vw - 40px), (max-width: 649px) calc((100vw - 64px) / 2), (max-width: 949px) calc((100vw - 128px) / 3), (min-width: 1360px) 240px, calc((100vw - 160px) / 5)'
 if page.relative_to(ROOT).as_posix().removeprefix('ua/')=='index.html' and index>0:return '(max-width: 649px) calc(100vw - 40px), (min-width: 1360px) 411px, calc((100vw - 128px) / 3)'
 return '(max-width: 649px) calc(100vw - 40px), (max-width: 949px) calc(100vw - 80px), (min-width: 1360px) 600px, calc((100vw - 160px) / 2)'
pages=[ROOT/'index.html',ROOT/'releases/index.html',*sorted((ROOT/'releases').glob('*/index.html')),*sorted((ROOT/'ua').rglob('index.html'))]
for page in pages:
 text=page.read_text();counter=[0]
 def update(m):
  tag=m[0];src=re.search(r'\bsrc="([^"]+)"',tag)[1];path=ROOT/src.lstrip('/')
  if not path.exists():return tag
  index=counter[0];counter[0]+=1
  tag=re.sub(r'\s+(?:srcset|sizes|decoding|fetchpriority)="[^"]*"','',tag)
  candidates=[(w,src.removesuffix('.png')+f'-{w}.png') for w in [480,800] if (ROOT/(src.removesuffix('.png')+f'-{w}.png').lstrip('/')).exists()]
  with Image.open(path) as image:full_width=image.width
  candidates.append((full_width,src));srcset=', '.join(f'{url} {width}w' for width,url in candidates)
  attributes=f' srcset="{srcset}" sizes="{sizes(page,index)}" decoding="async"'
  if page.parent.parent.name=='releases':
   tag=re.sub(r'\s+loading="[^"]*"','',tag);attributes+=' fetchpriority="high"'
  return tag[:-1]+attributes+'>'
 text=re.sub(r'<img\b[^>]*\bsrc="/assets/images/releases/[^\"]+\.png"[^>]*>',update,text)
 if page.read_text()!=text:page.write_text(text)
original_bytes=sum(p.stat().st_size for p in originals)
small_bytes=sum(p.with_name(p.stem+'-480.png').stat().st_size for p in originals if p.with_name(p.stem+'-480.png').exists())
print(f'Prepared responsive PNGs for {len(originals)} covers: originals {original_bytes:,} bytes; 480px variants {small_bytes:,} bytes.')
