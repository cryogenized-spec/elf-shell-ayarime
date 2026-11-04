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
      window.__mock={closed:[],created:[],removed:[],discarded:[],grants:()=>origins,addTab:tab=>tabs.push(tab),updateTab:(id,patch)=>Object.assign(tabs.find(t=>t.id===id),patch),localStorage:local};
      let tabs=[{id:101,url:'https://example.org/abc',active:true,pinned:false,audible:false,incognito:false,windowId:1,index:0},
                {id:102,url:'https://example.org/abc',active:false,pinned:false,audible:false,incognito:false,windowId:1,index:1},
                {id:103,url:'https://example.org/other',active:false,pinned:false,audible:false,incognito:false,windowId:1,index:2},
                {id:104,url:'https://example.org/abc',active:false,pinned:false,audible:false,incognito:false,windowId:2,index:0},
                {id:105,url:'https://example.org/inactive',active:false,pinned:false,audible:false,incognito:false,windowId:2,index:1,lastAccessed:Date.now()-3600000}];
      window.confirm=()=>true;
      window.browser={
        storage:{local:{get:async keys=>Object.fromEntries([].concat(keys).map(k=>[k,local[k]])),set:async value=>Object.assign(local,value)}},
        theme:{update:async()=>{}},
        permissions:{contains:async ({permissions,origins:orig})=>permissions?permissions.every(x=>x==='tabs'):orig.every(x=>origins.includes(x)),getAll:async()=>({permissions:['tabs'],origins}),remove:async obj=>{if(obj.origins){origins=origins.filter(x=>!obj.origins.includes(x));return true;}return false;},request:async()=>true},
        tabs:{query:async opts=>opts?.currentWindow?tabs.filter(t=>t.windowId===1):Number.isInteger(opts?.windowId)?tabs.filter(t=>t.windowId===opts.windowId):tabs,get:async id=>{const tab=tabs.find(t=>t.id===id);if(!tab)throw Error('Tab not found');return {...tab};},remove:async ids=>{window.__mock.removed.push(...ids);tabs=tabs.filter(t=>!ids.includes(t.id));},create:async data=>{window.__mock.created.push(data);return {...data,id:104}},discard:async ids=>{window.__mock.discarded.push(...ids);return [];}} ,
        runtime:{onInstalled:{addListener:()=>{}},onStartup:{addListener:()=>{}},onMessage:{addListener:listener=>{window.__sessionListener=listener;}},sendMessage:msg=>window.__sessionListener(msg)},
        sessions:{getRecentlyClosed:async()=>[]}
      };
      window.fetch=async()=>({ok:true,json:async()=>JSON.parse(%s)});
    })();'''%json.dumps((ROOT/'assets/ayarime-quotes.json').read_text())
    page.evaluate(mock)
    for source in ['background.js','newtab.js','memory.js','feeds.js']:
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
    # Denied site permission must never create a subscription.
    page.locator('#station-menu summary').click()
    page.locator('#feeds-toggle').click()
    page.locator('#feed-url').fill('https://news.example.org/rss')
    page.evaluate('() => {window.browser.permissions.request=async()=>false;}')
    page.locator('#feed-add-form button[type=submit]').click()
    page.wait_for_function("document.getElementById('feed-message').textContent.includes('declined')")
    assert page.evaluate('window.elfFeeds.snapshot().feeds.length')==0
    page.locator('#feed-close').click()
    page.locator('#station-menu summary').click()
    page.locator('#housekeeping-toggle').click()
    # A recovery reservation must succeed before any tab is removed.
    page.evaluate("() => {window.__savedSet=window.browser.storage.local.set;window.browser.storage.local.set=async()=>{throw Error('simulated recovery disk failure')};}")
    page.locator('#close-duplicates').click()
    page.wait_for_timeout(80)
    assert page.evaluate('window.__mock.removed.length')==0, 'never close a tab when the recovery record cannot be stored'
    page.evaluate('() => {window.browser.storage.local.set=window.__savedSet;}')
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
    # Codex P2: a new cleanup during a slow reopen must remain in the LIVE queue.
    page.evaluate('''() => {
      window.__mock.addTab({id:107,url:'https://example.org/other',active:false,pinned:false,audible:false,incognito:false,windowId:1,index:4});
      window.__originalCreateAgain=window.browser.tabs.create;
      window.__reopenGateTriggered=false;
      window.browser.tabs.create=async data=>{
        if(!window.__reopenGateTriggered){
          window.__reopenGateTriggered=true;
          await new Promise(resolve=>window.__releaseReopen=resolve);
        }
        return window.__originalCreateAgain(data);
      };
    }''')
    page.locator('#close-duplicates').click()
    page.evaluate('''() => {window.__reopenTask=reopenDuplicates();}''')
    page.wait_for_function('window.__reopenGateTriggered && typeof window.__releaseReopen === "function"')
    page.evaluate('''() => window.__mock.addTab({id:108,url:'https://example.org/other',active:false,pinned:false,audible:false,incognito:false,windowId:1,index:5})''')
    page.locator('#close-duplicates').click()
    page.evaluate('''() => window.__releaseReopen()''')
    page.evaluate('''async()=>await window.__reopenTask''')
    assert page.locator('#undo-duplicates').is_visible(), 'cleanup added during reopen must remain recoverable'
    assert page.evaluate('lastClosedDuplicates.length')==1
    page.locator('#undo-duplicates').click()
    assert page.locator('#undo-duplicates').is_hidden()
    # Codex P2: a tab that navigates during the recovery reservation must NOT
    # be closed. Its old duplicate URL can no longer recover the new page.
    page.evaluate('''() => {
      window.__mock.addTab({id:109,url:'https://example.org/abc',active:false,pinned:false,audible:false,incognito:false,windowId:1,index:5});
      window.__saveBeforeNavigation=window.browser.storage.local.set;
      window.__navigationRaceTriggered=false;
      window.browser.storage.local.set=async values=>{
        if(values['elfshell-duplicate-recovery-v1']&&!window.__navigationRaceTriggered){
          window.__navigationRaceTriggered=true;
          window.__mock.updateTab(109,{url:'https://example.org/important-work',active:true});
        }
        return window.__saveBeforeNavigation(values);
      };
    }''')
    page.locator('#close-duplicates').click()
    page.wait_for_function('window.__navigationRaceTriggered')
    assert 109 not in page.evaluate('window.__mock.removed'), 'navigation during recovery reservation must block tab removal'
    assert page.evaluate('window.__mock.localStorage["elfshell-duplicate-recovery-v1"].length')==0, 'unused recovery reservation must be acknowledged'
    # A moved tab must not be removed from another browser window.
    page.evaluate('''() => {
      window.__mock.addTab({id:110,url:'https://example.org/abc',active:false,pinned:false,audible:false,incognito:false,windowId:1,index:6});
      window.__navigationRaceTriggered=false;
      window.browser.storage.local.set=async values=>{
        if(values['elfshell-duplicate-recovery-v1']&&!window.__navigationRaceTriggered){
          window.__navigationRaceTriggered=true;
          window.__mock.updateTab(110,{windowId:2});
        }
        return window.__saveBeforeNavigation(values);
      };
    }''')
    page.locator('#close-duplicates').click()
    page.wait_for_function('window.__navigationRaceTriggered')
    assert 110 not in page.evaluate('window.__mock.removed'), 'window move during recovery reservation must block tab removal'
    page.evaluate('() => {window.browser.storage.local.set=window.__saveBeforeNavigation;}')
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
