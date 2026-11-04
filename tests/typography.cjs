"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,".."),read=p=>fs.readFileSync(path.join(root,p),"utf8");
const html=read("newtab.html"),css=read("typography.css"),js=read("newtab.js");
assert(html.includes('href="typography.css"'),"Typography CSS must load locally");
for(const id of ["typography-preset","typography-scale","typography-display","typography-ui","typography-mono","typography-japanese","typography-preview"]){
  assert(html.includes('id="'+id+'"'),"Missing typography control "+id);
}
const ids=[...html.matchAll(/\bid="([^"]+)"/g)].map(match=>match[1]);
assert.equal(ids.length,new Set(ids).size,"Duplicate DOM ids");
for(const preset of ["original","classic","neural","archive"])assert(html.includes('value="'+preset+'"'),preset+" absent");
const fonts=[
  "cormorant-garamond-latin-400-normal",
  "cormorant-garamond-latin-400-italic",
  "rajdhani-latin-400-normal","rajdhani-latin-600-normal",
  "ibm-plex-mono-latin-400-normal","oxanium-latin-400-normal",
  "jetbrains-mono-latin-400-normal","marcellus-latin-400-normal",
  "ibm-plex-sans-latin-400-normal"
];
for(const name of fonts){
  const file="assets/fonts/"+name+".woff2",buffer=fs.readFileSync(path.join(root,file));
  assert(buffer.length>4000&&buffer.subarray(0,4).toString("ascii")==="wOF2","Missing/invalid WOFF2: "+file);
  assert(css.includes(name+".woff2"),"Font not used: "+name);
}
for(const family of ["cormorant-garamond","rajdhani","ibm-plex-mono","oxanium","jetbrains-mono","marcellus","ibm-plex-sans"]){
  assert(read("assets/fonts/licenses/"+family+"-OFL.txt").includes("OPEN FONT LICENSE"),"Missing font license "+family);
}
assert(!/@import\s+url\(https?:/i.test(css)&&!/url\(\s*["']?https?:/i.test(css),"No remote fonts allowed");
assert(css.includes('body.typography-on'),"Original preset must leave the old typography unchanged");
assert(css.includes("Ayarime Cormorant")&&css.includes("Ayarime JetBrains"));
const cut=js.indexOf('$("search-form").addEventListener');
assert(cut>1000,"Missing event handler boundary");
const ctx={URL,Date,Intl,console,setTimeout,clearTimeout,document:{body:{}}};
vm.createContext(ctx);
vm.runInContext(js.slice(0,cut),ctx,{timeout:2500});
function evalJSON(expression){return JSON.parse(vm.runInContext("JSON.stringify("+expression+")",ctx,{timeout:1000}));}
assert.deepEqual(evalJSON("cleanTypography(undefined)"),{preset:"original",scale:100,display:"preset",ui:"preset",mono:"preset",japanese:"preset"});
assert.deepEqual(evalJSON('cleanTypography({preset:"neural",scale:120,display:"marcellus"})'),{preset:"neural",scale:120,display:"marcellus",ui:"preset",mono:"preset",japanese:"preset"});
assert.deepEqual(evalJSON('cleanTypography({preset:"evil",scale:10000,display:"url(javascript:bad)"})'),{preset:"original",scale:100,display:"preset",ui:"preset",mono:"preset",japanese:"preset"});
const captured={};
ctx.preview={style:{setProperty:(key,val)=>{captured[key]=val;}}};
vm.runInContext('applyTypography(preview,{preset:"classic",scale:110})',ctx,{timeout:1000});
assert(captured["--ayr-font-display"].includes("Ayarime Cormorant"));
assert(captured["--ayr-font-ui"].includes("Ayarime Rajdhani"));
assert(captured["--ayr-font-mono"].includes("Ayarime Plex Mono"));
assert.equal(captured["--ayr-type-scale"],"1.1");
assert(js.includes('typography:cleanTypography(x.typography)'),"Legacy settings migration should provide defaults");
assert(js.includes('["motion","contrast","cursor","typography"].includes(f)'),"Cross-tab typography sync required");
assert(js.includes('typography:typographyFromForm()'),"Preset changes must save");
assert(js.includes(',"typography"]'),"Typography should persist on independent storage key");
console.log("ELF//SHELL typography: preset validation, font licensing, WOFF2 assets and CSS integration passed.");
