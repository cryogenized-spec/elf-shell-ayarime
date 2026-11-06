#!/usr/bin/env python3
"""Genuine Firefox per-site spelling consent from a persistent extension tab.

Temporary add-on in an isolated, disposable headless Firefox profile.
Does not touch user tabs, browser settings, files or accounts.
"""
from __future__ import annotations
import json,os,sys,traceback
from pathlib import Path
from urllib.parse import quote
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.support.ui import WebDriverWait

ROOT=Path(__file__).resolve().parent.parent
PACKAGE=ROOT/"dist"/("ELF-SHELL-Ayarime-v"+
  json.loads((ROOT/"manifest.json").read_text())["version"]+"-AMO.zip")
OUT=ROOT/"dist"/"firefox-spell-popup-qa"
OUT.mkdir(exist_ok=True,parents=True)
report={"scope":"Persistent spelling manager Deny/Allow, injection, Disable, native fallback","checks":[]}
driver=None
def ensure(value,message):
    if not value:raise AssertionError(message)
def check(name,func):
    func();report["checks"].append({"name":name,"status":"PASS"});print("PASS:",name,flush=True)
def api(source):
    response=driver.execute_async_script(
      "const done=arguments[arguments.length-1];Promise.resolve().then(async()=>{"+
      source+"}).then(done,error=>done({__error:String(error)}));")
    ensure(not(isinstance(response,dict) and "__error" in response),str(response))
    return response
def grant():
    return api('return browser.permissions.contains({origins:["https://example.com/*"]});')
def scripts():
    return api('return (await browser.scripting.getRegisteredContentScripts()).map(s=>s.id);')
def prompt(choice):
    with driver.context(driver.CONTEXT_CHROME):
        WebDriverWait(driver,12).until(lambda d:d.execute_script("""
          const p=document.getElementById("notification-popup");
          const n=document.getElementById("addon-webext-permissions-notification");
          return ["showing","open"].includes(p?.state)&&n&&!n.hidden&&
             (n.textContent||"").includes("example.com");
        """))
        target=driver.find_element(By.CSS_SELECTOR,
            "#addon-webext-permissions-notification .popup-notification-"+(
              "primary" if choice=="allow" else "secondary")+"-button")
        ensure(target.get_attribute("label")==("Allow" if choice=="allow" else "Deny"),
            "Unexpected Firefox native permission button")
        ActionChains(driver).move_to_element(target).click().perform()
