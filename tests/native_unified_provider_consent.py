#!/usr/bin/env python3
"""Real Firefox BYOK provider consent / revoke / session-key checks. No API calls.

Uses a disposable profile and synthetic key. It deliberately does NOT test
paid inference or contact the API provider; that is an owner-only acceptance.
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
XPI=ROOT/"dist/ELF-SHELL-Ayarime-v0.5.6-unified-RC-UNSIGNED.xpi"
OUT=ROOT/"dist/native-provider-consent"
OUT.mkdir(parents=True,exist_ok=True)
HOST="https://api.openai.com/*"
DATA=["authenticationInfo","personalCommunications","websiteContent",
      "personallyIdentifyingInfo"]
done=[]
driver=None


def check(label, ok):
    if not ok:
        raise AssertionError(label)
    done.append(label)
    print("PASS:",label,flush=True)


def query(script,*args):
    return driver.execute_async_script(script,*args)


def has_provider():
    return query("""
      const done=arguments[arguments.length-1];
      browser.permissions.contains({
        origins:[arguments[0]],data_collection:arguments[1]
      }).then(done,()=>done(false));
    """,HOST,DATA)


def panel():
    with driver.context(driver.CONTEXT_CHROME):
        return driver.execute_script("""
          const notice=document.getElementById(
            'addon-webext-permissions-notification');
          const popup=window.PopupNotifications?.panel ||
            document.getElementById('notification-popup');
          return {open:popup?.state==='open',visible:!!notice&&!notice.hidden,
            primary:!!notice?.querySelector('.popup-notification-primary-button'),
            secondary:!!notice?.querySelector('.popup-notification-secondary-button')};
        """)


def choose(approve):
    WebDriverWait(driver,15).until(
        lambda _: panel()["visible"] and panel()["primary"] and panel()["secondary"])
    time.sleep(1.4)  # native Firefox permission anti-clickjacking grace period
    with driver.context(driver.CONTEXT_CHROME):
        selector=(".popup-notification-primary-button" if approve else
                  ".popup-notification-secondary-button")
        choice=driver.execute_script("""
          const n=document.querySelector(
            '#addon-webext-permissions-notification '+arguments[0]);
          if(!n)return false;
          (n.shadowRoot?.querySelector('button')||n).click();
          return true;
        """,selector)
    check("real Firefox "+("Allow" if approve else "Deny")+" selection",choice)


try:
    check("unsigned unified RC XPI available",XPI.is_file())
    options=webdriver.FirefoxOptions()
    options.add_argument("-headless")
    if os.environ.get("FIREFOX_BINARY"):
        options.binary_location=os.environ["FIREFOX_BINARY"]
    options.set_preference("browser.shell.checkDefaultBrowser",False)
    options.set_preference("browser.startup.homepage","about:blank")
    driver=webdriver.Firefox(options=options,service=FirefoxService(
        service_args=["--allow-system-access"]))
    driver.set_script_timeout(25)
    driver.set_window_size(1366,900)
    addon=driver.install_web_extension(str(XPI),permanent=False).id
    check("production Firefox ID preserved",addon=="elf-shell-ayarime@local.theme")
    before=set(driver.window_handles)
    with driver.context(driver.CONTEXT_CHROME):
        driver.execute_script("window.BrowserCommands.openTab();")
    WebDriverWait(driver,15).until(lambda d:len(set(d.window_handles)-before)==1)
    driver.switch_to.window(next(iter(set(driver.window_handles)-before)))
    WebDriverWait(driver,15).until(lambda d:
        d.find_element(By.ID,"ai-module-toggle").is_enabled())
    check("fresh profile has no provider host/data consent",has_provider() is False)
    # The user explicitly enables AI in the Station. This action does not
    # grant a provider URL or API key.
    menu=driver.find_element(By.ID,"station-menu")
    if not menu.get_property("open"):
        menu.find_element(By.CSS_SELECTOR,"summary").click()
    driver.find_element(By.ID,"ai-module-toggle").click()
    WebDriverWait(driver,10).until(lambda d:
        d.find_element(By.ID,"ai-module-toggle").get_attribute("aria-pressed")=="true")
    check("AI on still has no provider consent",has_provider() is False)
    hub=driver.execute_script("return browser.runtime.getURL('hub.html')")
    driver.get(hub)
    WebDriverWait(driver,15).until(lambda d:
        len(d.find_elements(By.ID,"ai-grant"))==1)
    driver.find_element(By.ID,"ai-grant").click()
    choose(False)
    WebDriverWait(driver,10).until(lambda _:has_provider() is False)
    check("Deny leaves host and optional data collection ungranted",
          has_provider() is False)
    has_key=query("""
      const done=arguments[arguments.length-1];
      browser.storage.session.get("elfshell.byok.apiKey.v1")
        .then(value=>done(Object.hasOwn(value,"elfshell.byok.apiKey.v1")));
    """)
    check("Deny does not produce a provider API key",has_key is False)
    driver.find_element(By.ID,"ai-grant").click()
    choose(True)
    WebDriverWait(driver,12).until(lambda _:has_provider() is True)
    check("Allow grants exactly user-gesture provider and optional data consent",
          has_provider() is True)
    key_field=driver.find_element(By.ID,"ai-key")
    key_field.send_keys("CI-SENTINEL-NEVER-TRANSMIT")
    driver.find_element(By.ID,"ai-set-key").click()
    WebDriverWait(driver,10).until(lambda d:
        d.find_element(By.ID,"ai-clear-key").is_enabled())
    stored=query("""
      const done=arguments[arguments.length-1];
      Promise.all([
        browser.storage.session.get("elfshell.byok.apiKey.v1"),
        browser.storage.local.get("elfshell.byok.apiKey.v1")
      ]).then(([session,persistent])=>done({
        session:!!session["elfshell.byok.apiKey.v1"],
        persistent:!!persistent["elfshell.byok.apiKey.v1"]
      }),()=>done({session:false,persistent:true}));
    """)
    check("synthetic BYOK key lives in session storage only",
          stored["session"] is True and stored["persistent"] is False)
    driver.find_element(By.ID,"ai-clear-key").click()
    WebDriverWait(driver,10).until(lambda d:
        not d.find_element(By.ID,"ai-clear-key").is_enabled())
    after_clear=query("""
      const done=arguments[arguments.length-1];
      browser.storage.session.get("elfshell.byok.apiKey.v1")
        .then(value=>done(!Object.hasOwn(value,"elfshell.byok.apiKey.v1")));
    """)
    check("Forget session key really removes credential",after_clear is True)
    removed=query("""
      const done=arguments[arguments.length-1];
      browser.permissions.remove({
        origins:[arguments[0]],data_collection:arguments[1]
      }).then(done,()=>done(false));
    """,HOST,DATA)
    check("Firefox permits explicit provider consent revocation",removed is True)
    check("revocation blocks any further provider request",has_provider() is False)
    result={"status":"PASS","checks":done,"real_provider_inference":False}
except Exception as error:
    print("FAIL:",error,file=sys.stderr,flush=True)
    result={"status":"FAIL","checks":done,"error":str(error),
            "traceback":traceback.format_exc()}
    if driver:
        try:driver.save_screenshot(str(OUT/"failure.png"))
        except Exception:pass
finally:
    (OUT/"report.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    if driver:driver.quit()
if result["status"]!="PASS":
    raise SystemExit(1)
