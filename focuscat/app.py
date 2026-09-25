"""The desktop cat: a transparent always-on-top window that wanders around the screen."""

import argparse
import json
import math
import os
import random
import sys
import threading
import time
import tkinter as tk
import traceback
import urllib.request
from tkinter import messagebox

from focuscat import config, winsys
from focuscat import drawing as d
from focuscat import sprites
from focuscat import watcher as w
from focuscat.items import BOX_BACK, BOX_FRONT, CUSHION, KINDS, SINK, Item, LaserDot, draw_art
from focuscat.server import ReportServer
from focuscat.settings_window import SettingsWindow

KEY = "#010102"  # this exact colour becomes see-through (and click-through) on Windows
BASE_W, BASE_H = 300, 250
FRAME_MS = 33

GOOD = ["good human ♥", "thank you. proud of u", "yay. back to the good stuff ♥", "that's my human"]
SUS = ["hm?", "...?", "is that shorts?", "what are we watching"]
MAD_LINES = [
    ["hey.", "HEY. that's shorts.", "we don't do shorts.", "put the scroll down."],
    ["i'm serious.", "don't make me do it.", "tail is swishing. that's bad."],
    ["i WILL close it.", "paw is on the X.", "ok. OK. last chance."],
]
CLOSED = ["closed it. you're welcome ♥", "gone. go drink some water", "bonk. tab's gone ♥"]
PETS = ["prrr ♥", "mrrp ♥", "purrrrr", "♥"]
NO_PETS = ["no pets. close it.", "don't try to bribe me.", "pets won't save u"]
NOMS = ["nom nom ♥", "*crunch crunch*", "delicious ♥", "more pls"]


