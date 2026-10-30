from __future__ import annotations

from dataclasses import dataclass, field

from . import binxml

# CGameLogic::GetDialogLanguageRegionName @75d190 decomp, CGameLogic_TranslationSystem::GetLanguageName decomp
LANGUAGES = {"English": "English(US)", "French": "French(France)",
             "Spanish": "Spanish(Spain)", "Portuguese": "English(US)"}


# CGameDialogIO_V20::ReadXML @ad9760 decomp, CGameDialog::RequestAnimations @9bfd10 decomp, CGameDialog::RequestLipsynchAnimations @9bfd70 decomp
def packs(episode: str, name: str, language: str = "English") -> tuple[str, str]:
    folder = f"Win32\\Characters\\{episode}\\Dialogs\\"
    return f"{folder}{name}.dialog", f"{folder}{name}{LANGUAGES.get(language, language)}.dialog"


@dataclass
class Node:
    uid: str
    id: str
    greeting: bool
    npc: bool
    end: bool
    automated: bool
    cue: str = ""
    speaker: str = ""
    links: list[str] = field(default_factory=list)
    links_back: list[str] = field(default_factory=list)
    checks_true: list[str] = field(default_factory=list)
    checks_false: list[str] = field(default_factory=list)
    sets_true: list[str] = field(default_factory=list)
    sets_false: list[str] = field(default_factory=list)
    connections: list["Node"] = field(default_factory=list)


@dataclass
class Dialog:
    name: str
    automated: bool
    flags: dict[str, str]
    nodes: list[Node]
    greetings: list[Node]


def _items(node: binxml.Node) -> list[str]:
    return [(c.text or "").strip() for c in node.children]


def _codes(node: binxml.Node, off: list[str], on: list[str]) -> None:
    for part in node.children:
        if part.name == "false":
            off += _items(part)
        elif part.name == "true":
            on += _items(part)


def _number(text: str | None) -> float:
    try:
        return float(text) if text else 0.0
    except ValueError:
        return 0.0


# CGameDialogIO_V20::ProcessFlag @ad94d0 decomp
def _flag(node: binxml.Node, flags: dict[str, str]) -> None:
    parts = {}
    for part in node.children:
        if part.name not in ("name", "code"):
            return
        parts[part.name] = part.text or ""
    if "name" in parts and "code" in parts:
        flags[parts["code"]] = parts["name"]


# CBaseNode::GetLanguageCueTag @a22460 decomp
def _shot(node: binxml.Node) -> Node:
    greeting = bool(node.attr("sortkey"))
    npc = greeting or _number(node.attr("npc")) == 1
    n = Node(node.attr("uid") or "", node.attr("id") or "", greeting, npc,
             not greeting and npc and _number(node.attr("end")) == 1, False)
    seen: set[str] = set()
    play_length = 0.0
    for child in node.children:
        name = child.name
        if name in ("Cue", "CueEnglishUS"):
            n.cue = n.cue or child.text or ""
            continue
        if name in seen:
            continue
        seen.add(name)
        if name == "Speaker":
            n.speaker = child.text or ""
        elif name == "PlayLength":
            play_length = _number(child.text)
        elif name == "Links":
            n.links = _items(child)
        elif name == "LinksBack" and not greeting:
            n.links_back = _items(child)
        elif name == "FlagChecks":
            _codes(child, n.checks_false, n.checks_true)
        elif name == "FlagSets":
            _codes(child, n.sets_false, n.sets_true)
    n.automated = npc and _number(node.attr("automated")) == 1 and play_length != 0
    return n


# CGameDialogIO_V20::ReadXML @ad9760, CBaseNode::AddConnection @a22ce0 decomp
def read(data: bytes) -> Dialog:
    root = binxml.parse(binxml.payload(data))
    doc = next(root.find("dialog"), root)
    d = Dialog(doc.attr("name") or "", _number(doc.attr("automated")) != 0, {}, [], [])
    others: dict[str, Node] = {}
    for child in doc.children:
        if child.name == "Flags":
            for flag in child.children:
                _flag(flag, d.flags)
        elif child.name == "Shot":
            n = _shot(child)
            d.nodes.append(n)
            if n.greeting:
                d.greetings.append(n)
            elif n.id:
                others[n.id] = n
    for n in d.nodes:
        for target in n.links + n.links_back:
            if target in others and others[target] not in n.connections:
                n.connections.append(others[target])
    return d


# CGameDialog::IsGlobalEvent @9bfed0 decomp
def global_events(data: bytes) -> set[str]:
    root = binxml.parse(binxml.payload(data))
    return {n.attr("UUID") for n in root.find("Event") if n.attr("UUID")}
