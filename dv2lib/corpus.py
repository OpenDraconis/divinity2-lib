r"""Which archive serves each path: the engine's search order.

The executable names 31 global archives under `Data/Win32/Packed/`, and the
order it names them in is the search order:

    grep -a -o 'Win32\\Packed\\[ -~]*\.dv2' <game>/bin/Divinity2-debug.exe

`CSoundBankManager::Init` @86d860 mounts one more, `Soundbanks.dv2`, before it
loads `Init.bnk`; the executable spells it `"Win32"` + `"\\Packed\\Soundbanks.dv2"`,
so the grep above misses it. It is searched after the 31; of its 223 paths one
is in another archive, byte-identical (`RS_BV2_Main.bnk`, `Episode_1_Extended/Dialogs.dv2`).

512 more archives sit under `World/<Region>/...` and `Episode_*/` and are
searched after those. Among them no XML path appears twice with different
content, so they are sorted by path. The first archive that holds a path
serves it -- per path, not per archive: `Patch.dv2` overrides region files,
and 1,824 of the 35,079 paths are in more than one archive.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from . import archive

#: Search order, highest priority first.
LOAD_ORDER: tuple[str, ...] = (
    "DKS_Patch.dv2", "DKS_Patch_2.dv2", "DKS_Patch_3.dv2", "DKS_Patch_4.dv2",
    "FOV_Patch.dv2", "FOV_Patch_2.dv2", "FOV_Patch_3.dv2", "FOV_Patch_4.dv2",
    "Patch.dv2", "Patch_2.dv2", "Patch_3.dv2", "Patch_4.dv2",
    "GUI.dv2", "GFX.dv2",
    "MainDataPlatform.dv2", "MainDataStartup.dv2", "MainDataStreaming.dv2",
    "MainDataStub.dv2",
    "Textures.dv2", "Textures2.dv2", "CompiledAssets.dv2",
    "ItemPhysx.dv2", "SceneryPhysx.dv2", "KFMs.dv2", "Effects.dv2",
    "FlyingFortresses.dv2", "Items.dv2", "Scenery.dv2",
    "Characters.dv2", "CharacterTemplates.dv2", "Trees.dv2",
)

#: Slots the executable names but the game does not ship: eleven of the twelve
#: override archives are empty, `Patch.dv2` is Larian's. What sits in them is a
#: mod, and a mod is not the game.
MOD_SLOTS: tuple[str, ...] = tuple(n for n in LOAD_ORDER[:12] if n != "Patch.dv2")

#: The sound archive, mounted by `CSoundBankManager::Init` @86d860.
SOUNDBANKS = "Soundbanks.dv2"


@dataclass(frozen=True)
class Entry:
    """One file the game would load, and the archive it comes from."""

    path: str                 # as the archive spells it, with backslashes
    archive: Path
    entry: archive.Entry

    @property
    def key(self) -> str:
        return self.path.lower()


def archives(packed: Path, *, shipped: bool = True) -> list[Path]:
    """Every archive the game consults, best first.

    `shipped` leaves out the mod slots, so the answer is the game as Larian shipped it;
    without it an installed mod wins its paths the way the engine lets it.
    """
    out = [packed / n for n in LOAD_ORDER
           if (packed / n).exists() and not (shipped and n in MOD_SLOTS)]
    out += [packed / SOUNDBANKS] if (packed / SOUNDBANKS).exists() else []
    out += sorted(p for p in packed.rglob("*.dv2") if p.parent != packed)
    return out


#: The last index per (packed, shipped), with the archive list it was read from.
_index_cache: dict[tuple[str, bool], tuple[tuple, dict[str, Entry]]] = {}


def stamp(files: list[Path]) -> tuple:
    """What makes a cached read stale: an archive added, removed, or written.

    Every cache over the packed data keys on this, so they all go stale together.
    """
    out = []
    for p in files:
        try:
            st = p.stat()
        except OSError:
            continue
        out.append((str(p), st.st_mtime_ns, st.st_size))
    return tuple(out)


def _all(packed: Path, shipped: bool) -> dict[str, Entry]:
    """Every entry of every archive, read once and kept until an archive changes."""
    ck = (str(packed), shipped)
    files = archives(packed, shipped=shipped)
    st = stamp(files)
    hit = _index_cache.get(ck)
    if hit is not None and hit[0] == st:
        return hit[1]
    out: dict[str, Entry] = {}
    for a in files:
        with archive.Archive(a) as ar:
            for e in ar:
                out.setdefault(e.path.lower(), Entry(e.path, a, e))
    _index_cache[ck] = (st, out)
    return out


def index(packed: Path, want: Callable[[str], bool] | None = None, *,
          shipped: bool = True) -> dict[str, Entry]:
    """Lower-cased path -> the entry the game would load.

    Reading 500 archive directories costs more than everything a caller does with the
    answer, and every caller wants a subset of the same thing, so the whole index is
    read once and filtered in memory."""
    full = _all(Path(packed), shipped)
    if want is None:
        return dict(full)
    return {k: v for k, v in full.items() if want(k)}


def read(entry: Entry) -> bytes:
    with archive.Archive(entry.archive) as ar:
        return ar.read(entry.entry)


def read_many(entries: Iterable[Entry]) -> dict[str, bytes]:
    """key -> bytes, opening each archive once."""
    by_archive: dict[Path, list[Entry]] = {}
    for e in entries:
        by_archive.setdefault(e.archive, []).append(e)
    out: dict[str, bytes] = {}
    for a, items in by_archive.items():
        with archive.Archive(a) as ar:
            for e in items:
                out[e.key] = ar.read(e.entry)
    return out


def find(packed: Path, suffix: str, *, shipped: bool = True) -> Entry:
    """The winning entry whose path ends with `suffix`, case-insensitive."""
    suffix = suffix.lower()
    hits = index(packed, lambda k: k.endswith(suffix), shipped=shipped)
    if not hits:
        raise FileNotFoundError(f"no archive under {packed} holds *{suffix}")
    if len(hits) > 1:
        raise LookupError(f"{len(hits)} paths end with {suffix}: {sorted(hits)[:5]}")
    return next(iter(hits.values()))


def owners(packed: Path, paths: Iterable[str]) -> dict[str, str]:
    """Lower-cased path -> the name of the archive that wins it, mod slots included."""
    wanted = {p.lower() for p in paths}
    hits = index(packed, lambda k: k in wanted, shipped=False)
    return {k: e.archive.name for k, e in hits.items()}


def xml_documents(packed: Path, *, shipped: bool = True) -> dict[str, Entry]:
    return index(packed, lambda k: k.endswith(".xml"), shipped=shipped)
