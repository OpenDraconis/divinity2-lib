from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import corpus, osiris_story, savegame
from .osiris_source import Decompiler

SUFFIX = savegame.SUFFIX


@dataclass
class Loaded:
    episode: str
    entry: corpus.Entry
    story: osiris_story.Story
    index: osiris_story.StoryIndex
    decompiler: Decompiler
    save: bytes = b""

    @property
    def names(self) -> list[str]:
        return [g.name for g in self.story.goals]


def episodes(packed: Path) -> dict[str, corpus.Entry]:
    idx = corpus.index(packed, lambda k: k.endswith(SUFFIX))
    out = {}
    for e in idx.values():
        parts = e.path.replace("\\", "/").split("/")
        name = parts[2] if len(parts) > 3 else e.path
        out[name] = e
    return dict(sorted(out.items()))


def load(packed: Path, episode: str) -> Loaded:
    entry = episodes(packed)[episode]
    save = corpus.read(entry)
    st = osiris_story.read_story(savegame.story_of(save))
    return Loaded(episode, entry, st, osiris_story.StoryIndex(st), Decompiler(st), save)
