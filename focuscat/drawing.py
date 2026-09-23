"""Draws the cat with plain Tk canvas shapes, so there are no image files to ship.

Every pose is drawn around a ground point (ox, oy). Local coordinates are in "cat units":
x grows toward where the cat faces, y is negative going up. Pen handles scaling and mirroring.

The pixel style lives in pixel.py. The minimal style is a side-on "blob" cat: every part is the same flat colour with no outline,
so the pieces melt into one silhouette and only a tiny line face stands out. The outlined
style is a chibi cat with a big front-facing head.
"""

import math
import re

from focuscat import pixel

ANGRY = "#E5484D"
HEART = "#FF6B8B"
YARN = "#7EC8E3"
YARN_DARK = "#4A9CC0"

EAR_SHAPES = ("pointy", "round", "folded")
EYE_STYLES = ("content", "dots", "big")
STYLES = ("pixel", "minimal", "outlined")
PATTERNS = tuple(pixel.PATTERNS)

# Presets for the settings window: fur, inner ear, eyes, stripes, second colour, pattern.
PRESETS = {
    "Ginger": ("#F0A35E", "#F4A7B0", "#2A2226", False, "#F3EAD8", "bib"),
    "Tabby": ("#E39A58", "#F4A7B0", "#2A2226", True, "#F3EAD8", "bib"),
    "Tuxedo": ("#34343C", "#D98FA3", "#F2D15C", False, "#F4F4F4", "bib"),
    "Calico": ("#FFF6EA", "#F4A7B0", "#2A2226", False, "#E58F46", "patches"),
    "Gray": ("#A9B1BC", "#F4B8C4", "#2B3340", False, "#F2F2F2", "socks"),
    "Cloud": ("#D6E4F0", "#F2C4CF", "#2E2F3A", False, "#FFFFFF", "solid"),
    "Snow": ("#F7F5F0", "#F7B6C2", "#4F86C6", False, "#F7F5F0", "solid"),
    "Cocoa": ("#8A5A44", "#E8A6A6", "#2A1A14", False, "#D9B99B", "socks"),
}

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
    """Turn the user's choices into every colour and switch the drawing code needs."""
    fur = cfg["fur_color"]
    dark_fur = luminance(fur) < 0.3
    # Face lines need contrast: dark lines on light fur, light lines on dark fur.
    line = mix(fur, "#FFFFFF", 0.55) if dark_fur else mix(fur, "#000000", 0.62)
    minimal = cfg["style"] == "minimal"
    return {
        "style": cfg["style"],
        "fur": fur,
        "dark": mix(fur, "#FFFFFF", 0.12) if dark_fur else mix(fur, "#000000", 0.14),
        "belly": cfg["second_color"] if cfg["pattern"] == "bib" else mix(fur, "#FFFFFF", 0.6),
        "second": cfg["second_color"],
        "pattern": cfg["pattern"],
        "px_outline": mix(fur, "#000000", 0.8),
        "px_shade": mix(fur, "#FFFFFF", 0.18) if dark_fur else mix(fur, "#000000", 0.18),
        "px_nose": mix(cfg["ear_color"], "#C04070", 0.35),
        "line": line,
        "outline": "" if minimal else line,
        "pink": cfg["ear_color"],
        "eye": cfg["eye_color"],
        "blush": mix(fur, "#FF7B93", 0.4),
        "minimal": minimal,
        "stripes": cfg["stripes"],
        "blush_on": cfg["blush"],
        "whiskers": cfg["whiskers"],
        "ears": cfg["ear_shape"],
        "eye_style": cfg["eye_style"],
    }


