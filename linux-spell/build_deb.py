#!/usr/bin/python3
"""Build the optional Ayarime local spell-assistance .deb (no startup hooks)."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "linux-spell"
OUTPUT = ROOT / "dist" / "linux-spell"
VERSION = "0.1.0-1"
NAME = f"ayarime-spell_{VERSION}_all.deb"

LAUNCHER = """#!/usr/bin/python3
import runpy
import sys
sys.path.insert(0, "/usr/lib/ayarime-spell")
runpy.run_path("/usr/lib/ayarime-spell/app.py", run_name="__main__")
"""

DESKTOP = """[Desktop Entry]
Type=Application
Name=Ayarime Spell · Left-Click Corrections
Comment=Opt-in local Enchant suggestions in compatible Linux text fields
Exec=ayarime-spell --language en_GB
Terminal=false
Categories=Utility;Accessibility;
StartupNotify=false
"""

CONTROL = f"""Package: ayarime-spell
Version: {VERSION}
Section: utils
Priority: optional
Architecture: all
Maintainer: ELF//SHELL Ayarime contributors
Depends: python3 (>= 3.12), python3-gi, gir1.2-gtk-3.0, gir1.2-atspi-2.0, python3-enchant, python3-xlib, at-spi2-core
Recommends: hunspell-en-gb
Homepage: https://github.com/cryogenized-spec/elf-shell-ayarime
Description: Opt-in local Linux spell correction on left click
 A small GTK/AT-SPI helper using locally installed Enchant dictionaries.
 The user must explicitly activate it after launching the UI. It listens
 for focus and X11 button releases only, never keyboard contents.
 It does not change Firefox native context menus or run at login.
"""


def build() -> Path:
    if not shutil.which("dpkg-deb"):
        raise RuntimeError("Missing dpkg-deb")
    for name in ("app.py", "core.py", "x11_click.py", "README.md"):
        if not (SOURCE / name).is_file() or (SOURCE / name).is_symlink():
            raise RuntimeError("Invalid spell source " + name)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    result = OUTPUT / NAME
    with tempfile.TemporaryDirectory(prefix="ayarime-spell-") as tmp:
        stage = Path(tmp) / "package"
        lib = stage / "usr" / "lib" / "ayarime-spell"
        lib.mkdir(parents=True)
        for name in ("app.py", "core.py", "x11_click.py"):
            shutil.copyfile(SOURCE / name, lib / name)
        bindir = stage / "usr" / "bin"
        bindir.mkdir(parents=True)
        (bindir / "ayarime-spell").write_text(LAUNCHER, encoding="utf-8")
        applications = stage / "usr" / "share" / "applications"
        applications.mkdir(parents=True)
        (applications / "ayarime-spell.desktop").write_text(
            DESKTOP, encoding="utf-8"
        )
        doc = stage / "usr" / "share" / "doc" / "ayarime-spell"
        doc.mkdir(parents=True)
        shutil.copyfile(SOURCE / "README.md", doc / "README.md")
        shutil.copyfile(ROOT / "LICENSE", doc / "LICENSE")
        control = stage / "DEBIAN"
        control.mkdir()
        (control / "control").write_text(CONTROL, encoding="utf-8")
        for item in stage.rglob("*"):
            if item.is_symlink():
                raise RuntimeError("Refusing package symlink")
            item.chmod(
                0o755 if item.is_dir() or item.name == "ayarime-spell" else 0o644
            )
        if sorted(x.name for x in control.iterdir()) != ["control"]:
            raise AssertionError("Ayarime Spell must not include maintainer scripts")
        env = os.environ.copy()
        env.setdefault("SOURCE_DATE_EPOCH", "1762800000")
        subprocess.run(
            ["dpkg-deb", "--build", "--root-owner-group", str(stage), str(result)],
            check=True, env=env,
        )
    print(f"Built {result} ({result.stat().st_size:,} bytes)")
    return result


if __name__ == "__main__":
    build()
