"""Dev helper: renders every behaviour of the animated cat in a few looks (needs Pillow + display)."""
import os
import sys
import tkinter as tk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from focuscat import config, sprites  # noqa: E402
from focuscat import drawing as d  # noqa: E402

out = sys.argv[1] if len(sys.argv) > 1 else "sprites.png"
LOOKS = [{},
         {"fur_color": "#34343C", "second_color": "#F4F4F4", "eye_color": "#F2D15C", "ear_color": "#C98A9A",
          "ear_shape": "folded", "blush": True},
         {"fur_color": "#B8773A", "second_color": "#E3C08E", "eye_color": "#9BD37A", "stripes": True,
          "eye_style": "big"},
         {"fur_color": "#F0A35E", "second_color": "#FFFFFF", "pattern": "socks", "eye_color": "#9BD37A",
          "ear_shape": "folded", "eye_style": "big", "blush": True}]
ACTS = [("sit", 0), ("walk", 1), ("walk", -1), ("sleep", 1), ("groom", 1), ("play:crouch", 1),
        ("play:pounce", 1), ("sus", -1), ("angry", 1), ("happy", 1), ("smug", 1), ("eat", 1), ("zoomies", -1)]
S = float(os.environ.get("SCALE", "1.0"))
W, H = int(110 * S), int(120 * S)
root = tk.Tk()
cv = tk.Canvas(root, width=W * len(ACTS), height=H * len(LOOKS), bg="#2E7DB5", highlightthickness=0)
cv.pack()
for r, over in enumerate(LOOKS):
    look = d.make_look(config._clean(dict(config.DEFAULTS, **over)))
    for c, (act, facing) in enumerate(ACTS):
        p = d.Pen(cv, c * W + W / 2, (r + 1) * H - 10, S, facing or 1, look)
        step = None
        if act.startswith("play:"):
            act, step = act.split(":")
        sprites.draw_action(p, act, 0.4, 3.0 if act == "walk" else 0.0, step)
        if r == 0:
            cv.create_text(c * W + W / 2, 8, text=act + (":" + step if step else ""), fill="white")


def snap():
    from PIL import ImageGrab
    root.update()
    x, y = cv.winfo_rootx(), cv.winfo_rooty()
    ImageGrab.grab(bbox=(x, y, x + cv.winfo_width(), y + cv.winfo_height())).save(out)
    root.destroy()


root.after(500, snap)
root.mainloop()
