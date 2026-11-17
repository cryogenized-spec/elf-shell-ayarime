"use strict";
(() => {
  const button=document.getElementById("ayarime-sidebar-launcher");
  if(!button)return;
  const KEY="elfshell.station.launcherVisible.v1";
  const message=document.getElementById("ayarime-sidebar-launcher-status");
  const update=()=>browser.storage.local.get(KEY)
    .then(state=>{button.hidden=state[KEY]===false;})
    .catch(()=>{button.hidden=false;});
  button.addEventListener("click",()=>{
    // Firefox owns its single, native sidebar; no custom overlay is created.
    const open=browser.sidebarAction?.open?.();
    if(!open){message.textContent="Use Firefox's sidebar button to open Ayarime.";return;}
    Promise.resolve(open).catch(()=>{
      message.textContent="Firefox could not open the sidebar. Use the sidebar selector and choose Ayarime.";
    });
  });
  document.addEventListener("keydown",event=>{
    if(event.altKey&&event.shiftKey&&event.key.toLowerCase()==="a"&&
       !event.ctrlKey&&!event.metaKey){
      event.preventDefault();button.click();
    }
  });
  browser.storage.onChanged?.addListener((changes,area)=>{
    if(area==="local"&&Object.hasOwn(changes,KEY))void update();
  });
  void update();
})();
