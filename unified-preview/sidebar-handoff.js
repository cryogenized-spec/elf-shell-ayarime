"use strict";
/* A visible full-screen handoff from the narrow sidebar. Firefox sidebar
   close is only attempted directly in a real button click handler. */
(() => {
  if(document.body?.dataset.view!=="sidebar")return;
  const chat=document.querySelector(".side-shell .ai-console");
  const title=chat?.querySelector("h2");
  if(!title)return;
  const button=document.createElement("button");
  button.id="ayarime-open-workspace";button.type="button";button.className="mini";
  button.textContent="▣ Open full Workspace";
  const notice=document.createElement("p");notice.className="quiet";
  notice.id="ayarime-workspace-handoff-status";
  button.addEventListener("click",()=>{
    try{browser.sidebarAction.close().catch(()=>{});}catch{}
    browser.tabs.create({url:browser.runtime.getURL("hub.html#overview")})
      .catch(error=>{notice.textContent="Unable to open Workspace: "+error.message;});
  });
  title.after(button,notice);
})();
