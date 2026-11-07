"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const root=path.resolve(__dirname,"..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const pkg=JSON.parse(read("package.json"));
assert.equal(pkg.license,"MPL-2.0");
const license=read("LICENSE");
assert(license.startsWith("Mozilla Public License Version 2.0"));
assert(license.includes("Exhibit A - Source Code Form License Notice"));
assert(license.length>15000);
assert(read("LICENSE_SCOPE.md").includes("third-party"));
assert(read("LICENSES/MIT-legacy.txt").startsWith("MIT License"));
const python=read("scripts/package.py");
for(const f of ["LICENSE","LICENSE_SCOPE.md","LICENSES/MIT-legacy.txt","ARTWORK_LICENSE.md"])
  assert(python.includes("'"+f+"'"),"AMO package must include "+f);
console.log("MPL-2.0 licence scope, bundled notices and historical MIT preservation QA PASS.");
