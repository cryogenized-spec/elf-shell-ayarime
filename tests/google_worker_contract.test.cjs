"use strict";
const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),path=require("node:path");
const c=require("../unified-preview/google-worker-contract.js");
test("only M10's seven known read-only Google operations are accepted",()=>{
  assert.equal(c.NAMES.length,7);
  const input={operations:[
    {name:"tasks_list_tasks",risk:"read",description:"List tasks"},
    {name:"tasks_list_tasks",risk:"read",description:"Duplicate"},
    {name:"tasks_delete_task",risk:"write",description:"Unsafe mutation"},
    {name:"script_get_project",risk:"write",description:"Risk mismatch"},
    {name:"script_get_content",risk:"read",description:"Read source"},
    {name:"google_api_request",risk:"read",description:"Unknown proxy"},
    {name:"script_list_deployments",risk:"read",description:"Read deployments"}
  ]};
  const caps=c.parseCapabilities(input);
  assert.deepEqual(caps.map(x=>x.name),
    ["tasks_list_tasks","script_get_content","script_list_deployments"]);
  assert(Object.isFrozen(caps));
  assert(Object.isFrozen(caps[0]));
});
test("capabilities parser fails closed on invalid or oversized server data",()=>{
  for(const payload of [null,{},[],{operations:{}},
    {operations:Array(129).fill({name:"tasks_list_tasks",risk:"read",description:"x"})}])
    assert.throws(()=>c.parseCapabilities(payload),/Invalid Google Master/);
});
test("read-only planning cannot invoke unrecognized, absent or write-labelled operations",()=>{
  const caps=c.parseCapabilities({operations:[
    {name:"tasks_list_tasks",risk:"read",description:"List tasks"}
  ]});
  const p=c.previewRead(caps,"tasks_list_tasks",{tasklistId:"demo",maxResults:25});
  assert.deepEqual(p.inputKeys,["maxResults","tasklistId"]);
  assert.equal(p.path,"/v1/operations/tasks_list_tasks");
  assert.equal(p.method,"POST");
  assert.equal(p.risk,"read");
  assert.equal(p.executionEnabled,false);
  assert.match(p.requires,/mcp:read/);
  assert.match(p.requires,/separately linked Google account/);
  for(const name of ["tasks_delete_task","script_get_content","google_api_request","__proto__"]){
    assert.throws(()=>c.previewRead(caps,name,{}),/unavailable|not approved/);
  }
});
test("input is strict object, finite JSON and max 32 KiB",()=>{
  const caps=c.parseCapabilities({operations:[
    {name:"tasks_list_tasks",risk:"read",description:"Tasks"}
  ]});
  for(const input of [null,"string",[],42,{"constructor":"evil"},{tasklistId:"z".repeat(34000)}])
    assert.throws(()=>c.previewRead(caps,"tasks_list_tasks",input));
  const obj={};obj.self=obj;
  assert.throws(()=>c.previewRead(caps,"tasks_list_tasks",obj),/Invalid/);
});
test("this integration seam does not call Google, execute tools or handle tokens",()=>{
  const js=fs.readFileSync(path.join(__dirname,"../unified-preview/google-worker-contract.js"),"utf8");
  assert(!js.includes("fetch("));
  assert(!js.includes("browser.identity"));
  assert(!js.includes("browser.storage"));
  assert(!js.includes("Authorization: Bearer"));
  assert(!js.includes("browser.runtime.sendMessage"));
  assert(!js.includes("tools/call"));
  const builder=fs.readFileSync(path.join(__dirname,"../scripts/build_unified_preview.py"),"utf8");
  assert(builder.includes('inventory["unified/google-worker-contract.js"]'));
  assert(!builder.includes('<script defer src="unified/google-worker-contract.js"'));
});
