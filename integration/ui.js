"use strict";
/* One optional website spelling preference; native Firefox always available. */
(() => {
  const SCOPE="https://*/*";
  const $=id=>document.getElementById(id);
  const spell=$("integration-spelling"),apply=$("integration-apply"),
    revoke=$("integration-revoke"),status=$("integration-status"),
    permission=$("integration-permission");
  if(!spell||!apply||!revoke||!status||!permission)return;
  const setStatus=text=>{status.textContent=text;};
  if(typeof browser==="undefined"||!browser.permissions?.request||!browser.runtime?.sendMessage){
    apply.disabled=true;revoke.disabled=true;
    setStatus("Website spelling settings require the installed Firefox extension.");
    return;
  }
  let busy=false;
  const setBusy=flag=>{
    busy=flag;apply.disabled=flag;revoke.disabled=flag;spell.disabled=flag;
  };
  async function refresh() {
    try{
      const result=await browser.runtime.sendMessage({type:"elfshell:integration:get"});
      if(!result?.ok)throw Error(result?.error||"Could not read spelling mode");
      if(!busy)spell.value=result.modes.spellMode;
      permission.textContent=result.allowed?
        "Optional all-HTTPS permission is granted. Broad spelling only runs if enabled.":
        "Broad HTTPS permission is not granted. Firefox native spelling remains available.";
      revoke.disabled=busy||!result.allowed;
      if(!result.allowed&&result.modes.spellMode==="all")
        setStatus("Website access was revoked. Approve a new request to resume.");
    }catch(e){setStatus("Unable to refresh spelling permissions: "+String(e.message||e));}
  }
  apply.addEventListener("click",async()=>{
    if(busy)return;
    const mode=spell.value;
    // Start the optional Firefox prompt synchronously from the real click.
    // Prompts from the toolbar popup can be destroyed when the popup closes.
    let request=null;
    try {
      if(mode==="all")request=browser.permissions.request({origins:[SCOPE]});
    }catch(e){
      setStatus("Permission prompt could not open: "+String(e.message||e));return;
    }
    setBusy(true);
    let applied=false;
    setStatus(request?"Choose Allow or Deny in Firefox's permission prompt…":
      "Updating spelling preferences…");
    try{
      if(request&&!await request){
        setStatus("Permission declined. Your selected preference is retained for retry.");
        return;
      }
      const result=await browser.runtime.sendMessage({
        type:"elfshell:integration:set",modes:{spellMode:mode}
      });
      if(!result?.ok)throw Error(result?.error||"The spelling preference was not applied");
      applied=true;
      setStatus("Spelling setting saved. Unsupported editors retain Firefox's native checker.");
    }catch(e){setStatus("Could not apply spelling settings: "+String(e.message||e));}
    finally{
      setBusy(false);
      await refresh();
      if(!applied)spell.value=mode;
    }
  });
  revoke.addEventListener("click",async()=>{
    if(busy)return;
    setBusy(true);
    try{
      const result=await browser.runtime.sendMessage({
        type:"elfshell:integration:set",modes:{spellMode:"sites"}
      });
      if(!result?.ok)throw Error(result?.error||"Could not disable broad spelling");
      const removed=await browser.permissions.remove({origins:[SCOPE]});
      setStatus(removed?"Broad HTTPS permission revoked; individual RSS/site grants may remain.":
        "Broad spelling disabled; no wildcard permission needed removing.");
    }catch(e){setStatus("Unable to revoke: "+String(e.message||e));}
    finally{setBusy(false);await refresh();}
  });
  browser.permissions.onAdded.addListener(()=>{if(!busy)refresh();});
  browser.permissions.onRemoved.addListener(()=>{if(!busy)refresh();});
  browser.storage.onChanged.addListener((changes,area)=>{
    if(area==="local"&&changes["elfshell:browser-integration:v1"]&&!busy)refresh();
  });
  refresh();
})();