"use strict";
/* Optional browser-wide integration for ordinary HTTPS pages.
   No host access is requested at installation or by the background script.
   Only a direct user action on the new-tab configuration page may prompt. */
(() => {
  const KEY="elfshell:browser-integration:v1";
  const SCOPE="https://*/*";
  const CURSOR_ID="elfshell-cursors-global-v1";
  const SPELL_ID="elfspell-global-v1";
  const DEFAULT=Object.freeze({cursorMode:"station",spellMode:"sites"});
  const clean=value=>({
    cursorMode:["station","all","off"].includes(value?.cursorMode)?value.cursorMode:DEFAULT.cursorMode,
    spellMode:["sites","all","off"].includes(value?.spellMode)?value.spellMode:DEFAULT.spellMode
  });
  const read=async()=>clean((await browser.storage.local.get(KEY))[KEY]);
  const granted=()=>browser.permissions.contains({origins:[SCOPE]});
  const entries=()=>browser.scripting.getRegisteredContentScripts();
  const sourceUrl=browser.runtime.getURL("newtab.html");
  let chain=Promise.resolve();
  function queue(fn) {
    const task=chain.then(fn);
    chain=task.catch(error=>console.error("ELF//SHELL integration:",error));
    return task;
  }
  async function registration(id,enable,definition) {
    const current=(await entries()).find(item=>item.id===id);
    if(current&&!enable)await browser.scripting.unregisterContentScripts({ids:[id]});
    else if(enable&&!current)await browser.scripting.registerContentScripts([definition]);
  }
  async function syncTabs(inject,allowed,modes) {
    // Never inspect page text or send it off-device. URLs only identify
    // eligible HTTPS tabs for an explicitly consented extension action.
    const tabs=await browser.tabs.query({});
    for(const tab of tabs) {
      if(!Number.isInteger(tab.id)||tab.incognito||!/^https:\/\//i.test(tab.url||""))continue;
      if(inject&&allowed) {
        if(modes.cursorMode==="all") {
          try { await browser.scripting.executeScript({
            target:{tabId:tab.id},files:["integration/cursors.js"]
          }); } catch {} // Restricted pages retain Firefox defaults.
        }
        if(modes.spellMode==="all") {
          try { await browser.scripting.insertCSS({
            target:{tabId:tab.id},files:["spelling/content.css"]
          }); } catch {}
          try { await browser.scripting.executeScript({
            target:{tabId:tab.id},files:["spelling/content.js"]
          }); } catch {}
        }
      }
      // Re-evaluate currently injected scripts when configuration changes,
      // even on tabs where their registrations have been removed.
      try { await browser.tabs.sendMessage(tab.id,{type:"elfshell:integration:cursor-sync"}); } catch {}
      try { await browser.tabs.sendMessage(tab.id,{
        type:modes.spellMode==="off"?"elfshell:spell:disable":"elfshell:spell:revalidate"
      }); } catch {}
    }
  }
  async function reconcile(inject=false) {
    const modes=await read(),allowed=await granted();
    await registration(CURSOR_ID,allowed&&modes.cursorMode==="all",{
      id:CURSOR_ID,matches:[SCOPE],js:["integration/cursors.js"],
      runAt:"document_idle",allFrames:false,persistAcrossSessions:true
    });
    await registration(SPELL_ID,allowed&&modes.spellMode==="all",{
      id:SPELL_ID,matches:[SCOPE],
      js:["spelling/content.js"],css:["spelling/content.css"],
      runAt:"document_idle",allFrames:false,persistAcrossSessions:true
    });
    if(modes.spellMode==="off") {
      // "Firefox native only" must also disable older per-site registrations.
      for(const item of await entries()) {
        if(item.id.startsWith("elfspell-")&&item.id!==SPELL_ID) {
          await browser.scripting.unregisterContentScripts({ids:[item.id]});
        }
      }
    }
    await syncTabs(inject,allowed,modes);
    return {modes,allowed};
  }
  browser.runtime.onMessage.addListener((message,sender)=>{
    if(!message||typeof message.type!=="string"||
       !message.type.startsWith("elfshell:integration:"))return undefined;
    if(message.type==="elfshell:integration:cursor-allowed") {
      // A content script needs a fresh confirmation after permission removal.
      return (async()=>{
        if(!sender.tab?.id||sender.frameId!==0||!sender.url)return {allowed:false};
        let url,tab;
        try {url=new URL(sender.url);tab=new URL(sender.tab.url||"");}
        catch {return {allowed:false};}
        if(url.protocol!=="https:"||url.origin!==tab.origin||sender.tab.incognito)
          return {allowed:false};
        const modes=await read();
        const enabled=(await entries()).some(s=>s.id===CURSOR_ID&&
          Array.isArray(s.matches)&&s.matches.includes(SCOPE));
        return {allowed:modes.cursorMode==="all"&&enabled&&await granted()};
      })().catch(()=>({allowed:false}));
    }
    // No arbitrary website content script can change integration preferences.
    if(sender.url!==sourceUrl)return Promise.resolve({ok:false,error:"Only Station configuration can change integration"});
    if(message.type==="elfshell:integration:get") {
      return (async()=>({ok:true,...await reconcile(false)}))().catch(e=>({ok:false,error:String(e.message||e)}));
    }
    if(message.type==="elfshell:integration:set") {
      if(!message.modes||typeof message.modes!=="object"||
         !["station","all","off"].includes(message.modes.cursorMode)||
         !["sites","all","off"].includes(message.modes.spellMode))
        return Promise.resolve({ok:false,error:"Invalid integration mode"});
      return queue(async()=>{
        const next=clean(message.modes),previous=await read();
        if((next.cursorMode==="all"||next.spellMode==="all")&&!await granted())
          return {ok:false,error:"Firefox has not granted optional all-HTTPS access"};
        try {
          await browser.storage.local.set({[KEY]:next});
          const status=await reconcile(true);
          return {ok:true,...status};
        }catch(error) {
          // Never report a successful configuration that was not applied.
          try {await browser.storage.local.set({[KEY]:previous});await reconcile(true);}
          catch(e){console.error("ELF//SHELL integration rollback failed:",e);}
          return {ok:false,error:"Could not activate browser integration: "+String(error.message||error)};
        }
      });
    }
    return Promise.resolve({ok:false,error:"Unknown integration command"});
  });
  browser.permissions.onRemoved.addListener(()=>{queue(()=>reconcile(false));});
  browser.permissions.onAdded.addListener(()=>{queue(()=>reconcile(false));});
  browser.runtime.onStartup.addListener(()=>{queue(()=>reconcile(false));});
  browser.runtime.onInstalled.addListener(()=>{queue(()=>reconcile(false));});
  queue(()=>reconcile(false));
})();