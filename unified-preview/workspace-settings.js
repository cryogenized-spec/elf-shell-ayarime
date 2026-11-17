"use strict";
/* All advanced controls live in the existing native sidebar's More tab or
 * within the tabbed full Hub. No second Station drawer or shadow connection
 * state is created. Registration is inert until OAuth/MCP transport is built. */
(() => {
  const isHub=document.body?.dataset.view==="hub";
  const isSidebar=document.body?.dataset.view==="sidebar";
  if(!isHub&&!isSidebar)return;
  const KEY="elfshell.mcp.registry.v1";
  const AI_KEY="elfshell.unified.aiEnabled.v1";
  const LAUNCHER_KEY="elfshell.station.launcherVisible.v1";
  const google=Object.freeze({
    gmail:["Google Gmail","https://gmailmcp.googleapis.com/mcp/v1"],
    drive:["Google Drive","https://drivemcp.googleapis.com/mcp/v1"],
    docs:["Google Docs","https://docsmcp.googleapis.com/mcp/v1"],
    sheets:["Google Sheets","https://sheetsmcp.googleapis.com/mcp/v1"],
    calendar:["Google Calendar","https://calendarmcp.googleapis.com/mcp/v1"]
  });
  const choose=(name,selector)=>document.querySelector(selector);
  const make=(tag,className,value)=>{
    const element=document.createElement(tag);
    if(className)element.className=className;
    if(value!==undefined)element.textContent=value;
    return element;
  };
  function createPrefs(parent) {
    if(!parent)return;
    const box=make("section","frame unified-controls");
    box.setAttribute("aria-label","Ayarime and Station preferences");
    box.innerHTML='<h2>Ayarime controls</h2>'+
      '<p class="quiet">One Firefox sidebar. Pausing the model clears its session key; it does not delete workspace data or permissions.</p>'+
      '<button type="button" class="mini" id="unified-ai-pause">Checking Ayarime…</button>'+
      '<p class="quiet" id="unified-ai-pause-status" role="status"></p>'+
      '<label class="unified-control-check"><input type="checkbox" id="unified-launcher-visible"> Show neon Ayarime launcher on Station</label>'+
      '<p class="quiet">If the launcher is hidden, use the Firefox sidebar selector or Alt+Shift+A on Station.</p>';
    parent.append(box);
    const pause=box.querySelector("#unified-ai-pause");
    const status=box.querySelector("#unified-ai-pause-status");
    const launcher=box.querySelector("#unified-launcher-visible");
    let enabled=true;
    async function sync() {
      try {
        const values=await browser.storage.local.get([AI_KEY,LAUNCHER_KEY]);
        enabled=values[AI_KEY]!==false;
        pause.textContent=enabled?"Pause Ayarime AI":"Resume Ayarime AI";
        launcher.checked=values[LAUNCHER_KEY]!==false;
      } catch { status.textContent="Could not load local preferences."; }
    }
    pause.addEventListener("click",async()=>{
      pause.disabled=true;
      try {
        await browser.storage.local.set({[AI_KEY]:!enabled});
        status.textContent=enabled
          ?"Ayarime paused. Background clears the session API key."
          :"Ayarime resumed. Provider permission and session key remain separate.";
        await sync();
      } catch {status.textContent="Could not change Ayarime setting."; }
      finally{pause.disabled=false;}
    });
    launcher.addEventListener("change",async()=>{
      try {await browser.storage.local.set({[LAUNCHER_KEY]:launcher.checked});}
      catch {launcher.checked=!launcher.checked;status.textContent="Could not save launcher visibility.";}
    });
    browser.storage.onChanged?.addListener((changes,area)=>{
      if(area==="local"&&(Object.hasOwn(changes,AI_KEY)||Object.hasOwn(changes,LAUNCHER_KEY)))
        void sync();
    });
    void sync();
  }
  if(isSidebar) {
    const more=document.getElementById("ayarime-sidebar-pane-more");
    createPrefs(more);
    const link=make("button","mini","Manage MCP connections in Workspace");
    link.type="button";
    link.id="unified-open-connections";
    link.addEventListener("click",()=>{
      try {browser.sidebarAction?.close?.().catch(()=>{});}catch{}
      browser.tabs.create({url:browser.runtime.getURL("hub.html#connections")})
        .catch(()=>{link.textContent="Open Workspace → Connections using the Hub.";});
    });
    more?.append(link);
    return;
  }
  createPrefs(document.getElementById("unified-hub-pane-settings"));
  const parent=document.getElementById("unified-hub-pane-connections");
  if(!parent)return;
  const section=make("section","frame unified-controls unified-mcp-registry");
  section.setAttribute("aria-label","Saved MCP server configurations");
  section.innerHTML='<h2>MCP servers</h2>'+
    '<p class="quiet">Configure endpoints here, not in an extra sidebar. Saving a URL does not authenticate, connect or discover tools.</p>'+
    '<form id="unified-mcp-form" class="unified-mcp-form">'+
    '<label for="unified-mcp-google">Google MCP template</label>'+
    '<select id="unified-mcp-google"><option value="">Custom HTTPS endpoint</option>'+
    Object.keys(google).map(key=>'<option value="'+key+'">'+google[key][0]+'</option>').join("")+
    '</select>'+
    '<label for="unified-mcp-name">Connection name</label>'+
    '<input id="unified-mcp-name" type="text" maxlength="70" required placeholder="My MCP server">'+
    '<label for="unified-mcp-url">MCP server HTTPS URL</label>'+
    '<input id="unified-mcp-url" type="url" maxlength="400" required spellcheck="false" autocomplete="off" placeholder="https://example.com/mcp">'+
    '<label for="unified-mcp-auth">Authentication</label>'+
    '<select id="unified-mcp-auth"><option value="oauth">OAuth · sign-in required</option>'+
    '<option value="none">No authentication · public endpoint</option></select>'+
    '<button type="submit" class="mini">Add saved configuration</button></form>'+
    '<p id="unified-mcp-status" class="quiet" role="status"></p>'+
    '<div id="unified-mcp-list" class="unified-mcp-list" aria-live="polite"></div>';
  parent.append(section);
  const form=section.querySelector("#unified-mcp-form");
  const name=section.querySelector("#unified-mcp-name");
  const url=section.querySelector("#unified-mcp-url");
  const auth=section.querySelector("#unified-mcp-auth");
  const preset=section.querySelector("#unified-mcp-google");
  const status=section.querySelector("#unified-mcp-status");
  const list=section.querySelector("#unified-mcp-list");
  let entries=[];
  preset.addEventListener("change",()=>{
    if(google[preset.value]){name.value=google[preset.value][0];url.value=google[preset.value][1];auth.value="oauth";}
  });
  function normalizeURL(value){
    const parsed=new URL(value);
    const host=parsed.hostname.toLowerCase().replace(/\.$/,"");
    if(parsed.protocol!=="https:"||parsed.username||parsed.password||parsed.port||
       parsed.search||parsed.hash||parsed.href.length>400||host.includes(":")||
       !host.includes(".")||host.endsWith(".localhost")||host.endsWith(".local")||
       host.endsWith(".internal")||host.endsWith(".test")||host.endsWith(".invalid")||
       /^(\d{1,3}\.){3}\d{1,3}$/.test(host))
      throw Error("Use a public HTTPS MCP endpoint without credentials or token parameters.");
    return parsed.toString();
  }
  function render(){
    list.replaceChildren();
    if(!entries.length){
      list.append(make("p","quiet","No custom MCP servers saved. Google endpoints can be selected above."));
      return;
    }
    for(const entry of entries){
      const box=make("article","unified-mcp-entry");
      box.append(make("strong","",entry.name));
      box.append(make("small","",entry.url));
      box.append(make("p","quiet",entry.auth==="oauth"
        ?"OAuth configuration saved · not connected":
        "No-auth configuration saved · not connected"));
      const buttons=make("div","unified-mcp-actions");
      const inspect=make("button","mini","Inspect");
      inspect.type="button";
      inspect.addEventListener("click",()=>{
        status.textContent=entry.name+" is configured only. OAuth and live tool discovery are not yet enabled.";
      });
      const refresh=make("button","mini","Refresh tools");
      refresh.type="button";refresh.disabled=true;
      refresh.title="Available when an authenticated MCP transport is implemented.";
      const remove=make("button","mini","Remove");
      remove.type="button";
      remove.addEventListener("click",async()=>{
        if(!confirm("Remove "+entry.name+" from saved MCP configurations?"))return;
        const previous=entries;
        entries=entries.filter(item=>item.id!==entry.id);
        try {await browser.storage.local.set({[KEY]:entries});render();status.textContent="Configuration removed.";}
        catch{entries=previous;render();status.textContent="Removal failed; no changes were saved.";}
      });
      buttons.append(inspect,refresh,remove);box.append(buttons);list.append(box);
    }
  }
  form.addEventListener("submit",async event=>{
    event.preventDefault();
    try{
      const title=name.value.trim(),endpoint=normalizeURL(url.value.trim());
      if(title.length<2||title.length>70||!["oauth","none"].includes(auth.value))
        throw Error("Enter a 2–70 character name and supported authentication mode.");
      if(entries.length>=20)throw Error("Maximum 20 registered servers. Remove one first.");
      if(entries.some(item=>item.url===endpoint))throw Error("Endpoint already saved.");
      const next=[...entries,{id:crypto.randomUUID(),name:title,url:endpoint,auth:auth.value}];
      await browser.storage.local.set({[KEY]:next});
      entries=next;form.reset();render();
      status.textContent="Saved locally; no server contacted and no permission granted.";
    }catch(error){status.textContent=error.message||"Unable to save configuration.";}
  });
  browser.storage.local.get(KEY).then(saved=>{
    entries=Array.isArray(saved[KEY])?saved[KEY].filter(item=>item&&
      typeof item.id==="string"&&typeof item.name==="string"&&
      typeof item.url==="string"&&["oauth","none"].includes(item.auth)).slice(0,20):[];
    render();
  }).catch(()=>{status.textContent="Could not read MCP configurations.";});
})();
