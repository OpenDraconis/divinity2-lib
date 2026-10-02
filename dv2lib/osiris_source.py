from __future__ import annotations

import decimal
import struct
from dataclasses import dataclass, field

from . import codec
from .osiris_story import (REL_OPS, Adapter, Node, Story, StoryIndex, Value,
                           read_story)

SECTION_HEADER = "//Osiris Header"
SECTION_DEFINITIONS = "//Osiris Definitions"
SECTION_GOALS = "//Osiris story code"

DECLARATION = {1: "event", 2: "query", 3: "call", 6: "sysquery", 7: "syscall"}

COMBINATION = {1: "AND", 0: "OR"}


def real(x: float) -> str:
    s = "0.0"
    for p in range(1, 10):
        s = f"{x:.{p}g}"
        if struct.unpack("f", struct.pack("f", float(s)))[0] == x:
            break
    if "e" in s or "E" in s:
        s = format(decimal.Decimal(s), "f")
    if "." not in s:
        s += ".0"
    return s


@dataclass
class Tuple:
    logical: dict = field(default_factory=dict)
    physical: list = field(default_factory=list)


def adapt(adapter: Adapter, columns: Tuple) -> Tuple:
    out = Tuple()
    constants = dict(adapter.constants)
    for i, index in enumerate(adapter.logical_indices):
        if index != -1:
            v = columns.logical.get(index)
        else:
            v = constants.get(i)
        if v is None:
            v = Value(type_id=0, is_variable=True, unused=True)
        out.physical.append(v)
    mapped = set()
    for logical, physical in adapter.logical_to_physical.items():
        out.logical[logical] = out.physical[physical]
        mapped.add(physical)
    for i, index in enumerate(adapter.logical_indices):
        if index != -1 and i not in mapped and i not in out.logical:
            out.logical[i] = out.physical[i]
    return out


