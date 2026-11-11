#!/usr/bin/python3
"""Verify spell .deb content, no root hooks, no autostart, and a small payload."""
from pathlib import Path
import subprocess
import tempfile
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "linux-spell"))
import build_deb

package = build_deb.build()
assert package.stat().st_size < 128 * 1024, "The helper should remain lightweight"
info = subprocess.run(
    ["dpkg-deb", "--field", str(package)],
    check=True, text=True, capture_output=True,
).stdout
assert "Package: ayarime-spell" in info
assert "Architecture: all" in info
assert "python3-enchant" in info
assert "gir1.2-atspi-2.0" in info
assert "hunspell-en-gb" in info

with tempfile.TemporaryDirectory(prefix="ayarime-spell-check-") as tmp:
    root = Path(tmp)
    subprocess.run(["dpkg-deb", "--extract", str(package), str(root)],
                   check=True)
    py = root / "usr/lib/ayarime-spell"
    assert sorted(p.name for p in py.iterdir()) == ["app.py", "core.py"]
    assert (root / "usr/bin/ayarime-spell").is_file()
    assert "Exec=ayarime-spell" in (
        root / "usr/share/applications/ayarime-spell.desktop"
    ).read_text()
    assert not any(p.name.endswith(".service") for p in root.rglob("*"))
    assert not any("autostart" in p.parts for p in root.rglob("*"))
    control = root / "DEBIAN"
    control.mkdir()
    subprocess.run(["dpkg-deb", "--control", str(package), str(control)],
                   check=True)
    assert [p.name for p in control.iterdir()] == ["control"]
    source = (py / "app.py").read_text()
    assert "mouse:b1r" in source
    assert "set_active" in source  # Opt-in button only
    assert "key:" not in source
    for forbidden_import in ("import requests", "import socket", "import urllib", "import pynput"):
        assert forbidden_import not in source
print("PASS: small offline native spell package with explicit opt-in, no services")
