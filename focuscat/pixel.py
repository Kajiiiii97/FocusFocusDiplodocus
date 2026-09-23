"""Pixel-art cat. Sprites are little text grids that get stacked into one image and then
drawn as crisp squares.

Letters in the grids:
    O outline   F fur   D darker fur   P inner ear
    m face mask   c chest/belly   k paws   t tail tip   p patches
The lowercase ones are fur-coloured unless the chosen two-tone pattern paints them in the
second colour.

Sprite coordinates: x = 0 is the middle of the cat, y = -1 is the row touching the ground.
"""

PATTERNS = {
    "solid": "",
    "bib": "mckt",
    "socks": "kt",
    "patches": "pt",
}

# --- head (18 x 14), front-facing ----------------------------------------------------------

EARS = {
    "pointy": [".OO............OO.",
               ".OPO..........OPO.",
               ".OPPO........OPPO.",
               ".OFPFOOOOOOOOFPFO."],
    "round": ["..................",
              "..OOO........OOO..",
              ".OPPPO......OPPPO.",
              ".OFPFFOOOOOOFFPFO."],
    "folded": ["..................",
               "..................",
               "..OOOO......OOOO..",
               ".ODDDFOOOOOOFDDDO."],
    "back": ["..................",
             "OOO............OOO",
             "OPPOO........OOPPO",
             ".OPPFOOOOOOOOFPPO."],
}

FACE = [".OFFppFFFFFFFFFFO.",
        "OFppppFFFFFFFFFFFO",
        "OFFppFFFmmFFFFFFFO",
        "OFFFFFFmmmmFFFFFFO",
        "OFFFFmmmmmmmmFFFFO",
        "OFFFmmmmmmmmmmFFFO",
        "OFFmmmmmmmmmmmmFFO",
        ".OFmmmmmmmmmmmmFO.",
        "..OOmmmmmmmmmmOO..",
        "....OOOOOOOOOO...."]

L_EYE, R_EYE = (4, 7), (12, 7)  # top-left pixel of each 2-wide eye, in head grid coords

# --- sitting body (18 wide), front-facing --------------------------------------------------

SIT_BODY = ["...OccccccccccO...",
            "..OFFccccccccFFO..",
            ".OppFccccccccFFFO.",
            ".OpppFccccccFFFFO.",
            "OFppFFccccccFFFFFO",
            "OFFFFFFccccFFFFFFO",
            "OFFFFOkkOOkkOFFFFO",
            "OFFFOkkkOOkkkOFFFO",
            "OFFOkkkkOOkkkkOFFO",
            ".OOOOOOOOOOOOOOOO."]

SIT_TAILS = [
    [".OO..",
     "OttO.",
     "OttO.",
     "OFFO.",
     "OFFO.",
     ".OFFO",
     ".OFFO",
     ".OFFO",
     "OFFO."],
    ["..OO.",
     ".OttO",
     ".OttO",
     ".OFFO",
     "OFFO.",
     "OFFO.",
     ".OFFO",
     ".OFFO",
     "OFFO."],
]

# --- side-on bodies (18 wide) --------------------------------------------------------------

WALK_BODY = [".OOOOOOOOOOOOOO...",
             "OFFppFFFFFFFFFFO..",
             "OFppppFFFFFFFFFFO.",
             "OFFppFFFFFFFFFFFO.",
             "OFFFFFFFcccccccFO.",
             ".OFFFFFcccccccccO.",
             "..OOOOOOOOOOOOOO.."]

LEG = ["OFFO",
       "OFFO",
       "OFFO",
       "OkkO",
       "OOOO"]

WALK_TAILS = [
    [".OO...",
     "OttO..",
     "OFFO..",
     ".OFFO.",
     "..OFFO"],
    ["..OO..",
     ".OttO.",
     ".OFFO.",
     ".OFFO.",
     "..OFFO"],
]

LOAF = ["..OOOOOOOOOOOO....",
        ".OFFppFFFFFFFFO...",
        "OFppppFFFFFFFFFO..",
        "OFFppFFFFFFFFFFO..",
        "OFFFFFFFFFFFFFFO..",
        "OFFFFFFFFFFFFFFO..",
        ".OOOOOOOOOOOOOO..."]

GROOM_PAW = [".OO.",
             "OkkO",
             "OkkO",
             "OkkO"]

ANGER = [".R.R.",
         "RR.RR",
         ".....",
         "RR.RR",
         ".R.R."]

HEART = [".RR.RR.",
         "RRRRRRR",
         "RRRRRRR",
         ".RRRRR.",
         "..RRR..",
         "...R..."]


class Sprite:
    def __init__(self):
        self.px = {}

    def blit(self, rows, x0, y0):
        for r, row in enumerate(rows):
            for c, ch in enumerate(row):
                if ch != ".":
                    self.px[(x0 + c, y0 + r)] = ch

    def put(self, x0, y0, points):
        for dx, dy, ch in points:
            self.px[(x0 + dx, y0 + dy)] = ch

    def puff(self, frame):
        """Fluff up: sprout outline pixels on every other empty spot around the edge."""
        add = {}
        for (x, y), ch in self.px.items():
            if ch != "O":
                continue
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y - 1)):
                if (nx, ny) not in self.px and (nx + ny + frame) % 2 == 0 and ny < -1:
                    add[(nx, ny)] = "O"
        self.px.update(add)

    def top(self):
        return min(y for _, y in self.px) if self.px else 0


