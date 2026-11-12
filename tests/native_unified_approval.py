#!/usr/bin/env python3
"""Real Firefox user-gesture permission prompts for the unified Ayarime preview.

No Google account, OAuth, provider keys, or model inference are involved.
This runs with a new temporary Firefox profile and an unsigned add-on.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import time
import traceback
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.support.ui import WebDriverWait

ROOT=Path(__file__).resolve().parents[1]
XPI=ROOT/"dist"/"ELF-SHELL-Ayarime-unified-UNSIGNED.xpi"
REPORTS=ROOT/"dist"/"native-approval"
REPORTS.mkdir(parents=True,exist_ok=True)
results={"suite":"Actual Firefox optional permissions accept/deny for unified Ayarime",
         "checks":[]}
driver=None

def require(ok, message):
    if not ok:raise AssertionError(message)

def check(name,fn):
    fn()
    results["checks"].append({"name":name,"status":"PASS"})
    print("PASS:",name,flush=True)

def ext_call(script,*args):
    return driver.execute_async_script(script,*args)

def granted(name):
    return ext_call("""
      const done=arguments[arguments.length-1];
      browser.permissions.contains({permissions:[arguments[0]]})
        .then(done,error=>done({error:String(error)}));
    """,name)

def window_tabs():
    return ext_call("""
      const done=arguments[arguments.length-1];
      browser.tabs.query({}).then(
        tabs=>done(tabs.map(tab=>({id:tab.id,url:tab.url||"",pinned:tab.pinned}))),
        error=>done({error:String(error)}));
    """)

def launch_from_station():
    menu=driver.find_element(By.ID,"station-menu")
    if not menu.get_property("open"):
        menu.find_element(By.CSS_SELECTOR,"summary").click()
    WebDriverWait(driver,8).until(
        lambda d:d.find_element(By.ID,"ask-ayarime-toggle").is_displayed())
    # Real Selenium click, not synthetic JS dispatch: triggers an actual Firefox
    # user gesture for permissions.request().
    driver.find_element(By.ID,"ask-ayarime-toggle").click()

def popup_details():
    with driver.context(driver.CONTEXT_CHROME):
        return driver.execute_script("""
          const panel=window.PopupNotifications?.panel ||
            document.getElementById("notification-popup");
          const notice=document.getElementById(
            "addon-webext-permissions-notification");
          return {
            panelState:panel?.state||"",
            note:!!notice,
            visible:!!notice&&!notice.hidden,
            primary:!!notice?.querySelector(".popup-notification-primary-button"),
            secondary:!!notice?.querySelector(".popup-notification-secondary-button"),
            openPanels:[...document.querySelectorAll("panel")]
              .filter(p=>p.state==="open").map(p=>p.id).slice(0,10)
          };
        """)

def respond_to_permission(approve):
    def ready(_):
        info=popup_details()
        return info["visible"] and info["primary"] and info["secondary"]
    try:
        WebDriverWait(driver,12).until(ready)
    except Exception:
        # Only UI identifiers, not permission contents or browser profile data.
        print("PERMISSION_UI_DIAGNOSTIC:",json.dumps(popup_details()),flush=True)
        raise
    with driver.context(driver.CONTEXT_CHROME):
        selector=(".popup-notification-primary-button" if approve else
                  ".popup-notification-secondary-button")
        control=driver.find_element(By.CSS_SELECTOR,
          "#addon-webext-permissions-notification "+selector)
        control.click()

try:
    require(XPI.is_file(),"Unsigned preview XPI not found")
    options=webdriver.FirefoxOptions()
    options.add_argument("-headless")
    if os.environ.get("FIREFOX_BINARY"):
        options.binary_location=os.environ["FIREFOX_BINARY"]
    options.set_preference("browser.shell.checkDefaultBrowser",False)
    options.set_preference("browser.startup.homepage","about:blank")
    driver=webdriver.Firefox(options=options,service=FirefoxService(
        service_args=["--allow-system-access"]))
    driver.set_page_load_timeout(25)
    driver.set_script_timeout(25)
    driver.set_window_size(1366,900)
    installed=driver.install_web_extension(str(XPI),permanent=False).id
    check("one native add-on retains ELF//SHELL identity",
          lambda:require(installed=="elf-shell-ayarime@local.theme",installed))
    initial=set(driver.window_handles)
    with driver.context(driver.CONTEXT_CHROME):
        driver.execute_script("window.BrowserCommands.openTab();")
    WebDriverWait(driver,15).until(
        lambda d:len(set(d.window_handles)-initial)==1)
    dashboard=next(iter(set(driver.window_handles)-initial))
    driver.switch_to.window(dashboard)
    WebDriverWait(driver,15).until(
        lambda d:len(d.find_elements(By.ID,"ask-ayarime-toggle"))==1)
    check("initially no tabs permission",
          lambda:require(granted("tabs") is False,"Unexpected tab access already granted"))
    before=window_tabs()
    require(isinstance(before,list),"Unable to inspect initial browser tabs")
    hub_url=driver.execute_script('return browser.runtime.getURL("hub.html")')

    # First user gesture: explicit denial must not silently create Hub.
    launch_from_station()
    respond_to_permission(False)
    WebDriverWait(driver,12).until(
        lambda d:"declined" in
        d.find_element(By.ID,"workspace-bridge-status").text.lower())
    check("real Firefox denial leaves tab access ungranted",
          lambda:require(granted("tabs") is False,"Denied tabs became granted"))
    check("real Firefox denial creates no Hub or Google tabs",
          lambda:require({t["id"] for t in window_tabs()}==
                         {t["id"] for t in before},
                         "Permission denial changed tab set"))

    # Second user gesture: actual native approval is respected.
    launch_from_station()
    respond_to_permission(True)
    check("native grant is recorded by Firefox",
          lambda:require(granted("tabs") is True,"Tabs still ungranted after Allow"))
    WebDriverWait(driver,18).until(
        lambda d:"ai console ready" in
        d.find_element(By.ID,"workspace-bridge-status").text.lower())
    check("Ask Ayarime reaches the integrated Hub after approval",
          lambda:require(
            sum(1 for tab in window_tabs()
                if tab["url"].split("#")[0]==hub_url and tab["pinned"])==1,
            "Pinned Hub was not created or reused"))
    check("Ask Ayarime does not restore Google tabs or request tabGroups",
          lambda:require(
            granted("tabGroups") is False and
            not any("docs.google.com" in tab["url"] or
                    "mail.google.com" in tab["url"] for tab in window_tabs()),
            "Ask Ayarime unexpectedly used Google or tabGroups"))

    # With the original permission still granted, another click reuses one Hub.
    initial_ids={tab["id"] for tab in window_tabs()}
    driver.switch_to.window(dashboard)
    launch_from_station()
    WebDriverWait(driver,15).until(lambda d:
        "ai console ready" in
        d.find_element(By.ID,"workspace-bridge-status").text.lower())
    check("repeat launch reuses Hub without extra windows or permissions",
          lambda:require(
             {tab["id"] for tab in window_tabs()}==initial_ids,
             "Repeat Ask Ayarime created duplicate tabs"))

    results["status"]="PASS"
    driver.save_screenshot(str(REPORTS/"approval-flow.png"))
except Exception as exc:
    results["status"]="FAIL"
    results["error"]=str(exc)
    results["traceback"]=traceback.format_exc()
    print("FAIL:",str(exc),file=sys.stderr,flush=True)
    if driver:
        try:driver.save_screenshot(str(REPORTS/"failure.png"))
        except Exception:pass
finally:
    (REPORTS/"report.json").write_text(json.dumps(results,indent=2),encoding="utf-8")
    if driver:driver.quit()
if results["status"]!="PASS":
    raise SystemExit(1)
