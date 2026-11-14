#!/usr/bin/env python3
"""Build a separate, unsigned one-extension engineering preview.

This script never changes manifest.json, AMO package inventory, or installed add-ons.
It assembles *two pinned, reviewed source trees* into dist/unified-preview/.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from zipfile import ZipFile, ZIP_DEFLATED, ZipInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from package import sources as core_sources  # reviewed release inventory, not a recursive scan

COMPANION_COMMIT = "885157e3d7bfeba3d1a344068448c1f4782d3be0"
KIND = "elfshell.workspace.bridge"
BRIDGE_COMMAND = "elfshell:unified:bridge:v1"
OUTPUT = ROOT / "dist" / "ELF-SHELL-Ayarime-unified-UNSIGNED.xpi"
STAGING = ROOT / "dist" / "unified-preview"
STAMP = (2026, 11, 12, 0, 0, 0)


def check(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def checked_companion(folder: Path) -> None:
    check(folder.is_dir(), "Companion checkout missing")
    head = subprocess.check_output(
        ["git", "-C", str(folder), "rev-parse", "HEAD"],
        text=True, stderr=subprocess.DEVNULL,
    ).strip()
    check(head == COMPANION_COMMIT,
          "Companion checkout mismatch: use the reviewed exact commit (not a moving branch)")


def companion_inventory(folder: Path) -> list[str]:
    """Read the existing companion's explicit packaging whitelist without executing it."""
    tree = ast.parse((folder / "scripts/package.py").read_text(encoding="utf-8"))
    candidates = [
        ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "FILES" for t in node.targets)
    ]
    check(len(candidates) == 1 and isinstance(candidates[0], list),
          "Companion runtime whitelist changed: manual review needed")
    files = candidates[0]
    check(len(files) == len(set(files)), "Duplicate companion source path")
    for rel in files:
        check(isinstance(rel, str) and rel and rel == Path(rel).as_posix()
              and ".." not in Path(rel).parts and not rel.startswith("/"),
              "Unsafe companion runtime source path")
        check((folder / rel).is_file(), "Missing companion runtime source: " + rel)
    check("manifest.json" in files and "background.js" in files
          and "hub.html" in files and "sidebar.html" in files,
          "Companion runtime whitelist lacks mandatory extension assets")
    return files


def combine_manifest(core: dict, companion: dict) -> dict:
    check(core["manifest_version"] == companion["manifest_version"] == 3,
          "Unexpected WebExtension manifest version")
    check(core["browser_specific_settings"]["gecko"]["id"]
          == "elf-shell-ayarime@local.theme",
          "Do not change public ELF//SHELL add-on identity")
    required = set(core["permissions"])
    check(required == {"theme", "search", "storage"}, "Core permissions changed: review first")
    extra = set(companion["permissions"]) - required
    check(extra == {"tabs", "tabGroups", "identity", "alarms"},
          "Companion runtime permissions changed: review before bundling")
    manifest = json.loads(json.dumps(core))
    manifest["name"] = "ELF//SHELL — Ayarime Unified Preview"
    manifest["description"] = "Development-only integrated Ayarime sidebar, workspace and AI."
    manifest["background"]["scripts"] = [
        *core["background"]["scripts"],
        *[script for script in companion["background"]["scripts"] if script != "background.js"],
        "workspace-ai-background.js",
    ]
    check(len(manifest["background"]["scripts"]) ==
          len(set(manifest["background"]["scripts"])),
          "Duplicate merged background script")
    manifest["sidebar_action"] = companion["sidebar_action"]
    manifest["action"] = companion["action"]
    # The published core's required permissions remain exactly unchanged.
    manifest["permissions"] = list(core["permissions"])
    # Mozilla does not support identity/alarms in optional_permissions.
    # Keep them out of the preview instead of escalating core required grants.
    manifest["optional_permissions"] = sorted(
        set(core.get("optional_permissions", [])) | {"tabs", "tabGroups"})
    manifest["optional_host_permissions"] = sorted(
        set(core.get("optional_host_permissions", []))
        | set(companion.get("optional_host_permissions", [])))
    gecko = manifest["browser_specific_settings"]["gecko"]
    gecko["data_collection_permissions"] = {
        "required": ["none"],
        "optional": list(companion["browser_specific_settings"]["gecko"]
                         ["data_collection_permissions"].get("optional", [])),
    }
    check("externally_connectable" not in manifest,
          "Unified extension must not expose companion's cross-extension interface")
    # Preserve the existing public core CSP in the preview, do not silently broaden it.
    check(manifest["content_security_policy"] == core["content_security_policy"],
          "Core CSP changed during preview assembly")
    check(manifest["chrome_url_overrides"] == core["chrome_url_overrides"],
          "New-tab ownership changed")
    return manifest


