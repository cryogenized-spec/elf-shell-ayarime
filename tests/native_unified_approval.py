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

def launch_from_sidebar():
    # Model a user returning to a normal tab before bringing up the
    # native sidebar again. When the Hub itself is foreground the sidebar is
    # deliberately passive, so its Hub launcher is correctly hidden.
    driver.switch_to.window(dashboard)
    sidebar=driver.execute_script('return browser.runtime.getURL("sidebar.html")')
    driver.get(sidebar)
    driver.execute_async_script("""
      const done=arguments[arguments.length-1];
      browser.tabs.getCurrent()
        .then(tab=>browser.tabs.update(tab.id,{active:true}))
        .then(()=>done(true),error=>done({error:String(error)}));
    """)
    def sidebar_owns_chat(_):
        probe=ext_call("""
          const done=arguments[arguments.length-1];
          browser.runtime.sendMessage({type:"UI_SURFACE_STATUS"})
            .then(done,error=>done({ok:false,error:String(error)}));
        """)
        return probe.get("ok") is True and probe.get("hubActive") is False and (
            driver.find_element(By.ID,"ayarime-open-workspace").is_displayed())
    try:
        WebDriverWait(driver,12,poll_frequency=.1).until(sidebar_owns_chat)
    except Exception:
        status=ext_call("""
          const done=arguments[arguments.length-1];
          browser.runtime.sendMessage({type:"UI_SURFACE_STATUS"})
            .then(done,error=>done({ok:false,error:String(error)}));
        """)
        view=driver.execute_script("""
          const button=document.getElementById("ayarime-open-workspace");
          return {passive:document.body.classList.contains("hub-foreground"),
            buttonVisible:!!button && getComputedStyle(button).display!=="none",
            status:document.getElementById("ayarime-passive-surface")?.textContent||""};
        """)
        tabs=window_tabs()
        print("SIDEBAR_HANDOFF_DIAGNOSTIC:",json.dumps({
            "background":status,"view":view,
            "tabs":[{"kind":("hub" if t.get("url","").split("#")[0].endswith("/hub.html")
                       else "sidebar" if t.get("url","").split("#")[0].endswith("/sidebar.html")
                       else "other"),"id":t.get("id"),"pinned":t.get("pinned")}
                      for t in tabs]
        }),flush=True)
        raise
    driver.find_element(By.ID,"ayarime-open-workspace").click()


