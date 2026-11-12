"use strict";
/* Unsigned unified-preview AI opt-in. Standalone storage key: core workspace
   v2/v3 fields and the backup/export format are never changed by this module. */
(() => {
  const KEY="elfshell.unified.aiEnabled.v1";
  const button=()=>document.getElementById("ai-module-toggle");
  const status=()=>document.getElementById("ai-module-status");
  const ask=()=>document.getElementById("ask-ayarime-toggle");
  let enabled=false,loaded=false;
  function render(){
    const toggle=button(),note=status(),launch=ask();
    if(toggle){
      toggle.setAttribute("aria-pressed",String(enabled));
      toggle.textContent=enabled?"✧ DISABLE AYARIME AI":"✧ ENABLE AYARIME AI";
      toggle.disabled=!loaded;
    }
    if(note)note.textContent=!loaded
      ?"Reading AI module preferences from Firefox local storage…"
      :enabled
        ?"AI module enabled locally. Firefox tab access and provider consent remain separate."
        :"AI module off. No model requests; your existing ELF//SHELL settings are unchanged.";
    if(launch){
      launch.setAttribute("aria-disabled",String(!enabled));
      launch.title=enabled?"Focus the integrated Ayarime AI console":"Enable Ayarime AI first; no account access is granted";
    }
  }
  function current(){return loaded&&enabled;}
  const ready=(async()=>{
    try{
      const data=await browser.storage.local.get(KEY);
      enabled=data[KEY]===true;  // missing/malformed preference -> disabled
    }catch{enabled=false;}
    loaded=true;
    render();
    return enabled;
  })();
  async function toggle(){
    await ready;
    const next=!enabled;
    const node=button();
    if(node)node.disabled=true;
    try{
      // Key is not part of ELF//SHELL's exported v5 settings, field-save
      // migration, or its existing storage object: no legacy values are touched.
      await browser.storage.local.set({[KEY]:next});
      enabled=next;
    }catch{
      const note=status();
      if(note)note.textContent="Firefox could not save the AI module preference. No changes applied.";
    }finally{render();}
  }
  document.addEventListener("DOMContentLoaded",()=>{
    render();
    button()?.addEventListener("click",()=>void toggle());
  });
  browser.storage.onChanged?.addListener((changes,area)=>{
    if(area!=="local"||!Object.prototype.hasOwnProperty.call(changes,KEY))return;
    enabled=changes[KEY].newValue===true;
    loaded=true;
    render();
  });
  window.AyarimeUnifiedModule=Object.freeze({isEnabled:current,ready});
})();