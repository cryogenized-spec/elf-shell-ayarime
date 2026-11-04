'use strict';
// Simulate independent dashboard tabs plus a full extension-background restart.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const code=fs.readFileSync(path.join(__dirname,'../background.js'),'utf8');
const key='elfshell-duplicate-recovery-v1';
const storage={};
let rejectNext=false;
const liveTabs=[
 {id:201,url:'https://example.org/duplicate',windowId:1,index:0,active:true,pinned:false,audible:false,incognito:false},
 {id:202,url:'https://example.org/duplicate',windowId:1,index:1,active:false,pinned:false,audible:false,incognito:false}
];
const removed=[];
const browser={
 storage:{local:{
  async get(names){await new Promise(r=>setTimeout(r,6));return Object.fromEntries([].concat(names).map(k=>[k,storage[k]]));},
  async set(entries){if(rejectNext){rejectNext=false;throw Error('Simulated disk failure');}await new Promise(r=>setTimeout(r,6));Object.assign(storage,JSON.parse(JSON.stringify(entries)));}
 }},
 theme:{update:async()=>{}},
 tabs:{
   async get(id){const tab=liveTabs.find(t=>t.id===id);if(!tab)throw Error('Tab disappeared');return {...tab};},
   async query({windowId}){return liveTabs.filter(t=>t.windowId===windowId).map(t=>({...t}));},
   async remove(ids){removed.push(...ids);for(const id of ids){const i=liveTabs.findIndex(t=>t.id===id);if(i>=0)liveTabs.splice(i,1);}}
 },
 runtime:{onInstalled:{addListener(){}},onStartup:{addListener(){}},onMessage:{addListener(fn){this.handler=fn;}}}
};
function launchBackground(){
 vm.runInNewContext(code,{browser,URL,Promise,Date,console,setTimeout},{timeout:2000});
 return payload=>browser.runtime.onMessage.handler({type:'elfshell:recovery:mutate:v1',...payload});
}
(async()=>{
 let send=launchBackground();
 const one={url:'https://example.org/a?private=token',windowId:1,index:0};
 const two={url:'https://example.org/b',windowId:2,index:3};
 const [a,b]=await Promise.all([send({action:'append',entries:[one]}),send({action:'append',entries:[two]})]);
 assert.equal(a.ok,true);assert.equal(b.ok,true);
 assert.equal(storage[key].length,2,'simultaneous dashboard appends must both persist');
 assert(storage[key].every(x=>x.id&&x.url));
 assert.notEqual(storage[key][0].id,storage[key][1].id,'recovery record IDs must not collide');
 assert.equal((await send({action:'list'})).entries.length,2);
 const first=storage[key][0].id;
 const finished=await send({action:'complete',ids:[first]});
 assert.equal(finished.entries.length,1,'acknowledging recovery must retain other pending entries');
 send=launchBackground(); // fresh background process / browser startup
 const reopened=await send({action:'list'});
 assert.equal(reopened.ok,true);assert.equal(reopened.entries.length,1,'pending recovery must survive browser restart');
 assert.equal(reopened.entries[0].url,two.url);
 rejectNext=true;
 const failed=await send({action:'append',entries:[one]});
 assert.equal(failed.ok,false,'failed persistence must not report success');
 assert.equal((await send({action:'list'})).entries.length,1,'failed persistence must not silently change saved entries');
 const retry=await send({action:'append',entries:[one]});
 assert.equal(retry.ok,true,'a failed operation must not poison the serial queue');
 assert.equal(retry.entries.length,2);
 const invalid=await send({action:'append',entries:[{url:'javascript:alert(1)',windowId:1,index:0}]});
 assert.equal(invalid.ok,false,'non-web recovery URLs must be rejected');
 assert.equal((await send({action:'list'})).entries.length,2);
 // Simulate another dashboard clearing history while a duplicate's recovery
 // address is durably reserved but its second tab safety check is pending.
 const olderIds=storage[key].map(item=>item.id);
 const originalGet=browser.tabs.get;
 let getCount=0,releaseRecheck;
 let signalRecheck;
 const reachedRecheck=new Promise(resolve=>{signalRecheck=resolve;});
 browser.tabs.get=async id=>{
   getCount++;
   if(getCount===2){
     signalRecheck();
     await new Promise(resolve=>{releaseRecheck=resolve;});
   }
   return originalGet(id);
 };
 const closing=send({action:'closeDuplicate',item:{tabId:202,url:'https://example.org/duplicate',windowId:1,index:1}});
 await reachedRecheck;
 assert.equal(storage[key].length,olderIds.length+1,'reserve recovery before removing the tab');
 const clearing=send({action:'clear',ids:olderIds});
 releaseRecheck();
 const [closed,oldCleared]=await Promise.all([closing,clearing]);
 assert.equal(closed.ok,true);assert.equal(closed.closed,true);
 assert.deepEqual(removed,[202]);
 assert.equal(oldCleared.ok,true);
 assert.equal(storage[key].length,1,'concurrent clear must preserve the newer duplicate recovery address');
 assert.equal(storage[key][0].url,'https://example.org/duplicate');
 const unqualifiedClear=await send({action:'clear'});
 assert.equal(unqualifiedClear.ok,false,'unqualified clear is unsafe');
 const cleared=await send({action:'clear',ids:storage[key].map(x=>x.id)});
 assert.equal(cleared.ok,true);assert.equal(storage[key].length,0);
 // Codex P1: the target can navigate / move / become active while the
 // final query is pending. The old tabs.get snapshot must not authorize
 // closing a changed tab, even if another tab still has the old URL.
 const originalQuery=browser.tabs.query;
 const savedGet=browser.tabs.get;
 for(const [kind,patch] of [
   ['navigation',{url:'https://example.org/important',active:true}],
   ['window move',{windowId:2}],
   ['pin',{pinned:true}]
 ]){
   const id=203+['navigation','window move','pin'].indexOf(kind);
   const target={id,url:'https://example.org/duplicate',windowId:1,index:1,active:false,pinned:false,audible:false,incognito:false};
   liveTabs.push(target);
   let queryCalls=0;
   browser.tabs.query=async opts=>{
     queryCalls++;
     if(queryCalls===2)Object.assign(target,patch);
     return originalQuery(opts);
   };
   const beforeRemoved=removed.length;
   const outcome=await send({action:'closeDuplicate',item:{tabId:id,url:'https://example.org/duplicate',windowId:1,index:1}});
   assert.equal(outcome.ok,true,kind+' check should complete safely');
   assert.equal(outcome.closed,false,kind+' during final query must not close tab');
   assert.equal(outcome.skipped,true,kind+' must be treated as an ineligible target');
   assert.equal(removed.length,beforeRemoved,kind+' may not remove the changed tab');
   assert(liveTabs.some(t=>t.id===id),kind+' tab must remain open');
   assert.equal(storage[key].length,0,kind+' unused reservation must be cleaned');
   browser.tabs.query=originalQuery;
   liveTabs.splice(liveTabs.findIndex(t=>t.id===id),1);
 }
 // A change between the last query and the final tabs.get must also
 // cause cleanup to skip the tab instead of trusting the query snapshot.
 const newest={id:207,url:'https://example.org/duplicate',windowId:1,index:1,active:false,pinned:false,audible:false,incognito:false};
 liveTabs.push(newest);
 let getCalls=0;
 browser.tabs.get=async id=>{
   getCalls++;
   if(getCalls===3)newest.active=true;
   return savedGet(id);
 };
 const latest=await send({action:'closeDuplicate',item:{tabId:207,url:'https://example.org/duplicate',windowId:1,index:1}});
 assert.equal(latest.ok,true);
 assert.equal(latest.closed,false,'final get must detect an activated tab');
 assert.equal(removed.includes(207),false);
 assert.equal(storage[key].length,0);
 browser.tabs.get=savedGet;
 console.log('Recovery persistence QA PASS: durable reservations, restart, write failures, concurrent clear/close, and final query/get tab-race safety.');
})().catch(e=>{console.error(e);process.exitCode=1;});
