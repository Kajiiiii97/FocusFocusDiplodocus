"""Draws the cat with plain Tk canvas shapes, so there are no image files to ship.

Every pose is drawn around a ground point (ox, oy). Local coordinates are in "cat units":
x grows toward where the cat faces, y is negative going up. Pen handles scaling and mirroring.
"""

import math

PALETTES = {
    "orange": dict(fur="#F7B267", dark="#E08A3E", belly="#FFF1DC", line="#5B3A29",
                   pink="#F4A0B5", eye="#2E2019", blush="#F9B9B7"),
    "gray": dict(fur="#B9C1CD", dark="#8D97A6", belly="#F1F3F6", line="#3D4450",
                 pink="#F4A0B5", eye="#1F2430", blush="#F6BDC6"),
    "black": dict(fur="#3C3C47", dark="#27272F", belly="#5A5A66", line="#15151A",
                  pink="#E88DA4", eye="#F5D76E", blush="#8E5B6A"),
    "white": dict(fur="#FBFAF7", dark="#E6E1D8", belly="#FFFFFF", line="#4A4440",
                  pink="#F4A0B5", eye="#3A6EA5", blush="#F9C4C4"),
    "calico": dict(fur="#FFF6EA", dark="#E58F46", belly="#FFFFFF", line="#4E3629",
                   pink="#F4A0B5", eye="#2E2019", blush="#F9B9B7"),
}

ANGRY = "#E5484D"
HEART = "#FF6B8B"
YARN = "#7EC8E3"
YARN_DARK = "#4A9CC0"


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
            outline = self.pal["line"]
        self.cv.create_oval(a, self.Y(y1), b, self.Y(y2), fill=fill, outline=outline,
                            width=self.w(width) if outline else 0)

    def poly(self, pts, fill, outline=None, width=2.2, smooth=False):
        if outline is None:
            outline = self.pal["line"]
        self.cv.create_polygon(self._flat(pts), fill=fill, outline=outline,
                               width=self.w(width) if outline else 0, smooth=smooth)

    def line(self, pts, fill=None, width=2.0, smooth=True):
        self.cv.create_line(self._flat(pts), fill=fill or self.pal["line"], width=self.w(width),
                            smooth=smooth, capstyle="round", joinstyle="round")


# --- pieces -------------------------------------------------------------------------------

