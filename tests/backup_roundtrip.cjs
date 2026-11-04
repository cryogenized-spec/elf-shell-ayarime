"use strict";
// The maximum supported 10 saved workspaces × 40 tabs must export and
// re-import successfully, even with long (but valid) 2048-char URLs.
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const path=require("node:path");
const source=fs.readFileSync(path.resolve(__dirname,"../newtab.js"),"utf8");
const pure=source.slice(0,source.indexOf('$("search-form").addEventListener'));
let exported=null,clicked=0,revoked=0,mutations=0;
class TestURL extends URL {
  static createObjectURL(blob){exported=blob;return "blob:elfshell-test";}
  static revokeObjectURL(){revoked++;}
}
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
  window:{},document,
  browser:{storage:{local:{set:async()=>{}}}}
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
(async()=>{
  const limit=run("MAX_SETTINGS_BACKUP_BYTES");
  assert.equal(limit,2*1024*1024);
  run("state.sessions=fullSessions");
  run("saveJSON()");
  assert.equal(clicked,1,"export anchor should have been clicked");
  assert(exported,"export must produce a downloadable Blob");
  assert(exported.size>131072,"regression needs a backup above old 128 KiB cap");
  assert(exported.size<limit,"legal maximum workspace set should fit the new cap");
  const json=JSON.parse(await exported.text());
  assert.equal(json.sessions.length,10);
  assert.equal(json.sessions[0].urls.length,40);
  // No unrelated browser DOM needs to be exercised here.
  run("persist=async()=>true; mutateSessions=async()=>{return {ok:true}}; applyAppearance=()=>{}; renderLinks=()=>{}; buildSettings=()=>{};");
  ctx.importFile={size:exported.size,text:()=>exported.text()};
  run("state.sessions=[]");
  await run("importJSON(importFile)");
  assert.equal(run("state.sessions.length"),10,"previously exported workspaces must restore");
  assert.equal(run("state.sessions[9].urls.length"),40);
  assert.equal(els.get("settings-message").textContent,"Settings imported successfully.");
  // Keep the limit bounded and apply the same ceiling to both directions.
  const oldClicks=clicked;
  ctx.huge="https://example.org/?q="+"a".repeat(limit);
  exported=null;
  run("state.links[0].url=huge;saveJSON()");
  assert.equal(exported,null,"overlarge settings must not be exported");
  assert.equal(clicked,oldClicks,"no download for a backup we cannot restore");
  assert.match(els.get("settings-message").textContent,/2 MiB/);
  let readOversize=false;
  ctx.rejectedFile={size:limit+1,async text(){readOversize=true;return "{}";}};
  const previous=run("state.sessions.length");
  await run("importJSON(rejectedFile)");
  assert.equal(readOversize,false,"oversized import must not be read");
  assert.equal(run("state.sessions.length"),previous,"oversized import must not mutate state");
  assert.match(els.get("settings-message").textContent,/File is too large/);
  console.log("Backup round-trip QA PASS: 10 x 40 URLs, 128 KiB regression, 2 MiB export/import bound.");
})().catch(error=>{console.error(error);process.exitCode=1;});
