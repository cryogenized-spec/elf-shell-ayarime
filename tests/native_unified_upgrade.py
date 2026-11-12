#!/usr/bin/env python3
"""Isolated old-core -> fused-preview -> optional rollback acceptance.

All data are synthetic, generated in a clean CI profile. Never load a user's
real Firefox profile, extensions, Google tokens, or saved browser settings.
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

ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT/"dist"/"ELF-SHELL-Ayarime-core-before-upgrade-UNSIGNED.xpi"
NEW=ROOT/"dist"/"ELF-SHELL-Ayarime-unified-UNSIGNED.xpi"
OUT=ROOT/"dist"/"upgrade-acceptance"
OUT.mkdir(parents=True,exist_ok=True)
ADDON_ID="elf-shell-ayarime@local.theme"
FIELDS=["links","note","focus","motion","contrast","cursor","typography","bangs","sessions"]
PREFIX="elfshell-workspace-v3:field:"
TRACKED=[PREFIX+f for f in FIELDS]+[
    "elfshell-workspace-v2","elfshell-rss-settings-v1",
    "elfshell-memory-v1","elfshell-duplicate-recovery-v1",
    "non_elfshell_legacy_marker"]
checks=[]
driver=None

def check(label,condition):
    if not condition:
        raise AssertionError(label)
    checks.append(label)
    print("PASS:",label,flush=True)

def async_js(script,*args):
    return driver.execute_async_script(script,*args)

def open_station():
    before=set(driver.window_handles)
    with driver.context(driver.CONTEXT_CHROME):
        driver.execute_script("window.BrowserCommands.openTab();")
    WebDriverWait(driver,15).until(
        lambda d:len(set(d.window_handles)-before)==1)
    handle=next(iter(set(driver.window_handles)-before))
    driver.switch_to.window(handle)
    WebDriverWait(driver,20).until(
        lambda d:len(d.find_elements(By.ID,"note-input"))==1)
    return handle

def snapshot():
    data=async_js("""
      const done=arguments[arguments.length-1];
      browser.storage.local.get(arguments[0]).then(done,
        error=>done({error:String(error)}));
    """,TRACKED)
    if not isinstance(data,dict) or "error" in data:
        raise AssertionError("Cannot read seeded local storage")
    return data

def assert_preserved(actual,expected,purpose):
    for key,value in expected.items():
        check(purpose+": "+key,key in actual and actual[key]==value)

try:
    check("core and fused unsigned XPI files exist",OLD.is_file() and NEW.is_file())
    options=webdriver.FirefoxOptions()
    options.add_argument("-headless")
    binary=os.environ.get("FIREFOX_BINARY")
    if binary:options.binary_location=binary
    options.set_preference("browser.shell.checkDefaultBrowser",False)
    options.set_preference("browser.startup.homepage","about:blank")
    driver=webdriver.Firefox(options=options,service=FirefoxService(
        service_args=["--allow-system-access"]))
    driver.set_script_timeout(25)
    driver.set_page_load_timeout(25)
    driver.set_window_size(1366,900)

    first=driver.install_web_extension(str(OLD),permanent=False).id
    check("pre-fusion core installed under production add-on ID",first==ADDON_ID)
    old_handle=open_station()
    check("pre-fusion core has no AI toggle",
          not driver.find_elements(By.ID,"ai-module-toggle"))
    WebDriverWait(driver,15).until(lambda d:d.find_element(By.ID,"note-input").is_displayed())

    seeded=async_js("""
      const done=arguments[arguments.length-1];
      // Explicit representative fields from the reviewed core v3 schema:
      // WebDriver's isolated script execution cannot read top-level let state.
      const base={
        links:[
          {label:"My old Firefox",icon:"firefox",glyph:"◉",
           url:"https://www.mozilla.org/en-US/firefox/",group:"GENERAL"},
          {label:"Mail",icon:"mail",glyph:"✉",
           url:"https://mail.google.com/",group:"WORK"},
          {label:"Calendar",icon:"calendar",glyph:"▦",
           url:"https://calendar.google.com/",group:"WORK"},
          {label:"Drive",icon:"drive",glyph:"◇",
           url:"https://drive.google.com/",group:"WORK"},
          {label:"Video",icon:"video",glyph:"▷",
           url:"https://www.youtube.com/",group:"MEDIA"},
          {label:"Library",icon:"library",glyph:"▤",
           url:"https://openlibrary.org/",group:"MEDIA"}
        ],
        note:"PRE-MERGE NOTE: synthetic legacy archive kept intact",
        focus:"PRE-MERGE FOCUS: keep the original work plan",
        motion:true,contrast:true,cursor:"system",
        typography:{preset:"original",scale:110,display:"preset",
          ui:"preset",mono:"preset",japanese:"preset"},
        bangs:[{key:"test",url:"https://www.mozilla.org/search/?q={query}"}],
        sessions:[
          {name:"Original Research",created:"2026-10-01T10:00:00Z",
            urls:["https://www.mozilla.org/en-US/firefox/","https://example.org/research"]},
          {name:"Other Tab Set",created:"2026-10-02T10:00:00Z",
            urls:["https://example.net/reference","https://example.com/start"]}
        ]
      };
      const changes={};
      for(const field of arguments[0])
        changes["elfshell-workspace-v3:field:"+field]=structuredClone(base[field]);
      changes["elfshell-workspace-v2"]=structuredClone(base);
      changes["elfshell-rss-settings-v1"]={
        enabled:false,interval:60,feeds:[
          {url:"https://www.mozilla.org/en-US/firefox/feed/",title:"Example old feed",
           group:"REFERENCE",enabled:false}
        ]
      };
      const originalMemory=window.elfMemory?.snapshot();
      if(originalMemory)changes["elfshell-memory-v1"]=structuredClone(originalMemory);
      changes["elfshell-duplicate-recovery-v1"]=[
        {id:"synthetic-recovery-1",url:"https://example.org/recover"}
      ];
      changes["non_elfshell_legacy_marker"]={value:"keep",revision:3};
      browser.storage.local.set(changes).then(()=>done({ok:true,fields:Object.keys(changes).length}),
        error=>done({ok:false,error:String(error)}));
    """,FIELDS)
    check("synthetic legacy settings seeded into genuine core extension",
          seeded.get("ok") is True and seeded.get("fields",0)>=12)
    driver.refresh()
    WebDriverWait(driver,15).until(lambda d:
        d.find_element(By.ID,"note-input").get_attribute("value")==
        "PRE-MERGE NOTE: synthetic legacy archive kept intact")
    check("existing core really reads seeded note/focus",
          driver.find_element(By.ID,"focus-input").get_attribute("value").startswith("PRE-MERGE FOCUS"))
    baseline=snapshot()
    check("baseline includes all nine v3 independent workspace fields",
          all(PREFIX+field in baseline for field in FIELDS))

    # Read the exported JSON through the original core's *actual* export
    # function, without downloading any file or uploading any user information.
    exported=async_js("""
      const done=arguments[arguments.length-1];
      const originalUrl=URL.createObjectURL;
      const originalClick=HTMLAnchorElement.prototype.click;
      let blob=null;
      try{
        URL.createObjectURL=value=>{blob=value;return "blob:synthetic-upgrade-test";};
        HTMLAnchorElement.prototype.click=function(){};
        saveJSON();
      }catch(error){
        URL.createObjectURL=originalUrl;
        HTMLAnchorElement.prototype.click=originalClick;
        done({ok:false,error:String(error)});return;
      }
      URL.createObjectURL=originalUrl;
      HTMLAnchorElement.prototype.click=originalClick;
      if(!blob){done({ok:false,error:"Legacy export generated no Blob"});return;}
      blob.text().then(text=>done({ok:true,text}),error=>done({ok:false,error:String(error)}));
    """)
    check("actual pre-fusion v5 backup export succeeds",exported.get("ok") is True)
    backup=json.loads(exported["text"])
    check("legacy backup includes existing workspace and sessions",
          backup["version"]==5 and backup["format"]=="elfshell-settings"
          and len(backup["sessions"])==2 and
          backup["note"]==baseline[PREFIX+"note"])
    check("backup excludes future optional AI preference",
          "elfshell.unified.aiEnabled.v1" not in backup)

    # Install the assembled extension with exactly the same add-on ID.
    # A replaced temporary add-on may behave differently from a signed AMO
    # update. Record that limitation, never invent successful migration.
    second=driver.install_web_extension(str(NEW),permanent=False).id
    check("unified preview installs with the same add-on ID",second==first)
    fused_handle=open_station()
    WebDriverWait(driver,15).until(lambda d:
        len(d.find_elements(By.ID,"ai-module-toggle"))==1 and
        d.find_element(By.ID,"ai-module-toggle").is_enabled())
    check("upgraded dashboard contains optional AI toggle",
          driver.find_element(By.ID,"ai-module-toggle").get_attribute("aria-pressed")=="false")
    persisted=snapshot()
    assert_preserved(persisted,baseline,"same-ID upgrade preserved data")
    check("legacy note restored in unified Station UI",
          driver.find_element(By.ID,"note-input").get_attribute("value")==baseline[PREFIX+"note"])
    check("legacy focus restored in unified Station UI",
          driver.find_element(By.ID,"focus-input").get_attribute("value")==baseline[PREFIX+"focus"])

    # The actual core import function must accept an old v5 export; import
    # without introducing a new AI preference or deleting unrelated keys.
    imported=async_js("""
      const done=arguments[arguments.length-1];
      const payload=arguments[0];
      const file=new File([payload],"synthetic-elfshell-v5-backup.json",
        {type:"application/json"});
      importJSON(file).then(()=>{
        done({status:document.getElementById("settings-message").textContent});
      },error=>done({error:String(error)}));
    """,exported["text"])
    check("unified build imports real v5 ELF//SHELL backup",
          imported.get("status")=="Settings imported successfully.")
    after_import=snapshot()
    for field in FIELDS:
        key=PREFIX+field
        check("v5 import preserves "+field,
              key in after_import and after_import[key]==baseline[key])
    for key in ["elfshell-rss-settings-v1","elfshell-memory-v1",
                "elfshell-duplicate-recovery-v1","non_elfshell_legacy_marker"]:
        if key in baseline:
            check("v5 import retains "+key,
                  after_import.get(key)==baseline[key])
    ai=async_js("""
      const done=arguments[arguments.length-1];
      browser.storage.local.get("elfshell.unified.aiEnabled.v1").then(done);
    """)
    check("upgrade and backup import do not silently enable AI",
          ai.get("elfshell.unified.aiEnabled.v1") is not True)

    results={"status":"PASS","checks":checks,
             "note":"Clean synthetic Firefox temporary-addon replacement; not a signed AMO upgrade"}
    driver.save_screenshot(str(OUT/"unified-after-upgrade.png"))
except Exception as error:
    results={"status":"FAIL","checks":checks,"error":str(error),
             "traceback":traceback.format_exc()}
    print("FAIL:",str(error),file=sys.stderr,flush=True)
    if driver:
        try:driver.save_screenshot(str(OUT/"failure.png"))
        except Exception:pass
finally:
    (OUT/"report.json").write_text(json.dumps(results,indent=2),encoding="utf-8")
    if driver:driver.quit()
if results["status"]!="PASS":raise SystemExit(1)
