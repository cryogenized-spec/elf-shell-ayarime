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
      '<p class="quiet" id="unified-ai-pause-status" role="status"></p>';
    parent.append(box);
    const pause=box.querySelector("#unified-ai-pause");
    const status=box.querySelector("#unified-ai-pause-status");
    let enabled=true;
    async function sync() {
      try {
        const values=await browser.storage.local.get(AI_KEY);
        enabled=values[AI_KEY]!==false;
        pause.textContent=enabled?"Pause Ayarime AI":"Resume Ayarime AI";
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
    browser.storage.onChanged?.addListener((changes,area)=>{
      if(area==="local"&&Object.hasOwn(changes,AI_KEY))
        void sync();
    });
    void sync();
  }
  if(isSidebar) {
    // Sidebar Settings only. Opening the Hub is centralized in its header.
    createPrefs(document.getElementById("ayarime-sidebar-pane-settings"));
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
  const guide=make("section","frame unified-controls unified-mcp-guide");
  guide.setAttribute("aria-label","Google MCP developer configuration");
  guide.innerHTML='<h2>Google MCP setup</h2>'+
    '<p class="quiet">Developer configuration only; saving these settings neither signs you in nor starts a tool connection.</p>'+
    '<div class="unified-mcp-guides">'+
    '<a href="https://console.cloud.google.com/projectcreate" target="_blank" rel="noopener noreferrer">Create Google Cloud project</a>'+
    '<a href="https://console.cloud.google.com/apis/library" target="_blank" rel="noopener noreferrer">Google API library</a>'+
    '<a href="https://console.cloud.google.com/auth/clients" target="_blank" rel="noopener noreferrer">Google OAuth clients</a>'+
    '<a href="https://dash.cloudflare.com/" target="_blank" rel="noopener noreferrer">Cloudflare dashboard</a>'+
    '<a href="https://github.com/cryogenized-spec/Google-master-worker-MCP" target="_blank" rel="noopener noreferrer">Google Master Worker reference</a></div>'+
    '<p class="quiet">A public Google OAuth client ID identifies your app; it is not an access token. Do not paste API keys or client secrets into these fields.</p>'+
    '<label for="unified-google-client-id">Public Google OAuth client ID</label>'+
    '<input id="unified-google-client-id" type="text" maxlength="180" autocomplete="off" spellcheck="false" placeholder="123456789-abc.apps.googleusercontent.com">'+
    '<button id="unified-google-save-client" type="button" class="mini">Save public client ID</button>'+
    '<div class="unified-mcp-form"><label for="unified-google-resource">Self-hosted HTTPS MCP resource</label>'+
    '<input id="unified-google-resource" type="url" maxlength="400" spellcheck="false" placeholder="https://my-server.example/mcp">'+
    '<label for="unified-google-issuer">OAuth issuer origin</label>'+
    '<input id="unified-google-issuer" type="url" maxlength="400" spellcheck="false" placeholder="https://auth.example">'+
    '<button id="unified-google-save-endpoints" type="button" class="mini">Save unconnected endpoint settings</button></div>'+
    '<p id="unified-google-status" class="quiet" role="status"></p>';
  parent.append(guide);
  const googleStatus=guide.querySelector("#unified-google-status");
  const clientInput=guide.querySelector("#unified-google-client-id");
  const resourceInput=guide.querySelector("#unified-google-resource");
  const issuerInput=guide.querySelector("#unified-google-issuer");
  const CLIENT_KEY="elfshell.mcp.publicGoogleClient.v1";
  const PROFILE_KEY="elfshell.mcp.userProfile.v1";
  const publicClient=/^[0-9]+-[a-z0-9_-]+\.apps\.googleusercontent\.com$/i;
  guide.querySelector("#unified-google-save-client").addEventListener("click",async()=>{
    const value=clientInput.value.trim();
    if(value&&!publicClient.test(value)){
      googleStatus.textContent="Invalid public Google client ID. Nothing saved.";return;
    }
    try{
      if(value)await browser.storage.local.set({[CLIENT_KEY]:value});
      else await browser.storage.local.remove(CLIENT_KEY);
      googleStatus.textContent=value
        ?"Public client ID saved locally. No authorization attempted."
        :"Public client ID cleared.";
    }catch{googleStatus.textContent="Unable to save public Google client ID.";}
  });
  guide.querySelector("#unified-google-save-endpoints").addEventListener("click",async()=>{
    try{
      const resource=normalizeURL(resourceInput.value.trim());
      const issuer=normalizeURL(issuerInput.value.trim());
      if(new URL(resource).pathname!=="/mcp"||new URL(issuer).pathname!=="/")
        throw Error("MCP resource must end with /mcp and issuer must be an HTTPS origin.");
      await browser.storage.local.set({[PROFILE_KEY]:{resource,issuer}});
      googleStatus.textContent="Endpoint profile saved locally; not connected and no OAuth performed.";
    }catch(error){googleStatus.textContent=error.message||"Invalid endpoint profile.";}
  });
  browser.storage.local.get([CLIENT_KEY,PROFILE_KEY]).then(saved=>{
    if(typeof saved[CLIENT_KEY]==="string")clientInput.value=saved[CLIENT_KEY];
    if(saved[PROFILE_KEY]&&typeof saved[PROFILE_KEY]==="object"){
      resourceInput.value=saved[PROFILE_KEY].resource||"";
      issuerInput.value=saved[PROFILE_KEY].issuer||"";
    }
  }).catch(()=>{googleStatus.textContent="Could not restore saved Google developer settings.";});
  const template=section.querySelector("#unified-mcp-google");
  for(const [key,[label]] of Object.entries(google)) {
    const option=document.createElement("option");
    option.value=key;
    option.textContent=label;
    template.append(option);
  }
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
