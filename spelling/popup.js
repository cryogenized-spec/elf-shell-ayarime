"use strict";
const $=id=>document.getElementById(id);
let tab=null,origin=null,scriptId=null,active=false;
const idForOrigin=url=>"elfspell-"+[...url].map(ch=>ch.charCodeAt(0).toString(16).padStart(2,"0")).join("");
function setStatus(message){$("status").textContent=message;}
async function readState(){
  const registrations=await browser.scripting.getRegisteredContentScripts();
  const data=await browser.storage.local.get("elfshell:browser-integration:v1");
  const mode=data["elfshell:browser-integration:v1"]?.spellMode||"sites";
  const global=mode==="all"&&registrations.some(item=>item.id==="elfspell-global-v1");
  active=registrations.some(item=>item.id===scriptId);
  if(global||mode==="off"){
    $("toggle").textContent=global?"Global spelling enabled in Station":"Firefox native spelling only";
    $("toggle").disabled=true;
    setStatus(global?"Change browser-wide preferences in STATION → CONFIGURE STATION.":
      "Enable per-site or browser-wide spelling from STATION → CONFIGURE STATION.");
    return;
  }
  $("toggle").textContent=active?"Disable spelling on this site":"Enable spelling on this site";
  $("toggle").disabled=false;
}
async function init(){
  try{
    [tab]=await browser.tabs.query({active:true,currentWindow:true});
    const url=new URL(tab?.url);
    if(url.protocol!=="https:")throw Error("Only HTTPS websites are supported.");
    origin=url.origin;scriptId=idForOrigin(origin);
    $("site").textContent=origin;
    await readState();
  }catch(error){
    $("site").textContent="This page cannot use the spelling module.";
    setStatus(String(error.message||error));
  }
}
async function toggle(){
  $("toggle").disabled=true;setStatus("");
  try{
    if(active){
      // Unregister first, so a newly opened tab will not receive the
      // spelling content script while existing instances are being disabled.
      await browser.scripting.unregisterContentScripts({ids:[scriptId]});
      const matching=await browser.tabs.query({url:origin+"/*"});
      let unreachable=0;
      for(const other of matching){
        try{await browser.tabs.sendMessage(other.id,{type:"elfshell:spell:disable"});}
        catch{unreachable++;} // A page without an injected receiver is safe.
      }
      // Do not revoke the host grant: RSS subscriptions may share it.
      setStatus(unreachable?
        "Disabled for the site. Some tabs may need a reload to restore native spelling.":
        "Disabled across open site tabs. Host access is retained for other ELF//SHELL features.");
    }else{
      const permission=await browser.permissions.request({origins:[origin+"/*"]});
      if(!permission)throw Error("Site access was not granted.");
      const existing=await browser.scripting.getRegisteredContentScripts();
      if(!existing.some(item=>item.id===scriptId)){
        await browser.scripting.registerContentScripts([{
          id:scriptId,
          matches:[origin+"/*"],
          js:["spelling/content.js"],css:["spelling/content.css"],
          runAt:"document_idle",persistAcrossSessions:true
        }]);
      }
      // The active tab might navigate while its host grant is being
      // requested. Never inject into a different origin by cached tab ID.
      const live=await browser.tabs.get(tab.id);
      if(new URL(live.url||"").origin!==origin)
        throw Error("Tab changed site during permission setup. Spelling is enabled only for the original site.");
      await browser.scripting.insertCSS({target:{tabId:tab.id},files:["spelling/content.css"]});
      // The content script independently asks the background to authorize
      // its actual sender origin before reading any editor.
      await browser.scripting.executeScript({target:{tabId:tab.id},files:["spelling/content.js"]});
      setStatus("Enabled. Click a misspelled word in a supported rich-text editor.");
    }
    await readState();
  }catch(error){
    setStatus("Could not change spelling access: "+String(error.message||error));
    try{await readState();}catch{$("toggle").disabled=false;}
  }
}
$("toggle").addEventListener("click",toggle);
init();