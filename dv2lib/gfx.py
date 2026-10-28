from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass, field

from . import Dv2Error

SIGNATURES = {b"FWS": False, b"GFX": False, b"CWS": True, b"CFX": True}

TAG_NAMES = {
    0: "End", 1: "ShowFrame", 2: "DefineShape", 9: "SetBackgroundColor", 12: "DoAction",
    22: "DefineShape2", 26: "PlaceObject2", 28: "RemoveObject2", 32: "DefineShape3",
    37: "DefineEditText", 39: "DefineSprite", 43: "FrameLabel", 46: "DefineMorphShape",
    56: "ExportAssets", 69: "FileAttributes", 70: "PlaceObject3", 71: "ImportAssets2",
    74: "CSMTextSettings", 75: "DefineFont3", 77: "Metadata", 78: "DefineScalingGrid",
    83: "DefineShape4", 1000: "ExporterInfo", 1001: "DefineExternalImage",
    1003: "DefineExternalGradientImage",
}

OPCODES = {
    0x04: ("next_frame", 0), 0x05: ("prev_frame", 0), 0x06: ("play", 0), 0x07: ("stop", 0),
    0x08: ("toggle_qlty", 0), 0x09: ("stop_sounds", 0), 0x0A: ("add", 0), 0x0B: ("sub", 0),
    0x0C: ("mul", 0), 0x0D: ("div", 0), 0x0E: ("equ", 0), 0x0F: ("lt", 0), 0x10: ("and", 0),
    0x11: ("or", 0), 0x12: ("not", 0), 0x13: ("str_eq", 0), 0x14: ("str_len", 0),
    0x15: ("substr", 0), 0x17: ("pop", 0), 0x18: ("floor", 0), 0x1C: ("get_var", 0),
    0x1D: ("set_var", 0), 0x20: ("set_target2", 0), 0x21: ("str_cat", 0), 0x22: ("get_prop", 0),
    0x23: ("set_prop", 0), 0x24: ("dup_sprite", 0), 0x25: ("rem_sprite", 0), 0x26: ("trace", 0),
    0x27: ("start_drag", 0), 0x28: ("stop_drag", 0), 0x29: ("str_lt", 0), 0x2A: ("throw", 0),
    0x2B: ("cast_object", 0), 0x2C: ("implements", 0), 0x30: ("random", 0),
    0x31: ("mb_length", 0), 0x32: ("ord", 0), 0x33: ("chr", 0), 0x34: ("get_timer", 0),
    0x35: ("substr_mb", 0), 0x36: ("ord_mb", 0), 0x37: ("chr_mb", 0), 0x3A: ("delete", 0),
    0x3B: ("delete2", 1), 0x3C: ("set_local", 0), 0x3D: ("call_func", 0), 0x3E: ("return", 0),
    0x3F: ("mod", 0), 0x40: ("new", 0), 0x41: ("decl_local", 0), 0x42: ("decl_array", 0),
    0x43: ("decl_obj", 0), 0x44: ("type_of", 0), 0x45: ("get_target", 0), 0x46: ("enumerate", 0),
    0x47: ("add_t", 0), 0x48: ("lt_t", 0), 0x49: ("eq_t", 0), 0x4A: ("number", 0),
    0x4B: ("string", 0), 0x4C: ("dup", 0), 0x4D: ("swap", 0), 0x4E: ("get_member", 0),
    0x4F: ("set_member", 0), 0x50: ("inc", 0), 0x51: ("dec", 0), 0x52: ("call_method", 0),
    0x53: ("new_method", 0), 0x54: ("is_inst_of", 0), 0x55: ("enum_object", 0),
    0x60: ("bit_and", 0), 0x61: ("bit_or", 0), 0x62: ("bit_xor", 0), 0x63: ("shl", 0),
    0x64: ("asr", 0), 0x65: ("lsr", 0), 0x66: ("eq_strict", 0), 0x67: ("gt_t", 0),
    0x68: ("gt_str", 0), 0x69: ("extends", 0), 0x81: ("goto_frame", 4), 0x83: ("get_url", 1),
    0x87: ("store_register", 3), 0x88: ("decl_dict", 7), 0x8A: ("wait_for_frame", 2),
    0x8B: ("set_target", 1), 0x8C: ("goto_frame_lbl", 1), 0x8D: ("wait_for_fr_exp", 2),
    0x8E: ("function2", 9), 0x8F: ("try", 2), 0x94: ("with", 4), 0x96: ("push_data", 6),
    0x99: ("goto", 5), 0x9A: ("get_url2", 2), 0x9B: ("function", 8), 0x9D: ("branch_if_true", 5),
    0x9E: ("call_frame", 2), 0x9F: ("goto_frame_exp", 2),
}

