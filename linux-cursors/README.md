# Ayarime Native Cursors for Linux Mint

A separate, optional desktop cursor pack built from ELF//SHELL's original
Ayarime pointer artwork. This is **not part of the Firefox extension**.
The Firefox extension continues to use your system pointer everywhere except
for its own dashboard, where its separate dashboard cursor setting is optional.

**Seven variations** are included: Ayarime Core (six functional states),
Classic Spearhead, Crystal-Tech Shard, Elven Feather, Hollow Frame, Rune-Edged,
and Minimal Precision. Each alternate pointer is paired with Ayarime's text,
link, busy, crosshair and diagonal-resize imagery.

These are genuine native **Xcursor** cursor files, not Firefox CSS injections.
They work with many X11 applications, including Cinnamon and Firefox chrome,
subject to the toolkit's normal theme support. **This is not a spellchecker.**
Firefox's built-in spelling continues to work unchanged; no system-wide
spellchecker or keylogging/injection service is bundled.

## Install (no sudo)

Extract the provided Ayarime-Cursors-Linux-Mint.tar.gz archive. From the
extracted Ayarime-Cursors folder, run:

    bash install.sh

Themes are copied into ~/.local/share/icons/. Nothing is changed
system-wide, and the script never automatically changes your cursor selection.
Existing directories are left untouched instead of overwritten.

In Linux Mint Cinnamon open **Themes → Mouse Pointer** and select your
preferred Ayarime theme. Some applications may require restarting or a
logout/login before the new cursor becomes visible. You can always restore
your prior pointer in the same settings panel.

To list installed themes:

    bash install.sh --list

To remove only themes installed by this package (after switching to a
different cursor theme in Cinnamon):

    bash install.sh --remove

It checks the Ayarime identification marker before removal and leaves
unknown installations and files alone. **Never run this script with sudo.**

## Building from source

On Ubuntu 24.04 or Linux Mint 22, install the standard cursor compiler once:

    sudo apt install x11-apps

From the ELF//SHELL repository root:

    python3 linux-cursors/build.py
    python3 linux-cursors/build.py --verify-only

The build produces dist/linux-cursors/Ayarime-Cursors-Linux-Mint.tar.gz.
No network requests or Python dependencies are needed during compilation.

The six visual states have 48px and 64px sources; alternate primary pointers
currently have 64px sources. Hotspots are documented in the build script;
check them on your own hardware and display scaling before broad release.
Busy is a **static**, not animated, cursor.

Only the cursor shapes with suitable Ayarime artwork are overridden. Other
shapes, notably horizontal/vertical resizing, forbidden and drag-and-drop,
inherit the normal **Adwaita** theme where installed. Applications that ignore
Xcursor or force custom CSS cursors may not use the selected pointer.
Wayland and XWayland cursor handling is toolkit-dependent.

This pack ships independently of Mozilla AMO. Installing or uninstalling it
never affects Firefox extension permissions, bookmarks, notes or RSS.
