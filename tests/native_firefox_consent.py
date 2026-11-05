#!/usr/bin/env python3
"""Real Firefox release consent QA: no network or spelling before opt-in.

Only disposable GitHub runner profiles, synthetic OPML and public test URLs.
Diagnostics for Firefox's actual extension toolbar are captured to support
a follow-up genuine consent/revocation interaction test.
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
VER = json.loads((ROOT / "manifest.json").read_text())["version"]
ZIP = ROOT / "dist" / f"ELF-SHELL-Ayarime-v{VER}-AMO.zip"
OUT = ROOT / "dist" / "firefox-consent-qa"
OUT.mkdir(parents=True, exist_ok=True)
results = {"check_group": "Real Firefox RSS / spelling pre-consent", "checks": []}
driver = None


def check(name, action):
    action()
    results["checks"].append({"name": name, "result": "PASS"})
    print("PASS:", name, flush=True)


def ensure(condition, message):
    if not condition:
        raise AssertionError(message)


def ext_async(js):
    result = driver.execute_async_script(
        "const done = arguments[arguments.length - 1];"
        "Promise.resolve().then(async () => {" + js +
        "}).then(done, err => done({__error: String(err)}));"
    )
    ensure(not (isinstance(result, dict) and "__error" in result), "Extension API failed: " + repr(result))
    return result


def new_tab():
    old = set(driver.window_handles)
    with driver.context(driver.CONTEXT_CHROME):
        driver.execute_script("window.BrowserCommands.openTab();")
    WebDriverWait(driver, 12).until(lambda d: len(set(d.window_handles) - old) == 1)
    driver.switch_to.window(next(iter(set(driver.window_handles) - old)))
    WebDriverWait(driver, 16).until(lambda d: d.current_url.startswith("moz-extension://") and
                                  d.find_elements(By.ID, "feed-manage"))
    return driver.current_url


def grants():
    return ext_async("return await browser.permissions.getAll();")


try:
    ensure(ZIP.exists(), "Missing release package: run scripts/package.py first")
    options = webdriver.FirefoxOptions()
    options.add_argument("-headless")
    if os.environ.get("FIREFOX_BINARY"):
        options.binary_location = os.environ["FIREFOX_BINARY"]
    options.set_preference("browser.shell.checkDefaultBrowser", False)
    options.set_preference("app.update.enabled", False)
    driver = webdriver.Firefox(options=options,
        service=FirefoxService(service_args=["--allow-system-access"]))
    driver.set_script_timeout(20)
    driver.set_page_load_timeout(18)
    driver.set_window_size(1366, 768)
    results["firefoxVersion"] = driver.capabilities.get("browserVersion")
    results["addonId"] = driver.install_addon(str(ZIP), temporary=True)
    results["dashboardUrl"] = new_tab()

    def preconsent():
        ps = grants()
        ensure(not ps.get("origins"), "Site permission unexpectedly granted")
        scripts = ext_async("return await browser.scripting.getRegisteredContentScripts();")
        ensure(not scripts, "Spelling was unexpectedly registered for websites")
        response = ext_async('return await browser.runtime.sendMessage({type:"elfshell:spelling:check",words:["teh"]});')
        ensure(response.get("ok") is False and "disabled" in response.get("error", "").lower(),
               "Spelling endpoint granted access to a dashboard sender: " + repr(response))
    check("no implicit host grants, no spelling injections, background rejects unauthorized spelling", preconsent)

    fixture = OUT / "nonconsenting-public-feeds.opml"
    fixture.write_text("""<?xml version="1.0"?>
