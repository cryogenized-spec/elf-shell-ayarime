'use strict';
// Two independent new-tab pages sending overlapping mutations to the same
// Firefox background page must not overwrite one another's saved workspaces.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const source=fs.readFileSync(path.resolve(__dirname,'../background.js'),'utf8');
const key='elfshell-workspace-v3:field:sessions';
const data={
  'elfshell-workspace-v3':{sessions:[{name:'Legacy',created:'2026-11-01',urls:['https://legacy.example/']}]}
};
let listener,failNextWrite=false;
const browser={
  storage:{local:{
    async get(keys){
      // Mimic a staggered async Firefox storage read, amplifying the race.
      await new Promise(r=>setTimeout(r,10));
      return Object.fromEntries([].concat(keys).map(k=>[k,data[k]]));
    },
    async set(changes){
      if(failNextWrite){failNextWrite=false;throw Error('Simulated Firefox storage failure');}
      await new Promise(r=>setTimeout(r,10));
      Object.assign(data,JSON.parse(JSON.stringify(changes)));
    }
  }},
  theme:{update:async()=>{}},
  runtime:{onInstalled:{addListener(){}},onStartup:{addListener(){}},onMessage:{addListener(fn){listener=fn;}}}
};
vm.runInNewContext(source,{browser,URL,Date,Promise,console,setTimeout}, {timeout:2000});
assert.equal(typeof listener,'function');
const req=(action,details={})=>listener({type:'elfshell:sessions:mutate:v1',action,...details});
const URLs=['https://one.example/','https://two.example/','https://three.example/'];
(async()=>{
  const [a,b]=await Promise.all([
    req('save',{name:'Tab A',urls:[URLs[0]]}),
    req('save',{name:'Tab B',urls:[URLs[1]]})
  ]);
  assert.equal(a.ok,true);assert.equal(b.ok,true);
  assert.deepEqual(new Set(data[key].map(s=>s.name)),new Set(['Legacy','Tab A','Tab B']),'concurrent saves must keep legacy and both new workspaces');
  const target=data[key].find(s=>s.name==='Tab A');
  const [deleted,saved]=await Promise.all([
    req('delete',{workspace:target}),
    req('save',{name:'Tab C',urls:[URLs[2]]})
  ]);
  assert.equal(deleted.ok,true);assert.equal(saved.ok,true);
  assert.deepEqual(new Set(data[key].map(s=>s.name)),new Set(['Legacy','Tab B','Tab C']),'concurrent deletion and save must both persist');
  failNextWrite=true;
  const fail=await req('save',{name:'Rejected',urls:['https://rejected.example/']});
  assert.equal(fail.ok,false);
  assert.equal(data[key].some(s=>s.name==='Rejected'),false);
  const recovered=await req('save',{name:'Retry',urls:['https://retry.example/']});
  assert.equal(recovered.ok,true,'the queue must recover after a failed Firefox storage write');
  assert.equal(data[key].some(s=>s.name==='Retry'),true);
  const clear=await req('replace',{sessions:[{name:'Import',created:'2026-11-03',urls:['https://import.example/']} ]});
  assert.equal(clear.ok,true);
  assert.deepEqual(data[key].map(x=>x.name),['Import']);
  const bad=await req('save',{name:'javascript',urls:['javascript:alert(1)']});
  assert.equal(bad.ok,false,'unsafe URLs must not be stored by background messages');
  console.log('Background session race QA PASS: concurrent saves, save/delete, legacy preservation, import serialization, error retry, unsafe URL rejection.');
})().catch(e=>{console.error(e);process.exitCode=1;});
