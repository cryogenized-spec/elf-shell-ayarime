"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const m=JSON.parse(read("manifest.json"));
const KEY="elfshell:browser-integration:v1";
const CURSOR_ID="elfshell-cursors-global-v1";
const SPELL_ID="elfspell-global-v1";
const SCOPE="https://*/*";
assert(m.optional_host_permissions.includes(SCOPE),"broad grant must remain optional");
assert(!m.host_permissions,"never require blanket site permission on installation");
assert(m.background.scripts.includes("integration/background.js"));
assert(m.web_accessible_resources.some(r=>
  r.resources.includes("assets/cursors/states/*.png")&&r.matches.includes(SCOPE)),
  "only bundled cursor images should be web-accessible");
const html=read("newtab.html"),ui=read("integration/ui.js");
for(const id of ["integration-cursors","integration-spelling","integration-apply",
  "integration-revoke","integration-status","integration-permission"])
  assert(html.includes('id="'+id+'"'),"missing user-facing integration control "+id);
assert(html.includes('src="integration/ui.js"'));
assert(ui.includes("browser.permissions.request({origins:[scope]})"),"consent must be explicit");
const applyBody=ui.split('apply.addEventListener("click"')[1];
assert(applyBody.indexOf("browser.permissions.request")<applyBody.indexOf("await request"),
  "Firefox permission request must start in trusted click handler before awaiting");
assert(!read("integration/cursors.js").includes("fetch("),"cursor mode must not transmit page data");
assert(!read("integration/cursors.js").includes("innerHTML"),"no page HTML mutation");
assert(read("scripts/package.py").includes("'integration/background.js'"),
  "runtime ZIP must carry integration service");

