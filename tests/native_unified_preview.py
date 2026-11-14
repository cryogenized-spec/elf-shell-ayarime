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

    # The Station should be visible without digging through the old menu.
    opener=driver.find_element(By.ID,"station-drawer-open")
    check("Station control is visible directly on the new tab",
          opener.is_displayed())
    opener.click()
    WebDriverWait(driver,5).until(lambda d:
        d.find_element(By.ID,"station-drawer").is_displayed())
    check("Station drawer opens from the left without a new page",
          len(driver.window_handles)==len(existing_handles)+1 and
          driver.find_element(By.ID,"station-drawer").is_displayed())
    # The drawer deliberately animates in from outside the viewport.
    # Wait for the real tab to reach the screen before Selenium clicks it.
    WebDriverWait(driver,5,poll_frequency=.05).until(
        lambda d:d.execute_script("""
          const r=document.getElementById('station-drawer').getBoundingClientRect();
          return r.left>=-2 && r.right>100;
        """))
    driver.find_element(By.ID,"sd-tab-mcp").click()
    check("MCP tab recommends official Google endpoints by default",
          driver.find_element(By.ID,"sd-provider").get_attribute("value")=="official" and
          "gmailmcp.googleapis.com" in
          driver.find_element(By.ID,"sd-google-url").get_attribute("value"))
    driver.find_element(By.ID,"sd-tab-ayarime").click()
    check("AI controls are directly accessible from the drawer",
          driver.find_element(By.ID,"sd-ai-toggle").is_displayed())
    driver.find_element(By.ID,"station-drawer-close").click()
    check("Station drawer closes and preserves the dashboard",
          not driver.find_element(By.ID,"station-drawer").is_displayed() and
          driver.title=="ELF//SHELL — Ayarime")

    reply=message({"type":"UNIFIED_HELLO",
                   "kind":"elfshell.workspace.bridge","version":1})
    state_probe=message({"type":"GET_STATE"})
    # Only print the response types and booleans, never saved URLs or accounts.
    print("UNIFIED_ROUTER_DIAGNOSTIC:",json.dumps({
      "hello":type(reply).__name__,"hello_ok":isinstance(reply,dict) and reply.get("ok"),
      "state":type(state_probe).__name__,
      "state_ok":isinstance(state_probe,dict) and state_probe.get("ok")
    }),flush=True)
    check("new-tab is authenticated to internal versioned AI bridge",
          isinstance(reply,dict) and reply.get("ok") and reply.get("version")==1 and
          "OPEN_ASSISTANT" in reply.get("capabilities",[]))

    malformed=message({"type":"UNIFIED_OPEN_ASSISTANT","kind":"elfshell.workspace.bridge",
                       "version":99})
    check("internal bridge rejects inference commands",
          malformed.get("ok") is False)

    WebDriverWait(driver,8).until(lambda d:
        d.find_element(By.ID,"ai-module-toggle").is_enabled())
    check("new unified installation leaves AI module disabled by default",
          driver.find_element(By.ID,"ai-module-toggle").get_attribute("aria-pressed")=="false" and
          "AI module off" in driver.find_element(By.ID,"ai-module-status").text)
    blocked_model=message({"type":"AI_STATUS"})
    check("disabled AI module blocks direct provider status requests",
          isinstance(blocked_model,dict) and blocked_model.get("ok") is False and
          "enable ayarime ai" in blocked_model.get("error","").lower())
    blocked_stream=driver.execute_async_script("""
      const done=arguments[arguments.length-1];
      const port=browser.runtime.connect({name:"elfshell.openai.trace.v1"});
      let completed=false;
      port.onMessage.addListener(msg=>{
        if(completed || msg.kind!=="terminal")return;
        completed=true;
        done({status:msg.status,message:msg.message||""});
        port.disconnect();
      });
      port.onDisconnect.addListener(()=>{
        if(!completed){completed=true;done({status:"disconnect"});}
      });
      port.postMessage({type:"start",text:"Do not send this to a provider",
        effort:"medium",webSearch:false,maxOutputTokens:768,
        includeHistory:false,historyLimit:0});
    """)
    check("disabled AI module rejects streaming before any provider request",
          isinstance(blocked_stream,dict) and
          blocked_stream.get("status")=="failed" and
          "enable ayarime ai" in blocked_stream.get("message","").lower())

    # Stage 6.1 is intentionally companion-only: even a same-extension
    # script cannot use an unreviewed Master OAuth route from this RC.
    # These are real Firefox background messages, not static string checks.
    blocked_master=[message({"type":kind}) for kind in (
        "MASTER_STATUS","MASTER_CONNECT","MASTER_PROBE","MASTER_DISCONNECT")]
    check("unified v0.5.6 blocks every experimental Google Master OAuth route",
          all(isinstance(reply,dict) and reply.get("ok") is False and
              "disabled" in reply.get("error","").lower()
              for reply in blocked_master))
    master_login=driver.execute_script("""
      const hub=document.querySelector(".master-panel");
      return hub===null;
    """)
    check("core new-tab does not expose a Master OAuth login",master_login is True)

    # Seed representative existing ELF//SHELL per-field settings, plus an
    # unrelated local key. The AI toggle must not overwrite any of them.
    stored=driver.execute_async_script("""
      const done=arguments[arguments.length-1];
      browser.storage.local.set({
        "elfshell-workspace-v3:field:note":"Existing local archive note",
        "elfshell-workspace-v3:field:focus":"Existing focus line",
        "thirdparty.unchanged.v1":{"value":31}
      }).then(()=>browser.storage.local.get([
        "elfshell-workspace-v3:field:note",
        "elfshell-workspace-v3:field:focus",
        "thirdparty.unchanged.v1"
      ])).then(done,error=>done({error:String(error)}));
    """)
    check("existing ELF//SHELL fields can be staged without changing AI state",
          stored.get("elfshell-workspace-v3:field:note")=="Existing local archive note")
    driver.find_element(By.CSS_SELECTOR,"#station-menu summary").click()
    driver.find_element(By.ID,"ai-module-toggle").click()
    WebDriverWait(driver,8).until(lambda d:
        d.find_element(By.ID,"ai-module-toggle").get_attribute("aria-pressed")=="true")
    check("explicit Station click enables AI independently of tab permissions",
          driver.find_element(By.ID,"ai-module-toggle").get_attribute("aria-pressed")=="true")
    saved=driver.execute_async_script("""
      const done=arguments[arguments.length-1];
      browser.storage.local.get([
        "elfshell.unified.aiEnabled.v1",
        "elfshell-workspace-v3:field:note",
        "elfshell-workspace-v3:field:focus",
        "thirdparty.unchanged.v1"
      ]).then(done,error=>done({error:String(error)}));
    """)
    check("module preference preserves existing field keys and unrelated storage",
          saved.get("elfshell.unified.aiEnabled.v1") is True and
          all(saved.get(k)==v for k,v in stored.items()))
    # Disabling the module must clear even a previously entered session key.
    # A synthetic sentinel avoids any live provider credential or request.
    staged_key=driver.execute_async_script("""
      const done=arguments[arguments.length-1];
      browser.storage.session.set({
        "elfshell.byok.apiKey.v1":{provider:"openai",key:"CI-SENTINEL-DO-NOT-SEND"}
      }).then(()=>done(true),()=>done(false));
    """)
    check("synthetic BYOK key staged only in Firefox session storage",staged_key is True)
    station=driver.find_element(By.ID,"station-menu")
    if not station.get_property("open"):
        station.find_element(By.CSS_SELECTOR,"summary").click()
    driver.find_element(By.ID,"ai-module-toggle").click()
    WebDriverWait(driver,10).until(lambda d:
        d.find_element(By.ID,"ai-module-toggle").get_attribute("aria-pressed")=="false")
    cleared=driver.execute_async_script("""
      const done=arguments[arguments.length-1];
      browser.storage.session.get("elfshell.byok.apiKey.v1")
        .then(v=>done(!Object.hasOwn(v,"elfshell.byok.apiKey.v1")),()=>done(false));
    """)
    check("disabling Ayarime AI removes BYOK key without modifying core settings",cleared is True)
    station=driver.find_element(By.ID,"station-menu")
    if not station.get_property("open"):
        station.find_element(By.CSS_SELECTOR,"summary").click()
    driver.find_element(By.ID,"ai-module-toggle").click()
    WebDriverWait(driver,10).until(lambda d:
        d.find_element(By.ID,"ai-module-toggle").get_attribute("aria-pressed")=="true")
    check("re-enabling AI does not restore a cleared credential",
          driver.execute_async_script("""
            const done=arguments[arguments.length-1];
            browser.storage.session.get("elfshell.byok.apiKey.v1")
              .then(v=>done(!Object.hasOwn(v,"elfshell.byok.apiKey.v1")));
          """) is True)
    check("AI enabled does not grant Firefox tab permissions",
          driver.execute_async_script("""
            const done=arguments[arguments.length-1];
            browser.permissions.contains({permissions:["tabs"]}).then(done);
          """) is False)

    permissions=driver.execute_async_script("""
      const done=arguments[arguments.length-1];
      Promise.all(["tabs","tabGroups"].map(async name=>
        ({name,granted:await browser.permissions.contains({permissions:[name]})})
      )).then(done,error=>done([{error:String(error)}]));
    """)
    check("tabs and tabGroups remain ungranted until user consent",
          len(permissions)==2 and all(item.get("granted") is False for item in permissions))

    # Even a same-extension page cannot open workspaces by sending the
    # internal command directly before the optional grants have been given.
    blocked_ai=message({"type":"UNIFIED_OPEN_ASSISTANT",
                        "kind":"elfshell.workspace.bridge","version":1})
    blocked_workspace=message({"type":"OPEN_WORKSPACE"})
    check("background rejects assistant launch before real tab permission",
          isinstance(blocked_ai,dict) and blocked_ai.get("ok") is False and
          "tab access" in blocked_ai.get("error","").lower())
    check("background rejects workspace restore before tab-group approval",
          isinstance(blocked_workspace,dict) and
          blocked_workspace.get("ok") is False and
          "tab-group access" in blocked_workspace.get("error","").lower())

    # Test the real Station click handler without invoking Firefox's live
    # permission doorhanger: a deterministic temporary page-local stub
    # imitates a denied permission request. This is NOT user grant acceptance.
    stubbed=driver.execute_script("""
      window.__qaOriginalPermissionRequest=browser.permissions.request;
      const deny=()=>Promise.resolve(false);
      browser.permissions.request=deny;
      return browser.permissions.request===deny;
    """)
    check("QA can simulate a declined permission without touching browser grants",stubbed)
    station=driver.find_element(By.ID,"station-menu")
    if not station.get_property("open"):
        station.find_element(By.CSS_SELECTOR,"summary").click()
    driver.find_element(By.ID,"ask-ayarime-toggle").click()
    WebDriverWait(driver,10).until(lambda d:
        "declined" in d.find_element(By.ID,"workspace-bridge-status").text.lower())
    check("Station shows a useful error after declined access",
          "existing tabs are unchanged" in
          driver.find_element(By.ID,"workspace-bridge-status").text.lower())
    driver.execute_script("browser.permissions.request=window.__qaOriginalPermissionRequest;")

    # The dashboard must not be able to bypass the background permission check
    # by falsely reporting that a prompt was approved.
    simulated=driver.execute_script("""
      const allow=()=>Promise.resolve(true);
      browser.permissions.request=allow;
      return browser.permissions.request===allow;
    """)
    check("QA can simulate an optimistic page-local grant",simulated)
    menu=driver.find_element(By.ID,"station-menu")
    if not menu.get_property("open"):
        menu.find_element(By.CSS_SELECTOR,"summary").click()
    WebDriverWait(driver,5).until(lambda d:
        d.find_element(By.ID,"ask-ayarime-toggle").is_displayed())
    driver.find_element(By.ID,"ask-ayarime-toggle").click()
    WebDriverWait(driver,10).until(lambda d:
        "tab access must be granted" in
        d.find_element(By.ID,"workspace-bridge-status").text.lower())
    check("background blocks launch even if the page claims permission was granted",
          "workspace unavailable" in
          driver.find_element(By.ID,"workspace-bridge-status").text.lower())
    driver.execute_script("browser.permissions.request=window.__qaOriginalPermissionRequest;")
    check("simulated grants have not changed Firefox's actual tab permissions",
          all(item.get("granted") is False for item in
          driver.execute_async_script("""
             const done=arguments[arguments.length-1];
             Promise.all(["tabs","tabGroups"].map(async name=>({
               name,granted:await browser.permissions.contains({permissions:[name]})
             }))).then(done);
          """)))

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
    denied=message({"type":"UNIFIED_HELLO",
                   "kind":"elfshell.workspace.bridge","version":1})
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
