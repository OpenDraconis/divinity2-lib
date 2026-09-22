"""Write an Osiris story back to bytes, in the version the game reads."""

from __future__ import annotations

import datetime
import struct
from dataclasses import replace

from .osiris_story import (VER_QUERY, VER_TYPE_MAP, XOR_KEY, Header, Story,
                           TYPE_ALIAS_MAX, TYPE_ALIAS_MIN, Value)


class Out:
    """`COsiSmartBuf`, writing side."""

    def __init__(self, big: bool = False) -> None:
        self.b = bytearray()
        self.key = 0
        self.big = big

    def cstr(self, s: str) -> None:
        for c in s.encode("latin-1", errors="replace"):
            self.b.append(c ^ self.key)
        self.b.append(self.key)

    def raw(self, data: bytes) -> None:
        self.b += data

    def u8(self, v: int) -> None:
        self.b.append(v & 0xFF)

    def i8(self, v: int) -> None:
        self.b += struct.pack("b", v)

    def _n(self, fmt: str, v) -> None:
        self.b += struct.pack((">" if self.big else "<") + fmt, v)

    def u32(self, v: int) -> None:
        self._n("I", v)

    def i32(self, v: int) -> None:
        self._n("i", v)

    def f32(self, v: float) -> None:
        self._n("f", v)

    def flag(self, v: bool) -> None:
        self.u8(1 if v else 0)


def write_header(o: Out, h: Header) -> None:
    o.u8(h.lead)
    o.cstr(h.banner)
    o.u8(h.major)
    o.u8(h.minor)
    o.u8(h.big_endian)
    o.u8(h.fourth)
    ver = (h.major, h.minor)
    if not (h.major < 2 and h.minor < 2):
        o.raw(h.version_block[:0x80].ljust(0x80, b"\0"))
    if not (h.major < 2 and h.minor < 3):
        o.u32(h.debug_flags)
    if h.major > 1 or h.minor > 3:
        o.key = XOR_KEY
    if ver >= VER_TYPE_MAP:
        o.u32(len(h.types))
        for name, type_id in h.types:
            o.cstr(name)
            o.u8(type_id)


def write_key(o: Out, key) -> None:
    for k in key:
        o.u32(k)


def write_div_objects(o: Out, objs) -> None:
    o.u32(len(objs))
    for x in objs:
        o.cstr(x.name)
        o.u8(x.type_id)
        write_key(o, x.key)


def write_functions(o: Out, funcs) -> None:
    o.u32(len(funcs))
    for f in funcs:
        o.u32(f.a)
        o.u32(f.b)
        o.u32(f.c)
        o.u32(f.d)
        o.u8(f.type_id)
        write_key(o, f.key)
        o.cstr(f.name)
        o.u32(len(f.out_mask))
        o.raw(f.out_mask)
        o.u8(len(f.params))
        for p in f.params:
            o.u32(p)


def write_value(o: Out, v: Value) -> None:
    if v.handle:
        o.u8(ord("1"))
        o.u32(v.type_id)
        o.i32(v.value)
        return
    o.u8(ord("0"))
    o.u32(v.type_id)
    t = v.type_id
    if TYPE_ALIAS_MIN <= t <= TYPE_ALIAS_MAX:
        o.cstr(v.value or "")
    elif t == 0:
        pass
    elif t == 1:
        o.i32(v.value)
    elif t == 2:
        o.f32(v.value)
    elif t == 3:
        o.u8(1 if v.value is not None else 0)
        if v.value is not None:
            o.cstr(v.value)
    else:
        o.cstr(v.value or "")


def write_typed_value(o: Out, v: Value) -> None:
    write_value(o, v)
    o.flag(v.is_valid)
    o.flag(v.out_param)
    o.flag(v.is_a_type)


def write_variable(o: Out, v: Value) -> None:
    write_typed_value(o, v)
    o.i8(v.index)
    o.flag(v.unused)
    o.flag(v.adapted)


def write_tuple(o: Out, pairs) -> None:
    o.u8(len(pairs))
    for idx, v in pairs:
        o.u8(idx)
        write_value(o, v)


def write_call(o: Out, c) -> None:
    o.cstr(c.name)
    if c.name:
        has = c.has_params if c.has_params or not c.params else 1
        o.u8(has)
        if has > 0:
            o.u8(len(c.params))
            for p in c.params:
                o.u8(1 if p.is_variable else 0)
                if p.is_variable:
                    write_variable(o, p)
                else:
                    write_typed_value(o, p)
        o.flag(c.negate)
    o.i32(c.goal_id)


def write_call_list(o: Out, calls) -> None:
    o.u32(len(calls))
    for c in calls:
        write_call(o, c)


def write_entry(o: Out, e) -> None:
    o.u32(e.node)
    o.u32(e.entry_point)
    o.u32(e.goal)


