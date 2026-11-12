#!/usr/bin/env python3
"""Real Firefox single-extension assembly smoke: no Google OAuth or model inference."""
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

ROOT=Path(__file__).resolve().parents[1]
XPI=ROOT/"dist"/"ELF-SHELL-Ayarime-unified-UNSIGNED.xpi"
REPORTS=ROOT/"dist"/"unified-firefox"
REPORTS.mkdir(parents=True,exist_ok=True)
results={"suite":"Single-addon ELF//SHELL + Workspace AI developer preview","checks":[]}
driver=None

def check(name, predicate):
    if not predicate:
        raise AssertionError(name)
    results["checks"].append({"name":name,"status":"PASS"})
    print("PASS:",name,flush=True)

def message(payload):
    return driver.execute_async_script("""
      const done=arguments[arguments.length-1];
      browser.runtime.sendMessage(arguments[0]).then(done,
        error=>done({ok:false,error:String(error)}));
    """,payload)

try:
    check("unsigned unified XPI exists",XPI.is_file())
    opts=webdriver.FirefoxOptions()
    opts.add_argument("-headless")
    binary=os.environ.get("FIREFOX_BINARY")
    if binary:opts.binary_location=binary
    opts.set_preference("browser.shell.checkDefaultBrowser",False)
    opts.set_preference("browser.startup.homepage","about:blank")
    driver=webdriver.Firefox(options=opts,service=FirefoxService(service_args=["--allow-system-access"]))
    driver.set_script_timeout(25)
    driver.set_page_load_timeout(25)
    driver.set_window_size(1366,900)
    installed=driver.install_web_extension(str(XPI),permanent=False).id
    check("one unified add-on keeps original ELF//SHELL identity",
          installed=="elf-shell-ayarime@local.theme")
    existing_handles=set(driver.window_handles)
    with driver.context(driver.CONTEXT_CHROME):
        uuids=driver.execute_script("""
          const services=typeof Services!=="undefined"?Services:window.Services;
          return JSON.parse(services.prefs.getStringPref("extensions.webextensions.uuids","{}"));
        """)
        driver.execute_script("window.BrowserCommands.openTab();")
    WebDriverWait(driver,15).until(
        lambda d:len(set(d.window_handles)-existing_handles)==1)
    dashboard=next(iter(set(driver.window_handles)-existing_handles))
    driver.switch_to.window(dashboard)
    check("no separate Workspace AI companion installed",
          "workspace-ai@elf-shell.local" not in uuids)
    WebDriverWait(driver,25).until(lambda d:
        len(d.find_elements(By.ID,"search-input"))==1)
    check("original ELF//SHELL new-tab interface survives",
          driver.title=="ELF//SHELL — Ayarime")
    check("Ask Ayarime entry is present in the unified Station",
          len(driver.find_elements(By.ID,"ask-ayarime-toggle"))==1)

    reply=message({"type":"elfshell:unified:bridge:v1",
                   "kind":"elfshell.workspace.bridge","version":1,"command":"HELLO"})
    check("new-tab is authenticated to internal versioned AI bridge",
          reply.get("ok") and reply.get("version")==1 and
          "OPEN_ASSISTANT" in reply.get("capabilities",[]))

    malformed=message({"type":"elfshell:unified:bridge:v1","kind":"elfshell.workspace.bridge",
                       "version":1,"command":"AI_SEND_PROMPT"})
    check("internal bridge rejects inference commands",
          malformed.get("ok") is False)

    permissions=driver.execute_async_script("""
      const done=arguments[arguments.length-1];
      Promise.all(["tabs","tabGroups"].map(async name=>
        ({name,granted:await browser.permissions.contains({permissions:[name]})})
      )).then(done,error=>done([{error:String(error)}]));
    """)
    check("tabs and tabGroups remain ungranted until user consent",
          len(permissions)==2 and all(item.get("granted") is False for item in permissions))

    native=message({"type":"elfshell:telemetry:read:v1"})
    check("core background still owns its telemetry permission boundary",
          native.get("ok") is False and "telemetry" in native.get("error","").lower())

    state=message({"type":"GET_STATE"})
    check("companion background state router operates inside original extension",
          state.get("ok") and len(state.get("resources",[]))>=1)

    hub=driver.execute_script('return browser.runtime.getURL("hub.html")')
    driver.get(hub)
    WebDriverWait(driver,20).until(lambda d:
        len(d.find_elements(By.ID,"ai-prompt"))==1)
    check("Workspace AI Hub works without installing a second add-on",
          len(driver.find_elements(By.ID,"ai-console"))==1 and
          len(driver.find_elements(By.CLASS_NAME,"ayarime-rose-loader"))==1)
    denied=message({"type":"elfshell:unified:bridge:v1",
                   "kind":"elfshell.workspace.bridge","version":1,"command":"HELLO"})
    check("Hub cannot impersonate the dashboard's privileged internal bridge",
          denied.get("ok") is False)

    driver.get(driver.execute_script('return browser.runtime.getURL("sidebar.html")'))
    WebDriverWait(driver,20).until(lambda d:
        len(d.find_elements(By.ID,"ai-prompt"))==1)
    check("native sidebar document is bundled in the same add-on",
          len(driver.find_elements(By.CLASS_NAME,"ayarime-rose-loader"))==1)

    results["status"]="PASS"
    driver.save_screenshot(str(REPORTS/"one-extension.png"))
except Exception as e:
    results["status"]="FAIL"
    results["error"]=str(e)
    results["traceback"]=traceback.format_exc()
    print("FAIL:",e,file=sys.stderr,flush=True)
    if driver:
        try:driver.save_screenshot(str(REPORTS/"failure.png"))
        except Exception:pass
finally:
    (REPORTS/"report.json").write_text(json.dumps(results,indent=2),encoding="utf-8")
    if driver:driver.quit()
if results["status"]!="PASS":
    raise SystemExit(1)
