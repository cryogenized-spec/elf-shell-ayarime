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
  $("sd-workspace")?.addEventListener("click",()=>{close();void window.AyarimeWorkspaceBridge?.openWorkspace();});
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
  $("sd-save-endpoints")?.addEventListener("click",async()=>{
    try{const resource=validate($("sd-mcp-resource").value.trim(),true),issuer=validate($("sd-mcp-issuer").value.trim());if(new URL(issuer).pathname!=="/")throw Error("Issuer must be origin");await browser.storage.local.set({[KEY]:{resource,issuer}});await browser.storage.session.remove(["elfshell.master.oauthToken.v1","elfshell.master.oauthPending.v1"]);status.textContent="Your endpoints were saved locally. No connection was made. Read-only OAuth for arbitrary servers is not yet enabled.";status.dataset.error="false";}
    catch{status.textContent="Enter your own HTTPS resource ending in /mcp and OAuth issuer origin. Nothing was saved.";status.dataset.error="true";}
  });
  browser.storage.local.get(KEY).then(x=>{const p=x[KEY];if(p){$("sd-mcp-resource").value=p.resource||"";$("sd-mcp-issuer").value=p.issuer||"";status.textContent="Your local connection configuration is saved. No remote service is active.";}}).catch(()=>{status.textContent="Unable to read local configuration.";});
})();