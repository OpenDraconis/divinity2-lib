from __future__ import annotations

import struct
from dataclasses import dataclass, field

from . import Dv2Error

MAGIC = b"Kynogon HPD\0"
MESH_MAGIC = b"KynogonRuntimeMesh\0"
HEADER_AT = 0x10
ENTRY_AT = 0x9C
ENTRY_SIZE = 0x30
SLOT_HEADER = 8
NONE = 0xFFFFFFFF


class KynapseError(Dv2Error, ValueError):
    pass


@dataclass
class DataDesc:
    id: int
    offset: int
    size: int


@dataclass
class Entry:
    unique_id: int
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    z_min: float
    z_max: float
    level: int
    size: int
    offset: int
    tag1: int
    tag2: int


@dataclass
class Node:
    unique_id: int
    x: float
    y: float
    z: float
    abstract: int
    next_copy: int
    first_out: int
    extra: bytes


@dataclass
class Edge:
    cost: int
    p1: int
    p2: int


@dataclass
class Link:
    p1: tuple[float, float, float]
    p2: tuple[float, float, float]
    lm: int
    lm_size: int


@dataclass
class MultiMeshLink(Link):
    mask: tuple[float, float, float]


@dataclass
class Shape:
    first_offset: int
    orientation: tuple[float, float, float]
    points: list[tuple[float, float, float]]


@dataclass
class LocalMap:
    mesh_id: int
    a: int
    b: int
    c: int
    radius: float
    pitch: float
    max_alt: float
    min_alt: float
    in_links: list[Link]
    out_links: list[Link]
    multi_mesh_links: list[MultiMeshLink]
    in_obstacles: list[list[tuple[float, float, float]]]
    out_obstacles: list[list[tuple[float, float, float]]]
    shapes: list[Shape]
    shape_end: tuple[int, tuple[float, float, float]] | None
    offsets: dict[str, int]
    size: int


@dataclass
class ColumnHeader:
    lm: int
    alt_min: float
    alt_max: float


@dataclass
class Column:
    headers: list[ColumnHeader]
    end: int | None
    maps: list[LocalMap]


@dataclass
class AiMesh:
    pad: bytes
    version: int
    self_pointer: int
    mesh_id: int
    inv_local_map_size: float
    pitch: float
    right_min: float
    right_max: float
    front_min: float
    front_max: float
    a_max: int
    b_max: int
    radius: float
    column_table_at: int
    column_offsets: list[int]
    neighbour_count: int
    neighbour_offset: int
    columns: list[Column]
    tail: int
    size: int

    @property
    def local_map_size(self) -> float:
        return 1.0 / self.inv_local_map_size


@dataclass
class Slot:
    entry: Entry
    nodes: list[Node]
    edges: list[Edge]
    mesh: AiMesh | None
    mesh_at: int
    trailer: tuple[int, int] | None


@dataclass
class Hpd:
    version: int
    file_version: int
    project_type: int
    origin: tuple[float, float, float]
    edge_length: float
    node_data: list[DataDesc]
    edge_data: list[DataDesc]
    node_size: int
    edge_size: int
    ai_meshes: int
    pod_entries: list[tuple[int, int, int]]
    entries: list[Entry]
    slots: list[Slot]


def _u(data: bytes, at: int, n: int = 1) -> tuple[int, ...]:
    return struct.unpack_from(f"<{n}I", data, at)


def _f(data: bytes, at: int, n: int = 1) -> tuple[float, ...]:
    return struct.unpack_from(f"<{n}f", data, at)


def _vectors(data: bytes, start: int, end: int) -> list[tuple[float, float, float]]:
    return [_f(data, at, 3) for at in range(start, end, 12)]


