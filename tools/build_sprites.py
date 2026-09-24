"""Extracts the animations Focus Cat uses from assets/cat_template.aseprite into
focuscat/sprite_data.py.

The sheet is a grid of 64x64 cells; every row is one animation. Each pixel is stored as a
colour *role* (outline, fur, shadow, ...) so the app can recolour the cat to any look.

    python tools/build_sprites.py
"""
import base64
import json
import os
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import aseprite  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CELL = 64

# Colours of the gray template cat -> role letters.
ROLES = {
    (0x12, 0x0E, 0x14): "O",  # outline
    (0xBD, 0xB5, 0xC8): "F",  # fur
    (0x93, 0x8B, 0x9E): "S",  # fur shadow
    (0xE1, 0xDE, 0xE7): "L",  # light fur (chest, highlights): the second colour on two-tone cats
    # (c and d are fur and shadow on the face blaze, added below; f, s and l are paws.)
    (0x9A, 0x87, 0x7E): "P",  # inside of the ears
    (0xD3, 0xDF, 0xE1): "E",  # eyes
    (0xCA, 0x71, 0x9F): "M",  # mouth / tongue
    (0x19, 0x0F, 0x29): "N",  # inside of the mouth
}

# name: (sheet row, has feet on the ground so "socks" make sense)
ANIMS = {
    "sit": (19, True), "blink": (14, True), "sit_l": (21, True), "sit_r": (22, True),
    "stand": (16, True), "stand_l": (25, True), "stand_r": (26, True),
    "walk_l": (4, True), "walk_r": (5, True),
    "groom": (12, True), "scratch": (17, True),
    "sleep_l": (48, False), "sleep_r": (49, False), "loaf_l": (46, False), "loaf_r": (47, False),
    "pounce_l": (63, True), "pounce_r": (64, True),
    "hiss_l": (60, True), "hiss_r": (61, True),
    "happy": (65, True), "meow": (43, True),
    "run_l": (11, True), "run_r": (10, True),
    "eat_l": (32, True), "eat_r": (34, True),
}


def find_eyes(grid):
    """(left x, right x, y) of the eye pixels on the top eye row, or None if they're closed."""
    eyes = [(x, y) for y, line in enumerate(grid) for x, ch in enumerate(line) if ch == "E"]
    if not eyes:
        return None
    top = min(y for _, y in eyes)
    xs = [x for x, y in eyes if y <= top + 1]
    return min(xs), max(xs), top


def split_teeth(grid):
    """The sheet uses the eye colour for teeth too. Those become T, so they stay white whatever eye
    colour you pick."""
    rows = [list(line) for line in grid]
    mouth = {(x, y) for y, line in enumerate(grid) for x, ch in enumerate(line) if ch in "MN"}
    eyes = [(x, y) for y, line in enumerate(grid) for x, ch in enumerate(line) if ch == "E"]
    if not eyes:
        return grid
    top = min(y for _, y in eyes)
    for x, y in eyes:
        # Fangs sit below the eyes (hiss) or right against the open mouth (meow, where the eyes
        # are closed so the teeth are the only "eye" pixels left).
        touching = any((x + dx, y + dy) in mouth for dx in (-1, 0, 1) for dy in (-1, 0, 1))
        if y > top + 2 or touching:
            rows[y][x] = "T"
    return ["".join(r) for r in rows]


def blaze(grid, eyes, side):
    """Mark the tuxedo "curtain" on the face: fur pixels become lowercase-ish role letters
    (c = fur, d = shadow) that two-tone cats paint in their second colour. Only colours change;
    outlines, eyes and the silhouette stay exactly as drawn."""
    xl, xr, ey = eyes
    rows = [list(line) for line in grid]

    def inside(x, y):
        if side == 0:  # facing us: a point between the eyes widening over the muzzle and chest
            cx = (xl + xr) / 2
            if y < ey - 3:
                return False
            if y < ey:
                w = (y - (ey - 3)) * 0.5 + 0.5
            elif y <= ey + 2:
                w = (xr - xl) / 2 - 1.5
            elif y <= ey + 12:
                w = (xr - xl) / 2 + 1.5
            else:
                return False
            return abs(x - cx) <= w
        # Side view: the front of the face (toward where the cat looks), then chin and chest.
        front = (xl - x) if side < 0 else (x - xr)
        if y < ey - 2 or y > ey + 10:
            return False
        if y <= ey:
            return front >= 1
        if y <= ey + 3:
            return front >= -1
        return front >= -4

    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch in "FS" and inside(x, y):
                row[x] = "c" if ch == "F" else "d"
    return ["".join(r) for r in rows]


