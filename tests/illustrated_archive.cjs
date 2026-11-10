"use strict";
const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root = path.resolve(__dirname,"..");
const read = file => fs.readFileSync(path.join(root,file),"utf8");
const html = read("stories/archive.html");
const css = read("stories/archive.css");
const js = read("stories/archive.js");
const tab = read("newtab.html");
const palette = read("newtab.js");
const pkg = read("scripts/package.py");
const manifest = JSON.parse(read("stories/asset-manifest.json"));
const extension = JSON.parse(read("manifest.json"));

assert.equal(extension.version,JSON.parse(read("package.json")).version);
assert(!extension.host_permissions,"No new host permissions");
assert(!/\<script(?![^>]*src=)/.test(html),"No inline script: Firefox CSP");
assert(!/\<style(?![^>]*href=)/.test(html),"No inline style: Firefox CSP");
assert(html.includes('src="archive.js"') && html.includes('href="archive.css"'));
assert(!/fetch\s*\(/.test(js),"Reader must not fetch remotely");
assert(!/XMLHttpRequest|sendBeacon|localStorage|browser\.storage/.test(js),"Reader is non-tracking and read-only");
assert(!/https?:\/\//.test(html+css+js),"Reader must have no external resource URLs");
assert.equal((tab.match(/href="stories\/archive\.html"/g)||[]).length,3);
assert(tab.includes("9 TOOLS · CTRL+K"));
assert(palette.includes('Browse illustrated Ayarime stories'));
assert(!tab.includes("window.open("),"Shortcuts and toolbar links must remain native");
assert(manifest.requiresExplicitHumanMergeApproval===true);
assert(manifest.requiresSeparateMozillaPublicationApproval===true);
assert.equal(manifest.assetImportStatus,"COMMITTED_TO_FEATURE_BRANCH");
assert.equal(manifest.mergeApprovalGranted,true);
assert.equal(manifest.mozillaPublicationApprovalGranted,false);

let n = 0;
for(const story of manifest.stories){
  for(const art of story.artwork){
    n++;
    const f = path.join(root,art.proposedRepoPath);
    const bytes = fs.readFileSync(f);
    assert.equal(bytes.length,art.bytes,art.proposedRepoPath+" byte count");
    assert.equal(crypto.createHash("sha256").update(bytes).digest("hex"),art.sha256,art.proposedRepoPath+" checksum");
    assert.equal(bytes.subarray(0,8).toString("hex"),"89504e470d0a1a0a","PNG magic");
    assert.equal(bytes.readUInt32BE(16),art.width,"PNG width");
    assert.equal(bytes.readUInt32BE(20),art.height,"PNG height");
    assert(pkg.includes("'"+art.proposedRepoPath+"'") ||
      pkg.includes("'"+path.basename(art.proposedRepoPath)+"'"),"Artwork not on runtime whitelist");
  }
}
assert.equal(n,5,"Exactly five original artwork masters");
for(const file of ["stories/archive.html","stories/archive.css","stories/archive.js"]){
  assert(pkg.includes("'"+file+"'"),"Reader runtime file not packaged: "+file);
}

const registry = new Map();
function element(id){
  const listeners = new Map(),classes = new Set();
  const e = {
    id, listeners, dataset:{}, children:[], attributes:{}, src:"",
    classList:{toggle(cls,flag){if(flag)classes.add(cls);else classes.delete(cls);},contains(cls){return classes.has(cls);}},
    setAttribute(k,v){this.attributes[k]=v;},
    append(...items){this.children.push(...items);},
    replaceChildren(...items){this.children=[...items];},
    addEventListener(name,cb){listeners.set(name,cb);},
    click(){const cb=listeners.get("click");if(cb)cb({target:e});}
  };
  registry.set(id,e);
  return e;
}
const ids=[...html.matchAll(/\bid="([^"]+)"/g)].map(x=>x[1]);
assert.equal(new Set(ids).size,ids.length,"Duplicate archive HTML IDs");
for(const id of ids) element(id);
registry.get("story-letters").dataset.story="letters";
registry.get("story-beans").dataset.story="beans";
const dlg=registry.get("art-dialog");
dlg.open=false;dlg.showModal=()=>{dlg.open=true;};dlg.close=()=>{dlg.open=false;};
const docEvents=new Map(),winEvents=new Map();
const document={
  getElementById(id){return registry.get(id)||null;},
  createElement(tag){return element(tag+"-dynamic-"+registry.size);},
  querySelectorAll(query){
    assert.equal(query,"button[data-story]");
    return [registry.get("story-letters"),registry.get("story-beans")];
  },
  addEventListener(type,cb){docEvents.set(type,cb);}
};
const location={hash:"#beans/2"};
const history={replaceState(_s,_t,fragment){location.hash=fragment;}};
const window={addEventListener(type,cb){winEvents.set(type,cb);}};
vm.runInNewContext(js,{document,window,history,location,console},{timeout:1000});
assert.equal(registry.get("hero-title").textContent,"Crushed Rainforest Beans");
assert.equal(registry.get("archive-id").textContent,"AYR-002-C");
assert.equal(registry.get("sequence-list").children.length,3);
assert.equal(registry.get("main-art").src,"assets/crushed-rainforest-beans-09-12.png");
registry.get("story-letters").click();
assert.equal(registry.get("hero-title").textContent,"Letters from the Lower City");
assert.equal(registry.get("sequence-list").children.length,2);
assert.equal(registry.get("main-art").src,"assets/letters-from-the-lower-city-01-04.png");
assert.equal(location.hash,"#letters/0");
registry.get("next-set").click();
assert.equal(registry.get("archive-id").textContent,"AYR-001-B");
assert.equal(location.hash,"#letters/1");
registry.get("expand-art").click();
assert.equal(dlg.open,true,"Expand must open native modal");
registry.get("close-art").click();
assert.equal(dlg.open,false,"Close must dismiss native modal");
registry.get("story-beans").click();
const last=registry.get("sequence-list").children[2];
last.click();
assert.equal(registry.get("archive-id").textContent,"AYR-002-C");
assert.equal(registry.get("expanded-art").src,"assets/crushed-rainforest-beans-09-12.png");
let prevented=false;
docEvents.get("keydown")({key:"ArrowLeft",altKey:false,ctrlKey:false,metaKey:false,shiftKey:false,target:{closest:()=>false},preventDefault(){prevented=true;}});
assert(prevented);
assert.equal(registry.get("archive-id").textContent,"AYR-002-B");
location.hash="#letters/1";
winEvents.get("hashchange")();
assert.equal(registry.get("archive-id").textContent,"AYR-001-B");
assert.equal(registry.get("main-art").src,"assets/letters-from-the-lower-city-05-07.png");
console.log("Illustrated Archive QA PASS: five byte-perfect images, local packaging, bilingual originals, navigation, deep links, accessible zoom, no new permissions.");
