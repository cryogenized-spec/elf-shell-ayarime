#!/usr/bin/python3
"""Ayarime Spell — opt-in X11 mouse-click suggestions via AT-SPI + Enchant.

Uses the system-installed Hunspell/Enchant dictionaries, never copies typed
content, never listens to keypresses and never installs a background service.
Only reads the word beneath a left click in a focused editable control.
This is *not* Firefox's native context-menu API; web editors vary in their
accessibility support. Current Firefox releases may ignore AT-SPI edits.
"""
from __future__ import annotations

import argparse
import os
import sys
import time

gi_error = None
try:
    import gi
    gi.require_version("Gtk", "3.0")
    gi.require_version("Atspi", "2.0")
    from gi.repository import Gtk, Gdk, GLib, Atspi
    import enchant
except ImportError as exc:
    gi_error = exc

from core import (
    apply_replacement, clicked_word, normalize_suggestions,
)

APP_TITLE = "Ayarime · Linux Spell"
EVENT_FOCUS = "object:state-changed:focused"
EVENT_CLICK = "mouse:b1r"
# We intentionally do not query terminal/password widgets or dialogs.
PRIVATE_ROLE_WORDS = ("password", "terminal", "secret")


def _field_is_safe(accessible) -> bool:
    if accessible is None:
        return False
    try:
        role = (accessible.get_role_name() or "").casefold()
        if any(word in role for word in PRIVATE_ROLE_WORDS):
            return False
        states = accessible.get_state_set()
        if not states or not states.contains(Atspi.StateType.EDITABLE):
            return False
        if states.contains(Atspi.StateType.READ_ONLY):
            return False
        if not (accessible.get_text_iface() and accessible.get_editable_text_iface()):
            return False
        parent = accessible.get_parent()
        # Refuse fields inside secure/prompts regardless of their own role.
        for _ in range(2):
            if parent is None:
                break
            role = (parent.get_role_name() or "").casefold()
            if any(token in role for token in PRIVATE_ROLE_WORDS):
                return False
            parent = parent.get_parent()
        return True
    except (GLib.Error, AttributeError, RuntimeError, TypeError):
        return False


def _parse_range(value):
    # Older typelib bindings can expose an object or a 3-tuple.
    if isinstance(value, (tuple, list)) and len(value) >= 3:
        return str(value[0]), int(value[1]), int(value[2])
    return str(value.content), int(value.start_offset), int(value.end_offset)


