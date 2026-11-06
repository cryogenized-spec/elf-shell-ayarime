"use strict";
/* ELF//SHELL optional spelling UI. Custom highlights on compatible contenteditables;
   left-click suggestions on ordinary text fields use Firefox native squiggles and Undo. */
(() => {
  if(globalThis.__elfshellSpelling){
    // Reuse an injected instance only after a fresh background authorization.
    globalThis.__elfshellSpelling.reauthorize();
    return;
  }
  const MARK="elfshell-spelling-errors-v1";
  const ignored=new Set();
  let enabled=false, editor=null, originalSpell=null, revision=0, composing=false, timer=0;
  let mistakes=new Set(), menu=null, menuRange=null, menuWord="";
  let menuField=null,menuFieldStart=0,menuFieldEnd=0,menuFieldValue="",menuFieldCaret=null,fieldRequest=0;
  let focusMenuFirst=null;
  const WORD=/[A-Za-z]+(?:['’\-][A-Za-z]+)*/g;
  const request=(type,extra={})=>browser.runtime.sendMessage({type:"elfshell:spelling:"+type,...extra});
  const asElement=n=>n instanceof Element?n:n?.parentElement;
  function closestEditor(n){
    const el=asElement(n);
    return el?.closest?.('[contenteditable="true"],[contenteditable="plaintext-only"]')||null;
  }
  function spellcheckDisabled(node){
    // HTML's spellcheck attribute is inherited. A child's explicit true
    // overrides an ancestor false; values are case-insensitive.
    for(let el=node;el&&el.nodeType===Node.ELEMENT_NODE;el=el.parentElement){
      const attr=el.getAttribute("spellcheck");
      if(attr===null)continue;
      const value=attr.trim().toLowerCase();
      if(value==="false")return true;
      if(value==="true")return false;
    }
    return false;
  }
  function nativeField(target){
    // Standard controls retain Firefox's own underlines. Never read or
    // interact with password, code, private, disabled or readonly controls.
    const el=asElement(target);
    const field=el?.closest?.("textarea,input")||null;
    if(!field||!field.isConnected||field.disabled||field.readOnly)return null;
    // HTML <input> without a type attribute defaults to "text".
    if(field.tagName==="INPUT"&&!["text","search"].includes(field.type))return null;
    if(spellcheckDisabled(field))return null;
    if(field.closest("code,pre,[role='code'],[data-elfshell-spelling-off],"+
      "[data-private],[data-sensitive],.CodeMirror,.cm-editor,.monaco-editor,.ace_editor"))return null;
    const detail=[field.name,field.id,field.getAttribute("autocomplete"),field.getAttribute("aria-label")]
      .filter(Boolean).join(" ").toLowerCase();
    if(/password|passphrase|secret|token|otp|one.time.code|verification.code|api.key|credit.card|card.number/.test(detail))
      return null;
    return field;
  }
  function clickedFieldWord(field){
    // A single collapsed caret inside a word demonstrates a genuine click
    // on that token. Clicking empty space (caret at token boundary) does not.
    const start=field.selectionStart,end=field.selectionEnd;
    if(start===null||end===null||start!==end)return null;
    for(const match of field.value.matchAll(WORD)){
      const first=match.index,last=first+match[0].length;
      if(start>first&&start<last&&match[0].length>=3&&match[0].length<=78)
        return {field,word:match[0],start:first,end:last,value:field.value,caret:start};
    }
    return null;
  }
  function canManage(root){
    if(!root||!root.isConnected||root.closest('code,pre,[role="code"],[data-elfshell-spelling-off]'))return false;
    if(root.getAttribute("spellcheck")==="false")return false;
    // Firefox 142-148 exposed parts of the Highlight API without painting
    // ::highlight text decorations. Keep native spellcheck on those versions.
    return !!(globalThis.CSS?.highlights&&globalThis.Highlight&&
      globalThis.CSS?.supports?.("selector(::highlight(elfshell-spelling-errors-v1))")&&
      document.caretPositionFromPoint);
  }
  function closeMenu(){
    if(menu){menu.remove();menu=null;}
    menuRange=null;menuWord="";
    menuField=null;menuFieldStart=0;menuFieldEnd=0;menuFieldValue="";
    menuFieldCaret=null;focusMenuFirst=null;
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
    const result=[];let chars=0,complete=true;
    while(walker.nextNode()){
      const node=walker.currentNode,parent=node.parentElement;
      if(!parent||parent.closest('code,pre,[contenteditable="false"],[data-elfshell-spelling-off]'))continue;
      // Full editor coverage is required before disabling Firefox's native
      // checker. An incomplete prefix is not a safe replacement.
      if(chars+node.data.length>4500){complete=false;break;}
      chars+=node.data.length;
      for(const match of node.data.matchAll(WORD)){
        if(match[0].length<3||match[0].length>78)continue;
        if(result.length>=350){complete=false;break;}
        const range=document.createRange();
        range.setStart(node,match.index);range.setEnd(node,match.index+match[0].length);
        result.push({word:match[0],range});
      }
      if(!complete)break;
    }
    return {found:result,complete};
  }
  async function refresh(){
    const root=editor;
    if(!enabled||!root||composing)return;
    const thisRevision=++revision;
    const scan=tokens(root);
    if(!scan.complete){
      // Restore native checking for ALL words when our bounded scan cannot
      // cover the entire editor. Re-evaluate after subsequent edits.
      clearMark();
      if(originalSpell===null)root.removeAttribute("spellcheck");
      else root.setAttribute("spellcheck",originalSpell);
      return;
    }
    const found=scan.found;
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
    if(menuField){
      const field=menuField,start=menuFieldStart,end=menuFieldEnd;
      const original=menuFieldValue,word=menuWord,caret=menuFieldCaret;
      // The text AND collapsed selection must still be at the original click.
      // Never silently replace a word after the user moved the caret.
      if(!field.isConnected||field.disabled||field.readOnly||
         field.value!==original||field.value.slice(start,end)!==word||
         field.selectionStart!==caret||field.selectionEnd!==caret)
        return closeMenu();
      closeMenu();
      try{
        field.focus();
        field.setSelectionRange(start,end);
        // Firefox's native editor command preserves Undo and input events.
        // Never overwrite React's managed value or fall back to setRangeText.
        if(!document.execCommand("insertText",false,choice))
          console.warn("ELF//SHELL: this field rejected correction; native spelling remains.");
      }catch(error){console.warn("ELF//SHELL text control correction unavailable",error);}
      return;
    }
    if(!editor||!menuRange||!menuRange.startContainer.isConnected||
       !editor.contains(menuRange.startContainer)||menuRange.toString()!==menuWord)
      return closeMenu();
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
  function placeMenu(evt,word,range,suggestions,fieldHit=null){
    closeMenu();menuWord=word;menuRange=range;
    if(fieldHit){
      menuField=fieldHit.field;menuFieldStart=fieldHit.start;
      menuFieldEnd=fieldHit.end;menuFieldValue=fieldHit.value;
      menuFieldCaret=fieldHit.caret;
    }
    const pane=document.createElement("div");
    pane.className="elfshell-spell-menu";
    pane.setAttribute("role","menu");
    pane.setAttribute("aria-label","Spelling suggestions for "+word);
    // Closed shadow root prevents page scripts from reaching extension menu
    // buttons. No untrusted DOM click can authorize dictionary changes.
    const shadow=pane.attachShadow({mode:"closed"});
    const style=document.createElement("style");
    style.textContent=':host{position:fixed;z-index:2147483647;display:block;padding:5px;min-width:180px;max-width:285px;border:1px solid #64656d;border-radius:7px;background:#303136;color:#f2f2f3;box-shadow:0 6px 20px #0005;font:13px/1.35 system-ui,sans-serif;color-scheme:dark}button{display:block;width:100%;border:0;border-radius:4px;padding:7px 12px;background:transparent;color:inherit;text-align:left;font:inherit;cursor:default}button:hover,button:focus-visible{outline:none;background:#53545c}.elfshell-spell-separator{border-top:1px solid #55565b;margin:4px 5px}@media(prefers-color-scheme:light){:host{background:#f8f8f9;color:#161719;border-color:#c7c8ce;color-scheme:light}button:hover,button:focus-visible{background:#e5e6eb}.elfshell-spell-separator{border-color:#dddee2}}';
    shadow.append(style);
    const add=(label,fn)=>{
      const b=document.createElement("button");
      b.type="button";b.setAttribute("role","menuitem");b.textContent=label;
      b.addEventListener("pointerdown",e=>e.preventDefault());
      b.addEventListener("click",e=>{
        if(!e.isTrusted)return;
        e.preventDefault();fn();
      });
      shadow.append(b);
    };
    for(const suggestion of suggestions) add(suggestion,()=>replace(suggestion));
    if(suggestions.length){
      const divider=document.createElement("div");divider.className="elfshell-spell-separator";shadow.append(divider);
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
    // A menu appended after the editor is not always next in tab order.
    // Let the user's keyboard focus enter its real buttons deliberately.
    focusMenuFirst=()=>shadow.querySelector("button")?.focus();
    pane.addEventListener("keydown",e=>{
      const items=[...shadow.querySelectorAll("button")],idx=items.indexOf(shadow.activeElement);
      if(e.key==="Escape"){
        e.preventDefault();const target=menuField||editor;closeMenu();target?.focus();
      }
      if(e.key==="ArrowDown"||e.key==="ArrowUp"){
        e.preventDefault();items[(idx+items.length+(e.key==="ArrowDown"?1:-1))%items.length].focus();
      }
    });
  }
  async function onClick(event){
    if(!enabled||!event.isTrusted||event.button!==0||composing||
       event.ctrlKey||event.altKey||event.metaKey||event.shiftKey)return;
    if(menu&&menu.contains(event.target))return;
    const requestId=++fieldRequest;
    closeMenu();
    const field=nativeField(event.target);
    if(field){
      // Standard inputs/textarea use the already-visible native squiggles.
      // Firefox doesn't expose their mistake list to WebExtensions; verify
      // the exact clicked word locally instead of hijacking its context menu.
      const hit=clickedFieldWord(field);
      if(!hit||ignored.has(hit.word))return;
      const stillValid=()=>enabled&&requestId===fieldRequest&&
        field.isConnected&&document.activeElement===field&&
        field.value===hit.value&&field.selectionStart===hit.caret&&
        field.selectionEnd===hit.caret;
      try{
        const result=await request("check",{words:[hit.word]});
        if(!result?.ok||!Array.isArray(result.incorrect)||
           !result.incorrect.includes(hit.word)||!stillValid())return;
        const response=await request("suggest",{word:hit.word});
        if(!response?.ok||!stillValid())return;
        const options=(response.suggestions||[])
          .filter(w=>typeof w==="string"&&w!==hit.word).slice(0,6);
        placeMenu(event,hit.word,null,options,hit);
      }catch(error){console.warn("ELF//SHELL field spelling unavailable; using Firefox spelling.",error);}
      return;
    }
    if(!editor||!editor.contains(event.target)||editor.getAttribute("spellcheck")!=="false")return;
    const hit=clickedToken(event);
    if(!hit)return;
    const targetEditor=editor,targetRevision=revision;
    try{
      const response=await request("suggest",{word:hit.word});
      if(!response?.ok||!enabled||editor!==targetEditor||revision!==targetRevision||
         editor?.getAttribute("spellcheck")!=="false")return;
      const options=(response.suggestions||[]).filter(w=>typeof w==="string"&&w!==hit.word).slice(0,6);
      placeMenu(event,hit.word,hit.range,options);
    }catch(error){console.warn("ELF//SHELL suggestion unavailable",error);}
  }
  function disable(){enabled=false;++fieldRequest;restore();}
  function enable(){enabled=true;selectEditor(closestEditor(document.activeElement));}
  async function reauthorize(){
    // A tab ID and a previously injected script do not confer continued
    // permission. Background independently checks the exact sender origin,
    // site registration and current host permission before enabling.
    const result=await request("authorize").catch(()=>null);
    if(!result?.ok){disable();return;}
    if(!enabled)enable();
  }
  globalThis.__elfshellSpelling={disable,reauthorize};
  document.addEventListener("focusin",e=>{if(!menu?.contains(e.target))selectEditor(closestEditor(e.target));},true);
  document.addEventListener("click",onClick,true);
  document.addEventListener("beforeinput",e=>{
    if(nativeField(e.target)){++fieldRequest;closeMenu();}
    if(editor?.contains(e.target)){closeMenu();++revision;}
  },true);
  document.addEventListener("input",e=>{
    if(nativeField(e.target)){++fieldRequest;closeMenu();}
    if(editor?.contains(e.target)){closeMenu();++revision;schedule();}
  },true);
  document.addEventListener("compositionstart",()=>{composing=true;++fieldRequest;closeMenu();++revision;},true);
  document.addEventListener("compositionend",()=>{composing=false;++fieldRequest;closeMenu();++revision;schedule();},true);
  document.addEventListener("keydown",e=>{
    if(e.key==="Escape"){
      ++fieldRequest;
      const target=menuField||editor;
      const focusedMenu=!!menu && (document.activeElement===menu||
        menu.contains(document.activeElement));
      closeMenu();
      if(focusedMenu&&target?.isConnected)target.focus({preventScroll:true});
      return;
    }
    if(menu&&focusMenuFirst&&
       (document.activeElement===menuField||document.activeElement===editor)&&
       (e.key==="Tab"||e.key==="ArrowDown")){
      e.preventDefault();focusMenuFirst();return;
    }
    if(menuField&&document.activeElement===menuField&&
       ["ArrowLeft","ArrowRight","Home","End","PageUp","PageDown"].includes(e.key)){
      ++fieldRequest;closeMenu();
    }
  },true);
  document.addEventListener("scroll",()=>{++fieldRequest;closeMenu();},true);
  document.addEventListener("selectionchange",()=>{
    if(menuField&&(menuField.selectionStart!==menuFieldCaret||
                   menuField.selectionEnd!==menuFieldCaret)){
      ++fieldRequest;closeMenu();
    }
  },true);
  document.addEventListener("focusin",e=>{
    if(menuField&&e.target!==menuField&&!menu?.contains(e.target)){
      ++fieldRequest;closeMenu();
    }
  },true);
  browser.runtime.onMessage.addListener(msg=>{
    if(msg?.type==="elfshell:spell:disable")disable();
    if(msg?.type==="elfshell:spell:revalidate")reauthorize();
  });
  reauthorize();
})();