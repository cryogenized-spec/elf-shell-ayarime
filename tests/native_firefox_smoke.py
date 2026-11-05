#!/usr/bin/env python3
"""Selenium smoke acceptance in *real headless Firefox*, isolated from user data.

This supplements (not replaces) interactive Linux Mint, Firefox permissions,
IME/undo, real RSS, signed upgrade and visual/manual tests.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import sys
import traceback
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

ROOT = Path(__file__).resolve().parent.parent
VERSION = json.loads((ROOT / "manifest.json").read_text())["version"]
PACKAGE = ROOT / "dist" / f"ELF-SHELL-Ayarime-v{VERSION}-AMO.zip"
OUTPUT = ROOT / "dist" / "native-firefox-qa"
OUTPUT.mkdir(exist_ok=True, parents=True)
results = {"tested_by": "Selenium / Firefox (temporary add-on)", "checks": []}
driver = None

def check(name, fn):
    fn()
    results["checks"].append({"name": name, "status": "PASS"})
    print("PASS:", name, flush=True)

def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)

def async_value(source):
    return driver.execute_async_script(
        "const done = arguments[arguments.length - 1];"
        "Promise.resolve().then(async () => { " + source +
        " }).then(done, err => done({__error: String(err)}));"
    )

def storage(key):
    reply = async_value("return (await browser.storage.local.get(arguments[0]))[arguments[0]];".replace("arguments[0]", json.dumps(key)))
    assert_true(not (isinstance(reply, dict) and "__error" in reply), "storage API error: " + str(reply))
    return reply

def new_tab():
    driver.get("about:newtab")
    WebDriverWait(driver, 20).until(
        lambda d: d.current_url.startswith("moz-extension://") and
        len(d.find_elements(By.ID, "search-input")) == 1
    )

try:
    assert_true(PACKAGE.is_file(), "AMO candidate ZIP not available; build first")
    options = webdriver.FirefoxOptions()
    options.add_argument("-headless")
    binary = os.environ.get("FIREFOX_BINARY")
    if binary:
        options.binary_location = binary
    options.set_preference("browser.shell.checkDefaultBrowser", False)
    options.set_preference("app.update.enabled", False)
    options.set_preference("browser.startup.homepage", "about:blank")
    driver = webdriver.Firefox(options=options)
    driver.set_page_load_timeout(25)
    driver.set_script_timeout(20)
    driver.set_window_size(1366, 768)
    results["browserVersion"] = driver.capabilities.get("browserVersion")
    results["browserName"] = driver.capabilities.get("browserName")
    print("Browser:", results["browserName"], results["browserVersion"], flush=True)
    assert_true(int(results["browserVersion"].split(".")[0]) >= 142, "Firefox version is too old")

    addon_id = driver.install_addon(str(PACKAGE), temporary=True)
    results["addonId"] = addon_id
    check("temporary unsigned add-on installation in isolated Firefox", lambda: assert_true(bool(addon_id), "no add-on ID"))

    check("new-tab override and extension origin", lambda: (new_tab(),
        assert_true(driver.title == "ELF//SHELL — Ayarime", "unexpected title: " + repr(driver.title))))
    results["newTabUrl"] = driver.current_url

    def dashboard():
        assert_true(len(driver.find_elements(By.CSS_SELECTOR, "#shortcuts a")) >= 6,
                    "six dashboard shortcuts did not render")
        assert_true(bool(driver.find_element(By.ID, "memory-compact-en").text.strip()),
                    "Memory Trace quote missing")
        assert_true(driver.find_element(By.ID, "feed-manage").is_displayed(),
                    "RSS manager inaccessible")
    check("six launchers, Memory Trace and RSS controls render", dashboard)

    def default_permissions():
        grants = async_value("return await browser.permissions.getAll();")
        assert_true(not (isinstance(grants, dict) and "__error" in grants), "permissions API failed")
        assert_true(not grants.get("origins"), "unexpected default host access: " + repr(grants))
        assert_true(not any(p in grants.get("permissions", []) for p in ("history","bookmarks","tabs","sessions")),
                    "optional browser permission was pre-granted")
        results["defaultPermissions"] = grants
    check("privacy: no optional host or browsing permissions enabled initially", default_permissions)

    note = "Ayarime Firefox CI test note — no personal information."
    focus = "Firefox native smoke test"
    def local_note():
        el = driver.find_element(By.ID, "note-input")
        el.click()
        el.send_keys(note)
        field_key = "elfshell-workspace-v3:field:note"
        WebDriverWait(driver, 12).until(lambda _d: storage(field_key) == note)
        f = driver.find_element(By.ID, "focus-input")
        f.click()
        f.send_keys(focus)
        WebDriverWait(driver, 12).until(lambda _d: storage("elfshell-workspace-v3:field:focus") == focus)
    check("notes and focus persist to actual Firefox extension storage", local_note)

    def search_math():
        el = driver.find_element(By.ID, "search-input")
        el.click()
        el.send_keys("= 15% of 2400")
        WebDriverWait(driver, 8).until(lambda d: "360" in d.find_element(By.ID, "search-results").text)
        el.send_keys(Keys.ESCAPE)
        assert_true(el.get_attribute("value") == "", "Escape should clear palette search")
    check("command palette calculator and Escape", search_math)

    def cross_tab_persistence():
        driver.switch_to.new_window("tab")
        new_tab()
        WebDriverWait(driver, 15).until(lambda d: d.find_element(By.ID, "note-input").get_attribute("value") == note)
        assert_true(driver.find_element(By.ID, "focus-input").get_attribute("value") == focus,
                    "focus lost on new tab")
    check("local note/focus survive second actual Firefox new tab", cross_tab_persistence)

    results["status"] = "PASS"
except Exception as exc:
    results["status"] = "FAIL"
    results["error"] = str(exc)
    results["traceback"] = traceback.format_exc()
    print("FAIL:", exc, file=sys.stderr, flush=True)
finally:
    if driver is not None:
        try:
            driver.save_screenshot(str(OUTPUT / "firefox-new-tab.png"))
            results["screenshot"] = "firefox-new-tab.png"
        except Exception as exc:
            results["screenshotError"] = str(exc)
        try:
            driver.quit()
        except Exception:
            pass
    (OUTPUT / "report.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(results, indent=2, ensure_ascii=False), flush=True)
if results["status"] != "PASS":
    sys.exit(1)