CLIP_EVENTS = ("KeyUp", "KeyDown", "MouseUp", "MouseDown", "MouseMove", "Unload", "EnterFrame",
               "Load", "DragOver", "RollOut", "RollOver", "ReleaseOutside", "Release", "Press",
               "Initialize", "Data", None, None, None, None, None, "Construct", "KeyPress",
               "DragOut", None, None, None, None, None, None, None, None)

FILTERS = {0: "DropShadow", 1: "Blur", 2: "Glow", 3: "Bevel", 4: "GradientGlow", 5: "Convolution",
           6: "ColorMatrix", 7: "GradientBevel"}


class GfxError(Dv2Error):
    pass


@dataclass
class Tag:
    code: int
    name: str
    raw: bytes
    fields: dict = field(default_factory=dict)


@dataclass
class Movie:
    signature: bytes
    version: int
    file_length: int
    frame_size: dict
    frame_rate: float
    frame_count: int
    header: bytes
    tags: list[Tag]

    def of(self, name: str) -> list[Tag]:
        return [t for t in self.tags if t.name == name]

    @property
    def exporter_info(self) -> dict | None:
        found = self.of("ExporterInfo")
        return found[0].fields if found else None

    @property
    def external_images(self) -> list[dict]:
        return [t.fields for t in self.of("DefineExternalImage")]

    @property
    def external_gradients(self) -> list[dict]:
        return [t.fields for t in self.of("DefineExternalGradientImage")]

    @property
    def imports(self) -> list[dict]:
        return [t.fields for t in self.of("ImportAssets2")]


class _Reader:
    def __init__(self, data: bytes, pos: int = 0, end: int | None = None):
        self.data, self.pos = data, pos
        self.end = len(data) if end is None else end
        self.bit = 0
        self.byte = 0

    def align(self):
        self.bit = 0

    def take(self, fmt: str):
        self.align()
        size = struct.calcsize("<" + fmt)
        if self.pos + size > self.end:
            raise GfxError(f"read past the end at {self.pos:#x}")
        v = struct.unpack_from("<" + fmt, self.data, self.pos)
        self.pos += size
        return v if len(v) > 1 else v[0]

    def raw(self, n: int) -> bytes:
        self.align()
        if self.pos + n > self.end:
            raise GfxError(f"read past the end at {self.pos:#x}")
        b = self.data[self.pos:self.pos + n]
        self.pos += n
        return b

    def u8(self): return self.take("B")
    def u16(self): return self.take("H")
    def s16(self): return self.take("h")
    def u32(self): return self.take("I")
    def s32(self): return self.take("i")
    def f32(self): return self.take("f")

    def f64(self):
        hi, lo = self.raw(4), self.raw(4)
        return struct.unpack("<d", lo + hi)[0]

    def fixed(self): return self.s32() / 65536
    def fixed8(self): return self.s16() / 256

    def ub(self, n: int) -> int:
        v = 0
        for _ in range(n):
            if self.bit == 0:
                if self.pos >= self.end:
                    raise GfxError(f"read past the end at {self.pos:#x}")
                self.byte = self.data[self.pos]
                self.pos += 1
                self.bit = 8
            self.bit -= 1
            v = (v << 1) | ((self.byte >> self.bit) & 1)
        return v

    def sb(self, n: int) -> int:
        v = self.ub(n)
        return v - (1 << n) if n and v & (1 << (n - 1)) else v

    def fb(self, n: int) -> float:
        return self.sb(n) / 65536

    def flag(self) -> bool:
        return self.ub(1) == 1

    def string(self) -> str:
        self.align()
        e = self.data.index(0, self.pos, self.end)
        s = self.data[self.pos:e].decode("utf-8", "surrogateescape")
        self.pos = e + 1
        return s

    def string_with_length(self) -> str:
        return self.raw(self.u8()).decode("utf-8", "surrogateescape")

    def rect(self) -> dict:
        n = self.ub(5)
        r = {"xmin": self.sb(n), "xmax": self.sb(n), "ymin": self.sb(n), "ymax": self.sb(n)}
        self.align()
        return r

    def rgb(self) -> tuple:
        return self.take("3B")

    def rgba(self) -> tuple:
        return self.take("4B")

    def matrix(self) -> dict:
        m = {"scale": None, "rotate": None, "translate": None}
        if self.flag():
            n = self.ub(5)
            m["scale"] = (self.fb(n), self.fb(n))
        if self.flag():
            n = self.ub(5)
            m["rotate"] = (self.fb(n), self.fb(n))
        n = self.ub(5)
        m["translate"] = (self.sb(n), self.sb(n))
        self.align()
        return m

    def cxform(self, alpha: bool) -> dict:
        has_add, has_mult, n = self.flag(), self.flag(), self.ub(4)
        count = 4 if alpha else 3
        mult = tuple(self.sb(n) for _ in range(count)) if has_mult else None
        add = tuple(self.sb(n) for _ in range(count)) if has_add else None
        self.align()
        return {"mult": mult, "add": add}


