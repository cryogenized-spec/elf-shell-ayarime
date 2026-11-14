"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const Tunnel=require("../unified-preview/google-master-tunnel.js");
const TOKEN="FAKE_OWNER_MCP_TOKEN_FOR_LOCAL_SYNTHETIC_TESTS_ONLY";
function mockTools(){
  return {jsonrpc:"2.0",id:1,result:{tools:[
    {name:"tasks_list_tasks",securitySchemes:[{type:"oauth2",scopes:["mcp:read"]}]},
    {name:"tasks_create_task",securitySchemes:[{type:"oauth2",scopes:["mcp:read","mcp:write"]}]}
  ]}};
}
function fixture(overrides={}){
  const calls={network:0,token:0,permission:0,init:null};
  const args={
    hasHostPermission:async origin=>{calls.permission++;assert.equal(origin,Tunnel.ORIGIN);return true;},
    getAccessToken:async()=>{calls.token++;return TOKEN;},
    fetchImpl:async(url,init)=>{calls.network++;calls.init=init;
      assert.equal(url,Tunnel.RESOURCE);return Response.json(mockTools());},
    ...overrides
  };
  return {calls,args};
}
test("fixed Cloudflare MCP resource; no background I/O or local tunnel",()=>{
  assert.equal(Tunnel.RESOURCE,"https://google-master-mcp.cryogenized.workers.dev/mcp");
  assert.equal(Tunnel.PROTOCOL,"2026-07-28");
  assert.equal(typeof Tunnel.probe,"function");
  assert(!Object.hasOwn(Tunnel,"callTool"));
});
test("manual probe discovers read/write scopes without executing any tool",async()=>{
  const {calls,args}=fixture();
  assert.equal(calls.network,0);
  const reply=await Tunnel.probe(args);
  assert.deepEqual(reply,{resource:Tunnel.RESOURCE,protocol:Tunnel.PROTOCOL,
    total:2,read:1,write:1,reachable:true,toolsExecuted:0,googleContentFetched:false});
  assert.equal(calls.network,1);assert.equal(calls.permission,1);assert.equal(calls.token,1);
  const opt=calls.init;
  assert.equal(opt.method,"POST");
  assert.equal(opt.headers.Authorization,"Bearer "+TOKEN);
  assert.equal(opt.headers["Mcp-Method"],"tools/list");
  assert.equal(opt.headers["MCP-Protocol-Version"],Tunnel.PROTOCOL);
  assert.equal(opt.redirect,"error");assert.equal(opt.cache,"no-store");
  assert.equal(opt.credentials,"omit");assert.equal(opt.referrerPolicy,"no-referrer");
  const body=JSON.parse(opt.body);
  assert.equal(body.method,"tools/list");
  assert.equal(body.params._meta["io.modelcontextprotocol/protocolVersion"],Tunnel.PROTOCOL);
  assert(!JSON.stringify(body).includes("tools/call"));
});
test("denied permission and absent OAuth token block network",async()=>{
  let calls=0;
  const bad=()=>{calls++;return Response.json(mockTools());};
  await assert.rejects(Tunnel.probe({fetchImpl:bad,
    hasHostPermission:async()=>false,getAccessToken:async()=>TOKEN}),/MCP_FIREFOX_HOST_PERMISSION_REQUIRED/);
  await assert.rejects(Tunnel.probe({fetchImpl:bad,
    hasHostPermission:async()=>true,getAccessToken:async()=>""}),/MCP_CLIENT_OAUTH_REQUIRED/);
  assert.equal(calls,0);
});
test("oversized, altered scopes, wrong protocol and provider errors fail closed",async()=>{
  for(const [reply,code]of [
    [Response.json({jsonrpc:"2.0",id:99,result:{tools:[]}}),"MCP_REPLY_INVALID"],
    [Response.json({jsonrpc:"2.0",id:1,result:{tools:[
      {name:"tasks_create_task",securitySchemes:[{type:"oauth2",scopes:["mcp:read"]}]},
      {name:"tasks_create_task",securitySchemes:[{type:"oauth2",scopes:["mcp:read"]}]}
    ]}}),"MCP_REPLY_INVALID"],
    [Response.json({jsonrpc:"2.0",id:1,result:{tools:[{name:"mutate"}]}}),"MCP_SECURITY_METADATA_INVALID"],
    [new Response("PRIVATE_PROVIDER_MESSAGE",{status:403}),"MCP_CLIENT_SCOPE_REQUIRED"],
    [new Response("x".repeat(600000),{headers:{"Content-Type":"application/json"}}),"MCP_REPLY_TOO_LARGE"],
    [new Response("event: message\\ndata: {}\\n",{headers:{"Content-Type":"text/event-stream"}}),"MCP_MEDIA_TYPE_UNSUPPORTED"]
  ]){
    const {args}=fixture({fetchImpl:async()=>reply});
    await assert.rejects(Tunnel.probe(args),e=>e.name==="AyarimeMcpConnectionError"&&e.message===code);
  }
});
