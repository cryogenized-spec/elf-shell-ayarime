#!/usr/bin/env python3
"""Build reproducible unsigned v0.5.6 unified RC and reviewer source archives.

Never signs, submits to Mozilla, touches an installed Firefox profile, or
activates Google accounts. Builds exclusively from current tracked core files
including its locally maintained assistant/ subtree.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_unified_preview as unified

VERSION = "0.5.6"
DIST = ROOT / "dist"
STAGE = DIST / "unified-rc"
ZIP = DIST / f"ELF-SHELL-Ayarime-v{VERSION}-unified-RC-UNSIGNED.zip"
XPI = DIST / f"ELF-SHELL-Ayarime-v{VERSION}-unified-RC-UNSIGNED.xpi"
SOURCE = DIST / f"ELF-SHELL-Ayarime-v{VERSION}-unified-RC-source.zip"
REPORT = DIST / "unified-rc-evidence.json"
DATE = (2026, 11, 13, 0, 0, 0)
OPTIONAL_DATA = ["authenticationInfo", "personalCommunications",
                 "websiteContent", "personallyIdentifyingInfo"]
BANNER = ('<div class="frame" role="note" '
          'style="padding:12px;margin-bottom:12px;border-color:#aa83ad">'
          'UNSIGNED UNIFIED PREVIEW — Google OAuth/account operations '
          'and automatic update checks are disabled until separately reviewed.'
          '</div>')


def check(condition: bool, problem: str) -> None:
    if not condition:
        raise ValueError(problem)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def tracked(base: Path) -> list[str]:
    value = subprocess.check_output(["git", "-C", str(base), "ls-files", "-z"])
    names = sorted(x.decode("utf-8") for x in value.split(b"\0") if x)
    check(bool(names) and len(names) == len(set(names)), "Invalid tracked file set")
    blocked = (".env", ".pem", ".key", "id_rsa", "node_modules/", "dist/",
               ".git/", "__pycache__/", "credentials.json")
    for name in names:
        p = base / name
        check(not p.is_symlink() and p.is_file(), "Missing/unsafe source: " + name)
        check(not any(name == b or name.startswith(b) or name.endswith(b)
                      for b in blocked), "Secret or generated file tracked: " + name)
    return names


def archive(out: Path, entries: dict[str, bytes]) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(out, "w", ZIP_DEFLATED, compresslevel=9) as z:
        for name, content in sorted(entries.items()):
            check(not name.startswith("/") and ".." not in Path(name).parts,
                  "Invalid archive path")
            info = ZipInfo(name, DATE)
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, content, compress_type=ZIP_DEFLATED, compresslevel=9)
    with ZipFile(out) as z:
        check(z.namelist() == sorted(entries) and z.testzip() is None,
              "Archive structure/CRC mismatch")
        check(all(z.read(name) == data for name, data in entries.items()),
              "Archive was not byte-for-byte reproducible")


def release(companion: Path) -> None:
    # This verifies the local assistant import and both runtime whitelists.
    unified.build(companion)
    check(unified.STAGING.is_dir(), "Missing integrated source stage")
    check(unified.OUTPUT.is_file(), "Missing integrated development XPI")
    src = unified.STAGING
    if STAGE.exists():
        shutil.rmtree(STAGE)
    shutil.copytree(src, STAGE)
    manifest_file = STAGE / "manifest.json"
    m = json.loads(manifest_file.read_text(encoding="utf-8"))
    core = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    check(core["version"] == m["version"] == VERSION, "Wrong release version")
    check(m["browser_specific_settings"]["gecko"]["id"] ==
          core["browser_specific_settings"]["gecko"]["id"] ==
          "elf-shell-ayarime@local.theme", "Firefox add-on ID changed")
    check(set(m["permissions"]) == {"theme", "search", "storage"},
          "Required Firefox permissions increased")
    check(set(m.get("optional_permissions", [])) >=
          {"tabs", "tabGroups", "sessions", "bookmarks", "history"},
          "Missing reviewed optional browser permission")
    check("externally_connectable" not in m, "Unexpected external bridge")
    check(m.get("content_security_policy") == core.get("content_security_policy"),
          "Core content security policy changed")
    dc = m["browser_specific_settings"]["gecko"]["data_collection_permissions"]
    check(dc["required"] == ["none"] and set(dc["optional"]) == set(OPTIONAL_DATA),
          "Incorrect Firefox optional BYOK data declaration")
    check("workspace-ai-background.js" in m["background"]["scripts"] and
          "sidebar_action" in m, "Not a unified Firefox extension")
    m["name"] = "ELF//SHELL — Ayarime"
    m["description"] = ("Original illustrated Firefox new-tab workstation with "
                        "opt-in RSS and optional, consent-gated BYOK AI Hub/sidebar. "
                        "Google account connectivity is not enabled.")
    manifest_file.write_text(json.dumps(m, indent=2, ensure_ascii=False) + "\n",
                             encoding="utf-8")

    stylesheet = (ROOT / "unified-preview/rc.css").read_bytes()
    (STAGE / "unified/rc.css").write_bytes(stylesheet)
    for name in ("hub.html", "sidebar.html"):
        page = STAGE / name
        html = page.read_text(encoding="utf-8")
        check(html.count(BANNER) == 1, "Missing/changed development banner: " + name)
        html = html.replace(BANNER, "")
        css_link = '<link rel="stylesheet" href="unified/ui-polish.css">'
        check(html.count(css_link) == 1, "Expected unified stylesheet is missing")
        html = html.replace(css_link, css_link +
                            '<link rel="stylesheet" href="unified/rc.css">')
        if name == "sidebar.html":
            google = '<section class="frame side-panel"><p class="eyebrow">// GOOGLE AUTH</p>'
            check(html.count(google) == 1, "Google section structure changed")
            html = html.replace(google, '<section class="frame side-panel rc-unavailable" '
                                'hidden aria-hidden="true"><p class="eyebrow">// GOOGLE AUTH</p>')
        page.write_text(html, encoding="utf-8")

    background = (STAGE / "workspace-ai-background.js").read_text(encoding="utf-8")
    check("Google OAuth and update checks are disabled" in background,
          "Inactive Google/update request guard missing")
    check("UNIFIED_STREAMS" in background and
          'storage.session.remove("elfshell.byok.apiKey.v1")' in background,
          "AI shutdown does not abort streams and purge credentials")
    module = (STAGE / "unified/module.js").read_text(encoding="utf-8")
    check('type:"AI_CLEAR_SESSION_KEY"' in module,
          "The AI-off switch may retain a provider key")
    for name in ("hub.html", "sidebar.html"):
        page = (STAGE / name).read_text(encoding="utf-8")
        check('href="unified/rc.css"' in page and "UNSIGNED UNIFIED PREVIEW" not in page,
              "Old preview branding remains")
    check((STAGE / "newtab.html").read_text(encoding="utf-8").count(
        'id="ai-module-toggle"') == 1, "No opt-in station toggle")

    runtime = {p.relative_to(STAGE).as_posix(): p.read_bytes()
               for p in STAGE.rglob("*") if p.is_file()}
    archive(ZIP, runtime)
    shutil.copyfile(ZIP, XPI)
    check(sha(XPI.read_bytes()) == sha(ZIP.read_bytes()),
          "XPI and AMO ZIP differ")

    # One repo, one source archive. assistant/ is regular tracked source,
    # included exactly once alongside ELF//SHELL and the fusion script.
    core_head = subprocess.check_output(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    upstream_import = unified.COMPANION_COMMIT  # historical provenance only
    source_files = {}
    for name in tracked(ROOT):
        source_files["core/" + name] = (ROOT / name).read_bytes()
    check("core/assistant/ai/providers.js" in source_files and
          "core/assistant/google/master-oauth.js" in source_files and
          "core/assistant/SOURCE_LOCK.json" in source_files,
          "Reviewer source ZIP is missing integrated assistant sources")
    build_guide = (
        "Ayarime unified v0.5.6 reviewer source — unsigned release candidate\\n"
        "Single source Git commit: " + core_head + "\\n"
        "Historical Ayarime import commit: " + upstream_import + "\\n\\n"
        "From ONE Git checkout at the commit above, run:\\n"
        "  python3 core/scripts/build_unified_preview.py\\n"
        "  python3 core/scripts/package_unified_rc.py\\n"
        "The one repository contains both original unminified components in\\n"
        "core/ and core/assistant/ and all audited build transformations.\\n"
        "The runtime ZIP is deterministic (UTC 2026-11-13 ZIP timestamp). "
        "No AMO upload, signing or live BYOK inference is performed.\\n"
    )
    source_files["RC-BUILD-INSTRUCTIONS.txt"] = build_guide.encode("utf-8")
    archive(SOURCE, source_files)
    REPORT.write_text(json.dumps({
        "version": VERSION, "status": "UNSIGNED_RC_ONLY",
        "core_commit": core_head, "companion_commit": upstream_import,
         "source_layout": "single-repository-assistant-subtree",
        "firefox_id": m["browser_specific_settings"]["gecko"]["id"],
        "required_permissions": m["permissions"],
        "optional_data_collection": dc["optional"],
        "runtime_sha256": sha(ZIP.read_bytes()),
        "source_sha256": sha(SOURCE.read_bytes()),
        "runtime_files": len(runtime),
        "reviewer_source_files": len(source_files),
        "live_byok": "NOT_TESTED_NO_USER_KEY",
        "signed_v056": False,
        "mozilla_submitted": False,
        "google_worker_connected": False,
    }, indent=2) + "\n", encoding="utf-8")
    print("Unsigned release-candidate runtime:", ZIP)
    print("Unsigned release-candidate XPI:", XPI)
    print("Reviewable unified sources:", SOURCE)
    print("SHA-256 runtime:", sha(ZIP.read_bytes()))
    print("SHA-256 source:", sha(SOURCE.read_bytes()))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    # Reviewed assistant source is inside this repository.
    args = p.parse_args()
    try:
        release(ROOT / "assistant")
    except (ValueError, OSError, subprocess.CalledProcessError) as e:
        print("RC PACKAGING BLOCKED:", e, file=sys.stderr)
        raise SystemExit(1)