def read(data: bytes) -> Movie:
    signature = data[:3]
    if signature not in SIGNATURES:
        raise GfxError(f"not a movie: signature {signature!r}")
    version, file_length = data[3], struct.unpack_from("<I", data, 4)[0]
    body = data[:8] + (zlib.decompress(data[8:]) if SIGNATURES[signature] else data[8:])
    r = _Reader(body, 8)
    frame_size = r.rect()
    rate = r.u16() / 256
    count = r.u16()
    header = body[8:r.pos]
    return Movie(signature, version, file_length, frame_size, rate, count, header,
                 _tags(body, r.pos, len(body), version))


def _tags(data: bytes, pos: int, end: int, version: int) -> list[Tag]:
    tags = []
    while pos < end:
        if pos + 2 > end:
            raise GfxError(f"tag header past the end at {pos:#x}")
        head = struct.unpack_from("<H", data, pos)[0]
        pos += 2
        code, length = head >> 6, head & 0x3F
        if length == 0x3F:
            length = struct.unpack_from("<I", data, pos)[0]
            pos += 4
        if pos + length > end:
            raise GfxError(f"tag {code} at {pos:#x} runs past the end")
        tag = Tag(code, TAG_NAMES.get(code, f"Tag{code}"), data[pos:pos + length])
        tag.fields = _decode(tag, version)
        tags.append(tag)
        pos += length
        if code == 0:
            break
    return tags


def _decode(tag: Tag, version: int) -> dict:
    reader = _READERS.get(tag.code)
    if reader is None:
        raise GfxError(f"tag {tag.code} has no reader")
    r = _Reader(tag.raw)
    fields = reader(r, tag.code, version)
    r.align()
    if r.pos != len(tag.raw):
        raise GfxError(f"{tag.name} read {r.pos} of {len(tag.raw)} bytes")
    return fields


def _empty(r, code, version):
    return {}


def _background(r, code, version):
    return {"color": r.rgb()}


def _shape_version(code: int) -> int:
    return {2: 1, 22: 2, 32: 3, 83: 4}[code]


def _gradient(r, shape: int, focal: bool) -> dict:
    g = {"spread": r.ub(2), "interpolation": r.ub(2)}
    n = r.ub(4)
    g["records"] = [(r.u8(), r.rgba() if shape >= 3 else r.rgb()) for _ in range(n)]
    g["focal_point"] = r.fixed8() if focal else None
    return g


def _fill_style(r, shape: int) -> dict:
    kind = r.u8()
    f = {"type": kind}
    if kind == 0x00:
        f["color"] = r.rgba() if shape >= 3 else r.rgb()
    elif kind in (0x10, 0x12, 0x13):
        f["matrix"] = r.matrix()
        f["gradient"] = _gradient(r, shape, kind == 0x13)
    elif kind in (0x40, 0x41, 0x42, 0x43):
        f["bitmap"] = r.u16()
        f["matrix"] = r.matrix()
    else:
        raise GfxError(f"fill style type {kind:#x}")
    return f


def _count(r, shape: int) -> int:
    n = r.u8()
    return r.u16() if n == 0xFF and shape >= 2 else n


