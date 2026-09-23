"""The Settings window: pick how the cat looks (with a live preview) and tweak the rules."""

import math
import tkinter as tk
from tkinter import colorchooser, ttk

from focuscat import config
from focuscat import drawing as d

PREVIEWS = [("Chill", "sit"), ("Walk", "walk"), ("Nap", "sleep"), ("Mad", "angry"), ("Happy", "happy")]
EAR_LABELS = [("Pointy", "pointy"), ("Round", "round"), ("Folded", "folded")]
EYE_LABELS = [("Content", "content"), ("Dots", "dots"), ("Big & shiny", "big")]
STYLE_LABELS = [("Minimal", "minimal"), ("Outlined", "outlined")]
COLOR_ROWS = [("Fur", "fur_color"), ("Inner ears", "ear_color"), ("Eye color", "eye_color")]
LOOK_KEYS = ("style", "fur_color", "ear_color", "eye_color", "ear_shape", "eye_style", "stripes", "blush", "whiskers")


class SettingsWindow:
    def __init__(self, master, cfg, on_save, ui_scale=1.0):
        self.cfg, self.on_save, self.k = cfg, on_save, ui_scale
        self.draft = dict(cfg)
        self.t = 0.0

        top = self.top = tk.Toplevel(master)
        top.title(f"{cfg['cat_name']}'s settings")
        top.resizable(False, False)
        top.attributes("-topmost", True)
        top.protocol("WM_DELETE_WINDOW", self.close)
        top.bind("<Escape>", lambda e: self.close())

        outer = ttk.Frame(top, padding=12)
        outer.pack(fill="both", expand=True)

        # Left: live preview.
        left = ttk.Frame(outer)
        left.grid(row=0, column=0, sticky="n", padx=(0, 14))
        self.preview = tk.Canvas(left, width=int(230 * self.k), height=int(210 * self.k),
                                 bg="#2E7DB5", highlightthickness=0)
        self.preview.pack()
        self.mode = tk.StringVar(value="sit")
        modes = ttk.Frame(left)
        modes.pack(pady=(8, 0))
        for label, value in PREVIEWS:
            ttk.Radiobutton(modes, text=label, value=value, variable=self.mode).pack(side="left", padx=2)

        # Right: tabs.
        tabs = ttk.Notebook(outer)
        tabs.grid(row=0, column=1, sticky="nsew")
        tabs.add(self._look_tab(tabs), text="Look")
        tabs.add(self._rules_tab(tabs), text="Doomscroll rules")

        buttons = ttk.Frame(outer)
        buttons.grid(row=1, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(buttons, text="Reset look", command=self.reset_look).pack(side="left", padx=4)
        ttk.Button(buttons, text="Cancel", command=self.close).pack(side="left", padx=4)
        ttk.Button(buttons, text="Save", command=self.save).pack(side="left", padx=4)

        self._tick()
        top.lift()
        top.focus_force()

    # --- building the form ----------------------------------------------------------------

    def _look_tab(self, parent):
        f = ttk.Frame(parent, padding=10)
        row = 0

        ttk.Label(f, text="Name").grid(row=row, column=0, sticky="w")
        self.name = tk.StringVar(value=self.draft["cat_name"])
        ttk.Entry(f, textvariable=self.name, width=18).grid(row=row, column=1, columnspan=3, sticky="w", pady=2)
        row += 1

        ttk.Label(f, text="Quick picks").grid(row=row, column=0, sticky="nw", pady=(8, 0))
        picks = ttk.Frame(f)
        picks.grid(row=row, column=1, columnspan=3, sticky="w", pady=(8, 0))
        for i, (name, preset) in enumerate(d.PRESETS.items()):
            self._preset_button(picks, name, preset).grid(row=i // 4, column=i % 4, padx=2, pady=2)
        row += 1

        self.swatches = {}
        for label, key in COLOR_ROWS:
            ttk.Label(f, text=label).grid(row=row, column=0, sticky="w", pady=(6, 0))
            sw = tk.Canvas(f, width=int(54 * self.k), height=int(22 * self.k), highlightthickness=1,
                           highlightbackground="#999", cursor="hand2")
            sw.grid(row=row, column=1, sticky="w", pady=(6, 0))
            sw.bind("<Button-1>", lambda e, k=key, lbl=label: self.pick_color(k, lbl))
            self.swatches[key] = sw
            row += 1

        self.choice_vars = {}
        for label, key, options in (("Ear shape", "ear_shape", EAR_LABELS), ("Eye shape", "eye_style", EYE_LABELS),
                                    ("Style", "style", STYLE_LABELS)):
            ttk.Label(f, text=label).grid(row=row, column=0, sticky="w", pady=(8, 0))
            var = tk.StringVar(value=self.draft[key])
            var.trace_add("write", lambda *a, k=key, v=var: self.draft.__setitem__(k, v.get()))
            box = ttk.Frame(f)
            box.grid(row=row, column=1, columnspan=3, sticky="w", pady=(8, 0))
            for text, value in options:
                ttk.Radiobutton(box, text=text, value=value, variable=var).pack(side="left", padx=(0, 8))
            self.choice_vars[key] = var
            row += 1

        ttk.Label(f, text="Extras").grid(row=row, column=0, sticky="w", pady=(8, 0))
        box = ttk.Frame(f)
        box.grid(row=row, column=1, columnspan=3, sticky="w", pady=(8, 0))
        self.flag_vars = {}
        for text, key in (("Stripes", "stripes"), ("Blush", "blush"), ("Whiskers", "whiskers")):
            var = tk.BooleanVar(value=self.draft[key])
            var.trace_add("write", lambda *a, k=key, v=var: self.draft.__setitem__(k, v.get()))
            ttk.Checkbutton(box, text=text, variable=var).pack(side="left", padx=(0, 8))
            self.flag_vars[key] = var
        row += 1

        ttk.Label(f, text="Size").grid(row=row, column=0, sticky="w", pady=(8, 0))
        self.size = tk.DoubleVar(value=self.draft["scale"])
        self.size_label = ttk.Label(f, width=5)
        ttk.Scale(f, from_=0.6, to=2.0, variable=self.size, length=int(150 * self.k),
                  command=lambda v: self.size_label.config(text=f"{float(v):.1f}×")).grid(
            row=row, column=1, columnspan=2, sticky="w", pady=(8, 0))
        self.size_label.config(text=f"{self.size.get():.1f}×")
        self.size_label.grid(row=row, column=3, sticky="w", pady=(8, 0))

        self._refresh_swatches()
        return f

    def _preset_button(self, parent, name, preset):
        box = ttk.Frame(parent)
        size = int(42 * self.k)
        cv = tk.Canvas(box, width=size, height=size, bg="#2E7DB5", highlightthickness=0, cursor="hand2")
        cv.pack()
        look = d.make_look(dict(self.draft, fur_color=preset[0], ear_color=preset[1], eye_color=preset[2],
                                stripes=preset[3], style="minimal", eye_style="content"))
        d.portrait(d.Pen(cv, size / 2, size * 0.6, 0.62 * self.k, 1, look))
        label = ttk.Label(box, text=name, font=("Segoe UI", 8), cursor="hand2")
        label.pack()
        for w in (cv, box, label):
            w.bind("<Button-1>", lambda e: self.apply_preset(preset))
        return box

    def _rules_tab(self, parent):
        f = ttk.Frame(parent, padding=10)
        self.notice = tk.IntVar(value=int(self.draft["notice_after_seconds"]))
        self.close_min = tk.DoubleVar(value=round(self.draft["close_after_seconds"] / 60, 1))
        self.break_min = tk.IntVar(value=int(self.draft["break_minutes"]))
        rows = [
            ("Notice me after (seconds)", self.notice, 0, 600, 1),
            ("Close the tab after (minutes)", self.close_min, 0.5, 60, 0.5),
            ("Break length (minutes)", self.break_min, 1, 240, 1),
        ]
        for r, (label, var, lo, hi, inc) in enumerate(rows):
            ttk.Label(f, text=label).grid(row=r, column=0, sticky="w", pady=3)
            ttk.Spinbox(f, from_=lo, to=hi, increment=inc, textvariable=var, width=7).grid(
                row=r, column=1, sticky="w", padx=(8, 0))
        ttk.Label(f, text="Doomscroll sites (one per line, any part of the address)").grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(12, 3))
        self.sites = tk.Text(f, width=34, height=7, font=("Consolas", 9))
        self.sites.insert("1.0", "\n".join(self.draft["blocked"]))
        self.sites.grid(row=4, column=0, columnspan=2, sticky="w")
        return f

    # --- actions --------------------------------------------------------------------------

    def _refresh_swatches(self):
        for key, sw in self.swatches.items():
            sw.delete("all")
            sw.create_rectangle(0, 0, 200, 60, fill=self.draft[key], outline="")

    def _sync_widgets(self):
        for key, var in self.choice_vars.items():
            var.set(self.draft[key])
        for key, var in self.flag_vars.items():
            var.set(self.draft[key])
        self._refresh_swatches()

    def pick_color(self, key, label):
        _, hexcode = colorchooser.askcolor(self.draft[key], parent=self.top, title=label)
        if hexcode:
            self.draft[key] = hexcode.upper()
            self._refresh_swatches()

    def apply_preset(self, preset):
        self.draft.update(fur_color=preset[0], ear_color=preset[1], eye_color=preset[2], stripes=preset[3])
        self._sync_widgets()

    def reset_look(self):
        for key in LOOK_KEYS:
            self.draft[key] = config.DEFAULTS[key]
        self.size.set(config.DEFAULTS["scale"])
        self._sync_widgets()

    def _number(self, var, fallback):
        try:
            return float(var.get())
        except (tk.TclError, ValueError):
            return fallback

    def collect(self):
        out = dict(self.draft)
        out["cat_name"] = self.name.get().strip() or config.DEFAULTS["cat_name"]
        out["scale"] = round(self.size.get(), 2)
        out["notice_after_seconds"] = int(self._number(self.notice, self.cfg["notice_after_seconds"]))
        out["close_after_seconds"] = int(self._number(self.close_min, self.cfg["close_after_seconds"] / 60) * 60)
        out["break_minutes"] = int(self._number(self.break_min, self.cfg["break_minutes"]))
        out["blocked"] = [line.strip() for line in self.sites.get("1.0", "end").splitlines() if line.strip()]
        return config._clean(out)

    def save(self):
        self.on_save(self.collect())
        self.close()

    def close(self):
        try:
            self.top.destroy()
        except tk.TclError:
            pass

    def alive(self):
        try:
            return bool(self.top.winfo_exists())
        except tk.TclError:
            return False

    # --- preview --------------------------------------------------------------------------

    def _tick(self):
        if not self.alive():
            return
        self.t += 0.04
        self.draw_preview()
        self.top.after(40, self._tick)

    def draw_preview(self):
        cv, t, k = self.preview, self.t, self.k
        cv.delete("all")
        look = d.make_look(self.draft)
        s = k * 1.45
        w, h = int(cv["width"]), int(cv["height"])
        cv.create_line(12 * k, h - 22 * k, w - 12 * k, h - 22 * k, fill="#5B9BC8", width=max(1, round(2 * k)))
        p = d.Pen(cv, w / 2, h - 22 * k, s, 1, look)
        mode = self.mode.get()
        blink = (t % 3.7) < 0.13
        if mode == "walk":
            d.pose_walk(p, t, t * 9)
        elif mode == "sleep":
            d.pose_sleep(p, t)
            d.zzz(cv, p.X(26), p.Y(-58), s, t, look["line"])
        elif mode == "angry":
            yelling = (t % 1.6) < 0.9
            d.pose_sit(p, t, face={"eyes": "angry", "mouth": "yell" if yelling else "frown", "ears": "back",
                                   "angry": True}, puff=True, paw=max(0.0, math.sin(t * 7)),
                       tail_speed=9, tail_amp=8)
        elif mode == "happy":
            d.pose_sit(p, t, face={"eyes": "happy", "mouth": "w"}, tail_speed=6, tail_amp=8)
            d.heart(cv, w / 2 + 34 * s, h - 22 * k - 118 * s + math.sin(t * 3) * 4, 14 * s)
        else:
            d.pose_sit(p, t, face={"eyes": "closed" if blink else "open", "mouth": "w"})
