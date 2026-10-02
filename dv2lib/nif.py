from __future__ import annotations

import struct
from dataclasses import dataclass

from . import Dv2Error

MAGIC = b"Gamebryo File Format"


class NifError(Dv2Error):
    pass


@dataclass(frozen=True)
class Header:
    types: list[str]
    sizes: list[int]
    sizes_at: int
    strings: list[str]
    end: int

    def bounds(self, index: int) -> tuple[int, int]:
        if not 0 <= index < len(self.sizes):
            raise NifError(f"block {index} is out of range (0..{len(self.sizes) - 1})")
        return self.end + sum(self.sizes[:index]), self.sizes[index]


def parse_header(data: bytes) -> Header:
    if not data.startswith(MAGIC):
        raise NifError("not a NIF file")
    try:
        pos = data.index(b"\n") + 1
        pos += 4
        if data[pos] != 1:
            raise NifError(f"big-endian NIF not supported (endian={data[pos]})")
        pos += 1 + 4
        num_blocks, = struct.unpack_from("<I", data, pos); pos += 4
        num_types, = struct.unpack_from("<H", data, pos); pos += 2
        types = []
        for _ in range(num_types):
            n, = struct.unpack_from("<I", data, pos); pos += 4
            types.append(data[pos:pos + n].decode("latin-1")); pos += n
        pos += 2 * num_blocks
        sizes_at = pos
        sizes = list(struct.unpack_from(f"<{num_blocks}I", data, pos)); pos += 4 * num_blocks
        num_strings, = struct.unpack_from("<I", data, pos); pos += 8
        strings = []
        for _ in range(num_strings):
            n, = struct.unpack_from("<I", data, pos); pos += 4
            strings.append(data[pos:pos + n].decode("latin-1")); pos += n
        num_groups, = struct.unpack_from("<I", data, pos); pos += 4 + 4 * num_groups
    except (struct.error, IndexError, ValueError) as exc:
        raise NifError(f"truncated NIF header: {exc}") from None
    return Header(types, sizes, sizes_at, strings, pos)


def get_block(data: bytes, index: int) -> bytes:
    start, size = parse_header(data).bounds(index)
    return data[start:start + size]


def set_block(data: bytes, index: int, payload: bytes) -> bytes:
    h = parse_header(data)
    start, size = h.bounds(index)
    out = bytearray(data[:start])
    struct.pack_into("<I", out, h.sizes_at + 4 * index, len(payload))
    return bytes(out) + payload + data[start + size:]
