#!/usr/bin/env python3
"""Import reviewed Ayarime art masters without committing, merging or publishing.

Usage: python3 stories/import_assets.py /path/to/ELF-SHELL-Ayarime-Side-Stories-PR22-Handoff.zip
Requires the handoff ZIP and stories/asset-manifest.json from this exact PR.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "stories" / "asset-manifest.json"
TARGET = ROOT / "stories" / "assets"


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 stories/import_assets.py PATH_TO_HANDOFF_ZIP")
    source = Path(sys.argv[1])
    if not source.is_file():
        raise SystemExit(f"Missing handoff archive: {source}")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if not manifest.get("requiresExplicitHumanMergeApproval"):
        raise SystemExit("Refusing import: merge-approval gate missing")
    staged = []
    with zipfile.ZipFile(source) as archive:
        if archive.testzip() is not None:
            raise SystemExit("Archive CRC validation failed")
        for story in manifest["stories"]:
            for record in story["artwork"]:
                repo_name = record["proposedRepoPath"]
                prefix = "stories/assets/"
                if not repo_name.startswith(prefix):
                    raise SystemExit("Asset path must be inside stories/assets")
                filename = Path(repo_name).name
                if filename != repo_name[len(prefix):] or "/" in filename or "\\" in filename:
                    raise SystemExit("Unsafe asset path")
                entry = "assets/" + filename
                blob = archive.read(entry)
                if len(blob) != record["bytes"]:
                    raise SystemExit(f"Incorrect byte count: {entry}")
                if hashlib.sha256(blob).hexdigest() != record["sha256"]:
                    raise SystemExit(f"Hash mismatch (art changed): {entry}")
                if not blob.startswith(b"\x89PNG\r\n\x1a\n"):
                    raise SystemExit(f"Not PNG: {entry}")
                staged.append((filename, blob))
    TARGET.mkdir(parents=True, exist_ok=True)
    for name, blob in staged:
        dest = TARGET / name
        if dest.exists() and dest.read_bytes() != blob:
            raise SystemExit(f"Existing asset differs: {name}")
        dest.write_bytes(blob)
        print(f"Staged verified original: {dest.relative_to(ROOT)}")
    print("\nNo commit, PR merge, release build, or Mozilla submission was performed.")
    print("⛔ Human approval required before any merge or publication.")


if __name__ == "__main__":
    main()
