"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const root=path.resolve(__dirname,"..");
const read=file=>fs.readFileSync(path.join(root,file),"utf8");

test("one native sidebar and one header path to canonical Workspace",()=>{
  const builder=read("scripts/build_unified_preview.py");
  const menu=read("assistant/sidebar-tabs.js");
  const handoff=read("unified-preview/sidebar-handoff.js");
  const guard=read("unified-preview/surface-exclusive.js");
  const css=read("unified-preview/surface-exclusive.css");
  const hub=read("assistant/hub.html");

  assert.match(builder,/manifest\["sidebar_action"\]\["open_at_install"\] = True/);
  assert.match(builder,/browser\.sidebarAction\.open\(\)/);
  assert.doesNotMatch(builder,/station-launcher\.js|station-launcher\.css|id="ayarime-sidebar-launcher"|id="ayarime-workspace-launcher"/);
  assert.match(builder,/for control in \("ask-ayarime-toggle", "workspace-companion-toggle"\)/);
  assert.match(css,/#ask-ayarime-toggle\[hidden\]/);
  assert.match(css,/#workspace-companion-toggle\[hidden\]/);
  assert.doesNotMatch(hub,/id="ai-open-sidebar"/);
  assert.match(handoff,/id="ayarime-open-workspace"/);
  assert.match(handoff,/type:"UI_OPEN_WORKSPACE"/);
  assert.doesNotMatch(handoff,/tabs\.create\(/);
  assert.match(builder,/return \{ok:true,result:await serialise\(focusAssistant\)\}/);
  assert.match(builder,/sender\?\.url !== browser\.runtime\.getURL\("sidebar\.html"\)/);
  assert.match(guard,/UI_SURFACE_STATUS/);
  assert.match(css,/hub-foreground/);
  assert.deepEqual([...menu.matchAll(/\{key:"(\w+)", title:/g)].map(x=>x[1]),["chat","settings"]);
  assert.match(menu,/group\("Google & Morning Coffee"/);
  assert.match(menu,/oldLaunch\.hidden=true/);
  assert.match(menu,/coffeeLaunch\.hidden=true/);
});

test("Hub and sidebar share one session transcript and recover pending draft",()=>{
  const conversation=read("assistant/ui-conversation.js");
  assert.match(conversation,/elfshell\.byok\.visibleTranscript\.v1/);
  assert.match(conversation,/elfshell\.byok\.sharedDraft\.v1/);
  assert.match(conversation,/AI_CONVERSATION_LIST/);
  assert.match(conversation,/AI_CONVERSATION_APPEND/);
  assert.match(conversation,/browser\.storage\.session\?\.get\(DRAFT_KEY\)/);
  assert.match(conversation,/browser\.storage\.session\.set\(\{\[DRAFT_KEY\]:value\}\)/);
  assert.match(conversation,/browser\.storage\?\.onChanged\?\.addListener/);
  assert.match(read("unified-preview/sidebar-handoff.js"),/WorkspaceConversationUI\?\.flushDraft\?\.\(\)/);
});

test("an untrusted Station cannot masquerade as a sidebar or Hub",()=>{
  const builder=read("scripts/build_unified_preview.py");
  assert.match(builder,/UI_REGISTER_HUB/);
  assert.match(builder,/Untrusted Hub registration/);
  assert.match(builder,/Untrusted sidebar control/);
  assert.match(builder,/UI_SURFACE_STATUS/);
  assert.match(builder,/unifiedHubTabId=sender\.tab\.id/);
  assert.match(builder,/async function unifiedHubIsForeground/);
  assert.match(builder,/tab\.id===unifiedHubTabId/);
});
