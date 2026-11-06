"use strict";
/* Action popup only opens a stable extension tab. Permission prompts must
   never depend on a transient toolbar popup remaining alive. */
const $=id=>document.getElementById(id);
const params=new URL(location.href).searchParams;
const manager=params.has("target")&&params.has("site");
let tab=null,origin=null,scriptId=null,active=false;
const idForOrigin=url=>"elfspell-"+[...url].map(ch=>ch.charCodeAt(0).toString(16).padStart(2,"0")).join("");
const setStatus=message=>{$("status").textContent=message;};
function validSite(value) {
  if(typeof value!=="string"||value.length>2048)throw Error("Invalid website");
  const url=new URL(value);
  if(url.protocol!=="https:"||url.origin!==value)throw Error("Only HTTPS website origins are supported");
  return url.origin;
}
async function readState() {
  const [registrations,stored]=await Promise.all([
    browser.scripting.getRegisteredContentScripts(),
    browser.storage.local.get("elfshell:browser-integration:v1")
  ]);
  const mode=stored["elfshell:browser-integration:v1"]?.spellMode||"sites";
  const global=mode==="all"&&registrations.some(item=>item.id==="elfspell-global-v1");
  active=registrations.some(item=>item.id===scriptId);
  if(mode==="off"||global) {
    $("toggle").textContent=global?"Browser-wide spelling enabled":"Firefox native spelling enabled";
    $("toggle").disabled=true;
    setStatus("To change browser-wide settings, open Ayarime → STATION → CONFIGURE STATION.");
    return;
  }
  $("toggle").textContent=manager?
    (active?"DISABLE SPELLING FOR THIS SITE":"ENABLE SPELLING FOR THIS SITE"):
    "OPEN SITE SPELLING CONTROLS";
  $("toggle").disabled=false;
}
async function init() {
  try {
    if(manager) {
      const id=Number(params.get("target"));
      if(!Number.isSafeInteger(id)||id<=0)throw Error("Invalid target tab");
      tab={id};
      origin=validSite(params.get("site"));
      document.body.classList.add("spelling-manager");
      document.title="Ayarime — Website spelling controls";
    } else {
      [tab]=await browser.tabs.query({active:true,currentWindow:true});
      if(!tab||!Number.isInteger(tab.id))throw Error("No website tab selected");
      origin=validSite(new URL(tab.url).origin);
    }
    scriptId=idForOrigin(origin);
    $("site").textContent=origin;
    await readState();
    if(manager)setStatus("This page stays open while Firefox asks for permission.");
  } catch(error) {
    $("site").textContent="This tab cannot use the spelling module.";
    $("toggle").disabled=true;
    setStatus(String(error.message||error));
  }
}
async function toggle() {
  if(!tab||!origin)return;
  if(!manager) {
    // The popup may close immediately after opening a tab. This is intentional.
    const url=browser.runtime.getURL("spelling/popup.html")+
      "?target="+encodeURIComponent(tab.id)+"&site="+encodeURIComponent(origin);
    try{await browser.tabs.create({url});}
    catch(error){setStatus("Could not open spelling controls: "+String(error.message||error));}
    return;
  }
  const wasActive=active;
  let permissionRequest=null;
  try {
    // Required Firefox gesture: invoke request directly in this click handler,
    // before ANY async await. Unlike toolbar popups, this extension page stays.
    if(!wasActive)permissionRequest=browser.permissions.request({origins:[origin+"/*"]});
  }catch(error) {
    setStatus("Firefox site permission prompt failed: "+String(error.message||error));
    return;
  }
  $("toggle").disabled=true;
  setStatus(wasActive?"Disabling website spelling…":"Waiting for Firefox website access approval…");
  try {
    if(wasActive) {
      await browser.scripting.unregisterContentScripts({ids:[scriptId]});
      // Send by tab ID even if permissions no longer expose tab URL.
      const tabs=await browser.tabs.query({});
      for(const t of tabs) {
        if(!Number.isInteger(t.id)||t.incognito)continue;
        try{await browser.tabs.sendMessage(t.id,{type:"elfshell:spell:revalidate"});}
        catch{}
      }
      setStatus("Spelling disabled for this site. Native spelling restored; any separate RSS grant remains.");
    } else {
      if(!await permissionRequest){
        setStatus("Firefox site permission was declined; no spelling was enabled.");
        return;
      }
      const live=await browser.tabs.get(tab.id);
      if(new URL(live.url||"").origin!==origin)
        throw Error("The original website tab has navigated elsewhere. No script was injected.");
      const stored=await browser.storage.local.get("elfshell:browser-integration:v1");
      if(stored["elfshell:browser-integration:v1"]?.spellMode==="off")
        throw Error("Station is set to Firefox native spelling only.");
      const existing=await browser.scripting.getRegisteredContentScripts();
      if(!existing.some(item=>item.id===scriptId))
        await browser.scripting.registerContentScripts([{
          id:scriptId,matches:[origin+"/*"],
          js:["spelling/content.js"],css:["spelling/content.css"],
          runAt:"document_idle",persistAcrossSessions:true
        }]);
      // Permission changes can arrive in Firefox content processes after the
      // permission promise resolves. Retry only the two immediate injections;
      // the registered content script always handles later navigations.
      async function inject(operation,fn){
        let last=null;
        for(let attempt=0;attempt<3;attempt++){
          try{
            const result=await fn();
            if(Array.isArray(result)){
              const error=result.find(item=>item?.error)?.error;
              if(error)throw Error(String(error.message||error));
            }
            return;
          }catch(error){
            last=error;
            if(attempt<2)
              await new Promise(resolve=>setTimeout(resolve,120*(attempt+1)));
          }
        }
        throw Error(operation+": "+String(last?.message||last));
      }
      try{
        await inject("CSS injection",()=>browser.scripting.insertCSS({
          target:{tabId:tab.id},files:["spelling/content.css"]}));
        await inject("Script injection",()=>browser.scripting.executeScript({
          target:{tabId:tab.id},files:["spelling/content.js"]}));
        setStatus("Enabled for this site. Left-click a misspelled word in a compatible editor.");
      }catch(error){
        // Never falsely claim the current page is active: registration is
        // durable for the next navigation, but this page needs user reload.
        setStatus("Spelling registered, but could not activate this open tab ("+
          String(error.message||error)+"). Reload the website tab to activate it.");
      }
    }
  } catch(error){
    setStatus("Website spelling could not be updated: "+String(error.message||error));
  } finally {
    try {
      const note=$("status").textContent;
      await readState();
      // Keep operation-specific diagnostics visible instead of generic status.
      if(note)setStatus(note);
    }catch(error){$("toggle").disabled=false;}
  }
}
$("toggle").addEventListener("click",toggle);
init();
