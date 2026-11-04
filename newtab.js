"use strict";
/* ELF//SHELL v0.5.4 audit candidate. No telemetry. RSS network fetches only for opt-in publications. No remote libraries or eval. */
const defaults = [
  {label:"Firefox",icon:"firefox",glyph:"◉",url:"https://www.mozilla.org/firefox/",group:"GENERAL"},
  {label:"Mail",icon:"mail",glyph:"✉",url:"https://mail.google.com/",group:"WORK"},
  {label:"Calendar",icon:"calendar",glyph:"▦",url:"https://calendar.google.com/",group:"WORK"},
  {label:"Drive",icon:"drive",glyph:"◇",url:"https://drive.google.com/",group:"WORK"},
  {label:"Video",icon:"video",glyph:"▷",url:"https://www.youtube.com/",group:"MEDIA"},
  {label:"Library",icon:"library",glyph:"▤",url:"https://openlibrary.org/",group:"MEDIA"}
];
const dataKey="elfshell-workspace-v3";
const previousKey="elfshell-workspace-v2";
// Store each workspace field independently. A note save must never overwrite a
// different tab's newer shortcuts, sessions, focus, or appearance settings.
const workspaceFields=["links","note","focus","motion","contrast","bangs","sessions"];
const fieldKey=field=>`${dataKey}:field:${field}`;
const dirtyFields=new Set();
const saveFailures=new Set();
const saveTimers=new Map();
const iconNames=["firefox","mail","calendar","drive","video","library","globe","code","tasks","terminal","notes","news"];
const defaultBangs=[
  {key:"yt",url:"https://www.youtube.com/results?search_query={query}"},
  {key:"gh",url:"https://github.com/search?q={query}"},
  {key:"ddg",url:"https://duckduckgo.com/?q={query}"},
  {key:"w",url:"https://en.wikipedia.org/w/index.php?search={query}"}
];
const legacyKey="elfshell-shortcuts-v1";
const $=id=>document.getElementById(id);
const ext=typeof browser!=="undefined" && !!browser.storage;
let state={links:defaults.map(x=>({...x})),note:"",focus:"",motion:false,contrast:false,bangs:defaultBangs.map(x=>({...x})),sessions:[]};
let searchItems=[];
let searchQuery="";
let selected=0;
let searchRevision=0;
let lastClosedDuplicates=[];

