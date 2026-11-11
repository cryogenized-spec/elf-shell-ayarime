#!/usr/bin/python3
"""Probe required Linux Mint GTK, Enchant and AT-SPI interfaces on a real X11 bus.

Fails loudly on missing GI types/mouse listener APIs, rather than shipping
a non-working daemon. Does not access any real clipboard or text editor.
"""
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Atspi", "2.0")
from gi.repository import Gtk, Atspi
import enchant
from Xlib import display

assert Gtk.init_check()[0], "Cannot launch GTK on test display"
assert enchant.Dict("en_GB").check("computer")
assert not enchant.Dict("en_GB").check("mispeltwrod")
Atspi.init()
listener = Atspi.EventListener.new(lambda event, *_: None, None, None)
d = display.Display()
assert d.has_extension("RECORD"), "No XRecord extension for release-only listener"
d.close()
assert listener.register("object:state-changed:focused"), "Cannot monitor focus"
assert listener.deregister("object:state-changed:focused")
print("PASS: system English dictionary, AT-SPI focus API, and X11 RECORD support")
