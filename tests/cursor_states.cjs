"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const html=read("newtab.html"),js=read("newtab.js"),css=read("styles.css");
const states=["pointer","ibeam","busy","crosshair","resize","link"];
for(const state of states){
  for(const size of [48,64]){
    const asset="assets/cursors/states/"+state+"-"+size+".png";
    const bytes=fs.readFileSync(path.join(root,asset));
    assert(bytes.length>350,asset+" missing");
    assert.equal(bytes.subarray(0,8).toString("hex"),"89504e470d0a1a0a",asset+" must be PNG");
    assert.equal(bytes.readUInt32BE(16),size,asset+" width");
    assert.equal(bytes.readUInt32BE(20),size,asset+" height");
    assert.equal(bytes[25],6,asset+" must be RGBA");
    if(size===48)assert(css.includes(asset),asset+" missing from CSS");
  }
  const demo=state==="ibeam"?"text":state==="pointer"?"default":state;
  assert(html.includes('data-cursor-state="'+demo+'"'),state+" preview missing");
}
assert(html.includes('name="cursor-choice" value="system" checked'),"system must remain default");
assert(html.includes('value="ayarime-core"'),"new family choice missing");
assert(html.includes('src="assets/cursors/states/pointer-64.png"'),"preview asset missing");
assert(js.includes('"ayarime-core"'),"allowlisted cursor family missing");
assert(js.includes('choice==="ayarime-core"'),"cursor art must be opt-in");
assert(css.includes('body[data-cursor]:not([data-cursor="system"])'),"CSS must remain opt-in");
for(const state of ["link","text","busy","crosshair","resize"]){
  assert(css.includes("--elf-"+state+"-cursor:"),"Missing cursor state "+state);
}
for(const native of ["pointer","text","progress","crosshair","nwse-resize"]){
  assert(css.includes(","+native+");"),"Missing cursor fallback "+native);
}
const cut=js.indexOf('$("search-form").addEventListener');
assert(cut>3000);
const context={URL,Date,Intl,console,setTimeout,clearTimeout,document:{body:{}}};
vm.createContext(context);
vm.runInContext(js.slice(0,cut),context,{timeout:3000});
const clean=x=>vm.runInContext("cleanCursor("+JSON.stringify(x)+")",context,{timeout:1000});
assert.equal(clean("ayarime-core"),"ayarime-core");
assert.equal(clean("rune-edged"),"rune-edged");
assert.equal(clean("../../etc/passwd"),"system");
assert.equal(clean(null),"system");
console.log("Ayarime six-state cursor QA PASS: 12 transparent PNGs, state mapping, opt-in fallbacks and cursor safety.");
