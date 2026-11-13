'use strict';
const assert=require('node:assert/strict');
const {officialFeed,normaliseFeedUrl,validFeedUrl,originPattern,sanitiseFeed,validateSnapshot,validArticleUrl,parseFeedXml,parseOpml,exportOpml,hasUnsafeXmlDeclaration}=require('../feeds.js');
assert.equal(officialFeed.url,'https://cryogenized-spec.github.io/elf-shell-ayarime/feed.xml');
assert.equal(officialFeed.group,'PROJECT');
// Featured first-party feed is opt-in; browser host consent is requested
// synchronously from the actual click before any network fetch begins.
const fs=require('node:fs'),path=require('node:path');
const ui=fs.readFileSync(path.join(__dirname,'..','newtab.html'),'utf8');
const source=fs.readFileSync(path.join(__dirname,'..','feeds.js'),'utf8');
assert(ui.includes('id="feed-official-subscribe"'),'Official feed needs a direct subscribe button');
assert(ui.includes('Firefox asks for site access'),'Explicit host disclosure is needed');
assert(source.includes('$("feed-official-subscribe").addEventListener("click",subscribeOfficialFeed)'));
assert(/function subscribeOfficialFeed\(\)[\s\S]*?permission=requestHost\(feed.url\);/.test(source),
       'Permission must be requested synchronously in the official click handler');
assert(source.includes('void completeSubscription(feed,permission,false)'),
       'Featured source must preserve unfinished custom RSS drafts');
assert(source.includes('officialRequestPending=true')&&source.includes('button.disabled=true'),
       'Duplicate clicks must not open repeated permission dialogs');
assert(source.includes('const initial = () => ({enabled:true, interval:30, feeds:[]})'),
       'Fresh installs must not automatically subscribe or fetch');

assert.equal(normaliseFeedUrl(officialFeed.url),officialFeed.url,'official RSS remains canonical');
assert.equal(originPattern(officialFeed.url),'https://cryogenized-spec.github.io/*','official feed still requires explicit site permission');
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
// A real feed may contain sample HTML in inert CDATA or XML comments.
assert.equal(hasUnsafeXmlDeclaration('<rss><item><description><![CDATA[<html><!DOCTYPE html><p>Example</p>]]></description></item></rss>'),false,
  'doctype text inside CDATA is inert data, not an XML DTD');
assert.equal(hasUnsafeXmlDeclaration('<rss><!-- <!ENTITY local SYSTEM "file:///etc/passwd"> --><channel/></rss>'),false,
  'entity text inside XML comments is inert');
assert.equal(hasUnsafeXmlDeclaration('<rss><![CDATA[<!-- <!DOCTYPE html> -->]]></rss>'),false,
  'nested markup inside CDATA remains inert');
assert.equal(hasUnsafeXmlDeclaration('<!DOCTYPE rss [<!ENTITY read SYSTEM "file:///etc/passwd">]><rss/>'),true,
  'real external-entity declaration must be blocked before parsing');
assert.equal(hasUnsafeXmlDeclaration('<?xml version="1.0"?><!-- harmless --><!DOCTYPE rss><rss/>'),true,
  'a real DTD after comments must still be rejected');
assert.equal(hasUnsafeXmlDeclaration('<rss><![CDATA[<!DOCTYPE html>]]><!DOCTYPE rss></rss>'),true,
  'a real DTD after closed CDATA cannot be hidden');
assert.equal(hasUnsafeXmlDeclaration('<rss><![CDATA[unclosed <!DOCTYPE html></rss>'),true,
  'unclosed CDATA is malformed and must fail closed');
assert.equal(hasUnsafeXmlDeclaration('<rss><!-- unclosed <!ENTITY x SYSTEM "file:///a"></rss>'),true,
  'unclosed XML comments must fail closed');
const processingInstructionBypass='<?sample <!-- ?><!DOCTYPE rss [<!ENTITY title "expanded">]><!-- --><rss/>';
assert.equal(hasUnsafeXmlDeclaration(processingInstructionBypass),true,
  'processing-instruction comment text must not hide a later real DTD');
assert.throws(()=>parseFeedXml(processingInstructionBypass,'https://example.org/rss'),/DTD\/entities/,
  'RSS parsing must reject processing-instruction DTD bypass before DOMParser');
assert.throws(()=>parseOpml(processingInstructionBypass),/DTD\/entities/,
  'OPML parsing must reject processing-instruction DTD bypass before DOMParser');
assert.equal(hasUnsafeXmlDeclaration('<?sample <!-- ?><rss/>'),false,
  'a completed processing instruction is not a real XML comment or DTD');
assert.equal(hasUnsafeXmlDeclaration('<?sample <!-- <rss/>'),true,
  'unterminated processing instructions must fail closed');
// Parser rejects DTD before any DOM parsing (no external entity expansion).
assert.throws(()=>parseFeedXml('<!DOCTYPE x><rss/>','https://example.org/rss'),/DTD\/entities/);
assert(/redirect:"error"/.test(require('node:fs').readFileSync(require('node:path').join(__dirname,'..','feeds.js'),'utf8')),'feed fetches must not follow redirects to unapproved sites');
console.log('RSS module: URL handling, per-host grants, backup validation, OPML escaping, XML safety checks passed.');
