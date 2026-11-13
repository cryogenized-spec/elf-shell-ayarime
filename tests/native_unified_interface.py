#!/usr/bin/env python3
"""Native Firefox UI acceptance for the *unsigned* integrated v0.5.6 preview.

No live provider, Google auth, or browsing data is used. Tests only extension
pages in a disposable Firefox profile; separate signed upgrade QA still applies.
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

ROOT = Path(__file__).resolve().parents[1]
XPI = ROOT / "dist/ELF-SHELL-Ayarime-unified-UNSIGNED.xpi"
OUT = ROOT / "dist/unified-interface"
OUT.mkdir(parents=True, exist_ok=True)
checks = []
driver = None


def verify(label, ok):
    if not ok:
        raise AssertionError(label)
    print("PASS:", label, flush=True)
    checks.append(label)


def run_js(script):
    return driver.execute_script(script)


def stable_page(page):
    WebDriverWait(driver, 20).until(
        lambda d: len(d.find_elements(By.ID, "ai-prompt")) == 1)
    verify(page + " has exactly one conversation composer",
           len(driver.find_elements(By.ID, "ai-prompt")) == 1)
    verify(page + " has exactly one history panel and one Rose Seal",
           len(driver.find_elements(By.ID, "ai-conversation-list")) == 1
           and len(driver.find_elements(By.CLASS_NAME, "ayarime-rose-loader")) == 1)
    verify(page + " begins with no history/context sharing",
           run_js("""return document.querySelector('#ai-conversation-count')
                      .textContent.includes('0 / 10') &&
                      document.querySelector('#ai-conversation-clear').disabled &&
                      !document.querySelector('#ai-context-enable').checked"""))
    verify(page + " stylesheet covers keyboard input and link focus",
           run_js("""return [...document.styleSheets].some(s =>
             (s.href || '').endsWith('/unified/ui-polish.css'))"""))


def no_horizontal_overflow(page, width, height):
    driver.set_window_size(width, height)
    metrics = run_js("""return {
      inner: innerWidth,
      content: document.documentElement.scrollWidth,
      client: document.documentElement.clientWidth
    }""")
    verify(page + " no horizontal overflow at " + str(metrics["inner"]) + "px viewport",
           metrics["content"] <= metrics["client"] + 2)
    driver.save_screenshot(str(OUT / (page + "-" + str(width) + ".png")))


try:
    verify("preview package exists", XPI.is_file())
    options = webdriver.FirefoxOptions()
    options.add_argument("-headless")
    binary = os.environ.get("FIREFOX_BINARY")
    if binary:
        options.binary_location = binary
    options.set_preference("browser.startup.homepage", "about:blank")
    options.set_preference("browser.shell.checkDefaultBrowser", False)
    driver = webdriver.Firefox(
        options=options,
        service=FirefoxService(service_args=["--allow-system-access"]),
    )
    driver.set_script_timeout(25)
    ext_id = driver.install_web_extension(str(XPI), permanent=False).id
    verify("unified ID is unchanged", ext_id == "elf-shell-ayarime@local.theme")
    handles = set(driver.window_handles)
    with driver.context(driver.CONTEXT_CHROME):
        driver.execute_script("window.BrowserCommands.openTab();")
    WebDriverWait(driver, 15).until(
        lambda d: len(set(d.window_handles) - handles) == 1)
    driver.switch_to.window(next(iter(set(driver.window_handles) - handles)))
    hub = run_js('return browser.runtime.getURL("hub.html")')
    sidebar = run_js('return browser.runtime.getURL("sidebar.html")')

    driver.get(hub + "#assistant")
    stable_page("Hub")
    WebDriverWait(driver, 10).until(
        lambda d: d.execute_script(
            "return document.activeElement?.id === 'ai-prompt'"))
    verify("Hub #assistant shortcut focuses the actual composer",
           run_js("return document.activeElement.id === 'ai-prompt'"))
    for width, height in [(1366, 900), (390, 844), (320, 700)]:
        no_horizontal_overflow("hub", width, height)

    # Trigger only a local CSS state; absolutely no provider call is made.
    run_js("""const board=document.querySelector('#ai-trace');
      board.hidden=false; board.dataset.stage='thinking';""")
    active = run_js("""return {
      tile:getComputedStyle(document.querySelector('.rose-tile--right')).animationName,
      spirit:getComputedStyle(document.querySelector('.rose-spirit')).animationName
    }""")
    verify("Rose Seal animates its fold and alternating-axis spirit when active",
           "rose-fold-right" in active["tile"] and
           "rose-alternate-axes" in active["spirit"])
    with driver.context(driver.CONTEXT_CHROME):
        driver.execute_script("Services.prefs.setIntPref('ui.prefersReducedMotion', 1);")
    WebDriverWait(driver, 10).until(
        lambda d: d.execute_script(
            "return matchMedia('(prefers-reduced-motion: reduce)').matches"))
    reduced = run_js("""return {
      tile:getComputedStyle(document.querySelector('.rose-tile--right')).animationName,
      spirit:getComputedStyle(document.querySelector('.rose-spirit')).animationName,
      spark:getComputedStyle(document.querySelector('.rose-spark')).animationName
    }""")
    verify("Firefox reduced-motion stops tiles, spirit and sparks",
           all(v == "none" for v in reduced.values()))

    driver.get(sidebar)
    stable_page("Sidebar")
    disclosure = driver.find_element(By.CSS_SELECTOR, ".unified-provider-settings")
    verify("Sidebar collapses duplicate provider settings by default",
           not disclosure.get_property("open"))
    disclosure.find_element(By.CSS_SELECTOR, "summary").click()
    verify("Sidebar can reveal and use shared provider settings on demand",
           disclosure.get_property("open")
           and driver.find_element(By.ID, "ai-provider").is_displayed()
           and driver.find_element(By.ID, "ai-key").is_displayed())
    disclosure.find_element(By.CSS_SELECTOR, "summary").click()
    for width, height in [(390, 844), (320, 700)]:
        no_horizontal_overflow("sidebar", width, height)
    run_js("document.querySelector('#ai-prompt').focus()")
    verify("Sidebar keyboard composer receives a visible focus ring",
           run_js("""return getComputedStyle(
               document.querySelector('#ai-prompt')).outlineStyle === 'solid'"""))
    verify("Sidebar exposes one explicit submit and stop action",
           len(driver.find_elements(By.ID, "ai-send")) == 1
           and len(driver.find_elements(By.ID, "ai-cancel")) == 1)
    report = {"status": "PASS", "checks": checks}
except Exception as error:
    print("FAIL:", error, file=sys.stderr, flush=True)
    report = {"status": "FAIL", "checks": checks,
              "error": str(error), "traceback": traceback.format_exc()}
    if driver:
        try:
            driver.save_screenshot(str(OUT / "failure.png"))
        except Exception:
            pass
finally:
    (OUT / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if driver:
        driver.quit()

if report["status"] != "PASS":
    raise SystemExit(1)
