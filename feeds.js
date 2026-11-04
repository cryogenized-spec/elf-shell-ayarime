"use strict";
/* ELF//SHELL RSS/Atom module. Remote requests only to opted-in, site-authorised feeds. */
(() => {
  const settingsKey = "elfshell-rss-settings-v1";
  const cacheKey = "elfshell-rss-cache-v1";
  const maxFeeds = 32;
  const maxArticles = 180;
  const validMinutes = [15, 30, 60, 180, 360];
  const initial = () => ({enabled:true, interval:30, feeds:[]});
  let prefs = initial();
  let cache = {};
  let headlines = [];
  let tickerIndex = 0;
  let tickerTimer = null;
  let tickerPaused = false;
  let fetching = false;

  
  const $ = id => document.getElementById(id);

  function validFeedUrl(value) {
    try {
      const url = new URL(value);
      if (url.protocol !== "https:" || !url.hostname || url.username || url.password || url.port || value.length > 2048) return false;
      if (url.hostname === "localhost" || url.hostname.endsWith(".localhost") || url.hostname.endsWith(".local")) return false;
      if (/^\d+\.\d+\.\d+\.\d+$/.test(url.hostname) || url.hostname.startsWith("[")) return false;
      return true;
    } catch { return false; }
  }
  function normaliseFeedUrl(input) {
    const value = String(input || "").trim();
    if (!value) return null;
    const candidate = /^[a-z][a-z\d+.-]*:\/\//i.test(value) ? value : "https://" + value;
    if (!validFeedUrl(candidate)) return null;
    const url = new URL(candidate);
    const isSubstack = /(^|\.)substack\.com$/i.test(url.hostname) && url.hostname !== "substack.com";
    // Substack publications and their /p/article links use a public /feed endpoint.
    // Only rewrite known Substack-hosted publications. Other hosts may use
    // /p/ for unrelated content. Custom domains should supply their /feed URL.
    if (isSubstack) {
      url.pathname = "/feed"; url.search = ""; url.hash = "";
    } else url.hash = "";
    return url.href;
  }
  function originPattern(value) {
    const url = new URL(value);
    if (!validFeedUrl(url.href)) throw new Error("Only public HTTPS feed domains are supported.");
    return `https://${url.hostname}/*`;
  }
  function sanitiseFeed(value) {
    if (!value || typeof value !== "object") return null;
    const url = normaliseFeedUrl(value.url);
    if (!url) return null;
    const title = typeof value.title === "string" ? value.title.trim().slice(0, 72) : "";
    const group = typeof value.group === "string" ? value.group.trim().slice(0, 28) : "";
    return {url, title:title || new URL(url).hostname, group:group || "GENERAL", enabled:value.enabled !== false};
  }
  function validateSnapshot(value) {
    if (!value || typeof value !== "object" || !Array.isArray(value.feeds) || value.feeds.length > maxFeeds) return null;
    const output = [], seen = new Set();
    for (const item of value.feeds) {
      const feed = sanitiseFeed(item);
      if (!feed) return null;
      if (seen.has(feed.url)) continue;
      seen.add(feed.url); output.push(feed);
    }
    return {enabled:value.enabled !== false, interval:validMinutes.includes(value.interval) ? value.interval : 30, feeds:output};
  }
  function validArticleUrl(value) {
    try {
      if (typeof value !== "string" || value.length > 2048) return false;
      const url = new URL(value);
      return (url.protocol === "https:" || url.protocol === "http:") && !url.username && !url.password;
    } catch { return false; }
  }
  function parseFeedXml(xml, sourceUrl) {
    if (typeof xml !== "string" || xml.length > 1500000) throw new Error("Feed XML exceeds the size limit.");
    if (/<!\s*(?:DOCTYPE|ENTITY)\b/i.test(xml))throw new Error("Feeds with XML DTD/entities are not supported.");
    const doc = new DOMParser().parseFromString(xml, "application/xml");
    if (doc.getElementsByTagName("parsererror").length) throw new Error("Invalid RSS/Atom XML.");
    const root = doc.documentElement;
    if (!root || !["rss", "feed", "RDF"].includes(root.localName)) throw new Error("The URL did not return an RSS or Atom feed.");
    const atom = root.localName === "feed";
    const entries = [...doc.getElementsByTagName(atom ? "entry" : "item")].slice(0, 40);
    function child(node, name) {
      return [...node.children].find(x => x.localName === name) || null;
    }
    const out = [];
    for (const entry of entries) {
      const title = (child(entry, "title")?.textContent || "").trim().slice(0, 240);
      if (!title) continue;
      let link = "";
      if (atom) {
        const links = [...entry.children].filter(x => x.localName === "link");
        link = (links.find(x => !x.getAttribute("rel") || x.getAttribute("rel") === "alternate") || links[0])?.getAttribute("href") || "";
      } else link = child(entry, "link")?.textContent?.trim() || "";
      let article;
      try { article = new URL(link, sourceUrl).href; } catch { continue; }
      if (!validArticleUrl(article)) continue;
      const rawDate = child(entry, "pubDate")?.textContent || child(entry, "published")?.textContent || child(entry, "updated")?.textContent || "";
      const date = Date.parse(rawDate);
      out.push({title, url:article, date:Number.isFinite(date) ? date : 0});
    }
    return out;
  }
  function parseOpml(xml) {
    if (typeof xml !== "string" || xml.length > 350000) throw new Error("OPML file too large.");
    if (/<!\s*(?:DOCTYPE|ENTITY)\b/i.test(xml))throw new Error("OPML with XML DTD/entities is not supported.");
    const doc = new DOMParser().parseFromString(xml, "application/xml");
    if (doc.getElementsByTagName("parsererror").length || doc.documentElement?.localName.toLowerCase() !== "opml") throw new Error("Invalid OPML document.");
    const result = [], seen = new Set();
    for (const element of doc.getElementsByTagName("outline")) {
      const value = element.getAttribute("xmlUrl");
      if (!value) continue;
      const parent = element.parentElement;
      const group = element.getAttribute("category") || (parent?.localName === "outline" && !parent.hasAttribute("xmlUrl") ? (parent.getAttribute("title") || parent.getAttribute("text") || "") : "");
      const feed = sanitiseFeed({url:value, title:element.getAttribute("title") || element.getAttribute("text") || "", group});
      if (feed && !seen.has(feed.url)) {seen.add(feed.url); result.push(feed);}
      if (result.length >= maxFeeds) break;
    }
    return result;
  }
  const escapeXml = value => String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&apos;");
  function exportOpml(feeds) {
    const items = feeds.map(f => `    <outline type="rss" text="${escapeXml(f.title)}" title="${escapeXml(f.title)}" category="${escapeXml(f.group)}" xmlUrl="${escapeXml(f.url)}"/>`).join("\n");
    return `<?xml version="1.0" encoding="UTF-8"?>\n<opml version="2.0"><head><title>ELF//SHELL subscriptions</title></head><body>\n${items}\n</body></opml>\n`;
  }
  function status(message) { $("feed-message").textContent = message; }
  function fileDownload(text, filename, type) {
    const url = URL.createObjectURL(new Blob([text], {type}));
    const anchor = document.createElement("a"); anchor.href = url; anchor.download = filename;
    document.body.append(anchor); anchor.click(); anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1500);
  }
  async function storageGet(key) {
    if (typeof browser !== "undefined" && browser.storage) return (await browser.storage.local.get(key))[key];
    try { return JSON.parse(localStorage.getItem(key) || "null"); } catch { return null; }
  }
  async function storageSet(key, data) {
    if (typeof browser !== "undefined" && browser.storage) await browser.storage.local.set({[key]:data});
    else localStorage.setItem(key, JSON.stringify(data));
  }
  function savePrefs() {return storageSet(settingsKey,prefs);}
  function saveCache() {return storageSet(cacheKey,cache);}
  async function hasHost(url) {
    if (typeof browser === "undefined" || !browser.permissions) return false;
    try { return await browser.permissions.contains({origins:[originPattern(url)]}); } catch {return false;}
  }
  // IMPORTANT: Called directly inside an actual button click, before any async work.
  function requestHost(url) {return browser.permissions.request({origins:[originPattern(url)]});}
  function makeButton(text, handler, className) {
    const button = document.createElement("button");button.type="button";button.textContent=text;
    if (className) button.className=className;
    button.addEventListener("click",handler); return button;
  }
  function rebuildHeadlines() {
    const unique = new Set();const out = [];
    for (const feed of prefs.feeds.filter(x=>x.enabled)) {
      for (const item of cache[feed.url]?.items || []) {
        if (!validArticleUrl(item.url) || typeof item.title !== "string") continue;
        if (unique.has(item.url)) continue;
        unique.add(item.url);out.push({...item,source:feed.title,group:feed.group});
      }
    }
    headlines=out.sort((a,b)=>b.date-a.date).slice(0,maxArticles);
    tickerIndex=Math.min(tickerIndex,Math.max(0,headlines.length-1));
    renderTicker();renderArticles();
  }
  function renderTicker() {
    const label=$("feed-headline");const link=$("feed-headline-link");
    const placeholder=$("feed-placeholder");
    if (!prefs.enabled) {placeholder.textContent="NEWS TICKER PAUSED";placeholder.hidden=false;link.hidden=true;return;}
    if (!headlines.length) {placeholder.textContent=prefs.feeds.length?"NO CACHED HEADLINES · MANAGE FEEDS":"YOUR NETWORK · ADD A PUBLICATION";placeholder.hidden=false;link.hidden=true;return;}
    placeholder.hidden=true;
    const item=headlines[tickerIndex%headlines.length];
    label.textContent=item.source+" // "+item.title;
    link.href=item.url;link.hidden=false;link.title=item.title;
  }
  function renderArticles() {
    const root=$("feed-articles");root.replaceChildren();
    if (!headlines.length) {const p=document.createElement("p");p.className="quiet";p.textContent="No headlines loaded. Add a publication, enable its host access and refresh.";root.append(p);return;}
    for(const item of headlines.slice(0,55)) {
      const row=document.createElement("a");row.href=item.url;row.target="_blank";row.rel="noopener noreferrer";row.className="feed-article";
      const headline=document.createElement("span");headline.textContent=item.title;
      const meta=document.createElement("small");meta.textContent=item.source+(item.date?" · "+new Date(item.date).toLocaleDateString():"");
      row.append(headline,meta);root.append(row);
    }
  }
  async function renderFeeds() {
    const root=$("feed-subscriptions");root.replaceChildren();
    if (!prefs.feeds.length) {const p=document.createElement("p");p.className="quiet";p.textContent="No subscriptions yet. Add a Substack address or an RSS/Atom URL above.";root.append(p);return;}
    for(const feed of prefs.feeds) {
      const row=document.createElement("div");row.className="feed-subscription";
      const details=document.createElement("div");details.className="feed-description";
      const title=document.createElement("strong");title.textContent=feed.title;
      const url=document.createElement("small");url.textContent=feed.group+" // "+feed.url;url.title=feed.url;
      const cached=cache[feed.url];
      const hint=document.createElement("small");hint.className="feed-hint";hint.textContent=cached?.error?"ERROR: "+cached.error:(cached?.checkedAt?`UPDATED ${new Date(cached.checkedAt).toLocaleString()}`:"NOT YET FETCHED");
      details.append(title,url,hint);
      const actions=document.createElement("div");actions.className="feed-sub-actions";
      const checked=await hasHost(feed.url);
      const toggle=makeButton(feed.enabled?"ON":"OFF",async()=>{feed.enabled=!feed.enabled;await savePrefs();rebuildHeadlines();renderFeeds();},feed.enabled?"feed-active":"");toggle.title="Include or exclude this publication";
      const permission=makeButton(checked?"REVOKE HOST":"ALLOW HOST",()=>{
        if(!checked) {
          // Do not await before triggering permissions.request: Firefox requires user activation.
          const request=requestHost(feed.url);
          request.then(async ok=>{status(ok?"Permission granted for "+new URL(feed.url).hostname:"Permission declined.");await renderFeeds();if(ok){const result=await fetchOne(feed,true);await saveCache();rebuildHeadlines();await renderFeeds();status(result.error?"Feed error: "+result.error:"Access granted. Latest headlines updated.");}}).catch(e=>status("Permission error: "+e.message));
        }else {
          browser.permissions.remove({origins:[originPattern(feed.url)]}).then(async()=>{status("Host access revoked; other feeds at this site will also lose access.");await renderFeeds();}).catch(e=>status("Revoke failed: "+e.message));
        }
      });
      const edit=makeButton("EDIT",()=>{
        const name=prompt("Publication label",feed.title);if(name===null)return;
        const group=prompt("Subscription group",feed.group);if(group===null)return;
        feed.title=String(name).trim().slice(0,72)||feed.title;feed.group=String(group).trim().slice(0,28)||"GENERAL";
        savePrefs().then(()=>{rebuildHeadlines();renderFeeds();});
      });
      const remove=makeButton("REMOVE",async()=>{if(!confirm("Remove "+feed.title+" from ELF//SHELL?"))return;prefs.feeds=prefs.feeds.filter(x=>x.url!==feed.url);delete cache[feed.url];await Promise.all([savePrefs(),saveCache()]);rebuildHeadlines();renderFeeds();});
      actions.append(toggle,permission,edit,remove);row.append(details,actions);root.append(row);
    }
  }
  async function fetchOne(feed, force) {
    if (!feed.enabled || !await hasHost(feed.url)) return {skipped:true};
    const cached=cache[feed.url];
    if (!force && cached?.attemptedAt && Date.now()-cached.attemptedAt < prefs.interval*60000) return {skipped:true};
    const abort=new AbortController();const timeout=setTimeout(()=>abort.abort(),12000);
    try {
      const response=await fetch(feed.url,{credentials:"omit",referrerPolicy:"no-referrer",redirect:"error",signal:abort.signal,cache:"no-cache"});
      if(!response.ok)throw Error("HTTP "+response.status);
      const length=Number(response.headers.get("content-length") || 0);
      if (length > 1500000)throw Error("Feed too large");
      let xml="";
      if (response.body && response.body.getReader) {
        const reader=response.body.getReader(),decoder=new TextDecoder();let count=0;
        while(true){const {done,value}=await reader.read();if(done)break;count+=value.byteLength;if(count>1500000){await reader.cancel();throw Error("Feed too large");}xml+=decoder.decode(value,{stream:true});}
        xml+=decoder.decode();
      } else {xml=await response.text();}
      const parsed=parseFeedXml(xml,response.url||feed.url);
      cache[feed.url]={items:parsed.slice(0,36),checkedAt:Date.now(),attemptedAt:Date.now(),error:""};
      return {count:parsed.length};
    } catch(error) {
      cache[feed.url]={items:cached?.items||[],checkedAt:cached?.checkedAt||0,attemptedAt:Date.now(),error:(error.name==="AbortError"?"Timed out":error instanceof TypeError?"Fetch blocked, unavailable, or redirected; check the canonical HTTPS feed URL and site permission.":error.message||"Unknown error").slice(0,150)};
      return {error:cache[feed.url].error};
    } finally {clearTimeout(timeout);}
  }
  async function refreshFeeds(force=false) {
    if(fetching || !prefs.enabled)return;
    fetching=true;
    const pending=prefs.feeds.filter(f=>f.enabled);
    let count=0,errors=0;
    status("Refreshing authorised subscriptions…");
    // A small pool avoids hammering a user's subscribed services on every new tab.
    let next=0;
    const worker=async()=>{while(next<pending.length){const feed=pending[next++];const result=await fetchOne(feed,force);if(result.count!==undefined)count+=result.count;if(result.error)errors++;}};
    try {await Promise.all(Array.from({length:Math.min(3,pending.length)},worker));await saveCache();rebuildHeadlines();await renderFeeds();
      status(`Feed check complete · ${count} entries retrieved · ${errors} errors · ${headlines.length} cached headlines`);
    } finally {fetching=false;}
  }
  async function addFeed(event) {
    event.preventDefault();
    const url=normaliseFeedUrl($("feed-url").value);
    if (!url) {status("Enter a public HTTPS RSS or Substack address.");return;}
    if(prefs.feeds.some(f=>f.url===url)){status("Already subscribed to this publication.");return;}
    if(prefs.feeds.length>=maxFeeds){status("Subscription limit reached (32 feeds).");return;}
    const title=$("feed-label").value.trim().slice(0,72)||new URL(url).hostname;
    const group=$("feed-group").value.trim().slice(0,28)||"GENERAL";
    const feed={url,title,group,enabled:true};
    if (typeof browser === "undefined" || !browser.permissions){status("RSS fetching requires Firefox extension mode. Feed settings preview only.");return;}
    // Request access immediately from form submit. Do NOT await ahead of this request.
    const permission=requestHost(url);
    try {
      const accepted=await permission;
      if (!accepted){status("Host access declined. Nothing was subscribed.");return;}
      prefs.feeds.push(feed);await savePrefs();
      $("feed-url").value="";$("feed-label").value="";
      status("Subscription saved. Fetching the publication feed…");await renderFeeds();
      const result=await fetchOne(feed,true);await saveCache();rebuildHeadlines();await renderFeeds();
      status(result.error?"Subscription saved, but could not fetch: "+result.error:"Subscription saved. "+(result.count||0)+" headlines retrieved.");
    } catch(error){status("Unable to subscribe: "+error.message);}
  }
  async function importOpml(file) {
    try {
      if(!file||file.size>350000)throw Error("OPML exceeds 350 KB");
      const additions=parseOpml(await file.text());if(!additions.length)throw Error("No supported HTTPS RSS feeds found");
      let count=0;const current=new Set(prefs.feeds.map(f=>f.url));
      for(const f of additions){if(prefs.feeds.length>=maxFeeds)break;if(current.has(f.url))continue;current.add(f.url);prefs.feeds.push(f);count++;}
      await savePrefs();await renderFeeds();rebuildHeadlines();
      status(`Imported ${count} subscriptions. Grant host access to each source before fetching; no external requests were made.`);
    }catch(error){status("OPML import rejected: "+error.message);}
  }
  function show(){renderFeeds();renderArticles();$("feeds-dialog").showModal();}
  async function init(){
    try{
      prefs=validateSnapshot(await storageGet(settingsKey))||initial();
      const saved=await storageGet(cacheKey);
      cache={};
      if(saved&&typeof saved==="object"&&!Array.isArray(saved)){
        // Cache is local but untrusted: only restore small, safe article metadata.
        for(const feed of prefs.feeds){
          const entry=saved[feed.url];
          if(!entry||typeof entry!=="object")continue;
          const items=Array.isArray(entry.items)?entry.items.slice(0,36).filter(item=>
            item&&validArticleUrl(item.url)&&typeof item.title==="string"
          ).map(item=>({title:item.title.slice(0,240),url:item.url,date:Number.isFinite(item.date)?item.date:0})):[];
          cache[feed.url]={items,checkedAt:Number.isFinite(entry.checkedAt)?entry.checkedAt:0,attemptedAt:Number.isFinite(entry.attemptedAt)?entry.attemptedAt:0,error:typeof entry.error==="string"?entry.error.slice(0,150):""};
        }
      }
    }
    catch(error){console.warn("ELF//SHELL: RSS settings unavailable",error);}

    $("feed-enabled").checked=prefs.enabled;$("feed-frequency").value=String(prefs.interval);
    rebuildHeadlines();
    $("feed-headline").addEventListener("mouseenter",()=>{tickerPaused=true;});
    $("feed-headline").addEventListener("mouseleave",()=>{tickerPaused=false;});
    tickerTimer=setInterval(()=>{if(!tickerPaused&&prefs.enabled&&headlines.length>1){tickerIndex=(tickerIndex+1)%headlines.length;renderTicker();}},15000);
    // No periodic background service. Only check saved, already-authorised feeds on an open new tab.
    if(prefs.feeds.some(f=>f.enabled))refreshFeeds(false);
  }
  if(typeof module!=="undefined" && module.exports)module.exports={normaliseFeedUrl,validFeedUrl,originPattern,sanitiseFeed,validateSnapshot,validArticleUrl,parseFeedXml,parseOpml,exportOpml};
  if(typeof document==="undefined")return;
  window.elfFeeds={
    snapshot:()=>({...prefs,feeds:prefs.feeds.map(x=>({...x}))}),
    validateSnapshot,
    applySnapshot:async value=>{const clean=validateSnapshot(value);if(!clean)throw Error("Invalid RSS settings");prefs=clean;await savePrefs();$("feed-enabled").checked=prefs.enabled;$("feed-frequency").value=String(prefs.interval);await renderFeeds();rebuildHeadlines();},
    show,
  };
  $("feeds-toggle").addEventListener("click",show);
  $("feed-manage").addEventListener("click",show);
  $("feed-add-form").addEventListener("submit",addFeed);
  $("feed-close").addEventListener("click",()=>$("feeds-dialog").close());
  $("feed-refresh").addEventListener("click",()=>refreshFeeds(true));
  $("feed-enabled").addEventListener("change",async e=>{prefs.enabled=e.target.checked;await savePrefs();renderTicker();if(prefs.enabled)refreshFeeds(false);});
  $("feed-frequency").addEventListener("change",async e=>{prefs.interval=validMinutes.includes(Number(e.target.value))?Number(e.target.value):30;await savePrefs();});
  $("feed-export-opml").addEventListener("click",()=>fileDownload(exportOpml(prefs.feeds),"elfshell-subscriptions.opml","text/xml"));
  $("feed-import-opml").addEventListener("click",()=>$("feed-opml-file").click());
  $("feed-opml-file").addEventListener("change",e=>{const f=e.target.files?.[0];if(f)importOpml(f);e.target.value="";});
  $("feed-prev").addEventListener("click",()=>{if(headlines.length){tickerIndex=(tickerIndex+headlines.length-1)%headlines.length;renderTicker();}});
  $("feed-next").addEventListener("click",()=>{if(headlines.length){tickerIndex=(tickerIndex+1)%headlines.length;renderTicker();}});
  init();
})();