class Decompiler:
    def __init__(self, story: Story):
        self.st = story
        self.idx = StoryIndex(story)
        self.by = self.idx.by_index
        self.types = story.type_names()
        self.adapters = {a.index: a for a in story.adapters}
        self.user_procs = {f.name for f in story.functions if f.type_id == 5}
        self.signatures = {f.name: f.params for f in story.functions}


    def literal(self, v: Value) -> str:
        t = v.type_id
        if t == 1:
            return str(v.value)
        if t == 2:
            return real(v.value)
        if t == 3:
            return f'"{v.value}"'
        if t == 0 or v.value is None:
            return "_"
        return str(v.value)

    def typed(self, v: Value, name: str, column: int = 0) -> str:
        t = self.types.get(v.type_id or column)
        return f"({t}){name}" if t and (v.type_id or column) else name

    def argument(self, v: Value, bound: set, annotate: bool, column: int) -> str:
        if v.is_variable:
            if v.unused or not v.name:
                return self.typed(v, "_", column) if annotate else "_"
            if v.name in bound:
                return v.name
            bound.add(v.name)
            return self.typed(v, v.name, column)
        return self.literal(v)

    def action_argument(self, v: Value, variables: list) -> str:
        if v.is_variable:
            var = variables[v.index]
            return var.name if var.adapted else "_"
        return self.literal(v)

    def call(self, c, variables: list) -> str:
        if not c.name:
            return "GoalCompleted;"
        args = ", ".join(self.action_argument(p, variables) for p in c.params)
        s = f"{c.name}({args});"
        return "NOT " + s if c.negate else s

    def init_call(self, c) -> str:
        if not c.name:
            return "GoalCompleted;"
        args = ", ".join(self.literal(p) for p in c.params)
        s = f"{c.name}({args});"
        return "NOT " + s if c.negate else s


    def leftmost(self, node: Node) -> Node:
        while True:
            t = node.type_id
            if t in (4, 5):
                node = self.by[node.fields["left_parent"]]
            elif t in (6, 7):
                node = self.by[node.fields["parent"]]
            else:
                return node

    def condition(self, node: Node, columns: Tuple, bound: set) -> str:
        annotate = node.type_id in (1, 2)
        signature = self.signatures.get(node.name, [])
        physical = columns.physical[:node.n_params] if node.n_params else columns.physical
        args = ", ".join(self.argument(v, bound, annotate,
                                       signature[i] if i < len(signature) else 0)
                         for i, v in enumerate(physical))
        return f"{node.name}({args})"

    def conditions(self, node: Node, columns: Tuple, bound: set) -> list:
        t = node.type_id
        f = node.fields
        if t in (1, 2, 3, 8):
            return [self.condition(node, columns, bound)]
        if t in (4, 5):
            left = self.conditions(self.by[f["left_parent"]],
                                   adapt(self.adapters[f["left_adapter"]], columns), bound)
            right_node = self.by[f["right_parent"]]
            right = self.conditions(right_node,
                                    adapt(self.adapters[f["right_adapter"]], columns), bound)
            if t == 5:
                assert len(right) == 1, f"NOT over a join at node {node.index}"
                return left + ["AND", "NOT " + right[0]]
            return left + ["AND"] + right
        if t == 6:
            adapted = adapt(self.adapters[f["adapter"]], columns)
            out = self.conditions(self.by[f["parent"]], adapted, bound)
            li, ri = f["left_index"], f["right_index"]
            left = (self.operand(adapted.logical[li], bound) if li != -1
                    else self.literal(f["left_value"]))
            right = (self.operand(adapted.logical[ri], bound) if ri != -1
                     else self.literal(f["right_value"]))
            return out + ["AND", f"{left} {REL_OPS[f['rel_op']]} {right}"]
        raise ValueError(f"node {node.index} of type {node.type_name} in a condition chain")

    def operand(self, v: Value, bound: set) -> str:
        if v.is_variable:
            return v.name or "_"
        return self.literal(v)

    def rule(self, r: Node) -> list:
        variables = r.fields["variables"]
        columns = Tuple({i: v for i, v in enumerate(variables)}, list(variables))
        head = self.leftmost(r)
        kind = "PROC" if head.type_id == 2 and head.name in self.user_procs else "IF"
        bound: set = set()
        parent = self.by[r.fields["parent"]]
        lines = [kind]
        lines += self.conditions(parent, adapt(self.adapters[r.fields["adapter"]], columns), bound)
        lines.append("THEN")
        lines += [self.call(c, variables) for c in r.fields["calls"]]
        return lines


    def goal_title(self, g) -> str:
        return f'Goal({g.index}).Title("{g.name}");'

    def goal_body(self, g) -> list:
        out = [f"Goal({g.index})", "{", "INIT", "{"]
        out += [self.init_call(c) for c in g.init]
        out += ["}", "KB", "{"]
        for r in self.idx.rules_of.get(g.index, []):
            out += self.rule(r)
            out.append("")
        out += ["}", "EXIT", "{"]
        out += [self.init_call(c) for c in g.exit]
        out += ["}", "}"]
        return out

    def goal_tree(self, g) -> list:
        out = [f"Goal({g.index}).SubGoal({c});" for c in g.children]
        out.append(f"Goal({g.index}).SubGoals({COMBINATION.get(g.combination, 'OR')});")
        return out

    def goal(self, g) -> str:
        return "\n".join([self.goal_title(g)] + self.goal_body(g)) + "\n"


    def declaration(self, f) -> str:
        kw = DECLARATION[f.type_id]
        params = []
        for i, (t, out) in enumerate(zip(f.params, f.outs), 1):
            p = f"({self.types.get(t, f'type{t}')})_Arg{i}"
            if kw in ("query", "sysquery"):
                p = ("[out]" if out else "[in]") + p
            params.append(p)
        return f"{kw} {f.name}({','.join(params)}) ({','.join(str(k) for k in f.key)})"

    def version(self) -> str:
        return self.st.header.version_block.split(b"\0", 1)[0].decode("latin-1")

    def header(self) -> list:
        out = [SECTION_HEADER]
        if self.version():
            out.append(f'version "{self.version()}"')
        out += [f"type {{{name}, {t}}}" for t, name in sorted(self.types.items()) if t >= 4]
        out += [self.declaration(f) for f in self.st.functions if f.type_id in DECLARATION]
        return out

    def definitions(self) -> list:
        return [SECTION_DEFINITIONS] + [
            f"object {{{o.name},{o.type_id},({','.join(str(k) for k in o.key)})}}"
            for o in self.st.objects]

    def source(self) -> str:
        goals = sorted(self.st.goals, key=lambda g: g.index)
        lines = self.header() + [""] + self.definitions() + ["", SECTION_GOALS]
        for g in goals:
            lines += [self.goal_title(g)] + self.goal_body(g) + [""]
        for g in goals:
            lines += self.goal_tree(g)
        return "\n".join(lines) + "\n"
