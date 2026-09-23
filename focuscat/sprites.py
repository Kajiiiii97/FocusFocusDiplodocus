"""The animated sprite cat (art from assets/cat_template.aseprite, packed by tools/build_sprites.py).

Frames are stored as colour roles, recoloured to the user's look, turned into PNG images in
memory and cached, so each frame is a single canvas image item.
"""

import base64
import json
import struct
import tkinter as tk
import zlib

from focuscat.sprite_data import DATA

ANIMS = json.loads(zlib.decompress(base64.b64decode("".join(DATA))))
for _a in ANIMS.values():
    _a["frames"] = [f.split("\n") for f in _a["frames"]]

OUTLINE = "#120E14"
MOUTH = "#CA719F"
MOUTH_DARK = "#190F29"

# action -> (animation, or (left, right) pair, frames per second)
ACTIONS = {
    "sit": ("sit", 5), "blink": ("blink", 8), "sus": (("sit_l", "sit_r"), 3),
    "walk": (("walk_l", "walk_r"), None), "approach": (("walk_l", "walk_r"), None),
    "groom": ("groom", 6), "scratch": ("scratch", 8),
    "sleep": (("sleep_l", "sleep_r"), 0.8),
    "angry": (("hiss_l", "hiss_r"), 3), "happy": ("happy", 6), "smug": ("meow", 5),
    "held": ("stand", 8),
}


def _mix(a, b, t):
    ra = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    rb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02X%02X%02X" % tuple(round(x + (y - x) * t) for x, y in zip(ra, rb))


def _lum(h):
    r, g, b = (int(h[i:i + 2], 16) for i in (1, 3, 5))
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255


def palette(look):
    fur, second, pattern = look["fur"], look["second"], look["pattern"]
    dark = _lum(fur) < 0.35
    shadow = _mix(fur, "#000000", 0.38 if dark else 0.24)
    light = _mix(fur, "#FFFFFF", 0.2 if dark else 0.45)
    if pattern in ("bib", "patches"):
        light = second
    table = {"O": OUTLINE, "F": fur, "S": shadow, "L": light, "P": look["pink"], "E": look["eye"],
             "M": MOUTH, "N": MOUTH_DARK}
    if pattern == "socks":
        table.update(f=second, s=_mix(second, "#000000", 0.2), l=second)
    else:
        table.update(f=table["F"], s=table["S"], l=table["L"])
    return table


def _png(width, height, rgba_rows):
    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))
    raw = b"".join(b"\x00" + row for row in rgba_rows)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)) +
            chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


_cache = {}


def image(name, index, n, look):
    """A PhotoImage of one frame, scaled up by n with crisp pixels."""
    table = palette(look)
    key = (name, index, n, tuple(sorted(table.items())))
    img = _cache.get(key)
    if img is not None:
        return img
    if len(_cache) > 600:
        _cache.clear()
    grid = ANIMS[name]["frames"][index]
    rgb = {k: bytes(int(v[i:i + 2], 16) for i in (1, 3, 5)) + b"\xff" for k, v in table.items()}
    clear = b"\x00\x00\x00\x00"
    rows = []
    for line in grid:
        row = b"".join((rgb[ch] if ch != "." else clear) * n for ch in line)
        rows.extend([row] * n)
    w, h = len(grid[0]) * n, len(grid) * n
    img = tk.PhotoImage(data=base64.b64encode(_png(w, h, rows)).decode())
    _cache[key] = img
    return img


def pixel_size(s):
    return max(1, round(3 * s))


def draw(p, name, index):
    """Draw a frame with its feet on the pen's ground point. Returns where speech bubbles go."""
    a = ANIMS[name]
    n = pixel_size(p.s)
    index %= len(a["frames"])
    p.cv.create_image(p.ox + a["x0"] * n, p.oy + a["y0"] * n, image=image(name, index, n, p.pal), anchor="nw")
    return p.f * a["head_x"] * n / p.s, a["y0"] * n / p.s + 38


def pick(action, facing):
    anim, fps = ACTIONS.get(action, ACTIONS["sit"])
    if isinstance(anim, tuple):
        anim = anim[0] if facing < 0 else anim[1]
    return anim, fps


def frame_count(name):
    return len(ANIMS[name]["frames"])


def draw_action(p, action, t, phase=0.0, play_step=None):
    """Pick the right animation for what the cat is doing and draw the current frame."""
    f = p.f
    if action == "play":
        pounce = "pounce_l" if f < 0 else "pounce_r"
        if play_step in ("crouch", "pounce", "done"):
            # Frames of the sheet's pounce: 2 is mid-leap, 3 is the low landing/crouch.
            return draw(p, pounce, {"crouch": 3, "pounce": 2, "done": 4}[play_step])
        action = "walk" if phase else "sit"
    if action == "sit" and (t % 7.0) > 6.5:
        action = "blink"
    name, fps = pick(action, f)
    if fps is None:  # walking: step with the distance travelled
        index = int(phase / 1.6)
    else:
        index = int(t * fps)
    if action == "sleep" or name.startswith("hiss"):
        index %= frame_count(name)
    return draw(p, name, index)


def anger_mark(cv, x, y, n):
    rows = [".R.R.", "RR.RR", ".....", "RR.RR", ".R.R."]
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            if ch == "R":
                cv.create_rectangle(x + (c - 2.5) * n, y + (r - 2.5) * n, x + (c - 1.5) * n, y + (r - 1.5) * n,
                                    fill="#D93A45", outline="")


def portrait(p):
    draw(p, "sit", 0)