def colors(pal):
    second = set(PATTERNS.get(pal["pattern"], ""))
    table = {
        "O": pal["px_outline"], "F": pal["fur"], "D": pal["px_shade"], "P": pal["pink"],
        "E": pal["eye"], "W": "#FFFFFF", "N": pal["px_nose"], "B": pal["blush"], "R": "#D93A45",
        "X": "#7A2833",
    }
    for ch in "mckpt":
        table[ch] = pal["second"] if ch in second else pal["fur"]
    return table


def render(p, sprite):
    """Draw the sprite with the pen's origin at the ground, merging runs into rectangles."""
    cv, pal = p.cv, p.pal
    size = max(2, round(4 * p.s))
    table = colors(pal)
    rows = {}
    for (x, y), ch in sprite.px.items():
        sx = x if p.f > 0 else -x - 1
        rows.setdefault(y, []).append((sx, table[ch]))
    for y, cells in rows.items():
        cells.sort()
        start, prev, color = cells[0][0], cells[0][0], cells[0][1]
        for x, c in cells[1:] + [(None, None)]:
            if x is not None and x == prev + 1 and c == color:
                prev = x
                continue
            cv.create_rectangle(p.ox + start * size, p.oy + y * size, p.ox + (prev + 1) * size,
                                p.oy + (y + 1) * size, fill=color, outline="")
            if x is not None:
                start, prev, color = x, x, c
    return size


# --- faces ---------------------------------------------------------------------------------

def _eye_points(kind, style, side):
    if kind == "open" and style == "content":
        kind = "closed"
    if kind == "open":
        if style == "big":
            return [(0, -1, "W"), (1, -1, "E"), (0, 0, "E"), (1, 0, "E"), (0, 1, "E"), (1, 1, "E")]
        return [(0, 0, "E"), (1, 0, "E"), (0, 1, "E"), (1, 1, "E")]
    if kind == "wide":
        return [(0, -1, "W"), (1, -1, "E"), (0, 0, "E"), (1, 0, "E"), (0, 1, "E"), (1, 1, "W"),
                (0, 2, "E"), (1, 2, "E")]
    if kind == "closed":
        return [(-1, 0, "O"), (0, 1, "O"), (1, 1, "O"), (2, 0, "O")]
    if kind == "happy":
        return [(-1, 1, "O"), (0, 0, "O"), (1, 0, "O"), (2, 1, "O")]
    if kind in ("sus", "smug"):
        return [(-1, 0, "O"), (0, 0, "O"), (1, 0, "O"), (2, 0, "O"), (0, 1, "E"), (1, 1, "E")]
    if kind == "angry":
        brow = [(-1, -2, "O"), (0, -2, "O"), (1, -1, "O"), (2, -1, "O")]
        if side > 0:
            brow = [(1 - dx, dy, ch) for dx, dy, ch in brow]
        return brow + [(0, 0, "E"), (1, 0, "E"), (0, 1, "E"), (1, 1, "E")]
    return []


MOUTHS = {
    "w": [(6, 10, "O"), (7, 11, "O"), (8, 10, "O"), (9, 10, "O"), (10, 11, "O"), (11, 10, "O")],
    "frown": [(7, 11, "O"), (8, 10, "O"), (9, 10, "O"), (10, 11, "O")],
    "yell": [(7, 10, "X"), (8, 10, "X"), (9, 10, "X"), (10, 10, "X"), (7, 11, "X"), (8, 11, "P"),
             (9, 11, "P"), (10, 11, "X"), (8, 12, "X"), (9, 12, "X")],
    "smug": [(7, 11, "O"), (8, 11, "O"), (9, 11, "O"), (10, 10, "O")],
    "o": [(8, 10, "X"), (9, 10, "X"), (8, 11, "X"), (9, 11, "X")],
}
MOUTHS["tongue"] = MOUTHS["w"] + [(8, 11, "P"), (9, 11, "P")]


def head(sp, x0, y0, pal, eyes="open", mouth="w", ears="up", angry=False, t=0.0, **_):
    shape = "back" if ears == "back" and pal["ears"] == "pointy" else pal["ears"]
    sp.blit(EARS[shape] + FACE, x0, y0)
    if pal["stripes"]:
        sp.put(x0, y0, [(6, 4, "D"), (6, 5, "D"), (8, 4, "D"), (9, 4, "D"), (11, 4, "D"), (11, 5, "D")])
    if pal["blush_on"] or angry:
        blush = "R" if angry else "B"
        sp.put(x0, y0, [(3, 10, blush), (4, 10, blush), (13, 10, blush), (14, 10, blush)])
    for side, (ex, ey) in ((-1, L_EYE), (1, R_EYE)):
        sp.put(x0 + ex, y0 + ey, _eye_points(eyes, pal["eye_style"], side))
    sp.put(x0, y0, [(8, 9, "N"), (9, 9, "N")])
    sp.put(x0, y0, MOUTHS.get(mouth, MOUTHS["w"]))
    if pal["whiskers"]:
        # Two lines on each cheek that poke just past the outline.
        sp.put(x0, y0, [(x, 9, "O") for x in (-1, 1, 2)] + [(x, 11, "O") for x in (-1, 0, 2)] +
               [(x, 9, "O") for x in (15, 16, 18)] + [(x, 11, "O") for x in (15, 17, 18)])
    if angry and int(t * 4) % 2 == 0:
        sp.blit(ANGER, x0 + 15, y0 - 2)


