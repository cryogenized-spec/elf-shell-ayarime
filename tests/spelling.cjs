"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const root=path.resolve(__dirname,"..");
const read=f=>fs.readFileSync(path.join(root,f),"utf8");
const manifest=JSON.parse(read("manifest.json"));
assert(manifest.permissions.includes("scripting"));
assert(manifest.permissions.includes("activeTab"));
assert.equal(manifest.action.default_popup,"spelling/popup.html");
assert(manifest.background.scripts.includes("spelling/background.js"));
assert(manifest.optional_host_permissions.includes("https://*/*"));
const popup=read("spelling/popup.js"),content=read("spelling/content.js");
const css=read("spelling/content.css"),worker=read("spelling/worker.js");
const bg=read("spelling/background.js");
assert(popup.includes("permissions.request"),"per-site opt-in required");
assert(popup.includes("scripting.registerContentScripts"),"dynamic site scripts required");
assert(popup.includes("scripting.unregisterContentScripts"),"site opt-out required");
assert(popup.includes('browser.tabs.query({})')&&popup.includes('browser.tabs.sendMessage(t.id'),
  "site opt-out must revalidate open tabs by ID even without host URL access");
assert(popup.includes('browser.tabs.create({url})')&&popup.includes('if(!manager)'),
  "toolbar popup must open a persistent extension tab for site permissions");
assert(popup.includes('browser.permissions.request({origins:[origin+"/*"]})'),
  "site permission must originate from a click in the persistent manager");
assert(content.includes("menuFieldCaret")&&content.includes("field.selectionStart!==caret"),
  "changing caret before choosing a correction must cancel it");
assert(content.includes("focusMenuFirst")&&content.includes('!menu?.contains(e.target)'),
  "keyboard focus entering the closed-shadow suggestions must not dismiss them");
assert(content.includes('["text","search"].includes(field.type)'),
  "input default type text must receive optional suggestions");
assert(content.includes('if(e.key==="Escape"){++fieldRequest;closeMenu()'),
  "Escape must cancel pending asynchronous suggestions";
assert(content.includes('CSS?.supports?.("selector(::highlight(elfshell-spelling-errors-v1))")'),
  "native Firefox spelling must stay active when custom underline rendering is unsupported");
assert(content.includes('if(!scan.complete)')&&content.includes('root.removeAttribute("spellcheck")'),
  "incomplete editor scan must restore Firefox native spelling");
assert(bg.includes("spellWordChain=mutation.then"),"dictionary updates must be serialized across tabs");
assert(popup.includes("browser.tabs.get(tab.id)")&&popup.includes('!==origin'),"do not immediately inject into a navigated tab");
assert(bg.includes("spellingSenderAllowed(sender)")&&bg.includes('browser.permissions.contains({origins:[origin]})'),"all spelling messages must verify actual sender and permission");
assert(bg.includes('message.type==="elfshell:spelling:authorize"'),"spelling initialization requires background authorization");
assert(bg.includes('type:"elfshell:spell:revalidate"'),"revocation must revalidate existing tabs");
assert(content.includes('if(!enabled||!event.isTrusted||event.button!==0'),"only trusted, genuine left clicks may open correction controls");
assert(content.includes('if(!e.isTrusted)return;'),"synthetic clicks may not activate dictionary buttons");
assert(content.includes('attachShadow({mode:"closed"})'),"correction controls must be hidden from host scripts");
assert(content.includes("menuRange.toString()!==menuWord"),"stale replacement ranges must be rejected");
assert(content.includes("function nativeField(target)")&&content.includes("function clickedFieldWord(field)"),
  "left-click field word detection must be included");
assert(content.includes("field.selectionStart===hit.caret")&&content.includes("field.value===hit.value"),
  "stale field click cannot open a menu after selection or value changes");
assert(content.includes('document.execCommand("insertText",false,choice)'),
  "field correction must cooperate with native Undo stack");
assert(content.includes('field.getAttribute("spellcheck")==="false"'),
  "explicit opt-out of spelling must be preserved for native fields");
assert(!content.includes("field.setRangeText("),
  "no setRangeText fallback that could corrupt framework state or Undo");
assert(content.includes('field.type="password"')===false,
  "never retype or synthesize password data");

assert(content.includes('"beforeinput"')&&content.includes("closeMenu();++revision"),"typing invalidates correction menus");


assert(!popup.includes("matches:[\"<all_urls>\"]"),"no automatic broad injection");
assert(content.includes('root.setAttribute("spellcheck","false")'),"native spelling must be disabled only after successful checker");
assert(content.includes("function restore()"),"native spelling needs an error fallback");
assert(content.includes('if(!response?.ok)throw Error'),"checker failure must not become a false success");
assert(content.includes('document.execCommand("insertText"'),"replacement must use editable/undo command");
assert(!content.includes("editor.innerHTML="),"never inject markup into host editors");
assert(!content.includes("editor.textContent="),"never rewrite host editor text");
assert(!content.includes("fetch("),"editor text must never be sent to a remote endpoint");
assert(content.includes('add("Ignore"'),"ignore action required");
assert(content.includes('add("Add to Dictionary"'),"dictionary action required");
assert(css.includes("::highlight(elfshell-spelling-errors-v1)"));
assert(!content.includes("overrideContext"),"leave Firefox's ordinary context menu intact");
assert(bg.includes("browser.storage.local.set"),"persistent custom word list required");
assert(worker.includes('importScripts("nspell-bundle.js")'),"local checker must be bundled");
assert(!worker.includes("https://"),"worker may load extension resources only");
for(const file of ["spelling/en.aff","spelling/en.dic","spelling/DICTIONARY-LICENSE.txt","spelling/NSPELL-LICENSE.txt","spelling/nspell-bundle.js"]){
  assert(fs.statSync(path.join(root,file)).size>200,file);
}
// Smoke-check the actual bundled Hunspell engine, not only source strings.
const nspell=require("../spelling/nspell-bundle.js");
assert.equal(typeof nspell,"function");
const spell=nspell({aff:read("spelling/en.aff"),dic:read("spelling/en.dic")});
assert.equal(spell.correct("receive"),true);
assert.equal(spell.correct("colour"),true);
assert.equal(spell.correct("recieve"),false);
assert(spell.suggest("recieve").includes("receive"));
spell.add("Ayarime");
assert.equal(spell.correct("Ayarime"),true);
console.log("Offline spelling engine, permissions, fallbacks, UI and packaging checks passed.");