"""Toys and beds you can give the cat. Each one is a little pixel-art window of its own that you
can drag around (or throw, for the toys). Right-click one to put it away."""

import math
import tkinter as tk

from focuscat import sprites, winsys

OUTLINE = "#120E14"


# --- pixel art -----------------------------------------------------------------------------

def _rotate(grid):
    return ["".join(grid[len(grid) - 1 - r][c] for r in range(len(grid))) for c in range(len(grid[0]))]


YARN = ["...OOOOO...",
        "..OBBHBBO..",
        ".OBHDDBBBO.",
        "OBBDBBDBBBO",
        "OBDBBBBDBBO",
        "OBDBBHBBDBO",
        "OBBDBBBBDBO",
        "OBBBDDDDBBO",
        ".OBBBBBBBO.",
        "..OBBBBBO..",
        "...OOOOO..."]
YARN_FRAMES = [YARN, _rotate(YARN), _rotate(_rotate(YARN)), _rotate(_rotate(_rotate(YARN)))]

MOUSE = ["........OO......",
         ".......OPPO.....",
         ".....OOOOOOOO...",
         "....OGGGGGGGGO..",
         "...OGGGGGGGGEGO.",
         "TTTOGGGGGGGGGGPO",
         "....OGGGGGGGGGO.",
         ".....OOOOOOOOO.."]


def _post():
    w = 14
    rows = ["." + "O" * (w - 2) + ".", "O" + "C" * (w - 2) + "O", "O" + "c" * (w - 2) + "O",
            "." + "O" * (w - 2) + "."]
    for i in range(18):
        rows.append("....O" + ("RRRR" if i % 3 else "rrrr") + "O....")
    rows += ["." + "O" * (w - 2) + ".", "O" + "C" * (w - 2) + "O", "O" + "c" * (w - 2) + "O", "O" * w]
    return rows


POST = _post()


def _box():
    w = 42
    inner = w - 6
    back = ["OO" + "." * (w - 4) + "OO",
            "OKOO" + "." * (w - 8) + "OOKO",
            ".OKK" + "O" * (w - 8) + "KKO.",
            "..O" + "K" * inner + "O..",
            "..O" + "I" * inner + "O.."]
    front = ["..O" + "O" * inner + "O.."]
    for i in range(9):
        if i == 4:
            tape = (inner - 8) // 2
            front.append("..O" + "B" * tape + "T" * 8 + "B" * (inner - tape - 8) + "O..")
        else:
            front.append("..O" + "B" * inner + "O..")
    front += ["..O" + "D" * inner + "O..", "..O" + "O" * inner + "O.."]
    return back, front


BOX_BACK, BOX_FRONT = _box()

def _cushion(w=44):
    def row(pad, edge, fill, inner=None):
        mid = w - 2 * pad - 2 * len(edge)
        return "." * pad + edge + (inner or fill) * mid + edge[::-1] + "." * pad
    return [row(4, "OO", "O"), row(2, "OOC", "C"), row(1, "OCC", "H"), row(0, "OCC", "C"),
            row(0, "OCC", "C"), row(0, "ODC", "C"), row(1, "ODD", "C"), row(2, "OOD", "D"),
            row(4, "OO", "O")]


CUSHION = _cushion()

BOWL = [".....K.KK..KK.K....",
        "...KkKKkKKKkKKkK...",
        "..OOOOOOOOOOOOOOO..",
        ".OBBBBBBBBBBBBBBBO.",
        "OBBHHHHHHHHHHHHHBBO",
        ".OBBBBBBBBBBBBBBBO.",
        "..OBBBBBBBBBBBBBO..",
        "...OOOOOOOOOOOOO..."]
BOWL_EMPTY = ["." * 19, "." * 19, "..OOOOOOOOOOOOOOO..", ".OIIIIIIIIIIIIIIIO."] + BOWL[4:]

TREAT = ["...OOOOO..O",
         "..OYYYYYOOO",
         ".OYEYYYYYYO",
         "..OyyyyyOOO",
         "...OOOOO..O"]

LASER = ["..rrr..",
         ".rRRRr.",
         "rRWWWRr",
         "rRWWWRr",
         "rRWWWRr",
         ".rRRRr.",
         "..rrr.."]

