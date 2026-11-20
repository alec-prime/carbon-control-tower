"""Step 4: inline data into src/app.html and write index.html at the repo root."""
import os
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
r=lambda *p: open(os.path.join(ROOT,*p),encoding='utf-8').read()
pe=r('src','process-explorer.js').replace('__PEX__',r('data','derived','pe.json'))
html=r('src','app.html').replace('__DATA__',r('data','derived','data.json')).replace('__MAP__',r('src','world-map.json')).replace('__PE__',pe)
open(os.path.join(ROOT,'index.html'),'w',encoding='utf-8').write(html)
print('index.html', len(html)//1024, 'KB')
