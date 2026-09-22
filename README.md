# divinity2-lib

Divinity II: Developer's Cut's own files in Python: its archives, the binary XML
in them, named, and the Osiris story and savegames. The formats, and nothing else:
building and installing mods is [divinity2-tools](https://github.com/ygalsk/divinity2-tools).

- `.dv2` archive reading
- the engine's archive search order, and which entry wins a path
- binary XML read and written, and the names behind its hashes
- the Osiris story: read, written, decompiled; savegames and the state they load
- unpacking to named JSON

Python 3.11+ is required. Game data is not included.

## Install

```sh
pip install divinity2-lib
```

To work on it: `pip install -e .[dev]`, then `pytest -q`. The tests need no game files.

## Command

```sh
python -m dv2lib unpack <output> [<game>]
```

Without `<game>`, the command looks for `DV2_GAME` and Steam libraries.

## Library

```python
from dv2lib import archive, binxml, corpus, locate, unpack

packed = locate.packed_of(locate.find_game())
entry = corpus.index(packed)["worldregions.xml"]
with archive.Archive(entry.archive) as source:
    data = source.read(entry.entry)
tree = unpack.plain(binxml.parse(binxml.payload(data)), {}, entry.path)
```

| Module | Purpose |
|---|---|
| `archive` | `.dv2` containers |
| `corpus` | load order and winning entries |
| `nif` | the NIF container's header, one block got or set |
| `binxml` | binary XML, read and written |
| `names`, `larian_hash` | binary-XML names, and the hash that stands for them |
| `codec` | the game's text bytes, kept byte for byte |
| `osiris_story`, `osiris_write`, `osiris_source` | the Osiris story: read, written, decompiled |
| `story` | an episode's story, from its initial savegame |
| `savegame`, `savestate` | savegames, and the engine state they load |
| `unpack` | named JSON export |
| `locate` | game discovery |

## Checked against

The Steam Developer's Cut, with 0.2.0: the engine consults 532 shipped archives
and 34,857 paths win; 3,972 of the `.xml` files are binary XML and 124 are
plain text; the name table holds 1,146 names, and 49 hashes in the shipped
documents are still unnamed.

## License

MIT, see `LICENSE`.
