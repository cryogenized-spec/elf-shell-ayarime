#!/usr/bin/env python3
"""Real Firefox acceptance: actual Station browser-wide consent and revocation.
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
record={"scope":"Browser Integration Station user gesture, wildcard Deny/Allow, live existing-tab cursor + spell, revoke","checks":[]}
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
        document.body.prepend(native);
    """)
    driver.switch_to.window(dashboard)

    def initial():
        ensure(permission() is False,"Unexpected all-HTTPS grant")
        ensure(not registrations(),"Unexpected registered content scripts before consent")
        ensure(modes() is None,"Fresh profile must not silently enable integration")
        driver.find_element(By.CSS_SELECTOR,"#station-menu summary").click()
        driver.find_element(By.ID,"settings-toggle").click()
        WebDriverWait(driver,8).until(lambda d:d.find_element(By.ID,"settings-dialog").get_attribute("open") is not None)
        ensure(Select(driver.find_element(By.ID,"integration-cursors")).first_selected_option.get_attribute("value")=="station",
            "Cursor defaults must be station-only")
        ensure(Select(driver.find_element(By.ID,"integration-spelling")).first_selected_option.get_attribute("value")=="sites",
            "Spelling defaults must be per-site")
        Select(driver.find_element(By.ID,"integration-cursors")).select_by_value("all")
        Select(driver.find_element(By.ID,"integration-spelling")).select_by_value("all")
    check("all-site modes are off by default and require explicit user selection",initial)

    def deny():
        driver.find_element(By.ID,"integration-apply").click()
        prompt("deny")
        WebDriverWait(driver,12).until(lambda d:
            "Permission denied" in d.find_element(By.ID,"integration-status").text)
        ensure(permission() is False,"Deny must not grant blanket host access")
        ensure(not registrations(),"Deny must not register any site-wide script")
        ensure(modes() is None,"Deny must not change stored preference")
        ensure(Select(driver.find_element(By.ID,"integration-cursors")).first_selected_option.get_attribute("value")=="all",
            "Denied permission should preserve chosen cursor mode for retry")
        ensure(Select(driver.find_element(By.ID,"integration-spelling")).first_selected_option.get_attribute("value")=="all",
            "Denied permission should preserve chosen spelling mode for retry")
    check("real native Firefox Deny leaves defaults and pages unchanged",deny)

    def allow():
        driver.find_element(By.ID,"integration-apply").click()
        prompt("allow")
        WebDriverWait(driver,18).until(lambda d:permission() is True)
        WebDriverWait(driver,18).until(lambda d:
            modes() and modes().get("cursorMode")=="all" and modes().get("spellMode")=="all")
        WebDriverWait(driver,18).until(lambda d:
            {"elfshell-cursors-global-v1","elfspell-global-v1"}.issubset(
              {x["id"] for x in registrations()}))
        current=registrations()
        ensure(all(x["matches"]==["https://*/*"] for x in current),
            "Unexpected host match scope or per-site registration")
        record["registeredIds"]=[x["id"] for x in current]
    check("native Firefox Allow registers exactly the consented all-HTTPS scripts",allow)

    def existing_tab():
        driver.switch_to.window(site)
        WebDriverWait(driver,20).until(lambda d:d.execute_script("""
            return !!document.getElementById("elfshell-global-cursors-v1");
        """))
        css=driver.execute_script("""
            const style=document.getElementById("elfshell-global-cursors-v1");
            return style?.textContent||"";
        """)
        ensure("moz-extension://" in css and "pointer-48.png" in css,
               "Bundled cursor artwork was not applied to existing tab")
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
    check("existing HTTPS tab gets cursor art and offline spelling with native fallback",existing_tab)

    def revoke():
        driver.switch_to.window(dashboard)
        driver.find_element(By.ID,"integration-revoke").click()
        WebDriverWait(driver,18).until(lambda d:permission() is False)
        WebDriverWait(driver,18).until(lambda d:not registrations())
        ensure(modes()=={"cursorMode":"station","spellMode":"sites"},
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
    check("Revoke removes broad access and restores Firefox cursor/spelling",revoke)
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