class Pen:
    def __init__(self, cv, ox, oy, s, facing, pal):
        self.cv, self.ox, self.oy, self.s, self.f, self.pal = cv, ox, oy, s, facing, pal

    def X(self, dx):
        return self.ox + self.f * dx * self.s

    def Y(self, dy):
        return self.oy + dy * self.s

    def w(self, width):
        return max(1, round(width * self.s))

    def _flat(self, pts):
        out = []
        for x, y in pts:
            out += [self.X(x), self.Y(y)]
        return out

    def oval(self, x1, y1, x2, y2, fill, outline=None, width=2.2):
        a, b = sorted((self.X(x1), self.X(x2)))
        if outline is None:
            outline = self.pal["outline"]
        self.cv.create_oval(a, self.Y(y1), b, self.Y(y2), fill=fill, outline=outline,
                            width=self.w(width) if outline else 0)

    def poly(self, pts, fill, outline=None, width=2.2, smooth=False):
        if outline is None:
            outline = self.pal["outline"]
        self.cv.create_polygon(self._flat(pts), fill=fill, outline=outline,
                               width=self.w(width) if outline else 0, smooth=smooth)

    def line(self, pts, fill=None, width=2.0, smooth=True):
        self.cv.create_line(self._flat(pts), fill=fill or self.pal["line"], width=self.w(width),
                            smooth=smooth, capstyle="round", joinstyle="round")


# --- pieces -------------------------------------------------------------------------------

def _ears(p, hx, hy, back):
    pal, shape = p.pal, p.pal["ears"]
    for side in (-1, 1):
        def pts(raw):
            return [(hx + side * x, hy + y) for x, y in raw]

        if shape == "folded":
            # Little flaps that barely poke over the head, like a Scottish fold.
            p.poly(pts([(3, -22), (11, -31), (24, -28), (30, -13)]), fill=pal["fur"], smooth=True)
            continue
        if shape == "round":
            if back:
                outer = [(26, -8), (37, -24), (34, -33), (22, -30), (9, -22)]
                inner = [(25, -13), (32, -24), (29, -29), (20, -26)]
            else:
                outer = [(29, -6), (30, -31), (22, -41), (11, -35), (4, -24)]
                inner = [(24, -14), (25, -30), (19, -35), (12, -28)]
            p.poly(pts(outer), fill=pal["fur"], smooth=True)
            p.poly(pts(inner), fill=pal["pink"], outline="", smooth=True)
            continue
        if back:
            outer = [(27, -9), (39, -30), (12, -23)]
            inner = [(26, -13), (34, -26), (17, -21)]
        else:
            outer = [(28, -8), (25, -41), (5, -24)]
            inner = [(24, -14), (23, -34), (11, -23)]
        p.poly(pts(outer), fill=pal["fur"])
        p.poly(pts(inner), fill=pal["pink"], outline="")


def _eye(p, ex, ey, side, kind):
    pal = p.pal
    big = pal["eye_style"] == "big"
    k = 1.0 if big else 0.62 if not pal["minimal"] else 0.5

    def dot(rx, ry, top=None, bottom=None):
        p.oval(ex - rx * k, (top if top is not None else ey - ry * k),
               ex + rx * k, (bottom if bottom is not None else ey + ry * k), fill=pal["eye"], outline="")

    if kind == "open" and pal["eye_style"] == "content":
        kind = "closed"
    if kind == "open":
        dot(5, 6.5)
        if big:
            p.oval(ex - 3, ey - 5, ex, ey - 2, fill="white", outline="")
    elif kind == "wide":
        dot(6, 7.5)
        if big:
            p.oval(ex - 3.5, ey - 5.5, ex, ey - 2, fill="white", outline="")
            p.oval(ex + 1.5, ey + 2, ex + 3.5, ey + 4, fill="white", outline="")
        else:
            p.oval(ex - 2, ey - 3, ex - 0.2, ey - 1.2, fill="white", outline="")
    elif kind == "closed":
        p.line([(ex - 4.5, ey), (ex, ey + 2.6), (ex + 4.5, ey)], fill=pal["eye"], width=2.1)
    elif kind == "happy":
        p.line([(ex - 4.5, ey + 2), (ex, ey - 2.5), (ex + 4.5, ey + 2)], fill=pal["eye"], width=2.2)
    elif kind == "sus":
        dot(5, 4.5, top=ey - 2, bottom=ey + 5.5 * k + 1)
        p.line([(ex - 5.5, ey - 2.5), (ex + 5.5, ey - 2.5)], fill=pal["eye"], width=2.2, smooth=False)
    elif kind == "smug":
        dot(4.5, 3, top=ey - 1, bottom=ey + 5 * k + 1)
        p.line([(ex - 5.5, ey - 1), (ex + 5.5, ey - 1.5)], fill=pal["eye"], width=2.2, smooth=False)
    elif kind == "angry":
        dot(4.5, 4.5, top=ey - 3 * k, bottom=ey + 5 * k)
        # Brows slope down toward the nose.
        p.line([(ex + side * 7, ey - 10), (ex - side * 4.5, ey - 5)], width=2.8, smooth=False)


