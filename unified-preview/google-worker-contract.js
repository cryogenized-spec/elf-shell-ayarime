/* Google Master Worker M10 read-only contract — inert developer preview.
 * No network requests, OAuth sessions, token storage, provider prompts or tool
 * execution here. Future authenticated background transport is deliberately absent.
 */
(function(root){
  "use strict";
  const NAMES=Object.freeze([
    "tasks_list_tasklists","tasks_list_tasks","tasks_get_task",
    "script_get_project","script_get_content","script_list_versions",
    "script_list_deployments"
  ]);
  const ALLOWED=new Set(NAMES);
  const MAX_INPUT_BYTES=32768,MAX_CAPABILITIES=128;
  function plainObject(value){
    return value!==null&&typeof value==="object"&&!Array.isArray(value)&&
      (Object.getPrototypeOf(value)===Object.prototype||
       Object.getPrototypeOf(value)===null);
  }
  function parseCapabilities(payload){
    if(!plainObject(payload)||!Array.isArray(payload.operations)||
       payload.operations.length>MAX_CAPABILITIES)
      throw Error("Invalid Google Master capabilities response");
    const accepted=[],seen=new Set();
    for(const item of payload.operations){
      if(!plainObject(item)||typeof item.name!=="string")continue;
      if(!ALLOWED.has(item.name)||item.risk!=="read"||seen.has(item.name))continue;
      if(typeof item.description!=="string"||item.description.length>512)continue;
      seen.add(item.name);
      accepted.push(Object.freeze({
        name:item.name,
        description:item.description.slice(0,512),
        risk:"read",
        product:item.name.startsWith("tasks_")?"Google Tasks":"Google Apps Script"
      }));
    }
    return Object.freeze(accepted);
  }
  function previewRead(catalog,operation,input){
    if(!Array.isArray(catalog)||!catalog.some(item=>
       item&&item.name===operation&&item.risk==="read")||
       !ALLOWED.has(operation))
      throw Error("Google operation is unavailable or not approved for this preview");
    if(!plainObject(input))throw Error("Google operation input must be an object");
    let serialized;
    try{serialized=JSON.stringify(input);}catch{throw Error("Invalid Google operation input");}
    if(typeof serialized!=="string"||serialized.length===0)throw Error("Invalid Google operation input");
    const bytes=typeof TextEncoder==="function"
      ?new TextEncoder().encode(serialized).byteLength
      :Buffer.byteLength(serialized,"utf8");
    if(bytes>MAX_INPUT_BYTES)throw Error("Google operation input exceeds 32 KiB");
    if(Object.keys(input).some(key=>["__proto__","prototype","constructor"].includes(key)))
      throw Error("Unsafe input key");
    return Object.freeze({
      operation,
      product:operation.startsWith("tasks_")?"Google Tasks":"Google Apps Script",
      risk:"read",
      method:"POST",
      path:"/v1/operations/"+operation,
      inputKeys:Object.freeze(Object.keys(input).sort()),
      payloadBytes:bytes,
      requires:"MCP resource OAuth bearer with mcp:read plus separately linked Google account",
      executionEnabled:false
    });
  }
  root.AyarimeGoogleWorkerContract=Object.freeze({
    NAMES,MAX_INPUT_BYTES,parseCapabilities,previewRead
  });
  if(typeof module!=="undefined"&&module.exports)
    module.exports=root.AyarimeGoogleWorkerContract;
})(globalThis);
