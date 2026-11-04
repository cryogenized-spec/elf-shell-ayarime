"use strict";
/* AYARIME // MEMORY TRACE
   Original bilingual dialogue. Local-only; no telemetry, network feeds, or new permissions.
   The quote library is a packaged JSON asset. Rotation uses a shared time anchor
   so newly opened tabs do not restart the same quotation. */
(() => {
  const $ = id => document.getElementById(id);
  const key = "elfshell-memory-v1";
  const intervals = [0, 30, 90, 180, 300];
  const languages = ["both", "jp", "en"];
  const hasStorage = typeof browser !== "undefined" && !!browser.storage?.local;
  let quotes = [];
  let categories = [];
  let prefs = null;
  let presentedId = null;
  let detailId = null;
  let hovering = false;
  let heldId = null;
  let currentlySaving = false;

  const defaultPrefs = () => ({language:"both",interval:90,paused:false,baseId:"AYR-0001",anchor:Date.now(),pinnedId:null,favourites:[],favouritesOnly:false,categories:[]});
  const findQuote = id => quotes.find(x => x.id === id);
  const available = () => {
    const choices = quotes.filter(x => (!prefs.categories.length || prefs.categories.includes(x.category)) && (!prefs.favouritesOnly || prefs.favourites.includes(x.id)));
    return choices.length ? choices : quotes;
  };
  function validate(value) {
    if (!value || typeof value !== "object" || Array.isArray(value)) return null;
    const ids = new Set(quotes.map(x=>x.id));
    const safeCats = new Set(categories);
    return {
      language:languages.includes(value.language)?value.language:"both",
      interval:intervals.includes(value.interval)?value.interval:90,
      paused:value.paused===true,
      baseId:ids.has(value.baseId)?value.baseId:quotes[0].id,
      anchor:Number.isSafeInteger(value.anchor) && value.anchor>0 && value.anchor<=Date.now()+60000?value.anchor:Date.now(),
      pinnedId:ids.has(value.pinnedId)?value.pinnedId:null,
      favourites:Array.isArray(value.favourites)?[...new Set(value.favourites.filter(x=>ids.has(x)))].slice(0,quotes.length):[],
      favouritesOnly:value.favouritesOnly===true && Array.isArray(value.favourites) && value.favourites.some(x=>ids.has(x)),
      categories:Array.isArray(value.categories)?[...new Set(value.categories.filter(x=>safeCats.has(x)))].slice(0,categories.length):[]
    };
  }
  function activeQuote() {
    if (prefs.pinnedId) return findQuote(prefs.pinnedId)||quotes[0];
    const pool=available();
    const base=Math.max(0,pool.findIndex(x=>x.id===prefs.baseId));
    const elapsed=prefs.paused||!prefs.interval?0:Math.max(0,Math.floor((Date.now()-prefs.anchor)/(prefs.interval*1000)));
    return pool[(base+elapsed)%pool.length];
  }
  function setLanguage(root,mode){root.classList.toggle("memory-jp-only",mode==="jp");root.classList.toggle("memory-en-only",mode==="en");}
  function showPanel() {
    if(!prefs||!quotes.length)return;
    const next=findQuote(hovering?heldId:null)||activeQuote();
    if(!next||next.id===presentedId)return;
    presentedId=next.id;
    $("memory-compact-jp").textContent=next.shortJp;
    $("memory-compact-en").textContent=next.shortEn;
    $("memory-fragment-id").textContent=next.id;
    $("memory-category").textContent=next.category;
    $("memory-counter").textContent=String(quotes.findIndex(x=>x.id===next.id)+1).padStart(2,"0")+" / "+quotes.length;
    $("memory-open").title="Open full fragment " + next.id;
    setLanguage($("memory-panel"),prefs.language);
    $("memory-pause").textContent=prefs.paused?"▶":"Ⅱ";
    $("memory-pause").setAttribute("aria-label",prefs.paused?"Resume memory rotation":"Pause memory rotation");
    $("memory-panel").classList.toggle("memory-pinned",!!prefs.pinnedId);
  }
  function showDetail() {
    if(!prefs||!quotes.length)return;
    const q=findQuote(detailId)||activeQuote();
    detailId=q.id;
    $("memory-detail-id").textContent=q.id;
    $("memory-detail-category").textContent=q.category;
    $("memory-detail-jp").textContent=q.jp;
    $("memory-detail-en").textContent=q.en;
    $("memory-detail-language").value=prefs.language;
    $("memory-detail-interval").value=String(prefs.interval);
    $("memory-detail-favourite").textContent=prefs.favourites.includes(q.id)?"★ FAVOURITED":"☆ FAVOURITE";
    $("memory-detail-favourite").setAttribute("aria-pressed",String(prefs.favourites.includes(q.id)));
    $("memory-detail-pin").textContent=prefs.pinnedId===q.id?"UNPIN FRAGMENT":"PIN FRAGMENT";
    $("memory-detail-pin").setAttribute("aria-pressed",String(prefs.pinnedId===q.id));
    $("memory-view-favourites").setAttribute("aria-pressed",String(prefs.favouritesOnly));
    $("memory-view-favourites").textContent=prefs.favouritesOnly?"★ SHOW ALL FRAGMENTS":"★ FAVOURITES ONLY";
    setLanguage($("memory-dialog"),prefs.language);
    for(const c of $("memory-categories").querySelectorAll("input[data-memory-category]"))c.checked=!prefs.categories.length||prefs.categories.includes(c.value);
  }
  function render(force=false) {
    if(force)presentedId=null;
    showPanel();
    if($("memory-dialog").open&&force)showDetail();
  }
  async function save(){
    if(!prefs)return;
    currentlySaving=true;
    try {
      if(hasStorage) await browser.storage.local.set({[key]:prefs});
      else localStorage.setItem(key,JSON.stringify(prefs));
    }catch(error){console.error("AYARIME memory save failed",error);$("memory-message").textContent="Unable to save Memory Trace preferences.";}
    finally{currentlySaving=false;}
  }
  async function step(amount,fromDetail=false){
    const pool=available();
    const current=findQuote(fromDetail?detailId:presentedId)||activeQuote();
    let index=pool.findIndex(x=>x.id===current.id);if(index<0)index=0;
    const next=pool[(index+amount+pool.length)%pool.length];
    prefs.baseId=next.id;prefs.anchor=Date.now();prefs.pinnedId=null;
    presentedId=null;hovering=false;heldId=null;
    if(fromDetail)detailId=next.id;
    await save();render(true);
  }
  function openDetail(){detailId=presentedId||activeQuote().id;showDetail();$("memory-dialog").showModal();}
  function paintCategories(){
    const root=$("memory-categories");root.replaceChildren();
    for(const category of categories){
      const label=document.createElement("label");label.className="memory-category-choice";
      const input=document.createElement("input");input.type="checkbox";input.value=category;input.dataset.memoryCategory="true";
      const span=document.createElement("span");span.textContent=category;
      label.append(input,span);root.append(label);
      input.addEventListener("change",async()=>{
        const selected=[...root.querySelectorAll("input:checked")].map(x=>x.value);
        if(!selected.length){input.checked=true;$("memory-message").textContent="Keep at least one category selected.";return;}
        prefs.categories=selected.length===categories.length?[]:selected;
        prefs.baseId=available()[0].id;prefs.anchor=Date.now();prefs.pinnedId=null;detailId=prefs.baseId;
        await save();render(true);
        $("memory-message").textContent="Memory categories updated.";
      });
    }
  }
  function ensureValidQuotes(value){
    if(!Array.isArray(value)||value.length<1||value.length>100)return false;
    const seen=new Set();
    for(const q of value){
      if(!q||!/^AYR-\d{4}$/.test(q.id)||seen.has(q.id)||typeof q.category!=="string"||!q.category||typeof q.jp!=="string"||!q.jp||typeof q.en!=="string"||!q.en||typeof q.shortJp!=="string"||typeof q.shortEn!=="string")return false;
      seen.add(q.id);
    }
    return true;
  }
  async function init(){
    try{
      // Relative URL points to a packaged read-only extension resource, never an external URL.
      const response=await fetch("assets/ayarime-quotes.json",{cache:"no-store"});
      if(!response.ok)throw Error("Memory archive asset missing");
      const loaded=await response.json();
      if(!ensureValidQuotes(loaded))throw Error("Memory archive format invalid");
      quotes=loaded;categories=[...new Set(quotes.map(x=>x.category))].sort();
      paintCategories();
      let raw=null;
      try{raw=hasStorage?(await browser.storage.local.get(key))[key]:JSON.parse(localStorage.getItem(key)||"null");}catch(e){console.warn("AYARIME memory preferences not readable",e);}
      prefs=validate(raw)||defaultPrefs();
      if(!raw)await save();
      render(true);
      setInterval(()=>{if(!hovering&&!$("memory-dialog").open)render();},2500);
      if(hasStorage&&browser.storage.onChanged){browser.storage.onChanged.addListener((changes,area)=>{
        if(area==="local"&&changes[key]&&!currentlySaving){const updated=validate(changes[key].newValue);if(updated){prefs=updated;render(true);}}
      });}
    }catch(error){console.error(error);$("memory-compact-en").textContent="Memory archive unavailable.";$("memory-compact-jp").textContent="記憶領域 / 読込失敗";$("memory-message").textContent="The local memory archive could not be loaded.";}
  }
  $("memory-prev").addEventListener("click",()=>step(-1));
  $("memory-next").addEventListener("click",()=>step(1));
  $("memory-pause").addEventListener("click",async()=>{
    if(!prefs)return;
    if(!prefs.paused){prefs.baseId=(findQuote(presentedId)||activeQuote()).id;prefs.anchor=Date.now();prefs.paused=true;}
    else{prefs.anchor=Date.now();prefs.paused=false;}
    await save();render(true);
  });
  $("memory-open").addEventListener("click",openDetail);
  $("memory-panel").addEventListener("mouseenter",()=>{if(!prefs)return;heldId=(findQuote(presentedId)||activeQuote()).id;hovering=true;});
  $("memory-panel").addEventListener("mouseleave",()=>{hovering=false;heldId=null;render(true);});
  $("memory-detail-prev").addEventListener("click",()=>step(-1,true));
  $("memory-detail-next").addEventListener("click",()=>step(1,true));
  $("memory-detail-close").addEventListener("click",()=>$("memory-dialog").close());
  $("memory-detail-language").addEventListener("change",async e=>{prefs.language=e.target.value;await save();render(true);});
  $("memory-detail-interval").addEventListener("change",async e=>{
    const current=activeQuote();prefs.interval=Number(e.target.value);prefs.baseId=current.id;prefs.anchor=Date.now();
    await save();render(true);
  });
  $("memory-detail-favourite").addEventListener("click",async()=>{
    const id=detailId;
    prefs.favourites=prefs.favourites.includes(id)?prefs.favourites.filter(x=>x!==id):[...prefs.favourites,id];
    if(!prefs.favourites.length)prefs.favouritesOnly=false;
    await save();showDetail();
  });
  $("memory-view-favourites").addEventListener("click",async()=>{
    if(!prefs.favouritesOnly && !prefs.favourites.length){$("memory-message").textContent="Mark at least one fragment as a favourite first.";return;}
    prefs.favouritesOnly=!prefs.favouritesOnly;
    prefs.baseId=available()[0].id;prefs.anchor=Date.now();prefs.pinnedId=null;
    detailId=prefs.baseId;
    await save();render(true);
    $("memory-message").textContent=prefs.favouritesOnly?"Showing favourite fragments only.":"Showing all enabled categories.";
  });
  $("memory-detail-pin").addEventListener("click",async()=>{
    prefs.pinnedId=prefs.pinnedId===detailId?null:detailId;
    prefs.baseId=detailId;prefs.anchor=Date.now();
    await save();render(true);
  });
  // Exposed only to the local settings export/import handler; no global access to browsing data.
  window.elfMemory={
    snapshot:()=>prefs?JSON.parse(JSON.stringify(prefs)):null,
    validateSnapshot:input=>quotes.length?validate(input):null,
    applySnapshot:async input=>{const validated=validate(input);if(!validated)throw Error("Invalid memory archive preferences");prefs=validated;await save();render(true);}
  };
  init();
})();