def draw_head(p, hx, hy, eyes="open", mouth="w", ears="up", angry=False, look=0.0, t=0.0):
    pal = p.pal
    _ears(p, hx, hy, back=(ears == "back"))
    p.oval(hx - 31, hy - 26, hx + 31, hy + 24, fill=pal["fur"], width=2.4)

    if not pal["minimal"]:
        p.oval(hx - 13, hy + 2, hx + 13, hy + 19, fill=pal["belly"], outline="")
    if pal["stripes"]:
        for x1, x2 in ((-8, -6), (0, 0), (8, 6)):
            p.line([(hx + x1, hy - 24), (hx + x2, hy - 16)], fill=pal["dark"], width=3)

    if pal["blush_on"] or angry:
        blush = ANGRY if angry else pal["blush"]
        for side in (-1, 1):
            p.oval(hx + side * 19 - 5, hy + 5, hx + side * 19 + 5, hy + 10.5, fill=blush, outline="")

    for side in (-1, 1):
        _eye(p, hx + side * 12 + look * 3, hy - 1, side, eyes)

    p.poly([(hx - 3, hy + 4), (hx + 3, hy + 4), (hx, hy + 7)], fill=pal["pink"], outline=pal["line"], width=1)
    if mouth in ("w", "tongue"):
        p.line([(hx - 5.5, hy + 9.5), (hx - 2.7, hy + 12), (hx, hy + 9.5)], width=1.7)
        p.line([(hx, hy + 9.5), (hx + 2.7, hy + 12), (hx + 5.5, hy + 9.5)], width=1.7)
        if mouth == "tongue":
            p.oval(hx - 2.5, hy + 11, hx + 2.5, hy + 16, fill=pal["pink"], outline="")
    elif mouth == "frown":
        p.line([(hx - 5, hy + 14), (hx, hy + 10.5), (hx + 5, hy + 14)], width=1.9)
    elif mouth == "yell":
        p.oval(hx - 5.5, hy + 9, hx + 5.5, hy + 19, fill="#7A2833", outline="")
        p.oval(hx - 3.2, hy + 14, hx + 3.2, hy + 18.5, fill=pal["pink"], outline="")
    elif mouth == "smug":
        p.line([(hx - 5, hy + 11.5), (hx + 1, hy + 12), (hx + 6, hy + 9)], width=1.9)
    elif mouth == "o":
        p.oval(hx - 2.8, hy + 10, hx + 2.8, hy + 15.5, fill="#7A2833", outline="")

    if pal["whiskers"]:
        for side in (-1, 1):
            p.line([(hx + side * 23, hy + 5), (hx + side * 39, hy + 1)], width=1.3, smooth=False)
            p.line([(hx + side * 23, hy + 9), (hx + side * 39, hy + 11)], width=1.3, smooth=False)

    if angry:
        anger_mark(p, hx + 27, hy - 31, 1 + 0.15 * math.sin(t * 9))


def anger_mark(p, ax, ay, k=1.0):
    for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        p.line([(ax + sx * 2 * k, ay + sy * 7 * k), (ax + sx * 2 * k, ay + sy * 2 * k),
                (ax + sx * 7 * k, ay + sy * 2 * k)], fill=ANGRY, width=2.8, smooth=False)


def draw_tail(p, pts, width=9.0):
    pal = p.pal
    if not pal["minimal"]:
        p.line(pts, fill=pal["line"], width=width + 4.4)
    p.line(pts, fill=pal["fur"], width=width)
    if pal["stripes"]:
        (x1, y1), (x2, y2) = pts[-2], pts[-1]
        mx, my = x1 + (x2 - x1) * 0.45, y1 + (y2 - y1) * 0.45
        p.line([(mx, my), (x2, y2)], fill=pal["dark"], width=width)


def _limb(p, a, b, color=None):
    pal = p.pal
    if not pal["minimal"]:
        p.line([a, b], fill=pal["line"], width=11.5)
    p.line([a, b], fill=color or pal["fur"], width=7.5 if not pal["minimal"] else 9)


