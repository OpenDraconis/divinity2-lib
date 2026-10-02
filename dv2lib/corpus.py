from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from . import archive

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

MOD_SLOTS: tuple[str, ...] = tuple(n for n in LOAD_ORDER[:12] if n != "Patch.dv2")

# CSoundBankManager::Init @86d860 decomp
SOUNDBANKS = "Soundbanks.dv2"


@dataclass(frozen=True)
class Entry:
    path: str
    archive: Path
    entry: archive.Entry

    @property
    def key(self) -> str:
        return self.path.lower()


def archives(packed: Path, *, shipped: bool = True) -> list[Path]:
    out = [packed / n for n in LOAD_ORDER
           if (packed / n).exists() and not (shipped and n in MOD_SLOTS)]
    out += [packed / SOUNDBANKS] if (packed / SOUNDBANKS).exists() else []
    out += sorted(p for p in packed.rglob("*.dv2") if p.parent != packed)
    return out


_index_cache: dict[tuple[str, bool], tuple[tuple, dict[str, Entry]]] = {}


def stamp(files: list[Path]) -> tuple:
    out = []
    for p in files:
        try:
            st = p.stat()
        except OSError:
            continue
        out.append((str(p), st.st_mtime_ns, st.st_size))
    return tuple(out)


def _all(packed: Path, shipped: bool) -> dict[str, Entry]:
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
    full = _all(Path(packed), shipped)
    if want is None:
        return dict(full)
    return {k: v for k, v in full.items() if want(k)}


def read(entry: Entry) -> bytes:
    with archive.Archive(entry.archive) as ar:
        return ar.read(entry.entry)


def read_many(entries: Iterable[Entry]) -> dict[str, bytes]:
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
    suffix = suffix.lower()
    hits = index(packed, lambda k: k.endswith(suffix), shipped=shipped)
    if not hits:
        raise FileNotFoundError(f"no archive under {packed} holds *{suffix}")
    if len(hits) > 1:
        raise LookupError(f"{len(hits)} paths end with {suffix}: {sorted(hits)[:5]}")
    return next(iter(hits.values()))


def owners(packed: Path, paths: Iterable[str]) -> dict[str, str]:
    wanted = {p.lower() for p in paths}
    hits = index(packed, lambda k: k in wanted, shipped=False)
    return {k: e.archive.name for k, e in hits.items()}


def xml_documents(packed: Path, *, shipped: bool = True) -> dict[str, Entry]:
    return index(packed, lambda k: k.endswith(".xml"), shipped=shipped)