# Kaim::CAiMesh::LoadAiMesh @d158d0, `anonymous namespace'::ReadLocalMapBuffer @d15640 decomp
def read_local_map(blob: bytes, at: int, end: int) -> LocalMap:
    head = struct.unpack_from("<4I4f12I", blob, at)
    (mesh_id, a, b, c, radius, pitch, max_alt, min_alt, in_n, in_o, out_n, out_o, mm_n, mm_o,
     io_n, io_o, oo_n, oo_o, sh_n, sh_o) = head

    def links(count: int, offset: int, size: int, build):
        return [build(at + offset + size * i) for i in range(count)] if count else []

    def link(p: int) -> Link:
        return Link(_f(blob, p, 3), _f(blob, p + 12, 3), *_u(blob, p + 24, 2))

    def multi(p: int) -> MultiMeshLink:
        return MultiMeshLink(_f(blob, p, 3), _f(blob, p + 12, 3), *_u(blob, p + 24, 2), _f(blob, p + 32, 3))

    def obstacles(count: int, offset: int):
        if not count:
            return []
        table = _u(blob, at + offset, count + 1)
        return [_vectors(blob, at + table[i], at + table[i + 1]) for i in range(count)]

    in_links = links(in_n, in_o, 32, link)
    out_links = links(out_n, out_o, 32, link)
    mm_links = links(mm_n, mm_o, 44, multi)
    in_obs = obstacles(io_n, io_o)
    out_obs = obstacles(oo_n, oo_o)
    shapes: list[Shape] = []
    shape_end = None
    if sh_n:
        first = [_u(blob, at + sh_o + 16 * i)[0] for i in range(sh_n + 1)]
        for i in range(sh_n):
            shapes.append(Shape(first[i], _f(blob, at + sh_o + 16 * i + 4, 3),
                                _vectors(blob, at + first[i], at + first[i + 1])))
        shape_end = (first[sh_n], _f(blob, at + sh_o + 16 * sh_n + 4, 3))
    return LocalMap(mesh_id, a, b, c, radius, pitch, max_alt, min_alt, in_links, out_links, mm_links, in_obs,
                    out_obs, shapes, shape_end,
                    {"in_links": in_o, "out_links": out_o, "multi_mesh_links": mm_o, "in_obstacles": io_o,
                     "out_obstacles": oo_o, "shapes": sh_o},
                    end - at)


# Kaim::CAiMesh::LoadAiMesh @d158d0, Kaim::CAiMeshHeader::GetMap @d0e600, `anonymous namespace'::ReadColumnBuffer @d15780 decomp
def read_ai_mesh(blob: bytes) -> AiMesh:
    if blob[:19] != MESH_MAGIC:
        raise KynapseError("not a Kynogon runtime mesh")
    version, self_pointer = _u(blob, 0x14, 2)
    if version != 2 or self_pointer != 0:
        raise KynapseError(f"AI mesh version {version}, pointer {self_pointer:#x}")
    (mesh_id, inv, pitch, r_min, r_max, f_min, f_max, a_max, b_max, radius, col_at, nb_n,
     nb_at) = struct.unpack_from("<I6fIIfIII", blob, 0x1C)
    if nb_n:
        raise KynapseError(f"AI mesh with {nb_n} neighbour mesh infos")
    count = a_max * b_max
    offsets = list(_u(blob, col_at, count + 1))
    columns: list[Column] = []
    for i in range(count):
        at = offsets[i]
        n = _u(blob, at)[0]
        headers = [ColumnHeader(_u(blob, at + 4 + 12 * k)[0], *_f(blob, at + 8 + 12 * k, 2)) for k in range(n)]
        end = _u(blob, at + 4 + 12 * n)[0] if n else None
        ends = [h.lm for h in headers[1:]] + ([end] if end is not None else [])
        columns.append(Column(headers, end, [read_local_map(blob, h.lm, e) for h, e in zip(headers, ends)]))
    if offsets[count] + 4 != len(blob):
        raise KynapseError(f"AI mesh ends at {len(blob)}, its last word at {offsets[count]}")
    return AiMesh(blob[19:20], version, self_pointer, mesh_id, inv, pitch, r_min, r_max, f_min, f_max, a_max, b_max,
                  radius, col_at, offsets, nb_n, nb_at, columns, _u(blob, offsets[count])[0], len(blob))