def spiky_oval(p, cx, cy, rx, ry, fill, spikes=26, t=0.0):
    """Puffed-up fur: an oval whose edge zigzags."""
    pts = []
    for i in range(spikes * 2):
        a = math.pi * 2 * i / (spikes * 2)
        r = 1.0 if i % 2 == 0 else 1.13 + 0.03 * math.sin(t * 20 + i)
        pts.append((cx + math.cos(a) * rx * r, cy + math.sin(a) * ry * r))
    p.poly(pts, fill=fill, width=2.2)


def heart(cv, x, y, size, color=HEART, pixelated=False):
    if pixelated:
        return pixel.heart(cv, x, y, size)
    pts = []
    for i in range(24):
        a = math.pi * 2 * i / 24
        hx = 16 * math.sin(a) ** 3
        hy = 13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a)
        pts += [x + hx * size / 32, y - hy * size / 32]
    cv.create_polygon(pts, fill=color, outline="", smooth=True)


def yarn(cv, x, y, r, spin):
    cv.create_oval(x - r, y - r, x + r, y + r, fill=YARN, outline=YARN_DARK, width=max(1, round(r / 5)))
    for k in (-0.4, 0.15, 0.6):
        a = spin + k * 2
        cv.create_line(x + math.cos(a) * r * 0.9, y + math.sin(a) * r * 0.9,
                       x + math.cos(a + 2.2) * r * 0.9, y + math.sin(a + 2.2) * r * 0.9,
                       fill=YARN_DARK, width=max(1, round(r / 6)), smooth=True)


# --- poses --------------------------------------------------------------------------------

def pose_sit(p, t, face=None, puff=False, paw=0.0, groom=False, tail_speed=2.2, tail_amp=6.0, lean=0.0):
    if p.pal["style"] == "pixel":
        return pixel.sit(p, t, face, puff, paw, groom, tail_speed, tail_amp)
    if p.pal["minimal"]:
        return blob_stand(p, t, face, puff, paw, groom, tail_speed, tail_amp)
    pal = p.pal
    face = face or {}
    sw = math.sin(t * tail_speed) * tail_amp
    draw_tail(p, [(-14, -8), (-34, -6), (-46, -20), (-44 + sw * 0.5, -40), (-36 + sw, -52)],
              width=15 if puff else 9)

    if puff:
        spiky_oval(p, 0, -27, 27, 29, pal["fur"], t=t)
    else:
        p.oval(-24, -54, 24, 1, fill=pal["fur"], width=2.4)
    if not pal["minimal"]:
        p.oval(-14, -42, 14, -6, fill=pal["belly"], outline="")

    p.oval(-17, -10, -4, 1, fill=pal["fur"], width=2)
    lift = paw * 7
    p.oval(4, -10 - lift, 17, 1 - lift, fill=pal["fur"], width=2)

    draw_head(p, lean, -64, t=t, **face)

    if groom:
        # A paw held up to the mouth, bobbing while it licks. It gets a soft edge even in the
        # minimal style, or it would vanish into the face.
        bob = math.sin(t * 7) * 2.5
        p.oval(3, -58 + bob, 17, -44 + bob, fill=pal["fur"], outline=pal["dark"], width=1.6)


