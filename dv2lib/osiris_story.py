from __future__ import annotations

import struct
from dataclasses import dataclass, field

XOR_KEY = 0xAD


class Buf:
    def __init__(self, data: bytes) -> None:
        self.d = data
        self.p = 0
        self.key = 0
        self.big = False
        self.ver = (1, 4)

    def cstr(self) -> str:
        out = bytearray()
        while True:
            c = self.d[self.p] ^ self.key
            self.p += 1
            if c == 0:
                break
            out.append(c)
        return out.decode("latin-1")

    def raw(self, n: int) -> bytes:
        b = self.d[self.p:self.p + n]
        self.p += n
        return b

    def u8(self) -> int:
        v = self.d[self.p]
        self.p += 1
        return v

    def _n(self, n: int, fmt: str) -> int:
        v = struct.unpack((">" if self.big else "<") + fmt,
                          self.d[self.p:self.p + n])[0]
        self.p += n
        return v

    def u32(self) -> int:
        return self._n(4, "I")

    def i32(self) -> int:
        return self._n(4, "i")

    def f32(self) -> float:
        v = struct.unpack((">" if self.big else "<") + "f",
                          self.d[self.p:self.p + 4])[0]
        self.p += 4
        return v

    def eof(self) -> bool:
        return self.p >= len(self.d)


@dataclass
class Header:
    lead: int
    banner: str
    major: int
    minor: int
    big_endian: int
    fourth: int
    version_block: bytes
    debug_flags: int
    types: list = field(default_factory=list)


VER_TYPE_MAP = (1, 5)
VER_QUERY = (1, 6)


# COsiris::_ReadHeader @d61c90 decomp
def read_header(b: Buf) -> Header:
    lead = b.u8()
    banner = b.cstr()
    major, minor, endian, fourth = b.u8(), b.u8(), b.u8(), b.u8()
    b.big = endian == 1
    b.ver = (major, minor)
    vblock = b"" if (major < 2 and minor < 2) else b.raw(0x80)
    flags = 0 if (major < 2 and minor < 3) else b.u32()
    if major > 1 or minor > 3:
        b.key = XOR_KEY
    types = []
    if b.ver >= VER_TYPE_MAP:
        types = [(b.cstr(), b.u8()) for _ in range(b.u32())]
    return Header(lead, banner, major, minor, endian, fourth, vblock, flags, types)


@dataclass
class DivObject:
    name: str
    type_id: int
    key: tuple


# COsiris::_ReadDIVObjects @d62760 decomp
def read_div_objects(b: Buf) -> list:
    n = b.u32()
    out = []
    for _ in range(n):
        name = b.cstr()
        t = b.u8()
        k = (b.u32(), b.u32(), b.u32(), b.u32())
        out.append(DivObject(name, t, k))
    return out


VALUE_TYPES = {0: "unknown", 1: "INTEGER", 2: "REAL", 3: "STRING"}

def type_names_from_objects(objs) -> dict:
    m = {}
    for o in objs:
        m.setdefault(o.type_id, set()).add(o.name.split("_")[0])
    return {t: sorted(v)[0] if len(v) == 1 else "/".join(sorted(v))
            for t, v in m.items()}


@dataclass
class Function:
    a: int
    b: int
    c: int
    d: int
    type_id: int
    key: tuple
    name: str
    out_mask: int
    params: list = field(default_factory=list)
    outs: list = field(default_factory=list)

    @property
    def arity(self) -> int:
        return len(self.params)


