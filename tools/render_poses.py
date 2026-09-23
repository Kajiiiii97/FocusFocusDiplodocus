"""Dev helper: draws every pose side by side and saves a PNG (needs Pillow and a display).

    python tools/render_poses.py out.png [key=value ...]   e.g. ear_shape=round eye_style=big
"""
import os
import sys
import tkinter as tk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from focuscat import config  # noqa: E402
from focuscat import drawing as d  # noqa: E402

out = sys.argv[1] if len(sys.argv) > 1 else "poses.png"
overrides = dict(arg.split("=", 1) for arg in sys.argv[2:])
for key, value in overrides.items():
    if isinstance(config.DEFAULTS.get(key), bool):
        overrides[key] = value.lower() in ("1", "true", "yes")
cfg = config._clean(dict(config.DEFAULTS, **overrides))
S = 1.4
root = tk.Tk()
cv = tk.Canvas(root, width=1050, height=int(430 * S / 1.4), bg="#2E7DB5", highlightthickness=0)
cv.pack()
pal = d.make_look(cfg)
font = ("Segoe UI", -int(13 * S), "bold")


def pen(x, y, f=1):
    return d.Pen(cv, x, y, S, f, pal)


row = 190
d.pose_sit(pen(80, row), 0.3, face={"eyes": "open", "mouth": "w"})
d.pose_walk(pen(230, row), 0.3, 0.9)
d.pose_sleep(pen(390, row), 1.0)
d.zzz(cv, 420, row - 60, S, 1.0, pal["line"])
d.pose_sit(pen(540, row), 0.5, face={"eyes": "closed", "mouth": "tongue"}, groom=True)
d.pose_walk(pen(690, row), 0.5, 0.0, face={"eyes": "wide", "mouth": "o"}, crouch=1.0, wiggle=1.0, amp=0.0)
d.yarn(cv, 800, row - 12, 12, 0.5)
d.pose_walk(pen(930, row - 30), 0.5, 0.0, face={"eyes": "wide", "mouth": "o"}, stretch=1.0, amp=0)
row2 = 410
d.pose_sit(pen(80, row2), 0.2, face={"eyes": "sus", "mouth": "frown", "look": 1.0})
d.bubble(cv, 80, row2 - 150, "hm?", S, font, 0, 400)
d.pose_sit(pen(300, row2), 0.2, face={"eyes": "angry", "mouth": "yell", "ears": "back", "angry": True}, puff=True, paw=1.0)
d.bubble(cv, 300, row2 - 150, "HEY. that's shorts.\nclosing it in 4:32", S, font, 0, 800)
d.pose_sit(pen(560, row2), 0.2, face={"eyes": "happy", "mouth": "w"})
d.heart(cv, 600, row2 - 150, 18)
d.heart(cv, 530, row2 - 170, 12)
d.pose_sit(pen(760, row2), 0.2, face={"eyes": "smug", "mouth": "smug"})
d.bubble(cv, 760, row2 - 150, "closed it. you're welcome", S, font, 600, 1100)
d.pose_sit(pen(960, row2), 0.2, face={"eyes": "wide", "mouth": "o"})


def snap():
    from PIL import ImageGrab
    root.update()
    x, y = cv.winfo_rootx(), cv.winfo_rooty()
    ImageGrab.grab(bbox=(x, y, x + cv.winfo_width(), y + cv.winfo_height())).save(out)
    root.destroy()


root.after(500, snap)
root.mainloop()
