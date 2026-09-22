"""The NIF container every Gamebryo file comes in: a header, then its blocks back to back.

The header at NIF 20.3.0.9: a version line, version, endianness, user version, block
count, block type names, a type index and a size per block, the string table, then the
groups. Only the header is read here; what a block holds is its type's business.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

from . import Dv2Error

MAGIC = b"Gamebryo File Format"


class NifError(Dv2Error):
    pass


@dataclass(frozen=True)
class Header:
    types: list[str]            # the block type names, each once
    sizes: list[int]            # per block, in bytes
    sizes_at: int               # offset of the first block size
    strings: list[str]
    end: int                    # where the first block starts

    def bounds(self, index: int) -> tuple[int, int]:
        """(start, size) of one block."""
        if not 0 <= index < len(self.sizes):
            raise NifError(f"block {index} is out of range (0..{len(self.sizes) - 1})")
        return self.end + sum(self.sizes[:index]), self.sizes[index]


def parse_header(data: bytes) -> Header:
    if not data.startswith(MAGIC):
        raise NifError("not a NIF file")
    try:
        pos = data.index(b"\n") + 1
        pos += 4                                   # version
        if data[pos] != 1:
            raise NifError(f"big-endian NIF not supported (endian={data[pos]})")
        pos += 1 + 4                               # endianness, user version
        num_blocks, = struct.unpack_from("<I", data, pos); pos += 4
        num_types, = struct.unpack_from("<H", data, pos); pos += 2
        types = []
        for _ in range(num_types):
            n, = struct.unpack_from("<I", data, pos); pos += 4
            types.append(data[pos:pos + n].decode("latin-1")); pos += n
        pos += 2 * num_blocks                      # block type index
        sizes_at = pos
        sizes = list(struct.unpack_from(f"<{num_blocks}I", data, pos)); pos += 4 * num_blocks
        num_strings, = struct.unpack_from("<I", data, pos); pos += 8   # and max length
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
    """`data` with one block's bytes replaced and the size the header declares for it."""
    h = parse_header(data)
    start, size = h.bounds(index)
    out = bytearray(data[:start])
    struct.pack_into("<I", out, h.sizes_at + 4 * index, len(payload))
    return bytes(out) + payload + data[start + size:]
