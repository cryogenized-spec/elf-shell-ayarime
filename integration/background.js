"use strict";
/* Optional spelling on approved HTTPS sites only. The station requests
   permissions from a real user click; background NEVER requests grants. */
(() => {
  const KEY="elfshell:browser-integration:v1";
  const SCOPE="https://*/*";
  const SPELL_ID="elfspell-global-v1";
  const LEGACY_CURSOR_ID="elfshell-cursors-global-v1";
  const sourceUrl=browser.runtime.getURL("newtab.html");
  const clean=value=>({spellMode:["sites","all","off"].includes(value?.spellMode)?value.spellMode:"sites"});
  const read=async()=>clean((await browser.storage.local.get(KEY))[KEY]);
  const granted=()=>browser.permissions.contains({origins:[SCOPE]});
  let chain=Promise.resolve();
  function queue(fn) {
    const next=chain.then(fn);
    chain=next.catch(e=>{console.warn("ELF//SHELL integration reconciliation failed",e);});
    return next;
  }
  async function reconcile(inject=false) {
    const modes=await read(),allowed=await granted();
    const old=await browser.scripting.getRegisteredContentScripts();
    // An obsolete beta may have installed the experimental website cursor
    // script. Remove it, without touching dashboard-only pointer settings.
    if(old.some(s=>s.id===LEGACY_CURSOR_ID))
      await browser.scripting.unregisterContentScripts({ids:[LEGACY_CURSOR_ID]});
    const existing=old.some(s=>s.id===SPELL_ID);
    if(allowed&&modes.spellMode==="all"&&!existing) {
      await browser.scripting.registerContentScripts([{
        id:SPELL_ID,matches:[SCOPE],
        js:["spelling/content.js"],css:["spelling/content.css"],
        runAt:"document_idle",allFrames:false,persistAcrossSessions:true
      }]);
    } else if((!allowed||modes.spellMode!=="all")&&existing) {
      await browser.scripting.unregisterContentScripts({ids:[SPELL_ID]});
    }
    if(modes.spellMode==="off") {
      for(const entry of await browser.scripting.getRegisteredContentScripts()) {
        if(entry.id.startsWith("elfspell-")&&entry.id!==SPELL_ID)
          await browser.scripting.unregisterContentScripts({ids:[entry.id]});
      }
    }
    // Permission revocation can make tab.url unavailable without optional
    // "tabs" permission. Revalidate every tab by ID, even without URL.
    const tabs=await browser.tabs.query({});
    for(const tab of tabs) {
      if(!Number.isInteger(tab.id))continue;
      if(inject&&!tab.incognito&&allowed&&modes.spellMode==="all"&&/^https:\/\//i.test(tab.url||"")) {
        try{await browser.scripting.insertCSS({
          target:{tabId:tab.id},files:["spelling/content.css"]});
          await browser.scripting.executeScript({
            target:{tabId:tab.id},files:["spelling/content.js"]});
        }catch { /* Browser-protected or navigated tabs retain native spelling. */ }
      }
      try{await browser.tabs.sendMessage(tab.id,{
        type:modes.spellMode==="off"?"elfshell:spell:disable":"elfshell:spell:revalidate"
      });}catch{}
      // Cleanup only: older beta cursor injection is never re-enabled.
      try{await browser.tabs.sendMessage(tab.id,{type:"elfshell:integration:cursor-sync"});}catch{}
    }
    return {modes,allowed};
  }
  browser.runtime.onMessage.addListener((message,sender)=>{
    if(!message||!["elfshell:integration:get","elfshell:integration:set"].includes(message.type))
      return undefined;
    if(sender.url!==sourceUrl)
      return Promise.resolve({ok:false,error:"Only Station can change browser integration"});
    if(message.type==="elfshell:integration:get")
      return queue(async()=>({ok:true,...await reconcile(false)}))
        .catch(e=>({ok:false,error:String(e.message||e)}));
    if(!["sites","all","off"].includes(message.modes?.spellMode))
      return Promise.resolve({ok:false,error:"Invalid spelling mode"});
    return queue(async()=>{
      const next=clean(message.modes),previous=await read();
      if(next.spellMode==="all"&&!await granted())
        return {ok:false,error:"Firefox has not granted optional HTTPS access"};
      try{
        await browser.storage.local.set({[KEY]:next});
        return {ok:true,...await reconcile(true)};
      }catch(e){
        try{await browser.storage.local.set({[KEY]:previous});await reconcile(true);}
        catch(rollback){console.error("ELF//SHELL integration rollback failed",rollback);}
        return {ok:false,error:String(e.message||e)};
      }
    }).catch(e=>({ok:false,error:String(e.message||e)}));
  });
  browser.permissions.onRemoved.addListener(()=>{queue(()=>reconcile(false));});
  browser.permissions.onAdded.addListener(()=>{queue(()=>reconcile(false));});
  browser.runtime.onStartup.addListener(()=>{queue(()=>reconcile(false));});
  browser.runtime.onInstalled.addListener(()=>{queue(()=>reconcile(false));});
  queue(()=>reconcile(false));
})();