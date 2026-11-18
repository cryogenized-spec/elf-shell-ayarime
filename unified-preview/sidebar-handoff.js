"use strict";
/* One and only one in-extension Workspace launch control: Ayarime's
 * native-sidebar header. The background reuses the canonical Hub tab.
 * The Firefox extension toolbar is the sole advertised sidebar launcher. */
(() => {
  if(document.body?.dataset.view!=="sidebar")return;
  const header=document.querySelector(".side-shell > .sidebar-header");
  if(!header)return;
  const button=document.createElement("button");
  button.id="ayarime-open-workspace";
  button.type="button";
  button.className="mini";
  button.textContent="Open Workspace";
  button.setAttribute("aria-label","Open Ayarime full Workspace");
  const status=document.createElement("span");
  status.className="sr-only";
  status.id="ayarime-workspace-handoff-status";
  status.setAttribute("role","status");
  button.addEventListener("click",()=>{
    const sending=document.getElementById("ai-send");
    const cancel=document.getElementById("ai-cancel");
    if(globalThis.WorkspaceTraceUI?.isRunning()||
       (sending?.disabled && cancel && !cancel.hidden)){
      status.textContent="Finish or stop the current response before switching views.";
      return;
    }
    // Firefox only permits closing a native sidebar from a user gesture.
    // Close before the asynchronous tab-switch request; no new Hub tab is
    // created in the UI itself.
    button.disabled=true;
    // Queue the session draft before Firefox destroys the sidebar document.
    globalThis.WorkspaceConversationUI?.flushDraft?.();
    try{browser.sidebarAction.close().catch(()=>{});}catch{}
    browser.runtime.sendMessage({type:"UI_OPEN_WORKSPACE"})
      .then(reply=>{
        if(!reply?.ok||!reply.result?.focused)
          throw Error(reply?.error||"Workspace could not be opened");
      })
      .catch(error=>{status.textContent=error.message;button.disabled=false;});
  });
  header.append(button,status);
})();
