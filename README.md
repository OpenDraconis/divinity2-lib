# divinity2-lib

Reads the files of Divinity II: Developer's Cut (Larian Studios, 2009): the
`.dv2` archives, which archive wins each path, and the binary XML inside them,
with its names recovered. Standard library only; Python 3.11 or newer.

It is the part of [dv2mod](https://github.com/ygalsk/dv2-mod) that a reader of
the game needs, on its own. The
[Blender add-on](https://github.com/ygalsk/divinity2-blender) carries a copy
and runs it from its preferences.

You need your own copy of the game. This ships none of it, and it is not
endorsed by or affiliated with Larian Studios.

## Unpack the game

    pip install git+https://github.com/ygalsk/divinity2-lib
    python -m dv2lib unpack <folder> [<game folder>]

Without a game folder, the Developer's Cut is looked for in `DV2_GAME` and in
every Steam library. `<folder>` then holds:

| path | what |
|---|---|
| `<archive path>` | every file the game can load, from the archive that wins it |
| `docs/<archive path>.json` | every binary-XML document, as a plain named tree |
| `unpack.json` | the counts, every hash no name was recovered for, every `.xml` that is not binary XML |

On the Steam Developer's Cut: 34,857 files, 6.9 GB, 3,972 documents, 57
unnamed hashes, 37 s (`time python -m dv2lib unpack <folder>`). Every file and
every document is byte-identical to what `python -m dv2mod.core.bundle game`
writes (`diff -rq`); that also writes the 222 sound banks of `Soundbanks.dv2`,
an archive outside the search order, and this does not.

A tree is `{"name", "attrs": {name: value}, "text"?, "children"?}`. A name that
was never recovered is written `#hhhhhhhh`, so its value still arrives. Children
are in the engine's order, which is the stream's reversed
(`xml::dom::CStreamableNode::LoadBinary`).

The original Ego Draconis (2009) stores its archives as version 4, which is not
implemented: there is no version-4 copy to test against.

## Use it as a library

```python
from dv2lib import archive, binxml, corpus, locate, unpack

packed = locate.packed_of(locate.find_game())
entry = corpus.index(packed)["worldregions.xml"]
with archive.Archive(entry.archive) as ar:
    data = ar.read(entry.entry)
tree = unpack.plain(binxml.parse(binxml.payload(data)), {}, entry.path)
```

| module | what |
|---|---|
| `archive` | one `.dv2`: its directory, and each file's bytes |
| `corpus` | the search order, and the entry the game loads for each path |
| `binxml` | a NIF-wrapped binary XML file to a tree of hashes |
| `names` | hash to name, 1,138 names |
| `unpack` | the tree named, and the whole game written out |
| `locate` | the game in `DV2_GAME` or a Steam library |

Where each rule comes from is dv2mod's: `docs/reference/archives.md` and
`docs/reference/binxml.md` there.

## License

MIT, see `LICENSE`.
