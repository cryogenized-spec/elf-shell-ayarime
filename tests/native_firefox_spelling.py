#!/usr/bin/env python3
"""Real Firefox spelling runtime acceptance in a disposable headless profile.

The real Firefox permission UI grants example.com access. The test registers
the spelling script through extension scripting APIs, not through the toolbar
popup (which Marionette cannot enter), so it does NOT assert the popup UI.
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
from selenium.webdriver.support.ui import WebDriverWait

ROOT=Path(__file__).resolve().parent.parent
VERSION=json.loads((ROOT/"manifest.json").read_text())["version"]
ZIP=ROOT/"dist"/f"ELF-SHELL-Ayarime-v{VERSION}-AMO.zip"
OUT=ROOT/"dist"/"firefox-spelling-qa"
OUT.mkdir(parents=True,exist_ok=True)
res={"scope":"Real Firefox spelling engine registration, native restoration and revocation (not popup UI)","checks":[]}
driver=None

def ensure(condition,message):
    if not condition:raise AssertionError(message)

def check(name,fn):
    fn()
    res["checks"].append({"name":name,"status":"PASS"})
    print("PASS:",name,flush=True)

def ext_async(source):
    value=driver.execute_async_script(
        "const done=arguments[arguments.length-1];"
        "Promise.resolve().then(async()=>{" + source +
        "}).then(done,error=>done({__apiError:String(error)}));"
    )
    ensure(not (isinstance(value,dict) and "__apiError" in value),"Extension API failure: "+str(value))
    return value

try:
    ensure(ZIP.is_file(),"AMO test package is missing")
    options=webdriver.FirefoxOptions()
    options.add_argument("-headless")
    if os.environ.get("FIREFOX_BINARY"):options.binary_location=os.environ["FIREFOX_BINARY"]
    options.set_preference("browser.shell.checkDefaultBrowser",False)
    driver=webdriver.Firefox(options=options,service=FirefoxService(service_args=["--allow-system-access"]))
    driver.set_window_size(1366,768)
    driver.set_page_load_timeout(25)
    driver.set_script_timeout(25)
    res["browserVersion"]=driver.capabilities.get("browserVersion")
    res["addonId"]=driver.install_addon(str(ZIP),temporary=True)

    old=set(driver.window_handles)
    with driver.context(driver.CONTEXT_CHROME):
        driver.execute_script("window.BrowserCommands.openTab();")
    WebDriverWait(driver,15).until(lambda d:len(set(d.window_handles)-old)==1)
    dashboard=next(iter(set(driver.window_handles)-old))
    driver.switch_to.window(dashboard)
    WebDriverWait(driver,15).until(lambda d:d.current_url.startswith("moz-extension://")
        and d.find_elements(By.ID,"feed-manage"))

    driver.switch_to.new_window("tab")
    site=driver.current_window_handle
    driver.get("https://example.com/")
    ensure(driver.current_url.startswith("https://example.com/"),"Public test site did not load")
    driver.switch_to.window(dashboard)

    def confirm_actual_host_permission():
        original=ext_async('return await browser.permissions.contains({origins:["https://example.com/*"]});')
        ensure(original is False,"Example.com unexpectedly pre-authorized")
        driver.find_element(By.ID,"feed-manage").click()
        WebDriverWait(driver,8).until(lambda d:d.find_element(By.ID,"feeds-dialog").get_attribute("open") is not None)
        driver.find_element(By.ID,"feed-url").send_keys("https://example.com/qa-synthetic-feed")
        driver.find_element(By.CSS_SELECTOR,"#feed-add-form button[type=submit]").click()
        with driver.context(driver.CONTEXT_CHROME):
            WebDriverWait(driver,12).until(lambda d:d.execute_script("""
                const panel=document.getElementById("notification-popup");
                const prompt=document.getElementById("addon-webext-permissions-notification");
                return ["showing","open"].includes(panel?.state) &&
                    !prompt?.hidden && (prompt?.textContent||"").includes("example.com") &&
                    prompt?.button?.getAttribute("label")==="Allow";
            """))
            button=driver.find_element(By.CSS_SELECTOR,
                "#addon-webext-permissions-notification .popup-notification-primary-button")
            ActionChains(driver).move_to_element(button).click().perform()
        WebDriverWait(driver,12).until(lambda d:
            ext_async('return await browser.permissions.contains({origins:["https://example.com/*"]});') is True)
        ensure(ext_async('return (await browser.permissions.getAll()).origins;')==["https://example.com/*"],
               "Unexpected extra host permissions")
    check("real Firefox Allow grants only test-site origin",confirm_actual_host_permission)

    origin="https://example.com"
    registration="elfspell-"+"".join(f"{ord(c):02x}" for c in origin)
    def register_and_inject():
        ensure(ext_async("return await browser.scripting.getRegisteredContentScripts();")==[],
               "Spelling was registered before test activation")
        tabs=ext_async('return (await browser.tabs.query({url:"https://example.com/*"})).map(t=>({id:t.id,url:t.url}));')
        ensure(len(tabs)==1,"Could not identify the authorized test website tab: "+str(tabs))
        tab_id=tabs[0]["id"]
        payload=json.dumps({"id":registration,"matches":["https://example.com/*"],
            "js":["spelling/content.js"],"css":["spelling/content.css"],
            "runAt":"document_idle","persistAcrossSessions":True})
        ext_async("await browser.scripting.registerContentScripts(["+payload+"]); return true;")
        ext_async("await browser.scripting.insertCSS({target:{tabId:"+str(tab_id)+"},files:['spelling/content.css']}); return true;")
        ext_async("await browser.scripting.executeScript({target:{tabId:"+str(tab_id)+"},files:['spelling/content.js']}); return true;")
        current=ext_async("return (await browser.scripting.getRegisteredContentScripts()).map(s=>s.id);")
        ensure(registration in current,"Expected site spelling registration absent")
    check("site-authorized extension script registers and injects in real Firefox",register_and_inject)

    def highlighted_editor():
        driver.switch_to.window(site)
        driver.execute_script("""
            const el=document.createElement("div");
            el.id="qa-rich-editor";
            el.setAttribute("contenteditable","true");
            el.setAttribute("spellcheck","true");
            el.style.cssText="font:24px sans-serif;min-height:80px;padding:16px;width:650px;border:1px solid #777";
            document.body.prepend(el);
        """)
        editor=driver.find_element(By.ID,"qa-rich-editor")
        editor.click()
        editor.send_keys("This is a mispeled sentance.")
        WebDriverWait(driver,25).until(lambda d:d.execute_script("""
            const root=document.getElementById("qa-rich-editor");
            const marked=CSS.highlights?.get("elfshell-spelling-errors-v1");
            return root?.getAttribute("spellcheck")==="false" && marked?.size>=1;
        """))
        highlights=driver.execute_script("""
            return {supported:!!CSS.highlights, exists:!!CSS.highlights?.get("elfshell-spelling-errors-v1"),
                count:CSS.highlights?.get("elfshell-spelling-errors-v1")?.size||0};
        """)
        res["highlights"]=highlights
        ensure(highlights["count"]>=1,"Offline spellchecker did not mark any misspelled words: "+str(highlights))
        ensure("mispeled" in editor.text,"Editor text changed unexpectedly")
    check("offline dictionary marks actual misspellings and takes over eligible rich editor",highlighted_editor)

    original_text="This is a mispeled sentance."
    def correction_and_undo():
        driver.switch_to.window(site)
        editor=driver.find_element(By.ID,"qa-rich-editor")
        geometry=driver.execute_script("""
            const editor=document.getElementById("qa-rich-editor");
            const node=editor.firstChild;
            const index=node.data.indexOf("mispeled");
            if(index<0) throw Error("Misspelled token missing");
            const token=document.createRange();
            token.setStart(node,index); token.setEnd(node,index+8);
            const r=token.getBoundingClientRect(),e=editor.getBoundingClientRect();
            return {dx:r.left+r.width/2-e.left-e.width/2,
                dy:r.top+r.height/2-e.top-e.height/2};
        """)
        ActionChains(driver).move_to_element_with_offset(
            editor,int(geometry["dx"]),int(geometry["dy"])).click().perform()
        WebDriverWait(driver,18).until(lambda d:
            len(d.find_elements(By.CSS_SELECTOR,".elfshell-spell-menu"))==1)
        menu=driver.find_element(By.CSS_SELECTOR,".elfshell-spell-menu")
        ensure("mispeled" in (menu.get_attribute("aria-label") or ""),
               "Wrong spelling suggestion menu opened")
        res["spellMenu"]={"role":menu.get_attribute("role"),
            "ariaLabel":menu.get_attribute("aria-label"),
            "width":menu.rect["width"],"height":menu.rect["height"]}
        ensure(menu.rect["height"]>45,"Spelling menu has no choices")
        # The extension deliberately uses a closed ShadowRoot, which blocks
        # test scripts from reading its buttons. Use a real WebDriver pointer
        # positioned over the first visible suggestion, not a synthetic click.
        ActionChains(driver).move_to_element_with_offset(
            menu,int(32-menu.rect["width"]/2),
            int(22-menu.rect["height"]/2)).click().perform()
        WebDriverWait(driver,10).until(lambda d:
            d.find_element(By.ID,"qa-rich-editor").text!=original_text)
        edited=driver.find_element(By.ID,"qa-rich-editor").text
        res["correctionText"]=edited
        ensure("mispeled" not in edited,
               "The first suggestion did not replace the misspelled token")
        editor.send_keys(Keys.CONTROL,"z")
        WebDriverWait(driver,10).until(lambda d:
            d.find_element(By.ID,"qa-rich-editor").text==original_text)
        res["undoRestored"]=True
    check("trusted spelling suggestion click corrects rich text and native Undo restores it",
          correction_and_undo)

    def revoke_and_restore():
        driver.switch_to.window(dashboard)
        removed=ext_async('return await browser.permissions.remove({origins:["https://example.com/*"]});')
        ensure(removed is True,"Firefox did not revoke site permission")
        WebDriverWait(driver,14).until(lambda d:
            registration not in ext_async("return (await browser.scripting.getRegisteredContentScripts()).map(s=>s.id);"))
        driver.switch_to.window(site)
        WebDriverWait(driver,15).until(lambda d:d.execute_script("""
            return document.getElementById('qa-rich-editor').getAttribute('spellcheck')==="true"
                && !CSS.highlights?.has("elfshell-spelling-errors-v1");
        """))
        ensure(driver.find_element(By.ID,"qa-rich-editor").text=="This is a mispeled sentance.",
               "Revocation disturbed user's editor text")
    check("Firefox permission revocation unregisters script and restores native checker without changing text",revoke_and_restore)
    res["status"]="PASS"
except Exception as exc:
    res["status"]="FAIL"
    res["error"]=str(exc)
    res["traceback"]=traceback.format_exc()
    print("FAIL:",str(exc),flush=True)
finally:
    if driver:
        try:driver.save_screenshot(str(OUT/"spelling-editor.png"))
        except Exception as exc:res["screenshotError"]=str(exc)
        try:driver.quit()
        except Exception:pass
    (OUT/"report.json").write_text(json.dumps(res,ensure_ascii=False,indent=2),encoding="utf-8")
    print("REPORT:",json.dumps(res,ensure_ascii=False)[:13000],flush=True)
sys.exit(0 if res.get("status")=="PASS" else 1)