def draw_head(p, hx, hy, eyes="open", mouth="w", ears="up", angry=False, look=0.0, t=0.0):
    pal, L = p.pal, p.pal["line"]

    for side in (-1, 1):
        if ears == "up":
            outer = [(hx + side * 28, hy - 8), (hx + side * 25, hy - 41), (hx + side * 5, hy - 24)]
            inner = [(hx + side * 24, hy - 14), (hx + side * 23, hy - 34), (hx + side * 11, hy - 23)]
        else:  # flattened back: grumpy
            outer = [(hx + side * 27, hy - 9), (hx + side * 39, hy - 30), (hx + side * 12, hy - 23)]
            inner = [(hx + side * 26, hy - 13), (hx + side * 34, hy - 26), (hx + side * 17, hy - 21)]
        p.poly(outer, fill=pal["fur"], width=2.2)
        p.poly(inner, fill=pal["pink"], outline="")

    p.oval(hx - 31, hy - 26, hx + 31, hy + 24, fill=pal["fur"], width=2.4)
    if pal is PALETTES["calico"]:
        p.oval(hx - 29, hy - 24, hx - 6, hy - 4, fill=pal["dark"], outline="")
        p.oval(hx + 10, hy - 25, hx + 28, hy - 10, fill="#4E3F38", outline="")
    p.oval(hx - 13, hy + 2, hx + 13, hy + 19, fill=pal["belly"], outline="")

    for x1, x2 in ((-8, -6), (0, 0), (8, 6)):
        p.line([(hx + x1, hy - 24), (hx + x2, hy - 16)], fill=pal["dark"], width=3)

    blush = ANGRY if angry else pal["blush"]
    for side in (-1, 1):
        p.oval(hx + side * 20 - 5.5, hy + 5, hx + side * 20 + 5.5, hy + 11, fill=blush, outline="")

    for side in (-1, 1):
        ex, ey = hx + side * 12 + look * 3, hy - 1
        if eyes == "open":
            p.oval(ex - 5, ey - 6.5, ex + 5, ey + 6.5, fill=pal["eye"], outline="")
            p.oval(ex - 3, ey - 5, ex, ey - 2, fill="white", outline="")
        elif eyes == "wide":
            p.oval(ex - 6, ey - 7.5, ex + 6, ey + 7.5, fill=pal["eye"], outline="")
            p.oval(ex - 3.5, ey - 5.5, ex, ey - 2, fill="white", outline="")
            p.oval(ex + 1.5, ey + 2, ex + 3.5, ey + 4, fill="white", outline="")
        elif eyes == "closed":
            p.line([(ex - 5, ey), (ex, ey + 3), (ex + 5, ey)], width=2.2)
        elif eyes == "happy":
            p.line([(ex - 5, ey + 2), (ex, ey - 3), (ex + 5, ey + 2)], width=2.4)
        elif eyes == "sus":
            p.oval(ex - 5, ey - 3, ex + 5, ey + 5.5, fill=pal["eye"], outline="")
            p.line([(ex - 6, ey - 3), (ex + 6, ey - 3)], width=2.4, smooth=False)
        elif eyes == "smug":
            p.oval(ex - 4.5, ey - 1, ex + 4.5, ey + 5, fill=pal["eye"], outline="")
            p.line([(ex - 6, ey - 1), (ex + 6, ey - 1.5)], width=2.4, smooth=False)
        elif eyes == "angry":
            p.oval(ex - 4.5, ey - 3.5, ex + 4.5, ey + 5.5, fill=pal["eye"], outline="")
            p.oval(ex - 2.5, ey - 2, ex - 0.5, ey, fill="white", outline="")
            # Brows slope down toward the nose.
            p.line([(ex + side * 7, ey - 11), (ex - side * 5, ey - 5)], width=3, smooth=False)

    p.poly([(hx - 3.5, hy + 4), (hx + 3.5, hy + 4), (hx, hy + 7.5)], fill=pal["pink"], width=1)
    if mouth in ("w", "tongue"):
        p.line([(hx, hy + 7.5), (hx, hy + 10)], width=1.6, smooth=False)
        p.line([(hx - 7, hy + 10), (hx - 3.5, hy + 13), (hx, hy + 10)], width=1.8)
        p.line([(hx, hy + 10), (hx + 3.5, hy + 13), (hx + 7, hy + 10)], width=1.8)
        if mouth == "tongue":
            p.oval(hx - 2.5, hy + 11.5, hx + 2.5, hy + 17, fill=pal["pink"], width=1)
    elif mouth == "frown":
        p.line([(hx - 6, hy + 15), (hx, hy + 11), (hx + 6, hy + 15)], width=2)
    elif mouth == "yell":
        p.oval(hx - 6, hy + 9, hx + 6, hy + 20, fill="#8C2F39", width=1.6)
        p.oval(hx - 3.5, hy + 14.5, hx + 3.5, hy + 19.5, fill=pal["pink"], outline="")
    elif mouth == "smug":
        p.line([(hx - 6, hy + 12), (hx + 1, hy + 12.5), (hx + 7, hy + 9)], width=2)
    elif mouth == "o":
        p.oval(hx - 3, hy + 10, hx + 3, hy + 16, fill="#8C2F39", width=1.4)

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
    p.line(pts, fill=p.pal["line"], width=width + 4.4)
    p.line(pts, fill=p.pal["fur"], width=width)
    # Darker tip, drawn over the last stretch of the tail.
    (x1, y1), (x2, y2) = pts[-2], pts[-1]
    mx, my = x1 + (x2 - x1) * 0.45, y1 + (y2 - y1) * 0.45
    p.line([(mx, my), (x2, y2)], fill=p.pal["dark"], width=width)


def spiky_oval(p, cx, cy, rx, ry, fill, spikes=26, t=0.0):
    """Puffed-up fur: an oval whose edge zigzags."""
    pts = []
    for i in range(spikes * 2):
        a = math.pi * 2 * i / (spikes * 2)
        r = 1.0 if i % 2 == 0 else 1.13 + 0.03 * math.sin(t * 20 + i)
        pts.append((cx + math.cos(a) * rx * r, cy + math.sin(a) * ry * r))
    p.poly(pts, fill=fill, width=2.2)


