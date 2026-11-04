'use strict';
const fs=require('node:fs');const path=require('node:path');const assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..');
const quotes=JSON.parse(fs.readFileSync(path.join(root,'assets/ayarime-quotes.json'),'utf8'));
const code=fs.readFileSync(path.join(root,'memory.js'),'utf8');
const main=fs.readFileSync(path.join(root,'newtab.js'),'utf8');
const html=fs.readFileSync(path.join(root,'newtab.html'),'utf8');
assert.equal(quotes.length,28);
assert.equal(new Set(quotes.map(q=>q.id)).size,quotes.length);
assert(quotes.every(q=>/^AYR-\d{4}$/.test(q.id)&&q.category&&q.jp&&q.en&&q.shortJp&&q.shortEn));
assert(quotes.every(q=>q.jp.length<=350&&q.en.length<=400));
for(const id of ['memory-panel','memory-counter','memory-fragment-id','memory-category','memory-open','memory-compact-jp','memory-compact-en','memory-prev','memory-pause','memory-next','memory-dialog','memory-detail-jp','memory-detail-en','memory-detail-language','memory-detail-interval','memory-detail-prev','memory-detail-next','memory-detail-favourite','memory-detail-pin','memory-view-favourites','memory-detail-id','memory-detail-category','memory-categories','memory-message','memory-detail-close']){
 assert(html.includes('id="'+id+'"'),'missing memory HUD node: '+id);
}
assert(html.includes('<script defer src="memory.js"></script>'));
assert(main.includes('window.elfMemory?.snapshot()')&&main.includes('window.elfMemory.applySnapshot(memoryImport)'));
assert(!/https?:\/\//.test(code),'Memory Trace must not call remote endpoints');
assert(!/\beval\s*\(/.test(code),'No evaluation of quote contents');
assert(code.includes('textContent=q.jp')&&code.includes('textContent=q.en'),'Plain-text insertion required for untrusted content');
assert(code.includes('setInterval(')&&code.includes('Date.now()-prefs.anchor'),'Timer must use shared time anchor');
console.log(`Memory Trace: ${quotes.length} original bilingual fragments, dialog controls, backup and local-only policy validated.`);