COLORS = {
    "yarn": {"O": OUTLINE, "B": "#E0607E", "D": "#B23A5A", "H": "#F5A3B7"},
    "mouse": {"O": OUTLINE, "G": "#A7A7B3", "E": OUTLINE, "P": "#E48AA0", "T": "#E48AA0"},
    "post": {"O": OUTLINE, "C": "#8E7CC3", "c": "#6F5DA6", "R": "#D8B57A", "r": "#B48F55"},
    "box": {"O": "#5A3A1E", "K": "#B98A55", "I": "#6B4A2A", "B": "#D4A56A", "D": "#B98A55", "T": "#E9D3A8"},
    "cushion": {"O": "#7A3E55", "C": "#E7A0B6", "H": "#F6CBD8", "D": "#C07A93"},
    "food": {"O": "#6E2A22", "B": "#E86F5C", "H": "#F5A493", "I": "#8E3B30", "K": "#9A5B2E", "k": "#C47B45"},
    "treat": {"O": "#6B4214", "Y": "#F2B84B", "y": "#D9952E", "E": OUTLINE},
    "laser": {"R": "#FF2A2A", "r": "#FF8A8A", "W": "#FFE3E3"},
}

KINDS = {
    "yarn": {"label": "Yarn ball", "toy": True},
    "mouse": {"label": "Toy mouse", "toy": True},
    "post": {"label": "Scratching post"},
    "box": {"label": "Cardboard box", "home": True},
    "cushion": {"label": "Cushion", "home": True},
    "food": {"label": "Food bowl"},
    "treat": {"label": "Treat", "snack": True},
}

# How far into a bed the cat's feet sink, in art pixels: the box front hides the legs.
SINK = {"box": 2, "cushion": 5}


def grids(kind, frame=0, facing=1):
    if kind == "yarn":
        return [YARN_FRAMES[frame % 4]]
    if kind == "mouse":
        return [MOUSE if facing > 0 else [row[::-1] for row in MOUSE]]
    if kind == "post":
        return [POST]
    if kind == "box":
        return [BOX_BACK + BOX_FRONT]
    if kind == "food":
        return [BOWL if frame else BOWL_EMPTY]
    if kind == "treat":
        return [TREAT if facing > 0 else [row[::-1] for row in TREAT]]
    if kind == "laser":
        return [LASER]
    return [CUSHION]


def draw_art(cv, x, bottom, grid, kind, n):
    """Draw art with its bottom centre at (x, bottom)."""
    img = sprites.picture(grid, COLORS[kind], n)
    cv.create_image(x - len(grid[0]) * n / 2, bottom - len(grid) * n, image=img, anchor="nw")


# --- the item windows ----------------------------------------------------------------------

