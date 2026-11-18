const {test} = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const root = path.resolve(__dirname,"..");
const read = p => fs.readFileSync(path.join(root,p),"utf8");
test("Native sidebar loads its own tab navigation and scoped scrolling",() => {
  const html=read("sidebar.html"),js=read("sidebar-tabs.js"),css=read("sidebar-tabs.css");
  assert.match(html,/src="sidebar-tabs.js"/);
  assert.match(html,/href="sidebar-tabs.css"/);
  for(const key of ["chat","settings"])
    assert.match(js,new RegExp('key:"'+key+'"'));
  assert.match(js,/aria-selected/); assert.match(js,/aria-controls/);
  assert.match(js,/aria-labelledby/); assert.match(js,/ArrowLeft/);
  assert.match(css,/\.ayarime-sidebar-pane\[hidden\]/);
  assert.match(css,/overflow-y:auto/); assert.match(css,/height:100dvh/);
  assert.doesNotMatch(js,/key:"model"|key:"google"|key:"work"|key:"more"|ayarime-model-pane/);
  assert.match(js,/group\("Google & Morning Coffee"/);
  assert.match(js,/group\("Workspace"/);
  assert.match(js,/oldLaunch\.hidden=true/);
  assert.match(read("chat-first.js"),/disclosure\("Model & connection"/);
  assert.doesNotMatch(js,/fetch\s*\(/);
});