def pose_walk(p, t, phase, face=None, amp=1.0, crouch=0.0, wiggle=0.0, stretch=0.0):
    """Side-on body with a front-facing head. crouch lowers it for stalking, stretch is mid-pounce."""
    if p.pal["style"] == "pixel":
        return pixel.walk(p, t, phase, face, amp, crouch, wiggle, stretch)
    if p.pal["minimal"]:
        return blob_walk(p, t, phase, face, amp, crouch, wiggle, stretch)
    pal = p.pal
    far = pal["fur"] if pal["minimal"] else pal["dark"]
    face = face or {"eyes": "open", "mouth": "w"}
    bob = abs(math.sin(phase)) * 2 * amp
    by = -30 + crouch * 11 - bob
    wig = math.sin(t * 26) * 2.5 * wiggle
    sw = math.sin(t * (9 if wiggle else 3)) * (7 if wiggle else 4)

    def leg(lx, ph, color):
        swing = math.sin(ph) * 7 * amp
        lift = max(0.0, math.cos(ph)) * 4 * amp
        _limb(p, (lx, by + 4), (lx + swing, -4 - lift), color)

    draw_tail(p, [(-27 + wig, by - 3), (-40 + wig, by - 12), (-45 + sw, by - 28), (-38 + sw, by - 40)])

    if stretch:
        for i, (lx, dirn) in enumerate([(-18, -0.9), (16, 0.9), (-10, -0.9), (24, 0.9)]):
            end = (lx + dirn * 12 * stretch, by + 14 + 4 * (1 - stretch))
            _limb(p, (lx, by + 4), end, far if i < 2 else pal["fur"])
    else:
        leg(-18 + wig, phase + math.pi, far)
        leg(16, phase, far)

    p.oval(-32 + wig, by - 14, 32, by + 13, fill=pal["fur"], width=2.4)
    if not pal["minimal"]:
        p.oval(-20, by + 2, 20, by + 11, fill=pal["belly"], outline="")
    if pal["stripes"]:
        for x in (-14, -4, 6):
            p.line([(x + wig * 0.5, by - 13), (x + 3, by - 5)], fill=pal["dark"], width=3)

    if not stretch:
        leg(-10 + wig, phase, pal["fur"])
        leg(24, phase + math.pi, pal["fur"])

    draw_head(p, 28, by - 20 - bob * 0.5, t=t, **face)


def pose_sleep(p, t):
    if p.pal["style"] == "pixel":
        return pixel.sleep(p, t)
    if p.pal["minimal"]:
        return blob_sleep(p, t)
    pal = p.pal
    br = math.sin(t * 1.6)
    p.oval(-40, -33 - br * 1.3, 36, 1, fill=pal["fur"], width=2.4)
    if pal["stripes"]:
        for x in (-22, -12, -2):
            p.line([(x, -31 - br), (x + 3, -23 - br)], fill=pal["dark"], width=3)
    # Tail curled around the front. In the minimal style it needs a soft edge to read.
    tail = [(-38, -12), (-32, -2), (-6, 1), (14, -2)]
    if pal["minimal"]:
        p.line(tail, fill=pal["dark"], width=11)
    draw_tail(p, tail)
    draw_head(p, 22, -24 + br * 0.6, eyes="closed", mouth="w", t=t)


# --- the minimal "blob" cat ---------------------------------------------------------------
# Side view. Head is the front bump of the body at roughly (26, -52).

BLOB_HEAD = (26, -52)


def _rrect(p, x1, y1, x2, y2, r, fill, outline=""):
    pts = [(x1 + r, y1), (x2 - r, y1), (x2, y1), (x2, y1 + r), (x2, y2 - r), (x2, y2), (x2 - r, y2),
           (x1 + r, y2), (x1, y2), (x1, y2 - r), (x1, y1 + r), (x1, y1)]
    p.poly(pts, fill=fill, outline=outline, smooth=True)


def _blob_ears(p, hx, hy, back):
    pal, shape = p.pal, p.pal["ears"]
    if shape == "folded":
        for pts in ([(hx - 19, hy - 12), (hx - 16, hy - 24), (hx - 4, hy - 22)],
                    [(hx + 3, hy - 22), (hx + 14, hy - 25), (hx + 19, hy - 12)]):
            p.poly(pts, fill=pal["fur"], smooth=True)
        return
    if back:
        ears = [([(hx - 17, hy - 12), (hx - 30, hy - 27), (hx - 4, hy - 20)],
                 [(hx - 15, hy - 16), (hx - 25, hy - 24), (hx - 8, hy - 20)]),
                ([(hx + 4, hy - 20), (hx + 27, hy - 28), (hx + 19, hy - 10)],
                 [(hx + 8, hy - 20), (hx + 22, hy - 25), (hx + 17, hy - 14)])]
    else:
        ears = [([(hx - 20, hy - 10), (hx - 17, hy - 35), (hx - 17, hy - 35), (hx - 1, hy - 20)],
                 [(hx - 16, hy - 17), (hx - 15, hy - 29), (hx - 6, hy - 20)]),
                ([(hx + 2, hy - 20), (hx + 16, hy - 36), (hx + 16, hy - 36), (hx + 21, hy - 10)],
                 [(hx + 7, hy - 20), (hx + 15, hy - 30), (hx + 17, hy - 17)])]
    if shape == "round":
        tilt = 5 if back else 0
        for cx in (hx - 11 - tilt, hx + 11 + tilt):
            p.oval(cx - 9, hy - 32 + tilt, cx + 9, hy - 12, fill=pal["fur"], outline="")
            if pal["pink"] != pal["fur"]:
                p.oval(cx - 4.5, hy - 27 + tilt, cx + 4.5, hy - 17, fill=pal["pink"], outline="")
        return
    for outer, inner in ears:
        p.poly(outer, fill=pal["fur"], smooth=True)
        if pal["pink"] != pal["fur"]:
            p.poly(inner, fill=pal["pink"], smooth=True)


