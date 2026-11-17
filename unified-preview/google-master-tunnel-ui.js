/* Explicit Google Master remote MCP transport check. No automatic network. */
(() => {
  "use strict";
  const button=document.getElementById("master-mcp-ping");
  const output=document.getElementById("master-mcp-ping-result");
  if(!button||!output)return;
  let active=false;
  button.addEventListener("click",async()=>{
    if(active)return;active=true;button.disabled=true;
    output.textContent="Checking the private Google Master MCP endpoint…";
    try{
      const result=await browser.runtime.sendMessage({type:"MASTER_MCP_PING"});
      if(result?.ok!==true||result?.probe?.reachable!==true)
        throw Error("MCP discovery unavailable");
      const {total,read,write}=result.probe;
      if(!Number.isInteger(total)||!Number.isInteger(read)||!Number.isInteger(write))
        throw Error("Invalid MCP discovery response");
      output.textContent="Remote MCP reachable · "+total+" tools ("+read+
        " read, "+write+" write). No Google content was requested and no tool was executed.";
    }catch{
      output.textContent="MCP probe unavailable. Check host permission and the separate Firefox OAuth connection.";
    }finally{active=false;button.disabled=false;}
  });
})();