def _line_style(r, shape: int) -> dict:
    if shape < 4:
        return {"width": r.u16(), "color": r.rgba() if shape >= 3 else r.rgb()}
    s = {"width": r.u16(), "start_cap": r.ub(2), "join": r.ub(2), "has_fill": r.flag(),
         "no_hscale": r.flag(), "no_vscale": r.flag(), "pixel_hinting": r.flag()}
    r.ub(5)
    s["no_close"] = r.flag()
    s["end_cap"] = r.ub(2)
    s["miter_limit"] = r.fixed8() if s["join"] == 2 else None
    if s["has_fill"]:
        s["fill"] = _fill_style(r, shape)
    else:
        s["color"] = r.rgba()
    return s


def _styles(r, shape: int) -> tuple[list, list]:
    fills = [_fill_style(r, shape) for _ in range(_count(r, shape))]
    lines = [_line_style(r, shape) for _ in range(_count(r, shape))]
    return fills, lines


def _records(r, shape: int, styles: bool) -> list[dict]:
    fill_bits, line_bits = r.ub(4), r.ub(4)
    records = []
    while True:
        if r.flag():
            if r.flag():
                n = r.ub(4) + 2
                if r.flag():
                    records.append({"type": "line", "dx": r.sb(n), "dy": r.sb(n)})
                elif r.flag():
                    records.append({"type": "line", "dx": 0, "dy": r.sb(n)})
                else:
                    records.append({"type": "line", "dx": r.sb(n), "dy": 0})
            else:
                n = r.ub(4) + 2
                records.append({"type": "curve", "cx": r.sb(n), "cy": r.sb(n),
                                "ax": r.sb(n), "ay": r.sb(n)})
            continue
        new_styles, line, fill1, fill0, move = (r.flag() for _ in range(5))
        if not (new_styles or line or fill1 or fill0 or move):
            break
        s = {"type": "style"}
        if move:
            n = r.ub(5)
            s["move"] = (r.sb(n), r.sb(n))
        if fill0:
            s["fill0"] = r.ub(fill_bits)
        if fill1:
            s["fill1"] = r.ub(fill_bits)
        if line:
            s["line"] = r.ub(line_bits)
        if new_styles:
            if not styles:
                raise GfxError("new styles in a shape without styles")
            s["fills"], s["lines"] = _styles(r, shape)
            fill_bits, line_bits = r.ub(4), r.ub(4)
        records.append(s)
    r.align()
    return records


def _shape(r, code, version):
    shape = _shape_version(code)
    s = {"id": r.u16(), "bounds": r.rect()}
    if shape == 4:
        s["edge_bounds"] = r.rect()
        r.ub(5)
        s["uses_fill_winding"], s["non_scaling_strokes"], s["scaling_strokes"] = r.flag(), r.flag(), r.flag()
    s["fills"], s["lines"] = _styles(r, shape)
    s["records"] = _records(r, shape, True)
    return s


def _morph_fill(r) -> dict:
    kind = r.u8()
    f = {"type": kind}
    if kind == 0x00:
        f["start_color"], f["end_color"] = r.rgba(), r.rgba()
    elif kind in (0x10, 0x12):
        f["start_matrix"], f["end_matrix"] = r.matrix(), r.matrix()
        f["records"] = [(r.u8(), r.rgba(), r.u8(), r.rgba()) for _ in range(r.u8())]
    elif kind in (0x40, 0x41, 0x42, 0x43):
        f["bitmap"] = r.u16()
        f["start_matrix"], f["end_matrix"] = r.matrix(), r.matrix()
    else:
        raise GfxError(f"morph fill style type {kind:#x}")
    return f


def _morph(r, code, version):
    m = {"id": r.u16(), "start_bounds": r.rect(), "end_bounds": r.rect(), "offset": r.u32()}
    m["fills"] = [_morph_fill(r) for _ in range(_count(r, 3))]
    m["lines"] = [{"start_width": r.u16(), "end_width": r.u16(), "start_color": r.rgba(),
                   "end_color": r.rgba()} for _ in range(_count(r, 3))]
    m["start_records"] = _records(r, 3, False)
    m["end_records"] = _records(r, 3, False)
    return m


def _edit_text(r, code, version):
    t = {"id": r.u16(), "bounds": r.rect()}
    names = ("has_text", "word_wrap", "multiline", "password", "read_only", "has_text_color",
             "has_max_length", "has_font", "has_font_class", "auto_size", "has_layout",
             "no_select", "border", "was_static", "html", "use_outlines")
    t.update({n: r.flag() for n in names})
    if t["has_font"]:
        t["font"], t["height"] = r.u16(), r.u16()
    if t["has_text_color"]:
        t["color"] = r.rgba()
    if t["has_max_length"]:
        t["max_length"] = r.u16()
    if t["has_layout"]:
        t["align"], t["left_margin"], t["right_margin"] = r.u8(), r.u16(), r.u16()
        t["indent"], t["leading"] = r.u16(), r.s16()
    t["variable"] = r.string()
    if t["has_text"]:
        t["text"] = r.string()
    return t


