"""The savegame container, and the story inside it."""
from __future__ import annotations

import dataclasses
import struct
import zlib
from dataclasses import dataclass

from . import osiris_story
from . import Dv2Error
from .osiris_write import write_story

SUFFIX = "init_savegame.dsg"
SECTION = b"SaveLoadStory"
BLOCK = 1024
TAIL = b"\x00\x01\x00\x00\x00\x00"


class SaveError(Dv2Error, ValueError):
    pass


@dataclass
class Header:
    checksum: int
    id: int
    name: str
    major: int
    minor: int
    language: int
    time: int
    description: str
    type: int
    compressed: int
    saveload_objects: int
    region: str
    subregion: str
    timesettings: str
    position: tuple[float, float, float]
    episode: str
    zlib_length: int


class _Reader:
    def __init__(self, data: bytes):
        self.d, self.q = data, 0

    def u32(self) -> int:
        v = struct.unpack_from("<I", self.d, self.q)[0]
        self.q += 4
        return v

    def string(self) -> str:
        n = self.u32()
        v = self.d[self.q:self.q + n].decode("latin-1")
        self.q += n
        return v


def read_header(data: bytes) -> tuple[Header, int]:
    """The header, and the offset of the zlib stream."""
    r = _Reader(data)
    total4, checksum, total12 = r.u32(), r.u32(), r.u32()
    if total4 != len(data) - 4 or total12 != len(data) - 12:
        raise SaveError(f"size fields {total4}, {total12} do not fit {len(data)} bytes")
    h = Header(checksum, struct.unpack("<i", struct.pack("<I", r.u32()))[0], r.string(),
               r.u32(), r.u32(), r.u32(), r.u32() | (r.u32() << 32), r.string(), r.u32(),
               data[r.q], data[r.q + 1], "", "", "", (0.0, 0.0, 0.0), "", 0)
    r.q += 2
    h.region, h.subregion, h.timesettings = r.string(), r.string(), r.string()
    h.position = struct.unpack_from("<fff", data, r.q)
    r.q += 12
    h.episode = r.string()
    if data[r.q:r.q + 6] != TAIL:
        raise SaveError(f"unexpected bytes {data[r.q:r.q + 6].hex()} after the episode name")
    r.q += 6
    h.zlib_length = r.u32()
    if h.zlib_length != len(data) - r.q:
        raise SaveError(f"zlib length {h.zlib_length} does not fit {len(data) - r.q} bytes")
    return h, r.q


#: The game reads each byte as a signed char, so 0x80..0xFF count as negative.
_SIGNED = [b - 256 if b > 127 else b for b in range(256)]


def checksum(data: bytes) -> int:
    """The game's CalculateCheckSum over `data`."""
    h = 0
    for c in map(_SIGNED.__getitem__, data):
        h = (h * 33 + c) & 0xFFFFFFFF
        if h == 0xFFFFFFFF:
            h = 0
    return h


def check(data: bytes) -> Header:
    """The header, after the checksum passed; raises otherwise."""
    h, at = read_header(data)
    got = checksum(data[12:])
    if got != h.checksum:
        raise SaveError(f"checksum {got:#010x}, the file says {h.checksum:#010x}")
    return h


def split(data: bytes) -> tuple[bytes, bytes]:
    """(the header bytes, the decompressed stream)."""
    _, at = read_header(data)
    return data[:at], zlib.decompress(data[at:])


def story_span(stream: bytes) -> tuple[int, int, bytes]:
    """(first block, end of the last block, the story) in a decompressed stream."""
    s = stream.find(SECTION)
    if s < 0:
        raise SaveError("no SaveLoadStory section")
    q = s + len(SECTION) + 1 + 4 + 4          # NUL, u32 0, u32 block size
    start, parts = q, []
    while True:
        a, n = struct.unpack_from("<II", stream, q)
        if n == 0 or n > BLOCK or a not in (BLOCK, n):
            raise SaveError(f"unexpected block header {a}, {n} at {q}")
        parts.append(stream[q + 8:q + 8 + n])
        q += 8 + n
        if n < BLOCK:
            break
    return start, q, b"".join(parts)


def story_of(data: bytes) -> bytes:
    return story_span(split(data)[1])[2]


def blocks(story: bytes) -> bytes:
    out = bytearray()
    for i in range(0, len(story), BLOCK):
        chunk = story[i:i + BLOCK]
        out += struct.pack("<II", BLOCK if len(chunk) == BLOCK else len(chunk), len(chunk)) + chunk
    return bytes(out)


def header_bytes(h: Header) -> bytes:
    """`h` as `read_header` reads it. The sizes, the checksum and the zlib length are zero until
    `pack` sets them."""
    s = lambda t: struct.pack("<I", len(t.encode("latin-1"))) + t.encode("latin-1")
    return (bytes(12) + struct.pack("<i", h.id) + s(h.name)
            + struct.pack("<IIIQ", h.major, h.minor, h.language, h.time) + s(h.description)
            + struct.pack("<IBB", h.type, h.compressed, h.saveload_objects)
            + s(h.region) + s(h.subregion) + s(h.timesettings) + struct.pack("<3f", *h.position)
            + s(h.episode) + TAIL + bytes(4))


def pack(header: bytes, stream: bytes) -> bytes:
    """`header` and the zlib of `stream`, with the sizes and the checksum set. zlib at its default
    level, which both shipped saves carry (`78 9c`); the deflate bytes themselves differ between
    zlib builds and are not compared."""
    z = zlib.compress(stream)
    header = bytearray(header)
    total = len(header) + len(z)
    struct.pack_into("<I", header, 0, total - 4)
    struct.pack_into("<I", header, 8, total - 12)
    struct.pack_into("<I", header, len(header) - 4, len(z))
    struct.pack_into("<I", header, 4, checksum(bytes(header[12:]) + z))
    return bytes(header) + z


def rebuild(data: bytes, story: bytes) -> bytes:
    """`data` with `story` in place of its story: sizes, and the checksum."""
    header, stream = split(data)
    start, end, _ = story_span(stream)
    stream = stream[:start] + blocks(story) + stream[end:]
    return pack(header, struct.pack("<I", len(stream) - 4) + stream[4:])


def _databases(st: osiris_story.Story) -> dict:
    names = {n.db: n.name for n in st.nodes if n.type_id == 1}
    # a database is its name and its column types: HasRedOre exists with
    # one column and with two
    return {(names[d.index], tuple(d.params)): d for d in st.databases if d.index in names}


def transplant(fresh: bytes, runtime: bytes, new_goals: set[str]) -> bytes:
    """The freshly compiled story carrying the runtime story's state"""
    f = osiris_story.read_story(fresh)
    s = osiris_story.read_story(runtime)
    facts = _databases(s)
    for key, d in _databases(f).items():
        if key[0] == "StringTable":
            continue
        if key in facts:
            d.facts = list(facts[key].facts)
    flags = {g.name: g.flags for g in s.goals}
    for g in f.goals:
        if g.name in flags:
            g.flags = flags[g.name]
        elif g.name not in new_goals:
            raise SaveError(f"goal {g.name!r} is neither in the save nor new")
    f = dataclasses.replace(f, header=dataclasses.replace(f.header, banner=s.header.banner,
                                                          debug_flags=s.header.debug_flags))
    return write_story(f)
