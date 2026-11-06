#!/usr/bin/env python3
"""Real Firefox acceptance: spell-only Station consent, corrections and revocation.
Runs only in a disposable headless Firefox profile, never on a user session.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import sys
import traceback
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.support.ui import Select, WebDriverWait

ROOT=Path(__file__).resolve().parent.parent
VERSION=json.loads((ROOT/"manifest.json").read_text())["version"]
PACKAGE=ROOT/"dist"/f"ELF-SHELL-Ayarime-v{VERSION}-AMO.zip"
OUTPUT=ROOT/"dist"/"firefox-integration-qa"
OUTPUT.mkdir(parents=True,exist_ok=True)
record={"scope":"Station spelling consent Deny/Allow, existing-tab editor support and revocation","checks":[]}
driver=None
def check(name,fn):
    fn()
    record["checks"].append({"name":name,"status":"PASS"})
    print("PASS:",name,flush=True)
def ensure(ok,message):
    if not ok: raise AssertionError(message)
def api(code):
    response=driver.execute_async_script(
        "const done=arguments[arguments.length-1];"
        "Promise.resolve().then(async()=>{"+code+
        "}).then(done,error=>done({__error:String(error)}));")
    ensure(not(isinstance(response,dict) and "__error" in response),str(response))
    return response
def permission():
    return api('return await browser.permissions.contains({origins:["https://*/*"]});')
def registrations():
    return api('return (await browser.scripting.getRegisteredContentScripts()).map(x=>({id:x.id,matches:x.matches}));')
def modes():
    return api('return (await browser.storage.local.get("elfshell:browser-integration:v1"))["elfshell:browser-integration:v1"]||null;')
def prompt(choice):
    with driver.context(driver.CONTEXT_CHROME):
        WebDriverWait(driver,12).until(lambda d:d.execute_script("""
            const panel=document.getElementById("notification-popup");
            const node=document.getElementById("addon-webext-permissions-notification");
            return ["showing","open"].includes(panel?.state)&&node&&!node.hidden&&
                node.button?.getAttribute("label")==="Allow";
        """))
        target=driver.find_element(By.CSS_SELECTOR,
            "#addon-webext-permissions-notification .popup-notification-"+
            ("primary" if choice=="allow" else "secondary")+"-button")
        ensure(target.get_attribute("label")==("Allow" if choice=="allow" else "Deny"),
            "Unexpected permission prompt button")
        ActionChains(driver).move_to_element(target).click().perform()
try:
    ensure(PACKAGE.exists(),"Build the AMO ZIP before testing")
    options=webdriver.FirefoxOptions()
    options.add_argument("-headless")
    if os.environ.get("FIREFOX_BINARY"):options.binary_location=os.environ["FIREFOX_BINARY"]
    options.set_preference("browser.shell.checkDefaultBrowser",False)
    driver=webdriver.Firefox(options=options,
        service=FirefoxService(service_args=["--allow-system-access"]))
    driver.set_window_size(1366,768)
    driver.set_page_load_timeout(25)
    driver.set_script_timeout(30)
    record["browserVersion"]=driver.capabilities.get("browserVersion")
    record["addonId"]=driver.install_addon(str(PACKAGE),temporary=True)
    old=set(driver.window_handles)
    with driver.context(driver.CONTEXT_CHROME):
        driver.execute_script("window.BrowserCommands.openTab();")
    WebDriverWait(driver,15).until(lambda d:len(set(d.window_handles)-old)==1)
    dashboard=next(iter(set(driver.window_handles)-old))
    driver.switch_to.window(dashboard)
    WebDriverWait(driver,15).until(lambda d:d.current_url.startswith("moz-extension://") and
        d.find_elements(By.ID,"integration-apply"))
    driver.switch_to.new_window("tab")
    site=driver.current_window_handle
    driver.get("https://example.com/")
    ensure(driver.current_url.startswith("https://example.com/"),"Could not load public test website")
    driver.execute_script("""
        const e=document.createElement("div");
        e.id="qa-integration-editor";e.setAttribute("contenteditable","true");
        e.setAttribute("spellcheck","true");
        e.style.cssText="padding:16px;min-height:75px;font:24px sans-serif;border:1px solid #888";
        document.body.prepend(e);
        const native=document.createElement("textarea");
        native.id="qa-native-textarea";
        native.setAttribute("spellcheck","true");
        native.style.cssText="font:24px sans-serif;width:550px;height:120px;padding:10px";
        document.body.prepend(native);
        const input=document.createElement("input");
        input.id="qa-native-input"; // Default HTML input type must be supported
        input.setAttribute("spellcheck","true");
        input.style.cssText="font:24px sans-serif;width:550px;padding:10px";
        document.body.prepend(input);
        const password=document.createElement("input");
        password.type="password";password.id="qa-private-password";
        password.style.cssText="font:24px sans-serif;width:550px;padding:10px";
        document.body.prepend(password);
        const form=document.createElement("form");
        form.setAttribute("spellcheck","FALSE");
        const optedOut=document.createElement("textarea");
        optedOut.id="qa-native-optout";
        optedOut.style.cssText="font:24px sans-serif;width:550px;height:110px;padding:10px";
        optedOut.value="Unusualy spelt word";
        form.append(optedOut);document.body.prepend(form);
    """)
    driver.switch_to.window(dashboard)

    def initial():
        ensure(permission() is False,"Unexpected all-HTTPS grant")
        ensure(not registrations(),"Unexpected registered content scripts before consent")
        ensure(modes() is None,"Fresh profile must not silently enable integration")
        driver.find_element(By.CSS_SELECTOR,"#station-menu summary").click()
        driver.find_element(By.ID,"settings-toggle").click()
        WebDriverWait(driver,8).until(lambda d:d.find_element(By.ID,"settings-dialog").get_attribute("open") is not None)
        ensure(Select(driver.find_element(By.ID,"integration-spelling")).first_selected_option.get_attribute("value")=="sites",
            "Spelling defaults must be per-site")
        Select(driver.find_element(By.ID,"integration-spelling")).select_by_value("all")
    check("all-site modes are off by default and require explicit user selection",initial)

    def deny():
        driver.find_element(By.ID,"integration-apply").click()
        prompt("deny")
        WebDriverWait(driver,12).until(lambda d:
            "Permission declined" in d.find_element(By.ID,"integration-status").text)
        ensure(permission() is False,"Deny must not grant blanket host access")
        ensure(not registrations(),"Deny must not register any site-wide script")
        ensure(modes() is None,"Deny must not change stored preference")
        ensure(Select(driver.find_element(By.ID,"integration-spelling")).first_selected_option.get_attribute("value")=="all",
            "Denied permission should preserve chosen spelling mode for retry")
    check("real native Firefox Deny leaves defaults and pages unchanged",deny)

    def allow():
        driver.find_element(By.ID,"integration-apply").click()
        prompt("allow")
        WebDriverWait(driver,18).until(lambda d:permission() is True)
        WebDriverWait(driver,18).until(lambda d:
            modes() and modes().get("spellMode")=="all")
        WebDriverWait(driver,18).until(lambda d:
            {x["id"] for x in registrations()}=={"elfspell-global-v1"})
        current=registrations()
        ensure(all(x["matches"]==["https://*/*"] for x in current),
            "Unexpected host match scope or per-site registration")
        record["registeredIds"]=[x["id"] for x in current]
    check("native Firefox Allow registers only the consented all-HTTPS spelling script",allow)

    def spelling_grant_does_not_authorize_imported_rss():
        driver.switch_to.window(dashboard)
        import_result=api('''
          return await browser.runtime.sendMessage({
            type:"elfshell:rss:mutate:v1",action:"import",
            feeds:[{url:"https://github.blog/feed/",title:"Unapproved QA RSS",group:"QA",enabled:true}]
          });
        ''')
        ensure(import_result.get("ok"),"RSS import should store feed metadata only")
        ensure(api('return browser.permissions.contains({origins:["https://github.blog/*"]});') is True,
            "Wildcard spelling grant must technically cover the RSS host")
        approved=api('''
          return (await browser.storage.local.get("elfshell-rss-approved-urls-v1"))
             ["elfshell-rss-approved-urls-v1"]||[];
        ''')
        ensure("https://github.blog/feed/" not in approved,
               "Spelling permission must not approve an imported publication")
        # Explicitly load the imported settings into this already-open
        # dashboard rather than relying on a storage.onChanged render before
        # the NET FEED panel has ever been opened.
        loaded=driver.execute_async_script("""
          const done=arguments[arguments.length-1];
          Promise.resolve().then(async()=>{
            const prefs=(await browser.storage.local.get("elfshell-rss-settings-v1"))
              ["elfshell-rss-settings-v1"];
            await window.elfFeeds.applySnapshot(prefs);
            return document.querySelector("#feed-subscriptions")?.textContent
                ?.includes("Unapproved QA RSS")===true;
          }).then(done,error=>done({error:String(error)}));
        """)
        ensure(loaded is True,"Imported RSS metadata was not rendered: "+repr(loaded))
        # Instrument only this isolated CI extension page. Even a quick
        # network attempt must be observable before any external request.
        driver.execute_script("""
          window.__qaRSSAttempted=[];
          const old=window.fetch.bind(window);
          window.fetch=(...args)=>{
            window.__qaRSSAttempted.push(String(args[0]));
            return Promise.reject(Error("Unexpected CI RSS fetch"));
          };
          document.getElementById("feed-refresh").dispatchEvent(
            new MouseEvent("click",{bubbles:true}));
        """)
        try:
            WebDriverWait(driver,6).until(lambda d:
                "Feed check complete" in d.find_element(By.ID,"feed-message").text)
        except Exception as error:
            diagnostic=driver.execute_script("""
              const btn=document.getElementById("feed-refresh");
              return {message:document.getElementById("feed-message").textContent,
                disabled:btn.disabled,busy:btn.getAttribute("aria-busy"),
                prefs:window.elfFeeds.snapshot(),
                attempted:window.__qaRSSAttempted};
            """)
            record["rssDiagnostic"]=diagnostic
            raise AssertionError("RSS check did not finish: "+
                json.dumps(diagnostic,ensure_ascii=False)) from error
        attempted=driver.execute_script("return window.__qaRSSAttempted")
        ensure(not attempted,
            "Imported RSS must not make a network request under wildcard spelling permission: "+str(attempted))
        cache=api('''
          return (await browser.storage.local.get("elfshell-rss-cache-v1"))
            ["elfshell-rss-cache-v1"]||{};
        ''')
        ensure(not cache.get("https://github.blog/feed/"),
            "RSS refresh must not contact an imported feed under spelling wildcard grant")
        record["rssConsentIsolation"]=True
    check("wildcard spelling permission cannot auto-authorize OPML RSS imports",spelling_grant_does_not_authorize_imported_rss)

    def existing_tab():
        driver.switch_to.window(site)
        ensure(not driver.execute_script("""
            return !!document.getElementById("elfshell-global-cursors-v1");
        """),"Website cursor injection must not be active")
        textarea=driver.find_element(By.ID,"qa-native-textarea")
        textarea.click()
        textarea.send_keys("Unusualy spelt word")
        ensure(textarea.get_attribute("spellcheck")=="true",
               "Unsupported textarea must retain native Firefox spelling")
        editor=driver.find_element(By.ID,"qa-integration-editor")
        editor.click()
        editor.send_keys("This is a mispeled sentance.")
        WebDriverWait(driver,25).until(lambda d:d.execute_script("""
            const e=document.getElementById("qa-integration-editor");
            const marks=CSS.highlights?.get("elfshell-spelling-errors-v1");
            return e?.getAttribute("spellcheck")==="false"&&marks?.size>=1;
        """))
        ensure(editor.text=="This is a mispeled sentance.",
            "Spelling must not rewrite user text without consent")
    check("existing HTTPS tab gets only offline spelling and preserves native textarea checking",existing_tab)

    def click_misspelling(field,expected,choose=True):
        field.click()
        # Move the *real browser pointer* over the first word rather than
        # using a synthetic DOM click (trusted clicks are required).
        metrics=driver.execute_script("""
          const e=arguments[0],r=e.getBoundingClientRect(),css=getComputedStyle(e);
          const c=document.createElement("canvas").getContext("2d");
          c.font=css.font;
          const text=c.measureText(arguments[1].slice(0,Math.min(4,arguments[1].length))).width;
          const left=(parseFloat(css.paddingLeft)||0)+(parseFloat(css.borderLeftWidth)||0);
          const top=(parseFloat(css.paddingTop)||0)+(parseFloat(css.borderTopWidth)||0);
          return {dx:left+text-r.width/2,
            dy:top+(parseFloat(css.fontSize)||24)*.55-r.height/2};
        """,field,expected)
        ActionChains(driver).move_to_element_with_offset(field,
            round(metrics["dx"]),round(metrics["dy"])).click().perform()
        WebDriverWait(driver,14).until(lambda d:
            len(d.find_elements(By.CSS_SELECTOR,".elfshell-spell-menu"))==1)
        menu=driver.find_element(By.CSS_SELECTOR,".elfshell-spell-menu")
        ensure(expected in (menu.get_attribute("aria-label") or ""),
               "Left-click suggestions should be for "+expected+
               ", got "+str(menu.get_attribute("aria-label")))
        ensure(menu.rect["height"]>40,"No correction items appeared")
        if choose:
            ActionChains(driver).move_to_element_with_offset(
                menu,round(35-menu.rect["width"]/2),
                round(22-menu.rect["height"]/2)).click().perform()
        return menu

    def textarea_leftclick():
        driver.switch_to.window(site)
        native=driver.find_element(By.ID,"qa-native-textarea")
        original=native.get_attribute("value")
        ensure(original=="Unusualy spelt word","Unexpected QA textarea content")
        ensure(native.get_attribute("spellcheck")=="true",
               "Native textarea squiggle checking must stay enabled")
        click_misspelling(native,"Unusualy")
        WebDriverWait(driver,10).until(lambda d:
            d.find_element(By.ID,"qa-native-textarea").get_attribute("value")!=original)
        corrected=native.get_attribute("value")
        record["textareaCorrection"]=corrected
        ensure(corrected.endswith(" spelt word") and not corrected.startswith("Unusualy"),
            "Left-click correction changed surrounding textarea text: "+corrected)
        native.send_keys(Keys.CONTROL,"z")
        WebDriverWait(driver,10).until(lambda d:
            d.find_element(By.ID,"qa-native-textarea").get_attribute("value")==original)
        ensure(native.get_attribute("spellcheck")=="true",
               "Custom suggestions must never turn native textarea spellcheck off")
    check("ordinary textarea left-click offers offline correction and native Undo",textarea_leftclick)

    def input_leftclick():
        driver.switch_to.window(site)
        native=driver.find_element(By.ID,"qa-native-input")
        native.click()
        native.send_keys("Unusualy text")
        original=native.get_attribute("value")
        ensure(original=="Unusualy text","Unexpected QA input content")
        click_misspelling(native,"Unusualy")
        WebDriverWait(driver,10).until(lambda d:
            d.find_element(By.ID,"qa-native-input").get_attribute("value")!=original)
        corrected=native.get_attribute("value")
        record["inputCorrection"]=corrected
        ensure(corrected.endswith(" text") and not corrected.startswith("Unusualy"),
               "Correction changed surrounding input text: "+corrected)
        native.send_keys(Keys.CONTROL,"z")
        WebDriverWait(driver,10).until(lambda d:
            d.find_element(By.ID,"qa-native-input").get_attribute("value")==original)
        ensure(native.get_attribute("spellcheck")=="true",
               "Native input spelling must remain enabled")
    check("single-line text input left-click offers offline correction with Undo",input_leftclick)

    def optout_and_keyboard():
        driver.switch_to.window(site)
        field=driver.find_element(By.ID,"qa-native-optout")
        # A true left-click within a word must honour inherited, uppercase
        # spellcheck=FALSE even if the field itself has no attribute.
        field.click()
        metrics=driver.execute_script("""
          const e=arguments[0],r=e.getBoundingClientRect(),s=getComputedStyle(e);
          return {dx:30-r.width/2,dy:25-r.height/2};
        """,field)
        ActionChains(driver).move_to_element_with_offset(field,
            round(metrics["dx"]),round(metrics["dy"])).click().perform()
        ensure(driver.execute_script("""
            const f=document.getElementById("qa-native-optout");
            return f.selectionStart>0 && f.selectionStart<8;
        """),"QA click must land inside the inherited-opt-out word")
        ensure(not driver.find_elements(By.CSS_SELECTOR,".elfshell-spell-menu"),
               "Inherited spellcheck=FALSE must suppress Ayarime suggestions")
        input_box=driver.find_element(By.ID,"qa-native-input")
        menu=click_misspelling(input_box,"Unusualy",choose=False)
        ActionChains(driver).send_keys(Keys.TAB).perform()
        WebDriverWait(driver,5).until(lambda d:d.execute_script("""
            return document.activeElement===document.querySelector(".elfshell-spell-menu");
        """))
        ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        WebDriverWait(driver,6).until(lambda d:d.execute_script("""
            return !document.querySelector(".elfshell-spell-menu") &&
               document.activeElement?.id==="qa-native-input";
        """))
    check("inherited spellcheck opt-out and keyboard Escape focus restoration",optout_and_keyboard)

    def excluded_private():
        secret=driver.find_element(By.ID,"qa-private-password")
        secret.click()
        secret.send_keys("Unusualy")
        secret.click()
        ensure(not driver.find_elements(By.CSS_SELECTOR,".elfshell-spell-menu"),
               "Never offer spelling in a password field")
        driver.find_element(By.ID,"qa-integration-editor").click()
        WebDriverWait(driver,20).until(lambda d:d.execute_script("""
            const e=document.getElementById("qa-integration-editor");
            return e.getAttribute("spellcheck")==="false" &&
                CSS.highlights?.has("elfshell-spelling-errors-v1");
        """))
    check("password fields stay excluded and rich-text checker remains usable",excluded_private)

    def revoke():
        driver.switch_to.window(dashboard)
        driver.find_element(By.ID,"integration-revoke").click()
        WebDriverWait(driver,18).until(lambda d:permission() is False)
        WebDriverWait(driver,18).until(lambda d:not registrations())
        ensure(modes()=={"spellMode":"sites"},
            "Revoke must restore limited modes")
        driver.switch_to.window(site)
        WebDriverWait(driver,18).until(lambda d:d.execute_script("""
            const e=document.getElementById("qa-integration-editor");
            return !document.getElementById("elfshell-global-cursors-v1") &&
                e?.getAttribute("spellcheck")==="true" &&
                !CSS.highlights?.has("elfshell-spelling-errors-v1");
        """))
        ensure(driver.find_element(By.ID,"qa-integration-editor").text=="This is a mispeled sentance.",
            "Revocation must not alter editor contents")
    check("Revoke removes broad access and restores Firefox spelling",revoke)
    record["status"]="PASS"
except Exception as error:
    record["status"]="FAIL"
    record["error"]=str(error)
    record["traceback"]=traceback.format_exc()
    print("FAIL:",error,flush=True)
finally:
    if driver:
        try:driver.save_screenshot(str(OUTPUT/"integration.png"))
        except Exception as error:record["screenshotError"]=str(error)
        try:driver.quit()
        except Exception:pass
    (OUTPUT/"report.json").write_text(json.dumps(record,indent=2),encoding="utf-8")
    print("REPORT:",json.dumps(record)[:14000],flush=True)
sys.exit(0 if record.get("status")=="PASS" else 1)