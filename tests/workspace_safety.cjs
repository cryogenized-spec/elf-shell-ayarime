'use strict';
// Two independently loaded dashboard scripts share mocked Firefox storage.
// A stale page changing focus must not clobber the other page's newer note.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const source=fs.readFileSync(path.resolve(__dirname,'../newtab.js'),'utf8');
const pure=source.slice(0,source.indexOf('$("search-form").addEventListener'));
const store={};
let failWrites=false;
const local={
  async get(keys){const out={};for(const k of [].concat(keys))out[k]=store[k];return out;},
  async set(updates){if(failWrites)throw Error('Simulated storage write failure');Object.assign(store,JSON.parse(JSON.stringify(updates)));}
};
const status=()=>({textContent:''});
function realm(){
  const els=new Map();
  const ctx={URL,Date,Intl,console,structuredClone,setTimeout,clearTimeout,
    browser:{storage:{local}},
    document:{getElementById(id){if(!els.has(id))els.set(id,status());return els.get(id);},querySelectorAll(){return [];}}};
  vm.createContext(ctx);vm.runInContext(pure,ctx,{timeout:2000});
  return {ctx,els,run:(s)=>vm.runInContext(s,ctx,{timeout:2000})};
}
(async()=>{
 const A=realm(),B=realm();
 A.run('state.note="Notes from tab A"');
 assert.equal(await A.run('persist(["note"])'),true);
 B.run('state.focus="Focus from older tab B"');
 assert.equal(await B.run('persist(["focus"])'),true);
 const prefix='elfshell-workspace-v3:field:';
 assert.equal(store[prefix+'note'],'Notes from tab A');
 assert.equal(store[prefix+'focus'],'Focus from older tab B');
 B.run('applyWorkspaceStorageChanges({[fieldKey("note")]:{newValue:"Notes from tab A"}},"local")');
 assert.equal(B.run('state.note'),'Notes from tab A');
 // Separate debounce timers must not cancel a pending note save when focus changes.
 A.run('state.note="A second note";queueSave("note");state.focus="New focus";queueSave("focus")');
 await new Promise(r=>setTimeout(r,530));
 assert.equal(store[prefix+'note'],'A second note');
 assert.equal(store[prefix+'focus'],'New focus');
 // A failed session save cannot report success.
 failWrites=true;A.run('state.sessions=[{name:"Fail",created:"2026-11-04",urls:["https://example.org/"]}]');
 assert.equal(await A.run('persist(["sessions"])'),false);
 assert.equal(A.els.get('archive-status').textContent,'SAVE ERROR');
 failWrites=false;
 assert.equal(await A.run('persist(["sessions"])'),true);
 assert.equal(store[prefix+'sessions'][0].name,'Fail');
 assert.equal(A.els.get('archive-status').textContent,'SAVED');
 console.log('Workspace concurrency QA PASS: independent field saves, remote update, distinct debounce timers, failed and retryable saves.');
})().catch(e=>{console.error(e);process.exitCode=1;});