# Kaim::Mpd::CConcreteSlot::MapPointersLoaded @d0d850, Kaim::Mpd::CGraphManagerContext::FinalizeSlotFixing @d03180 decomp
def read_slot(data: bytes, start: int, entry: Entry, node_size: int, edge_size: int, ai_meshes: bool) -> Slot:
    n_nodes, n_edges = _u(data, start, 2)
    at = start + SLOT_HEADER
    nodes = []
    for i in range(n_nodes):
        p = at + node_size * i
        uid, x, y, z, abstract, next_copy, first_out = struct.unpack_from("<I3f3I", data, p)
        nodes.append(Node(uid, x, y, z, abstract, next_copy, first_out, data[p + 28:p + node_size]))
    at += node_size * n_nodes
    edges = [Edge(*_u(data, at + edge_size * i, 3)) for i in range(n_edges)]
    at += edge_size * n_edges
    end = start + entry.size
    if not ai_meshes:
        if at != end:
            raise KynapseError(f"entry {entry.unique_id}: {end - at} bytes after the edges")
        return Slot(entry, nodes, edges, None, 0, None)
    back, tail = _u(data, end - 8, 2)
    mesh_at = end - 8 - back
    if mesh_at != at:
        raise KynapseError(f"entry {entry.unique_id}: AI mesh at {mesh_at - start}, edges end at {at - start}")
    return Slot(entry, nodes, edges, read_ai_mesh(data[mesh_at:end - 8]), mesh_at - start, (back, tail))


# Kaim::Mpd::CGraphManagerContext::VersionHeaderUpdate @d019d0, HeaderUpdate @d01a90, IndexUpdate @d01d60, PODIndexUpdate @d02020 decomp
def read(data: bytes) -> Hpd:
    if data[:12] != MAGIC:
        raise KynapseError("not a Kynogon HPD")
    (version,) = _u(data, 12)
    file_version, n_entries, project_type = _u(data, HEADER_AT, 3)
    if version != 2 or file_version != 2:
        raise KynapseError(f"HPD version {version}, header version {file_version}")
    origin = _f(data, 0x1C, 3)
    (edge_length,) = _f(data, 0x28)
    node_data = [DataDesc(*_u(data, 0x2C + 12 * i, 3)) for i in range(4)]
    edge_data = [DataDesc(*_u(data, 0x5C + 12 * i, 3)) for i in range(4)]
    node_size, edge_size, ai_meshes, n_pod = _u(data, 0x8C, 4)
    entries = []
    for i in range(n_entries):
        p = ENTRY_AT + ENTRY_SIZE * i
        uid, *box, level, size, offset, tag1, tag2 = struct.unpack_from("<I6f5I", data, p)
        entries.append(Entry(uid, *box, level, size, offset, tag1, tag2))
    pod_at = ENTRY_AT + ENTRY_SIZE * n_entries
    pods = [struct.unpack_from("<IHH", data, pod_at + 8 * i) for i in range(n_pod)]
    base = pod_at + 8 * n_pod
    slots = []
    for entry in entries:
        if entry.level != 0:
            raise KynapseError(f"entry {entry.unique_id}: abstract level {entry.level}")
        slots.append(read_slot(data, base + entry.offset, entry, node_size, edge_size, bool(ai_meshes)))
    if base + max((e.offset + e.size for e in entries), default=0) != len(data):
        raise KynapseError("bytes after the last entry")
    return Hpd(version, file_version, project_type, origin, edge_length, node_data, edge_data, node_size, edge_size,
               ai_meshes, pods, entries, slots)


