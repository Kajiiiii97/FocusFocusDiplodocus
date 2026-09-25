"""Shared drawing bits: the cat's colours ("look"), presets, and the speech bubble and hearts that
float around it. The cat itself is drawn by sprites.py."""

import re

EAR_SHAPES = ("pointy", "folded")
EYE_STYLES = ("normal", "big")
PATTERNS = ("solid", "bib", "socks", "patches")

# Presets for the settings window: fur, inner ear, eyes, stripes, second colour, pattern.
PRESETS = {
    "Ginger": ("#AA6928", "#9A877E", "#D3DFE1", False, "#D1AB78", "bib"),
    "Tabby": ("#B8773A", "#9A877E", "#9BD37A", True, "#E3C08E", "bib"),
    "Gray": ("#BDB5C8", "#9A877E", "#D3DFE1", False, "#E1DEE7", "solid"),
    "Smoky": ("#504347", "#9A877E", "#D3DFE1", False, "#726361", "solid"),
    "Tuxedo": ("#34343C", "#C98A9A", "#F2D15C", False, "#F4F4F4", "bib"),
    "Orange": ("#F0A35E", "#F4A7B0", "#9BD37A", False, "#F3EAD8", "bib"),
    "Snow": ("#F4F2EE", "#F7B6C2", "#6FA8DC", False, "#F4F2EE", "solid"),
    "Cocoa": ("#6E4A3A", "#C98A8A", "#E8C06A", False, "#E6D3BF", "socks"),
}

HEART_COLOR = "#FF6B8B"
HEART = [".RR.RR.",
         "RRRRRRR",
         "RRRRRRR",
         ".RRRRR.",
         "..RRR..",
         "...R..."]

_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def is_color(value):
    return isinstance(value, str) and bool(_HEX.match(value))


def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mix(a, b, t):
    ra, rb = _rgb(a), _rgb(b)
    return "#%02X%02X%02X" % tuple(max(0, min(255, round(x + (y - x) * t))) for x, y in zip(ra, rb))


def luminance(h):
    r, g, b = _rgb(h)
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255


def make_look(cfg):
    """Everything about how the cat looks, in the form the sprite code wants."""
    return {
        "fur": cfg["fur_color"],
        "second": cfg["second_color"],
        "pattern": cfg["pattern"],
        "pink": cfg["ear_color"],
        "eye": cfg["eye_color"],
        "blush": mix(cfg["ear_color"], "#FF6F8E", 0.6),
        "ears": cfg["ear_shape"],
        "eye_style": cfg["eye_style"],
        "blush_on": cfg["blush"],
        "stripes": cfg["stripes"],
    }


class Pen:
    """Where and how big to draw: (ox, oy) is the ground point under the cat, s the scale,
    f which way it faces (1 right, -1 left)."""

    def __init__(self, cv, ox, oy, s, facing, pal):
        self.cv, self.ox, self.oy, self.s, self.f, self.pal = cv, ox, oy, s, facing, pal

    def X(self, dx):
        return self.ox + self.f * dx * self.s

    def Y(self, dy):
        return self.oy + dy * self.s


def heart(cv, x, y, size):
    n = max(1, round(size / 7))
    for r, row in enumerate(HEART):
        for c, ch in enumerate(row):
            if ch == "R":
                cv.create_rectangle(x + (c - 3.5) * n, y + (r - 3) * n, x + (c - 2.5) * n, y + (r - 2) * n,
                                    fill=HEART_COLOR, outline="")


def portrait(p):
    from focuscat import sprites
    sprites.portrait(p)


def zzz(cv, x, y, s, t, color):
    for i in range(3):
        ph = (t * 0.45 + i / 3.0) % 1.0
        size = -max(6, int((10 + 9 * ph) * s))
        cv.create_text(x + (10 + ph * 22) * s, y - (ph * 42) * s, text="z",
                       font=("Segoe UI", size, "bold"), fill=color)


def bubble(cv, cx, bottom, text, s, font, min_x, max_x):
    """Speech bubble whose tail points down at (cx, bottom)."""
    tid = cv.create_text(cx, bottom - 16 * s, text=text, font=font, fill="#2B2B2B",
                         justify="center", anchor="s", width=int(200 * s))
    x1, y1, x2, y2 = cv.bbox(tid)
    pad = 9 * s
    # Keep the bubble inside the window.
    shift = max(0, (min_x + pad) - x1) - max(0, x2 - (max_x - pad))
    if shift:
        cv.move(tid, shift, 0)
        x1, x2 = x1 + shift, x2 + shift
    x1, y1, x2, y2 = x1 - pad, y1 - pad * 0.7, x2 + pad, y2 + pad * 0.7
    r = 10 * s
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2, x2 - r, y2,
           x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    cv.create_polygon(pts, smooth=True, fill="white", outline="#2B2B2B", width=max(1, round(1.8 * s)))
    tx = min(max(cx, x1 + 2 * r), x2 - 2 * r)
    cv.create_polygon(tx - 7 * s, y2 - 1, tx + 7 * s, y2 - 1, cx, bottom - 3 * s,
                      fill="white", outline="")
    cv.create_line(tx - 7 * s, y2, cx, bottom - 3 * s, tx + 7 * s, y2, fill="#2B2B2B",
                   width=max(1, round(1.8 * s)))
    cv.tag_raise(tid)
