#!/usr/bin/env python3
"""Build an unsigned one-extension preview from this ONE repository.

The Ayarime assistant lives in assistant/. No second GitHub checkout,
remote network, GitHub token or separate version pin is required.
The existing public AMO manifest and installed add-ons are never modified.
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
    # The original import is recorded for history, NOT frozen forever. Future
    # feature edits change assistant/ directly in the same repository.
    check(folder.resolve() == (ROOT / "assistant").resolve(),
          "Use only the vendored assistant/ folder in this repository")
    check(folder.is_dir(), "Integrated assistant/ source missing")
    provenance = json.loads((folder / "SOURCE_LOCK.json").read_text(encoding="utf-8"))
    check(provenance.get("source_repository") ==
          "cryogenized-spec/elf-shell-workspace-ai" and
          provenance.get("source_commit") == COMPANION_COMMIT and
          provenance.get("import_path") == "assistant",
          "Assistant import provenance has changed: review required")


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


def combine_manifest(core: dict, companion: dict, enable_google_master: bool = False) -> dict:
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
    # The Firefox identity API is mandatory for launchWebAuthFlow. Add it ONLY
    # in the explicitly selected engineering build, never in the default/AMO RC.
    manifest["permissions"] = list(core["permissions"]) + (["identity"] if enable_google_master else [])
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


def adapt_background(source: str, enable_google_master: bool = False) -> str:
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
    # Keep the default build byte-for-byte safe. Only the explicitly selected
    # engineering package lifts the Master-only command block; desktop Google
    # REST OAuth, update checks and all other unrelated routes remain blocked.
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


def build(companion_dir: Path, enable_google_master: bool = False) -> None:
    checked_companion(companion_dir)
    files = companion_inventory(companion_dir)
    core_manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    companion_manifest = json.loads((companion_dir / "manifest.json").read_text(encoding="utf-8"))
    manifest = combine_manifest(core_manifest, companion_manifest, enable_google_master)
    # Neither the default preview nor the opt-in engineering build may
    # bundle the owner's pinned Cloudflare transport or its host grants.
    private = {"google/master-read-client.js", "google/master-oauth.js"}
    manifest["background"]["scripts"] = [
        p for p in manifest["background"]["scripts"] if p not in private
    ]
    manifest["optional_host_permissions"] = [
        p for p in manifest["optional_host_permissions"]
        if "cryogenized.workers.dev" not in p
    ]
    # Never overwrite or mutate the separately reviewed default-off RC package.
    staging = ROOT / "dist" / ("unified-google-master-preview" if enable_google_master else "unified-preview")
    output = ROOT / "dist" / ("ELF-SHELL-Ayarime-Google-Master-UNSIGNED.xpi" if enable_google_master else "ELF-SHELL-Ayarime-unified-UNSIGNED.xpi")
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    inventory: dict[str, bytes] = {}
    for source in core_sources():
        rel = source.relative_to(ROOT).as_posix()
        inventory[rel] = source.read_bytes()
    for rel in files:
        if rel in ("manifest.json", "background.js"):
            continue
        if rel in {
            "google/master-read-client.js", "google/master-oauth.js",
            "google/master-ui.js"
        }:
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
                      + ('UNSIGNED GOOGLE MASTER ENGINEERING PREVIEW — the '
                         'Google Master OAuth connect and capability probe are '
                         'manual. No Google account contents are fetched at startup; '
                         'direct Google REST OAuth and automatic update checks '
                         'remain disabled.'
                         if enable_google_master else
                         'UNSIGNED UNIFIED PREVIEW — Google OAuth/account operations '
                         'and automatic update checks are disabled until separately reviewed.')
                      + '</div>')
            html = html.replace(container, container + "\n" + banner, 1)
            if rel == "hub.html":
                # Historical pinned Cloudflare panel is never active in the
                # new public-facing user-owned engineering configuration.
                master_script = '<script defer src="google/master-ui.js"></script>'
                master_panel = '<section class="frame master-panel"'
                check(html.count(master_script) == html.count(master_panel) == 1,
                      "Private Master panel structure changed")
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
        '<link rel="stylesheet" href="unified/station-drawer.css">\n'
        '<script defer src="unified/module.js"></script>\n'
        '<script defer src="unified/station-drawer.js"></script>\n'
        + script_tag)
    tool_button = '<button id="ask-ayarime-toggle"'
    check(station_html.count(tool_button) == 1, "Station assistant control changed")
    toggle_html = (
        '<button id="ai-module-toggle" class="settings-toggle" type="button" '
        'aria-pressed="false" disabled>✧ ENABLE AYARIME AI</button>\n'
    )
    station_html = station_html.replace(tool_button, toggle_html + '          ' + tool_button)
    if enable_google_master:
        # Integrated Station navigation only in the opt-in engineering build;
        # no new extension, no separate credential store and no auto-connection.
        # Navigate within the SAME extension instead of requiring an opaque
        # moz-extension:// URL or requesting unrelated tab permissions.
        station_link = (
            '<a id="google-master-toggle" class="settings-toggle station-story-launch" '
            'type="button" '
            'aria-label="Google Master MCP private connection">'
            '✧ GOOGLE MASTER / MCP</button>\\n'
        )
        check(station_html.count(tool_button) == 1,
              "Station Google Master navigation insertion point changed")
        station_html = station_html.replace(tool_button, station_link + '          ' + tool_button)
        station_label = '10 TOOLS · CTRL+K'
        check(station_html.count(station_label) == 1,
              "Station tool count label changed")
        station_html = station_html.replace(station_label, '11 TOOLS · CTRL+K', 1)
    label = '<p id="workspace-bridge-status"'
    check(station_html.count(label) == 1, "Core bridge status element changed")
    station_html = station_html.replace(label,
        '<p id="ai-module-status" class="workspace-bridge-status" '
        'role="status" aria-live="polite"></p>\n      ' + label)
    inventory["unified/ui-polish.css"] = (
        ROOT / "unified-preview" / "ui-polish.css").read_bytes()
    inventory["unified/module.js"] = (
        ROOT / "unified-preview" / "module.js").read_bytes()
    inventory["unified/station-drawer.js"] = (
        ROOT / "unified-preview" / "station-drawer.js").read_bytes()
    inventory["unified/station-drawer.css"] = (
        ROOT / "unified-preview" / "station-drawer.css").read_bytes()
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
    drawer = (ROOT / "unified-preview" / "station-drawer.html").read_text(encoding="utf-8")
    check(station_html.count("<body>") == 1, "ELF Station body markup changed")
    station_html = station_html.replace("<body>", "<body>\n" + drawer, 1)
    inventory["newtab.html"] = station_html.encode("utf-8")
    inventory["newtab.js"] = station_js.encode("utf-8")
    inventory["manifest.json"] = (json.dumps(manifest, indent=2, ensure_ascii=False)
                                   + "\n").encode("utf-8")
    inventory["workspace/bridge.js"] = (
        ROOT / "unified-preview" / "bridge.js").read_bytes()
    inventory["workspace-ai-background.js"] = adapt_background(
        (companion_dir / "background.js").read_text(encoding="utf-8"),
        enable_google_master=enable_google_master
    ).encode("utf-8")
    for rel, data in sorted(inventory.items()):
        destination = staging / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", ZIP_DEFLATED, compresslevel=9) as archive:
        for rel, data in sorted(inventory.items()):
            info = ZipInfo(rel, STAMP)
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, data, compress_type=ZIP_DEFLATED, compresslevel=9)
    with ZipFile(output) as archive:
        check(set(archive.namelist()) == set(inventory), "Preview package inventory mismatch")
        check(all(archive.read(name) == data for name, data in inventory.items()),
              "Preview ZIP bytes differ from staged source")
        check(archive.testzip() is None, "Preview ZIP CRC mismatch")
    print("UNSIGNED, development only:", output)
    print("Core identity:", manifest["browser_specific_settings"]["gecko"]["id"])
    print("Historical assistant import commit:", COMPANION_COMMIT)
    print("Runtime files:", len(inventory))
    print("SHA256:", hashlib.sha256(output.read_bytes()).hexdigest())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    # Source-of-truth is always the local assistant/ directory.
    parser.add_argument("--enable-google-master", action="store_true",
                        help="Prepare separate unsigned Firefox build with explicit identity permission, manual Google Master OAuth and capability probe (NEVER an AMO build)")
    args = parser.parse_args()
    try:
        build(ROOT / "assistant", enable_google_master=args.enable_google_master)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        raise SystemExit("Unified preview build refused: " + str(error))