async function acceptance() {
  const storage=new Map();
  const registrations=new Map();
  const events={onRemoved:[],onAdded:[],onStartup:[],onInstalled:[]};
  const messages=[],injections=[];
  let wildcard=false,handler=null;
  const browser={
    runtime:{
      getURL:relative=>"moz-extension://qa/"+relative,
      onMessage:{addListener:cb=>{handler=cb;}},
      onStartup:{addListener:cb=>events.onStartup.push(cb)},
      onInstalled:{addListener:cb=>events.onInstalled.push(cb)}
    },
    storage:{local:{
      get:async keys=>{
        const names=Array.isArray(keys)?keys:[keys];
        return Object.fromEntries(names.filter(k=>storage.has(k)).map(k=>[k,storage.get(k)]));
      },
      set:async values=>{for(const [k,v] of Object.entries(values))storage.set(k,v);}
    }},
    permissions:{
      contains:async ({origins})=>wildcard&&origins.includes(SCOPE),
      onAdded:{addListener:cb=>events.onAdded.push(cb)},
      onRemoved:{addListener:cb=>events.onRemoved.push(cb)}
    },
    scripting:{
      getRegisteredContentScripts:async()=>[...registrations.values()],
      registerContentScripts:async scripts=>{
        for(const script of scripts){
          if(registrations.has(script.id))throw Error("duplicate registration");
          registrations.set(script.id,script);
        }
      },
      unregisterContentScripts:async ({ids})=>{
        for(const id of ids)registrations.delete(id);
      },
      executeScript:async data=>{injections.push({type:"js",...data});},
      insertCSS:async data=>{injections.push({type:"css",...data});}
    },
    tabs:{
      query:async()=>[
        {id:7,url:"https://example.com/editor",incognito:false},
        {id:8,url:"about:addons",incognito:false},
        {id:9,url:"https://secret.example/",incognito:true}
      ],
      sendMessage:async(id,message)=>{messages.push({id,message});}
    }
  };
  const logs=[];
  vm.runInNewContext(read("integration/background.js"),{
    browser,URL,console:{error:(...args)=>logs.push(args)}
  },{timeout:5000});
  const flush=()=>new Promise(resolve=>setImmediate(resolve));
  await flush();
  const dashboard={url:"moz-extension://qa/newtab.html"};
  const stranger={url:"https://example.com/editor",tab:{id:7,url:"https://example.com/editor"},frameId:0};
  const set=mode=>handler({type:"elfshell:integration:set",modes:mode},dashboard);
  const get=()=>handler({type:"elfshell:integration:get"},dashboard);
  assert.equal((await get()).modes.cursorMode,"station","safe legacy cursor default");
  assert.equal((await get()).modes.spellMode,"sites","safe legacy spelling default");
  assert.equal(registrations.size,0,"no content scripts before a grant");
  assert.equal((await set({cursorMode:"all",spellMode:"all"})).ok,false,
    "broad request must not work before Firefox permission");
  assert.equal(storage.has(KEY),false,"denied request must not persist a granted mode");
  wildcard=true;
  for(const callback of events.onAdded)callback({origins:[SCOPE]});
  await flush();
  assert.equal(registrations.size,0,
    "Firefox grant alone must not turn on either browser-wide feature");
  const blocked=await handler({type:"elfshell:integration:set",
    modes:{cursorMode:"all",spellMode:"all"}},stranger);
  assert.equal(blocked.ok,false,"website script must not set privileged preferences");
  const activated=await set({cursorMode:"all",spellMode:"all"});
  assert.equal(activated.ok,true,JSON.stringify(activated));
  assert(registrations.has(CURSOR_ID));
  assert(registrations.has(SPELL_ID));
  assert.deepEqual([...registrations.get(SPELL_ID).matches],[SCOPE]);
  assert(injections.some(x=>x.type==="js"&&x.target.tabId===7&&
    x.files.includes("integration/cursors.js")),"existing public HTTPS tab needs cursor injection");
  assert(!injections.some(x=>x.target.tabId===8||x.target.tabId===9),
    "never inject into privileged or incognito tabs");
  const authorised=await handler({type:"elfshell:integration:cursor-allowed"},stranger);
  assert.equal(authorised.allowed,true);
  assert.equal((await handler({type:"elfshell:integration:cursor-allowed"},{
    ...stranger,url:"https://different.example/"
  })).allowed,false,"origin mismatch must fail");
  assert.equal((await handler({type:"elfshell:integration:cursor-allowed"},{
    ...stranger,tab:{...stranger.tab,incognito:true}
  })).allowed,false,"incognito must not get global integration");

  // Switching to native spelling must also unregister previously enabled sites.
  registrations.set("elfspell-6874747073",{id:"elfspell-6874747073",
    matches:["https://example.com/*"]});
  const disabled=await set({cursorMode:"all",spellMode:"off"});
  assert.equal(disabled.ok,true);
  assert(registrations.has(CURSOR_ID));
  assert(!registrations.has(SPELL_ID));
  assert(!registrations.has("elfspell-6874747073"));
  assert(messages.some(v=>v.id===7&&v.message.type==="elfshell:spell:disable"),
    "open editors need native spelling restored");
  const restoring=await set({cursorMode:"station",spellMode:"sites"});
  assert.equal(restoring.ok,true);
  assert(!registrations.has(CURSOR_ID));
  assert(!registrations.has(SPELL_ID));
  assert.equal(await handler({type:"elfshell:integration:cursor-allowed"},stranger).then(r=>r.allowed),
    false);
  // Test a Firefox revocation after configuration, without silent regrant.
  assert.equal((await set({cursorMode:"all",spellMode:"all"})).ok,true);
  wildcard=false;
  for(const callback of events.onRemoved)callback({origins:[SCOPE]});
  await flush();
  assert(!registrations.has(CURSOR_ID)&&!registrations.has(SPELL_ID),
    "revocation must unregister both all-site content scripts");
  assert.equal((await get()).allowed,false);
  assert.equal((await handler({type:"elfshell:integration:cursor-allowed"},stranger)).allowed,false);
  assert.equal(logs.length,0,"mock lifecycle should not generate integration errors");
}
acceptance().then(()=>console.log(
  "Browser Integration QA PASS: explicit consent, mode transitions, site isolation, native spelling restoration, revocation and packaging."
)).catch(error=>{console.error(error);process.exitCode=1;});