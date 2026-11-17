"use strict";
(() => {
  const $=id=>document.getElementById(id),panel=$("station-drawer"),scrim=$("station-scrim"),openButton=$("station-drawer-open");
  if(!panel||!scrim||!openButton)return;
  const tabs=[...panel.querySelectorAll('[role="tab"]')],panes=tabs.map(t=>$(t.getAttribute("aria-controls")));
  let previous=null;
  function select(name,focus=true){const tab=tabs.find(t=>t.dataset.tab===name)||tabs[0];tabs.forEach((t,i)=>{const active=t===tab;t.setAttribute("aria-selected",String(active));t.tabIndex=active?0:-1;panes[i].hidden=!active;});if(focus)tab.focus();}
  function show(name="station"){previous=document.activeElement;panel.hidden=false;scrim.hidden=false;openButton.setAttribute("aria-expanded","true");select(name);}
  function close(){panel.hidden=true;scrim.hidden=true;openButton.setAttribute("aria-expanded","false");(previous?.isConnected?previous:openButton).focus();}
  openButton.addEventListener("click",()=>panel.hidden?show():close());
  $("station-drawer-close").addEventListener("click",close);scrim.addEventListener("click",close);
  document.addEventListener("keydown",e=>{
    if(panel.hidden)return;
    if(e.key==="Escape"){e.preventDefault();close();}
    if(e.key==="Tab"){const x=[...panel.querySelectorAll('button:not(:disabled),a[href],input:not(:disabled),select:not(:disabled)')].filter(n=>!n.closest("[hidden]"));if(e.shiftKey&&document.activeElement===x[0]){e.preventDefault();x.at(-1).focus();}else if(!e.shiftKey&&document.activeElement===x.at(-1)){e.preventDefault();x[0].focus();}}
  });
  tabs.forEach((t,i)=>{t.addEventListener("click",()=>select(t.dataset.tab,false));t.addEventListener("keydown",e=>{if(!["ArrowLeft","ArrowRight","Home","End"].includes(e.key))return;e.preventDefault();const j=e.key==="Home"?0:e.key==="End"?tabs.length-1:(i+(e.key==="ArrowRight"?1:-1)+tabs.length)%tabs.length;select(tabs[j].dataset.tab);});});
  $("google-master-toggle")?.addEventListener("click",e=>{e.preventDefault();show("mcp");});
  // Mirror the existing persisted AI switch; a single underlying setting
  // remains authoritative, regardless of whether the old menu is open.
  const aiToggle=$("ai-module-toggle"),quickAi=$("sd-ai-toggle");
  function syncAi(){
    if(!aiToggle||!quickAi)return;
    const active=aiToggle.getAttribute("aria-pressed")==="true";
    quickAi.textContent=active?"✧ DISABLE AYARIME AI":"✧ ENABLE AYARIME AI";
    quickAi.setAttribute("aria-pressed",String(active));
    quickAi.disabled=aiToggle.disabled;
  }
  if(aiToggle&&quickAi){
    quickAi.addEventListener("click",()=>{aiToggle.click();});
    new MutationObserver(syncAi).observe(aiToggle,{attributes:true,attributeFilter:["disabled","aria-pressed"]});
    syncAi();
  }
  $("sd-open-hub")?.addEventListener("click",()=>{
    try{browser.sidebarAction?.close?.().catch(()=>{});}catch{}
    close();
    void window.AyarimeWorkspaceBridge?.openAssistant();
  });
  $("sd-workspace")?.addEventListener("click",()=>{
    try{browser.sidebarAction?.close?.().catch(()=>{});}catch{}
    close();void window.AyarimeWorkspaceBridge?.openWorkspace();
  });
  $("sd-chat")?.addEventListener("click",async()=>{try{if(!browser.sidebarAction?.open)throw Error("unsupported");await browser.sidebarAction.open();}catch{$("sd-chat-status").textContent="Use Firefox's sidebar selector to open Ayarime."; }});
  [["sd-settings","settings-toggle"],["sd-access","permissions-toggle"],["sd-sessions","sessions-toggle"],["sd-rss","feeds-toggle"]].forEach(([a,b])=>$(a)?.addEventListener("click",()=>{close();$(b)?.click();}));
  const sites=Object.freeze({gmail:"https://gmailmcp.googleapis.com/mcp/v1",drive:"https://drivemcp.googleapis.com/mcp/v1",docs:"https://docsmcp.googleapis.com/mcp/v1",sheets:"https://sheetsmcp.googleapis.com/mcp/v1",calendar:"https://calendarmcp.googleapis.com/mcp/v1"});
  const product=$("sd-google-service");product?.addEventListener("change",()=>{$("sd-google-url").value=sites[product.value];});if(product)$("sd-google-url").value=sites[product.value];
  $("sd-provider")?.addEventListener("change",()=>{const self=$("sd-provider").value==="self";$("sd-self").hidden=!self;$("sd-official").hidden=self;});
  function validate(value,mcp=false){
    const u=new URL(value);
    if(u.protocol!=="https:"||u.port||u.username||u.password||u.search||u.hash||!u.hostname.includes(".")||/^(localhost|127\.)/i.test(u.hostname)||/(^|\.)cryogenized\.workers\.dev$/i.test(u.hostname)||(mcp&&u.pathname!=="/mcp"))throw Error("Invalid HTTPS endpoint");
    return u.href.replace(/\/$/,"");
  }
  const KEY="elfshell.mcp.userProfile.v1",status=$("sd-mcp-status");
  const CLIENT_KEY="elfshell.mcp.publicGoogleClient.v1";
  const clientInput=$("sd-google-client-id");
  $("sd-save-client-id")?.addEventListener("click",async()=>{
    const value=clientInput.value.trim();
    if(value && !/^[0-9]+-[a-z0-9_-]+\.apps\.googleusercontent\.com$/i.test(value)){
      status.textContent="Google client ID must end in .apps.googleusercontent.com. Nothing was stored.";
      status.dataset.error="true";return;
    }
    try {
      if(value) await browser.storage.local.set({[CLIENT_KEY]:value});
      else await browser.storage.local.remove(CLIENT_KEY);
      status.textContent=value ?
        "Public Google client ID saved locally. No connection, consent or token was created." :
        "Public Google client ID cleared. No Google connection was active.";
      status.dataset.error="false";
    } catch {
      status.textContent="Could not update local Google client settings.";
      status.dataset.error="true";
    }
  });
  browser.storage.local.get(CLIENT_KEY).then(x=>{
    if(clientInput && typeof x[CLIENT_KEY]==="string") clientInput.value=x[CLIENT_KEY];
  }).catch(()=>{status.textContent="Could not read saved Google client settings.";});
  $("sd-save-endpoints")?.addEventListener("click",async()=>{
    try{const resource=validate($("sd-mcp-resource").value.trim(),true),issuer=validate($("sd-mcp-issuer").value.trim());if(new URL(issuer).pathname!=="/")throw Error("Issuer must be origin");await browser.storage.local.set({[KEY]:{resource,issuer}});await browser.storage.session.remove(["elfshell.master.oauthToken.v1","elfshell.master.oauthPending.v1"]);status.textContent="Your endpoints were saved locally. No connection was made. Read-only OAuth for arbitrary servers is not yet enabled.";status.dataset.error="false";}
    catch{status.textContent="Enter your own HTTPS resource ending in /mcp and OAuth issuer origin. Nothing was saved.";status.dataset.error="true";}
  });
  browser.storage.local.get(KEY).then(x=>{const p=x[KEY];if(p){$("sd-mcp-resource").value=p.resource||"";$("sd-mcp-issuer").value=p.issuer||"";status.textContent="Your local connection configuration is saved. No remote service is active.";}}).catch(()=>{status.textContent="Unable to read local configuration.";});

  // These first-party Station actions call the *existing* controls. The old
  // two-column menu remains in the DOM for keyboard commands but is not shown.
  [["sd-notes","notes-toggle"],["sd-recents","recents-toggle"],
   ["sd-housekeeping","housekeeping-toggle"]].forEach(([a,b])=>{
    $(a)?.addEventListener("click",()=>{close();$(b)?.click();});
  });
  // A real user gesture is required to close the Firefox sidebar. It is not
  // forcibly closed from arbitrary web pages or extension startup timers.
  const AI_KEY="elfshell.station.launcherVisible.v1";
  const launcherCheck=$("sd-launcher-visible");
  async function applyLauncher() {
    try {
      const data=await browser.storage.local.get(AI_KEY);
      const visible=data[AI_KEY]!==false;
      openButton.hidden=!visible;
      if(launcherCheck)launcherCheck.checked=visible;
    }catch{
      openButton.hidden=false;
      if(launcherCheck)launcherCheck.checked=true;
    }
  }
  launcherCheck?.addEventListener("change",async()=>{
    try {
      await browser.storage.local.set({[AI_KEY]:launcherCheck.checked});
      await applyLauncher();
    }catch{
      launcherCheck.checked=!launcherCheck.checked;
      status.textContent="Could not save Station visibility.";
    }
  });
  browser.storage.onChanged?.addListener((changes,area)=>{
    if(area==="local"&&Object.hasOwn(changes,AI_KEY))void applyLauncher();
  });
  document.addEventListener("keydown",event=>{
    if(event.altKey&&event.shiftKey&&event.key.toLowerCase()==="a"&&
       !event.ctrlKey&&!event.metaKey){
      event.preventDefault();
      panel.hidden?show("station"):close();
    }
  });
  void applyLauncher();

  // Named MCP *registry* only: recording an HTTPS endpoint does NOT mean
  // OAuth, the MCP initialize handshake or tools/list has completed.
  const REGISTRY_KEY="elfshell.mcp.registry.v1",form=$("sd-mcp-add");
  const list=$("sd-mcp-list"),message=$("sd-mcp-list-status");
  let entries=[];
  function registryUrl(input) {
    const url=new URL(input);
    const host=url.hostname.toLowerCase().replace(/\.$/,"");
    const ipv4=/^(\d{1,3}\.){3}\d{1,3}$/.test(host);
    if(url.protocol!=="https:"||url.username||url.password||url.port||
       url.search||url.hash||url.href.length>400||!host.includes(".")||
       ipv4||host.includes(":")||host.endsWith(".local")||host.endsWith(".internal")||
       host.endsWith(".localhost")||host.endsWith(".test")||host.endsWith(".invalid"))
      throw Error("Use a public HTTPS MCP endpoint without embedded credentials, query tokens or local addresses.");
    return url.toString();
  }
  function note(value){if(message)message.textContent=value;}
  function renderRegistry() {
    if(!list)return;
    list.replaceChildren();
    if(!entries.length){
      const p=document.createElement("p");
      p.className="sd-note";
      p.textContent="No custom servers registered. Google's official endpoints are suggested above.";
      list.append(p);return;
    }
    for(const item of entries){
      const card=document.createElement("article");card.className="sd-mcp-entry";
      const heading=document.createElement("strong");heading.textContent=item.name;
      const url=document.createElement("small");url.textContent=item.url;
      const statusLine=document.createElement("span");statusLine.className="sd-configured";
      statusLine.textContent=item.auth==="oauth"
        ?"Configured · OAuth needed · not connected"
        :"Configured · no-auth transport pending · not connected";
      const actions=document.createElement("div");actions.className="sd-connection-actions";
      const inspect=document.createElement("button");
      inspect.type="button";inspect.textContent="Inspect";inspect.dataset.registryInspect=item.id;
      const refresh=document.createElement("button");
      refresh.type="button";refresh.disabled=true;refresh.textContent="Refresh tools";
      refresh.title="Available after the secure MCP transport, authorization and tool discovery are implemented.";
      const remove=document.createElement("button");
      remove.type="button";remove.textContent="Remove";remove.dataset.registryRemove=item.id;
      actions.append(inspect,refresh,remove);
      card.append(heading,url,statusLine,actions);list.append(card);
    }
  }
  async function saveRegistry(){
    await browser.storage.local.set({[REGISTRY_KEY]:entries});
    renderRegistry();
  }
  browser.storage.local.get(REGISTRY_KEY).then(data=>{
    const saved=data[REGISTRY_KEY];
    entries=Array.isArray(saved)?saved.filter(x=>x&&typeof x.id==="string"&&
      typeof x.name==="string"&&typeof x.url==="string"&&
      ["oauth","none"].includes(x.auth)).slice(0,20):[];
    renderRegistry();
  }).catch(()=>note("Could not read saved MCP configurations."));
  form?.addEventListener("submit",async event=>{
    event.preventDefault();
    const name=$("sd-mcp-name").value.trim();
    const auth=$("sd-mcp-auth").value;
    try {
      const url=registryUrl($("sd-mcp-url").value.trim());
      if(name.length<2||name.length>70||!["oauth","none"].includes(auth))
        throw Error("Enter a name of 2–70 characters and a supported authentication choice.");
      if(entries.length>=20)throw Error("The registry limit is 20 servers. Remove an old one first.");
      if(entries.some(x=>x.url===url))throw Error("That endpoint is already registered.");
      entries=[...entries,{id:crypto.randomUUID(),name,url,auth}];
      await saveRegistry();
      form.reset();
      note(name+" saved locally. No credentials were requested and no connection was made.");
    }catch(e){note(e.message||"Could not save server.");}
  });
  list?.addEventListener("click",async event=>{
    const button=event.target.closest("button");
    if(!button)return;
    const id=button.dataset.registryRemove||button.dataset.registryInspect;
    const item=entries.find(x=>x.id===id);
    if(!item)return;
    if(button.dataset.registryInspect){
      note(item.name+" · "+item.auth.toUpperCase()+" · not connected. Tools have not been discovered. This is an endpoint configuration, not an authorised session.");
      return;
    }
    if(button.dataset.registryRemove&&confirm("Remove "+item.name+" from your local MCP list?")){
      const previous=entries;entries=entries.filter(x=>x.id!==id);
      try {await saveRegistry();note(item.name+" removed. No external server was contacted.");}
      catch{entries=previous;renderRegistry();note("Unable to remove configuration.");}
    }
  });
  $("sd-use-google")?.addEventListener("click",()=>{
    $("sd-mcp-name").value="Google "+product.selectedOptions[0].textContent;
    $("sd-mcp-url").value=sites[product.value];
    $("sd-mcp-auth").value="oauth";
    $("sd-mcp-name").focus();
    note("Google endpoint selected. Add it to your list; OAuth onboarding requires Developer Preview eligibility.");
  });
})();