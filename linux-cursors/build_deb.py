#!/usr/bin/env python3
"""Package the existing seven Ayarime Xcursor themes as a native Debian .deb.

This installs *only* cursor themes in /usr/share/icons through the ordinary
package manager. No postinst/prerm scripts, background service, automatic
cursor activation, Firefox changes, or spelling interception are included.
Build the theme archive first using linux-cursors/build.py.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "dist" / "linux-cursors" / "Ayarime-Cursors" / "themes"
OUTPUT = ROOT / "dist" / "linux-cursors"
VERSION = "0.1.0-1"
PACKAGE = f"ayarime-cursors_{VERSION}_all.deb"
IDENTITY = "ayarime-cursors-v1"
VARIANTS = (
    "Ayarime-Core",
    "Ayarime-Classic-Spearhead",
    "Ayarime-Crystal-Tech-Shard",
    "Ayarime-Elven-Feather",
    "Ayarime-Hollow-Frame",
    "Ayarime-Rune-Edged",
    "Ayarime-Minimal-Precision",
)
CURSORS = (
    "left_ptr", "xterm", "watch", "crosshair", "size_fdiag", "hand2",
)


def validate_theme(theme: Path) -> None:
    if theme.is_symlink() or not theme.is_dir():
        raise ValueError(f"Missing/linked theme directory: {theme}")
    if (theme / ".ayarime-cursor-theme").read_text().strip() != IDENTITY:
        raise ValueError(f"Theme identity mismatch: {theme}")
    if "Inherits=Adwaita" not in (theme / "index.theme").read_text():
        raise ValueError(f"Adwaita fallback missing in {theme}")
    for cursor in CURSORS:
        path = theme / "cursors" / cursor
        if path.is_symlink() or not path.is_file() or path.read_bytes()[:4] != b"Xcur":
            raise ValueError(f"Missing/invalid Xcursor: {path}")
    for path in theme.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"Refusing linked archive path: {path}")


def build() -> Path:
    if not shutil.which("dpkg-deb"):
        raise RuntimeError("dpkg-deb is required (package: dpkg)")
    if not SOURCE.is_dir():
        raise RuntimeError("First run: python3 linux-cursors/build.py")
    actual = {p.name for p in SOURCE.iterdir()}
    if actual != set(VARIANTS):
        raise ValueError(f"Unexpected theme set: {sorted(actual)}")
    for name in VARIANTS:
        validate_theme(SOURCE / name)

    OUTPUT.mkdir(parents=True, exist_ok=True)
    output = OUTPUT / PACKAGE
    with tempfile.TemporaryDirectory(prefix="ayarime-deb-") as tmp:
        stage = Path(tmp) / "ayarime-cursors"
        cursor_root = stage / "usr" / "share" / "icons"
        cursor_root.mkdir(parents=True)
        for name in VARIANTS:
            shutil.copytree(SOURCE / name, cursor_root / name, symlinks=False)

        doc = stage / "usr" / "share" / "doc" / "ayarime-cursors"
        doc.mkdir(parents=True)
        shutil.copyfile(ROOT / "linux-cursors" / "README.md", doc / "README.md")
        shutil.copyfile(ROOT / "ARTWORK_LICENSE.md", doc / "ARTWORK_LICENSE.md")
        (doc / "README.Debian").write_text(
            "Ayarime cursor theme package for Linux Mint/Cinnamon.\n"
            "Use Themes -> Mouse Pointer to select a theme manually.\n"
            "This package does not change system settings, update services,\n"
            "Firefox, spellchecking or the current cursor selection.\n"
            "Removal with the package manager removes only installed themes.\n",
            encoding="utf-8",
        )
        control = stage / "DEBIAN"
        control.mkdir()
        (control / "control").write_text(
            f"Package: ayarime-cursors\nVersion: {VERSION}\n"
            "Section: x11\nPriority: optional\nArchitecture: all\n"
            "Maintainer: ELF//SHELL Ayarime contributors\n"
            "Homepage: https://github.com/cryogenized-spec/elf-shell-ayarime\n"
            "Description: Ayarime Xcursor themes for Linux Mint/Cinnamon\n"
            " Seven optional native pointer themes generated from ELF//SHELL\n"
            " Ayarime artwork. Includes core pointer, text, link, busy,\n"
            " crosshair and diagonal-resize states; Adwaita fallback.\n"
            " No services, global keyboard hooks or configuration changes.\n",
            encoding="utf-8",
        )
        if any(p.name.startswith(("post", "pre")) for p in control.iterdir()):
            raise AssertionError("Maintainer scripts must not be included")
        for path in stage.rglob("*"):
            if path.is_symlink():
                raise ValueError(f"Unexpected symlink in package: {path}")
            path.chmod(0o755 if path.is_dir() else 0o644)
        env = os.environ.copy()
        env.setdefault("SOURCE_DATE_EPOCH", "1762800000")
        subprocess.run(
            ["dpkg-deb", "--build", "--root-owner-group", str(stage), str(output)],
            check=True,
            env=env,
        )
    print(f"Built {output} ({output.stat().st_size:,} bytes)")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    build()
