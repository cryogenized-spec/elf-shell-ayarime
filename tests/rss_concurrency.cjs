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
 // A second dashboard may complete an older fetch after a newer one.
 // Its late cache write must not roll back the latest persisted headlines.
 const baseline=data[cacheKey][b].attemptedAt;
 const newer={...item('https://beta.org/new-headlines'),checkedAt:baseline+20,attemptedAt:baseline+20};
 const stale={...item('https://beta.org/obsolete-headlines'),checkedAt:baseline+10,attemptedAt:baseline+10};
 const newerResult=await req('cache',{url:b,entry:newer});
 const staleResult=await req('cache',{url:b,entry:stale});
 assert(newerResult.ok&&staleResult.ok);
 assert.equal(data[cacheKey][b].items[0].url,'https://beta.org/new-headlines','older RSS refresh must not replace later headline data');
 // A newer failed attempt may update error status, but must keep a successful
 // headline batch from another dashboard rather than an old local snapshot.
 const failedEntry={...item('https://beta.org/stale-copy'),attemptedAt:baseline+30,checkedAt:baseline+5,error:'Timeout'};
 await req('cache',{url:b,entry:failedEntry});
 assert.equal(data[cacheKey][b].items[0].url,'https://beta.org/new-headlines','failed refresh must retain newer cached articles');
 assert.equal(data[cacheKey][b].error,'Timeout');
 // Codex P2: a success fetched at T200 may be persisted after a failed
 // refresh at T300. The successful headlines are still fresher than cached
 // T100 content, even though the error/attempt metadata at T300 wins.
 const successfulAt200={...item('https://beta.org/success-at-200'),checkedAt:baseline+50,attemptedAt:baseline+50,error:''};
 const laterFailedAt300={...item('https://beta.org/stale-at-100'),checkedAt:baseline+25,attemptedAt:baseline+80,error:'Gateway timeout'};
 const first=await req('cache',{url:b,entry:laterFailedAt300});
 const second=await req('cache',{url:b,entry:successfulAt200});
 assert(first.ok&&second.ok,'both writes are valid even when delivered in reverse');
 assert.equal(data[cacheKey][b].items[0].url,'https://beta.org/success-at-200','late successful content must supersede older articles');
 assert.equal(data[cacheKey][b].checkedAt,baseline+50,'successful content carries its own newest checkedAt');
 assert.equal(data[cacheKey][b].attemptedAt,baseline+80,'later attempt status remains newest');
 assert.equal(data[cacheKey][b].error,'Gateway timeout','most recent attempted refresh still reports its error');


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
 // The dashboard must only submit cache entries it fetched itself, even
 // when its memory still includes an older entry for some other publication.
 const feedSource=fs.readFileSync(path.resolve(__dirname,'../feeds.js'),'utf8');
 const instrumentation='globalThis.__rssCacheQa={setPrefs(value){prefs=value;},seed(url,value){cache[url]=value;},mark(url,value){cache[url]=value;pendingCacheWrites.set(url,value);},save:()=>saveCache()};';
 const sourceForQa=feedSource.replace('  if(typeof module!=="undefined"', '  '+instrumentation+'\n  if(typeof module!=="undefined"');
 assert(sourceForQa!==feedSource,'RSS test hook must be inserted');
 const calls=[];
 const qa={URL,console,globalThis:null,browser:{storage:{local:{}},runtime:{sendMessage:async msg=>{calls.push(msg);return {ok:true,prefs: {enabled:true,interval:30,feeds:[feed(a),feed(b)]},cache: data[cacheKey]};}}}};
 qa.globalThis=qa;
 vm.runInNewContext(sourceForQa,qa,{timeout:2000});
 qa.__rssCacheQa.setPrefs({enabled:true,interval:30,feeds:[feed(a),feed(b)]});
 qa.__rssCacheQa.seed(b,item('https://beta.org/old-data-from-my-dashboard'));
 qa.__rssCacheQa.mark(a,item('https://alpha.org/the-feed-i-actually-refreshed'));
 await qa.__rssCacheQa.save();
 assert.equal(calls.length,1,'only one changed feed must be saved');
 assert.equal(calls[0].url,a,'other feeds from a stale snapshot must not be resent');

 console.log('RSS concurrency QA PASS: changed-only dashboard cache writes, concurrent add/cache, remove+add, no deleted-cache resurrection, config/edit, write failure/retry, unsafe hosts.');
})().catch(e=>{console.error(e);process.exitCode=1;});
