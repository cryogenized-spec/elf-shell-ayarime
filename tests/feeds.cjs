'use strict';
const assert=require('node:assert/strict');
const {normaliseFeedUrl,validFeedUrl,originPattern,sanitiseFeed,validateSnapshot,validArticleUrl,parseFeedXml,exportOpml}=require('../feeds.js');
assert.equal(normaliseFeedUrl('thebrowser.substack.com'), 'https://thebrowser.substack.com/feed');
assert.equal(normaliseFeedUrl('https://thebrowser.substack.com/p/a-story?utm_source=test'), 'https://thebrowser.substack.com/feed');
assert.equal(normaliseFeedUrl('https://www.example.org/rss.xml'), 'https://www.example.org/rss.xml');
assert.equal(normaliseFeedUrl('example.org/rss.xml'), 'https://example.org/rss.xml');
assert.equal(normaliseFeedUrl('https://www.example.org/p/something'), 'https://www.example.org/p/something', 'unrelated /p/ URLs must never be rewritten');
assert.equal(normaliseFeedUrl('https://mycustomdomain.com/feed'), 'https://mycustomdomain.com/feed', 'custom-domain Substack users can add an explicit /feed URL');
assert.equal(normaliseFeedUrl('https://thebrowser.substack.com/about'), 'https://thebrowser.substack.com/feed');
assert.equal(normaliseFeedUrl('http://example.org/rss'),null,'HTTP not supported');
assert.equal(normaliseFeedUrl('https://127.0.0.1/rss'),null,'no private address');
assert.equal(normaliseFeedUrl('https://x.local/rss'),null,'no local hostname');
for(const host of ['localhost.','router','nas','printer.lan','gateway.internal','device.home.arpa','local.test','anything.invalid','a.example']) {
  assert.equal(normaliseFeedUrl(`https://${host}/feed`),null,`reject non-public hostname ${host}`);
}
assert.equal(normaliseFeedUrl('https://example.org./feed'),null,'reject trailing-dot hostname');
assert.equal(normaliseFeedUrl('https://127.1/rss'),null,'URL parser canonicalises shorthand IPv4');
assert.equal(normaliseFeedUrl('https://0x7f000001/rss'),null,'URL parser canonicalises hexadecimal IPv4');
assert.equal(normaliseFeedUrl('https://example.org/feed'), 'https://example.org/feed','keep ordinary public feed URLs');
assert.equal(normaliseFeedUrl('javascript:alert(1)'),null);
assert.equal(originPattern('https://my.example.org/rss'), 'https://my.example.org/*');
assert.equal(validFeedUrl('https://example.org/rss'),true);
assert.equal(validArticleUrl('https://example.org/article'),true);
assert.equal(validArticleUrl('javascript:alert(1)'),false);
assert.equal(validArticleUrl('https://someone:secret@example.org/post'),false);
assert.equal(validArticleUrl('https://example.org/'+'x'.repeat(2050)),false);
assert.equal(validFeedUrl('https://user:password@example.org/rss'),false);
assert.equal(sanitiseFeed({url:'example.substack.com',title:'  Notes  ',group:' Tech '} ).title,'Notes');
const prefs=validateSnapshot({enabled:true,interval:30,feeds:[
 {url:'https://a.substack.com/feed',title:'a',group:'writing'},
 {url:'https://a.substack.com/feed',title:'duplicate'},
 {url:'https://b.org/atom.xml',title:'b',enabled:false}
]});
assert.equal(prefs.feeds.length,2);
assert.equal(prefs.feeds[1].enabled,false);
assert.equal(validateSnapshot({feeds:[{url:'file:///etc/passwd'}]}),null);
assert.equal(validateSnapshot({feeds:'not-an-array'}),null);
assert.equal(validateSnapshot({feeds:Array.from({length:33},()=>({url:'https://test.com/feed'}))}),null);
const opml=exportOpml([{title:'Test & <A>',url:'https://example.com/?q=a&b=1',group:'WRITING'}]);
assert(opml.includes('Test &amp; &lt;A&gt;'));
assert(opml.includes('q=a&amp;b=1'));
assert(opml.includes('category="WRITING"'));
// Parser rejects DTD before any DOM parsing (no external entity expansion).
assert.throws(()=>parseFeedXml('<!DOCTYPE x><rss/>','https://example.org/rss'),/DTD\/entities/);
assert(/redirect:"error"/.test(require('node:fs').readFileSync(require('node:path').join(__dirname,'..','feeds.js'),'utf8')),'feed fetches must not follow redirects to unapproved sites');
console.log('RSS module: URL handling, per-host grants, backup validation, OPML escaping, XML safety checks passed.');