def log_error():
    try:
        os.makedirs(config.config_dir(), exist_ok=True)
        with open(os.path.join(config.config_dir(), "focuscat.log"), "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + traceback.format_exc() + "\n")
    except OSError:
        pass


class CatApp:
    KEY = KEY

    def __init__(self, cfg, watcher, server, selftest=False):
        self.cfg, self.watcher, self.server, self.selftest = cfg, watcher, server, selftest
        self.errors = 0

        self.root = root = tk.Tk()
        root.title("Focus Cat")
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        try:
            root.attributes("-transparentcolor", KEY)
        except tk.TclError:
            pass  # not Windows: you'll see a dark box, which is fine for development
        root.report_callback_exception = self._callback_error

        self.dpi = max(1.0, root.winfo_fpixels("1i") / 96.0) if winsys.IS_WIN else 1.0
        self.cv = tk.Canvas(root, bg=KEY, highlightthickness=0, bd=0)
        self.cv.pack()
        self.look = d.make_look(cfg)
        self.settings_window = None
        self.t = 0.0
        self.items = []
        self.home = None  # the bed the cat lives in, if you've given it one
        self.in_home = False
        self._apply_scale()
        left, top, right, bottom = self.area
        self.x = random.uniform(self.min_x, self.max_x)
        self.y = random.uniform(max(self.min_y, bottom - 250 * self.s), self.max_y)
        self.hop = 0.0
        self.facing = random.choice((-1, 1))
        self.phase = 0.0
        self.moving = False
        self.dragging = False
        self._press = None
        self.hearts = []
        self.toy = None
        self.post = None
        self.target_item = None  # the bowl or treat it's heading for
        self.play_step = None
        self.hunger = 0.3  # 0 = full, 1 = starving; a bowl gets visited from about 0.6
        self.last_beg = -1e9
        self.laser = None
        self.laser_rest_until = 0.0
        self.bubble_text, self.bubble_until = None, 0.0
        self.demo_until = 0.0
        self.action = None
        self.start("sit", 3)

        self.cv.bind("<ButtonPress-1>", self._on_press)
        self.cv.bind("<B1-Motion>", self._on_drag)
        self.cv.bind("<ButtonRelease-1>", self._on_release)
        self.cv.bind("<ButtonPress-3>", self._on_menu)

        self._place()
        root.update_idletasks()
        winsys.set_no_activate(root, True)
        self._load_items()
        self._last = time.monotonic()
        root.after(FRAME_MS, self._frame)
        root.after(3000, self._housekeeping)

    # --- lifecycle ------------------------------------------------------------------------

    def run(self):
        self.root.mainloop()
        return 1 if self.errors else 0

    def quit(self):
        try:
            self._save_items()
            self.server.stop()
        finally:
            self.root.destroy()

    def _callback_error(self, *exc):
        self.errors += 1
        log_error()
        if self.selftest:
            traceback.print_exception(*exc)

    def _apply_scale(self):
        self.s = self.cfg["scale"] * self.dpi
        self.px = sprites.pixel_size(self.s)
        self.W, self.H = int(BASE_W * self.s), int(BASE_H * self.s)
        self.foot = self.H - 6 * self.s  # where the cat's feet are inside its window
        self.cv.config(width=self.W, height=self.H)
        self.font = ("Segoe UI", -int(13 * self.s), "bold")
        self._refresh_area()
        for item in self.items:
            item._drawn = None
            item.refresh()

    def _refresh_area(self):
        self.area = left, top, right, bottom = winsys.work_area(self.root)
        # (x, y) is where the cat's feet are. Keep the cat itself on screen; its speech bubble
        # may poke off the top edge.
        self.min_x, self.max_x = left + 25 * self.s, right - 25 * self.s
        self.min_y, self.max_y = top + 110 * self.s, bottom - 2 * self.s

    def _housekeeping(self):
        # Screens change and the taskbar likes to jump in front of topmost windows.
        self._refresh_area()
        for item in self.items:
            item.win.attributes("-topmost", True)
        self.root.attributes("-topmost", True)
        self.root.lift()
        self.root.after(3000, self._housekeeping)

    # --- speech & particles ---------------------------------------------------------------

    def say(self, text, seconds=3.0):
        self.bubble_text, self.bubble_until = text, self.t + seconds

    def burst_hearts(self, n=4):
        for _ in range(n):
            self.hearts.append({
                "x": self.W / 2 + random.uniform(-30, 30) * self.s,
                "y": self.foot - random.uniform(90, 110) * self.s,
                "size": random.uniform(10, 18) * self.s,
                "life": random.uniform(1.2, 2.0),
                "wob": random.uniform(0, 6),
            })

    # --- toys and beds --------------------------------------------------------------------

    def add_item(self, kind, x=None, y=None):
        if x is None:
            x = self.x + self.facing * 110 * self.s
            y = self.y
            if not self.min_x < x < self.max_x:
                x = self.x - self.facing * 110 * self.s
        item = Item(self, kind, min(max(x, self.min_x), self.max_x), min(max(y, self.min_y), self.max_y))
        self.items.append(item)
        self.root.lift()
        if item.home:
            self._leave_home()
            self.home = item
            if self.action not in ("approach", "angry"):
                self.say("ooh, is that for me?" if kind == "box" else "ooh, comfy", 2.5)
                self.next_action()
        elif item.toy and self.calm():
            self.say("!", 1.2)
            self.start("play", toy=item)
        elif kind == "treat":
            if self.calm():
                self._leave_home()
                self.say("!!", 1)
                self.start("snack", item=item)
            else:
                self.say("...a treat won't fix this.", 2.5)
        self._save_items()
        return item

    def fill_bowl(self, bowl):
        if not bowl.full:
            bowl.full = True
            bowl.refresh()
            if self.calm() and self.hunger > 0.6:
                self._leave_home()
                self.start("eat", item=bowl)
            else:
                self.say("ooh, food ♥", 2)
            self._save_items()

    def remove_item(self, item):
        if item is self.home:
            self._leave_home()
            self.home = next((i for i in reversed(self.items) if i.home and i is not item), None)
        if item is self.toy:
            self.toy = None
        if item is self.post:
            self.post = None
        if item is self.target_item:
            self.target_item = None
        if item in self.items:
            self.items.remove(item)
        item.destroy()
        if self.action in ("play", "scratch", "gohome", "eat", "snack", "beg") and not self.target_valid():
            self.start("sit", 2)
        self._save_items()

    def target_valid(self):
        a = self.action
        if a == "play":
            return self.toy is not None and self.toy.alive
        if a == "scratch":
            return self.post is not None and self.post.alive
        if a in ("eat", "snack", "beg"):
            return self.target_item is not None and self.target_item.alive
        if a == "gohome":
            return self.home is not None and self.home.alive
        return True

    def clear_items(self):
        for item in list(self.items):
            self.remove_item(item)

    def item_dropped(self, item, thrown):
        """You let go of an item after dragging it."""
        if item.toy and self.calm() and (thrown or math.hypot(item.x - self.x, item.y - self.y) < 250 * self.s):
            if self.in_home:
                self._leave_home()
            self.say("!", 1.2)
            self.start("play", toy=item)
        elif item.home and item is not self.home:
            self.home = item
        elif item.kind == "treat" and self.calm() and self.action != "snack":
            self._leave_home()
            self.start("snack", item=item)
        self._save_items()

    def calm(self):
        return not self.dragging and self.action not in ("approach", "angry", "sus", "smug")

    # --- laser pointer --------------------------------------------------------------------

    def toggle_laser(self, on=None):
        on = self.laser is None if on is None else on
        if on and self.laser is None:
            self.laser = LaserDot(self)
            if self.calm():
                self._leave_home()
                self.say("!!!", 1.2)
                self.start("laser")
        elif not on and self.laser is not None:
            self.laser.destroy()
            self.laser = None
            if self.action == "laser":
                self.start("sit", 3)
                self.say(random.choice(["where'd it go??", "...i almost had it", "it's gone :("]), 2.5)

    def _enter_home(self):
        if self.home and not self.in_home:
            self.in_home = True
            self.home.set_hidden(True)
            self.x, self.y = self.home.x, self.home.y

    def _leave_home(self):
        if self.in_home:
            self.in_home = False
            if self.home and self.home.alive:
                self.home.set_hidden(False)
                # Hop out in front of it so you can see both.
                self.y = min(self.home.y + 12 * self.s, self.max_y)

    def _items_path(self):
        return os.path.join(config.config_dir(), "items.json")

    def _save_items(self):
        if self.selftest:
            return
        data = [{"kind": i.kind, "x": round(i.x), "y": round(i.y), "full": i.full}
                for i in self.items if i.kind != "treat"]
        try:
            os.makedirs(config.config_dir(), exist_ok=True)
            with open(self._items_path(), "w", encoding="utf-8") as f:
                json.dump(data, f)
        except OSError:
            pass

    def _load_items(self):
        if self.selftest:
            return
        try:
            with open(self._items_path(), "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            return
        for entry in data if isinstance(data, list) else []:
            try:
                kind, x, y = entry["kind"], float(entry["x"]), float(entry["y"])
            except (KeyError, TypeError, ValueError):
                continue
            if kind in KINDS and kind != "treat":
                item = Item(self, kind, min(max(x, self.min_x), self.max_x), min(max(y, self.min_y), self.max_y))
                item.full = bool(entry.get("full", True))
                item.refresh()
                self.items.append(item)
                if item.home:
                    self.home = item
        self.root.lift()

    # --- behaviour ------------------------------------------------------------------------

    def start(self, action, dur=None, toy=None, item=None):
        self.action, self.action_t, self.action_dur = action, 0.0, dur
        self.hop = 0.0
        self.play_step = None
        if action in ("eat", "snack", "beg"):
            self.target_item = item
            self.play_step = "go"
        elif action == "zoomies":
            self.spots = [self._random_spot() for _ in range(random.randint(4, 7))]
            self.say(random.choice(["!!!", "brrrrr", "ZOOM"]), 1.2)
        elif action == "laser":
            self.play_step, self.step_t = "chase", 0.0
            self.laser_tired_at = self.t + random.uniform(35, 55)
        if action == "walk":
            self.target = self._random_spot()
        elif action == "play":
            self.toy = toy or self._nearest_toy()
            if self.toy is None:
                self.action = "sit"
                self.action_dur = 2
                return
            self.play_step, self.step_t, self.step_dur = "stalk", 0.0, 0.0
            self.pounces, self.pounce_goal = 0, random.randint(2, 4)
        elif action == "scratch":
            self.post = next((i for i in self.items if i.kind == "post"), None)
            self.play_step = "go"

    def _random_spot(self):
        best = (self.x, self.y)
        for _ in range(12):
            spot = (random.uniform(self.min_x, self.max_x), random.uniform(self.min_y, self.max_y))
            if math.hypot(spot[0] - self.x, spot[1] - self.y) > 160 * self.s:
                return spot
            best = spot
        return best

    def _nearest_toy(self):
        toys = [i for i in self.items if i.toy]
        return min(toys, key=lambda i: math.hypot(i.x - self.x, i.y - self.y)) if toys else None

    def next_action(self):
        if self.laser is not None and self.t >= self.laser_rest_until:
            self._leave_home()
            self.start("laser")
            return
        bowl = next((i for i in self.items if i.kind == "food"), None)
        if bowl and self.hunger > 0.6:
            if bowl.full:
                self._leave_home()
                self.start("eat", item=bowl)
                return
            if self.hunger > 0.85 and self.t - self.last_beg > 600:
                self.last_beg = self.t
                self._leave_home()
                self.start("beg", item=bowl)
                return
        has_toy = any(i.toy for i in self.items)
        has_post = any(i.kind == "post" for i in self.items)
        if self.home and not self.in_home:
            if self.home.alive:
                self.start("gohome")
                return
            self.home = None
        if self.in_home:
            # Living in the bed: mostly lounging, now and then popping out to play.
            options = {"sit": 30, "sleep": 45, "groom": 15}
            if has_toy:
                options["play"] = 6
            if has_post:
                options["scratch"] = 4
            options["zoomies"] = 2
            if self.home.kind == "cushion":
                options["sleep"] = 70
        else:
            options = {"walk": 30, "sit": 16, "sleep": 12, "groom": 12}
            if has_toy:
                options["play"] = 20
            if has_post:
                options["scratch"] = 10
            options["zoomies"] = 5
        if self.action == "sleep":
            options.pop("sleep", None)
        pick = random.choices(list(options), weights=list(options.values()))[0]
        if pick in ("play", "scratch", "zoomies"):
            self._leave_home()
        durations = {"sit": (3, 7), "sleep": (25, 70), "groom": (3.5, 6)}
        if self.in_home:
            durations = {"sit": (8, 20), "sleep": (40, 120), "groom": (4, 7)}
        lo_hi = durations.get(pick)
        self.start(pick, random.uniform(*lo_hi) if lo_hi else None)

    def move_toward(self, tx, ty, speed, dt):
        tx = min(max(tx, self.min_x), self.max_x)
        ty = min(max(ty, self.min_y), self.max_y)
        dx, dy = tx - self.x, ty - self.y
        dist = math.hypot(dx, dy)
        if dist < 3 * self.s:
            return True
        # Always face left or right, whichever way the walk leans.
        if abs(dx) > 2 * self.s:
            self.facing = 1 if dx > 0 else -1
        step = min(dist, speed * dt)
        self.x += dx / dist * step
        self.y += dy / dist * step
        self.phase += step / (4.5 * self.s)
        self.moving = True
        return dist <= step

    def pointer(self):
        try:
            return self.root.winfo_pointerx(), self.root.winfo_pointery()
        except tk.TclError:
            return self.x, self.y

    def face_pointer(self):
        px, _ = self.pointer()
        if abs(px - self.x) > 20 * self.s:
            self.facing = 1 if px > self.x else -1

    def _beside_pointer(self):
        """Where to stand to yell at you: next to the mouse, on the side the cat is already on."""
        px, py = self.pointer()
        side = 1 if self.x >= px else -1
        return px + side * 80 * self.s, py + 70 * self.s

    def react_to(self, st):
        """Watcher mood beats whatever the cat felt like doing."""
        if self.dragging:
            return
        mood, a = st["mood"], self.action
        if mood in (w.MAD, w.CLOSING) and not (mood == w.CLOSING and a == "smug"):
            if a not in ("approach", "angry"):
                if a == "sleep":
                    self.say("!!", 1.2)
                self._leave_home()
                self.start("approach")
        elif mood == w.SUSPICIOUS:
            if a not in ("sus", "approach", "angry"):
                self.start("sus")
                self.say(random.choice(SUS), 4)
        elif a in ("sus", "approach", "angry"):
            # Left in time, or Firefox went away. (A proper stop is handled by the event.)
            self.start("sit", 3)
            if a == "sus":
                self.say("mhm. good.", 2)

    def on_event(self, ev):
        if ev == "stopped":
            self.start("happy", 4)
            self.say(random.choice(GOOD), 4)
            self.burst_hearts(5)
        elif ev == "closed":
            self.start("smug", 5)
            self.say(random.choice(CLOSED), 5)

    def update_action(self, dt, st):
        a = self.action
        self.action_t += dt
        s = self.s
        if a == "walk":
            if self.move_toward(*self.target, 55 * s, dt):
                self.next_action()
        elif a == "gohome":
            if not (self.home and self.home.alive):
                self.home = None
                self.next_action()
            elif self.move_toward(self.home.x, self.home.y, 70 * s, dt):
                self._enter_home()
                self.next_action()
        elif a == "play":
            self.update_play(dt)
        elif a == "scratch":
            self.update_scratch(dt)
        elif a in ("eat", "snack", "beg"):
            self.update_food(dt)
        elif a == "zoomies":
            if self.move_toward(*self.spots[0], 380 * s, dt):
                self.spots.pop(0)
                if not self.spots:
                    self.start("sit", 4)
                    self.say(random.choice(["hff hff", "*pant pant*", "...what was that"]), 2)
        elif a == "laser":
            self.update_laser(dt)
        elif a == "sus":
            self.face_pointer()
        elif a == "approach":
            if self.move_toward(*self._beside_pointer(), 200 * s, dt):
                self.face_pointer()
                self.start("angry")
        elif a == "angry":
            self.face_pointer()
            tx, ty = self._beside_pointer()
            if math.hypot(tx - self.x, ty - self.y) > 240 * s:
                self.start("approach")
        elif self.action_dur is not None and self.action_t >= self.action_dur:
            if a == "smug" and st["mood"] == w.CALM:
                self.start("sleep", random.uniform(20, 40))
            else:
                self.next_action()

    def update_play(self, dt):
        s, toy = self.s, self.toy
        if toy is None or not toy.alive or self.action_t > 40:
            self.start("sit", 3)
            return
        self.step_t += dt
        dx = toy.x - self.x
        side = 1 if dx >= 0 else -1
        moving_toy = math.hypot(toy.vx, toy.vy) > 25 * s
        if self.play_step == "stalk":
            if not moving_toy:
                far = math.hypot(dx, toy.y - self.y) > 300 * s
                if self.move_toward(toy.x - side * 60 * s, toy.y, (150 if far else 60) * s, dt):
                    self.facing = side
                    self.play_step, self.step_t = "crouch", 0.0
                    self.step_dur = random.uniform(0.6, 1.4)
        elif self.play_step == "crouch":
            self.facing = side
            if self.step_t >= self.step_dur:
                self.play_step, self.step_t = "pounce", 0.0
                self.jump = (self.x, self.y, toy.x - side * 14 * s, toy.y)
        elif self.play_step == "pounce":
            k = min(1.0, self.step_t / 0.42)
            x0, y0, x1, y1 = self.jump
            self.x, self.y = x0 + (x1 - x0) * k, y0 + (y1 - y0) * k
            self.hop = math.sin(math.pi * k) * 34 * s
            if k >= 1:
                self.hop = 0.0
                toy.vx = self.facing * random.uniform(200, 340) * s
                toy.vy = random.uniform(-90, 90) * s
                if random.random() < 0.25:
                    toy.vx *= -0.6  # it squirts out the other way
                self.pounces += 1
                self.play_step = "stalk" if self.pounces < self.pounce_goal else "done"
                self.step_t = 0.0
        elif self.play_step == "done" and self.step_t > 1.2:
            self.start("sit", 3)
            if random.random() < 0.5:
                self.say("hehe", 1.5)

    def update_food(self, dt):
        item, a = self.target_item, self.action
        if item is None or not item.alive:
            self.start("sit", 2)
            return
        side = 1 if self.x < item.x else -1
        if self.play_step == "go":
            gap = 34 if item.kind == "food" else 24
            speed = 200 if a == "snack" else 80
            if self.move_toward(item.x - side * gap * self.s, item.y, speed * self.s, dt):
                self.facing = side
                self.play_step, self.action_t = "at", 0.0
                if a == "beg":
                    self.say(random.choice(["the bowl is empty...", "feed me? :(", "mrow. food?"]), 3)
                elif a == "eat" and not item.full:
                    self.say("oh. empty.", 2)
                    self.start("sit", 3)
        elif self.play_step == "at":
            if a == "beg":
                if self.action_t > 3.5:
                    self.start("sit", 5)
            elif self.action_t > (5.0 if a == "eat" else 2.5):
                self.say(random.choice(NOMS), 2)
                self.burst_hearts(3)
                if a == "eat":
                    item.full = False
                    item.refresh()
                    self.hunger = 0.0
                    self._save_items()
                else:
                    self.hunger = max(0.0, self.hunger - 0.3)
                    self.remove_item(item)
                if a == "snack" and random.random() < 0.35:
                    self.start("zoomies")  # sugar rush
                else:
                    self.start("happy", 2)

    def update_laser(self, dt):
        dot, s = self.laser, self.s
        if dot is None:
            self.start("sit", 2)
            return
        if self.t > self.laser_tired_at:
            # Out of breath. Flop down for a bit, then go again if the dot's still there.
            self.laser_rest_until = self.t + 10
            self.start("sleep", 8)
            self.say("*pant pant*", 2.5)
            return
        self.step_t += dt
        tx, ty = dot.x, dot.y
        if self.play_step == "chase":
            dist = math.hypot(tx - self.x, ty - self.y)
            if dist < 60 * s:
                self.facing = 1 if tx >= self.x else -1
                self.play_step, self.step_t = "pounce", 0.0
                self.jump = (self.x, self.y, tx, ty)
            else:
                self.move_toward(tx, ty, (300 if dist > 250 * s else 190) * s, dt)
        elif self.play_step == "pounce":
            k = min(1.0, self.step_t / 0.3)
            x0, y0, x1, y1 = self.jump
            self.x, self.y = x0 + (x1 - x0) * k, y0 + (y1 - y0) * k
            self.hop = math.sin(math.pi * k) * 26 * s
            if k >= 1:
                self.hop = 0.0
                self.play_step, self.step_t = "wait", 0.0
        elif self.play_step == "wait" and self.step_t > 0.25:
            self.play_step = "chase"

    def update_scratch(self, dt):
        post = self.post
        if post is None or not post.alive:
            self.start("sit", 2)
            return
        side = 1 if self.x < post.x else -1
        if self.play_step == "go":
            if self.move_toward(post.x - side * 26 * self.s, post.y, 70 * self.s, dt):
                self.facing = side
                self.play_step, self.action_t = "scratch", 0.0
                self.say(random.choice(["scritch scritch", "*scratch scratch*", "sharpening claws"]), 2.5)
        elif self.play_step == "scratch":
            post.shake = 0.15
            if self.action_t > 4.5:
                self.next_action()

    def update_physics(self, dt):
        self.hunger = min(1.0, self.hunger + dt / (20 * 60))
        if self.laser is not None:
            self.laser.follow()
        if not self.dragging:
            self.x = min(max(self.x, self.min_x), self.max_x)
            self.y = min(max(self.y, self.min_y), self.max_y)
        for item in self.items:
            item.update(dt)
        for h in self.hearts:
            h["y"] -= 30 * self.s * dt
            h["x"] += math.sin(self.t * 4 + h["wob"]) * 12 * self.s * dt
            h["life"] -= dt
        self.hearts = [h for h in self.hearts if h["life"] > 0]

    # --- frame loop -----------------------------------------------------------------------

    def _frame(self):
        now = time.monotonic()
        dt = min(now - self._last, 0.1)
        self._last = now
        self.t += dt
        try:
            self.watcher.tick()
            for ev in self.watcher.pop_events():
                self.on_event(ev)
            st = self.watcher.status()
            st = self._apply_demo(st)
            self.react_to(st)
            self.moving = False
            if not self.dragging:
                self.update_action(dt, st)
            self.update_physics(dt)
            self.render(st)
            self._place()
        except Exception:
            self.errors += 1
            log_error()
            if self.selftest:
                raise
        self.root.after(FRAME_MS, self._frame)

    def _apply_demo(self, st):
        if not self.demo_until:
            return st
        left = self.demo_until - self.t
        if left <= 0:
            self.demo_until = 0.0
            self.on_event("stopped")
            self.say("(that was just a demo) ♥", 3)
            return st
        # Race through all three anger levels in a few seconds.
        return dict(st, mood=w.MAD, remaining=st["total"] * left / 15.0)

    def _place(self):
        self.root.geometry(f"{self.W}x{self.H}+{int(self.x - self.W / 2)}+{int(self.y - self.foot)}")

    # --- drawing --------------------------------------------------------------------------

    def render(self, st):
        cv, s, t = self.cv, self.s, self.t
        cv.delete("all")
        pal = self.look
        a = self.action
        n = self.px
        ox, oy = self.W / 2, self.foot - self.hop
        if a == "angry":
            ox += math.sin(t * 40) * 1.5 * s
        # While the cat is in its bed, the bed is drawn here instead of in its own window, so the
        # cat can sit inside the box (back, cat, then the front on top) or lie on the cushion.
        bed = self.home.kind if self.in_home and self.home else None
        if bed == "box":
            draw_art(cv, ox, self.foot - len(BOX_FRONT) * n, BOX_BACK, "box", n)
            oy = self.foot - SINK["box"] * n
        elif bed == "cushion":
            draw_art(cv, ox, self.foot, CUSHION, "cushion", n)
            oy = self.foot - (len(CUSHION) - SINK["cushion"]) * n
        p = d.Pen(cv, ox, oy, s, self.facing, pal)
        pose = "happy" if (a == "scratch" and self.play_step == "scratch") else a
        if a in ("gohome", "scratch") and pose != "happy":
            pose = "walk"
        if a in ("eat", "snack", "beg"):
            if self.play_step == "go":
                pose = "zoomies" if a == "snack" else "walk"
            else:
                pose = {"eat": "eat", "snack": "eat", "beg": "beg"}[a]

        walking = self.moving or pose in ("walk", "approach", "zoomies")
        head = sprites.draw_action(p, pose, t, self.phase if walking else 0.0, self.play_step)
        if pose == "sleep":
            d.zzz(cv, p.X(head[0]), p.Y(head[1] - 30), s, t, "#3A3340")
        if pose in ("angry", "approach") and int(t * 4) % 2 == 0:
            sprites.anger_mark(cv, p.X(head[0] + 14 * p.f), p.Y(head[1] - 40), n)

        if bed == "box":
            draw_art(cv, ox, self.foot, BOX_FRONT, "box", n)

        for h in self.hearts:
            d.heart(cv, h["x"], h["y"], h["size"] * min(1.0, h["life"] * 1.5))

        text = None
        if a == "angry":
            text = self._mad_text(st)
        elif self.bubble_text and self.t < self.bubble_until:
            text = self.bubble_text
        if text:
            d.bubble(cv, p.X(head[0]), p.Y(head[1] - 46), text, s, self.font, 0, self.W)

    def _mad_text(self, st):
        if st["mood"] == w.CLOSING:
            return "that's it. closing it."
        rem = st["remaining"] or 0.0
        frac = rem / max(st["total"], 1.0)
        lines = MAD_LINES[0 if frac > 0.66 else 1 if frac > 0.33 else 2]
        line = lines[int(self.t / 6) % len(lines)]
        secs = int(math.ceil(rem))
        return f"{line}\nclosing it in {secs // 60}:{secs % 60:02d}"

    # --- mouse ----------------------------------------------------------------------------

    def _on_press(self, e):
        self._press = (e.x_root, e.y_root, self.x, self.y)

    def _on_drag(self, e):
        if not self._press:
            return
        px, py, x0, y0 = self._press
        if not self.dragging and math.hypot(e.x_root - px, e.y_root - py) > 6:
            self.dragging = True
            self._leave_home()
            self.start("held")
        if self.dragging:
            self.x = x0 + (e.x_root - px)
            self.y = y0 + (e.y_root - py)

    def _on_release(self, e):
        self._press = None
        if self.dragging:
            self.dragging = False
            self.x = min(max(self.x, self.min_x), self.max_x)
            self.y = min(max(self.y, self.min_y), self.max_y)
            bed = next((i for i in self.items if i.home and i.contains(self.x, self.y, 20 * self.s)), None)
            if bed:
                self.home = bed
                self._enter_home()
                self.say("mine now.", 2)
                self.start("sit", 6)
            else:
                self.start("sit", 2)
                self.say("mrrp!", 1.5)
            return
        self.pet()

    def pet(self):
        mood = self.watcher.status()["mood"]
        if self.action in ("approach", "angry") or mood in (w.MAD, w.CLOSING):
            self.say(random.choice(NO_PETS), 2.5)
        elif self.action == "sleep":
            self.start("sit", 4)
            self.say("mrrp..?", 2)
        elif self.action != "sus":
            self.start("happy", 2.5)
            self.say(random.choice(PETS), 2)
            self.burst_hearts(3)

    def _on_menu(self, e):
        st = self.watcher.status()
        name = self.cfg["cat_name"]
        m = tk.Menu(self.root, tearoff=0)
        if st["connected"]:
            m.add_command(label=f"{name} can see Firefox ✓", state="disabled")
            host = w.normalize(st["url"]).split("/")[0]
            if host:
                m.add_command(label=f"Looking at: {host}", state="disabled")
        else:
            m.add_command(label="Can't see Firefox yet (extension installed?)", state="disabled")
        if st["paused_for"] > 0:
            m.add_command(label=f"End break early ({math.ceil(st['paused_for'] / 60)} min left)",
                          command=self._end_break)
        else:
            m.add_command(label=f"Take a {self.cfg['break_minutes']} min break", command=self._take_break)
        m.add_command(label="Show me the angry cat (demo)", command=self._demo)
        m.add_separator()
        toys = tk.Menu(m, tearoff=0)
        for kind in ("yarn", "mouse", "post"):
            toys.add_command(label=KINDS[kind]["label"], command=lambda k=kind: self.add_item(k))
        m.add_cascade(label="Give a toy", menu=toys)
        beds = tk.Menu(m, tearoff=0)
        for kind in ("box", "cushion"):
            beds.add_command(label=KINDS[kind]["label"], command=lambda k=kind: self.add_item(k))
        m.add_cascade(label="Give a bed (it'll stay there)", menu=beds)
        food = tk.Menu(m, tearoff=0)
        food.add_command(label="A treat", command=lambda: self.add_item("treat"))
        food.add_command(label="A food bowl", command=lambda: self.add_item("food"))
        m.add_cascade(label="Feed", menu=food)
        self._laser_var = tk.BooleanVar(value=self.laser is not None)
        m.add_checkbutton(label="Laser pointer (on your mouse)", variable=self._laser_var,
                          command=lambda: self.toggle_laser(self._laser_var.get()))
        if self.items:
            m.add_command(label="Put all toys, beds and food away", command=self.clear_items)
        m.add_separator()
        if winsys.IS_WIN:
            self._autostart = tk.BooleanVar(value=winsys.get_autostart())
            m.add_checkbutton(label="Start with Windows", variable=self._autostart,
                              command=lambda: self._set_autostart(self._autostart.get()))
        m.add_command(label="Settings…", command=self.open_settings)
        m.add_separator()
        m.add_command(label=f"Quit (bye {name})", command=self.quit)
        # The menu needs a focusable window to close properly when you click elsewhere.
        winsys.set_no_activate(self.root, False)
        try:
            self.root.focus_force()
            m.tk_popup(e.x_root, e.y_root)
        finally:
            try:
                m.grab_release()
                winsys.set_no_activate(self.root, True)
            except tk.TclError:
                pass  # "Quit" was picked and the window is gone

    def _take_break(self):
        mins = self.cfg["break_minutes"]
        self.watcher.pause(mins * 60)
        self.start("sleep", mins * 60)
        self.say(f"ok. {mins} min. i'm timing you.", 3)

    def _end_break(self):
        self.watcher.resume()
        self.start("sit", 3)
        self.say("back to it!", 2)

    def _demo(self):
        self.demo_until = self.t + 15

    def _set_autostart(self, enabled):
        try:
            winsys.set_autostart(enabled)
            self.say("i'll be here when you log in ♥" if enabled else "ok, i won't auto-start", 2.5)
        except OSError:
            log_error()
            self.say("couldn't change that :(", 2.5)

    def open_settings(self):
        if self.settings_window and self.settings_window.alive():
            self.settings_window.top.lift()
            return
        self.settings_window = SettingsWindow(self.root, self.cfg, self.apply_settings, ui_scale=self.dpi)

    def apply_settings(self, new):
        rescale = new["scale"] != self.cfg["scale"]
        self.cfg.update(new)
        if not self.selftest:
            config.save(self.cfg)
        self.look = d.make_look(self.cfg)
        if rescale:
            self._apply_scale()
        self.start("happy", 2.5)
        self.say("ooh, new look ♥", 2.5)


def run_selftest_client(port, result):
    """Pretend to be the extension: sit on a Shorts tab until the cat closes it."""
    body = json.dumps({"url": "https://www.youtube.com/shorts/abc", "tabId": 123, "focused": True}).encode()
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/report", data=body, method="POST",
                                     headers={"Content-Type": "application/json", "X-Focus-Cat": "1"})
        try:
            with urllib.request.urlopen(req, timeout=3) as res:
                if json.load(res).get("close") == 123:
                    result["closed"] = True
                    return
        except OSError as exc:
            result["error"] = repr(exc)
        time.sleep(0.3)


def main(argv=None):
    parser = argparse.ArgumentParser(description="A desktop cat that hates doomscrolling.")
    parser.add_argument("--selftest", action="store_true", help="run every animation and the close flow, then exit")
    args = parser.parse_args(argv)

    winsys.enable_dpi_awareness()
    if args.selftest:
        cfg = dict(config.DEFAULTS, notice_after_seconds=0.5, close_after_seconds=2.0, port=0)
    else:
        cfg = config.load()
    watcher = w.FocusWatcher(cfg)
    try:
        server = ReportServer(watcher, cfg["port"]).start()
    except OSError:
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo("Focus Cat", f"{cfg['cat_name']} is already running "
                                         f"(or port {cfg['port']} is taken by something else).")
        root.destroy()
        return 1

    app = CatApp(cfg, watcher, server, selftest=args.selftest)
    if args.selftest:
        return _selftest(app, server)
    return app.run()


def settings_previews():
    from focuscat.settings_window import PREVIEWS
    return PREVIEWS


def _selftest(app, server):
    result = {}
    seq = ["walk", "sleep", "groom", "play", "happy", "smug", "held", "sus", "sit"]

    def step(i=0):
        if i < len(seq):
            app.start(seq[i], 5)
            if seq[i] == "play":
                app.play_step = "crouch"
            app.root.after(400, step, i + 1)
        elif i == len(seq):
            app.open_settings()
            win = app.settings_window
            win.apply_preset(d.PRESETS["Tuxedo"])
            win.choice_vars["ear_shape"].set("folded")
            win.choice_vars["eye_style"].set("big")
            win.size.set(1.3)
            for _, mode in settings_previews():
                win.mode.set(mode)
                win.draw_preview()
            win.save()
            assert app.cfg["fur_color"] == d.PRESETS["Tuxedo"][0] and app.cfg["ear_shape"] == "folded"
            assert app.W == int(300 * 1.3 * app.dpi)
            app.root.after(400, step, i + 1)
        elif i == len(seq) + 1:
            # Toys: play with a thrown yarn ball, then a toy mouse and the scratching post.
            yarn = app.add_item("yarn")
            yarn.vx, yarn.vy = 300.0, 80.0
            app.item_dropped(yarn, True)
            app.add_item("mouse")
            app.add_item("post")
            app.root.after(2500, step, i + 1)
        elif i == len(seq) + 2:
            assert app.action == "play", app.action
            app.start("scratch")
            app.root.after(1500, step, i + 1)
        elif i == len(seq) + 3:
            # Beds: the box becomes home; drawing the cat inside it and on the cushion.
            box = app.add_item("box")
            app._enter_home()
            assert app.in_home and box.hidden
            for pose in ("sit", "sleep", "groom"):
                app.start(pose, 5)
                app.render(app.watcher.status())
            cushion = app.add_item("cushion")
            assert app.home is cushion and not app.in_home
            app._enter_home()
            app.render(app.watcher.status())
            app.clear_items()
            assert not app.items and app.home is None
            # Food: a full bowl gets eaten from when hungry, a treat gets gobbled.
            bowl = app.add_item("food")
            app.hunger = 0.9
            app.next_action()
            assert app.action == "eat", app.action
            app.add_item("treat")
            assert app.action == "snack", app.action
            app.root.after(3500, step, i + 1)
        elif i == len(seq) + 4:
            assert not any(it.kind == "treat" for it in app.items), "treat should be eaten"
            app.start("zoomies")
            app.toggle_laser(True)
            assert app.action == "laser"
            app.root.after(1500, step, i + 1)
        elif i == len(seq) + 5:
            app.toggle_laser(False)
            assert app.laser is None and app.action != "laser"
            app.start("zoomies")
            app.root.after(800, step, i + 1)
        elif i == len(seq) + 6:
            app.clear_items()
            app.root.after(300, step, i + 1)
        else:
            app._demo()
            threading.Thread(target=run_selftest_client, args=(server.port, result), daemon=True).start()
            app.root.after(9000, finish)

    def finish():
        app.quit()

    app.root.after(300, step)
    code = app.run()
    ok = code == 0 and result.get("closed")
    if sys.stdout:
        print("selftest", "passed" if ok else f"FAILED (errors={app.errors}, result={result})")
    return 0 if ok else 1
