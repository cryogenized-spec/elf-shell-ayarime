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

COMPANION_COMMIT = "3c678bda35a64fe185135eb1b937e2d5eb26d810"
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
    """Keep companion top-level declarations separate from core's background script."""
    original = (
        'browser.runtime.onMessage.addListener((message,sender) => {\n'
        '  if (sender.id !== browser.runtime.id) return {ok:false,error:"Unauthorized sender"};\n'
        '  return handle(message);\n'
        '});'
    )
    check(source.count(original) == 1,
          "Companion background listener changed: manual review required")
    section = source.split("async function handle(message) {", 1)
    check(len(section) == 2, "Could not find companion handler")
    body = section[1].split(original, 1)[0]
    types = sorted(set(re.findall(r'case "([A-Z][A-Z0-9_]+)":', body)))
    check(len(types) >= 20 and "GOOGLE_AUTH_PREPARE" in types
          and "OPEN_WORKSPACE" in types and "AI_SEND_PROMPT" in types,
          "Companion message router changed: review required")
    guarded = (
        'const WORKSPACE_MESSAGE_TYPES = new Set(' + json.dumps(types) + ');\n'
        'browser.runtime.onMessage.addListener((message,sender) => {\n'
        '  if (message?.type==="elfshell:unified:bridge:v1") '
        'return handleUnifiedBridge(message,sender);\n'
        '  if (sender?.id !== browser.runtime.id || '
        ' !WORKSPACE_MESSAGE_TYPES.has(message?.type)) return undefined;\n'
        '  if (message.type.startsWith("GOOGLE_") || '
        'message.type==="MORNING_COFFEE_PREPARE" || '
        'message.type.startsWith("UPDATE_"))\n'
        '    return {ok:false,error:"Google OAuth and update checks are disabled '
        'in this unsigned unified preview."};\n'
        '  return handle(message);\n'
        '});'
    )
    source = source.replace(original, guarded)
    # Firefox action clicks remain user-initiated. Require the optional
    # tab/group grants before restoring any tabs.
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
    adapter = r"""
// Same-extension bridge, dispatched by the already-working companion listener.
// Only the core's own newtab.html may invoke these allowlisted commands.
function handleUnifiedBridge(message, sender) {
  if (message?.type !== "elfshell:unified:bridge:v1") return undefined;
  const caller = browser.runtime.getURL("newtab.html");
  if (sender?.id !== browser.runtime.id || sender?.url !== caller)
    return {ok:false,error:"Unauthorized dashboard sender"};
  if (message.kind !== "elfshell.workspace.bridge" || message.version !== 1 ||
      !["HELLO","OPEN_ASSISTANT","OPEN_WORKSPACE"].includes(message.command) ||
      Object.keys(message).some(key=>!["type","kind","version","command"].includes(key)))
    return {ok:false,error:"Unsupported unified bridge request"};
  if (message.command === "HELLO")
    return {ok:true,kind:"elfshell.workspace.bridge",version:1,
      capabilities:["OPEN_ASSISTANT","OPEN_WORKSPACE"],dataAccess:"browser-tabs-only"};
  if (message.command === "OPEN_ASSISTANT")
    return serialise(focusAssistant)
      .then(result=>({ok:true,result}),()=>({ok:false,error:"Could not focus AI Hub"}));
  return handle({type:"OPEN_WORKSPACE"});
}
"""
    # Register the reviewed internal adapter before optional companion event
    # handlers so an unrelated/unsupported add-on API cannot block handoff.
    marker = "// Versioned, tightly scoped communication with the independently installed ELF//SHELL core."
    check(source.count(marker) == 1, "Legacy external bridge location changed")
    source = source.replace(marker, adapter + "\n" + marker, 1)
    external = (
        'browser.runtime.onMessageExternal.addListener((message, sender) =>\n'
        '  handleCoreMessage(message, sender).catch(() => ({ok:false,error:"Bridge request failed"}))\n'
        ');'
    )
    check(source.count(external) == 1, "Companion external listener changed")
    source = source.replace(external, "// Disabled: one-extension build has no external connection.")
    # This IIFE prevents conflicting global 'const' names in the two backgrounds.
    return '(function(){\n"use strict";\n' + source + '\n})();\n'


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
        if rel in ("hub.html", "sidebar.html"):
            html = data.decode("utf-8")
            container = '<main class="shell">' if rel == "hub.html" else '<main class="side-shell">'
            check(html.count(container) == 1, "Companion page structure changed: " + rel)
            banner = ('<div class="frame" role="note" '
                      'style="padding:12px;margin-bottom:12px;border-color:#aa83ad">'
                      'UNSIGNED UNIFIED PREVIEW — Google OAuth/account operations '
                      'and automatic update checks are disabled until separately reviewed.'
                      '</div>')
            data = html.replace(container, container + "\n" + banner, 1).encode("utf-8")
        inventory[rel] = data
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