class Canvas:
    def __init__(self, size: int) -> None:
        self.data = bytearray(size)
        self.covered = bytearray(size)

    def put(self, at: int, raw: bytes) -> None:
        if any(self.covered[at:at + len(raw)]):
            raise KynapseError(f"bytes written twice at {at}")
        self.data[at:at + len(raw)] = raw
        self.covered[at:at + len(raw)] = b"\x01" * len(raw)

    def uncovered(self) -> list[tuple[int, int]]:
        out, start = [], None
        for i, c in enumerate(self.covered):
            if not c and start is None:
                start = i
            elif c and start is not None:
                out.append((start, i))
                start = None
        if start is not None:
            out.append((start, len(self.covered)))
        return out


def _vec_bytes(points) -> bytes:
    return b"".join(struct.pack("<3f", *p) for p in points)


def _link_bytes(link: Link) -> bytes:
    raw = struct.pack("<6f2I", *link.p1, *link.p2, link.lm, link.lm_size)
    return raw + struct.pack("<3f", *link.mask) if isinstance(link, MultiMeshLink) else raw


def _write_map(out: Canvas, base: int, m: LocalMap) -> None:
    o = m.offsets
    out.put(base, struct.pack("<4I4f12I", m.mesh_id, m.a, m.b, m.c, m.radius, m.pitch, m.max_alt, m.min_alt,
                              len(m.in_links), o["in_links"], len(m.out_links), o["out_links"],
                              len(m.multi_mesh_links), o["multi_mesh_links"], len(m.in_obstacles),
                              o["in_obstacles"], len(m.out_obstacles), o["out_obstacles"], len(m.shapes),
                              o["shapes"]))
    for links, key in ((m.in_links, "in_links"), (m.out_links, "out_links"), (m.multi_mesh_links, "multi_mesh_links")):
        for i, link in enumerate(links):
            out.put(base + o[key] + len(_link_bytes(link)) * i, _link_bytes(link))
    for polys, key in ((m.in_obstacles, "in_obstacles"), (m.out_obstacles, "out_obstacles")):
        if not polys:
            continue
        at = o[key] + 4 * (len(polys) + 1)
        table = [at]
        for poly in polys:
            at += 12 * len(poly)
            table.append(at)
        out.put(base + o[key], struct.pack(f"<{len(table)}I", *table))
        for poly, start in zip(polys, table):
            out.put(base + start, _vec_bytes(poly))
    if m.shapes:
        for i, shape in enumerate(m.shapes):
            out.put(base + o["shapes"] + 16 * i, struct.pack("<I3f", shape.first_offset, *shape.orientation))
            out.put(base + shape.first_offset, _vec_bytes(shape.points))
        out.put(base + o["shapes"] + 16 * len(m.shapes), struct.pack("<I3f", m.shape_end[0], *m.shape_end[1]))


def _write_mesh(out: Canvas, base: int, mesh: AiMesh) -> None:
    out.put(base, MESH_MAGIC + mesh.pad + struct.pack("<2I", mesh.version, mesh.self_pointer))
    out.put(base + 0x1C, struct.pack("<I6fIIfIII", mesh.mesh_id, mesh.inv_local_map_size, mesh.pitch, mesh.right_min,
                                     mesh.right_max, mesh.front_min, mesh.front_max, mesh.a_max, mesh.b_max,
                                     mesh.radius, mesh.column_table_at, mesh.neighbour_count, mesh.neighbour_offset))
    out.put(base + mesh.column_table_at, struct.pack(f"<{len(mesh.column_offsets)}I", *mesh.column_offsets))
    for at, column in zip(mesh.column_offsets, mesh.columns):
        out.put(base + at, struct.pack("<I", len(column.headers)))
        for k, h in enumerate(column.headers):
            out.put(base + at + 4 + 12 * k, struct.pack("<I2f", h.lm, h.alt_min, h.alt_max))
        if column.end is not None:
            out.put(base + at + 4 + 12 * len(column.headers), struct.pack("<I", column.end))
        for h, m in zip(column.headers, column.maps):
            _write_map(out, base + h.lm, m)
    out.put(base + mesh.column_offsets[-1], struct.pack("<I", mesh.tail))


