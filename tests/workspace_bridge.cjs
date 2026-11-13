"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root = path.resolve(__dirname,"..");
const read = name => fs.readFileSync(path.join(root,name),"utf8");

function harness(send) {
  const sent = [];
  const status={hidden:true,textContent:"",classList:{error:false,toggle(name,flag){this[name]=flag}}};
  const window={};
  const browser={runtime:{sendMessage:async(id,payload)=>{sent.push({id,payload});return send(id,payload);}}};
  vm.runInNewContext(read("workspace/bridge.js"),{
    browser,window,document:{getElementById:id=>id==="workspace-bridge-status"?status:null}
  });
  return {window,sent,status};
}

test("command controls are present and package includes the new bridge",()=>{
  const html=read("newtab.html"),js=read("newtab.js"),packagePy=read("scripts/package.py");
  assert(html.includes('id="workspace-companion-toggle"'));
  assert(html.includes("10 TOOLS · CTRL+K"));
  assert(html.includes('id="ask-ayarime-toggle"'));
  assert(js.includes('$("ask-ayarime-toggle").addEventListener("click",launchAyarimeAssistant)'));
  assert(js.includes('action("Ask Ayarime · AI Console"'));
  assert(js.includes('$("workspace-companion-toggle").addEventListener("click",launchAyarimeWorkspace)'));
  assert(html.includes('id="workspace-bridge-status"'));
  assert(html.includes('<script defer src="workspace/bridge.js"></script>'));
  assert(js.includes('isAyarimeWorkspaceCommand(q)'));
  assert(js.includes('action("Ayarime, please bring up my workspace"'));
  assert(packagePy.includes("'workspace/bridge.js'"));
  assert(js.includes("isAskAyarimeCommand(q)"));
  assert(!read("manifest.json").includes("workspace-ai@elf-shell.local"),"core should not declare the companion as an owned extension");
});

test("explicit launch performs HELLO then OPEN_WORKSPACE only",async()=>{
  const h=harness(async(id,payload)=>{
    if(payload.command==="HELLO") return {ok:true,kind:"elfshell.workspace.bridge",version:1,capabilities:["OPEN_WORKSPACE"]};
    return {ok:true,result:{opened:2,reused:4}};
  });
  const result=await h.window.AyarimeWorkspaceBridge.openWorkspace();
  assert.equal(result.opened,2);assert.equal(result.reused,4);
  assert.equal(h.sent.length,2);assert.deepEqual(h.sent.map(x=>x.payload.command),["HELLO","OPEN_WORKSPACE"]);
  assert(h.sent.every(x=>x.id==="workspace-ai@elf-shell.local"));
  assert.equal(h.status.hidden,false);assert.match(h.status.textContent,/2 opened · 4 reused/);
  assert.equal(h.status.classList.error,false);
  assert.match(h.status.textContent,/Workspace AI toolbar button/);
});

test("missing companion is explained instead of executing a web search",async()=>{
  const h=harness(async()=>{throw Error("Could not establish connection");});
  const result=await h.window.AyarimeWorkspaceBridge.openWorkspace();
  assert.equal(result,null);assert.equal(h.sent.length,1);
  assert.match(h.status.textContent,/Install or enable the optional ELF\/\/SHELL Workspace AI companion/);
  assert.equal(h.status.classList.error,true);
});

test("incompatible protocol never invokes a write-capable operation",async()=>{
  const h=harness(async()=>({ok:true,kind:"wrong",version:99,capabilities:["OPEN_WORKSPACE"]}));
  assert.equal(await h.window.AyarimeWorkspaceBridge.openWorkspace(),null);
  assert.equal(h.sent.length,1);
  assert.match(h.status.textContent,/protocol is incompatible/);
});

test("Ask Ayarime performs HELLO then OPEN_ASSISTANT; no model or Google data flows through core",async()=>{
  const h=harness(async(id,payload)=>{
    if(payload.command==="HELLO")return {ok:true,kind:"elfshell.workspace.bridge",version:1,capabilities:["OPEN_ASSISTANT","OPEN_WORKSPACE"]};
    return {ok:true,result:{focused:true,hubTabId:17,view:"assistant"}};
  });
  const result=await h.window.AyarimeWorkspaceBridge.openAssistant();
  assert.equal(result.hubTabId,17);
  assert.deepEqual(h.sent.map(x=>x.payload.command),["HELLO","OPEN_ASSISTANT"]);
  assert(h.sent.every(x=>x.id==="workspace-ai@elf-shell.local"));
  assert(h.sent.every(x=>Object.keys(x.payload).sort().join(",")==="command,kind,version"),"No prompt or account text may be passed");
  assert.match(h.status.textContent,/AI console opened/);
});
test("old companion without OPEN_ASSISTANT fails helpfully and sends no other operation",async()=>{
  const h=harness(async()=>({ok:true,kind:"elfshell.workspace.bridge",version:1,capabilities:["OPEN_WORKSPACE"]}));
  assert.equal(await h.window.AyarimeWorkspaceBridge.openAssistant(),null);
  assert.deepEqual(h.sent.map(x=>x.payload.command),["HELLO"]);
  assert.match(h.status.textContent,/Update the optional Workspace AI companion/);
});
