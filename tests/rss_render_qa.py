"""Browser DOM parser and overlapping RSS render regression (not Firefox certification)."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import json, re
ROOT=Path(__file__).resolve().parent.parent
html=(ROOT/'newtab.html').read_text(encoding='utf-8')
html=re.sub(r'<script defer src="(?:newtab|memory|feeds)\.js"></script>', '', html)
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
    page=browser.new_page()
    page.set_content(html)
    page.evaluate('''() => {
        const saved={};
        window.browser={
          storage:{local:{get:async k=>Object.fromEntries([].concat(k).map(key=>[key,saved[key]])),set:async x=>Object.assign(saved,x)}},
          permissions:{contains:async()=>new Promise(resolve=>setTimeout(()=>resolve(false),40))}
        };
    }''')
    source=(ROOT/'feeds.js').read_text(encoding='utf-8')
    source=source.replace('  if(typeof module!=="undefined"',
        '  window.__feedParserForQA = parseFeedXml;\n  if(typeof module!=="undefined"')
    page.add_script_tag(content=source)
    rss='''<rss xmlns:atom="http://www.w3.org/2005/Atom" version="2.0"><channel>
      <item><title>No article link</title><atom:link rel="self" href="https://feed.example.org/rss"/></item>
      <item><title>Article</title><atom:link rel="self" href="https://feed.example.org/rss"/><link>https://example.org/article</link></item>
    </channel></rss>'''
    items=page.evaluate('(xml)=>window.__feedParserForQA(xml,"https://feed.example.org/rss")',rss)
    assert len(items)==1, items
    assert items[0]['url']=='https://example.org/article', items
    atom='''<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Atom entry</title>
      <link rel="self" href="https://feed.example.org/feed"/>
      <link rel="alternate" href="https://example.org/post"/></entry></feed>'''
    items=page.evaluate('(xml)=>window.__feedParserForQA(xml,"https://feed.example.org/atom")',atom)
    assert len(items)==1 and items[0]['url']=='https://example.org/post',items
    self_only='''<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>No story</title>
      <link rel="self" href="https://feed.example.org/feed"/></entry></feed>'''
    assert page.evaluate('(xml)=>window.__feedParserForQA(xml,"https://feed.example.org/atom")',self_only)==[]
    # Interleave two renders. Old permission checks must not append duplicate
    # rows after the newer preferences have been applied.
    one={'enabled':True,'interval':30,'feeds':[{'url':'https://first.org/feed','title':'First','group':'TECH','enabled':True},{'url':'https://second.org/feed','title':'Second','group':'TECH','enabled':True}]}
    two={'enabled':True,'interval':30,'feeds':[{'url':'https://third.org/feed','title':'Third','group':'TECH','enabled':True}]}
    result=page.evaluate('''async values=>{
      const [a,b]=values;
      const older=window.elfFeeds.applySnapshot(a);
      const newer=window.elfFeeds.applySnapshot(b);
      await Promise.all([older,newer]);
      return [...document.querySelectorAll('#feed-subscriptions .feed-subscription strong')].map(x=>x.textContent);
    }''',[one,two])
    assert result==['Third'],result
    print('RSS browser QA PASS: Atom namespace vs RSS article links, missing-link rejection, overlapping asynchronous renders.');
    browser.close()
