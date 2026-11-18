"use strict";
/* The Hub and native sidebar are two views of one Firefox-session chat.
 * When the Hub tab is foreground, a manually opened Firefox sidebar becomes
 * passive instead of rendering a second conversation alongside the Hub.
 * Firefox chrome remains under the user's control; we never seize it. */
(() => {
  const view=document.body?.dataset.view;
  if(view==="hub"){
    browser.runtime.sendMessage({type:"UI_REGISTER_HUB"})
      .catch(()=>{ /* The shared transcript works even if foreground tracking is unavailable. */ });
    return;
  }
  if(view!=="sidebar")return;
  const shell=document.querySelector("main.side-shell");
  if(!shell)return;
  const passive=document.createElement("p");
  passive.id="ayarime-passive-surface";
  passive.textContent="Workspace active";
  passive.hidden=true;
  shell.append(passive);
  let seq=0;
  async function update(){
    const now=++seq;
    try{
      const reply=await browser.runtime.sendMessage({type:"UI_SURFACE_STATUS"});
      if(now!==seq||!reply?.ok)return;
      const hub=reply.hubActive===true;
      document.body.classList.toggle("hub-foreground",hub);
      passive.hidden=!hub;
    }catch{
      // Permission errors must not invent a current Hub. Retain the normal
      // native sidebar, with conversation still stored centrally.
    }
  }
  browser.tabs?.onActivated?.addListener(()=>void update());
  window.addEventListener("focus",()=>void update());
  document.addEventListener("visibilitychange",()=>{
    if(!document.hidden)void update();
  });
  void update();
})();
