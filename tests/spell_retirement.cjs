"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ROOT=path.resolve(__dirname,"..");
const read=p=>fs.readFileSync(path.join(ROOT,p),"utf8");
const manifest=JSON.parse(read("manifest.json"));
assert.deepEqual([...manifest.permissions].sort(),["search","storage","theme"]);
assert(!manifest.action?.default_popup,"no custom spelling toolbar popup");
assert.deepEqual(manifest.background.scripts,["background.js"]);
assert(!manifest.content_scripts,"no injected spelling scripts");
assert(!fs.existsSync(path.join(ROOT,"spelling")),"remove experimental bundled spelling resources");
assert(!fs.existsSync(path.join(ROOT,"integration")),"remove old integration registration");
const html=read("newtab.html");
assert(!html.includes("integration/ui.js"));
assert(!html.includes("integration-spelling"));
assert(html.includes('id="note-input"')&&html.includes('spellcheck="true"'),
  "native Firefox textarea spelling remains active");
const packageSrc=read("scripts/package.py");
assert(!packageSrc.includes("'spelling/'")&&!packageSrc.includes("'integration/"),
  "AMO must not bundle experimental spelling");
const bg=read("background.js");
assert(bg.includes("RSS_APPROVED_KEY"),"RSS retains explicit per-feed consent");
assert(bg.includes("await requireRSSHost(f.url)"),"RSS consent ledger requires Firefox host grant");
assert(fs.existsSync(path.join(ROOT,"linux-cursors","build.py")));
console.log("PASS: retired custom spellchecker and permissions; native browser spelling and RSS preserved.");