def _font3(r, code, version):
    f = {"id": r.u16()}
    for n in ("has_layout", "shift_jis", "small_text", "ansi", "wide_offsets", "wide_codes",
              "italic", "bold"):
        f[n] = r.flag()
    f["language"] = r.u8()
    f["name"] = r.string_with_length()
    n = r.u16()
    start = r.pos
    offsets = [r.u32() if f["wide_offsets"] else r.u16() for _ in range(n)]
    code_table = r.u32() if f["wide_offsets"] else r.u16()
    bounds = offsets[1:] + [code_table]
    f["glyphs"] = []
    for i in range(n):
        g = _Reader(r.data, start + offsets[i], start + bounds[i])
        f["glyphs"].append(_records(g, 1, False))
        if g.pos != g.end:
            raise GfxError(f"glyph {i} read to {g.pos:#x}, ends at {g.end:#x}")
    r.pos = start + code_table
    f["codes"] = [r.u16() if f["wide_codes"] else r.u8() for _ in range(n)]
    if f["has_layout"]:
        f["ascent"], f["descent"], f["leading"] = r.u16(), r.u16(), r.s16()
        f["advances"] = [r.s16() for _ in range(n)]
        f["glyph_bounds"] = [r.rect() for _ in range(n)]
        pair = (lambda: (r.u16(), r.u16())) if f["wide_codes"] else (lambda: (r.u8(), r.u8()))
        f["kerning"] = [(*pair(), r.s16()) for _ in range(r.u16())]
    f["unread"] = r.raw(r.end - r.pos)
    return f


def _filters(r) -> list[dict]:
    out = []
    for _ in range(r.u8()):
        kind = r.u8()
        f = {"type": FILTERS.get(kind, kind)}
        if kind == 0:
            f.update(color=r.rgba(), blur_x=r.fixed(), blur_y=r.fixed(), angle=r.fixed(),
                     distance=r.fixed(), strength=r.fixed8(), inner=r.flag(), knockout=r.flag(),
                     composite=r.flag(), passes=r.ub(5))
        elif kind == 1:
            f.update(blur_x=r.fixed(), blur_y=r.fixed(), passes=r.ub(5))
            r.ub(3)
        elif kind == 2:
            f.update(color=r.rgba(), blur_x=r.fixed(), blur_y=r.fixed(), strength=r.fixed8(),
                     inner=r.flag(), knockout=r.flag(), composite=r.flag(), passes=r.ub(5))
        elif kind == 3:
            f.update(shadow=r.rgba(), highlight=r.rgba(), blur_x=r.fixed(), blur_y=r.fixed(),
                     angle=r.fixed(), distance=r.fixed(), strength=r.fixed8(), inner=r.flag(),
                     knockout=r.flag(), composite=r.flag(), on_top=r.flag(), passes=r.ub(4))
        elif kind in (4, 7):
            n = r.u8()
            f["colors"] = [r.rgba() for _ in range(n)]
            f["ratios"] = [r.u8() for _ in range(n)]
            f.update(blur_x=r.fixed(), blur_y=r.fixed(), angle=r.fixed(), distance=r.fixed(),
                     strength=r.fixed8(), inner=r.flag(), knockout=r.flag(), composite=r.flag(),
                     on_top=r.flag(), passes=r.ub(4))
        elif kind == 5:
            x, y = r.u8(), r.u8()
            f.update(matrix_x=x, matrix_y=y, divisor=r.f32(), bias=r.f32(),
                     matrix=[r.f32() for _ in range(x * y)], default_color=r.rgba())
            r.ub(6)
            f.update(clamp=r.flag(), preserve_alpha=r.flag())
        elif kind == 6:
            f["matrix"] = [r.f32() for _ in range(20)]
        else:
            raise GfxError(f"filter type {kind}")
        out.append(f)
    return out


def _event_flags(r, width: int) -> dict:
    bits = [r.flag() for _ in range(width)]
    value = sum(b << (width - 1 - i) for i, b in enumerate(bits))
    return {"bits": value, "events": [n for n, b in zip(CLIP_EVENTS, bits) if b and n]}


