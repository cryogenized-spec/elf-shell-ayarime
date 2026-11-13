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
    response=driver.execute_async_script(
        "const done=arguments[arguments.length-1];"
        "Promise.resolve().then(async()=>{" + source +
        "}).then(done,e=>done({__apiError:String(e)}));"
    )
    if isinstance(response,dict) and "__apiError" in response:
        raise AssertionError("Firefox extension API rejected: "+response["__apiError"])
    return response

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
            # A real native prompt must appear; otherwise this check fails,
            # rather than logging an empty panel as successful consent UI.
            WebDriverWait(driver,12).until(lambda d:d.execute_script("""
                const panel=document.getElementById("notification-popup");
                const prompt=document.getElementById("addon-webext-permissions-notification");
                return ["showing","open"].includes(panel?.state) &&
                    prompt && !prompt.hidden &&
                    (prompt.textContent||"").includes("github.blog") &&
                    prompt.button?.getAttribute("label")==="Allow" &&
                    prompt.secondaryButton?.getAttribute("label")==="Deny";
            """))
            chrome=driver.execute_script("""
                const panel=document.getElementById("notification-popup");
                const match=document.getElementById("addon-webext-permissions-notification");
                return {
                  panelState:panel?.state||null,
                  permissionsNode:{id:match?.id||null,hidden:match?.hidden??null,
                    text:(match?.textContent||"").trim().slice(0,1200),
                    html:match?.outerHTML?.slice(0,4800)||null,
                    shadowHtml:match?.shadowRoot?.innerHTML?.slice(0,3500)||null,
                    button:match?.button?.outerHTML?.slice(0,800)||null,
                    secondary:match?.secondaryButton?.outerHTML?.slice(0,800)||null},
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

    def permission_snapshot():
        """Safely inspect native prompt state, browser grants and the page status."""
        with driver.context(driver.CONTEXT_CHROME):
            chrome=driver.execute_script("""
                const panel=document.getElementById("notification-popup");
                const notification=document.getElementById("addon-webext-permissions-notification");
                return {
                  state:panel?.state||"missing",
                  visible:!!notification&&!notification.hidden,
                  primary:notification?.button?.getAttribute("label")||null,
                  secondary:notification?.secondaryButton?.getAttribute("label")||null
                };
            """)
        return {
            "chrome":chrome,
            "status":driver.find_element(By.ID,"feed-message").text,
            "granted":await_api('return await browser.permissions.contains({origins:["https://github.blog/*"]});'),
            "origins":(await_api('return await browser.permissions.getAll();')).get("origins",[]),
            "savedCount":len((await_api('return (await browser.storage.local.get("elfshell-rss-settings-v1"))["elfshell-rss-settings-v1"];') or {}).get("feeds",[]))
        }

    def click_prompt_choice(choice):
        """Actuate the actual Firefox browser notification, not extension APIs.

        Modern Firefox exposes each moz-button's clickable inner <button>
        via shadow DOM. Old ActionChains against the outer host failed to
        activate the notification. This test never stubs permissions.request
        or directly sets extension permission state. The RSS request itself
        was initiated by a real Selenium click on the subscription form.
        """
        if choice not in ("secondary","primary"):
            raise AssertionError("Unknown Firefox permission choice")
        expected="Deny" if choice=="secondary" else "Allow"
        with driver.context(driver.CONTEXT_CHROME):
            WebDriverWait(driver,8).until(
                lambda d:d.execute_script("""
                  const panel=document.getElementById("notification-popup");
                  const prompt=document.getElementById("addon-webext-permissions-notification");
                  return ["showing","open"].includes(panel?.state)
                    && !!prompt&&!prompt.hidden;
                """))
            outcome=driver.execute_script("""
                const expected=arguments[0],which=arguments[1];
                const notification=document.getElementById(
                    "addon-webext-permissions-notification");
                const control=which==="secondary"
                    ?notification?.secondaryButton:notification?.button;
                const label=control?.getAttribute("label");
                if(label!==expected)return {clicked:false,label:label||null};
                // Browser-chrome automation of the real Firefox permission
                // control, rather than forging browser.permissions responses.
                const inner=control.shadowRoot?.querySelector("button");
                (inner||control).click();
                return {clicked:true,label};
            """,expected,choice)
            if outcome.get("clicked") is not True:
                raise AssertionError("Firefox permission control unavailable: "+repr(outcome))
        WebDriverWait(driver,12).until(
            lambda d:permission_snapshot()["chrome"]["state"] not in ("showing","open"))
        result["lastChoice"]=expected
        result["lastChoiceSnapshot"]=permission_snapshot()

    def deny_no_side_effect():
        click_prompt_choice("secondary")
        WebDriverWait(driver,12).until(
            lambda d:"declined" in d.find_element(By.ID,"feed-message").text.lower())
        result["postDeny"]=permission_snapshot()
        if await_api('return await browser.permissions.contains({origins:["https://github.blog/*"]});'):
            raise AssertionError("Firefox granted host access after Deny")
        if (await_api('return await browser.permissions.getAll();')).get("origins"):
            raise AssertionError("Deny left unexpected host grants")
        state=await_api('return (await browser.storage.local.get("elfshell-rss-settings-v1"))["elfshell-rss-settings-v1"];')
        if state and state.get("feeds"):
            raise AssertionError("Declined permission nonetheless saved feed: "+repr(state))
    check("real Firefox Deny prevents host grant and RSS subscription",deny_no_side_effect)

    def allow_and_subscribe():
        driver.find_element(By.CSS_SELECTOR,"#feed-add-form button[type=submit]").click()
        click_prompt_choice("primary")
        WebDriverWait(driver,18).until(
            lambda d:await_api('return await browser.permissions.contains({origins:["https://github.blog/*"]});') is True)
        result["postAllow"]=permission_snapshot()
        WebDriverWait(driver,18).until(lambda d:
            len((await_api('return (await browser.storage.local.get("elfshell-rss-settings-v1"))["elfshell-rss-settings-v1"];') or {}).get("feeds",[]))==1)
        host_grants=(await_api('return await browser.permissions.getAll();')).get("origins",[])
        if host_grants != ["https://github.blog/*"]:
            raise AssertionError("Allow unexpectedly granted other hosts: "+repr(host_grants))

        # Wait for the live RSS request to finish, rather than matching the
        # intermediate status "Subscription saved. Fetching...".
        WebDriverWait(driver,26).until(lambda d:
            "Subscription saved" in d.find_element(By.ID,"feed-message").text and
            "Fetching" not in d.find_element(By.ID,"feed-message").text)
        result["liveFeedMessage"]=driver.find_element(By.ID,"feed-message").text
        cache=await_api('return (await browser.storage.local.get("elfshell-rss-cache-v1"))["elfshell-rss-cache-v1"];') or {}
        result["liveFeedCacheCount"]=len(cache.get("https://github.blog/feed/",{}).get("items",[]))
    check("real Firefox Allow grants only requested HTTPS host and saves RSS subscription",allow_and_subscribe)

    def revoke_host():
        buttons=driver.find_elements(By.XPATH,"//button[normalize-space()='REVOKE HOST']")
        WebDriverWait(driver,8).until(lambda d:len(d.find_elements(By.XPATH,"//button[normalize-space()='REVOKE HOST']"))>=1)
        driver.find_element(By.XPATH,"//button[normalize-space()='REVOKE HOST']").click()
        WebDriverWait(driver,12).until(lambda d:
            await_api('return await browser.permissions.contains({origins:["https://github.blog/*"]});') is False)
        remaining=await_api('return (await browser.storage.local.get("elfshell-rss-settings-v1"))["elfshell-rss-settings-v1"];')
        if len((remaining or {}).get("feeds",[]))!=1:
            raise AssertionError("Revocation deleted subscription metadata")
        if (await_api('return await browser.permissions.getAll();')).get("origins"):
            raise AssertionError("Revocation left host grants behind")
    check("RSS Revoke Host removes access but preserves local subscription",revoke_host)

    def post_revoke_no_fetch():
        before=await_api('return (await browser.storage.local.get("elfshell-rss-cache-v1"))["elfshell-rss-cache-v1"];') or {}
        attempted=(before.get("https://github.blog/feed/") or {}).get("attemptedAt")
        driver.find_element(By.ID,"feed-refresh").click()
        WebDriverWait(driver,10).until(lambda d:"Feed check complete" in d.find_element(By.ID,"feed-message").text)
        after=await_api('return (await browser.storage.local.get("elfshell-rss-cache-v1"))["elfshell-rss-cache-v1"];') or {}
        if (after.get("https://github.blog/feed/") or {}).get("attemptedAt")!=attempted:
            raise AssertionError("Refreshing after host revocation made a new feed attempt")
    check("refresh after host revocation makes no new RSS fetch",post_revoke_no_fetch)

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
