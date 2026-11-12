# ELF//SHELL — Ayarime Linux Desktop Tools (developer preview)

An **independent native Linux Mint/Cinnamon companion**, not part of the Firefox add-on. Source-first and per-user; no `sudo` required to run the tools. This is a **prototype, not yet live-tested on the target HP OMEN**.

## 1. Cursor themes

Three new ELF//SHELL-inspired color options: `ELF-SHELL-Rose`, `ELF-SHELL-Teal`, `ELF-SHELL-Gold`. Each generates real multi-resolution (24/32/48 px) Xcursor files with standard default, pointer, text, busy, help, crosshair, move, forbidden, and horizontal/vertical resize shapes and alias names. The busy/wait cursor is animated. The exact original Firefox cursor assets are **not included**—those originals are not currently present in the public GitHub repository. Missing shapes inherit Adwaita.

```bash
# The downloadable preview archive includes prebuilt cursors (no dependencies).
# GitHub source checkouts instead require: sudo apt install python3-pil
./install.sh cursor
```

Open **Linux Mint System Settings → Themes → Mouse Pointer** and select a theme. This keeps your current theme unchanged until you opt in. Installed under `~/.local/share/icons/` and usable by native applications, not only Firefox. If an application does not pick up the change, restart that application or log out and back in. To uninstall, switch back to your old pointer theme before removing the relevant `~/.local/share/icons/ELF-SHELL-*` folder.

To regenerate the native cursors from source, install `python3-pil` and run `python3 cursors/build.py`.

## 2. Left-click spelling suggestions (X11 experimental)

Clicking **on a misspelled word** in a compatible *single-line editable text field* opens up to five local Enchant/Hunspell suggestions. Left-click a suggestion to replace **only that word**. Ordinary clicks continue normally. The original right-click menu remains untouched.

```bash
sudo apt install python3-gi gir1.2-gtk-3.0 gir1.2-atspi-2.0 python3-enchant hunspell-en-gb
./install.sh spellcheck
/usr/bin/python3 spellcheck/ayarime_spell.py --language en_GB
```

Test first in a disposable single-line GTK app, such as a search input, typing `teh` and clicking on that word. Once verified, you may opt in to desktop autostart:

```bash
./install.sh spellcheck --autostart
```

To stop an interactive launch use Ctrl+C in its terminal. To disable autostart:

```bash
rm -f ~/.config/autostart/ayarime-spellcheck.desktop
```

**Scope and known limits:** This opt-in proof-of-concept requires a Cinnamon/X11 session and functioning AT-SPI accessibility events. It checks only fields exposing `Atspi.Role.ENTRY`, `Text`, and `EditableText`; it deliberately ignores multiline rich-text, password fields, selection-only widgets, inaccessible applications and text over 4096 characters. Firefox, Chromium, some Qt and Electron applications may not expose a usable accessibility object, and Wayland mouse events are not supported. Suggestions come from the local selected dictionary, not necessarily the application's existing built-in spellchecker; their suggestion lists can differ. The field is checked again before the edit to avoid overwriting text changed while the popup was open. The replacement uses AT-SPI deletion/insertion and may not have the same Undo behavior as a native edit. Do not enable this globally before testing it in disposable text. No clipboard reads, web requests, logging of typed text or background starts by default.

**Why not force every program to show its right-click menu on left click?** Desktop applications manage their own spelling menus. No single Linux API exposes those suggestions universally. Simulating a right click would interfere with editing, selecting and dragging; this tool instead offers a targeted alternative where application accessibility permits.

## Developer tests

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile cursors/build.py spellcheck/ayarime_spell.py spellcheck/words.py
```

**Still required before declaring complete:** live acceptance on Linux Mint 22 Cinnamon X11, verifying AT-SPI mouse delivery, a GTK field and a real browser field; original Firefox cursor artwork export/consistency; packaging as a `.deb` if needed.