# Frames whose eyes are closed throughout (so there's nothing to find the face from) get the
# face blaze placed by hand, in the animation's cropped coordinates. The _l version is mirrored.
MANUAL_BLAZE = {
    "sleep_r": [(22, 11), (23, 11), (23, 10), (24, 10), (24, 9), (25, 8),
                (20, 12), (21, 12), (22, 12), (23, 12), (24, 12),
                (19, 13), (20, 13), (21, 13), (22, 13), (23, 13),
                (20, 14), (22, 14), (23, 14), (24, 14), (25, 14),
                (20, 15), (21, 15), (23, 15), (24, 15), (25, 15), (26, 15)],
}


def manual_blaze(grid, points):
    rows = [list(line) for line in grid]
    for x, y in points:
        if rows[y][x] in "FS":
            rows[y][x] = "c" if rows[y][x] == "F" else "d"
    return ["".join(r) for r in rows]


def cell(rows, r, c):
    return [row[c * CELL:(c + 1) * CELL] for row in rows[r * CELL:(r + 1) * CELL]]


def to_roles(px):
    out = []
    for row in px:
        line = ""
        for p in row:
            if p[3] < 128:
                line += "."
            else:
                role = ROLES.get(p[:3])
                if role is None:
                    raise SystemExit(f"unknown colour {p}")
                line += role
        out.append(line)
    return out


def main():
    doc = aseprite.read(os.path.join(ROOT, "assets", "cat_template.aseprite"))
    rows = aseprite.frame_rgba(doc, 0, ["Layer 1"])
    anims = {}
    for name, (r, feet) in ANIMS.items():
        frames = []
        for c in range(doc["width"] // CELL):
            grid = split_teeth(to_roles(cell(rows, r, c)))
            if sum(ch != "." for line in grid for ch in line) > 20:  # skip stray specks
                frames.append(grid)
        # One bounding box for the whole animation so frames don't jitter.
        ys = [y for f in frames for y, line in enumerate(f) if line.strip(".")]
        xs = [x for f in frames for line in f for x, ch in enumerate(line) if ch != "."]
        top, bottom, left, right = min(ys), max(ys), min(xs), max(xs)
        side = -1 if name.endswith("_l") else 1 if name.endswith("_r") else 0
        eyes = [find_eyes(f) for f in frames]
        cropped = []
        for i, f in enumerate(frames):
            # Closed eyes: borrow the eye position from the nearest frame that has them open.
            near = sorted(range(len(frames)), key=lambda j: abs(j - i))
            found = next((eyes[j] for j in near if eyes[j] and (side or eyes[j][1] - eyes[j][0] >= 4)), None)
            if found:
                # Two eyes showing means the head is turned toward us, whatever the body does.
                f = blaze(f, found, 0 if found[1] - found[0] >= 4 else side)
            g = [line[left:right + 1] for line in f[top:bottom + 1]]
            if name in MANUAL_BLAZE:
                g = manual_blaze(g, MANUAL_BLAZE[name])
            elif name.endswith("_l") and name[:-2] + "_r" in MANUAL_BLAZE:
                width = len(g[0])
                g = manual_blaze(g, [(width - 1 - x, y) for x, y in MANUAL_BLAZE[name[:-2] + "_r"]])
            if feet:
                # Lowercase fur in the bottom three rows = paws, for the "socks" pattern.
                low = max(i for i, line in enumerate(g) if line.strip("."))
                g = [line.translate(str.maketrans("FSLcd", "fslfs")) if i > low - 3 else line
                     for i, line in enumerate(g)]
            cropped.append(g)
        # Head position: middle of the top few rows of the first frame.
        first = cropped[0]
        first_row = next(i for i, line in enumerate(first) if line.strip("."))
        head_rows = [line for line in first[first_row:first_row + 6] if line.strip(".")]
        hx = [x for line in head_rows for x, ch in enumerate(line) if ch != "."]
        anims[name] = {
            "x0": left - CELL // 2,          # left edge relative to the cell centre
            "y0": top - (bottom + 1),        # top edge relative to the ground
            "head_x": left - CELL // 2 + (min(hx) + max(hx)) / 2,
            "frames": ["\n".join(g) for g in cropped],
        }
    blob = base64.b64encode(zlib.compress(json.dumps(anims).encode(), 9)).decode()
    lines = [blob[i:i + 96] for i in range(0, len(blob), 96)]
    with open(os.path.join(ROOT, "focuscat", "sprite_data.py"), "w") as f:
        f.write('"""Generated by tools/build_sprites.py from assets/cat_template.aseprite. Do not edit."""\n\n')
        f.write("DATA = (\n" + "".join(f'    "{line}"\n' for line in lines) + ")\n")
    print(f"{len(anims)} animations, {sum(len(a['frames']) for a in anims.values())} frames, "
          f"{len(blob) // 1024} KB")


if __name__ == "__main__":
    main()