def adapt_background(source: str) -> str:
    """Isolate companion source and route a limited set of internal messages."""
    original = (
        'browser.runtime.onMessage.addListener((message,sender) => {\n'
        '  if (sender.id !== browser.runtime.id) return {ok:false,error:"Unauthorized sender"};\n'
        '  return handle(message);\n'
        '});'
    )
    check(source.count(original) == 1,
          "Companion background listener changed: manual review required")

    # Use the SAME switch and listener that already handle GET_STATE. This avoids
    # competing Firefox runtime.onMessage listeners for the unified bridge.
    anchor = '      case "GET_STATE":'
    check(source.count(anchor) == 1, "Companion internal switch changed")
    source = source.replace(anchor, (
        '      case "UNIFIED_HELLO":\n'
        '        return {ok:true,kind:"elfshell.workspace.bridge",version:1,\n'
        '          capabilities:["OPEN_ASSISTANT","OPEN_WORKSPACE"],\n'
        '          dataAccess:"browser-tabs-only"};\n'
        '      case "UNIFIED_OPEN_ASSISTANT":\n'
        '        if(!await browser.permissions.contains({permissions:["tabs"]}))\n'
        '          throw Error("Firefox tab access must be granted before opening the AI Hub");\n'
        '        return {ok:true,result:await serialise(focusAssistant)};\n'
        + anchor
    ))
    # Any extension page can send same-extension messages; keep the actual
    # capability boundary in the background, not only in a page click handler.
    workspace_case = (
        '      case "OPEN_WORKSPACE":\n'
        '        return {ok:true,result:await serialise(launchWorkspace)};'
    )
    check(source.count(workspace_case) == 1,
          "Companion workspace handler changed: review permission guard")
    source = source.replace(workspace_case, (
        '      case "OPEN_WORKSPACE":\n'
        '        if(!await browser.permissions.contains({permissions:["tabs","tabGroups"]}))\n'
        '          throw Error("Firefox tab and tab-group access must be approved first");\n'
        '        return {ok:true,result:await serialise(launchWorkspace)};'
    ))
    section = source.split("async function handle(message) {", 1)
    check(len(section) == 2, "Could not find companion handler")
    body = section[1].split(original, 1)[0]
    types = sorted(set(re.findall(r'case "([A-Z][A-Z0-9_]+)":', body)))
    check(len(types) >= 20 and "UNIFIED_HELLO" in types
          and "UNIFIED_OPEN_ASSISTANT" in types
          and "GOOGLE_AUTH_PREPARE" in types and "OPEN_WORKSPACE" in types,
          "Companion internal message router changed: review required")
    guarded = (
        'const WORKSPACE_MESSAGE_TYPES = new Set(' + json.dumps(types) + ');\n'
        'browser.runtime.onMessage.addListener((message,sender) => {\n'
        '  if (sender?.id !== browser.runtime.id || '
        ' !WORKSPACE_MESSAGE_TYPES.has(message?.type)) return undefined;\n'
        '  if (message.type.startsWith("UNIFIED_")) {\n'
        '    if (sender?.url !== browser.runtime.getURL("newtab.html") || '
        'message.kind!=="elfshell.workspace.bridge" || message.version!==1 ||\n'
        '        Object.keys(message).some(key=>'
        '!["type","kind","version"].includes(key)))\n'
        '      return Promise.resolve({ok:false,error:"Unsupported unified dashboard command"});\n'
        '  }\n'
        '  if (message.type.startsWith("GOOGLE_") || message.type.startsWith("MASTER_") || '
        'message.type==="MORNING_COFFEE_PREPARE" || '
        'message.type.startsWith("UPDATE_"))\n'
        '    return Promise.resolve({ok:false,error:"Google OAuth and update checks are disabled '
        'in this unsigned unified preview."});\n'
        '  if (message.type==="UNIFIED_OPEN_ASSISTANT" || '
        '(message.type.startsWith("AI_") && '
        '!["AI_CLEAR_SESSION_KEY","AI_CONVERSATION_CLEAR","AI_CANCEL_REQUEST"].includes(message.type)))\n'
        '    return unifiedAiEnabled().then(allowed=>allowed ? handle(message) '
        ': {ok:false,error:"Enable Ayarime AI in the Station before using the assistant"});\n'
        '  return handle(message);\n'
        '});'
    )
    source = source.replace(original, guarded)
    action = (
        '  serialise(launchWorkspace).catch(error => '
        'console.error("Workspace initialization failed:",error));'
    )
    check(source.count(action) == 1, "Companion action listener changed")
    source = source.replace(action, (
        '  browser.permissions.request({permissions:["tabs","tabGroups"]})\n'
        '    .then(granted=>granted ? serialise(launchWorkspace) : undefined)\n'
        '    .catch(()=>{});'
    ))
    external = (
        'browser.runtime.onMessageExternal.addListener((message, sender) =>\n'
        '  handleCoreMessage(message, sender).catch(() => ({ok:false,error:"Bridge request failed"}))\n'
        ');'
    )
    check(source.count(external) == 1, "Companion external listener changed")
    source = source.replace(external, "// Disabled: one-extension build has no external connection.")
    gate = (
        'const UNIFIED_AI_KEY="elfshell.unified.aiEnabled.v1";\n'
        'const UNIFIED_STREAMS=new Set();\n'
        'async function unifiedAiEnabled(){\n'
        '  const state=await browser.storage.local.get(UNIFIED_AI_KEY);\n'
        '  return state[UNIFIED_AI_KEY]===true;\n'
        '}\n'
        'browser.storage.onChanged.addListener((changes,area)=>{\n'
        '  if(area!=="local" || !Object.hasOwn(changes,UNIFIED_AI_KEY) ||\n'
        '     changes[UNIFIED_AI_KEY].newValue===true)return;\n'
        '  for(const controller of UNIFIED_STREAMS)controller.abort();\n'
        '  browser.storage.session.remove("elfshell.byok.apiKey.v1")\n'
        '    .catch(()=>console.warn("Ayarime AI session-key removal failed"));\n'
        '});\n'
        'unifiedAiEnabled().then(enabled=>{\n'
        '  if(!enabled)return browser.storage.session.remove("elfshell.byok.apiKey.v1");\n'
        '}).catch(()=>console.warn("Ayarime AI startup credential check failed"));\n'
    )
    open_marker = '      controller=new AbortController();'
    check(source.count(open_marker)==1, "OpenAI stream controller allocation changed")
    source = source.replace(open_marker, open_marker +
        '\n      UNIFIED_STREAMS.add(controller);')
    close_marker = '    port.onDisconnect.addListener(()=>{closed=true;controller?.abort();});'
    check(source.count(close_marker)==1, "OpenAI stream cleanup changed")
    source = source.replace(close_marker,
        '    port.onDisconnect.addListener(()=>{closed=true;controller?.abort();'
        'if(controller)UNIFIED_STREAMS.delete(controller);});')
    stream_marker = '      globalThis.WorkspaceOpenAIStream.run({'
    check(source.count(stream_marker) == 1, "OpenAI streaming entrypoint changed")
    # The model stream must enforce the same persisted flag as the one-shot
    # router; a direct Port message may not bypass the Station toggle.
    source = source.replace(stream_marker, (
        '      unifiedAiEnabled().then(allowed=>{\n'
        '        if(!allowed){send({kind:"terminal",status:"failed",\n'
        '          message:"Enable Ayarime AI in the Station before streaming"});return;}\n'
        '        if(controller.signal.aborted)return;\n'
        + stream_marker
    ))
    end_marker = '      });\n    });\n    port.onDisconnect.addListener'
    check(source.count(end_marker) == 1, "OpenAI stream close structure changed")
    source = source.replace(end_marker,
        '      });\n      }).catch(()=>send({kind:"terminal",status:"failed",\n'
        '        message:"Could not read local AI module preference"}));\n'
        '    });\n    port.onDisconnect.addListener')
    return '(function(){\n"use strict";\n' + gate + source + '\n})();\n'

