"use strict";
/* ELF//SHELL optional spelling UI. Handles supported contenteditable editors
   only; keeps Firefox's native spellchecker on unsupported fields. */
(() => {
  if(globalThis.__elfshellSpelling){
    globalThis.__elfshellSpelling.enable();
    return;
  }
  const MARK="elfshell-spelling-errors-v1";
  const ignored=new Set();
  let enabled=true, editor=null, originalSpell=null, revision=0, composing=false, timer=0;
  let mistakes=new Set(), menu=null, menuRange=null, menuWord="";
  const WORD=/[A-Za-z]+(?:['’\-][A-Za-z]+)*/g;
  const request=(type,extra={})=>browser.runtime.sendMessage({type:"elfshell:spelling:"+type,...extra});
  const asElement=n=>n instanceof Element?n:n?.parentElement;
  function closestEditor(n){
    const el=asElement(n);
    return el?.closest?.('[contenteditable="true"],[contenteditable="plaintext-only"]')||null;
  }
  function canManage(root){
    if(!root||!root.isConnected||root.closest('code,pre,[role="code"],[data-elfshell-spelling-off]'))return false;
    if(root.getAttribute("spellcheck")==="false")return false;
    return !!(globalThis.CSS?.highlights&&globalThis.Highlight&&document.caretPositionFromPoint);
  }
  function closeMenu(){
    if(menu){menu.remove();menu=null;}
    menuRange=null;menuWord="";
  }
  function clearMark(){if(globalThis.CSS?.highlights)CSS.highlights.delete(MARK);mistakes.clear();}
  function restore(){
    clearTimeout(timer);++revision;closeMenu();clearMark();
    if(editor&&editor.isConnected){
      if(originalSpell===null)editor.removeAttribute("spellcheck");
      else editor.setAttribute("spellcheck",originalSpell);
    }
    editor=null;originalSpell=null;
  }
  function tokens(root){
    const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
    const result=[];let chars=0;
    while(walker.nextNode()&&result.length<350&&chars<4500){
      const node=walker.currentNode;
      const parent=node.parentElement;
      if(!parent||parent.closest('code,pre,[contenteditable="false"],[data-elfshell-spelling-off]'))continue;
      chars+=node.data.length;
      for(const match of node.data.matchAll(WORD)){
        if(match[0].length<3||match[0].length>78)continue;
        const range=document.createRange();
        range.setStart(node,match.index);range.setEnd(node,match.index+match[0].length);
        result.push({word:match[0],range});
        if(result.length>=350)break;
      }
    }
    return result;
  }
  async function refresh(){
    const root=editor;
    if(!enabled||!root||composing)return;
    const thisRevision=++revision;
    const found=tokens(root);
    const words=[...new Set(found.map(x=>x.word).filter(w=>!ignored.has(w)))];
    try{
      const response=await request("check",{words});
      if(!response?.ok)throw Error(response?.error||"Spelling not available");
      if(thisRevision!==revision||root!==editor||!enabled)return;
      mistakes=new Set(response.incorrect||[]);
      const ranges=found.filter(item=>mistakes.has(item.word)).map(item=>item.range);
      CSS.highlights.set(MARK,new Highlight(...ranges));
      // Only now is the replacement checker known to be working.
      root.setAttribute("spellcheck","false");
    }catch(error){
      if(thisRevision===revision&&root===editor){
        console.warn("ELF//SHELL spelling unavailable; using Firefox spelling.",error);
        restore();
      }
    }
  }
  function selectEditor(root){
    if(root===editor)return;
    restore();
    if(!enabled||!canManage(root))return;
    editor=root;
    originalSpell=root.getAttribute("spellcheck");
    refresh();
  }
  function schedule(){
    clearTimeout(timer);
    timer=setTimeout(refresh,240);
  }
  function clickedToken(evt){
    if(!editor||!document.caretPositionFromPoint)return null;
    const pos=document.caretPositionFromPoint(evt.clientX,evt.clientY);
    const node=pos?.offsetNode;
    if(!node||node.nodeType!==Node.TEXT_NODE||!editor.contains(node))return null;
    const offset=pos.offset;
    for(const match of node.data.matchAll(WORD)){
      const start=match.index,end=start+match[0].length;
      if(offset>=start&&offset<=end&&mistakes.has(match[0])){
        const range=document.createRange();
        range.setStart(node,start);range.setEnd(node,end);
        return {word:match[0],range};
      }
    }
    return null;
  }
  function replace(choice){
    if(!editor||!menuRange||!menuRange.startContainer.isConnected)return closeMenu();
    const root=editor,range=menuRange.cloneRange();
    closeMenu();
    try{
      root.focus();
      const selection=getSelection();
      selection.removeAllRanges();selection.addRange(range);
      // insertText cooperates with Firefox's editor undo stack and common
      // rich editors. Do not fall back to raw textContent/innerHTML mutation.
      if(!document.execCommand("insertText",false,choice)){
        console.warn("ELF//SHELL: this editor rejected replacement; no DOM fallback.");
      }
      schedule();
    }catch(error){console.warn("ELF//SHELL: replacement unavailable",error);}
  }
  function placeMenu(evt,word,range,suggestions){
    closeMenu();menuWord=word;menuRange=range;
    const pane=document.createElement("div");
    pane.className="elfshell-spell-menu";
    pane.setAttribute("role","menu");
    pane.setAttribute("aria-label","Spelling suggestions for "+word);
    const add=(label,fn)=>{
      const b=document.createElement("button");
      b.type="button";b.setAttribute("role","menuitem");b.textContent=label;
      b.addEventListener("pointerdown",e=>e.preventDefault());
      b.addEventListener("click",e=>{e.preventDefault();fn();});
      pane.append(b);
    };
    for(const suggestion of suggestions) add(suggestion,()=>replace(suggestion));
    if(suggestions.length){
      const divider=document.createElement("div");divider.className="elfshell-spell-separator";pane.append(divider);
    }
    add("Ignore",()=>{ignored.add(word);closeMenu();schedule();});
    add("Add to Dictionary",async()=>{
      closeMenu();
      const response=await request("add",{word}).catch(()=>null);
      if(response?.ok)schedule();else console.warn("ELF//SHELL: could not add spelling word");
    });
    document.documentElement.append(pane);
    const rect=pane.getBoundingClientRect();
    pane.style.left=Math.max(5,Math.min(evt.clientX,innerWidth-rect.width-5))+"px";
    pane.style.top=Math.max(5,Math.min(evt.clientY+9,innerHeight-rect.height-5))+"px";
    menu=pane;
    pane.addEventListener("keydown",e=>{
      const items=[...pane.querySelectorAll("button")],idx=items.indexOf(document.activeElement);
      if(e.key==="Escape"){e.preventDefault();closeMenu();editor?.focus();}
      if(e.key==="ArrowDown"||e.key==="ArrowUp"){
        e.preventDefault();items[(idx+items.length+(e.key==="ArrowDown"?1:-1))%items.length].focus();
      }
    });
  }
  async function onClick(event){
    if(!enabled)return;
    if(menu&&menu.contains(event.target))return;
    closeMenu();
    if(!editor||!editor.contains(event.target)||editor.getAttribute("spellcheck")!=="false")return;
    const hit=clickedToken(event);
    if(!hit)return;
    try{
      const response=await request("suggest",{word:hit.word});
      if(!response?.ok||!enabled||editor?.getAttribute("spellcheck")!=="false")return;
      const options=(response.suggestions||[]).filter(w=>typeof w==="string"&&w!==hit.word).slice(0,6);
      placeMenu(event,hit.word,hit.range,options);
    }catch(error){console.warn("ELF//SHELL suggestion unavailable",error);}
  }
  function disable(){enabled=false;restore();}
  function enable(){enabled=true;selectEditor(closestEditor(document.activeElement));}
  globalThis.__elfshellSpelling={disable,enable};
  document.addEventListener("focusin",e=>selectEditor(closestEditor(e.target)),true);
  document.addEventListener("click",onClick,true);
  document.addEventListener("input",e=>{if(editor?.contains(e.target))schedule();},true);
  document.addEventListener("compositionstart",()=>{composing=true;},true);
  document.addEventListener("compositionend",()=>{composing=false;schedule();},true);
  document.addEventListener("keydown",e=>{if(e.key==="Escape")closeMenu();},true);
  document.addEventListener("scroll",()=>closeMenu(),true);
  browser.runtime.onMessage.addListener(msg=>{
    if(msg?.type==="elfshell:spell:disable")disable();
  });
  enable();
})();