class Item:
    """One toy or bed on the screen. (x, y) is the bottom centre, where it touches the floor."""

    def __init__(self, app, kind, x, y):
        self.app, self.kind, self.x, self.y = app, kind, x, y
        self.vx = self.vy = 0.0
        self.spin = 0.0
        self.facing = 1
        self.shake = 0.0
        self.hidden = False
        self.alive = True
        self.full = True  # food bowls start filled
        self._press = None
        self._drawn = None
        self.win = tk.Toplevel(app.root)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        try:
            self.win.attributes("-transparentcolor", app.KEY)
        except tk.TclError:
            pass
        self.cv = tk.Canvas(self.win, bg=app.KEY, highlightthickness=0, bd=0)
        self.cv.pack()
        self.cv.bind("<ButtonPress-1>", self._on_press)
        self.cv.bind("<B1-Motion>", self._on_drag)
        self.cv.bind("<ButtonRelease-1>", self._on_release)
        self.cv.bind("<ButtonPress-3>", self._on_menu)
        self.refresh()
        self.win.update_idletasks()
        winsys.set_no_activate(self.win, True)

    @property
    def toy(self):
        return KINDS[self.kind].get("toy", False)

    @property
    def home(self):
        return KINDS[self.kind].get("home", False)

    def size(self):
        n = self.app.px
        grid = grids(self.kind)[0]
        return len(grid[0]) * n, len(grid) * n

    def contains(self, x, y, pad=10):
        w, h = self.size()
        return self.x - w / 2 - pad <= x <= self.x + w / 2 + pad and self.y - h - pad <= y <= self.y + pad

    # --- per frame ------------------------------------------------------------------------

    def update(self, dt):
        if self._press:
            return
        s = self.app.s
        if self.toy and (self.vx or self.vy):
            self.x += self.vx * dt
            self.y += self.vy * dt
            speed = math.hypot(self.vx, self.vy)
            self.spin += speed * dt / (9 * s)
            if abs(self.vx) > 5:
                self.facing = 1 if self.vx > 0 else -1
            keep = max(0.0, 1 - 2.4 * dt)
            self.vx *= keep
            self.vy *= keep
            if speed < 8 * s:
                self.vx = self.vy = 0.0
            self._bounce()
        if self.shake > 0:
            self.shake = max(0.0, self.shake - dt)
        self.refresh()

    def _bounce(self):
        left, top, right, bottom = self.app.area
        w, h = self.size()
        if self.x < left + w / 2:
            self.x, self.vx = left + w / 2, abs(self.vx) * 0.6
        if self.x > right - w / 2:
            self.x, self.vx = right - w / 2, -abs(self.vx) * 0.6
        if self.y < top + h:
            self.y, self.vy = top + h, abs(self.vy) * 0.6
        if self.y > bottom:
            self.y, self.vy = bottom, -abs(self.vy) * 0.6

    def refresh(self):
        if not self.alive:
            return
        frame = (1 if self.full else 0) if self.kind == "food" else int(self.spin) % 4
        n = self.app.px
        state = (frame, self.facing, n)
        w, h = self.size()
        if state != self._drawn:
            self._drawn = state
            self.cv.config(width=w, height=h)
            self.cv.delete("all")
            draw_art(self.cv, w / 2, h, grids(self.kind, frame, self.facing)[0], self.kind, n)
        jiggle = round(math.sin(self.shake * 60) * n) if self.shake else 0
        self.win.geometry(f"{w}x{h}+{int(self.x - w / 2 + jiggle)}+{int(self.y - h)}")

    def set_hidden(self, hidden):
        if hidden != self.hidden and self.alive:
            self.hidden = hidden
            (self.win.withdraw if hidden else self.win.deiconify)()

    def destroy(self):
        if self.alive:
            self.alive = False
            self.win.destroy()

    # --- mouse ----------------------------------------------------------------------------

    def _on_press(self, e):
        self._press = (e.x_root, e.y_root, self.x, self.y)
        self._track = [(self.app.t, e.x_root, e.y_root)]
        self.vx = self.vy = 0.0

    def _on_drag(self, e):
        if not self._press:
            return
        px, py, x0, y0 = self._press
        self.x, self.y = x0 + e.x_root - px, y0 + e.y_root - py
        self._track = (self._track + [(self.app.t, e.x_root, e.y_root)])[-5:]
        self.refresh()

    def _on_release(self, e):
        if not self._press:
            return
        self._press = None
        (t0, x0, y0), (t1, x1, y1) = self._track[0], (self.app.t, e.x_root, e.y_root)
        if self.kind == "food" and math.hypot(x1 - x0, y1 - y0) < 5:
            self.app.fill_bowl(self)  # a click (not a drag) on the bowl fills it up
            return
        thrown = False
        if self.toy and t1 - t0 > 0.01:
            vx, vy = (x1 - x0) / (t1 - t0), (y1 - y0) / (t1 - t0)
            if math.hypot(vx, vy) > 250 * self.app.s:
                self.vx, self.vy = vx * 0.7, vy * 0.7
                thrown = True
        self._bounce()
        self.app.item_dropped(self, thrown)

    def _on_menu(self, e):
        m = tk.Menu(self.win, tearoff=0)
        if self.kind == "food":
            m.add_command(label="Fill it up", command=lambda: self.app.fill_bowl(self))
        m.add_command(label=f"Put the {KINDS[self.kind]['label'].lower()} away",
                      command=lambda: self.app.remove_item(self))
        previous = winsys.foreground_window()
        winsys.set_no_activate(self.win, False)
        try:
            self.win.focus_force()
            m.tk_popup(e.x_root, e.y_root)
        finally:
            try:
                m.grab_release()
                winsys.set_no_activate(self.win, True)
            except tk.TclError:
                pass
            winsys.restore_foreground(previous)


class LaserDot:
    """The red dot. It sits on the mouse pointer and lets every click pass straight through."""

    def __init__(self, app):
        self.app = app
        n = app.px
        self.size = len(LASER) * n
        self.win = tk.Toplevel(app.root)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        try:
            self.win.attributes("-transparentcolor", app.KEY)
        except tk.TclError:
            pass
        self.cv = tk.Canvas(self.win, width=self.size, height=self.size, bg=app.KEY, highlightthickness=0, bd=0)
        self.cv.pack()
        draw_art(self.cv, self.size / 2, self.size, LASER, "laser", n)
        self.x, self.y = app.pointer()
        self.follow()
        self.win.update_idletasks()
        winsys.set_click_through(self.win)

    def follow(self):
        self.x, self.y = self.app.pointer()
        # Just below and right of the arrow's tip, so it doesn't hide what you're pointing at.
        self.win.geometry(f"{self.size}x{self.size}+{int(self.x + 6)}+{int(self.y + 6)}")
        self.x += 6 + self.size / 2
        self.y += 6 + self.size

    def destroy(self):
        self.win.destroy()
