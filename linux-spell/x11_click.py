"""Opt-in, release-only X11 mouse event source.

XRecord is needed on X11 configurations where AT-SPI focus events exist
but AT-SPI mouse events do not. Only ButtonRelease events are requested:
never KeyPress, KeyRelease, MotionNotify, or clipboard data. Coordinates
are obtained from the current X11 pointer, never written to disk.
"""
from __future__ import annotations

from threading import Lock, Thread

from Xlib import X, display
from Xlib.ext import record
from Xlib.protocol import rq


class X11LeftClickSource:
    def __init__(self, callback):
        self.callback = callback
        self.control = display.Display()
        self.stream = display.Display()
        self._lock = Lock()
        self._closed = False
        if not self.control.has_extension("RECORD"):
            self.stream.close()
            self.control.close()
            raise RuntimeError("X11 RECORD extension unavailable")
        self.context = self.control.record_create_context(
            0, [record.AllClients], [{
                "core_requests": (0, 0),
                "core_replies": (0, 0),
                "ext_requests": (0, 0, 0, 0),
                "ext_replies": (0, 0, 0, 0),
                "delivered_events": (0, 0),
                # Do NOT widen this range; keyboard and motion must not be
                # recorded by a spell-assistance utility.
                "device_events": (X.ButtonRelease, X.ButtonRelease),
                "errors": (0, 0),
                "client_started": False,
                "client_died": False,
            }]
        )
        self.thread = Thread(
            target=self._stream_events, name="Ayarime-X11LeftClick",
            daemon=True,
        )
        self.thread.start()

    def _stream_events(self):
        try:
            self.stream.record_enable_context(self.context, self._on_record)
        except Exception:
            # The GUI can still stop or quit normally on X server shutdown.
            pass

    def _on_record(self, reply):
        if (
            self._closed or reply.category != record.FromServer
            or reply.client_swapped or not reply.data
        ):
            return
        data = reply.data
        while data:
            try:
                event, data = rq.EventField(None).parse_binary_value(
                    data, self.stream.display, None, None
                )
            except (ValueError, TypeError, AttributeError):
                break
            if event.type != X.ButtonRelease or event.detail != 1:
                continue
            try:
                with self._lock:
                    if self._closed:
                        return
                    pos = self.control.screen().root.query_pointer()
                self.callback(int(pos.root_x), int(pos.root_y))
            except (OSError, RuntimeError, AttributeError):
                return

    def stop(self):
        with self._lock:
            if self._closed:
                return
            self._closed = True
            try:
                self.control.record_disable_context(self.context)
                self.control.sync()
            except Exception:
                pass
        self.thread.join(timeout=1.5)
        try:
            self.control.record_free_context(self.context)
            self.control.close()
            self.stream.close()
        except Exception:
            pass