def blob_face(p, hx, hy, eyes="open", mouth="w", angry=False, look=0.0, t=0.0, **_):
    pal = p.pal
    fx, fy = hx + 4 + look * 2, hy + 1
    if pal["blush_on"] or angry:
        for ex in (fx - 10, fx + 11):
            p.oval(ex - 4, fy + 4, ex + 4, fy + 8, fill=ANGRY if angry else pal["blush"], outline="")
    for side, ex in ((-1, fx - 9), (1, fx + 9)):
        _eye(p, ex, fy - 2, side, eyes)
    L = pal["line"]
    if mouth in ("w", "tongue"):
        p.line([(fx - 4.5, fy + 3.5), (fx - 2.2, fy + 6), (fx, fy + 3.8), (fx + 2.2, fy + 6), (fx + 4.5, fy + 3.5)],
               fill=L, width=1.7)
        if mouth == "tongue":
            p.oval(fx - 2, fy + 5, fx + 2, fy + 9.5, fill=pal["pink"], outline="")
    elif mouth == "frown":
        p.line([(fx - 4, fy + 8), (fx, fy + 5), (fx + 4, fy + 8)], fill=L, width=1.8)
    elif mouth == "yell":
        p.oval(fx - 4.5, fy + 3, fx + 4.5, fy + 12, fill="#7A2833", outline="")
    elif mouth == "smug":
        p.line([(fx - 4, fy + 5.5), (fx + 1, fy + 6), (fx + 5, fy + 3)], fill=L, width=1.8)
    elif mouth == "o":
        p.oval(fx - 2.5, fy + 3.5, fx + 2.5, fy + 9, fill="#7A2833", outline="")
    if pal["whiskers"]:
        for dy in (4, 7):
            p.line([(fx + 14, fy + dy), (fx + 26, fy + dy - 2 + (dy - 4))], fill=L, width=1.2, smooth=False)
    if angry:
        anger_mark(p, hx + 20, hy - 34, 1 + 0.15 * math.sin(t * 9))


def _blob_tail(p, pts, width=11):
    p.line(pts, fill=p.pal["fur"], width=width)
    if p.pal["stripes"]:
        for i in (1, 2):
            (x1, y1), (x2, y2) = pts[i], pts[i + 1]
            p.line([((x1 + x2) / 2 - 5, (y1 + y2) / 2), ((x1 + x2) / 2 + 5, (y1 + y2) / 2)],
                   fill=p.pal["dark"], width=3)


def _blob_leg(p, x, top, foot_x, foot_y):
    p.line([(x, top), (foot_x, foot_y)], fill=p.pal["fur"], width=12.5)


def _blob_stripes(p, by):
    if p.pal["stripes"]:
        for x in (-26, -15, -4):
            p.line([(x, by - 50), (x + 2, by - 41)], fill=p.pal["dark"], width=3.5)


