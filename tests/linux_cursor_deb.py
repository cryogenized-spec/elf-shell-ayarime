#!/usr/bin/env python3
"""Check native cursor .deb installs only the intended static Xcursor assets."""
from __future__ import annotations
from pathlib import Path
import subprocess
import tempfile
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "linux-cursors"))
import build_deb

archive = build_deb.build()
result = subprocess.run(["dpkg-deb", "--field", str(archive)],
                        capture_output=True, text=True, check=True).stdout
assert "Package: ayarime-cursors" in result
assert "Architecture: all" in result
assert "Version: 0.1.0-1" in result

with tempfile.TemporaryDirectory(prefix="ayarime-deb-qa-") as directory:
    dest = Path(directory)
    subprocess.run(["dpkg-deb", "--extract", str(archive), str(dest)],
                   check=True)
    cursor_root = dest / "usr" / "share" / "icons"
    assert {p.name for p in cursor_root.iterdir()} == set(build_deb.VARIANTS)
    for name in build_deb.VARIANTS:
        build_deb.validate_theme(cursor_root / name)

    listing = subprocess.run(["dpkg-deb", "--contents", str(archive)],
                             capture_output=True, text=True, check=True).stdout
    assert "./DEBIAN/" not in listing
    assert "usr/share/icons" in listing
    assert "usr/share/doc/ayarime-cursors/" in listing
    assert "etc/" not in listing
    assert "usr/bin/" not in listing
    assert "usr/lib/systemd/" not in listing
    assert "etc/xdg/" not in listing

    control = dest / "metadata"
    control.mkdir()
    subprocess.run(["dpkg-deb", "--control", str(archive), str(control)],
                   check=True)
    assert sorted(p.name for p in control.iterdir()) == ["control"]
    assert not any(dest.rglob("postinst"))
    assert not any(dest.rglob("prerm"))
print("PASS: seven themes, unmodified native cursor assets, no scripts or autostart")
