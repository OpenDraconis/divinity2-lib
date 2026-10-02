# Using divinity2-lib

Python 3.11 or newer, standard library only; it runs inside Blender's Python too. Game data is not included.

## Install

```sh
git clone https://github.com/OpenDraconis/divinity2-lib
cd divinity2-lib
pip install -e .
```

Or `pip install git+https://github.com/OpenDraconis/divinity2-lib`. For development: `pip install -e .[dev]`, then `pytest -q` ([test_core.py](../tests/test_core.py)); the tests need no game files. Package metadata is in [pyproject.toml](../pyproject.toml).

## Environment

| Variable | Meaning |
|---|---|
| `DV2_GAME` | The game's install folder, the one holding `Data` and `bin`. `locate.find_game()` returns it when it names a game; otherwise it searches the Developer's Cut in every Steam library (`steamapps/common/divinity2_dev_cut`) |

`locate.packed_of(game)` takes the game folder (or the `Data/Win32/Packed` folder itself) and returns the folder of archives, or `None`.

## Unpack the game

```sh
python -m dv2lib unpack <out> [<game>]
```

| Argument | Meaning |
|---|---|
| `<out>` | Folder to write into |
| `<game>` | The game's install folder; without it, `DV2_GAME` and the Steam libraries are searched |

It writes, from [unpack.py](../dv2lib/unpack.py):

| Path | Content |
|---|---|
| `<out>/<archive path>` | every file the game can load, from the archive that wins it |
| `<out>/docs/<archive path>.json` | every binary-XML document as a named tree `{"name", "attrs", "text"?, "children"?}`; an unrecovered name is `#hhhhhhhh` |
| `<out>/unpack.json` | what was written, every hash with no name, every `.xml` that is not binary XML, with the reason |

The result is the extracted copy that the other tools call `DV2_EXTRACT` (`~/dv2-extract`). Exit code 2 means no game or no archives were found.

## Pack an archive

```sh
python -m dv2lib pack <folder> <out.dv2>
```

Writes every file under `<folder>` into `<out.dv2>`, at its path relative to `<folder>` (`Win32/Textures/foo.nif`). The layout is `Patch.dv2`'s: zlib level 9, every file and the data 32 KiB aligned ([archive.py](../dv2lib/archive.py) `write`). A path that appears twice, ignoring case, is an error.

Named `DKS_Patch.dv2` in `Data/Win32/Packed`, it is searched before every shipped archive, so its files replace the game's ([search-order.md](../engine/search-order.md)). Delete it to undo.

## Savegames

```sh
python -m dv2lib.savestate to-json <save.dsg> <out.json>
python -m dv2lib.savestate to-dsg <in.json> <out.dsg>
python -m dv2lib.savestate round-trip <save.dsg>...
```

| Command | Does |
|---|---|
| `to-json` | writes the savegame as one JSON object: its sections at the top level, the header under `Header`, the story's bytes in base64 under `Story` |
| `to-dsg` | writes the savegame that a `to-json` file came from |
| `round-trip` | reads, writes through JSON and reads again, then prints `identical` or what differs (the decompressed stream and the header outside its sizes and checksum); exit code 1 when any file differs |

`to-json` and `to-dsg` write only their last argument.

## Library

```python
from dv2lib import archive, binxml, corpus, locate, unpack

packed = locate.packed_of(locate.find_game())
entry = corpus.index(packed)["worldregions.xml"]
with archive.Archive(entry.archive) as source:
    data = source.read(entry.entry)
tree = unpack.plain(binxml.parse(binxml.payload(data)), {}, entry.path)
```

| Module | Use |
|---|---|
| [archive](../dv2lib/archive.py) | `Archive(path)`: `.entries`, `.read(entry)`; `write(path, [(name, bytes)])`; `safe_destination(outdir, path)`; `check_invariants` |
| [corpus](../dv2lib/corpus.py) | `archives(packed, shipped=True)`, `index(packed, want=None, shipped=True)` (lower-cased path to `Entry`), `read`, `read_many`, `find(packed, suffix)`, `owners`, `xml_documents` |
| [nif](../dv2lib/nif.py) | `parse_header`, `get_block`, `set_block` |
| [binxml](../dv2lib/binxml.py) | `payload`, `parse`, `build`, `rewrap`, `hash_of`; `Node` with descendant lookup, `child`, `set_attr`, `set_items` |
| [names](../dv2lib/names.py), [larian_hash](../dv2lib/larian_hash.py) | `name_of(hash)`, `name_hash(text)` |
| [codec](../dv2lib/codec.py) | `decode`, `encode`, `decode_story`, `encode_story` |
| [osiris_story](../dv2lib/osiris_story.py), [osiris_write](../dv2lib/osiris_write.py), [osiris_source](../dv2lib/osiris_source.py) | `read_story`; `write_story`, `to_div2`; `Decompiler` |
| [story](../dv2lib/story.py) | `episodes(packed)`, `load(packed, episode)` |
| [savegame](../dv2lib/savegame.py) | `read_header`, `check`, `split`, `story_span`, `story_of`, `pack`, `rebuild`, `transplant`, `checksum` |
| [savestate](../dv2lib/savestate.py) | `read`, `write`, `to_json`, `from_json`, `round_trip` |
| [wwise](../dv2lib/wwise.py) | `read(data)` returns a `Bank` (`media`, `objects`, `events()`, `volume_threshold_db`); `id_of(name)`; `WwiseError` |
| [dialog](../dv2lib/dialog.py) | `packs(episode, name, language="English")` |
| [unpack](../dv2lib/unpack.py) | `unpack(packed, out, progress)`; `progress(done, total)` is called per file and raising in it stops |
| [locate](../dv2lib/locate.py) | `find_game`, `is_game`, `packed_of`, `steam_libraries` |

Every error is a `dv2lib.Dv2Error`. What the formats are is in [engine/](../engine/); see the [index](README.md).
