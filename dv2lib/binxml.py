from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Iterator

from . import Dv2Error, codec, nif
from .larian_hash import name_hash as _hash
from .names import name_of

NIF_MAGIC = nif.MAGIC
BLOCK_TYPE = "xml::dom::CStreamableNode"

HAS_CHILDREN = 0x01
HAS_ATTRIBUTES = 0x02
HAS_TEXT = 0x04
NARROW_COUNTS = 0x08
KNOWN_FLAGS = 0x0F


class BinXmlError(Dv2Error):
    pass


def hash_of(name: str) -> int:
    if name.startswith("#"):
        try:
            return int(name[1:], 16)
        except ValueError:
            raise BinXmlError(f"malformed hash {name!r}; want #hhhhhhhh") from None
    return _hash(name)


@dataclass
class Node:
    name_hash: int
    attributes: list[tuple[int, str]] = field(default_factory=list)
    text: str | None = None
    children: list["Node"] = field(default_factory=list)
    narrow: bool = True

    @property
    def name(self) -> str:
        return name_of(self.name_hash) or f"#{self.name_hash:08x}"

    def attr(self, name: str) -> str | None:
        wanted = _hash(name)
        return next((v for h, v in self.attributes if h == wanted), None)

    def walk(self) -> Iterator["Node"]:
        yield self
        for c in self.children:
            yield from c.walk()

    def find(self, name: str) -> Iterator["Node"]:
        wanted = _hash(name)
        return (n for n in self.walk() if n.name_hash == wanted)


    def copy(self) -> "Node":
        return Node(self.name_hash, list(self.attributes), self.text,
                    [c.copy() for c in self.children], self.narrow)

    def child(self, name: str, create: bool = True) -> "Node | None":
        h = hash_of(name)
        c = next((k for k in self.children if k.name_hash == h), None)
        if c is None and create:
            c = Node(h)
            self.children.append(c)
        return c

    def set_attr(self, name: str, value: str | None) -> None:
        h = hash_of(name)
        for i, (ah, _) in enumerate(self.attributes):
            if ah == h:
                if value is None:
                    del self.attributes[i]
                else:
                    self.attributes[i] = (h, value)
                return
        if value is not None:
            self.attributes.append((h, value))

    def set_items(self, name: str, values: list[str], text: str | None = None) -> None:
        c = self.child(name)
        c.children = [Node(hash_of("item"), text=v) for v in values]
        c.text = text

    def __repr__(self) -> str:
        return (f"<{self.name} {' '.join(f'{name_of(h) or hex(h)}={v!r}' for h, v in self.attributes)}"
                f"{f' text={self.text!r}' if self.text is not None else ''}"
                f"{f' ({len(self.children)} children)' if self.children else ''}>")


@dataclass
class Document:
    root: Node


def _header(data: bytes) -> nif.Header:
    if not data.startswith(NIF_MAGIC):
        raise BinXmlError("not a NIF file - binary XML is always NIF-wrapped")
    h = nif.parse_header(data)
    if h.types != [BLOCK_TYPE]:
        raise BinXmlError(f"not binary XML; this file holds {h.types}")
    if len(h.sizes) != 1:
        raise BinXmlError(f"expected one block, found {len(h.sizes)}")
    return h


def payload(data: bytes) -> bytes:
    h = _header(data)
    return data[h.end:h.end + h.sizes[0]]


def rewrap(data: bytes, block: bytes) -> bytes:
    _header(data)
    return nif.set_block(data, 0, block)


def parse(data: bytes) -> Node:
    if len(data) < 12:
        raise BinXmlError("block is too short to hold the three header counts")
    n_nodes, n_attrs, n_strings = struct.unpack_from("<III", data, 0)
    pos = 12
    if pos + n_strings > len(data):
        raise BinXmlError(f"string table claims {n_strings} bytes, block has "
                          f"{len(data) - pos}")
    table = data[pos:pos + n_strings]
    pos += n_strings

    strings = table.split(b"\x00")[:-1] if n_strings else []

    at, next_string, nodes, attrs = pos, 0, 0, 0

    def take_string() -> str:
        nonlocal next_string
        if next_string >= len(strings):
            raise BinXmlError(
                f"node {nodes} wants a value but all {len(strings)} "
                "strings are already spoken for"
            )
        next_string += 1
        return strings[next_string - 1].decode("utf-8", errors="surrogateescape")

    def count(flags: int) -> int:
        nonlocal at
        if flags & NARROW_COUNTS:
            at += 1
            return data[at - 1]
        at += 4
        return struct.unpack_from("<I", data, at - 4)[0]

    def node() -> Node:
        nonlocal at, nodes, attrs
        if at >= len(data):
            raise BinXmlError("ran off the end of the block")
        flags = data[at]
        if flags & ~KNOWN_FLAGS:
            raise BinXmlError(
                f"node at offset {at} has flag bits {flags:#04x}; only the low "
                "four are known, so the rest of the walk would be a guess"
            )
        h, = struct.unpack_from("<I", data, at + 1)
        at += 5
        nodes += 1

        out = Node(name_hash=h, narrow=bool(flags & NARROW_COUNTS))
        if flags & HAS_TEXT:
            out.text = take_string()
        if flags & HAS_ATTRIBUTES:
            for _ in range(count(flags)):
                ah, = struct.unpack_from("<I", data, at)
                at += 4
                out.attributes.append((ah, take_string()))
            attrs += len(out.attributes)
        n_child = count(flags) if flags & HAS_CHILDREN else 0
        for _ in range(n_child):
            out.children.append(node())
        return out

    try:
        root = node()
    except struct.error as exc:
        raise BinXmlError(f"ran off the end of the block: {exc}") from None

    if at != len(data):
        raise BinXmlError(f"consumed {at} of {len(data)} bytes")
    if nodes != n_nodes:
        raise BinXmlError(f"walked {nodes} nodes, header declares {n_nodes}")
    if attrs != n_attrs:
        raise BinXmlError(f"read {attrs} attributes, header declares {n_attrs}")
    if next_string != len(strings):
        raise BinXmlError(f"used {next_string} of {len(strings)} strings")
    return root


def build(doc: Document) -> bytes:
    values: list[str] = []
    body = bytearray()
    counts = [0, 0]

    def emit(node: Node) -> None:
        counts[0] += 1
        counts[1] += len(node.attributes)
        flags = 0
        if node.children:
            flags |= HAS_CHILDREN
        if node.attributes:
            flags |= HAS_ATTRIBUTES
        if node.text is not None:
            flags |= HAS_TEXT
        narrow = node.narrow and max(len(node.attributes), len(node.children)) < 256
        if narrow:
            flags |= NARROW_COUNTS

        body.extend(struct.pack("<BI", flags, node.name_hash))
        pack = (lambda n: struct.pack("<B", n)) if narrow else \
               (lambda n: struct.pack("<I", n))
        if node.text is not None:
            values.append(node.text)
        if node.attributes:
            body.extend(pack(len(node.attributes)))
            for h, v in node.attributes:
                body.extend(struct.pack("<I", h))
                values.append(v)
        if node.children:
            body.extend(pack(len(node.children)))
        for c in node.children:
            emit(c)

    emit(doc.root)

    n_nodes, n_attrs = counts
    table = b"".join(codec.encode(v) + b"\x00" for v in values)
    return struct.pack("<III", n_nodes, n_attrs, len(table)) + table + bytes(body)
