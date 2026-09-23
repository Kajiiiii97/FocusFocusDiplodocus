"""The desktop cat: a transparent always-on-top window that wanders along the taskbar."""

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
from focuscat import watcher as w
from focuscat.server import ReportServer

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


def log_error():
    try:
        os.makedirs(config.config_dir(), exist_ok=True)
        with open(os.path.join(config.config_dir(), "focuscat.log"), "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + traceback.format_exc() + "\n")
    except OSError:
        pass


class CatApp:
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

        dpi_scale = max(1.0, root.winfo_fpixels("1i") / 96.0) if winsys.IS_WIN else 1.0
        self.s = cfg["scale"] * dpi_scale
        self.W, self.H = int(BASE_W * self.s), int(BASE_H * self.s)
        self.cv = tk.Canvas(root, width=self.W, height=self.H, bg=KEY, highlightthickness=0, bd=0)
        self.cv.pack()
        self.font = ("Segoe UI", -int(13 * self.s), "bold")

        self._refresh_area()
        self.x = random.uniform(self.min_x, self.max_x)
        self.win_y = self.ground_y
        self.vy = 0.0
        self.hop = 0.0
        self.facing = random.choice((-1, 1))
        self.phase = 0.0
        self.moving = False
        self.t = 0.0
        self.dragging = self.falling = False
        self._press = None
        self.hearts = []
        self.ball = None
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
        self._last = time.monotonic()
        root.after(FRAME_MS, self._frame)
        root.after(3000, self._housekeeping)

    # --- lifecycle ------------------------------------------------------------------------

    def run(self):
        self.root.mainloop()
        return 1 if self.errors else 0

    def quit(self):
        try:
            self.server.stop()
        finally:
            self.root.destroy()

    def _callback_error(self, *exc):
        self.errors += 1
        log_error()
        if self.selftest:
            traceback.print_exception(*exc)

    def _refresh_area(self):
        left, top, right, bottom = winsys.work_area(self.root)
        self.min_x = left + self.W / 2
        self.max_x = max(self.min_x, right - self.W / 2)
        self.ground_y = bottom - self.H

    def _housekeeping(self):
        # Screens change and the taskbar likes to jump in front of topmost windows.
        self._refresh_area()
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
                "y": self.H - random.uniform(95, 115) * self.s,
                "size": random.uniform(10, 18) * self.s,
                "life": random.uniform(1.2, 2.0),
                "wob": random.uniform(0, 6),
            })

    # --- behaviour ------------------------------------------------------------------------

    def start(self, action, dur=None):
        if self.action == "play" and action != "play":
            self.ball = None
        self.action, self.action_t, self.action_dur = action, 0.0, dur
        self.hop = 0.0
        if action == "walk":
            span = self.max_x - self.min_x
            if span < 50 * self.s:
                self.target_x = self.x
            else:
                for _ in range(10):
                    self.target_x = random.uniform(self.min_x, self.max_x)
                    if abs(self.target_x - self.x) > min(140 * self.s, span / 3):
                        break
        elif action == "play":
            bx = self.x + self.facing * 95 * self.s
            if not self.min_x - 110 * self.s < bx < self.max_x + 110 * self.s:
                self.facing = -self.facing
                bx = self.x + self.facing * 95 * self.s
            self.ball = {"x": bx, "v": 0.0, "spin": 0.0}
            self.play_step, self.step_t, self.step_dur = "stalk", 0.0, 0.0
            self.pounces, self.pounce_goal = 0, random.randint(2, 4)

    def next_action(self):
        options = {"walk": 30, "sit": 18, "sleep": 16, "play": 16, "groom": 12}
        if self.action == "sleep":
            options.pop("sleep")
        if self.action == "play":
            options["play"] = 4
        pick = random.choices(list(options), weights=list(options.values()))[0]
        durations = {"sit": (3, 7), "sleep": (25, 70), "groom": (3.5, 6)}
        lo_hi = durations.get(pick)
        self.start(pick, random.uniform(*lo_hi) if lo_hi else None)

    def move_toward(self, tx, speed, dt):
        tx = min(max(tx, self.min_x), self.max_x)
        dist = tx - self.x
        if abs(dist) < 3 * self.s:
            return True
        self.facing = 1 if dist > 0 else -1
        step = min(abs(dist), speed * dt)
        self.x += self.facing * step
        self.phase += step / (4.5 * self.s)
        self.moving = True
        return abs(dist) <= step

    def pointer_x(self):
        try:
            return self.root.winfo_pointerx()
        except tk.TclError:
            return self.x

    def face_pointer(self):
        px = self.pointer_x()
        if abs(px - self.x) > 20 * self.s:
            self.facing = 1 if px > self.x else -1

    def react_to(self, st):
        """Watcher mood beats whatever the cat felt like doing."""
        if self.dragging or self.falling:
            return
        mood, a = st["mood"], self.action
        if mood in (w.MAD, w.CLOSING) and not (mood == w.CLOSING and a == "smug"):
            if a not in ("approach", "angry"):
                if a == "sleep":
                    self.say("!!", 1.2)
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
            if self.move_toward(self.target_x, 55 * s, dt):
                self.next_action()
        elif a == "play":
            self.update_play(dt)
        elif a == "sus":
            self.face_pointer()
        elif a == "approach":
            if self.move_toward(self.pointer_x(), 200 * s, dt):
                self.start("angry")
        elif a == "angry":
            self.face_pointer()
            if abs(self.pointer_x() - self.x) > 260 * s and self.min_x < self.pointer_x() < self.max_x:
                self.start("approach")
        elif self.action_dur is not None and self.action_t >= self.action_dur:
            if a == "smug" and st["mood"] == w.CALM:
                self.start("sleep", random.uniform(20, 40))
            else:
                self.next_action()

    def update_play(self, dt):
        s, b = self.s, self.ball
        b["x"] += b["v"] * dt
        b["spin"] += b["v"] * dt / (11 * s)
        b["v"] *= max(0.0, 1 - 2.8 * dt)
        edge_l, edge_r = self.min_x - self.W / 2 + 14 * s, self.max_x + self.W / 2 - 14 * s
        if not edge_l <= b["x"] <= edge_r:
            b["x"] = min(max(b["x"], edge_l), edge_r)
            b["v"] = -b["v"] * 0.5
        dx = b["x"] - self.x
        if abs(dx) > 125 * s:  # keep it inside the window
            b["x"] = self.x + math.copysign(125 * s, dx)
            b["v"] = 0.0
            dx = b["x"] - self.x

        self.step_t += dt
        side = 1 if dx >= 0 else -1
        if self.action_t > 30:
            self.start("sit", 3)
        elif self.play_step == "stalk":
            if abs(b["v"]) < 25 * s:
                if abs(dx) <= 80 * s or self.move_toward(b["x"] - side * 70 * s, 40 * s, dt):
                    self.facing = side
                    self.play_step, self.step_t = "crouch", 0.0
                    self.step_dur = random.uniform(0.7, 1.6)
        elif self.play_step == "crouch":
            self.facing = side
            if self.step_t >= self.step_dur:
                self.play_step, self.step_t = "pounce", 0.0
                self.jump = (self.x, min(max(b["x"] - side * 16 * s, self.min_x), self.max_x))
        elif self.play_step == "pounce":
            k = min(1.0, self.step_t / 0.42)
            self.x = self.jump[0] + (self.jump[1] - self.jump[0]) * k
            self.hop = math.sin(math.pi * k) * 34 * s
            if k >= 1:
                self.hop = 0.0
                b["v"] = self.facing * random.uniform(150, 260) * s
                if random.random() < 0.25:
                    b["v"] *= -0.6  # it squirts out the other way
                self.pounces += 1
                self.play_step = "stalk" if self.pounces < self.pounce_goal else "done"
                self.step_t = 0.0
        elif self.play_step == "done" and self.step_t > 1.2:
            self.start("sit", 3)
            if random.random() < 0.5:
                self.say("hehe", 1.5)

    def update_physics(self, dt):
        if self.falling:
            self.vy += 2400 * self.s * dt
            self.win_y += self.vy * dt
            if self.win_y >= self.ground_y:
                self.win_y, self.vy, self.falling = self.ground_y, 0.0, False
                self.start("sit", 2)
                self.say("mrrp!", 1.5)
        elif not self.dragging:
            self.win_y = self.ground_y
        self.win_y = min(self.win_y, self.ground_y)
        self.x = min(max(self.x, self.min_x), self.max_x)

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
            if not (self.dragging or self.falling):
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
        self.root.geometry(f"{self.W}x{self.H}+{int(self.x - self.W / 2)}+{int(self.win_y)}")

    # --- drawing --------------------------------------------------------------------------

    def render(self, st):
        cv, s, t = self.cv, self.s, self.t
        cv.delete("all")
        pal = d.PALETTES.get(self.cfg.get("palette"), d.PALETTES["orange"])
        a = self.action
        ox, oy = self.W / 2, self.H - 6 * s - self.hop
        if a == "angry":
            ox += math.sin(t * 40) * 1.5 * s
        p = d.Pen(cv, ox, oy, s, self.facing, pal)
        blink = (t % 4.3) < 0.13
        open_eyes = "closed" if blink else "open"
        head = (0, -64)  # where the bubble points

        if a in ("walk", "approach"):
            face = {"eyes": "angry", "mouth": "frown", "ears": "back", "angry": True} if a == "approach" \
                else {"eyes": open_eyes, "mouth": "w"}
            d.pose_walk(p, t, self.phase, face=face, amp=1.3 if a == "approach" else 1.0)
            head = (28, -50)
        elif a == "sleep":
            d.pose_sleep(p, t)
            d.zzz(cv, p.X(26), p.Y(-58), s, t, pal["line"])
            head = (22, -24)
        elif a == "groom":
            d.pose_sit(p, t, face={"eyes": "closed", "mouth": "tongue"}, groom=True)
        elif a == "play":
            face = {"eyes": "wide", "mouth": "o"}
            if self.play_step == "crouch":
                d.pose_walk(p, t, 0.0, face=face, amp=0.0, crouch=1.0, wiggle=1.0)
            elif self.play_step == "pounce":
                d.pose_walk(p, t, 0.0, face=face, amp=0.0, stretch=1.0)
            else:
                d.pose_walk(p, t, self.phase, face=face if self.moving else {"eyes": open_eyes, "mouth": "w"},
                            amp=1.0 if self.moving else 0.0)
            head = (28, -50)
        elif a == "sus":
            d.pose_sit(p, t, face={"eyes": "sus", "mouth": "frown", "look": 1.0}, tail_speed=1.2, tail_amp=3)
        elif a == "angry":
            yelling = (t % 1.6) < 0.9
            d.pose_sit(p, t, face={"eyes": "angry", "mouth": "yell" if yelling else "frown", "ears": "back",
                                   "angry": True},
                       puff=True, paw=max(0.0, math.sin(t * 7)), tail_speed=9, tail_amp=8)
        elif a == "happy":
            d.pose_sit(p, t, face={"eyes": "happy", "mouth": "w"}, tail_speed=6, tail_amp=8)
        elif a == "smug":
            d.pose_sit(p, t, face={"eyes": "smug", "mouth": "smug"}, tail_speed=1.5)
        elif a == "held":
            d.pose_sit(p, t, face={"eyes": "wide", "mouth": "o"}, tail_speed=10, tail_amp=5)
        else:
            look = (self.pointer_x() - self.x) / (250 * s) * self.facing
            d.pose_sit(p, t, face={"eyes": open_eyes, "mouth": "w", "look": max(-1.0, min(1.0, look))})

        if self.ball is not None:
            r = 11 * s
            d.yarn(cv, self.W / 2 + (self.ball["x"] - self.x), self.H - 6 * s - r, r, self.ball["spin"])

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
        self._press = (e.x_root, e.y_root, self.x, self.win_y)

    def _on_drag(self, e):
        if not self._press:
            return
        px, py, x0, y0 = self._press
        if not self.dragging and math.hypot(e.x_root - px, e.y_root - py) > 6:
            self.dragging, self.falling = True, False
            self.start("held")
        if self.dragging:
            self.x = x0 + (e.x_root - px)
            self.win_y = y0 + (e.y_root - py)

    def _on_release(self, e):
        self._press = None
        if self.dragging:
            self.dragging, self.falling, self.vy = False, True, 0.0
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
        else:
            m.add_command(label="Can't see Firefox yet (extension installed?)", state="disabled")
        if st["paused_for"] > 0:
            m.add_command(label=f"End break early ({math.ceil(st['paused_for'] / 60)} min left)",
                          command=self._end_break)
        else:
            m.add_command(label=f"Take a {self.cfg['break_minutes']} min break", command=self._take_break)
        m.add_command(label="Show me the angry cat (demo)", command=self._demo)
        m.add_separator()
        if winsys.IS_WIN:
            self._autostart = tk.BooleanVar(value=winsys.get_autostart())
            m.add_checkbutton(label="Start with Windows", variable=self._autostart,
                              command=lambda: self._set_autostart(self._autostart.get()))
        m.add_command(label="Edit settings…", command=lambda: winsys.open_file(config.config_path()))
        m.add_command(label="Reload settings", command=self._reload)
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

    def _reload(self):
        fresh = config.load()
        restart = fresh["port"] != self.cfg["port"] or fresh["scale"] != self.cfg["scale"]
        self.cfg.update(fresh)
        self.say("settings loaded" + (" (restart me for port/size)" if restart else " ♥"), 3)


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


def _selftest(app, server):
    result = {}
    seq = ["walk", "sleep", "groom", "play", "happy", "smug", "held", "sus", "sit"]

    def step(i=0):
        if i < len(seq):
            app.start(seq[i], 5)
            if seq[i] == "play":
                app.play_step = "crouch"
            app.root.after(400, step, i + 1)
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
