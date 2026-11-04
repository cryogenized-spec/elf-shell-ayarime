"""Standalone Chromium UI regression test with locally inlined release assets.

Uses a synthetic document (not an installed Firefox extension) because the QA
container's Chromium policy disallows file:// and localhost navigation. This
only validates page UI; Firefox-native APIs still require actual Firefox QA.
Run: python3 tests/visual_qa.py
"""
from pathlib import Path
from playwright.sync_api import sync_playwright
import base64
import json
import re

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'dist'/'visual-qa'
OUT.mkdir(parents=True,exist_ok=True)
html=(ROOT/'newtab.html').read_text(encoding='utf-8')
css=(ROOT/'styles.css').read_text(encoding='utf-8')
# Build a self-contained, offline visual test page. Its code is the real source.
def data_url(path):
    p=ROOT/path
    mime='image/webp' if p.suffix=='.webp' else 'image/svg+xml'
    return 'data:'+mime+';base64,'+base64.b64encode(p.read_bytes()).decode('ascii')
css=css.replace('url("assets/ayarime-background.webp")','url("'+data_url('assets/ayarime-background.webp')+'")')
html=html.replace('<link rel="stylesheet" href="styles.css">','<style>'+css+'</style>')
html=re.sub(r'<script defer src="(?:newtab|memory|feeds)\.js"></script>', '', html)
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
    page=browser.new_page(viewport={'width':1600,'height':900},device_scale_factor=1)
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.set_content(html,wait_until='domcontentloaded')
    # about:blank has an opaque origin. Provide an in-memory localStorage shim.
    quotes=(ROOT/'assets/ayarime-quotes.json').read_text(encoding='utf-8')
    setup='''(() => {
      const cache=new Map(); const store={getItem:k=>cache.get(k)??null,setItem:(k,v)=>cache.set(k,String(v)),removeItem:k=>cache.delete(k)};
      Object.defineProperty(window,'localStorage',{configurable:true,value:store});
      window.fetch=async()=>({ok:true,json:async()=>JSON.parse(%s)});
    })();''' % json.dumps(quotes)
    page.evaluate(setup)
    for script in ('newtab.js','memory.js','feeds.js'):
        page.add_script_tag(content=(ROOT/script).read_text(encoding='utf-8'))
    # Inline icon art for a faithful picture without network access.
    for icon in ['firefox','mail','calendar','drive','video','library']:
        url=data_url('assets/shortcut-icons/'+icon+'.webp')
        page.eval_on_selector_all('#shortcuts img','(imgs,arg)=>imgs.forEach(img=>{if(img.src.endsWith("/"+arg.icon+".webp"))img.src=arg.url})',{'icon':icon,'url':url})
    assert page.title()=='ELF//SHELL — Ayarime'
    assert page.locator('#shortcuts .shortcut').count()==6
    assert not page.locator('#station-menu').evaluate('(n)=>n.open')
    page.screenshot(path=str(OUT/'desktop.png'))
    page.locator('#station-menu summary').click()
    assert page.locator('#station-menu').evaluate('(n)=>n.open')
    assert page.locator('#station-menu .settings-toggle').count()==7
    page.locator('#permissions-toggle').click()
    assert page.locator('#access-dialog').evaluate('(n)=>n.open')
    assert page.locator('#permission-host-list').inner_text().strip()
    page.get_by_role('button',name='CLOSE',exact=True).click()
    assert not page.locator('#station-menu').evaluate('(n)=>n.open')
    page.keyboard.press('Control+k')
    assert page.locator('#search-input').input_value()== '>'
    assert page.locator('#search-results .search-item').count()>=7
    assert page.locator('#search-results .search-group-title').count()>=2
    page.keyboard.press('ArrowDown')
    assert page.locator('#search-input').get_attribute('aria-activedescendant')=='palette-option-1'
    page.keyboard.press('Escape')
    assert page.locator('#search-results').is_hidden()
    assert page.locator('#search-input').input_value()==''
    search=page.locator('#search-form').bounding_box()
    coords=page.locator('.coordinates').bounding_box()
    assert coords['y']+coords['height'] <= search['y']-8,('Label overlap',coords,search)
    for width,height,name in [(768,900,'tablet'),(390,844,'mobile')]:
        page.set_viewport_size({'width':width,'height':height})
        page.screenshot(path=str(OUT/f'{name}.png'))
        positions=[x.bounding_box() for x in page.locator('#shortcuts .shortcut').all()]
        assert len(positions)==6
        assert len(set(round(x['y']) for x in positions))==2, name+' expected 3×2 dock'
        assert all(x['width']>64 for x in positions)
    assert errors==[], errors
    print('Visual QA PASS: desktop/tablet/mobile layout, Station menu, Ctrl+K palette, grouped results, accessibility, permissions fallback, no page exceptions.')
    browser.close()
