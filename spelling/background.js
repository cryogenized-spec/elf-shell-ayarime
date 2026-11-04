"use strict";
// Isolated spelling service: words and suggestions remain inside Firefox.
const SPELL_WORDS_KEY="elfshell:spelling:personal-words:v1";
let spellWorker=null, spellInit=null, spellCounter=0;
const spellPending=new Map();
let spellWordChain=Promise.resolve();
// Content-script messages are accepted only from an actively enabled site.
// Having the same origin's host permission for RSS is not spelling opt-in.
const spellingSiteId=origin=>"elfspell-"+[...origin].map(ch=>ch.charCodeAt(0).toString(16).padStart(2,"0")).join("");
async function spellingSenderAllowed(sender){
  if(!sender?.tab?.id||!sender.url||sender.frameId!==0)return false;
  let url,tabUrl;
  try{url=new URL(sender.url);tabUrl=new URL(sender.tab.url||sender.url);}
  catch{return false;}
  if(url.protocol!=="https:"||url.origin!==tabUrl.origin)return false;
  const origin=url.origin+"/*";
  const [permission,registered]=await Promise.all([
    browser.permissions.contains({origins:[origin]}),
    browser.scripting.getRegisteredContentScripts()
  ]);
  return !!permission && registered.some(item=>item.id===spellingSiteId(url.origin)&&
    Array.isArray(item.matches)&&item.matches.includes(origin));
}
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
browser.runtime.onMessage.addListener((message,sender)=>{
  if(!message||typeof message.type!=="string"||!message.type.startsWith("elfshell:spelling:"))return undefined;
  return (async()=>{
    try{
      if(!await spellingSenderAllowed(sender))return {ok:false,error:"Spelling is disabled or site permission has been revoked"};
      if(message.type==="elfshell:spelling:authorize")return {ok:true};
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
        // Browser storage does not provide atomic array append. Serialize
        // the entire read/write so simultaneous tabs cannot lose each
        // other's acknowledged dictionary additions.
        const mutation=spellWordChain.then(async()=>{
          const existing=await browser.storage.local.get(SPELL_WORDS_KEY);
          const list=Array.isArray(existing[SPELL_WORDS_KEY])?existing[SPELL_WORDS_KEY].filter(w=>typeof w==="string"):[];
          if(!list.includes(word)){
            if(list.length>=2000)return {ok:false,error:"Personal word list limit reached"};
            await browser.storage.local.set({[SPELL_WORDS_KEY]:[...list,word]});
          }
          await spellCall("add",{word});
          return {ok:true};
        });
        spellWordChain=mutation.then(()=>undefined,()=>undefined);
        return await mutation;
      }
      return {ok:false,error:"Unknown spelling request"};
    }catch(e){return {ok:false,error:String(e.message||e)};}
  })();
});

 // Revoked host access must stop currently injected scripts, not only
 // prevent future registrations. Every spelling message also checks access.
 browser.permissions.onRemoved.addListener(async permissions=>{
   for(const pattern of permissions.origins||[]){
     if(!pattern.startsWith("https://")||!pattern.endsWith("/*"))continue;
     const origin=pattern.slice(0,-2);
     const id=spellingSiteId(origin);
     try{
       const registered=await browser.scripting.getRegisteredContentScripts();
       if(registered.some(entry=>entry.id===id))
         await browser.scripting.unregisterContentScripts({ids:[id]});
     }catch(error){console.warn("ELF//SHELL: cannot unregister revoked spelling script",error);}
   }
   // Query by tab ID without reading tab URLs; this works even when the
   // revoked origin no longer allows us to inspect addresses.
   try{
     const tabs=await browser.tabs.query({});
     await Promise.all(tabs.map(tab=>
       browser.tabs.sendMessage(tab.id,{type:"elfshell:spell:revalidate"}).catch(()=>undefined)
     ));
   }catch(error){console.warn("ELF//SHELL: cannot notify every spelling tab",error);}
 });
