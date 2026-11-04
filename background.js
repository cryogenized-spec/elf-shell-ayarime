"use strict";
// An extension and a static theme cannot occupy the same manifest.
// The Firefox theme API applies the palette dynamically.
const AYARIME_THEME = {
  images: { theme_frame: "assets/theme-frame.jpg" },
  colors: {
    frame: "#131723", tab_background_text: "#E9E5E5", toolbar: "#1B1A28",
    toolbar_text: "#EEE9E8", tab_selected: "#4C293C", tab_text: "#F7E8F2",
    tab_line: "#CA839F", toolbar_field: "#171924", toolbar_field_text: "#F0EBE8",
    toolbar_field_border: "#9E6982", toolbar_field_focus: "#1F2031",
    toolbar_field_text_focus: "#FFFFFF", toolbar_field_border_focus: "#D598B1",
    popup: "#191B27", popup_text: "#EDE8EA", popup_border: "#764862",
    button_background_hover: "#433248", button_background_active: "#683C55",
    sidebar: "#171923", sidebar_text: "#EEE9E8", sidebar_border: "#4A3A4D",
    ntp_background: "#111824", ntp_text: "#EDE7E8",
  }
};
async function applyTheme() {
  try { await browser.theme.update(AYARIME_THEME); }
  catch (error) { console.error("ELF//SHELL: could not apply theme", error); }
}
applyTheme();
browser.runtime.onInstalled.addListener(applyTheme);
browser.runtime.onStartup.addListener(applyTheme);

// Firefox extension pages share this background message handler. Serialize all
// changes to the saved-workspaces array here, rather than doing a read/write in
// each open new-tab page. One save or deletion finishes before the next reads.
const SESSIONS_KEY="elfshell-workspace-v3:field:sessions";
let sessionsChain=Promise.resolve();
function validSessionURL(raw){
  if(typeof raw!=="string"||raw.length>2048)return false;
  try {const url=new URL(raw);return url.protocol==="https:"||url.protocol==="http:";}catch{return false;}
}
function safeSessions(value){
  if(!Array.isArray(value))return [];
  return value.slice(0,10).map(item=>{
    if(!item||typeof item!=="object"||!Array.isArray(item.urls))return null;
    const name=typeof item.name==="string"?item.name.slice(0,48).trim():"";
    const urls=item.urls.slice(0,40).filter(validSessionURL);
    const created=typeof item.created==="string"?item.created.slice(0,30):"";
    return name&&urls.length?{name,created,urls}:null;
  }).filter(Boolean);
}
const sessionIdentity=item=>JSON.stringify([item.created,item.name,item.urls]);
async function changeSavedSessions(message){
  const stored=await browser.storage.local.get([SESSIONS_KEY,"elfshell-workspace-v3","elfshell-workspace-v2"]);
  // Upgrade users who have only the older combined workspace format: never
  // silently erase their previously saved tab sets on the first v0.5.4 save.
  const legacy=stored["elfshell-workspace-v3"]?.sessions||stored["elfshell-workspace-v2"]?.sessions;
  const current=safeSessions(stored[SESSIONS_KEY]===undefined?legacy:stored[SESSIONS_KEY]);
  let updated;
  switch(message.action){
    case "save": {
      const name=typeof message.name==="string"?message.name.slice(0,48).trim():"";
      const urls=Array.isArray(message.urls)?message.urls.slice(0,40).filter(validSessionURL):[];
      if(!name||!urls.length)throw Error("Workspace name and web URLs are required.");
      // Never silently drop an old workspace to make room for a new one.
      if(current.length>=10)throw Error("Ten workspaces already saved. Delete one before adding another.");
      // Millisecond timestamps can collide under rapid consecutive saves.
      // Make the complete identity unique so deleting one identical set never
      // inadvertently deletes a second saved set.
      let stamp=Date.now(),created=new Date(stamp).toISOString();
      while(current.some(item=>sessionIdentity(item)===JSON.stringify([created,name,urls]))){
        created=new Date(++stamp).toISOString();
      }
      updated=[{name,created,urls},...current];
      break;
    }
    case "delete": {
      const target=message.workspace;
      if(!target||typeof target!=="object")throw Error("Invalid workspace selection.");
      const identity=sessionIdentity(target);
      updated=current.filter(item=>sessionIdentity(item)!==identity);
      if(updated.length===current.length)throw Error("Workspace was already removed. Refresh the list.");
      break;
    }
    case "replace": {
      if(!Array.isArray(message.sessions)||message.sessions.length>10||
        safeSessions(message.sessions).length!==message.sessions.length)throw Error("Invalid imported workspaces.");
      updated=safeSessions(message.sessions);
      break;
    }
    default:throw Error("Unknown workspace operation.");
  }
  await browser.storage.local.set({[SESSIONS_KEY]:updated});
  return {ok:true,sessions:updated};
}
browser.runtime.onMessage.addListener(message=>{
  if(!message||message.type!=="elfshell:sessions:mutate:v1")return undefined;
  const operation=sessionsChain.then(()=>changeSavedSessions(message));
  // Keep the chain alive after a rejected storage write so the next action can retry.
  sessionsChain=operation.then(()=>undefined,()=>undefined);
  return operation.catch(error=>({ok:false,error:error?.message||"Workspace storage unavailable."}));
});
