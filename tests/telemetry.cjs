"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const {spawnSync}=require("node:child_process");
const root=path.resolve(__dirname,"..");
const read=name=>fs.readFileSync(path.join(root,name),"utf8");
const manifest=JSON.parse(read("manifest.json"));
const html=read("newtab.html"),css=read("styles.css");
const ui=read("telemetry.js"),background=read("background.js");
assert(manifest.optional_permissions.includes("nativeMessaging"),"native permission must be optional");
assert(html.includes('<script defer src="telemetry.js"></script>'));
for(const id of ["telemetry-toggle","telemetry-status","telemetry-hint","cpu-temp","gpu-temp","ram-usage","fan-speed","system-load"])
  assert(html.includes('id="'+id+'"'),"Missing telemetry UI: "+id);
assert(html.includes('href="https://chatgpt.com/"')&&html.includes('assets/chatgpt-mark.svg'));
assert(!css.includes("-webkit-line-clamp:2"),"Memory excerpts must not be line-clamped");
assert(ui.includes('browser.permissions.request({permissions:["nativeMessaging"]})'));
assert(background.includes('browser.runtime.sendNativeMessage("com.elfshell.ayarime.telemetry"'));
assert(!ui.includes("localhost")&&!ui.includes("127.0.0.1"),"Local messaging must not use a listening port");
assert(read("scripts/package.py").includes("'telemetry.js'"),"UI file must ship with extension");
const host=path.join(root,"telemetry/host.py");
assert(read("telemetry/install.py").includes('"allowed_extensions": [EXTENSION_ID]'),"Host installer must restrict extension ID");
const python=spawnSync("python3",["--version"],{encoding:"utf8"});
if(python.error) {
  console.log("Python3 unavailable; native-host protocol test skipped.");
} else {
  function call(obj) {
    const payload=Buffer.from(JSON.stringify(obj),"utf8");
    const header=Buffer.alloc(4);
    header.writeUInt32LE(payload.length);
    const child=spawnSync("python3",[host],{input:Buffer.concat([header,payload]),maxBuffer:65536,timeout:7000});
    assert.equal(child.status,0,"Host exit failure: "+child.stderr?.toString());
    const output=child.stdout;
    assert(output.length>=4,"Host did not return a frame");
    assert.equal(output.readUInt32LE(0),output.length-4,"Malformed native message frame");
    return JSON.parse(output.subarray(4).toString("utf8"));
  }
  const bad=call({action:"run",script:"anything"});
  assert.equal(bad.ok,false,"Host must reject arbitrary commands");
  const data=call({action:"read"});
  assert.equal(data.ok,true);
  for(const field of ["cpu_c","gpu_c","fan_rpm","ram_used_gib","ram_total_gib","load_1m"])
    assert(Object.prototype.hasOwnProperty.call(data,field),"Missing metric "+field);
  assert(Array.isArray(data.fan_rpm));
  assert(data.cpu_c===null || typeof data.cpu_c==="number");
  assert(data.gpu_c===null || typeof data.gpu_c==="number");
}
console.log("Optional local telemetry permission, UI, native-message framing and safety checks passed.");
