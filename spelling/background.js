"use strict";
// Isolated spelling service: words and suggestions remain inside Firefox.
const SPELL_WORDS_KEY="elfshell:spelling:personal-words:v1";
let spellWorker=null, spellInit=null, spellCounter=0;
const spellPending=new Map();
function spellReset(error){
  if(spellWorker)spellWorker.terminate();
  spellWorker=null;spellInit=null;
  for(const p of spellPending.values()){clearTimeout(p.timer);p.reject(error);}
  spellPending.clear();
}
function spellCall(type,data={},timeout=10000){
  if(!spellWorker)return Promise.reject(Error("Spell worker unavailable"));
  const id=++spellCounter;
  return new Promise((resolve,reject)=>{
    const timer=setTimeout(()=>{spellReset(Error("Spell request timed out"));reject(Error("Spell request timed out"));},timeout);
    spellPending.set(id,{resolve,reject,timer});
    try{spellWorker.postMessage({id,type,...data});}catch(e){clearTimeout(timer);spellPending.delete(id);reject(e);}
  });
}
async function spellReady(){
  if(!spellInit){
    spellInit=(async()=>{
      spellWorker=new Worker(browser.runtime.getURL("spelling/worker.js"));
      spellWorker.onmessage=event=>{
        const p=spellPending.get(event.data?.id);
        if(!p)return;
        clearTimeout(p.timer);spellPending.delete(event.data.id);
        if(event.data.ok)p.resolve(event.data);else p.reject(Error(event.data.error||"Spell request failed"));
      };
      spellWorker.onerror=event=>spellReset(Error(event.message||"Spell worker error"));
      const data=await browser.storage.local.get(SPELL_WORDS_KEY);
      const added=Array.isArray(data[SPELL_WORDS_KEY])?data[SPELL_WORDS_KEY]:[];
      await spellCall("init",{aff:browser.runtime.getURL("spelling/en.aff"),dic:browser.runtime.getURL("spelling/en.dic"),added},30000);
    })().catch(e=>{spellReset(e);throw e;});
  }
  await spellInit;
}
browser.runtime.onMessage.addListener(message=>{
  if(!message||typeof message.type!=="string"||!message.type.startsWith("elfshell:spelling:"))return undefined;
  return (async()=>{
    try{
      await spellReady();
      if(message.type==="elfshell:spelling:check"){
        const words=Array.isArray(message.words)?message.words.filter(w=>typeof w==="string"&&/^[A-Za-z][A-Za-z'’\-]*$/.test(w)).slice(0,500):[];
        const out=await spellCall("check",{words});return {ok:true,incorrect:out.incorrect};
      }
      if(message.type==="elfshell:spelling:suggest"){
        const word=String(message.word||"");
        if(!/^[A-Za-z][A-Za-z'’\-]{1,78}$/.test(word))return {ok:false,error:"Invalid word"};
        const out=await spellCall("suggest",{word});return {ok:true,suggestions:out.suggestions};
      }
      if(message.type==="elfshell:spelling:add"){
        const word=String(message.word||"").trim();
        if(!/^[A-Za-z][A-Za-z'’\-]{1,78}$/.test(word))return {ok:false,error:"Invalid word"};
        const existing=await browser.storage.local.get(SPELL_WORDS_KEY);
        const list=Array.isArray(existing[SPELL_WORDS_KEY])?existing[SPELL_WORDS_KEY].filter(w=>typeof w==="string"):[];
        if(!list.includes(word)){
          if(list.length>=2000)return {ok:false,error:"Personal word list limit reached"};
          await browser.storage.local.set({[SPELL_WORDS_KEY]:[...list,word]});
        }
        await spellCall("add",{word});return {ok:true};
      }
      return {ok:false,error:"Unknown spelling request"};
    }catch(e){return {ok:false,error:String(e.message||e)};}
  })();
});