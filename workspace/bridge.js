"use strict";
/* ELF//SHELL -> optional Workspace AI companion: no permissions, secrets or Google data. */
(() => {
  const EXTENSION_ID = "workspace-ai@elf-shell.local";
  const KIND = "elfshell.workspace.bridge";
  const VERSION = 1;
  const status = () => document.getElementById("workspace-bridge-status");
  function report(message, failed=false) {
    const element = status();
    if (!element) return;
    element.hidden = false;
    element.textContent = message;
    element.classList.toggle("error", failed);
  }
  async function message(command, extras={}) {
    if (typeof browser === "undefined" || !browser.runtime?.sendMessage)
      throw new Error("Firefox extension messaging is unavailable");
    let response;
    try {
      response = await browser.runtime.sendMessage(EXTENSION_ID, {
        kind:KIND, version:VERSION, command, ...extras
      });
    } catch {
      throw new Error("Install or enable the optional ELF//SHELL Workspace AI companion");
    }
    if (!response || response.ok !== true)
      throw new Error(response?.error || "Workspace AI did not respond");
    return response;
  }
  async function openAssistant() {
    report("Opening Ayarime's AI console in the Workspace Hub…");
    try {
      const hello=await message("HELLO");
      if (hello.kind!==KIND || hello.version!==VERSION || !Array.isArray(hello.capabilities))
        throw new Error("Workspace AI companion protocol is incompatible");
      if (!hello.capabilities.includes("OPEN_ASSISTANT"))
        throw new Error("Update the optional Workspace AI companion to enable Ask Ayarime");
      const result=(await message("OPEN_ASSISTANT")).result;
      if(!result || result.focused!==true || !Number.isInteger(result.hubTabId) || result.view!=="assistant")
        throw new Error("Workspace AI returned an invalid assistant handoff");
      report("Ayarime AI console opened in the pinned Workspace Hub. Use its toolbar button to open the Firefox sidebar.");
      return result;
    }catch(error){
      report("Assistant unavailable: "+(error?.message||"Unexpected error"),true);
      return null;
    }
  }
  async function openWorkspace() {
    report("Asking Ayarime to prepare your workspace…");
    try {
      const hello = await message("HELLO");
      if (hello.kind !== KIND || hello.version !== VERSION ||
          !Array.isArray(hello.capabilities) ||
          !hello.capabilities.includes("OPEN_WORKSPACE"))
        throw new Error("Workspace AI companion protocol is incompatible");
      const result = (await message("OPEN_WORKSPACE")).result;
      if (!result || !Number.isInteger(result.opened) || !Number.isInteger(result.reused))
        throw new Error("Workspace AI returned an invalid launch result");
      report("Workspace ready · " + result.opened + " opened · " + result.reused + " reused. Use the Workspace AI toolbar button to show Ayarime in Firefox’s sidebar.");
      return result;
    } catch (error) {
      report("Workspace unavailable: " + (error?.message || "Unexpected error"), true);
      return null;
    }
  }
  window.AyarimeWorkspaceBridge = Object.freeze({ openWorkspace, openAssistant });
})();