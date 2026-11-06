"use strict";
/* Dashboard-only, user-initiated optional browser integration preferences. */
(() => {
  const scope="https://*/*";
  const $=id=>document.getElementById(id);
  const cursor=$("integration-cursors"),spell=$("integration-spelling");
  const apply=$("integration-apply"),revoke=$("integration-revoke");
  const status=$("integration-status"),permission=$("integration-permission");
  if(!cursor||!spell||!apply||!revoke||!status||!permission)return;
  const setStatus=(message)=>{status.textContent=message;};
  const supported=typeof browser!=="undefined"&&
    !!browser.permissions?.request&&!!browser.runtime?.sendMessage;
  if(!supported) {
    apply.disabled=true;revoke.disabled=true;
    setStatus("Available only when installed as a Firefox extension.");
    return;
  }
  let busy=false;
  const setBusy=value=>{
    busy=value;apply.disabled=value;revoke.disabled=value;
    cursor.disabled=value;spell.disabled=value;
  };
  const desired=()=>({cursorMode:cursor.value,spellMode:spell.value});
  async function refresh() {
    try {
      const state=await browser.runtime.sendMessage({type:"elfshell:integration:get"});
      if(!state?.ok)throw Error(state?.error||"Integration status unavailable");
      if(!busy) {
        cursor.value=state.modes.cursorMode;
        spell.value=state.modes.spellMode;
      }
      permission.textContent=state.allowed?
        "All-HTTPS permission granted in Firefox. Broad scripts run only for enabled modes.":
        "No all-HTTPS permission. Browser-wide features are inactive.";
      revoke.disabled=busy||!state.allowed;
      if(!busy&&(state.modes.cursorMode==="all"||state.modes.spellMode==="all")&&!state.allowed)
        setStatus("Firefox site permission has been revoked. Apply again to request access.");
    }catch(error) {
      setStatus("Could not read integration settings: "+String(error.message||error));
    }
  }
  apply.addEventListener("click",async()=>{
    if(busy)return;
    // IMPORTANT: request immediately inside the trusted click gesture,
    // *before* any await or asynchronous state read. This is an ordinary
    // extension page, not the toolbar popup that Firefox may close.
    const modes=desired();
    let request=null;
    try {
      if(modes.cursorMode==="all"||modes.spellMode==="all")
        request=browser.permissions.request({origins:[scope]});
    }catch(error) {
      setStatus("Firefox could not start the permission request: "+String(error.message||error));
      return;
    }
    let success=false;
    setBusy(true);
    setStatus(request?"Waiting for your explicit Firefox site-access choice…":"Updating integration modes…");
    try {
      if(request&&!await request) {
        setStatus("Permission denied. Your previous settings remain unchanged.");
        return;
      }
      const result=await browser.runtime.sendMessage({
        type:"elfshell:integration:set",modes
      });
      if(!result?.ok)throw Error(result?.error||"Could not save integration modes");
      success=true;
      setStatus("Saved. Existing eligible tabs updated; restricted pages keep Firefox defaults.");
    }catch(error) {
      setStatus("Integration was not activated: "+String(error.message||error));
    }finally {
      setBusy(false);await refresh();
      // Denying permission must not erase the user\'s pending choices.
      // Keep both dropdowns selected so Retry requests consent again.
      if(!success){cursor.value=modes.cursorMode;spell.value=modes.spellMode;}
    }
  });
  revoke.addEventListener("click",async()=>{
    if(busy)return;
    setBusy(true);
    setStatus("Revoking optional broad HTTPS access…");
    try {
      // Switch broad features off first, before revoking their shared grant.
      // Specific host grants for RSS or manually enabled spelling stay intact.
      const result=await browser.runtime.sendMessage({
        type:"elfshell:integration:set",
        modes:{cursorMode:"station",spellMode:"sites"}
      });
      if(!result?.ok)throw Error(result?.error||"Failed to deactivate broad features");
      const removed=await browser.permissions.remove({origins:[scope]});
      setStatus(removed?
        "Broad HTTPS access revoked. Separately approved RSS/site access may remain.":
        "Broad features disabled. No separate broad grant was removed.");
    }catch(error) {
      setStatus("Could not complete revocation: "+String(error.message||error));
    }finally {
      setBusy(false);await refresh();
    }
  });
  browser.permissions.onAdded.addListener(()=>{if(!busy)refresh();});
  browser.permissions.onRemoved.addListener(()=>{if(!busy)refresh();});
  browser.storage.onChanged.addListener((changes,area)=>{
    if(area==="local"&&changes["elfshell:browser-integration:v1"]&&!busy)refresh();
  });
  refresh();
})();