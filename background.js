"use strict";
// An extension and a static theme cannot occupy the same manifest.
// The Firefox theme API applies the palette dynamically.
const AYARIME_THEME = {
  images: { theme_frame: "assets/theme-frame.jpg" },
  colors: {
    frame: "#131723", frame_inactive: "#10141d", tab_background_text: "#E9E5E5", toolbar: "#1B1A28",
    toolbar_text: "#EEE9E8", tab_selected: "#4C293C", tab_text: "#F7E8F2",
    tab_line: "#CA839F", toolbar_field: "#171924", toolbar_field_text: "#F0EBE8",
    toolbar_field_border: "#9E6982", toolbar_field_focus: "#1F2031",
    toolbar_field_text_focus: "#FFFFFF", toolbar_field_border_focus: "#D598B1",
    popup: "#23232e", popup_text: "#f3eef1", popup_border: "#62576b",
    popup_highlight: "#514455", popup_highlight_text: "#fff9fc",
    button_background_hover: "#433248", button_background_active: "#683C55",
    sidebar: "#171923", sidebar_text: "#EEE9E8", sidebar_border: "#4A3A4D",
    sidebar_highlight: "#514455", sidebar_highlight_text: "#fff9fc",
    ntp_background: "#111824", ntp_text: "#EDE7E8",
  },
  // Firefox uses this for supported browser chrome, including context-menu
  // light/dark selection. Native GTK window widgets remain OS-controlled.
  properties: { color_scheme: "dark", content_color_scheme: "system" }
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
// Recovery metadata is retained across new-tab navigation and browser restarts.
// It contains URLs, which can include private query parameters, and is never
// transmitted off the machine. This queue is serialized just like saved sessions
// so multiple open dashboard tabs cannot lose each other's recovery entries.
const RECOVERY_KEY="elfshell-duplicate-recovery-v1";
let recoveryChain=Promise.resolve();
let recoverySerial=0;
function safeRecovery(value){
  if(!Array.isArray(value))return [];
  return value.slice(0,100).map(item=>{
    if(!item||typeof item!=="object"||typeof item.id!=="string"||
       item.id.length>80||!validSessionURL(item.url))return null;
    const windowId=Number.isInteger(item.windowId)&&item.windowId>=1?item.windowId:undefined;
    const index=Number.isInteger(item.index)&&item.index>=0&&item.index<100000?item.index:undefined;
    return {id:item.id,url:item.url,windowId,index};
  }).filter(Boolean);
}

function eligibleDuplicate(tab,item,peers){
  return !!tab&&tab.id===item.tabId&&tab.url===item.url&&
    tab.windowId===item.windowId&&!tab.active&&!tab.pinned&&
    !tab.audible&&!tab.incognito&&
    peers.some(peer=>peer.id!==item.tabId&&peer.url===item.url&&
      peer.windowId===item.windowId&&!peer.incognito);
}
async function mutateRecovery(message){
  const stored=await browser.storage.local.get(RECOVERY_KEY);
  const pending=safeRecovery(stored[RECOVERY_KEY]);
  if(message.action==="list")return {ok:true,entries:pending};
  let updated=pending,added=[];
  if(message.action==="closeDuplicate"){
    const item=message.item;
    if(!item||!Number.isInteger(item.tabId)||item.tabId<1||
      !validSessionURL(item.url)||!Number.isInteger(item.windowId)||item.windowId<1||
      !Number.isInteger(item.index)||item.index<0||item.index>=100000){
      throw Error("Invalid duplicate-tab cleanup request.");
    }
    // The entire reservation, recheck and tab close is serialised with
    // history clearing. No other dashboard can remove its record mid-close.
    const before=await browser.tabs.get(item.tabId);
    const peers=await browser.tabs.query({windowId:item.windowId});
    if(!eligibleDuplicate(before,item,peers)){
      return {ok:true,entries:pending,added:[],closed:false,skipped:true};
    }
    if(pending.length>=100){
      throw Error("100 recovery addresses already stored. Reopen or clear some before closing more tabs.");
    }
    let id;
    do{id=Date.now().toString(36)+"-"+(++recoverySerial).toString(36);}
    while(pending.some(x=>x.id===id));
    const reserved={id,url:item.url,windowId:item.windowId,index:item.index};
    updated=[...pending,reserved];
    // Never close unless the recoverable URL was first saved durably.
    await browser.storage.local.set({[RECOVERY_KEY]:updated});
    try{
      const live=await browser.tabs.get(item.tabId);
      const currentPeers=await browser.tabs.query({windowId:item.windowId});
      // The target itself must also appear, unchanged and eligible, in
      // the FINAL query result. A tab can navigate or change windows while
      // the query is pending, making the earlier tabs.get snapshot stale.
      const queriedTarget=currentPeers.find(tab=>tab.id===item.tabId);
      // One final read narrows the remaining query-to-removal race. Firefox
      // has no conditional remove-by-id-and-URL API, so no check can make
      // removal fully atomic with unrelated browser navigation.
      const finalTarget=await browser.tabs.get(item.tabId);
      if(!eligibleDuplicate(live,item,currentPeers)||
         !eligibleDuplicate(queriedTarget,item,currentPeers)||
         !eligibleDuplicate(finalTarget,item,currentPeers)){
        // Changed or protected while we saved the URL: never close it.
        // If discarding the unused record fails, retain the harmless entry.
        try{
          await browser.storage.local.set({[RECOVERY_KEY]:pending});
          return {ok:true,entries:pending,added:[],closed:false,skipped:true};
        }catch(error){
          console.warn("Could not discard unused recovery address",error);
          return {ok:true,entries:updated,added:[reserved],closed:false,skipped:true};
        }
      }
    }catch(error){
      console.warn("Could not recheck duplicate tab: not closing",error);
      return {ok:true,entries:updated,added:[reserved],closed:false,skipped:true};
    }
    try{await browser.tabs.remove([item.tabId]);}
    catch(error){
      throw Error("Tab closure failed or cannot be confirmed; the recovery address remains saved. "+error.message);
    }
    return {ok:true,entries:updated,added:[reserved],closed:true,skipped:false};
  }
  if(message.action==="append"){
    if(!Array.isArray(message.entries)||!message.entries.length||message.entries.length>100||
       pending.length+message.entries.length>100)throw Error("100 recovery addresses are already stored. Reopen or clear some before closing more tabs.");
    added=message.entries.map(item=>{
      if(!item||!validSessionURL(item.url)||
         !Number.isInteger(item.windowId)||item.windowId<1||
         !Number.isInteger(item.index)||item.index<0||item.index>=100000)throw Error("Unsafe duplicate recovery record.");
      let id;
      do{id=Date.now().toString(36)+"-"+(++recoverySerial).toString(36);}while(pending.some(x=>x.id===id)||added.some(x=>x.id===id));
      return {id,url:item.url,windowId:item.windowId,index:item.index};
    });
    updated=[...pending,...added];
  }else if(message.action==="complete"||message.action==="clear"){
    // Clear only explicitly confirmed IDs, never newer records added by
    // a background cleanup during the user's confirmation dialog.
    if(!Array.isArray(message.ids)||message.ids.length>100||
       message.ids.some(id=>typeof id!=="string"||id.length>80)){
      throw Error("Invalid recovery record selection.");
    }
    const selected=new Set(message.ids);
    updated=pending.filter(item=>!selected.has(item.id));
  }else throw Error("Unknown recovery operation.");
  await browser.storage.local.set({[RECOVERY_KEY]:updated});
  return {ok:true,entries:updated,added};
}

// Feed subscriptions and caches are also shared by multiple new-tab instances.
// Serialize edits per URL in the background to prevent stale snapshots from
// dropping other dashboards' additions or cached headlines.
const RSS_PREFS_KEY="elfshell-rss-settings-v1";
const RSS_CACHE_KEY="elfshell-rss-cache-v1";
let rssChain=Promise.resolve();
function publicFeedURL(raw){
  if(typeof raw!=="string"||raw.length>2048)return null;
  try{
    const u=new URL(raw),host=u.hostname.toLowerCase();
    if(u.protocol!=="https:"||!host.includes(".")||host.endsWith(".")||host.startsWith("[")||u.username||u.password||u.port)return null;
    if(/^\d+\.\d+\.\d+\.\d+$/.test(host))return null;
    if(["localhost","local","lan","internal","home.arpa","test","invalid","example"].some(s=>host===s||host.endsWith("."+s)))return null;
    if(host.split(".").some(label=>!/^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/.test(label)))return null;
    return u.href;
  }catch{return null;}
}
function safeRSSFeed(value){
  if(!value||typeof value!=="object"||!publicFeedURL(value.url))return null;
  const title=typeof value.title==="string"?value.title.slice(0,72).trim():"";
  const group=typeof value.group==="string"?value.group.slice(0,28).trim():"";
  return {url:publicFeedURL(value.url),title:title||new URL(value.url).hostname,group:group||"GENERAL",enabled:value.enabled!==false};
}
function safeRSSPrefs(value){
  const base={enabled:true,interval:30,feeds:[]};
  if(!value||typeof value!=="object")return base;
  const list=Array.isArray(value.feeds)?value.feeds:[],seen=new Set();
  for(const item of list.slice(0,32)){
    const feed=safeRSSFeed(item);
    if(feed&&!seen.has(feed.url)){seen.add(feed.url);base.feeds.push(feed);}
  }
  return {enabled:value.enabled!==false,interval:[15,30,60,180,360].includes(value.interval)?value.interval:30,feeds:base.feeds};
}
function safeRSSCacheEntry(value){
  if(!value||typeof value!=="object")return null;
  const items=Array.isArray(value.items)?value.items.slice(0,36).map(x=>{
    if(!x||typeof x.title!=="string"||typeof x.url!=="string"||x.url.length>2048)return null;
    try{const u=new URL(x.url);if(!["https:","http:"].includes(u.protocol)||u.username||u.password)return null;}catch{return null;}
    return {title:x.title.slice(0,240),url:x.url,date:Number.isFinite(x.date)?x.date:0};
  }).filter(Boolean):[];
  return {items,checkedAt:Number.isFinite(value.checkedAt)?value.checkedAt:0,attemptedAt:Number.isFinite(value.attemptedAt)?value.attemptedAt:0,error:typeof value.error==="string"?value.error.slice(0,150):""};
}
async function mutateRSS(message){
  const stored=await browser.storage.local.get([RSS_PREFS_KEY,RSS_CACHE_KEY]);
  const prefs=safeRSSPrefs(stored[RSS_PREFS_KEY]);
  const cache={};
  const oldCache=stored[RSS_CACHE_KEY];
  if(oldCache&&typeof oldCache==="object"&&!Array.isArray(oldCache)){
    for(const feed of prefs.feeds){const entry=safeRSSCacheEntry(oldCache[feed.url]);if(entry)cache[feed.url]=entry;}
  }
  let added=0;
  const target=message.url;
  if(message.action==="add"){
    const f=safeRSSFeed(message.feed);
    if(!f)throw Error("Invalid public HTTPS feed address.");
    if(prefs.feeds.some(x=>x.url===f.url))throw Error("Already subscribed to this publication.");
    if(prefs.feeds.length>=32)throw Error("Subscription limit reached.");
    prefs.feeds.push(f);added=1;
  }else if(message.action==="toggle"){
    const f=prefs.feeds.find(x=>x.url===target);if(!f)throw Error("Subscription no longer exists.");
    f.enabled=!f.enabled;
  }else if(message.action==="edit"){
    const f=prefs.feeds.find(x=>x.url===target);if(!f)throw Error("Subscription no longer exists.");
    if(typeof message.title!=="string"||typeof message.group!=="string")throw Error("Invalid publication label.");
    f.title=message.title.trim().slice(0,72)||f.title;f.group=message.group.trim().slice(0,28)||"GENERAL";
  }else if(message.action==="remove"){
    const index=prefs.feeds.findIndex(x=>x.url===target);
    if(index<0)throw Error("Subscription no longer exists.");
    prefs.feeds.splice(index,1);delete cache[target];
  }else if(message.action==="import"){
    if(!Array.isArray(message.feeds)||message.feeds.length>32)throw Error("Too many subscriptions.");
    for(const raw of message.feeds){
      const f=safeRSSFeed(raw);if(!f)continue;
      if(prefs.feeds.some(x=>x.url===f.url))continue;
      if(prefs.feeds.length>=32)break;
      prefs.feeds.push(f);added++;
    }
  }else if(message.action==="replace"){
    const raw=message.snapshot;
    if(!raw||typeof raw!=="object"||!Array.isArray(raw.feeds)||raw.feeds.length>32||raw.feeds.some(x=>!safeRSSFeed(x)))throw Error("Invalid RSS import snapshot.");
    const next=safeRSSPrefs(raw);prefs.enabled=next.enabled;prefs.interval=next.interval;prefs.feeds=next.feeds;
    for(const url of Object.keys(cache))if(!prefs.feeds.some(x=>x.url===url))delete cache[url];
  }else if(message.action==="config"){
    if(message.enabled!==undefined)prefs.enabled=message.enabled!==false;
    if(message.interval!==undefined){if(![15,30,60,180,360].includes(message.interval))throw Error("Invalid RSS refresh interval.");prefs.interval=message.interval;}
  }else if(message.action==="cache"){
    if(!prefs.feeds.some(x=>x.url===target))return {ok:true,prefs,cache,added};
    const entry=safeRSSCacheEntry(message.entry);if(!entry)throw Error("Invalid feed cache update.");
    const previous=cache[target];
    // Successes and attempts are independent timelines. A delayed *successful*
    // batch may contain newer checked headlines even if a later failed attempt
    // has already persisted its error/attempt timestamp. Merge each timeline
    // independently: errors must not suppress newer successful article data.
    if(!previous)cache[target]=entry;
    else{
      const contentIsNewer=entry.checkedAt>previous.checkedAt;
      const attemptIsNewer=entry.attemptedAt>previous.attemptedAt;
      if(contentIsNewer||attemptIsNewer){
        cache[target]={
          items:contentIsNewer?entry.items:previous.items,
          checkedAt:contentIsNewer?entry.checkedAt:previous.checkedAt,
          attemptedAt:attemptIsNewer?entry.attemptedAt:previous.attemptedAt,
          error:attemptIsNewer?entry.error:previous.error
        };
      }
    }
  }else throw Error("Unknown RSS operation.");
  await browser.storage.local.set({[RSS_PREFS_KEY]:prefs,[RSS_CACHE_KEY]:cache});
  return {ok:true,prefs,cache,added};
}
browser.runtime.onMessage.addListener(message=>{
  if(!message||typeof message!=="object")return undefined;
  if(message.type==="elfshell:sessions:mutate:v1"){
    const operation=sessionsChain.then(()=>changeSavedSessions(message));
    // Keep the chain alive after a rejected storage write so the next action can retry.
    sessionsChain=operation.then(()=>undefined,()=>undefined);
    return operation.catch(error=>({ok:false,error:error?.message||"Workspace storage unavailable."}));
  }
  if(message.type==="elfshell:recovery:mutate:v1"){
    const operation=recoveryChain.then(()=>mutateRecovery(message));
    recoveryChain=operation.then(()=>undefined,()=>undefined);
    return operation.catch(error=>({ok:false,error:error?.message||"Recovery storage unavailable."}));
  }
  if(message.type==="elfshell:rss:mutate:v1"){
    const operation=rssChain.then(()=>mutateRSS(message));
    rssChain=operation.then(()=>undefined,()=>undefined);
    return operation.catch(error=>({ok:false,error:error?.message||"RSS storage unavailable."}));
  }
  return undefined;
});