def write(hpd: Hpd, canvas: Canvas | None = None) -> Canvas:
    pod_at = ENTRY_AT + ENTRY_SIZE * len(hpd.entries)
    base = pod_at + 8 * len(hpd.pod_entries)
    size = base + max((e.offset + e.size for e in hpd.entries), default=0)
    out = canvas or Canvas(size)
    out.put(0, MAGIC + struct.pack("<I", hpd.version))
    out.put(HEADER_AT, struct.pack("<3I4f", hpd.file_version, len(hpd.entries), hpd.project_type, *hpd.origin,
                                   hpd.edge_length))
    for i, d in enumerate(hpd.node_data):
        out.put(0x2C + 12 * i, struct.pack("<3I", d.id, d.offset, d.size))
    for i, d in enumerate(hpd.edge_data):
        out.put(0x5C + 12 * i, struct.pack("<3I", d.id, d.offset, d.size))
    out.put(0x8C, struct.pack("<4I", hpd.node_size, hpd.edge_size, hpd.ai_meshes, len(hpd.pod_entries)))
    for i, e in enumerate(hpd.entries):
        out.put(ENTRY_AT + ENTRY_SIZE * i, struct.pack("<I6f5I", e.unique_id, e.x_min, e.x_max, e.y_min, e.y_max,
                                                      e.z_min, e.z_max, e.level, e.size, e.offset, e.tag1, e.tag2))
    for i, pod in enumerate(hpd.pod_entries):
        out.put(pod_at + 8 * i, struct.pack("<IHH", *pod))
    for slot in hpd.slots:
        start = base + slot.entry.offset
        out.put(start, struct.pack("<2I", len(slot.nodes), len(slot.edges)))
        at = start + SLOT_HEADER
        for n in slot.nodes:
            out.put(at, struct.pack("<I3f3I", n.unique_id, n.x, n.y, n.z, n.abstract, n.next_copy, n.first_out) + n.extra)
            at += hpd.node_size
        for e in slot.edges:
            out.put(at, struct.pack("<3I", e.cost, e.p1, e.p2))
            at += hpd.edge_size
        if slot.mesh:
            _write_mesh(out, start + slot.mesh_at, slot.mesh)
            out.put(start + slot.entry.size - 8, struct.pack("<2I", *slot.trailer))
    return out


USAGE = """python -m dv2lib.kynapse info <file.hpd>...
    python -m dv2lib.kynapse round-trip <file.hpd>..."""


def main(argv: list[str]) -> int:
    from pathlib import Path

    if argv[:1] == ["info"] and len(argv) > 1:
        for path in argv[1:]:
            hpd = read(Path(path).read_bytes())
            for slot in hpd.slots:
                mesh = slot.mesh
                maps = sum(len(c.maps) for c in mesh.columns) if mesh else 0
                print(f"{path}: {len(slot.nodes)} nodes, {len(slot.edges)} edges, {len(hpd.pod_entries)} path objects, "
                      f"{maps} local maps" + (f" in {mesh.a_max}x{mesh.b_max} cells of {mesh.local_map_size:g} m" if mesh else ""))
        return 0
    if argv[:1] == ["round-trip"] and len(argv) > 1:
        bad = 0
        for path in argv[1:]:
            data = Path(path).read_bytes()
            try:
                out = write(read(data))
            except KynapseError as e:
                bad += 1
                print(f"{path}: {e}")
                continue
            same = bytes(out.data) == data and not out.uncovered()
            bad += not same
            print(f"{path}: {'identical' if same else 'differs, uncovered ' + str(out.uncovered()[:3])}")
        return 1 if bad else 0
    print(USAGE)
    return 2


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv[1:]))