def _clip_actions(r, width: int) -> dict:
    r.u16()
    c = {"all_events": _event_flags(r, width), "records": []}
    while True:
        pos = r.pos
        flags = r.u32() if width == 32 else r.u16()
        if flags == 0:
            break
        r.pos = pos
        events = _event_flags(r, width)
        size = r.u32()
        rec = {"events": events}
        end = r.pos + size
        if "KeyPress" in events["events"]:
            rec["key"] = r.u8()
        rec["actions"] = _actions(r.data, r.pos, end)
        r.pos = end
        c["records"].append(rec)
    return c


def _place(r, code, version):
    p = {}
    names = ("has_clip_actions", "has_clip_depth", "has_name", "has_ratio", "has_cxform",
             "has_matrix", "has_character", "move")
    p.update({n: r.flag() for n in names})
    if code == 70:
        r.ub(1)
        names3 = ("opaque_background", "has_visible", "has_image", "has_class_name",
                  "has_cache_as_bitmap", "has_blend_mode", "has_filters")
        p.update({n: r.flag() for n in names3})
    p["depth"] = r.u16()
    if code == 70 and (p["has_class_name"] or (p["has_image"] and p["has_character"])):
        p["class_name"] = r.string()
    if p["has_character"]:
        p["character"] = r.u16()
    if p["has_matrix"]:
        p["matrix"] = r.matrix()
    if p["has_cxform"]:
        p["cxform"] = r.cxform(True)
    if p["has_ratio"]:
        p["ratio"] = r.u16()
    if p["has_name"]:
        p["name"] = r.string()
    if p["has_clip_depth"]:
        p["clip_depth"] = r.u16()
    if code == 70:
        if p["has_filters"]:
            p["filters"] = _filters(r)
        if p["has_blend_mode"]:
            p["blend_mode"] = r.u8()
        if p["has_cache_as_bitmap"]:
            p["cache_as_bitmap"] = r.u8()
        if p["has_visible"]:
            p["visible"] = r.u8()
            p["background"] = r.rgba()
    if p["has_clip_actions"]:
        p["clip_actions"] = _clip_actions(r, 16 if version < 6 and code != 70 else 32)
    return p


def _remove(r, code, version):
    return {"depth": r.u16()}


def _sprite(r, code, version):
    s = {"id": r.u16(), "frame_count": r.u16()}
    s["tags"] = _tags(r.data, r.pos, r.end, version)
    r.pos = r.end
    return s


def _do_action(r, code, version):
    a = {"actions": _actions(r.data, 0, r.end)}
    r.pos = r.end
    return a


def _frame_label(r, code, version):
    f = {"label": r.string()}
    f["anchor"] = r.u8() if r.pos < r.end else None
    return f


def _export(r, code, version):
    return {"symbols": [(r.u16(), r.string()) for _ in range(r.u16())]}


def _import2(r, code, version):
    i = {"url": r.string()}
    n = r.u16()
    i["skipped"] = r.raw(2)
    i["symbols"] = [(r.u16(), r.string()) for _ in range(n)]
    return i


def _file_attributes(r, code, version):
    r.ub(1)
    a = {"use_direct_blit": r.flag(), "use_gpu": r.flag(), "has_metadata": r.flag(),
         "actionscript3": r.flag()}
    r.ub(2)
    a["use_network"] = r.flag()
    r.raw(3)
    return a


def _csm(r, code, version):
    c = {"text": r.u16(), "use_flash_type": r.ub(2), "grid_fit": r.ub(3)}
    r.ub(3)
    c["thickness"], c["sharpness"] = r.f32(), r.f32()
    r.u8()
    return c


def _metadata(r, code, version):
    return {"xml": r.string()}


def _scaling_grid(r, code, version):
    return {"character": r.u16(), "splitter": r.rect()}


def _exporter_info(r, code, version):
    e = {"version": r.u16()}
    e["flags"] = r.u32() if e["version"] >= 0x10A else 0
    e["bitmap_format"] = r.u16()
    e["prefix"] = r.string_with_length()
    e["swf_name"] = r.string_with_length()
    return e


def _external_image(r, code, version):
    return {"id": r.u16(), "format": r.u16(), "width": r.u16(), "height": r.u16(),
            "export_name": r.string_with_length(), "file_name": r.string_with_length()}