def _anchor(p, sp, head_x):
    """Where speech bubbles should point: above the head, in the pen's units."""
    size = max(2, round(4 * p.s))
    return (head_x + 9) * size / p.s, sp.top() * size / p.s - 4


# --- poses ---------------------------------------------------------------------------------

def sit(p, t, face=None, puff=False, paw=0.0, groom=False, tail_speed=2.2, tail_amp=6.0):
    pal = p.pal
    face = dict(face or {})
    sp = Sprite()
    frame = int(t * tail_speed / 1.6) % 2 if tail_amp else 0
    sp.blit(SIT_TAILS[frame], 7, -10)
    sp.blit(SIT_BODY, -9, -10)
    if pal["stripes"]:
        sp.put(0, 0, [(-7, -6, "D"), (-7, -5, "D"), (7, -6, "D"), (7, -5, "D")])
    if paw > 0.5:  # stomping: one front paw lifted
        sp.blit(["OkkO", "OOOO"], 1, -3)
        sp.put(0, 0, [(1, -1, "."), (2, -1, "."), (3, -1, "."), (4, -1, ".")])
        sp.px = {k: v for k, v in sp.px.items() if v != "."}
    head(sp, -9, -22, pal, t=t, **face)
    if groom:
        bob = int(t * 6) % 2
        sp.blit(GROOM_PAW, -9 + 10, -22 + 10 + bob)
    if puff:
        sp.puff(int(t * 8))
    render(p, sp)
    return _anchor(p, sp, -9)


def walk(p, t, phase, face=None, amp=1.0, crouch=0.0, wiggle=0.0, stretch=0.0):
    pal = p.pal
    face = dict(face or {"eyes": "open", "mouth": "w"})
    sp = Sprite()
    drop = 2 if crouch else 0
    wig = (int(t * 12) % 2) if wiggle else 0
    step = int(phase / 1.6) % 4 if amp else 1
    shifts = [(1, -1, -1, 1), (0, 0, 0, 0), (-1, 1, 1, -1), (0, 0, 0, 0)][step]
    if stretch:
        shifts = (-2, -2, 2, 2)
    for col, sh in zip((1, 4, 10, 13), shifts):
        x0 = col - 12 + (wig if col < 8 else 0)
        sp.blit(LEG[:3], x0, -5)
        sp.blit(LEG[3:], x0 + sh, -2)
    tail_frame = int(t * (6 if wiggle else 2)) % 2
    sp.blit(WALK_TAILS[tail_frame], -15 + wig, -13 + drop)
    sp.blit(WALK_BODY, -12 + wig, -10 + drop)
    if pal["stripes"]:
        sp.put(0, drop, [(-6, -9, "D"), (-6, -8, "D"), (-3, -9, "D"), (-3, -8, "D"), (0, -9, "D"), (0, -8, "D")])
    head(sp, -1, -20 + drop, pal, t=t, **face)
    render(p, sp)
    return _anchor(p, sp, -1)


def sleep(p, t):
    pal = p.pal
    sp = Sprite()
    breathe_in = int(t * 0.8) % 2
    rows = LOAF if not breathe_in else [LOAF[0], LOAF[1]] + LOAF[1:]
    sp.blit(rows, -12, -len(rows))
    if pal["stripes"]:
        sp.put(0, 0, [(-6, -6, "D"), (-6, -5, "D"), (-3, -6, "D"), (-3, -5, "D")])
    # Tail wrapped along the front.
    sp.put(0, 0, [(x, -3, "O") for x in range(-11, 1)] + [(x, -2, "F") for x in range(-11, -1)] +
           [(-1, -2, "t"), (0, -2, "t"), (1, -2, "O")])
    head(sp, -1, -14, pal, eyes="closed", mouth="w", t=t)
    render(p, sp)
    return _anchor(p, sp, -1)


def portrait(p):
    sp = Sprite()
    head(sp, -9, -14, p.pal)
    render(p, sp)


def heart(cv, x, y, size):
    n = max(1, round(size / 7))
    for r, row in enumerate(HEART):
        for c, ch in enumerate(row):
            if ch == "R":
                cv.create_rectangle(x + (c - 3.5) * n, y + (r - 3) * n, x + (c - 2.5) * n, y + (r - 2) * n,
                                    fill="#FF6B8B", outline="")
