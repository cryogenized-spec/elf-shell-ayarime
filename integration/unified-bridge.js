"use strict";
/* Unified, dev-only dashboard bridge. No external extension ID or credentials. */
(() => {
  const KIND = "elfshell.workspace.bridge";
  const VERSION = 1;
  const MESSAGE_TYPE = "elfshell:unified:bridge:v1";
  const status = () => document.getElementById("workspace-bridge-status");
  function report(message, error=false) {
    const target = status();
    if (!target) return;
    target.hidden = false;
    target.textContent = message;
    target.classList.toggle("error", error);
  }
  async function message(command) {
    const response = await browser.runtime.sendMessage({
      type:MESSAGE_TYPE,kind:KIND,version:VERSION,command
    });
    if (!response || response.ok !== true)
      throw Error(response?.error || "Ayarime's local workspace engine is unavailable.");
    return response;
  }
  async function allowed(permissions) {
    // Request is invoked immediately in the originating click/keyboard gesture,
    // before any await or deferred bridge operation.
    if (!browser.permissions?.request)
      throw Error("Firefox optional-permission controls are unavailable.");
    let granted;
    try {granted=await browser.permissions.request({permissions});}
    catch {throw Error("Firefox did not grant the requested workspace permissions.");}
    if (!granted)
      throw Error("Workspace access was declined. Your existing tabs are unchanged.");
  }
  async function launch(command,permissions) {
    report(command==="OPEN_ASSISTANT"
      ? "Preparing Ayarime's local AI console…"
      : "Preparing your Firefox workspace…");
    try {
      await allowed(permissions);
      const hello=await message("HELLO");
      if (hello.kind!==KIND || hello.version!==VERSION ||
          !Array.isArray(hello.capabilities) ||
          !hello.capabilities.includes(command))
        throw Error("The unified workspace engine is incompatible with this dashboard.");
      const result=(await message(command)).result;
      if(command==="OPEN_ASSISTANT"){
        if(!result || !result.focused || !Number.isInteger(result.hubTabId))
          throw Error("Workspace AI did not acknowledge the Hub focus.");
        report("Ayarime AI console ready · pinned Hub focused. Use its 'Continue in Firefox Sidebar' control.");
      }else{
        if(!result || !Number.isInteger(result.opened) ||
           !Number.isInteger(result.reused))
          throw Error("Workspace tab launcher returned an invalid result.");
        report("Workspace ready · "+result.opened+" opened · "+result.reused+
          " reused. The AI sidebar is part of this same ELF//SHELL extension.");
      }
      return result;
    }catch(error){
      report("Workspace unavailable: "+(error?.message||"Unexpected error"),true);
      return null;
    }
  }
  window.AyarimeWorkspaceBridge=Object.freeze({
    openAssistant:()=>launch("OPEN_ASSISTANT",["tabs"]),
    openWorkspace:()=>launch("OPEN_WORKSPACE",["tabs","tabGroups"])
  });
})();