def read_signature(b: Buf) -> tuple:
    name = b.cstr()
    nmask = b.u32()
    mask = b.raw(nmask)
    cnt = b.u8()
    params = [b.u32() for _ in range(cnt)]
    outs = [bool(mask[i // 8] & (0x80 >> (i % 8))) for i in range(cnt)]
    return name, mask, params, outs


# COsiris::_ReadFunctions @d62840 decomp
def read_functions(b: Buf) -> list:
    n = b.u32()
    out = []
    for _ in range(n):
        a, bb, c, e = b.u32(), b.u32(), b.u32(), b.u32()
        t = b.u8()
        k = (b.u32(), b.u32(), b.u32(), b.u32())
        name, mask, params, outs = read_signature(b)
        f = Function(a, bb, c, e, t, k, name, mask, params)
        f.outs = outs
        out.append(f)
    return out


TYPE_ALIAS_MIN, TYPE_ALIAS_MAX = 4, 17

NODE_TYPES = {
    1: "Database", 2: "Proc", 3: "DivQuery", 4: "And",
    5: "NotAnd", 6: "RelOp", 7: "Rule", 8: "InternalQuery",
}

REL_OPS = {0: "<", 1: "<=", 2: ">", 3: ">=", 4: "==", 5: "!="}


@dataclass
class Value:
    type_id: int = 0
    value: object = None
    is_valid: bool = False
    out_param: bool = False
    is_a_type: bool = False
    index: int = 0
    unused: bool = False
    adapted: bool = False
    is_variable: bool = False
    name: str = ""
    handle: bool = False

def read_value(b: Buf) -> Value:
    v = Value()
    tag = b.u8()
    if tag == ord("1"):
        v.handle = True
        v.type_id = b.u32()
        v.value = b.i32()
    elif tag == ord("0"):
        v.type_id = b.u32()
        written = v.type_id
        dos1alias = False
        if TYPE_ALIAS_MIN <= written <= TYPE_ALIAS_MAX:
            written, dos1alias = 3, True
        if written == 0:
            pass
        elif written == 1:
            v.value = b.i32()
        elif written == 2:
            v.value = b.f32()
        elif written == 3:
            if dos1alias or b.u8() > 0:
                v.value = b.cstr()
        else:
            v.value = b.cstr()
    else:
        raise ValueError(f"unrecognised value tag {tag!r} at 0x{b.p - 1:x}")
    return v


def read_typed_value(b: Buf) -> Value:
    v = read_value(b)
    v.is_valid = b.u8() != 0
    v.out_param = b.u8() != 0
    v.is_a_type = b.u8() != 0
    return v


def read_variable(b: Buf) -> Value:
    v = read_typed_value(b)
    v.index = struct.unpack("b", bytes([b.u8()]))[0]
    v.unused = b.u8() != 0
    v.adapted = b.u8() != 0
    v.is_variable = True
    return v


def read_tuple(b: Buf) -> list:
    out = []
    for _ in range(b.u8()):
        idx = b.u8()
        out.append((idx, read_value(b)))
    return out


@dataclass
class Call:
    name: str
    params: list
    negate: bool
    goal_id: int
    has_params: int = 0

def read_call(b: Buf) -> Call:
    name = b.cstr()
    params, negate, has = [], False, 0
    if name:
        has = b.u8()
        if has > 0:
            for _ in range(b.u8()):
                kind = b.u8()
                params.append(read_variable(b) if kind == 1 else read_typed_value(b))
        negate = b.u8() != 0
    return Call(name, params, negate, b.i32(), has)


def read_call_list(b: Buf) -> list:
    return [read_call(b) for _ in range(b.u32())]


@dataclass
class NodeEntry:
    node: int
    entry_point: int
    goal: int


def read_node_entry(b: Buf) -> NodeEntry:
    return NodeEntry(b.u32(), b.u32(), b.u32())


@dataclass
class Node:
    index: int
    type_id: int
    db: int
    name: str
    n_params: int
    fields: dict = field(default_factory=dict)

    @property
    def type_name(self) -> str:
        return NODE_TYPES.get(self.type_id, f"type{self.type_id}")


def _read_node_common(b: Buf, n: Node) -> None:
    n.db = b.u32()
    n.name = b.cstr()
    n.n_params = b.u8() if n.name else 0


def _read_tree_node(b: Buf, n: Node) -> None:
    _read_node_common(b, n)
    n.fields["next"] = read_node_entry(b)


def _read_rel_node(b: Buf, n: Node) -> None:
    _read_tree_node(b, n)
    n.fields["parent"] = b.u32()
    n.fields["adapter"] = b.u32()
    n.fields["rel_db"] = b.u32()
    n.fields["rel_join"] = read_node_entry(b)
    n.fields["rel_indirection"] = b.u8()


# COsiris::_ReadReteNodes @d61f40 decomp
def read_node(b: Buf) -> Node:
    t = b.u8()
    if t not in NODE_TYPES:
        raise ValueError(f"invalid rete node type 0x{t:02x} at 0x{b.p - 1:x}")
    n = Node(b.u32(), t, 0, "", 0)
    if t in (1, 2):
        _read_node_common(b, n)
        n.fields["referenced_by"] = [read_node_entry(b) for _ in range(b.u32())]
    elif t in (3, 8):
        _read_node_common(b, n)
    elif t in (4, 5):
        _read_tree_node(b, n)
        n.fields["left_parent"] = b.u32()
        n.fields["right_parent"] = b.u32()
        n.fields["left_adapter"] = b.u32()
        n.fields["right_adapter"] = b.u32()
        n.fields["left_db"] = b.u32()
        n.fields["left_join"] = read_node_entry(b)
        n.fields["left_indirection"] = b.u8()
        n.fields["right_db"] = b.u32()
        n.fields["right_join"] = read_node_entry(b)
        n.fields["right_indirection"] = b.u8()
    elif t == 6:
        _read_rel_node(b, n)
        n.fields["left_index"] = struct.unpack("b", bytes([b.u8()]))[0]
        n.fields["right_index"] = struct.unpack("b", bytes([b.u8()]))[0]
        n.fields["left_value"] = read_value(b)
        n.fields["right_value"] = read_value(b)
        n.fields["rel_op"] = b.i32()
    elif t == 7:
        _read_rel_node(b, n)
        n.fields["calls"] = read_call_list(b)
        variables = []
        for _ in range(b.u8()):
            kind = b.u8()
            if kind != 1:
                raise ValueError(f"illegal rule variable type {kind} at 0x{b.p - 1:x}")
            v = read_variable(b)
            if v.adapted:
                v.name = f"_Var{len(variables) + 1}"
            variables.append(v)
        n.fields["variables"] = variables
        n.fields["line"] = b.u32()
        n.fields["is_query"] = b.u8() != 0 if b.ver >= VER_QUERY else False
    return n


def read_nodes(b: Buf) -> list:
    return [read_node(b) for _ in range(b.u32())]


@dataclass
class Adapter:
    index: int
    constants: list
    logical_indices: list
    logical_to_physical: dict


def read_adapters(b: Buf) -> list:
    out = []
    for _ in range(b.u32()):
        index = b.u32()
        constants = read_tuple(b)
        logical = [struct.unpack("b", bytes([b.u8()]))[0] for _ in range(b.u8())]
        l2p = {}
        for _ in range(b.u8()):
            k = b.u8()
            l2p[k] = b.u8()
        out.append(Adapter(index, constants, logical, l2p))
    return out


@dataclass
class Database:
    index: int
    params: list
    facts: list


def read_databases(b: Buf) -> list:
    out = []
    for _ in range(b.u32()):
        index = b.u32()
        params = [b.u32() for _ in range(b.u8())]
        facts = []
        for _ in range(b.u32()):
            facts.append([read_value(b) for _ in range(b.u8())])
        out.append(Database(index, params, facts))
    return out


@dataclass
class Goal:
    index: int
    name: str
    combination: int
    parents: list
    children: list
    flags: int
    init: list
    exit: list


def read_goals(b: Buf) -> list:
    out = []
    for _ in range(b.u32()):
        index = b.u32()
        name = b.cstr()
        comb = b.u8()
        parents = [b.u32() for _ in range(b.u32())]
        children = [b.u32() for _ in range(b.u32())]
        flags = b.u8()
        out.append(Goal(index, name, comb, parents, children, flags,
                        read_call_list(b), read_call_list(b)))
    return out


@dataclass
class Story:
    header: Header
    objects: list
    functions: list
    nodes: list
    adapters: list
    databases: list
    goals: list
    global_actions: list
    consumed: int
    size: int

    @property
    def clean(self) -> bool:
        return self.consumed == self.size

    def type_names(self) -> dict:
        tn = dict(VALUE_TYPES)
        tn.update(type_names_from_objects(self.objects))
        return tn


# LoadTaskData::GetVersion @ec7860 decomp
def read_story(data: bytes) -> Story:
    b = Buf(data)
    h = read_header(b)
    objs = read_div_objects(b)
    funcs = read_functions(b)
    nodes = read_nodes(b)
    adapters = read_adapters(b)
    dbs = read_databases(b)
    goals = read_goals(b)
    globals_ = read_call_list(b)
    return Story(h, objs, funcs, nodes, adapters, dbs, goals, globals_,
                 b.p, len(b.d))


def rule_goals(nodes) -> dict:
    by_index = {n.index: n for n in nodes}
    out = {}
    for n in nodes:
        entries = []
        for k in ("next", "rel_join", "left_join", "right_join"):
            if k in n.fields:
                entries.append(n.fields[k])
        entries += n.fields.get("referenced_by", [])
        for e in entries:
            if e.node and e.goal and by_index.get(e.node) is not None:
                if by_index[e.node].type_id == 7:
                    out[e.node] = e.goal
    return out


class StoryIndex:
    def __init__(self, st: "Story"):
        self.story = st
        self.by_index = {n.index: n for n in st.nodes}
        self.goal_of = rule_goals(st.nodes)
        self.names = {g.index: g.name for g in st.goals}
        self.goal_by_index = {g.index: g for g in st.goals}
        self.rules = [n for n in st.nodes if n.type_id == 7]
        self.rules_of = {}
        for r in self.rules:
            self.rules_of.setdefault(self.goal_of.get(r.index, 0),
                                     []).append(r)
        for group in self.rules_of.values():
            group.sort(key=lambda n: n.fields["line"])

    def unattributed(self) -> int:
        return sum(1 for r in self.rules if r.index not in self.goal_of)
