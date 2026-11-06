"use strict";
/* Applies only to HTTPS top-level pages after explicit broad permission.
   Artwork is packaged locally. No page text or network requests. */
(() => {
  if(globalThis.__elfshellCursorRefresh) {
    globalThis.__elfshellCursorRefresh();
    return;
  }
  const KEY="elfshell:browser-integration:v1";
  const CURSOR="elfshell-workspace-v3:field:cursor";
  const STYLE_ID="elfshell-global-cursors-v1";
  const choices=new Set(["classic-spearhead","crystal-tech-shard",
    "elven-feather","hollow-frame","rune-edged","minimal-precision"]);
  let revision=0;
  const icon=(file,x=3,y=3,fallback="default")=>
    'url("'+browser.runtime.getURL("assets/cursors/"+file)+'") '+x+' '+y+', '+fallback;
  const state=(name,x=3,y=3,fallback="default")=>
    icon("states/"+name+"-48.png",x,y,fallback);
  function remove() {document.getElementById(STYLE_ID)?.remove();}
  async function refresh() {
    const current=++revision;
    try {
      const [permission,values]=await Promise.all([
        browser.runtime.sendMessage({type:"elfshell:integration:cursor-allowed"}),
        browser.storage.local.get([KEY,CURSOR])
      ]);
      if(current!==revision)return;
      if(!permission?.allowed||values[KEY]?.cursorMode!=="all") {
        remove();return;
      }
      const choice=values[CURSOR];
      const pointer=choices.has(choice)?
        icon(choice+".png",3,3,"default"):state("pointer");
      const text=state("ibeam",21,24,"text");
      const link=state("link",7,3,"pointer");
      const busy=state("busy",24,24,"progress");
      const crosshair=state("crosshair",24,24,"crosshair");
      const resize=state("resize",24,24,"nwse-resize");
      const css=[
        "html,html * {cursor:"+pointer+" !important;}",
        "html :is(input,textarea,[contenteditable='true'],[contenteditable='plaintext-only'],[role='textbox'],.ProseMirror),",
        "html :is([contenteditable='true'],[contenteditable='plaintext-only'],[role='textbox'],.ProseMirror) * {cursor:"+text+" !important;}",
        "html :is(a[href],button,summary,select,label[for],[role='button'],[role='link'],input[type='button'],input[type='submit'],input[type='reset'],input[type='checkbox'],input[type='radio']),",
        "html :is(a[href],button,summary,[role='button'],[role='link']) * {cursor:"+link+" !important;}",
        "html :is([aria-busy='true'],[data-cursor='busy'],[style*='cursor: wait'],[style*='cursor: progress']) {cursor:"+busy+" !important;}",
        "html :is([data-cursor='crosshair'],.cursor-crosshair) {cursor:"+crosshair+" !important;}",
        "html :is([role='separator'],[data-cursor='resize'],[data-resize-handle]) {cursor:"+resize+" !important;}"
      ].join("\n");
      let element=document.getElementById(STYLE_ID);
      if(!element) {
        element=document.createElement("style");
        element.id=STYLE_ID;
        (document.head||document.documentElement).append(element);
      }
      element.textContent=css;
    } catch {
      // Failure never leaves a stale custom cursor active.
      if(current===revision)remove();
    }
  }
  globalThis.__elfshellCursorRefresh=refresh;
  browser.storage.onChanged.addListener((changes,area)=>{
    if(area==="local"&&(changes[KEY]||changes[CURSOR]))refresh();
  });
  browser.runtime.onMessage.addListener(message=>{
    if(message?.type==="elfshell:integration:cursor-sync")refresh();
  });
  refresh();
})();