<opml version="2.0"><head><title>Disposable QA feed list</title></head><body>
<outline text="QA GitHub" xmlUrl="https://github.blog/feed/" type="rss"/>
<outline text="QA Browser" xmlUrl="https://thebrowser.substack.com/feed" type="rss"/>
<outline text="Unsafe local" xmlUrl="https://localhost/private/feed" type="rss"/>
</body></opml>""", encoding="utf-8")
    def import_opml():
        driver.find_element(By.ID, "feed-manage").click()
        WebDriverWait(driver, 6).until(lambda d: d.find_element(By.ID, "feeds-dialog").get_attribute("open") is not None)
        driver.find_element(By.ID, "feed-opml-file").send_keys(str(fixture))
        WebDriverWait(driver, 12).until(lambda d: "Imported 2 subscriptions" in d.find_element(By.ID, "feed-message").text)
        data = ext_async('return (await browser.storage.local.get("elfshell-rss-settings-v1"))["elfshell-rss-settings-v1"];')
        ensure(len(data["feeds"]) == 2, "OPML did not store exactly two safe feeds")
        ensure(all("localhost" not in f["url"] for f in data["feeds"]), "Private feed URL stored")
        ensure(not grants().get("origins"), "Import silently granted host access")
        cache = ext_async('return (await browser.storage.local.get("elfshell-rss-cache-v1"))["elfshell-rss-cache-v1"];')
        ensure(not cache, "Import fetched / cached headlines without consent: " + repr(cache)[:200])
        remote_resources = driver.execute_script(
            'return performance.getEntriesByType("resource").map(x=>x.name).filter(x=>x.includes("github.blog")||x.includes("thebrowser.substack.com"));'
        )
        ensure(not remote_resources, "Import initiated remote resource fetch: " + repr(remote_resources))
    check("OPML imports safe feeds without host grants, requests or cached headlines", import_opml)

    def manual_refresh_ungranted():
        driver.find_element(By.ID, "feed-refresh").click()
        WebDriverWait(driver, 10).until(
            lambda d: "Feed check complete" in d.find_element(By.ID, "feed-message").text)
        ensure(not grants().get("origins"), "Refresh silently obtained site grant")
        cache = ext_async('return (await browser.storage.local.get("elfshell-rss-cache-v1"))["elfshell-rss-cache-v1"];')
        ensure(not cache, "Refreshing non-authorised feeds wrote cached results")
        ensure("0 entries retrieved" in driver.find_element(By.ID, "feed-message").text,
               "Unauthorised feed returned headlines")
    check("manual refresh skips every unapproved feed", manual_refresh_ungranted)

    def second_tab_settings():
        new_tab()
        driver.find_element(By.ID, "feed-manage").click()
        WebDriverWait(driver, 10).until(lambda d: "QA GitHub" in d.find_element(By.ID, "feed-subscriptions").text and
                                     "QA Browser" in d.find_element(By.ID, "feed-subscriptions").text)
        ensure(not grants().get("origins"), "Second tab silently granted feed access")
    check("imported subscription metadata persists across Firefox new tabs without fetching", second_tab_settings)

    try:
        driver.switch_to.new_window("tab")
        driver.get("https://example.com/")
        results["websiteUrl"] = driver.current_url
        results["pageTitle"] = driver.title
        def untouched_site():
            ensure(driver.execute_script('return typeof window.__elfshellSpelling === "undefined"'),
                   "Spelling script appeared on an unapproved website")
            driver.execute_script('const d=document.createElement("div");d.id="qa-editor";d.contentEditable="true";d.textContent="teh quik brwn fox";document.body.append(d);')
            ensure(not driver.execute_script('return document.getElementById("qa-editor").hasAttribute("spellcheck")'),
                   "Unapproved site had its native spelling attribute changed")
        check("a public HTTPS rich editor remains unaffected without spelling opt-in", untouched_site)
        with driver.context(driver.CONTEXT_CHROME):
            controls = driver.execute_script("""
                return [...document.querySelectorAll(
                    '[id*="unified"],[id*="extension"],[id*="addon"],[id*="browser-action"],[data-extensionid]'
                )].slice(0,75).map(e=>({
                    tag:e.tagName,id:e.id, label:e.getAttribute('label'),
                    title:e.getAttribute('title'), extension:e.getAttribute('data-extensionid'),
                    hidden:e.hidden
                }));
            """)
        results["firefoxToolbarControls"] = controls
        print("FIREFOX TOOLBAR:", json.dumps(controls, ensure_ascii=False)[:7000], flush=True)
        try:
            with driver.context(driver.CONTEXT_CHROME):
                driver.find_element(By.ID, "unified-extensions-button").click()
                menu = driver.execute_script("""
                    return [...document.querySelectorAll(
                        '[data-extensionid],unified-extensions-item,[id*="unified-extensions"]'
                    )].filter(e=>e.isConnected).slice(0,100).map(e=>({
                        tag:e.tagName,id:e.id,
                        extension:e.getAttribute("data-extensionid"),
                        label:e.getAttribute("label"),title:e.getAttribute("title"),
                        className:String(e.className),text:(e.textContent||"").trim().slice(0,140),
                        hidden:e.hidden,
                        open:e.getAttribute("open")
                    }));
                """)
            results["firefoxExtensionsMenu"] = menu
            print("FIREFOX EXTENSIONS MENU:",json.dumps(menu,ensure_ascii=False)[:10000],flush=True)
            with driver.context(driver.CONTEXT_CHROME):
                driver.find_element(By.ID, "elf-shell-ayarime_local_theme-BAP").click()
                popup = driver.execute_script("""
                    return [...document.querySelectorAll(
                        'panel,[id*="webextension"],[id*="popup"],browser[webextension-view-type]'
                    )].filter(e=>e.isConnected).slice(0,100).map(e=>({
                        tag:e.tagName,id:e.id,label:e.getAttribute("label"),
                        type:e.getAttribute("type"),open:e.getAttribute("open"),
                        state:e.state||null,src:e.getAttribute("src"),
                        view:e.getAttribute("webextension-view-type"),
                        child:e.contentDocument?.documentElement?.outerHTML?.slice(0,300)||null,
                        title:e.getAttribute("title")
                    }));
                """)
            results["firefoxActionPopup"] = popup
            print("FIREFOX ACTION POPUP:", json.dumps(popup,ensure_ascii=False)[:12000],flush=True)
        except Exception as menuError:
            results["firefoxExtensionsMenuError"] = str(menuError)
            print("Firefox toolbar menu diagnostic:",str(menuError),flush=True)
    except AssertionError:
        raise
    except Exception as exc:
        results["externalWebsiteDiagnostic"] = str(exc)
        print("External website / toolbar diagnostic unavailable:", exc, flush=True)

    results["status"] = "PASS"
except Exception as exc:
    results["status"] = "FAIL"
    results["error"] = str(exc)
    results["traceback"] = traceback.format_exc()
    print("FAIL:", str(exc), flush=True)
finally:
    if driver:
        try:
            driver.save_screenshot(str(OUT / "consent-qa.png"))
        except Exception as exc:
            results["screenshotError"] = str(exc)
        try:
            driver.quit()
        except Exception:
            pass
    (OUT / "report.json").write_text(json.dumps(results, indent=2, ensure_ascii=False),
                                     encoding="utf-8")
    print("RESULT:", json.dumps({k:v for k,v in results.items() if k!="firefoxToolbarControls"},ensure_ascii=False)[:11000], flush=True)
sys.exit(0 if results["status"] == "PASS" else 1)
