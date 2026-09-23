"""Decides whether you're doomscrolling and when the cat should close the tab.

The Firefox extension reports the active tab every couple of seconds; the UI calls tick()
every frame. Everything here is plain logic so it can be tested without a window.
"""

import threading
import time

CALM = "calm"
SUSPICIOUS = "suspicious"  # on a doomscroll page, but still inside the grace period
MAD = "mad"  # countdown running
CLOSING = "closing"  # countdown hit zero, waiting for the extension to close the tab
PAUSED = "paused"

# Reports older than this mean Firefox (or the extension) went away.
STALE_AFTER = 8.0


def normalize(url):
    url = (url or "").strip().lower()
    if "://" in url:
        url = url.split("://", 1)[1]
    if url.startswith("www."):
        url = url[4:]
    return url


def is_distracting(url, patterns):
    u = normalize(url)
    if not u:
        return False
    for p in patterns:
        p = normalize(p)
        if p and p in u:
            return True
    return False


class FocusWatcher:
    def __init__(self, settings, clock=time.monotonic):
        self.settings = settings
        self.clock = clock
        self._lock = threading.Lock()
        self._url = ""
        self._tab_id = None
        self._focused = False
        self._report_at = None
        self._last_tick = None
        self._strike = 0.0  # seconds recently spent doomscrolling
        self._away = 0.0  # seconds since you were last on a doomscroll page
        self._mood = CALM
        self._close_tab = None
        self._closing_since = 0.0
        self._paused_until = 0.0
        self._events = []

    def _num(self, key):
        return float(self.settings[key])

    # --- called from the HTTP server thread -------------------------------------------

    def report(self, url, tab_id, focused):
        """Store the active tab. Returns a tab id to close, or None."""
        with self._lock:
            self._url = url or ""
            self._tab_id = tab_id if isinstance(tab_id, int) and not isinstance(tab_id, bool) else None
            self._focused = bool(focused)
            self._report_at = self.clock()
            close, self._close_tab = self._close_tab, None
            if close is not None:
                self._events.append("closed")
            return close

    # --- called from the UI thread ----------------------------------------------------

    def pause(self, seconds):
        with self._lock:
            self._paused_until = self.clock() + seconds
            self._strike = 0.0
            self._close_tab = None

    def resume(self):
        with self._lock:
            self._paused_until = 0.0

    def pop_events(self):
        with self._lock:
            events, self._events = self._events, []
            return events

    def _distracted(self, now):
        if self._report_at is None or now - self._report_at > STALE_AFTER:
            return False
        return self._focused and is_distracting(self._url, self.settings["blocked"])

    def tick(self):
        with self._lock:
            now = self.clock()
            # Clamp dt so waking the PC from sleep doesn't count as hours of scrolling.
            dt = 0.0 if self._last_tick is None else min(max(now - self._last_tick, 0.0), 1.0)
            self._last_tick = now

            grace = self._num("notice_after_seconds")
            close_after = self._num("close_after_seconds")
            limit = grace + close_after

            paused = now < self._paused_until
            distracted = self._distracted(now) and not paused

            if distracted:
                self._strike += dt
                self._away = 0.0
            else:
                self._away += dt
                self._close_tab = None
                if self._away >= self._num("forgive_after_seconds"):
                    self._strike = 0.0

            old = self._mood
            if paused:
                new = PAUSED
            elif not distracted:
                new = CALM
            elif old == CLOSING and now - self._closing_since < 6.0:
                new = CLOSING
            elif self._strike >= limit and self._tab_id is not None:
                new = CLOSING
                self._close_tab = self._tab_id
                self._closing_since = now
                # Coming right back after a close only buys you a short second chance.
                second = min(self._num("second_chance_seconds"), close_after)
                self._strike = max(grace, limit - second)
            elif self._strike >= grace:
                new = MAD
            else:
                new = SUSPICIOUS

            if new != old:
                if new == MAD and old in (CALM, SUSPICIOUS):
                    self._events.append("noticed")
                elif new == CALM and old == MAD:
                    self._events.append("stopped")
            self._mood = new

    def status(self):
        with self._lock:
            now = self.clock()
            limit = self._num("notice_after_seconds") + self._num("close_after_seconds")
            remaining = None
            if self._mood in (MAD, CLOSING):
                remaining = max(0.0, limit - self._strike) if self._mood == MAD else 0.0
            return {
                "mood": self._mood,
                "remaining": remaining,
                "total": self._num("close_after_seconds"),
                "connected": self._report_at is not None and now - self._report_at < STALE_AFTER,
                "paused_for": max(0.0, self._paused_until - now),
                "url": self._url,
            }