class SpellApp:
    def __init__(self, language: str):
        self.language = language
        self.dictionary = enchant.Dict(language)
        self.window = Gtk.Window(title=APP_TITLE)
        self.window.set_default_size(430, 250)
        self.window.set_border_width(16)
        self.window.connect("destroy", self._shutdown)
        self.listener = None
        self.focused = None
        self.menu = None
        self.last_click = 0.0
        self._build_ui()

    def _build_ui(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=9)
        self.window.add(outer)
        title = Gtk.Label()
        title.set_markup("<b>Ayarime · Left-click spell suggestions</b>")
        title.set_xalign(0)
        outer.pack_start(title, False, False, 0)
        desc = Gtk.Label(
            "Opt in below. Click a misspelled word in a compatible editable "
            "Linux application to see corrections from your installed "
            f"{self.language} dictionary. Text stays on your computer."
        )
        desc.set_line_wrap(True)
        desc.set_xalign(0)
        outer.pack_start(desc, False, False, 0)
        self.toggle = Gtk.ToggleButton(label="Enable left-click assistance")
        self.toggle.connect("toggled", self._on_toggle)
        outer.pack_start(self.toggle, False, False, 0)
        self.status = Gtk.Label(label="Stopped · no mouse events monitored")
        self.status.set_xalign(0)
        outer.pack_start(self.status, False, False, 0)
        demo_label = Gtk.Label(label="Try it here after enabling:")
        demo_label.set_xalign(0)
        outer.pack_start(demo_label, False, False, 0)
        self.demo = Gtk.Entry()
        self.demo.set_text("Ths is a smple txt with a mispelt wrd.")
        outer.pack_start(self.demo, False, False, 0)
        note = Gtk.Label(
            "No autostart, keylogger, clipboard edits or internet use. "
            "Firefox native right-click suggestions are unchanged."
        )
        note.set_line_wrap(True)
        note.set_xalign(0)
        outer.pack_start(note, False, False, 0)
        self.window.show_all()

    def _on_toggle(self, button):
        if not button.get_active():
            self.stop()
            return
        try:
            Atspi.init()
            # Only two event types: focus acquisition, and button-1 release.
            self.listener = Atspi.EventListener.new(self._on_event, None, None)
            if not self.listener.register(EVENT_FOCUS):
                raise RuntimeError("Accessibility focus listener unavailable")
            if not self.listener.register(EVENT_CLICK):
                raise RuntimeError("Accessibility mouse listener unavailable")
            self.status.set_text(
                f"Enabled · click misspelled words ({self.language})"
            )
            self.toggle.set_label("Stop left-click assistance")
        except Exception as exc:
            self.stop()
            self.toggle.set_active(False)
            self.status.set_text(
                "Cannot start accessibility listener; check your X11 session."
            )
            dialog = Gtk.MessageDialog(
                transient_for=self.window,
                flags=0, message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.CLOSE,
                text="Native spell listener unavailable",
            )
            dialog.format_secondary_text(str(exc))
            dialog.run()
            dialog.destroy()

    def stop(self):
        if self.listener is not None:
            for event_type in (EVENT_CLICK, EVENT_FOCUS):
                try:
                    self.listener.deregister(event_type)
                except Exception:
                    pass
        self.listener = None
        self.focused = None
        if self.menu is not None:
            self.menu.destroy()
            self.menu = None
        self.status.set_text("Stopped · no mouse events monitored")
        self.toggle.set_label("Enable left-click assistance")

    def _trace(self, reason):
        # Test-only metadata, never editor words or replacement candidates.
        if os.environ.get("AYARIME_SPELL_TEST_TRACE") == "1":
            print("AYARIME_SPELL_DIAGNOSTIC:", reason, flush=True)

    def _on_event(self, event, *_unused):
        event_type = str(event.type or "")
        self._trace("event="+event_type)
        if "state-changed:focused" in event_type:
            if event.detail1 and _field_is_safe(event.source):
                self.focused = event.source
                self._trace("focus: accepted editable")
            elif event.detail1:
                self.focused = None
                self._trace("focus: ignored role or state")
            return
        if "mouse" not in event_type or not event_type.endswith("1r"):
            return
        if self.menu is not None or not self.toggle.get_active():
            self._trace("click ignored: menu shown or switched off")
            return
        self._trace("click event delivered")
        # AT-SPI's mouse-event detail1 and detail2 are screen coordinates.
        x, y = int(event.detail1), int(event.detail2)
        GLib.idle_add(self._on_click, x, y)

    def _on_click(self, x: int, y: int):
        if self.menu is not None or not self.toggle.get_active():
            return False
        now = time.monotonic()
        if now - self.last_click < 0.25:
            return False
        self.last_click = now
        accessible = self.focused
        if not _field_is_safe(accessible):
            self._trace("click: no safe focus target")
            return False
        try:
            states = accessible.get_state_set()
            if not states.contains(Atspi.StateType.FOCUSED):
                self._trace("click: target not focused")
                return False
            component = accessible.get_component_iface()
            if component is None or not component.contains(x, y, Atspi.CoordType.SCREEN):
                self._trace("click: outside component")
                return False
            self._trace("click: inside editable component")
            text = accessible.get_text_iface()
            offset = text.get_offset_at_point(x, y, Atspi.CoordType.SCREEN)
            if offset is None or offset < 0:
                self._trace("click: no text offset")
                return False
            value, start, end = _parse_range(
                text.get_string_at_offset(offset, Atspi.TextGranularity.WORD)
            )
            if end - start > 256:
                return False
            hit = clicked_word(value, start, offset)
            if hit is None or self.dictionary.check(hit.word):
                self._trace("click: punctuation or known word")
                return False
            self._trace("click: misspelling confirmed")
            candidates = normalize_suggestions(
                hit.word, self.dictionary.suggest(hit.word)
            )
            if not candidates:
                self._trace("click: no safe local alternatives")
                return False
        except (GLib.Error, ValueError, TypeError, RuntimeError, AttributeError) as exc:
            self._trace("click: API error="+type(exc).__name__)
            return False
        self._trace("click: opening local corrections menu")
        self._show_suggestions(accessible, hit, candidates)
        return False

    def _show_suggestions(self, accessible, hit, candidates):
        menu = Gtk.Menu()
        title = Gtk.MenuItem(label=f"Correct: {hit.word}")
        title.set_sensitive(False)
        menu.append(title)
        menu.append(Gtk.SeparatorMenuItem())
        for suggestion in candidates:
            item = Gtk.MenuItem(label=suggestion)
            item.connect("activate", self._apply, accessible, hit, suggestion)
            menu.append(item)
        menu.connect("hide", self._close_menu, menu)
        self.menu = menu
        menu.show_all()
        menu.popup_at_pointer(None)

    def _close_menu(self, _menu, menu):
        if self.menu is menu:
            self.menu = None
        GLib.idle_add(menu.destroy)

    def _apply(self, _item, accessible, hit, suggestion):
        if not _field_is_safe(accessible):
            self._trace("apply: target no longer safe")
            return
        try:
            ok = apply_replacement(
                accessible.get_text_iface(),
                accessible.get_editable_text_iface(),
                hit, suggestion,
            )
        except (GLib.Error, RuntimeError, AttributeError):
            ok = False
        self._trace("apply: "+("success" if ok else "rejected"))
        if not ok:
            self.status.set_text(
                "Editor rejected the correction; existing text preserved"
            )

    def _shutdown(self, *_args):
        self.stop()
        Gtk.main_quit()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", default="en_GB")
    parser.add_argument("--start-enabled", action="store_true",
                        help="Explicitly activate local assistance at launch")
    args = parser.parse_args()
    if gi_error is not None:
        print("Missing GTK/AT-SPI/Enchant packages: "+str(gi_error), file=sys.stderr)
        return 2
    if os.environ.get("XDG_SESSION_TYPE", "x11").casefold() != "x11":
        print("This preview supports Linux Mint Cinnamon on X11 only.", file=sys.stderr)
        return 2
    try:
        app = SpellApp(args.language)
    except enchant.errors.DictNotFoundError:
        print(f"No installed local dictionary for {args.language}.", file=sys.stderr)
        return 2
    if args.start_enabled:
        app.toggle.set_active(True)  # Explicit command-line opt-in.
    Gtk.main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
