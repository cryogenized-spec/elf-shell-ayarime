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
const browser={
 storage:{local:{
  async get(names){await new Promise(r=>setTimeout(r,6));return Object.fromEntries([].concat(names).map(k=>[k,storage[k]]));},
  async set(entries){if(rejectNext){rejectNext=false;throw Error('Simulated disk failure');}await new Promise(r=>setTimeout(r,6));Object.assign(storage,JSON.parse(JSON.stringify(entries)));}
 }},
 theme:{update:async()=>{}},
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
 const cleared=await send({action:'clear'});
 assert.equal(cleared.ok,true);assert.equal(storage[key].length,0);
 console.log('Recovery persistence QA PASS: concurrent appends, unique IDs, restart, per-record completion, storage failure/retry, unsafe URLs and manual clear.');
})().catch(e=>{console.error(e);process.exitCode=1;});
