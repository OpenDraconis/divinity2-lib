from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Iterable, Iterator

from . import Dv2Error

HEADER_SIZE_V5 = 22
DIR_ENTRY_SIZE = 12


class ArchiveError(Dv2Error):
    pass


class UnsupportedVersion(ArchiveError):
    pass


@dataclass(frozen=True)
class Entry:
    path: str
    offset: int
    packed_size: int
    unpacked_size: int

    @property
    def is_compressed(self) -> bool:
        return self.unpacked_size != 0

    def posix_path(self) -> str:
        return self.path.replace("\\", "/")


@dataclass(frozen=True)
class Header:
    version: int
    unknown_a: int
    unknown_b: int
    align_32k: int
    unknown_d: int
    data_start: int
    string_space: int


class Archive:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self._fh: BinaryIO = self.path.open("rb")
        try:
            self.header = self._read_header()
            self.entries = self._read_directory()
        except Exception:
            self._fh.close()
            raise

    def __enter__(self) -> "Archive":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        self._fh.close()

    def __len__(self) -> int:
        return len(self.entries)

    def __iter__(self) -> Iterator[Entry]:
        return iter(self.entries)

    def _read_header(self) -> Header:
        raw = self._fh.read(4)
        if len(raw) < 4:
            raise ArchiveError(f"{self.path}: too short to be an archive")
        (version,) = struct.unpack("<I", raw)

        if version == 4:
            raise UnsupportedVersion(
                f"{self.path}: archive version 4 (the original Ego Draconis) is not "
                "implemented -- no V4 test corpus is available. Use the Developer's Cut."
            )
        if version != 5:
            raise UnsupportedVersion(f"{self.path}: unknown archive version {version}")

        rest = self._fh.read(HEADER_SIZE_V5 - 4)
        if len(rest) < HEADER_SIZE_V5 - 4:
            raise ArchiveError(f"{self.path}: truncated header")
        unknown_a, unknown_b, align_32k, unknown_d, data_start, string_space = (
            struct.unpack("<IIBBII", rest)
        )
        return Header(version, unknown_a, unknown_b, align_32k, unknown_d, data_start, string_space)

    def _read_directory(self) -> list[Entry]:
        blob = self._fh.read(self.header.string_space)
        if len(blob) != self.header.string_space:
            raise ArchiveError(f"{self.path}: truncated string table")
        names = [n.decode("latin-1") for n in blob.split(b"\0") if n]

        raw = self._fh.read(4)
        if len(raw) < 4:
            raise ArchiveError(f"{self.path}: truncated file count")
        (count,) = struct.unpack("<I", raw)

        if count != len(names):
            raise ArchiveError(
                f"{self.path}: file count {count} != string count {len(names)}"
            )

        table = self._fh.read(count * DIR_ENTRY_SIZE)
        if len(table) != count * DIR_ENTRY_SIZE:
            raise ArchiveError(f"{self.path}: truncated directory")

        entries = []
        for i, name in enumerate(names):
            offset, packed, unpacked = struct.unpack_from(
                "<III", table, i * DIR_ENTRY_SIZE
            )
            entries.append(Entry(name, offset, packed, unpacked))
        return entries

    def read(self, entry: Entry) -> bytes:
        self._fh.seek(self.header.data_start + entry.offset)
        raw = self._fh.read(entry.packed_size)
        if len(raw) != entry.packed_size:
            raise ArchiveError(f"{entry.path}: truncated (wanted {entry.packed_size} bytes)")

        if not entry.is_compressed:
            return raw

        try:
            out = zlib.decompress(raw)
        except zlib.error as exc:
            raise ArchiveError(f"{entry.path}: zlib error: {exc}") from exc

        if len(out) != entry.unpacked_size:
            raise ArchiveError(
                f"{entry.path}: decompressed to {len(out)} bytes, "
                f"directory says {entry.unpacked_size}"
            )
        return out


def safe_destination(outdir: Path, posix_path: str) -> Path:
    dest = (outdir / posix_path).resolve()
    if not dest.is_relative_to(outdir.resolve()):
        raise ArchiveError(f"{posix_path}: path escapes the output directory")
    return dest


ALIGNMENT = 32768


def _aligned(n: int) -> int:
    return -(-n // ALIGNMENT) * ALIGNMENT


def write(path: Path | str, files: Iterable[tuple[str, bytes]]) -> int:
    files = [(name.replace("/", "\\"), data) for name, data in files]
    seen: set[str] = set()
    for name, _ in files:
        if name.lower() in seen:
            raise ArchiveError(f"{name}: in the archive twice")
        seen.add(name.lower())
    table = b"".join(name.encode("latin-1") + b"\0" for name, _ in files)
    blobs = [(zlib.compress(data, 9), len(data)) if data else (data, 0) for _, data in files]
    data_start = _aligned(HEADER_SIZE_V5 + len(table) + 4 + DIR_ENTRY_SIZE * len(files))
    offsets, offset = [], 0
    for stored, _ in blobs:
        offsets.append(offset)
        offset = _aligned(offset + len(stored))
    with Path(path).open("wb") as out:
        out.write(struct.pack("<IIIBBII", 5, 1, 4, 0, 1, data_start, len(table)))
        out.write(table + struct.pack("<I", len(files)))
        out.write(b"".join(struct.pack("<III", o, len(stored), size) for o, (stored, size) in zip(offsets, blobs)))
        for o, (stored, _) in zip(offsets, blobs):
            out.seek(data_start + o)
            out.write(stored)
    return len(files)


def check_invariants(archive: Archive) -> list[str]:
    problems: list[str] = []
    h = archive.header

    if h.unknown_a != 1:
        problems.append(f"unknown_a={h.unknown_a}, expected 1 (spec §1.4)")
    if h.unknown_b != 4:
        problems.append(f"unknown_b={h.unknown_b}, expected 4 (spec §1.4)")
    if h.unknown_d != 1:
        problems.append(f"unknown_d={h.unknown_d}, expected 1 (spec §1.4)")

    aligned = h.data_start % ALIGNMENT == 0
    if h.align_32k == 0 and not aligned:
        problems.append(f"align_32k=0 but data_start={h.data_start} is not 32K-aligned")
    elif h.align_32k == 1 and aligned:
        problems.append(
            f"align_32k=1 but data_start={h.data_start} IS 32K-aligned "
            "(never observed in the shipped corpus)"
        )
    if h.align_32k not in (0, 1):
        problems.append(f"align_32k={h.align_32k}, expected 0 or 1")

    for e in archive:
        if e.is_compressed:
            continue
        aligned = (h.data_start + e.offset) % ALIGNMENT == 0
        if h.align_32k == 0 and not aligned:
            problems.append(
                f"{e.path}: align_32k=0 but raw entry is not 32K-aligned "
                f"(abs offset {h.data_start + e.offset})"
            )
        elif h.align_32k == 1 and aligned:
            problems.append(
                f"{e.path}: align_32k=1 but raw entry IS 32K-aligned "
                f"(abs offset {h.data_start + e.offset})"
            )

    return problems