def blob_body(p, t, face, by=0.0, legs=None, tail_sw=0.0, puff=False, crouch=0.0, wig=0.0, stretch=0.0,
              head_dy=0.0):
    pal = p.pal
    breathe = math.sin(t * 2.0) * 0.8
    top = -53 + by - breathe
    x1 = -40 - stretch * 6 + wig
    x2 = 32 + stretch * 4
    hx, hy = BLOB_HEAD[0] + stretch * 6, BLOB_HEAD[1] + by + head_dy

    tw = 17 if puff else 11
    _blob_tail(p, [(x1 + 6, top + 6), (x1 - 5, top - 2), (x1 - 9 + tail_sw * 0.4, top - 20),
                   (x1 - 3 + tail_sw, top - 33)], tw)
    if puff:
        spiky_oval(p, (x1 + x2) / 2, top + 17, (x2 - x1) / 2 + 3, 22, pal["fur"], t=t)
    for x, top_y, fx, fy in legs or []:
        _blob_leg(p, x, top_y, fx, fy)
    _rrect(p, x1, top, x2, -12 + by, 19, pal["fur"])
    _blob_stripes(p, by)
    _blob_ears(p, hx, hy, back=face.get("ears") == "back")
    p.oval(hx - 23, hy - 21, hx + 23, hy + 21, fill=pal["fur"], outline="")
    blob_face(p, hx, hy, t=t, **face)
    return hx, hy


def blob_stand(p, t, face=None, puff=False, paw=0.0, groom=False, tail_speed=2.2, tail_amp=6.0):
    face = face or {"eyes": "open", "mouth": "w"}
    sw = math.sin(t * tail_speed) * tail_amp
    lift = paw * 6
    legs = [(-32, -20, -32, -6), (-20, -20, -20, -6), (13, -20, 13, -6), (25, -20, 25, -6 - lift)]
    hx, hy = blob_body(p, t, face, legs=legs, tail_sw=sw, puff=puff, head_dy=3 if groom else 0)
    if groom:
        bob = math.sin(t * 7) * 2.5
        p.line([(24, -24), (hx + 8, hy + 12 + bob)], fill=p.pal["dark"], width=13)
        p.line([(24, -24), (hx + 8, hy + 12 + bob)], fill=p.pal["fur"], width=11)


def blob_walk(p, t, phase, face=None, amp=1.0, crouch=0.0, wiggle=0.0, stretch=0.0):
    face = face or {"eyes": "open", "mouth": "w"}
    bob = abs(math.sin(phase)) * 1.5 * amp
    by = crouch * 9 - bob
    wig = math.sin(t * 26) * 2.5 * wiggle
    sw = math.sin(t * (9 if wiggle else 3)) * (7 if wiggle else 4)
    top = -20 + by
    if stretch:
        legs = [(-32, top, -46, -6), (-21, top, -36, -4), (14, top, 36, -8), (25, top, 46, -10)]
    else:
        legs = []
        for x, ph in ((-32, 0), (-20, math.pi), (13, math.pi), (25, 0)):
            swing = math.sin(phase + ph) * 6 * amp
            lift = max(0.0, math.cos(phase + ph)) * 3.5 * amp
            legs.append((x + (wig if x < 0 else 0), top, x + swing + (wig if x < 0 else 0), -6 - lift))
    blob_body(p, t, face, by=by, legs=legs, tail_sw=sw, crouch=crouch, wig=wig, stretch=stretch,
              head_dy=crouch * 3)


def blob_sleep(p, t):
    pal = p.pal
    br = math.sin(t * 1.6)
    top = -34 - br * 1.2
    _rrect(p, -42, top, 30, 0, 17, pal["fur"])
    _blob_stripes(p, 16)
    hx, hy = 22, -28 + br * 0.5
    _blob_ears(p, hx, hy, back=False)
    p.oval(hx - 22, hy - 19, hx + 22, hy + 19, fill=pal["fur"], outline="")
    # Tail wrapped around the front, with a soft edge so it doesn't vanish into the body.
    tail = [(-40, -12), (-34, -1), (-10, 1), (8, -2)]
    p.line(tail, fill=pal["dark"], width=12)
    p.line(tail, fill=pal["fur"], width=10)
    blob_face(p, hx, hy, eyes="closed", mouth="w", t=t)


def portrait(p):
    """Just the head, centred on the pen's origin (for the settings window's quick picks)."""
    if p.pal["style"] == "pixel":
        pixel.portrait(p)
    elif p.pal["minimal"]:
        _blob_ears(p, 0, 0, back=False)
        p.oval(-23, -21, 23, 21, fill=p.pal["fur"], outline="")
        blob_face(p, -4, 0)
    else:
        draw_head(p, 0, 0)


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
