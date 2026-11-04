"use strict";
// Offline, bundled Hunspell-compatible engine. No network calls.
importScripts("nspell-bundle.js");
let engine=null;
self.onmessage=async event=>{
  const {id,type,words=[],word="",added=[]}=event.data||{};
  try{
    if(type==="init"){
      if(!engine){
        const [aff,dic]=await Promise.all([fetch(event.data.aff).then(r=>{if(!r.ok)throw Error("aff unavailable");return r.text()}),fetch(event.data.dic).then(r=>{if(!r.ok)throw Error("dictionary unavailable");return r.text()})]);
        engine=nspell({aff,dic});
      }
      for(const w of added)if(typeof w==="string"&&w.length<80)engine.add(w);
      self.postMessage({id,ok:true});return;
    }
    if(!engine)throw Error("Dictionary not ready");
    if(type==="check"){
      const incorrect=words.filter(w=>typeof w==="string"&&w.length>2&&w.length<80&&!engine.correct(w));
      self.postMessage({id,ok:true,incorrect});return;
    }
    if(type==="suggest"){
      self.postMessage({id,ok:true,suggestions:engine.suggest(word).slice(0,6)});return;
    }
    if(type==="add"){
      engine.add(word);
      self.postMessage({id,ok:true});return;
    }
    throw Error("Unknown request");
  }catch(e){self.postMessage({id,ok:false,error:String(e?.message||e)});}
};