"""Simulated Firefox WebExtensions API functional smoke test (not a Firefox certification)."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import json, re
ROOT=Path(__file__).resolve().parent.parent
html=(ROOT/'newtab.html').read_text()
html=re.sub(r'<script defer src="(?:newtab|memory|feeds)\.js"></script>', '', html)
html=html.replace('<link rel="stylesheet" href="styles.css">','<style>'+ (ROOT/'styles.css').read_text() +'</style>')
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1500,'height':900})
    page.set_content(html)
    mock='''(() => {
      const local={};let origins=['https://example.org/*'];
      window.__mock={closed:[],created:[],removed:[],discarded:[],grants:()=>origins,addTab:tab=>tabs.push(tab)};
      let tabs=[{id:101,url:'https://example.org/abc',active:true,pinned:false,audible:false,incognito:false,windowId:1,index:0},
                {id:102,url:'https://example.org/abc',active:false,pinned:false,audible:false,incognito:false,windowId:1,index:1},
                {id:103,url:'https://example.org/other',active:false,pinned:false,audible:false,incognito:false,windowId:1,index:2},
                {id:104,url:'https://example.org/abc',active:false,pinned:false,audible:false,incognito:false,windowId:2,index:0},
                {id:105,url:'https://example.org/inactive',active:false,pinned:false,audible:false,incognito:false,windowId:2,index:1,lastAccessed:Date.now()-3600000}];
      window.confirm=()=>true;
      window.browser={
        storage:{local:{get:async keys=>Object.fromEntries([].concat(keys).map(k=>[k,local[k]])),set:async value=>Object.assign(local,value)}},
        permissions:{contains:async ({permissions,origins:orig})=>permissions?permissions.every(x=>x==='tabs'):orig.every(x=>origins.includes(x)),getAll:async()=>({permissions:['tabs'],origins}),remove:async obj=>{if(obj.origins){origins=origins.filter(x=>!obj.origins.includes(x));return true;}return false;},request:async()=>true},
        tabs:{query:async opts=>opts?.currentWindow?tabs.filter(t=>t.windowId===1):tabs,remove:async ids=>{window.__mock.removed.push(...ids);tabs=tabs.filter(t=>!ids.includes(t.id));},create:async data=>{window.__mock.created.push(data);return {...data,id:104}},discard:async ids=>{window.__mock.discarded.push(...ids);return [];}} ,
        runtime:{},
        sessions:{getRecentlyClosed:async()=>[]}
      };
      window.fetch=async()=>({ok:true,json:async()=>JSON.parse(%s)});
    })();'''%json.dumps((ROOT/'assets/ayarime-quotes.json').read_text())
    page.evaluate(mock)
    for source in ['newtab.js','memory.js','feeds.js']:
        page.add_script_tag(content=(ROOT/source).read_text())
    page.locator('#station-menu summary').click()
    page.locator('#permissions-toggle').click()
    page.locator('.permission-host-row').wait_for()
    assert 'example.org' in page.locator('.permission-host-row').inner_text()
    page.get_by_role('button',name='Revoke access to https://example.org/*').click()
    page.wait_for_timeout(100)
    assert page.locator('.permission-host-row').count()==0
    assert page.evaluate('window.__mock.grants().length')==0
    page.locator('#close-access').click()
    page.locator('#station-menu summary').click()
    page.locator('#housekeeping-toggle').click()
    page.locator('#close-duplicates').click()
    assert page.evaluate('window.__mock.removed.join(",")')=='102', 'only same-window duplicates may be removed'
    assert page.locator('#undo-duplicates').is_visible()
    # Even failed reopen attempts remain retryable, rather than losing recovery metadata.
    page.evaluate('() => { window.__originalCreate=window.browser.tabs.create;window.browser.tabs.create=async()=>{throw Error("temporarily unavailable")}; }')
    page.locator('#undo-duplicates').click()
    page.wait_for_timeout(100)
    assert page.locator('#undo-duplicates').is_visible(), 'undo must stay available after a failed attempt'
    # A second cleanup must append, not discard, the first failed recovery record.
    page.evaluate('''() => window.__mock.addTab({id:106,url:'https://example.org/other',active:false,pinned:false,audible:false,incognito:false,windowId:1,index:3})''')
    page.locator('#close-duplicates').click()
    assert '106' in page.evaluate('window.__mock.removed.join(",")')
    page.evaluate('() => { window.browser.tabs.create=window.__originalCreate; }')
    page.locator('#undo-duplicates').click()
    page.wait_for_timeout(100)
    assert page.evaluate('window.__mock.created.length')==2
    assert set(page.evaluate('window.__mock.created.map(x=>x.url)'))=={'https://example.org/abc','https://example.org/other'}
    assert page.locator('#undo-duplicates').is_hidden()
    page.locator('#close-housekeeping').click()
    # Persist must not misreport success when Firefox local storage rejects a write.
    page.evaluate('() => { window.browser.storage.local.set=async()=>{throw Error("simulated disk or quota error")}; }')
    page.locator('#focus-input').fill('fail-save probe')
    page.wait_for_timeout(650)
    assert page.locator('#note-status').inner_text()=='SAVE ERROR'
    assert page.locator('#archive-status').inner_text()=='SAVE ERROR'
    # A failed saved-workspace operation must not clear the name or announce success.
    page.evaluate('() => {document.getElementById("workspace-name").value="Retry this workspace";}')
    page.evaluate('() => saveWorkspace()')
    assert 'Save failed' in page.locator('#sessions-message').inner_text()
    assert page.locator('#workspace-name').input_value()=='Retry this workspace'
    # Importing settings must similarly report the rejected write, not success.
    page.evaluate('''async () => {const backup={...state,format:'elfshell-settings',version:5};await importJSON({size:128,text:async()=>JSON.stringify(backup)});}''')
    assert 'Import rejected' in page.locator('#settings-message').inner_text()
    assert 'Settings imported successfully' not in page.locator('#settings-message').inner_text()
    print('Mock Firefox API QA PASS: per-origin permission ledger/revocation, cross-window duplicate safety, multi-batch recovery, and truthful failed workspace/import saves.')
    browser.close()