try:
    ensure(PACKAGE.is_file(),"Extension ZIP missing")
    opts=webdriver.FirefoxOptions()
    opts.add_argument("-headless")
    if os.environ.get("FIREFOX_BINARY"):opts.binary_location=os.environ["FIREFOX_BINARY"]
    opts.set_preference("browser.shell.checkDefaultBrowser",False)
    driver=webdriver.Firefox(options=opts,
        service=FirefoxService(service_args=["--allow-system-access"]))
    driver.set_page_load_timeout(25);driver.set_script_timeout(30)
    driver.set_window_size(1340,850)
    report["firefox"]=driver.capabilities.get("browserVersion")
    report["addonId"]=driver.install_addon(str(PACKAGE),temporary=True)
    old=set(driver.window_handles)
    with driver.context(driver.CONTEXT_CHROME):
        driver.execute_script("window.BrowserCommands.openTab();")
    WebDriverWait(driver,15).until(lambda d:len(set(d.window_handles)-old)==1)
    dashboard=next(iter(set(driver.window_handles)-old))
    driver.switch_to.window(dashboard)
    WebDriverWait(driver,15).until(lambda d:d.current_url.startswith("moz-extension://") and
         d.find_elements(By.ID,"integration-spelling"))
    info=api("""
       const tab=await browser.tabs.create({url:"https://example.com/"});
       return {id:tab.id,manager:browser.runtime.getURL("spelling/popup.html")};
    """)
    WebDriverWait(driver,15).until(lambda d:len(driver.window_handles)>=3)
    site=next(x for x in driver.window_handles if x not in old|{dashboard})
    driver.switch_to.window(site)
    WebDriverWait(driver,20).until(lambda d:d.current_url.startswith("https://example.com/"))
    driver.execute_script("""
      const div=document.createElement("div");div.id="test-editor";
      div.contentEditable="true";div.spellcheck=true;
      div.style.cssText="font:24px sans-serif;min-height:80px;padding:16px;border:1px solid #777";
      document.body.prepend(div);
    """)
    driver.switch_to.window(dashboard)
    url=info["manager"]+"?target="+str(info["id"])+"&site="+quote("https://example.com",safe="")
    driver.switch_to.new_window("tab")
    driver.get(url)
    WebDriverWait(driver,12).until(lambda d:
        d.find_element(By.ID,"toggle").is_enabled() and
        "ENABLE SPELLING" in d.find_element(By.ID,"toggle").text)
    manager=driver.current_window_handle

    def before():
        ensure(grant() is False,"No site grant should exist at first launch")
        ensure(not scripts(),"No spelling registration before consent")
        ensure("This page stays open" in driver.find_element(By.ID,"status").text,
               "Permission prompt must live on persistent extension page")
    check("persistent spelling manager shows before permission",before)

    def deny():
        driver.find_element(By.ID,"toggle").click()
        prompt("deny")
        WebDriverWait(driver,12).until(lambda d:
            "declined" in d.find_element(By.ID,"status").text.lower())
        ensure(grant() is False,"Firefox Deny must not grant the origin")
        ensure(not scripts(),"Firefox Deny must not register content scripts")
        ensure(driver.current_url==url,"The extension manager page must stay open")
    check("native Firefox Deny preserves site isolation and manager page",deny)

    def allow():
        driver.find_element(By.ID,"toggle").click()
        prompt("allow")
        WebDriverWait(driver,15).until(lambda d:grant() is True)
        WebDriverWait(driver,15).until(lambda d:any(x.startswith("elfspell-") for x in scripts()))
        try:
            WebDriverWait(driver,12).until(lambda d:
                "DISABLE SPELLING" in d.find_element(By.ID,"toggle").text)
        except Exception as error:
            raise AssertionError("Site manager did not finish enabling: button="+
               repr(driver.find_element(By.ID,"toggle").text)+
               " status="+repr(driver.find_element(By.ID,"status").text)) from error
        ensure(driver.current_url==url,"Permission prompt must not close manager page")
    check("native Firefox Allow registers the site script from real click",allow)

    def inspect():
        driver.switch_to.window(site)
        editor=driver.find_element(By.ID,"test-editor")
        editor.click();editor.send_keys("This is a mispeled sentance.")
        WebDriverWait(driver,22).until(lambda d:d.execute_script("""
          const e=document.getElementById("test-editor");
          return e?.getAttribute("spellcheck")==="false" &&
            CSS.highlights?.get("elfshell-spelling-errors-v1")?.size>=2;
        """))
        ensure(editor.text=="This is a mispeled sentance.",
          "Spellcheck must never silently modify typed words")
        driver.switch_to.window(manager)
    check("site manager activated actual Firefox offline highlighting",inspect)

    def disable():
        driver.find_element(By.ID,"toggle").click()
        WebDriverWait(driver,12).until(lambda d:
            not any(x.startswith("elfspell-") for x in scripts()))
        ensure(grant() is True,"Do not revoke an origin another RSS feature may need")
        driver.switch_to.window(site)
        WebDriverWait(driver,15).until(lambda d:d.execute_script("""
          const e=document.getElementById("test-editor");
          return e?.getAttribute("spellcheck")==="true" &&
            !CSS.highlights?.has("elfshell-spelling-errors-v1");
        """))
        ensure(driver.find_element(By.ID,"test-editor").text=="This is a mispeled sentance.",
               "Disabling custom spelling must preserve editor text")
    check("Disable unregisters spelling, restores Firefox checker, retains shared host grant",disable)
    report["status"]="PASS"
except Exception as error:
    report["status"]="FAIL";report["error"]=str(error)
    report["traceback"]=traceback.format_exc()
    print("FAIL:",error,flush=True)
finally:
    if driver:
        try:driver.save_screenshot(str(OUT/"manager.png"))
        except Exception:pass
        try:driver.quit()
        except Exception:pass
    (OUT/"report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print("REPORT:",json.dumps(report)[:10000],flush=True)
sys.exit(0 if report.get("status")=="PASS" else 1)
