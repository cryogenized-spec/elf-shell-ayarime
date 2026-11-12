#!/usr/bin/python3
"""Opt-in Linux Mint X11 left-click spelling suggestions for accessible ENTRY widgets.

Never intercepts the click and never runs in password fields. Requires a desktop
that emits AT-SPI mouse events and text fields implementing EditableText.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
from words import word_at, current_range_is_unchanged

try:
    import enchant
    import gi
    gi.require_version('Gtk', '3.0')
    gi.require_version('Atspi', '2.0')
    from gi.repository import Atspi, Gtk, Gdk, GLib
except (ImportError, ValueError) as err:
    raise SystemExit('Install the packages in README.md (python3-gi, python3-enchant, gir1.2-atspi-2.0, GTK3). '+str(err))

MAX_CHARS=4096


def active_editable_at(x: int, y: int):
    """Find the deepest visible accessible object at the screen coordinate.

    We intentionally accept only ENTRY role to avoid altering rich-text layout.
    """
    desktop=Atspi.get_desktop(0)
    if desktop is None:
        return None
    point=Atspi.CoordType.SCREEN
    for ai in reversed(range(min(desktop.get_child_count(),120))):
        try:
            app=desktop.get_child_at_index(ai)
            for wi in reversed(range(min(app.get_child_count(),100))):
                win=app.get_child_at_index(wi)
                component=win.get_component_iface()
                if not component or not component.contains(x,y,point):
                    continue
                target=win
                for _ in range(24):
                    comp=target.get_component_iface()
                    child=comp.get_accessible_at_point(x,y,point) if comp else None
                    if not child or child == target:
                        break
                    target=child
                if target.get_role() != Atspi.Role.ENTRY:
                    return None
                if not target.get_editable_text_iface() or not target.get_text_iface():
                    return None
                states=target.get_state_set()
                if states and not states.contains(Atspi.StateType.EDITABLE):
                    return None
                return target
        except (GLib.Error, RuntimeError, AttributeError):
            continue
    return None


class SpellPopup:
    def __init__(self, language: str):
        try:
            self.dict=enchant.Dict(language)
        except enchant.errors.DictNotFoundError:
            raise SystemExit(f'No {language} dictionary available. Install hunspell-en-gb or start with --language en_US.')
        self.popup=Gtk.Window(type=Gtk.WindowType.POPUP)
        self.popup.set_title('Ayarime — spelling')
        self.popup.set_decorated(False)
        self.popup.set_keep_above(True)
        self.popup.set_skip_taskbar_hint(True)
        self.popup.set_accept_focus(False)
        self.popup.set_border_width(7)
        self.box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=2)
        self.popup.add(self.box)
        self.popup.override_background_color(Gtk.StateFlags.NORMAL,Gdk.RGBA(.09,.08,.15,.98))
        self.pending=None
        self.listener=Atspi.EventListener.new(self.on_event)
        if not self.listener.register('mouse:button'):
            raise SystemExit('AT-SPI mouse event listener could not register. Check that you are using X11.')

    def close(self):
        self.popup.hide()
        self.pending=None

    def on_event(self,event,*_):
        if event.type not in ('mouse:button:1r','mouse:b1r'):
            return
        x,y=int(event.detail1),int(event.detail2)
        # Use idle handler to avoid re-entering AT-SPI while processing event.
        GLib.idle_add(self.on_click,x,y)

    def on_click(self,x,y):
        if self.popup.get_visible():
            px,py=self.popup.get_position()
            w,h=self.popup.get_size()
            if px <= x < px+w and py <= y < py+h:
                return False  # GTK handles clicking a suggestion itself.
            self.close()
        try:
            target=active_editable_at(x,y)
            if not target:
                return False
            text_iface=target.get_text_iface()
            char_count=text_iface.get_character_count()
            if not (1 <= char_count <= MAX_CHARS):
                return False
            offset=text_iface.get_offset_at_point(x,y,Atspi.CoordType.SCREEN)
            before=text_iface.get_text(0,char_count)
            if len(before)!=char_count:
                return False  # Unicode offsets/remote text mismatch: fail closed.
            selection=word_at(before,offset)
            if not selection or self.dict.check(selection.value):
                return False
            suggestions=self.dict.suggest(selection.value)[:5]
            if not suggestions:
                return False
            self.pending=(target,before,selection)
            self.display(x,y,selection.value,suggestions)
        except (GLib.Error, RuntimeError, AttributeError, ValueError):
            self.close()
        return False

    def display(self,x,y,word,suggestions):
        for child in self.box.get_children():
            self.box.remove(child)
        heading=Gtk.Label(label=f'Spelling: {word}')
        heading.set_xalign(0)
        self.box.pack_start(heading,False,False,4)
        for candidate in suggestions:
            button=Gtk.Button(label=candidate)
            button.set_halign(Gtk.Align.FILL)
            button.connect('clicked',self.apply,candidate)
            self.box.pack_start(button,False,False,0)
        self.box.show_all()
        self.popup.show_all()
        display=Gdk.Display.get_default()
        monitor=display.get_monitor_at_point(x,y)
        box=monitor.get_workarea()
        w,h=self.popup.get_size()
        self.popup.move(max(box.x,min(x,box.x+box.width-w)),
                        max(box.y,min(y+12,box.y+box.height-h)))

    def apply(self,_button,suggestion):
        pending=self.pending
        self.close()
        if not pending:
            return
        target,before,selection=pending
        try:
            iface=target.get_text_iface()
            editable=target.get_editable_text_iface()
            if not iface or not editable or target.get_role()!=Atspi.Role.ENTRY:
                return
            count=iface.get_character_count()
            if count!=len(before):
                return
            now=iface.get_text(0,count)
            if not current_range_is_unchanged(now,before,selection):
                return  # A click or typing changed the field; do not overwrite it.
            if not editable.delete_text(selection.start,selection.end):
                return
            # Insert only the changed word, not the entire field; do not touch clipboard.
            if not editable.insert_text(selection.start,suggestion,len(suggestion.encode('utf-8'))):
                print('Ayarime: insertion failed after deletion; restore the text in your editor.',file=sys.stderr)
                return
            try:
                iface.set_caret_offset(selection.start+len(suggestion))
            except GLib.Error:
                pass
        except (GLib.Error,RuntimeError):
            print('Ayarime: text field rejected the edit.',file=sys.stderr)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--language',default='en_GB')
    args=parser.parse_args()
    if not (sys.platform=='linux' and (bool(__import__('os').environ.get('DISPLAY')))):
        raise SystemExit('This experimental spelling overlay currently requires an X11 desktop.')
    Atspi.init()
    popup = SpellPopup(args.language)  # Keep a strong reference to the listener.
    print('Ayarime spelling overlay running for X11 accessible single-line text fields (Ctrl+C to stop).')
    try:
        Gtk.main()
    finally:
        popup.close()

if __name__=='__main__':
    main()
