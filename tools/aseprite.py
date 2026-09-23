"""Minimal .aseprite reader: frames, layers, cels, tags and palette. Enough to export sprites."""
import struct
import zlib


def _string(buf, off):
    (n,) = struct.unpack_from("<H", buf, off)
    return buf[off + 2:off + 2 + n].decode("utf-8", "replace"), off + 2 + n


def read(path):
    data = open(path, "rb").read()
    (size, magic, nframes, w, h, depth, flags, _speed, _a, _b, transp, _pad1, _pad2, _pad3, ncolors,
     pw, ph) = struct.unpack_from("<IHHHHHIHIIB3sBBHBB", data, 0)[:17] if False else (None,) * 17
    size, magic, nframes, w, h, depth = struct.unpack_from("<IHHHHH", data, 0)
    assert magic == 0xA5E0, "not an aseprite file"
    transparent_index = data[28]
    doc = {"width": w, "height": h, "depth": depth, "transparent": transparent_index,
           "frames": [], "layers": [], "tags": [], "palette": {}}
    off = 128
    for fi in range(nframes):
        fbytes, fmagic, old_chunks, duration = struct.unpack_from("<IHHH", data, off)
        assert fmagic == 0xF1FA
        (new_chunks,) = struct.unpack_from("<I", data, off + 12)
        nchunks = new_chunks or old_chunks
        frame = {"duration": duration, "cels": []}
        coff = off + 16
        for _ in range(nchunks):
            csize, ctype = struct.unpack_from("<IH", data, coff)
            body = coff + 6
            if ctype == 0x2004:  # layer
                lflags, ltype, level, _, _, blend, opacity = struct.unpack_from("<HHHHHHB", data, body)
                name, _ = _string(data, body + 16)
                doc["layers"].append({"name": name, "flags": lflags, "type": ltype, "level": level,
                                      "opacity": opacity, "visible": bool(lflags & 1)})
            elif ctype == 0x2005:  # cel
                layer, x, y, opacity, ctype2, z = struct.unpack_from("<HhhBHh", data, body)
                p = body + 16
                cel = {"layer": layer, "x": x, "y": y, "opacity": opacity, "type": ctype2}
                if ctype2 == 1:
                    (cel["link"],) = struct.unpack_from("<H", data, p)
                elif ctype2 in (0, 2):
                    cw, ch = struct.unpack_from("<HH", data, p)
                    raw = data[p + 4:coff + csize]
                    if ctype2 == 2:
                        raw = zlib.decompress(raw)
                    cel.update(w=cw, h=ch, pixels=raw)
                frame["cels"].append(cel)
            elif ctype == 0x2018:  # tags
                (n,) = struct.unpack_from("<H", data, body)
                p = body + 10
                for _ in range(n):
                    frm, to, direction = struct.unpack_from("<HHB", data, p)
                    name, p = _string(data, p + 17)
                    doc["tags"].append({"name": name, "from": frm, "to": to, "dir": direction})
            elif ctype == 0x2019:  # palette
                psize, first, last = struct.unpack_from("<III", data, body)
                p = body + 20
                for i in range(first, last + 1):
                    (eflags,) = struct.unpack_from("<H", data, p)
                    r, g, b, a = data[p + 2:p + 6]
                    p += 6
                    if eflags & 1:
                        _, p = _string(data, p)
                    doc["palette"][i] = (r, g, b, a)
            coff += csize
        doc["frames"].append(frame)
        off += fbytes
    # Resolve linked cels.
    for frame in doc["frames"]:
        for i, cel in enumerate(frame["cels"]):
            if cel["type"] == 1:
                src = next(c for c in doc["frames"][cel["link"]]["cels"] if c["layer"] == cel["layer"])
                frame["cels"][i] = dict(src, layer=cel["layer"])
    return doc


def frame_rgba(doc, index, layers=None):
    """Flatten one frame to a list of rows of (r, g, b, a) using visible layers (or the given names)."""
    w, h, bpp = doc["width"], doc["height"], doc["depth"] // 8
    out = [[(0, 0, 0, 0)] * w for _ in range(h)]
    cels = sorted(doc["frames"][index]["cels"], key=lambda c: c["layer"])
    for cel in cels:
        layer = doc["layers"][cel["layer"]]
        if layers is not None:
            if layer["name"] not in layers:
                continue
        elif not layer["visible"] or layer["type"] != 0:
            continue
        px = cel["pixels"]
        for yy in range(cel["h"]):
            for xx in range(cel["w"]):
                X, Y = cel["x"] + xx, cel["y"] + yy
                if not (0 <= X < w and 0 <= Y < h):
                    continue
                i = (yy * cel["w"] + xx) * bpp
                if bpp == 4:
                    rgba = tuple(px[i:i + 4])
                elif bpp == 1:
                    idx = px[i]
                    if idx == doc["transparent"]:
                        continue
                    rgba = doc["palette"].get(idx, (0, 0, 0, 255))
                else:
                    v, a = px[i], px[i + 1]
                    rgba = (v, v, v, a)
                if rgba[3] >= 128:
                    out[Y][X] = rgba
    return out
