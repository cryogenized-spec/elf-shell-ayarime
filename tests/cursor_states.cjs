"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const html=read("newtab.html"),js=read("newtab.js"),css=read("styles.css");
const feeds=read("feeds.js");
assert(feeds.includes('$("feed-refresh").setAttribute("aria-busy","true")'),"real RSS refresh must announce busy state");
assert(feeds.includes('$("feed-refresh").removeAttribute("aria-busy")'),"busy state must clear after refresh");
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
    if(size===48)assert((state==="pointer"?js:css).includes(asset),asset+" not referenced by cursor implementation");
  }
  const demo=state==="ibeam"?"text":state==="pointer"?"default":state;
  assert(html.includes('data-cursor-state="'+demo+'"'),state+" preview missing");
}
// Cursor previews are independent of the selected saved pointer family.
const previewCursorFiles={default:"pointer",text:"ibeam",busy:"busy",crosshair:"crosshair",resize:"resize",link:"link"};
for(const [sample,asset] of Object.entries(previewCursorFiles)){
  const rule='.cursor-state-preview [data-cursor-state="'+sample+'"]';
  const start=css.indexOf(rule+"{");
  assert(start>=0,"Unconditional hover preview missing for "+sample);
  const end=css.indexOf("}",start);
  assert(end>start && css.slice(start,end).includes('url("assets/cursors/states/'+asset+'-48.png")'),
         "Wrong cursor preview for "+sample);
}
assert(html.includes("even with System Default selected"),"Preview must work when System Default is selected");
assert(html.includes("previews do not change your saved choice"),"Preview must not change settings");
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