def _write_node_common(o: Out, n) -> None:
    o.u32(n.db)
    o.cstr(n.name)
    if n.name:
        o.u8(n.n_params)


def _write_tree_node(o: Out, n) -> None:
    _write_node_common(o, n)
    write_entry(o, n.fields["next"])


def _write_rel_node(o: Out, n) -> None:
    _write_tree_node(o, n)
    f = n.fields
    o.u32(f["parent"])
    o.u32(f["adapter"])
    o.u32(f["rel_db"])
    write_entry(o, f["rel_join"])
    o.u8(f["rel_indirection"])


def write_node(o: Out, n, ver) -> None:
    o.u8(n.type_id)
    o.u32(n.index)
    f = n.fields
    t = n.type_id
    if t in (1, 2):
        _write_node_common(o, n)
        o.u32(len(f["referenced_by"]))
        for e in f["referenced_by"]:
            write_entry(o, e)
    elif t in (3, 8):
        _write_node_common(o, n)
    elif t in (4, 5):
        _write_tree_node(o, n)
        o.u32(f["left_parent"])
        o.u32(f["right_parent"])
        o.u32(f["left_adapter"])
        o.u32(f["right_adapter"])
        o.u32(f["left_db"])
        write_entry(o, f["left_join"])
        o.u8(f["left_indirection"])
        o.u32(f["right_db"])
        write_entry(o, f["right_join"])
        o.u8(f["right_indirection"])
    elif t == 6:
        _write_rel_node(o, n)
        o.i8(f["left_index"])
        o.i8(f["right_index"])
        write_value(o, f["left_value"])
        write_value(o, f["right_value"])
        o.i32(f["rel_op"])
    elif t == 7:
        _write_rel_node(o, n)
        write_call_list(o, f["calls"])
        o.u8(len(f["variables"]))
        for v in f["variables"]:
            o.u8(1)
            write_variable(o, v)
        o.u32(f["line"])
        if ver >= VER_QUERY:
            o.flag(f.get("is_query", False))
    else:
        raise ValueError(f"node type {t}")


def write_nodes(o: Out, nodes, ver) -> None:
    o.u32(len(nodes))
    for n in nodes:
        write_node(o, n, ver)


def write_adapters(o: Out, adapters) -> None:
    o.u32(len(adapters))
    for a in adapters:
        o.u32(a.index)
        write_tuple(o, a.constants)
        o.u8(len(a.logical_indices))
        for i in a.logical_indices:
            o.i8(i)
        o.u8(len(a.logical_to_physical))
        for k, v in a.logical_to_physical.items():
            o.u8(k)
            o.u8(v)


def write_databases(o: Out, dbs) -> None:
    o.u32(len(dbs))
    for d in dbs:
        o.u32(d.index)
        o.u8(len(d.params))
        for p in d.params:
            o.u32(p)
        o.u32(len(d.facts))
        for fact in d.facts:
            o.u8(len(fact))
            for v in fact:
                write_value(o, v)


def write_goals(o: Out, goals) -> None:
    o.u32(len(goals))
    for g in goals:
        o.u32(g.index)
        o.cstr(g.name)
        o.u8(g.combination)
        o.u32(len(g.parents))
        for p in g.parents:
            o.u32(p)
        o.u32(len(g.children))
        for c in g.children:
            o.u32(c)
        o.u8(g.flags)
        write_call_list(o, g.init)
        write_call_list(o, g.exit)


def write_story(st: Story, version: tuple | None = None) -> bytes:
    """The story as bytes."""
    h = st.header
    if version is not None:
        h = replace(h, major=version[0], minor=version[1])
    o = Out(big=h.big_endian == 1)
    write_header(o, h)
    write_div_objects(o, st.objects)
    write_functions(o, st.functions)
    write_nodes(o, st.nodes, (h.major, h.minor))
    write_adapters(o, st.adapters)
    write_databases(o, st.databases)
    write_goals(o, st.goals)
    write_call_list(o, st.global_actions)
    return bytes(o.b)


def banner(version: str = "1.4", when: datetime.datetime | None = None) -> str:
    """`Osiris save file dd. 12/14/10 10:45:12. Version 1.4.`, as Larian's."""
    when = when or datetime.datetime.now()
    return f"Osiris save file dd. {when:%m/%d/%y %H:%M:%S}. Version {version}."


def to_div2(st: Story, template: Header | None = None) -> Story:
    """The story the compiler library wrote, with the game's header."""
    h = st.header
    flags = template.debug_flags if template else h.debug_flags
    lead = template.lead if template else h.lead
    h = replace(h, lead=lead, banner=banner(), major=1, minor=4,
                debug_flags=flags, types=[])
    return replace(st, header=h)
