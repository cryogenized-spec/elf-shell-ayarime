#!/usr/bin/python3
"""Synthetic end-to-end X11 acceptance: click a GTK word, select correction.

Runs only on disposable Xvfb/DBus session. No personal clipboard data is
read; no global desktop state is changed.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
NAME = "Ayarime Synthetic Spell Field"


def editor(result_path: Path):
    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk
    window = Gtk.Window(title=NAME)
    window.set_default_size(360, 100)
    entry = Gtk.Entry()
    entry.set_text("teh")
    entry.connect(
        "changed", lambda widget: result_path.write_text(
            widget.get_text(), encoding="utf-8"
        )
    )
    window.add(entry)
    window.connect("destroy", Gtk.main_quit)
    result_path.write_text("teh", encoding="utf-8")
    window.show_all()
    Gtk.main()


def invoke(*args, check=True):
    return subprocess.run(
        ["xdotool", *map(str, args)], check=check,
        text=True, capture_output=True,
    )


def wait_for_window(name, seconds=12):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        response = invoke("search", "--onlyvisible", "--name", name, check=False)
        if response.returncode == 0 and response.stdout.strip():
            return response.stdout.strip().splitlines()[-1]
        time.sleep(0.15)
    raise AssertionError(f"GTK X11 test window did not appear: {name}")


def integration():
    if not os.environ.get("DISPLAY"):
        raise AssertionError("Xvfb display required")
    with tempfile.TemporaryDirectory(prefix="ayarime-spell-x11-") as tmp:
        state = Path(tmp) / "synthetic-entry.txt"
        with (Path(tmp) / "editor.log").open("w") as editorlog, (
            Path(tmp) / "helper.log"
        ).open("w") as helperlog:
            fixture = subprocess.Popen(
                ["/usr/bin/python3", __file__, "--editor", str(state)],
                cwd=ROOT, stdout=editorlog, stderr=subprocess.STDOUT,
            )
            helper = None
            try:
                field_win = wait_for_window(NAME)
                invoke("windowmove", field_win, 500, 240)
                helper = subprocess.Popen(
                    ["/usr/bin/python3",
                     str(ROOT / "linux-spell" / "app.py"),
                     "--start-enabled", "--language", "en_GB"],
                    cwd=ROOT, stdout=helperlog, stderr=subprocess.STDOUT,
                    env={**os.environ, "AYARIME_SPELL_TEST_TRACE": "1"},
                )
                wait_for_window("Ayarime · Linux Spell")
                # Position the text field at a known screen coordinate.
                # Only the synthetic word "teh" is ever edited.
                for _ in range(3):
                    invoke("windowfocus", field_win)
                    invoke("mousemove", 516, 285)
                    invoke("click", "1")
                    time.sleep(0.55)
                    invoke("key", "--clearmodifiers", "Down", "Return")
                    time.sleep(0.55)
                    if state.read_text(encoding="utf-8") != "teh":
                        break
                result = state.read_text(encoding="utf-8")
                assert result != "teh", (
                    "Click and correction did not change the synthetic GTK "
                    f"field. Is AT-SPI mouse notification reaching the helper?"
                )
                assert result.isalpha() and len(result) < 50
                print("PASS: real GTK/X11 left-click → Enchant menu → text correction")
            except Exception:
                if helper is not None:
                    print("Helper diagnostic output:")
                    print((Path(tmp) / "helper.log").read_text()[-1200:])
                print("Editor diagnostic output:")
                print((Path(tmp) / "editor.log").read_text()[-1200:])
                raise
            finally:
                for proc in (helper, fixture):
                    if proc is None:
                        continue
                    proc.terminate()
                    try:
                        proc.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait(timeout=3)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--editor":
        editor(Path(sys.argv[2]))
    else:
        integration()
