"use strict";
/* Coffee in unsigned unified preview: clear, clickable readiness diagnostics.
   No Google account request is silently attempted. Live Google briefing stays
   disabled until OAuth and source access pass the extension's security gates. */
(() => {
  const button=document.getElementById("coffee-run");
  if(!button)return;
  if(document.body?.dataset.view==="sidebar") {
    button.textContent="Open Morning Coffee in Workspace";
    const status=document.getElementById("coffee-status");
    if(status)status.textContent="Opens the full Coffee tab. Live Google access remains disabled in this unsigned preview.";
    return;
  }
  if(document.body?.dataset.view!=="hub")return;
  button.textContent="Check Morning Coffee readiness";
  const coffee=document.querySelector(".coffee-panel");
  const note=document.createElement("p");
  note.className="quiet";
  note.id="unified-coffee-availability";
  note.textContent="The unified unsigned preview does not yet permit live Google OAuth or Calendar/Tasks reads. You can inspect the connection setup without sharing account data.";
  const connect=document.createElement("button");
  connect.type="button";connect.className="mini";connect.textContent="Review Google connection setup";
  connect.id="unified-coffee-connections";
  connect.addEventListener("click",()=>{location.hash="#connections";});
  button.after(note,connect);
  button.addEventListener("click",event=>{
    // Capture before the legacy live-read handler. The preview cannot produce a
    // real sourced briefing, so never invoke its blocked Google read operation.
    event.preventDefault();event.stopImmediatePropagation();
    const status=document.getElementById("coffee-status");
    if(status)status.textContent="No briefing prepared. Live Google Calendar/Tasks access is disabled in this unsigned build. Review Connections for setup.";
    const results=document.getElementById("coffee-results");
    if(results){
      results.replaceChildren();
      const card=document.createElement("article");
      const header=document.createElement("h3");header.textContent="Morning Coffee readiness";
      const detail=document.createElement("p");
      detail.textContent="Not connected. No Google information was accessed. A live briefing requires a reviewed OAuth implementation and permission for the selected sources.";
      card.append(header,detail);results.append(card);
    }
  },true);
})();
