'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const source=fs.readFileSync(path.resolve(__dirname,'../background.js'),'utf8');
const settingsKey='elfshell-rss-settings-v1',cacheKey='elfshell-rss-cache-v1';
const data={};let listener,failWrite=false;
const browser={
 storage:{local:{
   async get(keys){await new Promise(resolve=>setTimeout(resolve,5));return Object.fromEntries([].concat(keys).map(key=>[key,data[key]]));},
   async set(values){if(failWrite){failWrite=false;throw Error('Test disk quota failure');}await new Promise(resolve=>setTimeout(resolve,5));Object.assign(data,JSON.parse(JSON.stringify(values)));}
 }},
 theme:{update:async()=>{}},
 runtime:{onInstalled:{addListener(){}},onStartup:{addListener(){}},onMessage:{addListener(fn){listener=fn;}}}
};
vm.runInNewContext(source,{browser,URL,Date,Promise,console,setTimeout},{timeout:2000});
const req=(action,payload={})=>listener({type:'elfshell:rss:mutate:v1',action,...payload});
const feed=url=>({url,title:'Example',group:'TECH',enabled:true});
const a='https://news.alpha.org/feed',b='https://news.beta.org/rss',c='https://news.gamma.org/feed';
const item=url=>({items:[{title:'Article',url,date:Date.now()}],checkedAt:Date.now(),attemptedAt:Date.now(),error:''});
(async()=>{
 const [x,y]=await Promise.all([req('add',{feed:feed(a)}),req('add',{feed:feed(b)})]);
 assert.equal(x.ok,true);assert.equal(y.ok,true);
 assert.deepEqual(new Set(data[settingsKey].feeds.map(f=>f.url)),new Set([a,b]),'simultaneous subscriptions must both survive');
 const [cachedA,cachedB]=await Promise.all([req('cache',{url:a,entry:item('https://alpha.org/article')}),req('cache',{url:b,entry:item('https://beta.org/article')})]);
 assert.equal(cachedA.ok,true);assert.equal(cachedB.ok,true);
 assert(data[cacheKey][a]?.items.length===1&&data[cacheKey][b]?.items.length===1,'simultaneous independent cached feeds must survive');
 const [remove,add]=await Promise.all([req('remove',{url:a}),req('add',{feed:feed(c)})]);
 assert.equal(remove.ok,true);assert.equal(add.ok,true);
 assert.deepEqual(new Set(data[settingsKey].feeds.map(f=>f.url)),new Set([b,c]));
 assert(!data[cacheKey][a],'removing a feed must also remove its cache');
 const old=await req('cache',{url:a,entry:item('https://alpha.org/new')});
 assert.equal(old.ok,true);
 assert(!data[cacheKey][a],'in-flight fetches must never revive caches for deleted feeds');
 const [edit,config]=await Promise.all([req('edit',{url:b,title:'Reader',group:'WRITING'}),req('config',{interval:180,enabled:false})]);
 assert.equal(edit.ok,true);assert.equal(config.ok,true);
 assert.equal(data[settingsKey].feeds.find(f=>f.url===b).title,'Reader');
 assert.equal(data[settingsKey].interval,180);assert.equal(data[settingsKey].enabled,false);
 failWrite=true;
 const failed=await req('add',{feed:feed('https://new.example.org/rss')});
 assert.equal(failed.ok,false);
 assert(!data[settingsKey].feeds.some(f=>f.url==='https://new.example.org/rss'),'failed write must not be reported or persisted');
 const retry=await req('add',{feed:feed('https://new.example.org/rss')});
 assert.equal(retry.ok,true);
 for(const url of ['https://localhost./feed','https://router/feed','https://host.internal/rss','https://host.lan/rss']){
   const invalid=await req('add',{feed:feed(url)});
   assert.equal(invalid.ok,false,'background rejects '+url);
 }
 console.log('RSS concurrency QA PASS: concurrent add/cache, remove+add, no deleted-cache resurrection, config/edit, write failure/retry, unsafe hosts.');
})().catch(e=>{console.error(e);process.exitCode=1;});
