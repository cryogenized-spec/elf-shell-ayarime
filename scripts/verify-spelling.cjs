"use strict";
// Verify that Mozilla's shipped spelling bundle can be rebuilt byte-for-byte
// from the official npm packages pinned by spelling/vendor/package-lock.json.
// Build tools are not shipped in the AMO runtime archive.
const fs=require("node:fs");
const os=require("node:os");
const path=require("node:path");
const crypto=require("node:crypto");
const {spawnSync}=require("node:child_process");
const root=path.resolve(__dirname,"..");
const vendor=path.join(root,"spelling","vendor");
const bundled=path.join(root,"spelling","nspell-bundle.js");
const temporary=fs.mkdtempSync(path.join(os.tmpdir(),"ayarime-spell-"));
function sha256(bytes){return crypto.createHash("sha256").update(bytes).digest("hex");}
function run(executable,args,options){
  const result=spawnSync(executable,args,{...options,stdio:"inherit"});
  if(result.error)throw result.error;
  if(result.status!==0)throw Error(executable+" failed ("+(result.status??"unknown")+")");
}
try{
  // npm ci enforces the frozen registry URL/integrity for every dependency.
  run(process.platform==="win32"?"npm.cmd":"npm",
    ["ci","--ignore-scripts","--no-audit","--no-fund"],{cwd:vendor});
  const cli=path.join(vendor,"node_modules","browserify","bin","cmd.js");
  const generated=path.join(temporary,"nspell-bundle.js");
  run(process.execPath,[cli,"src/index.js","-s","nspell","-o",generated],{cwd:vendor});
  const expected=fs.readFileSync(bundled),actual=fs.readFileSync(generated);
  if(!expected.equals(actual)){
    throw Error("Bundled spelling engine is NOT reproducible; expected SHA256 "+
      sha256(expected)+", generated "+sha256(actual)+". Do not submit to Mozilla.");
  }
  console.log("nspell 2.1.5 / browserify 17.0.1: byte-for-byte reproducible ("+
    actual.length+" bytes, SHA256 "+sha256(actual)+").");
}catch(error){
  console.error("Spelling source verification failed:",error.message);
  process.exitCode=1;
}finally{
  fs.rmSync(temporary,{recursive:true,force:true});
}