def adapt_ui(source: str) -> str:
    needle = '    const response=await request({type:"OPEN_WORKSPACE"});'
    check(source.count(needle) == 1,
          "Companion launch UI changed; explicit tab permissions need manual review")
    return source.replace(needle, (
        '    const granted=await browser.permissions.request('
        '{permissions:["tabs","tabGroups"]});\n'
        '    if(!granted)throw Error("Workspace tab access was not granted");\n'
        + needle
    ))


def build(companion_dir: Path) -> None:
    checked_companion(companion_dir)
    files = companion_inventory(companion_dir)
    core_manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    companion_manifest = json.loads((companion_dir / "manifest.json").read_text(encoding="utf-8"))
    manifest = combine_manifest(core_manifest, companion_manifest)
    if STAGING.exists():
        shutil.rmtree(STAGING)
    STAGING.mkdir(parents=True)
    inventory: dict[str, bytes] = {}
    for source in core_sources():
        rel = source.relative_to(ROOT).as_posix()
        inventory[rel] = source.read_bytes()
    for rel in files:
        if rel in ("manifest.json", "background.js"):
            continue
        check(rel not in inventory, "Unreviewed runtime filename collision: " + rel)
        data = (companion_dir / rel).read_bytes()
        if rel == "ui.js":
            data = adapt_ui(data.decode("utf-8")).encode("utf-8")
        if rel == "newtab.html":
            raise ValueError("Core new-tab source must not be copied from Workspace AI")
        if rel in ("hub.html", "sidebar.html"):
            html = data.decode("utf-8")
            container = '<main class="shell">' if rel == "hub.html" else '<main class="side-shell">'
            check(html.count(container) == 1, "Companion page structure changed: " + rel)
            banner = ('<div class="frame" role="note" '
                      'style="padding:12px;margin-bottom:12px;border-color:#aa83ad">'
                      'UNSIGNED UNIFIED PREVIEW — Google OAuth/account operations '
                      'and automatic update checks are disabled until separately reviewed.'
                      '</div>')
            html = html.replace(container, container + "\n" + banner, 1)
            if rel == "hub.html":
                # Stage 6.1 is a reviewed *companion-only* OAuth pilot. The
                # current unified v0.5.6 manifest has no identity grant and
                # must not expose a nonfunctional login or start OAuth.
                master_script = '<script defer src="google/master-ui.js"></script>'
                master_panel = '<section class="frame master-panel"'
                check(html.count(master_script) == html.count(master_panel) == 1,
                      "Google Master preview UI structure changed")
                html = html.replace(master_script, "")
                html = html.replace(master_panel,
                    '<section class="frame master-panel" hidden aria-hidden="true"', 1)
            if rel == "sidebar.html":
                # Settings are shared with the Hub; keep all existing inputs and
                # handlers available but give the narrow sidebar a chat-first view.
                start = '<form id="ai-settings-form" class="ai-form">'
                end = '  </section>\n    <section class="conversation-panel"'
                check(html.count(start) == html.count(end) == 1,
                      "Sidebar provider settings structure changed")
                html = html.replace(start,
                    '<details class="unified-provider-settings">\n'
                    '<summary>PROVIDER &amp; API KEY SETTINGS</summary>\n'
                    '<p class="quiet">Shared with Workspace Hub. Expand to configure or clear a session key.</p>\n'
                    + start, 1)
                html = html.replace(end,
                    '  </section>\n</details>\n    <section class="conversation-panel"', 1)
            css_link = '<link rel="stylesheet" href="ui.css">'
            check(html.count(css_link) == 1,
                  "Companion page stylesheet changed: " + rel)
            html = html.replace(css_link, css_link +
                '<link rel="stylesheet" href="unified/ui-polish.css">', 1)
            data = html.encode("utf-8")
        inventory[rel] = data
    # Preview-only copy: remove references to a separate companion installation
    # while preserving the original core dashboard source byte-for-byte.
    station_html = inventory["newtab.html"].decode("utf-8")
    station_js = inventory["newtab.js"].decode("utf-8")
    script_tag = '<script defer src="workspace/bridge.js"></script>'
    check(station_html.count(script_tag) == 1, "Core bridge include changed")
    station_html = station_html.replace(script_tag,
        '<script defer src="unified/module.js"></script>\n' + script_tag)
    tool_button = '<button id="ask-ayarime-toggle"'
    check(station_html.count(tool_button) == 1, "Station assistant control changed")
    toggle_html = (
        '<button id="ai-module-toggle" class="settings-toggle" type="button" '
        'aria-pressed="false" disabled>✧ ENABLE AYARIME AI</button>\n'
    )
    station_html = station_html.replace(tool_button, toggle_html + '          ' + tool_button)
    label = '<p id="workspace-bridge-status"'
    check(station_html.count(label) == 1, "Core bridge status element changed")
    station_html = station_html.replace(label,
        '<p id="ai-module-status" class="workspace-bridge-status" '
        'role="status" aria-live="polite"></p>\n      ' + label)
    inventory["unified/ui-polish.css"] = (
        ROOT / "unified-preview" / "ui-polish.css").read_bytes()
    inventory["unified/module.js"] = (
        ROOT / "unified-preview" / "module.js").read_bytes()
    # Inert by design: bundled for contract review and tests, NOT injected into
    # the page or background until OAuth scopes and host allowlists are accepted.
    inventory["unified/google-worker-contract.js"] = (
        ROOT / "unified-preview" / "google-worker-contract.js").read_bytes()
    copy = {
        "Restore Google workspace using optional companion":
            "Open your integrated Ayarime Workspace Hub",
        "Focus the optional Workspace AI conversation":
            "Open the integrated Ayarime AI console",
    }
    for before, after in copy.items():
        check(station_html.count(before) == 1,
              "Core Station UI label changed: " + before)
        station_html = station_html.replace(before, after)
    labels = {
        "OPTIONAL WORKSPACE AI COMPANION": "INTEGRATED AYARIME WORKSPACE",
        "FOCUS OPTIONAL COMPANION PROMPT": "FOCUS AYARIME AI CONSOLE",
        "FIREFOX COMPANION / SUPER TAB": "AYARIME / WORKSPACE HUB",
        "FOCUS COMPANION / PINNED HUB": "AYARIME / PINNED HUB",
    }
    for before, after in labels.items():
        check(station_js.count(before) == 1,
              "Core Station command copy changed: " + before)
        station_js = station_js.replace(before, after)
    inventory["newtab.html"] = station_html.encode("utf-8")
    inventory["newtab.js"] = station_js.encode("utf-8")
    inventory["manifest.json"] = (json.dumps(manifest, indent=2, ensure_ascii=False)
                                   + "\n").encode("utf-8")
    inventory["workspace/bridge.js"] = (
        ROOT / "unified-preview" / "bridge.js").read_bytes()
    inventory["workspace-ai-background.js"] = adapt_background(
        (companion_dir / "background.js").read_text(encoding="utf-8")
    ).encode("utf-8")
    for rel, data in sorted(inventory.items()):
        destination = STAGING / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(OUTPUT, "w", ZIP_DEFLATED, compresslevel=9) as archive:
        for rel, data in sorted(inventory.items()):
            info = ZipInfo(rel, STAMP)
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, data, compress_type=ZIP_DEFLATED, compresslevel=9)
    with ZipFile(OUTPUT) as archive:
        check(set(archive.namelist()) == set(inventory), "Preview package inventory mismatch")
        check(all(archive.read(name) == data for name, data in inventory.items()),
              "Preview ZIP bytes differ from staged source")
        check(archive.testzip() is None, "Preview ZIP CRC mismatch")
    print("UNSIGNED, development only:", OUTPUT)
    print("Core identity:", manifest["browser_specific_settings"]["gecko"]["id"])
    print("Companion pinned commit:", COMPANION_COMMIT)
    print("Runtime files:", len(inventory))
    print("SHA256:", hashlib.sha256(OUTPUT.read_bytes()).hexdigest())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--companion", required=True, type=Path,
                        help="Exact, separately checked-out Workspace AI source tree")
    args = parser.parse_args()
    try:
        build(args.companion.resolve())
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        raise SystemExit("Unified preview build refused: " + str(error))
