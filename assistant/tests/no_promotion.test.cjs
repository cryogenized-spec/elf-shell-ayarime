"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");

const root=path.resolve(__dirname,"..");
const read=relative=>fs.readFileSync(path.join(root,relative),"utf8");

test("Hub and sidebar contain no promotional-token offer, meters or enrollment controls",()=>{
  for(const page of ["hub.html","sidebar.html"]){
    const html=read(page);
    assert.doesNotMatch(html,/id="ai-offer-(panel|selector|enrolled|standard-meter|small-meter)"/);
    assert.doesNotMatch(html,/complimentary.token.offer|250,000 \/ day|2,500,000 \/ day/i);
    assert.doesNotMatch(html,/ai\/openai-complimentary\.js/);
    assert.match(html,/id="ai-provider"/);
    assert.match(html,/id="ai-model"/);
    assert.match(html,/id="ai-grant"/);
    assert.match(html,/id="ai-key"/);
    assert.match(html,/id="ai-trace-usage"/);
    assert.match(html,/API usage may incur charges/i);
  }
});

test("model and provider controls have no hidden promotional accounting",()=>{
  const ui=read("ui.js"), background=read("background.js");
  const stream=read("ai/openai-stream.js"),manifest=read("manifest.json");
  for(const script of [ui,background,stream,manifest]){
    assert.doesNotMatch(script,/WorkspaceOpenAIComplimentary|AI_OFFER_|ai-offer-|openai-complimentary/);
  }
  assert.doesNotMatch(ui,/refreshOpenAIOffer|showOpenAIOffer|renderModelOffer|aiOfferSelector/);
  assert.doesNotMatch(stream,/localUsage/);
  assert.match(stream,/emit\(terminal\)/);
  assert.match(ui,/ai-check-model/);
  assert.match(ui,/ai-send/);
});

test("removed feature is not bundled into standalone or unified assistant",()=>{
  const files=read("scripts/package.py");
  assert.doesNotMatch(files,/openai-complimentary/);
  assert.equal(fs.existsSync(path.join(root,"ai/openai-complimentary.js")),false);
});
