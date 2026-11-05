#!/usr/bin/env python3
"""Trace actual optional host permission prompt in disposable Firefox.

No permission is auto-granted. Capture the true Chrome notification controls
before implementing trusted Deny/Allow click assertions.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import sys
import traceback
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.support.ui import WebDriverWait

ROOT = Path(__file__).resolve().parent.parent
VER = json.loads((ROOT/"manifest.json").read_text())["version"]
PACKAGE = ROOT/"dist"/f"ELF-SHELL-Ayarime-v{VER}-AMO.zip"
OUT = ROOT/"dist"/"firefox-permission-qa"
OUT.mkdir(parents=True,exist_ok=True)
result = {"scope":"Actual Firefox host permission prompt; diagnostics only", "checks":[]}
driver = None

def check(name,fn):
    fn()
    result["checks"].append({"name":name,"status":"PASS"})
    print("PASS:",name,flush=True)

def await_api(source):
    return driver.execute_async_script(
        "const done=arguments[arguments.length-1];"
        "Promise.resolve().then(async()=>{" + source +
        "}).then(done,e=>done({error:String(e)}));"
    )

try:
    options=webdriver.FirefoxOptions()
    options.add_argument("-headless")
    if os.environ.get("FIREFOX_BINARY"):options.binary_location=os.environ["FIREFOX_BINARY"]
    options.set_preference("browser.shell.checkDefaultBrowser",False)
    driver=webdriver.Firefox(options=options,
        service=FirefoxService(service_args=["--allow-system-access"]))
    driver.set_window_size(1366,768)
    driver.set_script_timeout(25)
    driver.set_page_load_timeout(20)
    result["firefoxVersion"]=driver.capabilities.get("browserVersion")
    result["addonId"]=driver.install_addon(str(PACKAGE),temporary=True)
    old=set(driver.window_handles)
    with driver.context(driver.CONTEXT_CHROME):
        driver.execute_script("window.BrowserCommands.openTab();")
    WebDriverWait(driver,15).until(lambda d:len(set(d.window_handles)-old)==1)
    driver.switch_to.window(next(iter(set(driver.window_handles)-old)))
    WebDriverWait(driver,15).until(lambda d:d.current_url.startswith("moz-extension://") and
                                  d.find_elements(By.ID,"feed-add-form"))

    def request_from_real_ui():
        driver.find_element(By.ID,"feed-manage").click()
        WebDriverWait(driver,8).until(lambda d:d.find_element(By.ID,"feeds-dialog").get_attribute("open") is not None)
        driver.find_element(By.ID,"feed-url").send_keys("https://github.blog/feed/")
        driver.find_element(By.ID,"feed-label").send_keys("Disposable QA Feed")
        before=await_api('return await browser.permissions.contains({origins:["https://github.blog/*"]});')
        if before is not False: raise AssertionError("Host already permitted without user consent")
        submit=driver.find_element(By.CSS_SELECTOR,"#feed-add-form button[type=submit]")
        submit.click()
        # The user gesture is from the actual add-subscription form, not JS.
        # No synthetic permission grant is issued to the extension.
        with driver.context(driver.CONTEXT_CHROME):
            chrome=driver.execute_script("""
                const panel=document.getElementById("notification-popup");
                const match=document.getElementById("addon-webext-permissions-notification");
                return {
                  panelState:panel?.state||null,
                  permissionsNode:{id:match?.id||null,hidden:match?.hidden??null,
                    text:(match?.textContent||"").trim().slice(0,1200)},
                  buttons:[...document.querySelectorAll(
                    '#notification-popup button, #notification-popup toolbarbutton, popupnotification button'
                  )].filter(x=>x.isConnected).slice(0,50).map(x=>({
                    tag:x.tagName,id:x.id,
                    label:x.getAttribute("label")||x.getAttribute("aria-label"),
                    text:(x.textContent||"").trim().slice(0,150),
                    className:String(x.className),
                    hidden:x.hidden
                  }))
                };
            """)
        result["permissionPrompt"]=chrome
        print("NATIVE FIREFOX PERMISSION PROMPT:",json.dumps(chrome,ensure_ascii=False)[:10000],flush=True)
    check("real subscription form requests Firefox optional host permission",request_from_real_ui)

    result["status"]="PASS"
except Exception as exc:
    result["status"]="FAIL"
    result["error"]=str(exc)
    result["traceback"]=traceback.format_exc()
    print("FAIL:",str(exc),flush=True)
finally:
    if driver:
        try:driver.save_screenshot(str(OUT/"prompt.png"))
        except Exception as exc:result["screenshotError"]=str(exc)
        try:driver.quit()
        except Exception:pass
    (OUT/"report.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print("REPORT:",json.dumps(result,ensure_ascii=False)[:15000],flush=True)
sys.exit(0 if result.get("status")=="PASS" else 1)
