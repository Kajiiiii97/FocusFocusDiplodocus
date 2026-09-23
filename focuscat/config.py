"""Settings, stored as JSON in %APPDATA%\\FocusCat\\config.json (or ~/.focuscat on other systems)."""

import json
import os
import sys

DEFAULTS = {
    # Local port the Firefox extension talks to. Change it in background.js too if you change it here.
    "port": 47321,
    # How long you can be on a doomscroll page before the cat decides it's a problem.
    "notice_after_seconds": 15,
    # Once the cat is mad, how long until it closes the tab.
    "close_after_seconds": 300,
    # How long you need to stay away before the countdown fully resets.
    # (Hopping off for 10 seconds and back doesn't reset it.)
    "forgive_after_seconds": 90,
    # If you go straight back after the cat closed a tab, you only get this long.
    "second_chance_seconds": 60,
    # A page counts as doomscrolling if its address contains any of these.
    "blocked": [
        "youtube.com/shorts",
        "tiktok.com",
        "instagram.com/reels",
        "instagram.com/reel/",
        "facebook.com/reel",
    ],
    # Length of the "take a break" option in the right-click menu.
    "break_minutes": 15,
    # Size multiplier for the cat (on top of Windows display scaling).
    "scale": 1.0,
    # orange, gray, black, white, calico
    "palette": "orange",
    "cat_name": "Mochi",
}


def config_dir():
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, "FocusCat")
    return os.path.join(os.path.expanduser("~"), ".focuscat")


def config_path():
    return os.path.join(config_dir(), "config.json")


def _clean(raw):
    cfg = dict(DEFAULTS)
    if not isinstance(raw, dict):
        return cfg
    for key, default in DEFAULTS.items():
        if key not in raw:
            continue
        value = raw[key]
        if isinstance(default, bool):
            cfg[key] = bool(value)
        elif isinstance(default, (int, float)):
            try:
                number = float(value)
            except (TypeError, ValueError):
                continue
            if number < 0:
                continue
            cfg[key] = int(number) if isinstance(default, int) else number
        elif isinstance(default, list):
            if isinstance(value, list):
                cfg[key] = [str(v).strip() for v in value if str(v).strip()]
        else:
            cfg[key] = str(value)
    cfg["scale"] = min(max(cfg["scale"], 0.4), 4.0)
    return cfg


def load(path=None):
    """Load settings, writing a default file on first run so there's something to edit."""
    path = path or config_path()
    raw = None
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except FileNotFoundError:
        save(DEFAULTS, path)
    except (OSError, ValueError):
        pass  # broken file: fall back to defaults but don't overwrite the user's edits
    return _clean(raw)


def save(cfg, path=None):
    path = path or config_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except OSError:
        pass
