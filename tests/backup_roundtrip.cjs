"use strict";
// Exercise the real dashboard persistence + real background sessions handler,
// not a success stub: all 400 URLs must survive an export/import round-trip.
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const path=require("node:path");
const source=fs.readFileSync(path.resolve(__dirname,"../newtab.js"),"utf8");
const bgSource=fs.readFileSync(path.resolve(__dirname,"../background.js"),"utf8");
const pure=source.slice(0,source.indexOf('$("search-form").addEventListener'));
const store={};
let exported=null,clicked=0,receivedSessionReplaces=0;
class TestURL extends URL {
  static createObjectURL(blob){exported=blob;return "blob:elfshell-test";}
  static revokeObjectURL(){}
}
const local={
  async get(keys){
    const out={};
    for(const key of [].concat(keys))if(Object.hasOwn(store,key))out[key]=structuredClone(store[key]);
    return out;
  },
  async set(updates){Object.assign(store,structuredClone(updates));}
};
const listeners=[];
const browser={
  theme:{update:async()=>{}},
  storage:{local},
  runtime:{
    onInstalled:{addListener(){}},onStartup:{addListener(){}},
    onMessage:{addListener(fn){listeners.push(fn);}},
    async sendMessage(message){
      if(message.type==="elfshell:sessions:mutate:v1"&&message.action==="replace")
        receivedSessionReplaces++;
      for(const fn of listeners){
        const result=fn(message);
        if(result!==undefined)return await result;
      }
      throw Error("No background handler");
    }
  }
};
vm.runInNewContext(bgSource,{browser,URL:TestURL,Date,console,setTimeout,clearTimeout},{timeout:2000});
assert.equal(listeners.length,1,"load real background sessions handler");
const els=new Map();
const document={
  getElementById(id){
    if(!els.has(id))els.set(id,{textContent:"",value:""});
    return els.get(id);
  },
  querySelectorAll(){return [];},
  body:{appendChild(){}},
  createElement(tag){
    assert.equal(tag,"a");
    return {click(){clicked++;},remove(){}};
  }
};
const ctx={URL:TestURL,Blob,Date,Intl,console,structuredClone,setTimeout,clearTimeout,
  window:{},document,browser
};
vm.createContext(ctx);
vm.runInContext(pure,ctx,{timeout:2000});
const run=s=>vm.runInContext(s,ctx,{timeout:2000});
const prefix="https://example.org/?q=";
const longUrl=prefix+"x".repeat(2048-prefix.length);
assert.equal(longUrl.length,2048);
ctx.fullSessions=Array.from({length:10},(_,i)=>({
  name:"Workspace "+i,created:"2026-11-04",
  urls:Array.from({length:40},()=>longUrl)
}));
const sessionsKey="elfshell-workspace-v3:field:sessions";
(async()=>{
  const limit=run("MAX_SETTINGS_BACKUP_BYTES");
  assert.equal(limit,2*1024*1024);
  run("state.sessions=fullSessions");
  run("saveJSON()");
  assert.equal(clicked,1,"export anchor must be clicked");
  assert(exported,"export must create a downloadable Blob");
  assert(exported.size>131072,"exercise previous 128 KiB failure");
  assert(exported.size<limit,"supported 400-URL backup fits new cap");
  const json=JSON.parse(await exported.text());
  assert.equal(json.sessions.length,10);
  assert.equal(json.sessions[0].urls.length,40);

  // Only visual repaint is stubbed; imports call actual persist() and
  // mutateSessions(), which dispatches to actual changeSavedSessions().
  run("applyAppearance=()=>{}; renderLinks=()=>{}; buildSettings=()=>{};");
  ctx.importFile={size:exported.size,text:()=>exported.text()};
  run("state.sessions=[]");
  await run("importJSON(importFile)");
  assert.equal(els.get("settings-message").textContent,"Settings imported successfully.");
  assert.equal(receivedSessionReplaces,1,"import must call the real sessions mutation");
  assert.equal(store[sessionsKey].length,10,"session list must reach storage");
  assert(store[sessionsKey].every(s=>s.urls.length===40),"all 40 URLs per workspace must reach storage");
  assert(store[sessionsKey].every(s=>s.urls.every(url=>url===longUrl)),"all 400 exact URLs must be preserved");
  run("state.sessions=[]");
  assert.equal((await run("freshestSessions()")).length,10,"saved workspaces survive a fresh state read");

  const oldClicks=clicked;
  ctx.huge="https://example.org/?q="+"a".repeat(limit);
  exported=null;
  run("state.links[0].url=huge;saveJSON()");
  assert.equal(exported,null,"oversized settings must not export");
  assert.equal(clicked,oldClicks,"unrestorable backup must not download");
  assert.match(els.get("settings-message").textContent,/2 MiB/);
  const baseline=JSON.stringify(store);
  let readOversize=false;
  ctx.rejectedFile={size:limit+1,async text(){readOversize=true;return "{}";}};
  await run("importJSON(rejectedFile)");
  assert.equal(readOversize,false,"oversized import should be rejected before read");
  assert.equal(JSON.stringify(store),baseline,"oversized import must not alter storage");
  assert.match(els.get("settings-message").textContent,/File is too large/);
  ctx.invalidFile={size:70,async text(){return '{"format":"elfshell-settings","version":5,"links":[]}';}};
  await run("importJSON(invalidFile)");
  assert.equal(JSON.stringify(store),baseline,"invalid import must not alter storage");
  assert.match(els.get("settings-message").textContent,/Invalid settings or URL/);
  console.log("Backup round-trip QA PASS: real stored 10 x 40 URLs, 128 KiB regression, bounded import/export.");
})().catch(error=>{console.error(error);process.exitCode=1;});