def heart(cv, x, y, size, color=HEART):
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
    pal = p.pal
    face = face or {}
    sw = math.sin(t * tail_speed) * tail_amp
    draw_tail(p, [(-14, -8), (-34, -6), (-46, -20), (-44 + sw * 0.5, -40), (-36 + sw, -52)],
              width=15 if puff else 9)

    if puff:
        spiky_oval(p, 0, -27, 27, 29, pal["fur"], t=t)
    else:
        p.oval(-24, -54, 24, 1, fill=pal["fur"], width=2.4)
    if pal is PALETTES["calico"]:
        p.oval(-22, -44, -4, -24, fill=pal["dark"], outline="")
    p.oval(-14, -42, 14, -6, fill=pal["belly"], outline="")

    p.oval(-17, -10, -4, 1, fill=pal["fur"], width=2)
    lift = paw * 7
    p.oval(4, -10 - lift, 17, 1 - lift, fill=pal["fur"], width=2)

    draw_head(p, lean, -64, t=t, **face)

    if groom:
        # A paw held up to the mouth, bobbing while it licks.
        bob = math.sin(t * 7) * 2.5
        p.oval(3, -58 + bob, 17, -44 + bob, fill=pal["fur"], width=2)
        p.line([(7, -46 + bob), (7, -49 + bob)], width=1.2, smooth=False)
        p.line([(11, -46 + bob), (11, -49 + bob)], width=1.2, smooth=False)


def _leg(p, lx, top, phase, amp, color):
    swing = math.sin(phase) * 7 * amp
    lift = max(0.0, math.cos(phase)) * 4 * amp
    p.line([(lx, top), (lx + swing, -4 - lift)], fill=p.pal["line"], width=11.5)
    p.line([(lx, top), (lx + swing, -4 - lift)], fill=color, width=7.5)


def pose_walk(p, t, phase, face=None, amp=1.0, crouch=0.0, wiggle=0.0, stretch=0.0):
    """Side-on body with a front-facing head. crouch lowers it for stalking, stretch is mid-pounce."""
    pal = p.pal
    face = face or {"eyes": "open", "mouth": "w"}
    bob = abs(math.sin(phase)) * 2 * amp
    by = -30 + crouch * 11 - bob
    wig = math.sin(t * 26) * 2.5 * wiggle
    sw = math.sin(t * (9 if wiggle else 3)) * (7 if wiggle else 4)

    draw_tail(p, [(-27 + wig, by - 3), (-40 + wig, by - 12), (-45 + sw, by - 28), (-38 + sw, by - 40)])

    if stretch:
        legs = [(-18, -0.9), (16, 0.9), (-10, -0.9), (24, 0.9)]
        for i, (lx, dirn) in enumerate(legs):
            color = pal["dark"] if i < 2 else pal["fur"]
            end = (lx + dirn * 12 * stretch, by + 14 + 4 * (1 - stretch))
            p.line([(lx, by + 4), end], fill=pal["line"], width=11.5)
            p.line([(lx, by + 4), end], fill=color, width=7.5)
    else:
        _leg(p, -18 + wig, by + 4, phase + math.pi, amp, pal["dark"])
        _leg(p, 16, by + 4, phase, amp, pal["dark"])

    p.oval(-32 + wig, by - 14, 32, by + 13, fill=pal["fur"], width=2.4)
    if pal is PALETTES["calico"]:
        p.oval(-24 + wig, by - 12, -2, by + 2, fill=pal["dark"], outline="")
        p.oval(4, by - 13, 20, by - 2, fill="#4E3F38", outline="")
    p.oval(-20, by + 2, 20, by + 11, fill=pal["belly"], outline="")
    for x in (-14, -4, 6):
        p.line([(x + wig * 0.5, by - 13), (x + 3, by - 5)], fill=pal["dark"], width=3)

    if not stretch:
        _leg(p, -10 + wig, by + 4, phase, amp, pal["fur"])
        _leg(p, 24, by + 4, phase + math.pi, amp, pal["fur"])

    draw_head(p, 28, by - 20 - bob * 0.5, t=t, **face)


def pose_sleep(p, t):
    pal = p.pal
    br = math.sin(t * 1.6)
    p.oval(-40, -33 - br * 1.3, 36, 1, fill=pal["fur"], width=2.4)
    if pal is PALETTES["calico"]:
        p.oval(-34, -30, -8, -12, fill=pal["dark"], outline="")
    for x in (-22, -12, -2):
        p.line([(x, -31 - br), (x + 3, -23 - br)], fill=pal["dark"], width=3)
    # Tail curled around the front.
    draw_tail(p, [(-38, -12), (-32, -2), (-6, 1), (14, -2)])
    draw_head(p, 22, -24 + br * 0.6, eyes="closed", mouth="w", t=t)


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