const validUrl=(url)=>{try{let u=new URL(url);return u.protocol==="https:"||u.protocol==="http:";}catch{return false;}};
const cleanString=(v,max)=>typeof v==="string"?v.slice(0,max):"";
function cleanLink(x,original){
  if(!x || typeof x!=="object" || !validUrl(x.url))return null;
  let label=cleanString(x.label,32).trim() || original.label;
  let glyph=cleanString(x.glyph,4).trim() || original.glyph;
  let group=cleanString(x.group,14).trim().toUpperCase() || original.group;
  const icon=iconNames.includes(x.icon)?x.icon:original.icon;
  return {label,glyph,url:x.url,group,icon};
}
function cleanWorkspace(x){
  if(!x||typeof x!=="object"||!Array.isArray(x.links)||x.links.length!==6)return null;
  let links=x.links.map((link,i)=>cleanLink(link,defaults[i]));
  if(links.some(x=>!x))return null;
  const bangs=cleanBangs(x.bangs);
  const sessions=cleanSessions(x.sessions);
  return {links,note:cleanString(x.note,6000),focus:cleanString(x.focus,120),motion:!!x.motion,contrast:!!x.contrast,bangs,sessions};
}
function safeBang(x){
  if(!x || typeof x!=="object")return null;
  const key=cleanString(x.key,12).trim().toLowerCase();
  const url=cleanString(x.url,512).trim();
  if(!/^[a-z][a-z0-9]{0,9}$/.test(key) || !url.includes("{query}"))return null;
  const substituted=url.replaceAll("{query}","sample");
  if(!validUrl(substituted) || !substituted.startsWith("https://"))return null;
  return {key,url};
}
function cleanBangs(value){
  if(!Array.isArray(value))return defaultBangs.map(x=>({...x}));
  const seen=new Set(),out=[];
  for(const entry of value.slice(0,12)){
    const b=safeBang(entry);
    if(!b||seen.has(b.key))continue;
    seen.add(b.key);out.push(b);
  }
  return out.length?out:defaultBangs.map(x=>({...x}));
}
function cleanSessions(value){
  if(!Array.isArray(value))return [];
  return value.slice(0,10).map(x=>{
    if(!x || typeof x!=="object" || !Array.isArray(x.urls))return null;
    const urls=x.urls.slice(0,40).filter(u=>typeof u==="string"&&u.length<=2048&&validUrl(u));
    const name=cleanString(x.name,48).trim();
    if(!urls.length||!name)return null;
    const created=typeof x.created==="string"?x.created.slice(0,30):"";
    return {name,created,urls};
  }).filter(Boolean);
}
const illustratedIcons=new Set(["firefox","mail","calendar","drive","video","library"]);
function imageUrl(icon){
  const name=iconNames.includes(icon)?icon:"globe";
  return "assets/shortcut-icons/"+name+(illustratedIcons.has(name)?".webp":".svg");
}
async function persist(fields){
  // Writes for different fields use different storage keys, so simultaneous
  // dashboard tabs cannot clobber one another's unrelated changes.
  const changed=[...new Set(fields)];
  if(!changed.length || changed.some(field=>!workspaceFields.includes(field)))throw Error("Invalid workspace save fields");
  const values={};
  for(const field of changed){
    dirtyFields.add(field);
    values[fieldKey(field)]=JSON.parse(JSON.stringify(state[field]));
  }
  try {
    if(ext)await browser.storage.local.set(values);
    else for(const [key,value] of Object.entries(values))localStorage.setItem(key,JSON.stringify(value));
    for(const field of changed){
      saveFailures.delete(field);
      // Don't clear dirty state if the user typed something newer in the meantime.
      if(JSON.stringify(state[field])===JSON.stringify(values[fieldKey(field)]))dirtyFields.delete(field);
    }
    $("archive-status").textContent=saveFailures.size?"SAVE ERROR":"SAVED";
    return true;
  } catch(error) {
    console.error("ELF//SHELL: local save failed",error);
    for(const field of changed)saveFailures.add(field);
    $("archive-status").textContent="SAVE ERROR";
    return false;
  }
}
function queueSave(field){
  clearTimeout(saveTimers.get(field));
  dirtyFields.add(field);
  $("note-status").textContent="EDITING";
  saveTimers.set(field,setTimeout(async()=>{
    saveTimers.delete(field);
    await persist([field]);
    $("note-status").textContent=saveFailures.size?"SAVE ERROR":dirtyFields.size?"EDITING":"SAVED";
    $("editor-note-status").textContent=saveFailures.size?"SAVE ERROR — RETRY BY EDITING":dirtyFields.size?"AUTOSAVING":"SAVED LOCALLY";
  },380));
}
function applyWorkspaceStorageChanges(changes,areaName){
  if(areaName!=="local")return;
  let candidate={...state},changedFields=[];
  for(const field of workspaceFields){
    const change=changes[fieldKey(field)];
    // Never replace a field with a remote value while this tab has unsaved edits.
    if(!change || change.newValue===undefined || dirtyFields.has(field))continue;
    candidate[field]=change.newValue;
    changedFields.push(field);
  }
  if(!changedFields.length)return;
  const cleaned=cleanWorkspace(candidate);
  if(!cleaned)return;
  state=cleaned;
  if(changedFields.includes("links"))renderLinks();
  if(changedFields.some(f=>["motion","contrast"].includes(f)))applyAppearance();
  for(const field of ["focus","note"]){
    if(!changedFields.includes(field))continue;
    for(const input of document.querySelectorAll(field==="focus"?"#focus-input, #focus-editor":"#note-input, #note-editor"))input.value=state[field];
  }
  if(changedFields.includes("sessions") && $("sessions-dialog").open)renderWorkspaces();
}
async function freshestSessions(){
  if(!ext)return state.sessions;
  const stored=await browser.storage.local.get(fieldKey("sessions"));
  return stored[fieldKey("sessions")]===undefined?state.sessions:cleanSessions(stored[fieldKey("sessions")]);
}
function applyAppearance(){document.body.classList.toggle("reduce-effects",state.motion);document.body.classList.toggle("high-contrast",state.contrast);}
function renderLinks(){
  const nav=$("shortcuts");nav.replaceChildren();
  state.links.forEach((item,i)=>{
    const a=document.createElement("a");a.className="shortcut";a.href=item.url;a.rel="noreferrer";a.title=`${i+1} · ${item.label} · ${item.url}`;
    const glyph=document.createElement("span");glyph.className="glyph";
    const art=document.createElement("img");art.className="shortcut-icon";art.alt="";art.decoding="async";art.src=imageUrl(item.icon);glyph.appendChild(art);
    const label=document.createElement("span");label.className="text";label.textContent=item.label;
    const group=document.createElement("span");group.className="link-group";group.textContent=item.group;
    const number=document.createElement("span");number.className="link-number";number.textContent=String(i+1);
    a.append(number,glyph,label,group);nav.appendChild(a);
  });
}
function renderClock(){
  const d=new Date();
  $("time").textContent=new Intl.DateTimeFormat(undefined,{hour:"2-digit",minute:"2-digit",hour12:false}).format(d);
  $("date").textContent=new Intl.DateTimeFormat(undefined,{year:"numeric",month:"2-digit",day:"2-digit",weekday:"short"}).format(d).toUpperCase();
}
async function diagnostics(){
  $("network-status").textContent=navigator.onLine?"ONLINE*":"OFFLINE";
  $("network-status").title="Browser connectivity hint; not a verified internet connection";
  try{if(typeof browser!=="undefined" && browser.tabs){let tabs=await browser.tabs.query({});$("tab-count").textContent=String(tabs.length);}else $("tab-count").textContent="—";}catch{$("tab-count").textContent="—";}
}
async function hasPermission(permission){if(!ext)return false;try{return await browser.permissions.contains({permissions:[permission]});}catch{return false;}}
async function refreshAccessButtons(){
  for(const button of document.querySelectorAll("[data-permission]")){
    const granted=await hasPermission(button.dataset.permission);
    button.textContent=granted?"ENABLED · REVOKE":"ENABLE";
    button.classList.toggle("granted",granted);
  }
  const hosts=$("permission-host-list");hosts.replaceChildren();
  try{
    if(!ext || !browser.permissions)throw Error("Preview has no extension permissions");
    const all=await browser.permissions.getAll();
    const allowed=new Set(["tabs","sessions","bookmarks","history"]);
    const granted=(all.permissions||[]).filter(p=>allowed.has(p));
    $("permission-ledger").textContent="GRANTED OPTIONAL / "+(granted.length?granted.join(" · ").toUpperCase():"NONE");
    const origins=[...new Set(all.origins||[])].sort();
    if(!origins.length){const p=document.createElement("p");p.className="quiet";p.textContent="No extra feed-host permissions granted.";hosts.append(p);}
    for(const origin of origins){
      const row=document.createElement("div");row.className="permission-host-row";
      const label=document.createElement("span");label.textContent=origin;label.title=origin;
      const revoke=document.createElement("button");revoke.type="button";revoke.textContent="REVOKE";
      revoke.setAttribute("aria-label","Revoke access to "+origin);
      revoke.addEventListener("click",async()=>{
        try{const ok=await browser.permissions.remove({origins:[origin]});
          $("access-message").textContent=ok?"Host access revoked. Saved headlines remain local; new feed requests will stop.":"No host access was removed.";
        }catch(error){$("access-message").textContent="Unable to revoke host access: "+error.message;}
        await refreshAccessButtons();
      });
      row.append(label,revoke);hosts.append(row);
    }
  }catch{ $("permission-ledger").textContent="GRANTED OPTIONAL / UNAVAILABLE IN WEB PREVIEW";
    const p=document.createElement("p");p.className="quiet";p.textContent="Host permissions are visible when installed as a Firefox extension.";hosts.append(p);
  }
  const enabled=await hasPermission("sessions");
  $("session-permission").hidden=enabled;
  if(enabled)await loadRecents();else renderRecentMessage("Session access disabled.");
}
function renderRecentMessage(message){for(const id of ["recent-list","recent-modal-list"]){let p=document.createElement("p");p.className="quiet";p.textContent=message;$(id).replaceChildren(p);}}
async function loadRecents(){
  if(!await hasPermission("sessions")){renderRecentMessage("Session access disabled.");return;}
  try{
    const sessions=await browser.sessions.getRecentlyClosed({maxResults:5});
    const roots=[$("recent-list"),$("recent-modal-list")];roots.forEach(root=>root.replaceChildren());
    if(!sessions.length){renderRecentMessage("No recently closed tabs in this browser session.");return;}
    for(const entry of sessions){
      let obj=entry.tab||entry.window;
      if(!obj||!obj.sessionId)continue;
      const title=entry.tab?(entry.tab.title||"Closed tab"):("Closed window"+(entry.window.tabs?.length?` · ${entry.window.tabs.length} tabs`:""));
      for(const root of roots){
        const button=document.createElement("button");button.type="button";button.className="recent-entry";
        button.textContent=title;button.title="Restore "+title;
        button.addEventListener("click",async()=>{try{await browser.sessions.restore(obj.sessionId);await loadRecents();}catch(e){console.error("Restore failed",e);renderRecentMessage("Restore failed. The session may have expired.");}});
        root.appendChild(button);
      }
    }
    if(!roots[0].childElementCount)renderRecentMessage("No restorable entries.");
  }catch(error){console.error(error);renderRecentMessage("Could not read recently closed tabs.");}
}
function showAccess(){refreshAccessButtons();$("access-dialog").showModal();}
async function onPermissionClick(button){
  const permission=button.dataset.permission;
  if(!["tabs","sessions","bookmarks","history"].includes(permission))return;
  try{
    // Use the click handler's active user gesture to request optional permissions immediately.
    const granted=button.classList.contains("granted");
    if(granted){await browser.permissions.remove({permissions:[permission]});$("access-message").textContent="Access revoked. Existing local notes and links are unchanged.";}
    else{const ok=await browser.permissions.request({permissions:[permission]});$("access-message").textContent=ok?"Permission granted.":"Permission declined.";}
    await refreshAccessButtons();
    await diagnostics();
    if($("search-input").value)await updateSearch();
  }catch(error){console.error(error);$("access-message").textContent="Permission request failed. Check Firefox extension settings.";}
}
function calcExpression(raw){
  let s=raw.trim();
  const percent=s.match(/^([+-]?\d+(?:\.\d+)?)\s*%\s*of\s*([+-]?\d+(?:\.\d+)?)$/i);
  if(percent)return Number(percent[1])*Number(percent[2])/100;
  if(!/^[\d\s.+*/()%\-]+$/.test(s) || s.length>70)return null;
  // Small arithmetic parser instead of eval: +, -, *, /, parentheses, percentage.
  const tokens=s.match(/(?:\d+(?:\.\d+)?|\.\d+)|[()+*/%\-]/g)||[];
  if(tokens.join("").length!==s.replace(/\s/g,"").length || tokens.length>45)return null;
  let p=0;
  const primary=()=>{
    if(tokens[p]==="+"){p++;return primary();}
    if(tokens[p]==="-"){p++;return -primary();}
    if(tokens[p]==="("){p++;const v=add();if(tokens[p++]!==")")throw Error("paren");return v;}
    const t=tokens[p++];if(!t||!/^\d+(\.\d+)?$|^\.\d+$/.test(t))throw Error("number");
    let v=Number(t);while(tokens[p]==="%") {p++;v=v/100;}return v;
  };
  const multiply=()=>{let v=primary();while(tokens[p]==="*"||tokens[p]==="/"){let op=tokens[p++],r=primary();v=op==="*"?v*r:v/r;}return v;};
  const add=()=>{let v=multiply();while(tokens[p]==="+"||tokens[p]==="-"){let op=tokens[p++],r=multiply();v=op==="+"?v+r:v-r;}return v;};
  try{let n=add();return p===tokens.length&&Number.isFinite(n)?n:null;}catch{return null;}
}
function formatNumber(n){return new Intl.NumberFormat(undefined,{maximumFractionDigits:8}).format(n);}
function bangUrl(key,query){
  const b=state.bangs.find(b=>b.key===key);
  return b?b.url.replaceAll("{query}",encodeURIComponent(query)):null;
}
function action(label,sub,run,group="RESULTS"){return {label,sub,run,group};}
async function suggestions(input){
  const q=input.trim();if(!q)return [];
  if(q.startsWith("@")){
    if(!await hasPermission("tabs"))return [action("Enable open-tab search","Open Browser Access and enable Tabs",showAccess)];
    try{const f=q.slice(1).trim().toLowerCase(), tabs=await browser.tabs.query({});
      return tabs.filter(t=>t.id&&((t.title||"").toLowerCase().includes(f)||(t.url||"").toLowerCase().includes(f))).slice(0,8).map(t=>action(t.title||t.url||"Untitled tab",t.url||"OPEN TAB",async()=>{await browser.tabs.update(t.id,{active:true});if(t.windowId)await browser.windows.update(t.windowId,{focused:true});}));
    }catch{return [action("Unable to read tabs","Check Firefox permissions",showAccess)];}
  }
  if(q.startsWith("#")){
    if(!await hasPermission("bookmarks"))return [action("Enable bookmark search","Open Browser Access",showAccess)];
    try{let result=await browser.bookmarks.search(q.slice(1).trim());return result.filter(x=>validUrl(x.url)).slice(0,8).map(b=>action(b.title||b.url,"BOOKMARK / "+b.url,()=>window.location.assign(b.url)));}
    catch{return [];}
  }
  if(q.startsWith("^")){
    if(!await hasPermission("history"))return [action("Enable history search","Open Browser Access",showAccess)];
    try{let result=await browser.history.search({text:q.slice(1).trim(),startTime:0,maxResults:8});return result.filter(x=>validUrl(x.url)).map(h=>action(h.title||h.url,"HISTORY / "+h.url,()=>window.location.assign(h.url)));}
    catch{return [];}
  }
  if(q.startsWith(">"))return commandSuggestions(q.slice(1).trim());
  const match=q.match(/^!([a-z0-9]+)(?:\s+(.*))?$/i);
  if(match){
    const key=match[1].toLowerCase(),text=(match[2]||"").trim();
    const url=text?bangUrl(key,text):null;
    if(!state.bangs.some(x=>x.key===key))return [action("Unknown bang: !"+key,"Configure search bangs under Station Configuration",showSettings)];
    if(!text)return [action("!"+key+" · enter a search","Custom site search / Configure Station",showSettings)];
    return [action(`Search !${key} for “${text}”`,`BANG / !${key}`,()=>window.location.assign(url))];
  }
  let arithmetic=q.startsWith("=")?q.slice(1).trim():q;
  let n=calcExpression(arithmetic);
  if(n!==null && /[%+*/()\-]|^=/.test(q))return [action(formatNumber(n),"CALCULATED LOCALLY · ENTER TO COPY",async()=>{try{await navigator.clipboard.writeText(String(n));}catch{ /* Clipboard unavailable; result remains visible. */ }})];
  if(q==="?"||q==="help")return [action("@ tabs · # bookmarks · ^ history","Search inside your browser",()=>{}),action("> actions · !gh query · = 15% of 2400","Actions, website bangs and arithmetic",()=>{})];
  return [];
}
function displaySuggestions(items,query=$("search-input").value.trim()){
  searchItems=items;searchQuery=query;selected=0;
  const root=$("search-results");root.replaceChildren();
  let previousGroup="";
  items.forEach((item,i)=>{
    const group=item.group||"RESULTS";
    if(group!==previousGroup){
      const heading=document.createElement("div");heading.className="search-group-title";
      heading.setAttribute("role","presentation");heading.textContent="// "+group;
      root.append(heading);previousGroup=group;
    }
    const b=document.createElement("button");b.type="button";b.id="palette-option-"+i;
    b.className="search-item";b.setAttribute("role","option");b.setAttribute("aria-selected",i===0?"true":"false");
    const title=document.createElement("span");title.className="search-item-title";title.textContent=item.label;
    const sub=document.createElement("span");sub.className="search-item-sub";sub.textContent=item.sub;
    b.append(title,sub);
    b.addEventListener("click",()=>executeItem(i));root.appendChild(b);
  });
  root.hidden=!items.length;
  $("search-input").setAttribute("aria-expanded",String(items.length>0));
  if(items.length)$("search-input").setAttribute("aria-activedescendant","palette-option-0");
  else $("search-input").removeAttribute("aria-activedescendant");
}
async function updateSearch(){
  const request=++searchRevision;
  const q=$("search-input").value.trim();
  let result=await suggestions(q);
  if(request!==searchRevision)return;
  displaySuggestions(result,q);
}
function updateSelected(){
  const options=$("search-results").querySelectorAll(".search-item");
  options.forEach((option,i)=>option.setAttribute("aria-selected",i===selected?"true":"false"));
  if(options[selected]){
    $("search-input").setAttribute("aria-activedescendant",options[selected].id);
    options[selected].scrollIntoView({block:"nearest"});
  }
}
async function executeItem(i){let chosen=searchItems[i];if(!chosen)return;displaySuggestions([]);endPalette();try{await chosen.run();}catch(err){console.error("Command failed",err);}}
async function runSearch(){
  const q=$("search-input").value.trim();if(!q)return;
  if(searchItems.length && searchQuery===q){await executeItem(selected);return;}
  // Avoid executing a stale suggestion when Enter races the asynchronous lookup.
  const latest=await suggestions(q);
  if(latest.length){displaySuggestions(latest,q);await executeItem(0);return;}
  if(q.startsWith("@")||q.startsWith("#")||q.startsWith("^")||q.startsWith("=")||q.startsWith(">"))return;
  if(/^!\w+\s/.test(q))return; // Unknown bangs never forwarded accidentally.
  try{if(typeof browser!=="undefined" && browser.search){await browser.search.search({query:q,disposition:"CURRENT_TAB"});return;}}
  catch(e){console.error("Default search failed",e);}
  $("search-input").setCustomValidity("Firefox's search API is unavailable in this preview.");
  $("search-input").reportValidity();setTimeout(()=>$("search-input").setCustomValidity(""),1500);
}
function buildSettings(){
  const root=$("shortcut-fields");root.replaceChildren();
  state.links.forEach((item,i)=>{
    const wrap=document.createElement("fieldset");wrap.className="shortcut-row";
    const legend=document.createElement("legend");legend.textContent=`0${i+1} / ${item.label}`;wrap.appendChild(legend);
    for(const [name,value,max] of [["label",item.label,32],["url",item.url,2048],["group",item.group,14]]){
      const label=document.createElement("label");label.textContent=name.toUpperCase();
      const input=document.createElement("input");input.dataset.index=String(i);input.dataset.field=name;input.value=value;input.maxLength=max;input.required=true;
      if(name==="url")input.type="url";
      label.appendChild(input);wrap.appendChild(label);
    }
    const iconLabel=document.createElement("label");iconLabel.textContent="ICON";
    const select=document.createElement("select");select.dataset.index=String(i);select.dataset.field="icon";
    for(const n of iconNames){const opt=document.createElement("option");opt.value=n;opt.textContent=n.toUpperCase();opt.selected=n===item.icon;select.append(opt);}
    iconLabel.append(select);wrap.appendChild(iconLabel);
    root.appendChild(wrap);
  });
  const rootBangs=$("bang-fields");rootBangs.replaceChildren();
  state.bangs.forEach((entry,i)=>{
    const row=document.createElement("div");row.className="bang-row";
    for(const field of ["key","url"]){
      const label=document.createElement("label");label.textContent=field.toUpperCase();
      const input=document.createElement("input");input.dataset.bangIndex=String(i);input.dataset.bangField=field;input.value=entry[field];input.maxLength=field==="key"?10:512;input.required=true;
      label.append(input);row.append(label);
    }rootBangs.append(row);
  });
  $("reduce-motion").checked=state.motion;$("high-contrast").checked=state.contrast;$("settings-message").textContent="";
}
function showSettings(){buildSettings();$("settings-dialog").showModal();}
async function saveSettings(event){
  event.preventDefault();
  const links=state.links.map(x=>({...x}));
  for(const input of $("shortcut-fields").querySelectorAll("input,select"))links[Number(input.dataset.index)][input.dataset.field]=input.value.trim();
  const bangs=state.bangs.map(x=>({...x}));
  for(const input of $("bang-fields").querySelectorAll("input"))bangs[Number(input.dataset.bangIndex)][input.dataset.bangField]=input.value.trim();
  const used=new Set();
  if(bangs.some(b=>!safeBang(b)||used.has(b.key)||(used.add(b.key),false))){$("settings-message").textContent="Invalid search bang: use a unique short key and an HTTPS template containing {query}.";return;}
  const validated=cleanWorkspace({...state,links,bangs,motion:$("reduce-motion").checked,contrast:$("high-contrast").checked});
  if(!validated){$("settings-message").textContent="Check all six links. Web addresses must start with https:// or http://.";return;}
  const before=state;
  state=validated;
  if(!await persist(["links","bangs","motion","contrast"])){
    state=before;
    for(const field of ["links","bangs","motion","contrast"])dirtyFields.delete(field);
    $("settings-message").textContent="Save failed. Your edits remain in this dialog; please retry.";
    return;
  }
  applyAppearance();renderLinks();$("settings-dialog").close();
}
function saveJSON(){
  const data={format:"elfshell-settings",version:5,exportedAt:new Date().toISOString(),...state,rss:window.elfFeeds?.snapshot(),memory:window.elfMemory?.snapshot()};
  const blob=new Blob([JSON.stringify(data,null,2)],{type:"application/json"});
  const url=URL.createObjectURL(blob);const a=document.createElement("a");a.href=url;a.download="elfshell-ayarime-settings.json";document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
async function importJSON(file){
  let workspaceCommitted=false;
  try{
    if(!file || file.size>131072)throw Error("File is too large");
    const raw=JSON.parse(await file.text());
    if(raw.format!=="elfshell-settings"||![2,3,4,5].includes(raw.version))throw Error("Not an ELF//SHELL v2–v5 settings file");
    const imported=cleanWorkspace(raw);if(!imported)throw Error("Invalid settings or URL");
    const feedImport=raw.rss===undefined?null:window.elfFeeds?.validateSnapshot(raw.rss);
    if(raw.rss!==undefined&&!feedImport)throw Error("Invalid RSS subscriptions in backup");
    const memoryImport=raw.memory===undefined?null:window.elfMemory?.validateSnapshot(raw.memory);
    if(raw.memory!==undefined&&!memoryImport)throw Error("Invalid Memory Trace settings in backup");
    const before=state;
    state=imported;
    if(!await persist(workspaceFields)){
      state=before;
      for(const field of workspaceFields)dirtyFields.delete(field);
      throw Error("Local storage rejected the import. Previous settings were retained; retry the file.");
    }
    workspaceCommitted=true;
    applyAppearance();renderLinks();$("focus-input").value=state.focus;$("note-input").value=state.note;
    if(feedImport)await window.elfFeeds.applySnapshot(feedImport);
    if(memoryImport)await window.elfMemory.applySnapshot(memoryImport);
    buildSettings();$("settings-message").textContent="Settings imported successfully.";
  }catch(error){$("settings-message").textContent=(workspaceCommitted?"Import incomplete: ":"Import rejected: ")+error.message;}
}
function startPalette(){
  if(document.querySelector("dialog[open]"))return;
  document.body.classList.add("palette-open");$("palette-scrim").hidden=false;
}
function endPalette(){
  searchRevision++; // Invalidate any pending async suggestions after dismissal.
  document.body.classList.remove("palette-open");$("palette-scrim").hidden=true;
  displaySuggestions([]);$("search-input").blur();
}
function commandSuggestions(term){
  const actions=[
    action("Open quick notes","LOCAL ARCHIVE",()=>$("notes-toggle").click(),"STATION"),
    action("Edit station and search bangs","CUSTOMISE SHORTCUTS",showSettings,"STATION"),
    action("Browser permissions ledger","GRANTED / REVOKE ACCESS",showAccess,"PRIVACY"),
    action("Manage saved workspaces","TAB SESSION SETS",showSessions,"BROWSER"),
    action("Restore a closed tab","CURRENT SESSION",()=>$("recents-toggle").click(),"BROWSER"),
    action("Open tab housekeeping","DUPLICATES / DISCARD IDLE",showHousekeeping,"BROWSER"),
    action("Manage RSS subscriptions","SUBSTACK / RSS / ATOM",()=>window.elfFeeds?.show(),"NETWORK"),
    action("Toggle reduced effects","LOW MOTION",async()=>{const before=state.motion;state.motion=!before;applyAppearance();if(!await persist(["motion"])){state.motion=before;dirtyFields.delete("motion");applyAppearance();}},"APPEARANCE"),
    action("Export local settings","JSON BACKUP",saveJSON,"STATION")
  ];
  if(!term)return actions;
  const needle=term.toLowerCase().replaceAll(/[^a-z0-9 ]/g,"").split(/\s+/).filter(Boolean);
  return actions.filter(a=>needle.every(w=>(a.label+" "+a.sub).toLowerCase().includes(w))).slice(0,8);
}
function showSessions(){renderWorkspaces();$("sessions-message").textContent="";$("sessions-dialog").showModal();}
function renderWorkspaces(){
  const root=$("workspace-list");root.replaceChildren();
  if(!state.sessions.length){const p=document.createElement("p");p.className="quiet";p.textContent="No saved workspaces yet.";root.append(p);return;}
  state.sessions.forEach((item,i)=>{
    const row=document.createElement("div");row.className="workspace-entry";
    const info=document.createElement("div");const title=document.createElement("strong");title.textContent=item.name;
    const subtitle=document.createElement("small");subtitle.textContent=`${item.urls.length} tabs · ${item.created?.slice(0,10)||"saved"}`;
    info.append(title,subtitle);const open=document.createElement("button");open.type="button";open.textContent="RESTORE";
    open.addEventListener("click",async()=>{
      try{await browser.windows.create({url:item.urls});$("sessions-message").textContent="Workspace restored in a new window.";}
      catch(err){console.error(err);$("sessions-message").textContent="Could not restore this workspace.";}
    });
    const remove=document.createElement("button");remove.type="button";remove.textContent="DELETE";
    remove.addEventListener("click",async()=>{
      if(!confirm(`Delete saved workspace “${item.name}”?`))return;
      const before=state.sessions;
      try{
        const latest=await freshestSessions();
        // A saved item is identified by its timestamp, name, and list of URLs.
        state.sessions=latest.filter(x=>!(x.created===item.created&&x.name===item.name&&JSON.stringify(x.urls)===JSON.stringify(item.urls)));
        if(!await persist(["sessions"]))throw Error("Local storage rejected deletion");
        renderWorkspaces();$("sessions-message").textContent="Workspace deleted locally.";
      }catch(error){state.sessions=before;dirtyFields.delete("sessions");console.error(error);$("sessions-message").textContent="Delete was not saved. Please retry.";}
    });
    row.append(info,open,remove);root.append(row);
  });
}
async function saveWorkspace(){
  if(!ext || !await hasPermission("tabs")){ $("sessions-message").textContent="Enable Tabs permission in Browser Access first.";return;}
  const name=$("workspace-name").value.trim().slice(0,48);
  if(!name){$("sessions-message").textContent="Enter a workspace name first.";return;}
  try{
    const tabs=await browser.tabs.query({currentWindow:true});
    const urls=tabs.filter(t=>!t.incognito && validUrl(t.url) && t.url.length<=2048).slice(0,40).map(t=>t.url);
    if(!urls.length){$("sessions-message").textContent="No web tabs to save. Internal Firefox tabs are skipped.";return;}
    const before=state.sessions;
    const latest=await freshestSessions();
    state.sessions=cleanSessions([{name,created:new Date().toISOString(),urls},...latest]).slice(0,10);
    if(!await persist(["sessions"])){
      state.sessions=before;
      dirtyFields.delete("sessions");
      $("sessions-message").textContent="Save failed. Your workspace name is still here; retry when storage is available.";
      return;
    }
    renderWorkspaces();$("workspace-name").value="";
    $("sessions-message").textContent=`Saved ${urls.length} tabs locally. URLs may contain sensitive query parameters; export with care.`;
  }catch(err){console.error(err);$("sessions-message").textContent="Unable to save workspace. Check Tabs permission.";}
}
function showHousekeeping(){$("housekeeping-message").textContent="";$("housekeeping-dialog").showModal();}
async function closeDuplicates(){
  if(!await hasPermission("tabs")){$("housekeeping-message").textContent="Enable Tabs permission in Browser Access first.";return;}
  try{
    // Never remove a tab from another window: the same URL may be intentional in a separate workspace.
    const tabs=await browser.tabs.query({currentWindow:true});const groups=new Map();
    for(const t of tabs){if(t.incognito||!validUrl(t.url))continue;const key=t.url; // A fragment can identify a distinct state in a modern web application.
      if(!groups.has(key))groups.set(key,[]);groups.get(key).push(t);}
    let ids=[];
    for(const list of groups.values()){
      if(list.length<2)continue;
      // Preserve active, pinned, audible tabs over background counterparts.
      list.sort((a,b)=>Number(b.active)-Number(a.active)||Number(b.pinned)-Number(a.pinned)||Number(b.audible)-Number(a.audible)||a.id-b.id);
      ids.push(...list.slice(1).filter(t=>!t.active&&!t.pinned&&!t.audible).map(t=>t.id));
    }
    if(!ids.length){$("housekeeping-message").textContent="No safe duplicate tabs found.";return;}
    if(!confirm(`Close ${ids.length} background duplicate tab(s) in this window? Unsaved page content may be lost.`))return;
    const chosen=tabs.filter(t=>ids.includes(t.id)).map(t=>({url:t.url,windowId:t.windowId,index:t.index}));
    await browser.tabs.remove(ids);
    // Append to the pending recovery list; never discard failures from an older cleanup.
    lastClosedDuplicates.push(...chosen);
    $("undo-duplicates").hidden=false;
    $("housekeeping-message").textContent=`Closed ${ids.length} duplicate tabs; ${lastClosedDuplicates.length} address(es) available to reopen. Page state is not saved.`;
    await diagnostics();
  }catch(error){console.error(error);$("housekeeping-message").textContent="Duplicate cleanup failed.";}
}
async function reopenDuplicates(){
  if(!lastClosedDuplicates.length)return;
  const pending=lastClosedDuplicates.slice(),failed=[];
  // Reopening is best effort; preserve addresses that failed so the user can retry.
  let recovered=0;
  for(const item of pending){
    try{
      await browser.tabs.create({url:item.url,windowId:item.windowId,active:false,index:item.index});recovered++;
    }catch{
      try{await browser.tabs.create({url:item.url,active:false});recovered++;}
      catch(error){console.error("Could not reopen duplicate URL",error);failed.push(item);}
    }
  }
  lastClosedDuplicates=failed;
  $("undo-duplicates").hidden=failed.length===0;
  $("housekeeping-message").textContent=`Reopened ${recovered} of ${pending.length} addresses.${failed.length?" Retry the remaining "+failed.length+" address(es) using the same button.":""} Unsaved page contents cannot be restored by this action.`;
  await diagnostics();
}
async function discardIdle(){
  if(!await hasPermission("tabs")){$("housekeeping-message").textContent="Enable Tabs permission in Browser Access first.";return;}
  try{
    // Limit housekeeping to this window, not unrelated windows or browser workflows.
    const tabs=await browser.tabs.query({currentWindow:true});const cutoff=Date.now()-30*60*1000;
    const ids=tabs.filter(t=>!t.incognito&&!t.active&&!t.pinned&&!t.audible&&!t.discarded&&t.autoDiscardable!==false&&Number.isFinite(t.lastAccessed)&&t.lastAccessed<cutoff&&validUrl(t.url)).map(t=>t.id);
    if(!ids.length){$("housekeeping-message").textContent="No idle eligible tabs over 30 minutes.";return;}
    if(!confirm(`Discard ${ids.length} idle background tabs in this window? They will reload when reopened.`))return;
    await browser.tabs.discard(ids);$("housekeeping-message").textContent=`Requested discard for ${ids.length} idle tabs.`;
  }catch(error){console.error(error);$("housekeeping-message").textContent="Idle-tab discard failed.";}
}
async function init(){
  try{
    let data;
    let values={};
    if(ext)values=await browser.storage.local.get([dataKey,previousKey,legacyKey,...workspaceFields.map(fieldKey)]);
    else{
      const old=localStorage.getItem(dataKey)||localStorage.getItem(previousKey);
      values[dataKey]=old?JSON.parse(old):null;
      for(const field of workspaceFields){const value=localStorage.getItem(fieldKey(field));if(value!==null)values[fieldKey(field)]=JSON.parse(value);}
    }
    data=values[dataKey]||values[previousKey];
    if(!data && Array.isArray(values[legacyKey])){
      const old=values[legacyKey];
      if(old.length===6)data={...state,links:defaults.map((link,i)=>({...link,url:validUrl(old[i]?.url)?old[i].url:link.url}))};
    }
    const base=cleanWorkspace(data)||state;
    const updated={...base};
    for(const field of workspaceFields){const key=fieldKey(field);if(Object.prototype.hasOwnProperty.call(values,key))updated[field]=values[key];}
    state=cleanWorkspace(updated)||base;
  }catch(error){console.warn("ELF//SHELL: could not load local configuration",error);}
  $("focus-input").value=state.focus;$("note-input").value=state.note;
  renderLinks();applyAppearance();renderClock();diagnostics();refreshAccessButtons();
  setInterval(renderClock,15000);setInterval(diagnostics,30000);
}

$("search-form").addEventListener("submit",event=>{event.preventDefault();runSearch();});
$("search-input").addEventListener("input",updateSearch);
$("search-input").addEventListener("focus",startPalette);
$("palette-scrim").addEventListener("click",endPalette);
$("search-input").addEventListener("keydown",event=>{
  if(event.key==="ArrowDown"&&searchItems.length){event.preventDefault();selected=(selected+1)%searchItems.length;updateSelected();}
  else if(event.key==="ArrowUp"&&searchItems.length){event.preventDefault();selected=(selected+searchItems.length-1)%searchItems.length;updateSelected();}
  else if(event.key==="Escape"){
    event.preventDefault();$("search-input").value="";endPalette();
  }
});
document.addEventListener("keydown",event=>{
  const target=event.target;const typing=target instanceof HTMLElement&&(target.matches("input, textarea, select")||target.isContentEditable);
  const commandKey=(event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==="k";
  const searchKey=event.key==="/"&&!typing&&!event.altKey&&!event.ctrlKey&&!event.metaKey;
  if((searchKey||commandKey)&&!document.querySelector("dialog[open]")){
    event.preventDefault();
    $("station-menu").open=false;
    if(commandKey){$("search-input").value=">";$("search-input").focus();updateSearch();}
    else {$("search-input").focus();$("search-input").select();}
  }
  if(!typing&&!event.altKey&&!event.ctrlKey&&!event.metaKey&&!document.querySelector("dialog[open]")&&/^[1-6]$/.test(event.key)){
    event.preventDefault();window.location.assign(state.links[Number(event.key)-1].url);
  }
});
$("settings-toggle").addEventListener("click",showSettings);
$("permissions-toggle").addEventListener("click",showAccess);
$("sessions-toggle").addEventListener("click",showSessions);
$("close-sessions").addEventListener("click",()=>$("sessions-dialog").close());
$("save-workspace").addEventListener("click",saveWorkspace);
$("housekeeping-toggle").addEventListener("click",showHousekeeping);
$("close-housekeeping").addEventListener("click",()=>$("housekeeping-dialog").close());
$("close-duplicates").addEventListener("click",closeDuplicates);
$("undo-duplicates").addEventListener("click",reopenDuplicates);
$("discard-inactive").addEventListener("click",discardIdle);
$("notes-toggle").addEventListener("click",()=>{$("focus-editor").value=state.focus;$("note-editor").value=state.note;$("notes-dialog").showModal();});
$("close-notes").addEventListener("click",()=>$("notes-dialog").close());
$("recents-toggle").addEventListener("click",()=>{$("recents-dialog").showModal();loadRecents();});
$("close-recents").addEventListener("click",()=>$("recents-dialog").close());
$("recent-enable").addEventListener("click",()=>{$("recents-dialog").close();showAccess();});
$("cancel-settings").addEventListener("click",()=>$("settings-dialog").close());
$("settings-form").addEventListener("submit",saveSettings);
$("reset-links").addEventListener("click",()=>{state.links=defaults.map(x=>({...x}));buildSettings();$("settings-message").textContent="Default links restored in editor. Save to apply.";});
$("export-settings").addEventListener("click",saveJSON);
$("import-settings").addEventListener("click",()=>$("import-file").click());
$("import-file").addEventListener("change",event=>{if(event.target.files?.[0])importJSON(event.target.files[0]);event.target.value="";});
$("close-access").addEventListener("click",()=>$("access-dialog").close());
for(const button of document.querySelectorAll("[data-permission]"))button.addEventListener("click",()=>onPermissionClick(button));
$("session-permission").addEventListener("click",showAccess);
$("recent-refresh").addEventListener("click",loadRecents);
$("station-menu").addEventListener("click",event=>{
  if(event.target.closest(".center-actions button"))$("station-menu").open=false;
});
document.addEventListener("click",event=>{
  if($("station-menu").open && !$("station-menu").contains(event.target))$("station-menu").open=false;
});
document.addEventListener("keydown",event=>{
  if(event.key==="Escape" && $("station-menu").open)$("station-menu").open=false;
});
function bindMirror(id,key,mirrorId){$(id).addEventListener("input",event=>{state[key]=event.target.value.slice(0,key==="note"?6000:120);$(mirrorId).value=state[key];queueSave(key);if(key==="note")$("editor-note-status").textContent="AUTOSAVING";});}
bindMirror("focus-input","focus","focus-editor");bindMirror("focus-editor","focus","focus-input");
bindMirror("note-input","note","note-editor");bindMirror("note-editor","note","note-input");
window.addEventListener("online",diagnostics);window.addEventListener("offline",diagnostics);
if(ext){try{
  browser.tabs?.onCreated?.addListener(diagnostics);
  browser.tabs?.onRemoved?.addListener(diagnostics);
  browser.sessions?.onChanged?.addListener(loadRecents);
  browser.storage?.onChanged?.addListener(applyWorkspaceStorageChanges);
}catch(error){console.warn("Optional live events not available",error);}}
else window.addEventListener("storage",event=>{
  if(!event.key?.startsWith(`${dataKey}:field:`) || event.newValue===null)return;
  try{applyWorkspaceStorageChanges({[event.key]:{newValue:JSON.parse(event.newValue)}},"local");}catch(error){console.warn("Invalid shared workspace change",error);}
});
init();
