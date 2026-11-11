# Ayarime Spell — local Linux Mint click-to-correct preview

A separate, **optional**, small GTK 3 companion for Linux Mint 22
Cinnamon **X11**, built independently of the ELF//SHELL Firefox extension
and the cursor themes. No cloud service or dictionary downloads occur
when running. Spell checking uses the installed Linux Enchant/Hunspell
provider and dictionary (default `en_GB`). Your keyboard text is not
recorded, logged or transmitted. No autostart and no root-level hooks.

## How to use

Install the `ayarime-spell_0.1.0-1_all.deb` using Linux Mint's package
manager, reviewing the normal dependencies before approving. Launch
**Ayarime Spell · Left-Click Corrections** from the application menu.

1. Select **Enable left-click assistance**. Until enabled, the helper
   does not register any mouse or accessibility listeners.
2. Click a misspelled word in an editable GTK/X11 field that exposes
   the AT-SPI AccessibleText/EditableText interfaces. The helper asks
   your *local*, system-installed Enchant dictionary for suggestions.
3. Select a replacement. The helper checks the original word still
   matches before attempting to edit, then verifies the editor applied
   the insertion before it removes the old word.
4. **Stop left-click assistance** disables both listeners. Closing the
   window also stops them. This is not a login service.

The window provides a local sample text input containing misspellings for
testing. To use a different installed dictionary, start from a terminal:

    ayarime-spell --language en_US

Install that language's normal system dictionary if needed. The package
recommends a local British English dictionary on Mint 22.

## Practical limitations (important)

- Supported where AT-SPI exposes *focused, editable, non-secret text* and
  screen coordinates. Some browsers, terminals, custom editors, Electron
  controls, protected fields, remote desktops and Wayland sessions do not.
  Unsupported controls are ignored; text is not modified.
- This is **not the internal Firefox spelling API**, and Enchant's
  suggestions may differ from Firefox's native spellchecker. Firefox
  currently has known versions that report accessibility text writes
  as successful while doing nothing. The helper explicitly reads back
  edits before deleting the original. Do not rely on Firefox support
  without a passing physical Mint test.
- Linux apps own their native **right-click menus**. A separate Linux
  helper cannot selectively remove their spelling suggestion section,
  so ordinary right-click actions remain unchanged. This does not yet
  fully satisfy the original "replace Firefox right-click" requirement.
- AT-SPI uses separate insert/delete operations; undo grouping varies
  by editor. Do not use this preview to edit sensitive or irreplaceable
  content before testing your target application.
- A foreground helper subscribes to AT-SPI focus events and X11 RECORD
  left-button-release events while enabled. It reads only the word-sized accessible text range at a
  candidate click, ignores role-named password/terminal controls, stores
  no text logs and never requests keyboard events. Applications may expose
  sensitive text incorrectly to accessibility; stop assistance whenever
  you don't need it.
- **No autostart, no background service, no telemetry, no root scripts**.
  Uninstall with the package manager, or simply leave it disabled.

## Project and testing

Source: `linux-spell/app.py` and `linux-spell/core.py`.
The separate `linux-spell/build_deb.py` builds an Architecture: all
Debian package using Python standard library and `dpkg-deb`. Tests
verify word bounds, Unicode replacement, no-op app protection and that
the Debian package has no services or maintainer scripts.

This is **an experimental Linux field preview**, not a proven universal
Firefox/GTK spellchecker. Please test with the specific applications you
actually use before considering a release.
