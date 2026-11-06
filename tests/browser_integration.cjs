"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const m=JSON.parse(read("manifest.json"));
const KEY="elfshell:browser-integration:v1",SCOPE="https://*/*";
const SPELL_ID="elfspell-global-v1",CURSOR_ID="elfshell-cursors-global-v1";
assert(m.optional_host_permissions.includes(SCOPE),"website access must be optional");
assert(!m.host_permissions,"no required blanket host access");
assert(m.background.scripts.includes("integration/background.js"));
assert(!m.web_accessible_resources?.some(x=>x.resources.some(r=>r.includes("cursors"))),
  "website cursor assets must not be exposed");
const html=read("newtab.html"),ui=read("integration/ui.js"),
  pkg=read("scripts/package.py");
for(const id of ["integration-spelling","integration-apply","integration-revoke",
  "integration-status","integration-permission"])
  assert(html.includes('id="'+id+'"'),"missing spelling integration option: "+id);
assert(!html.includes('id="integration-cursors"'),"browser-wide cursor selector must be removed");
assert(!pkg.includes("'integration/cursors.js'"),"no website cursor script in AMO");
assert(pkg.includes("'integration/background.js'"),"spell permission controller must be packaged");
assert(ui.includes("browser.permissions.request({origins:[SCOPE]})"),"explicit Firefox grant missing");
const apply=ui.split('apply.addEventListener("click"')[1];
assert(apply.indexOf("browser.permissions.request")<apply.indexOf("await request"),
  "permission request must originate from click gesture, before async work");

async function acceptance(){
  const storage=new Map(),scripts=new Map();
  scripts.set(CURSOR_ID,{id:CURSOR_ID,matches:[SCOPE]});
  const messages=[],injections=[],events={onRemoved:[],onAdded:[],onStartup:[],onInstalled:[]};
  let wildcard=false,handler=null,registerCount=0;
  const browser={
    runtime:{
      getURL:p=>"moz-extension://qa/"+p,
      onMessage:{addListener:fn=>{handler=fn;}},
      onStartup:{addListener:fn=>events.onStartup.push(fn)},
      onInstalled:{addListener:fn=>events.onInstalled.push(fn)}
    },
    storage:{local:{
      get:async key=>Object.fromEntries([key].filter(k=>storage.has(k)).map(k=>[k,storage.get(k)])),
      set:async obj=>{for(const [k,v] of Object.entries(obj))storage.set(k,v);}
    }},
    permissions:{
      contains:async()=>wildcard,
      onRemoved:{addListener:fn=>events.onRemoved.push(fn)},
      onAdded:{addListener:fn=>events.onAdded.push(fn)}
    },
    scripting:{
      getRegisteredContentScripts:async()=>[...scripts.values()],
      registerContentScripts:async list=>{
        for(const s of list){
          registerCount++;
          if(scripts.has(s.id))throw Error("duplicate registration");
          scripts.set(s.id,s);
        }
      },
      unregisterContentScripts:async ({ids})=>{ids.forEach(id=>scripts.delete(id));},
      insertCSS:async data=>injections.push({type:"css",...data}),
      executeScript:async data=>injections.push({type:"js",...data})
    },
    tabs:{
      query:async()=>[
        {id:4,url:"https://example.com/editor",incognito:false},
        {id:5,incognito:false}, // no URL after Firefox permission removal
        {id:6,url:"about:addons",incognito:false},
        {id:7,url:"https://private.example",incognito:true}
      ],
      sendMessage:async(id,message)=>messages.push({id,message})
    }
  };
  const errors=[];
  vm.runInNewContext(read("integration/background.js"),{
    browser,URL,console:{warn:(...v)=>errors.push(v),error:(...v)=>errors.push(v)}
  },{timeout:5000});
  const station={url:"moz-extension://qa/newtab.html"},site={url:"https://example.com/",tab:{id:4}};
  const get=()=>handler({type:"elfshell:integration:get"},station);
  const set=spellMode=>handler({type:"elfshell:integration:set",modes:{spellMode}},station);
  let state=await get();
  assert.equal(state.modes.spellMode,"sites");
  assert.equal(scripts.has(CURSOR_ID),false,"legacy site cursor registration must be removed");
  assert.equal(scripts.has(SPELL_ID),false);
  assert.equal((await set("all")).ok,false,"consent must precede global enable");
  assert.equal(storage.has(KEY),false);
  wildcard=true;
  for(const event of events.onAdded)event({origins:[SCOPE]});
  state=await get();
  assert.equal(state.allowed,true);
  assert.equal(scripts.has(SPELL_ID),false,"grant alone must not enable spelling");
  assert.equal((await handler({type:"elfshell:integration:set",modes:{spellMode:"all"}},site)).ok,false,
    "website sender must never set modes");
  // Concurrent status reads and Apply must serialize registration.
  const outcomes=await Promise.all([set("all"),get(),get()]);
  assert.equal(outcomes[0].ok,true,JSON.stringify(outcomes[0]));
  assert.equal(registerCount,1,"concurrent status must not register scripts twice");
  assert.equal(scripts.has(SPELL_ID),true);
  assert(injections.some(x=>x.type==="js"&&x.target.tabId===4&&
    x.files.includes("spelling/content.js")));
  assert(!injections.some(x=>x.target.tabId===5||x.target.tabId===6||x.target.tabId===7));
  assert(messages.some(x=>x.id===5&&x.message.type==="elfshell:spell:revalidate"),
    "revalidation must not require tab URL or tabs permission");
  scripts.set("elfspell-example",{id:"elfspell-example",matches:["https://example.com/*"]});
  assert.equal((await set("off")).ok,true);
  assert.equal(scripts.has(SPELL_ID),false);
  assert.equal(scripts.has("elfspell-example"),false);
  assert(messages.some(x=>x.message.type==="elfshell:spell:disable"));
  assert.equal((await set("sites")).ok,true);
  assert.equal((await set("all")).ok,true);
  wildcard=false;
  for(const event of events.onRemoved)event({origins:[SCOPE]});
  state=await get();
  assert.equal(state.allowed,false);
  assert.equal(scripts.has(SPELL_ID),false,"revocation must unregister global spellcheck");
  assert(!scripts.has(CURSOR_ID));
  assert(messages.some(x=>x.id===5&&x.message.type==="elfshell:integration:cursor-sync"),
    "cleanup of obsolete cursor script must work without URL access");
  assert.equal(errors.length,0,JSON.stringify(errors));
}
acceptance().then(()=>console.log(
  "Spell-only integration QA PASS: explicit grants, no site cursors, serialization, revocation, privileged isolation and native fallback."
)).catch(error=>{console.error(error);process.exitCode=1;});
