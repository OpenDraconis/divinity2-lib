# divinity2-lib

Divinity II: Developer's Cut's own files in Python: its archives, the binary XML
in them, named, and the Osiris story and savegames. The formats, and nothing else:
building and installing mods is [divinity2-tools](https://github.com/ygalsk/divinity2-tools).

- `.dv2` archive reading
- the engine's archive search order, and which entry wins a path
- binary XML read and written, and the names behind its hashes
- the Osiris story: read, written, decompiled; savegames and the state they load, read and written
- Wwise sound banks: the media and the objects
- unpacking to named JSON

Python 3.11+ is required. Game data is not included.

## Install

```sh
git clone git@github.com:OpenDraconis/divinity2-lib.git
pip install -e divinity2-lib
```

It is not on PyPI. For the Unity port nothing needs installing: the port loads it from
`../divinity2-lib`, see [divinity2-port](https://github.com/OpenDraconis/divinity2-port).

## Use

```sh
python -m dv2lib unpack ~/dv2-extract
```

Commands, environment and the library API: [docs/usage.md](docs/usage.md).
What the engine and its formats do: [engine/](engine/).

## License

MIT, see `LICENSE`.
