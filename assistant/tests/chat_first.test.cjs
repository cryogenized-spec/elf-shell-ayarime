"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const root=path.resolve(__dirname,"..");
const read=file=>fs.readFileSync(path.join(root,file),"utf8");
test("Hub and sidebar retain a single functional chat, model setup and options",()=>{
  for(const name of ["hub.html","sidebar.html"]){
    const html=read(name);
    for(const id of ["ai-conversation-list","ai-prompt","ai-send",
      "ai-cancel","ai-settings-form","ai-model-picker","ai-provider",
      "ai-model","ai-key","ai-grant","ai-trace","ai-context-enable",
      "ai-effort","ai-check-model"]) {
      assert.equal((html.match(new RegExp('id="'+id+'"',"g"))||[]).length,1,id+" in "+name);
    }
    assert.match(html,/src="chat-first\.js"/);
    assert.doesNotMatch(html,/id="ai-summary-hint"|>LIVE<|API usage may incur charges|higher cost|potential cost|additional charges|economical/i);
    assert.doesNotMatch(html,/class="quiet conversation-privacy"/);
  }
});
test("Chat-first enhancement reparents original nodes without duplicated controls",()=>{
  const source=read("chat-first.js");
  assert.match(source,/root\.append\(controls,stage\)/);
  assert.match(source,/stage\.append\(transcript,composer\)/);
  assert.match(source,/const provider=disclosure\("Model & connection"/);
  assert.match(source,/disclosure\("Response settings"/);
  assert.match(source,/syncActivity/);
  assert.doesNotMatch(source,/\.cloneNode\(/);
  assert.doesNotMatch(source,/innerHTML\s*=/);
});
test("Native sidebar has no independent Model tab and no fake activity indicator",()=>{
  const tabs=read("sidebar-tabs.js"),trace=read("ui-trace.js");
  assert.doesNotMatch(tabs,/key:"model"|ayarime-model-pane|ayarime-model-shortcut/);
  assert.doesNotMatch(trace,/hint\.textContent=|"LIVE"/);
  assert.match(read("ui.css"),/\.chat-first-stage/);
});
test("Standalone assistant package contains the chat-first module",()=>{
  assert.match(read("scripts/package.py"),/"chat-first\.js"/);
  assert.match(read("package.json"),/node --check chat-first\.js/);
});