def pause_ai_from_station():
    # After a Hub handoff the Selenium tab contains sidebar.html; explicitly
    # return to the Station page to inspect its legacy passive state marker.
    home=driver.execute_script('return browser.runtime.getURL("newtab.html")')
    sidebar=driver.execute_script('return browser.runtime.getURL("sidebar.html")')
    driver.get(sidebar)
    driver.execute_async_script("""
      const done=arguments[arguments.length-1];
      browser.tabs.getCurrent()
        .then(tab=>browser.tabs.update(tab.id,{active:true}))
        .then(()=>done(true),error=>done({error:String(error)}));
    """)
    WebDriverWait(driver,12).until(lambda d:
        d.find_element(By.ID,"ayarime-sidebar-tab-settings").is_displayed())
    driver.find_element(By.ID,"ayarime-sidebar-tab-settings").click()
    WebDriverWait(driver,12).until(lambda d:
        d.find_element(By.ID,"unified-ai-pause").is_displayed())
    driver.find_element(By.ID,"unified-ai-pause").click()
    driver.get(home)


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
    # Firefox's PopupNotifications may ignore click events during its
    # initial anti-clickjacking delay, even after the visible buttons exist.
    # Give the *actual browser notification* time to become interactive:
    # this is not a forged permission response or a mocked browser API.
    time.sleep(1.4)
    info=popup_details()
    require(info["visible"] and info["primary"] and info["secondary"],
            "Firefox permission prompt disappeared before a choice was made")
    with driver.context(driver.CONTEXT_CHROME):
        selector=(".popup-notification-primary-button" if approve else
                  ".popup-notification-secondary-button")
        result=driver.execute_script("""
          const control=document.querySelector(
            "#addon-webext-permissions-notification "+arguments[0]);
          if(!control)return "missing";
          // Firefox's moz-button is a web component; Marionette's native
          // scroll-and-click cannot reach the hidden internal button.
          const inner=control.shadowRoot?.querySelector("button");
          (inner||control).click();
          return "clicked";
        """,selector)
        require(result=="clicked","Permission prompt choice unavailable: "+str(result))

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
    WebDriverWait(driver,8).until(
        lambda d:d.find_element(By.ID,"ai-module-toggle").is_enabled())
    before_optin=window_tabs()
    require(isinstance(before_optin,list),"Could not inspect tabs before usage")
    check("AI sidebar available by default without browser tab permission",
          lambda:require(
            driver.find_element(By.ID,"ai-module-toggle").get_attribute("aria-pressed")=="true"
            and granted("tabs") is False
            and {tab["id"] for tab in window_tabs()}==
              {tab["id"] for tab in before_optin},
            "AI readiness must not automatically access browser tabs"))

    before=window_tabs()
    require(isinstance(before,list),"Unable to inspect initial browser tabs")
    hub_url=driver.execute_script('return browser.runtime.getURL("hub.html")')

    # The only Hub entry is the native-sidebar header. It must not require
    # unrelated tabs/tabGroups grants, create Google tabs or duplicate Hub tabs.
    launch_from_sidebar()
    WebDriverWait(driver,18,poll_frequency=.15).until(
        lambda _:sum(1 for tab in window_tabs()
            if tab["url"].split("#")[0]==hub_url and tab["pinned"])==1)
    check("sidebar header opens one canonical pinned Hub",
          lambda:require(
            sum(1 for tab in window_tabs()
                if tab["url"].split("#")[0]==hub_url and tab["pinned"])==1,
            "Canonical Hub was not created"))
    check("Hub handoff requires no unrelated Firefox tab or Google grants",
          lambda:require(
            not granted("tabs") and not granted("tabGroups") and
            not any("docs.google.com" in tab["url"] or
                    "mail.google.com" in tab["url"] for tab in window_tabs()),
            "Hub handoff requested unrelated privileges"))

    initial_ids={tab["id"] for tab in window_tabs()}
    launch_from_sidebar()
    try:
        WebDriverWait(driver,12,poll_frequency=.1).until(lambda _:sum(
            1 for tab in window_tabs()
            if tab["url"].split("#")[0]==hub_url and tab["pinned"])==1)
    except Exception:
        current=window_tabs()
        print("CANONICAL_HUB_REUSE_DIAGNOSTIC:",json.dumps({
            "pages":[{"name":("hub" if tab.get("url","").split("#")[0]==hub_url
                else "sidebar" if tab.get("url","").split("#")[0].endswith("/sidebar.html")
                else "other"),
                "id":tab["id"],"pinned":tab["pinned"]} for tab in current],
            "sidebarError":driver.execute_script(
                'return document.getElementById("ayarime-workspace-handoff-status")?.textContent||""'),
            "sidebarPassive":driver.execute_script(
                'return document.body.classList.contains("hub-foreground")')
        }),flush=True)
        raise
    check("reopening the full Workspace reuses the exact Hub tab",
          lambda:require(
            {tab["id"] for tab in window_tabs()}==initial_ids,
            "A second Hub tab was created"))

    # Switching the AI module off does not revoke unrelated browser
    # permissions or alter existing tabs, but it must block any *new* AI launch.
    driver.switch_to.window(dashboard)
    pause_ai_from_station()
    WebDriverWait(driver,8).until(lambda d:
        d.find_element(By.ID,"ai-module-toggle").get_attribute("aria-pressed")=="false")
    no_new_ai=ext_call("""
      const done=arguments[arguments.length-1];
      browser.runtime.sendMessage({type:"AI_STATUS"})
        .then(done,error=>done({ok:false,error:String(error)}));
    """)
    check("disabling AI blocks provider status even when the Hub exists",
          lambda:require(isinstance(no_new_ai,dict) and
            no_new_ai.get("ok") is False and
            "ayarime is paused" in no_new_ai.get("error","").lower(),
            "Disabling AI did not enforce the background guard"))
    check("turning AI off leaves Firefox permission and existing Hub untouched",
          lambda:require(granted("tabs") is False and
            {tab["id"] for tab in window_tabs()}==initial_ids,
            "Disabling AI unexpectedly revoked tabs or destroyed the Hub"))

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