def _external_gradient(r, code, version):
    return {"id": r.u16(), "format": r.u16(), "size": r.u16(), "file_name": r.string_with_length()}


def _push(r, end) -> list:
    values = []
    while r.pos < end:
        kind = r.u8()
        if kind == 0:
            values.append(("string", r.string()))
        elif kind == 1:
            values.append(("float", r.f32()))
        elif kind == 2:
            values.append(("null", None))
        elif kind == 3:
            values.append(("undefined", None))
        elif kind == 4:
            values.append(("register", r.u8()))
        elif kind == 5:
            values.append(("bool", r.u8() != 0))
        elif kind == 6:
            values.append(("double", r.f64()))
        elif kind == 7:
            values.append(("int", r.s32()))
        elif kind == 8:
            values.append(("constant", r.u8()))
        elif kind == 9:
            values.append(("constant", r.u16()))
        else:
            raise GfxError(f"push value type {kind}")
    return values


def _operands(op: int, r: _Reader, end: int) -> dict:
    if op == 0x81:
        return {"frame": r.u16()}
    if op == 0x83:
        return {"url": r.string(), "target": r.string()}
    if op == 0x87:
        return {"register": r.u8()}
    if op == 0x88:
        return {"constants": [r.string() for _ in range(r.u16())]}
    if op == 0x8A:
        return {"frame": r.u16(), "skip": r.u8()}
    if op == 0x8B:
        return {"target": r.string()}
    if op == 0x8C:
        return {"label": r.string()}
    if op == 0x8D:
        return {"skip": r.u8()}
    if op == 0x8E:
        f = {"function": r.string()}
        n = r.u16()
        f["registers"] = r.u8()
        flags = r.u16()
        f["flags"] = flags
        f["params"] = [(r.u8(), r.string()) for _ in range(n)]
        f["code_size"] = r.u16()
        return f
    if op == 0x8F:
        r.ub(5)
        t = {"catch_in_register": r.flag(), "has_finally": r.flag(), "has_catch": r.flag()}
        t["try_size"], t["catch_size"], t["finally_size"] = r.u16(), r.u16(), r.u16()
        t["catch"] = r.u8() if t["catch_in_register"] else r.string()
        return t
    if op == 0x94:
        return {"code_size": r.u16()}
    if op == 0x96:
        return {"values": _push(r, end)}
    if op in (0x99, 0x9D):
        return {"offset": r.s16()}
    if op == 0x9A:
        return {"send_method": r.ub(2), "reserved": r.ub(4), "load_target": r.flag(),
                "load_variables": r.flag()}
    if op == 0x9B:
        f = {"function": r.string()}
        f["params"] = [r.string() for _ in range(r.u16())]
        f["code_size"] = r.u16()
        return f
    if op == 0x9E:
        return {}
    if op == 0x9F:
        r.ub(6)
        g = {"scene_bias": r.flag(), "play": r.flag()}
        if g["scene_bias"]:
            g["bias"] = r.u16()
        return g
    raise GfxError(f"opcode {op:#x} has operands")


def _actions(data: bytes, pos: int, end: int) -> list[dict]:
    out = []
    while pos < end:
        op = data[pos]
        at = pos
        pos += 1
        if op == 0:
            out.append({"offset": at, "op": 0, "name": "end"})
            break
        name = OPCODES.get(op, (f"op_{op:02x}", 0))[0]
        a = {"offset": at, "op": op, "name": name}
        if op >= 0x80:
            length = struct.unpack_from("<H", data, pos)[0]
            pos += 2
            r = _Reader(data, pos, pos + length)
            a.update(_operands(op, r, pos + length))
            r.align()
            if r.pos != pos + length:
                raise GfxError(f"{name} at {at:#x} read {r.pos - pos} of {length} bytes")
            pos += length
        out.append(a)
    return out


_READERS = {
    0: _empty, 1: _empty, 2: _shape, 9: _background, 12: _do_action, 22: _shape, 26: _place,
    28: _remove, 32: _shape, 37: _edit_text, 39: _sprite, 43: _frame_label, 46: _morph,
    56: _export, 69: _file_attributes, 70: _place, 71: _import2, 74: _csm, 75: _font3,
    77: _metadata, 78: _scaling_grid, 83: _shape, 1000: _exporter_info,
    1001: _external_image, 1003: _external_gradient,
}
