"use strict";
const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),vm=require("node:vm"),path=require("node:path");
const script=fs.readFileSync(path.join(__dirname,"../unified-preview/module.js"),"utf8");
function harness(){
  const nodes=new Map();
  for(const id of ["ai-module-toggle","ai-module-status","ask-ayarime-toggle"])
    nodes.set(id,{id,disabled:false,textContent:"",title:"",attributes:{},
      setAttribute(name,value){this.attributes[name]=value;},
      addEventListener(name,cb){this[name]=cb;}});
  let onLoad,onChanged,hasKey=false,value=false,fail=false;
  let clearFails=false,clearCalls=0;
  const browser={runtime:{sendMessage:async message=>{
    assert.equal(message.type,"AI_CLEAR_SESSION_KEY");
    clearCalls++;
    if(clearFails)return {ok:false};
    return {ok:true,ai:{hasSessionKey:false}};
  }},storage:{
    local:{
      get:async()=>hasKey?{"elfshell.unified.aiEnabled.v1":value}:{},
      set:async obj=>{
        if(fail)throw Error("Synthetic storage quota failure");
        value=obj["elfshell.unified.aiEnabled.v1"];hasKey=true;
        onChanged?.({"elfshell.unified.aiEnabled.v1":{newValue:value}},"local");
      }
    },
    onChanged:{addListener:fn=>{onChanged=fn;}}
  }};
  const ctx={browser,document:{
    getElementById:id=>nodes.get(id)||null,
    addEventListener:(name,cb)=>{if(name==="DOMContentLoaded")onLoad=cb;}
  },window:{}};
  vm.createContext(ctx);vm.runInContext(script,ctx);
  return {ctx,nodes,load:async()=>{
    onLoad?.();await ctx.window.AyarimeUnifiedModule.ready;
  },click:async()=>{
    nodes.get("ai-module-toggle").click();
    await new Promise(resolve=>setImmediate(resolve));
  },fail:next=>{fail=next;},
    failCredentialClear:next=>{clearFails=next;},
    clearCalls:()=>clearCalls,stored:()=>({hasKey,value})};
}
test("AI is available by default without writing any preference",async()=>{
  const h=harness();await h.load();
  assert.equal(h.ctx.window.AyarimeUnifiedModule.isEnabled(),true);
  assert.deepEqual(h.stored(),{hasKey:false,value:false});
  assert.equal(h.nodes.get("ai-module-toggle").attributes["aria-pressed"],"true");
});

test("failing to pause does not claim pause or erase previous preference",async()=>{
  const h=harness();await h.load();
  h.fail(true);await h.click();
  assert.equal(h.ctx.window.AyarimeUnifiedModule.isEnabled(),true);
  assert.match(h.nodes.get("ai-module-status").textContent,/could not save|Could not save/);
  assert.equal(h.nodes.get("ai-module-toggle").attributes["aria-pressed"],"true");
  assert.deepEqual(h.stored(),{hasKey:false,value:false});
  h.fail(false);await h.click();
  assert.equal(h.ctx.window.AyarimeUnifiedModule.isEnabled(),false);
  assert.deepEqual(h.stored(),{hasKey:true,value:false});
  h.fail(true);await h.click();
  assert.equal(h.ctx.window.AyarimeUnifiedModule.isEnabled(),false,
    "Failed resume must never imply provider access was restored");
});

test("pausing purges credentials; a failure does not claim pause",async()=>{
  const h=harness();await h.load();
  h.failCredentialClear(true);
  await h.click();
  assert.equal(h.ctx.window.AyarimeUnifiedModule.isEnabled(),true);
  assert.match(h.nodes.get("ai-module-status").textContent,/session key/);
  assert.equal(h.clearCalls(),1);
  h.failCredentialClear(false);
  await h.click();
  assert.equal(h.ctx.window.AyarimeUnifiedModule.isEnabled(),false);
  assert.equal(h.clearCalls(),2);
  await h.click();
  assert.equal(h.ctx.window.AyarimeUnifiedModule.isEnabled(),true);
  assert.equal(h.stored().value,true);
});