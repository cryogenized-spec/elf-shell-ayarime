/* ELF//SHELL unsigned engineering preview — fixed remote MCP transport probe.
 * This module NEVER executes tools or contacts Google on its own.
 * Only an explicit authenticated Hub button may call probe().
 */
(function(root){
  "use strict";
  const RESOURCE="https://google-master-mcp.cryogenized.workers.dev/mcp";
  const ORIGIN="https://google-master-mcp.cryogenized.workers.dev";
  const PROTOCOL="2026-07-28";
  const MAX_BYTES=512*1024,MAX_TOOLS=250;
  function fail(code){const e=new Error(code);e.name="AyarimeMcpConnectionError";return e;}
  async function decode(response){
    if(!/^application\/json(?:\s*;|$)/i.test(response.headers?.get?.("content-type")||""))
      throw fail("MCP_MEDIA_TYPE_UNSUPPORTED");
    const claimed=response.headers?.get?.("content-length");
    if(claimed&&(!/^\d+$/.test(claimed)||Number(claimed)>MAX_BYTES))
      throw fail("MCP_REPLY_TOO_LARGE");
    if(!response.body?.getReader)throw fail("MCP_REPLY_INVALID");
    const reader=response.body.getReader(),parts=[];let count=0;
    try{
      for(;;){
        const {value,done}=await reader.read();if(done)break;
        if(!(value instanceof Uint8Array))throw fail("MCP_REPLY_INVALID");
        count+=value.byteLength;if(count>MAX_BYTES)throw fail("MCP_REPLY_TOO_LARGE");
        parts.push(value);
      }
    }finally{try{await reader.cancel();}catch{}reader.releaseLock();}
    const bytes=new Uint8Array(count);let at=0;
    for(const part of parts){bytes.set(part,at);at+=part.byteLength;}
    try{return JSON.parse(new TextDecoder("utf-8",{fatal:true}).decode(bytes));}
    catch{throw fail("MCP_REPLY_INVALID");}
  }
  async function probe({getAccessToken,hasHostPermission,fetchImpl=root.fetch,timeoutMs=12000}={}){
    if(typeof getAccessToken!=="function"||typeof hasHostPermission!=="function"||
       typeof fetchImpl!=="function"||!Number.isSafeInteger(timeoutMs)||
       timeoutMs<1000||timeoutMs>30000)throw fail("MCP_PROBE_CONFIGURATION_INVALID");
    let allowed=false;
    try{allowed=await hasHostPermission(ORIGIN);}catch{}
    if(allowed!==true)throw fail("MCP_FIREFOX_HOST_PERMISSION_REQUIRED");
    let token;
    try{token=await getAccessToken();}catch{throw fail("MCP_CLIENT_OAUTH_REQUIRED");}
    if(typeof token!=="string"||token.length<10||token.length>8192||
       /[^\x21-\x7e]/.test(token))throw fail("MCP_CLIENT_OAUTH_REQUIRED");
    const controller=new AbortController();
    const timer=setTimeout(()=>controller.abort(),timeoutMs);
    const body=JSON.stringify({
      jsonrpc:"2.0",id:1,method:"tools/list",
      params:{_meta:{
        "io.modelcontextprotocol/protocolVersion":PROTOCOL,
        "io.modelcontextprotocol/clientCapabilities":{},
        "io.modelcontextprotocol/clientInfo":{name:"elf-shell-ayarime",version:"0.5.6"}
      }}
    });
    try{
      const res=await fetchImpl(RESOURCE,{
        method:"POST",headers:{
          Authorization:"Bearer "+token,
          Accept:"application/json, text/event-stream",
          "Content-Type":"application/json",
          "MCP-Protocol-Version":PROTOCOL,
          "Mcp-Method":"tools/list"
        },body,signal:controller.signal,
        credentials:"omit",cache:"no-store",redirect:"error",referrerPolicy:"no-referrer"
      });
      if(!res||!Number.isInteger(res.status))throw fail("MCP_REPLY_INVALID");
      if(res.status===401||res.status===403)throw fail("MCP_CLIENT_SCOPE_REQUIRED");
      if(res.status===429)throw fail("MCP_RATE_LIMITED");
      if(!res.ok)throw fail("MCP_REMOTE_UNAVAILABLE");
      const data=await decode(res);
      const tools=data?.result?.tools;
      if(data?.jsonrpc!=="2.0"||data?.id!==1||!Array.isArray(tools)||
         tools.length>MAX_TOOLS)throw fail("MCP_REPLY_INVALID");
      const seen=new Set();let read=0,write=0;
      for(const tool of tools){
        if(!tool||typeof tool.name!=="string"||
           !/^[a-z][a-z0-9_]{0,95}$/.test(tool.name)||
           seen.has(tool.name))throw fail("MCP_REPLY_INVALID");
        seen.add(tool.name);
        const schemes=tool.securitySchemes;
        if(!Array.isArray(schemes)||!schemes.length||
           !schemes.some(x=>x?.type==="oauth2"&&Array.isArray(x.scopes)&&
             x.scopes.includes("mcp:read")))throw fail("MCP_SECURITY_METADATA_INVALID");
        if(schemes.some(x=>x?.type==="oauth2"&&x.scopes?.includes("mcp:write")))
          write++;
        else read++;
      }
      return Object.freeze({resource:RESOURCE,protocol:PROTOCOL,
        total:tools.length,read,write,reachable:true,
        toolsExecuted:0,googleContentFetched:false});
    }catch(error){
      if(controller.signal.aborted)throw fail("MCP_PROBE_TIMEOUT");
      if(error?.name==="AyarimeMcpConnectionError")throw error;
      throw fail("MCP_REMOTE_UNAVAILABLE");
    }finally{clearTimeout(timer);}
  }
  root.AyarimeGoogleMasterTunnel=Object.freeze({RESOURCE,ORIGIN,PROTOCOL,probe});
  if(typeof module!=="undefined"&&module.exports)
    module.exports=root.AyarimeGoogleMasterTunnel;
})(globalThis);
