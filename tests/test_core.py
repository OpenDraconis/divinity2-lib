"""dv2lib against archives and documents built here: no game files needed."""
import json
import struct
import zlib

import pytest

from dv2lib import archive, binxml, names, nif as nifmod, unpack


def dv2(files: dict[str, bytes], compress: bool = True) -> bytes:
    """A V5 archive, packed tight (align_32k=1)."""
    table = b"".join(n.encode("latin-1") + b"\0" for n in files)
    blobs = []
    for data in files.values():
        z = zlib.compress(data)
        blobs.append((z, len(data)) if compress and len(z) < len(data) else (data, 0))
    start = 22 + len(table) + 4 + 12 * len(blobs)
    dir_, body = b"", b""
    for stored, size in blobs:
        dir_ += struct.pack("<III", len(body), len(stored), size)
        body += stored
    head = struct.pack("<IIIBBII", 5, 1, 4, 1, 1, start, len(table))
    return head + table + struct.pack("<I", len(blobs)) + dir_ + body


def block(strings: list[str], nodes: bytes, n_nodes: int, n_attrs: int) -> bytes:
    table = b"".join(s.encode() + b"\0" for s in strings)
    return struct.pack("<III", n_nodes, n_attrs, len(table)) + table + nodes


def nif(payload: bytes) -> bytes:
    t = binxml.BLOCK_TYPE.encode()
    return (b"Gamebryo File Format, Version 20.3.0.9\n" + struct.pack("<IBI", 0x14030009, 1, 0x20000)
            + struct.pack("<IH", 1, 1) + struct.pack("<I", len(t)) + t + struct.pack("<H", 0)
            + struct.pack("<I", len(payload)) + struct.pack("<III", 0, 0, 0) + payload)


# Root(Name="a") with text "t" and two children <item>x</item>, <item>y</item>, narrow counts.
ROOT, NAME, ITEM = 0x11111111, 0x002C70A1, 0x003B8EAF
DOC = block(["t", "a", "x", "y"],
            struct.pack("<BI", 0x0F, ROOT) + bytes([1]) + struct.pack("<I", NAME) + bytes([2])
            + struct.pack("<BI", 0x0C, ITEM) + struct.pack("<BI", 0x0C, ITEM), 3, 1)


def test_archive_round_trip(tmp_path):
    files = {"Data\\a.xml": b"x" * 1000, "b.bin": b"\1\2\3"}
    p = tmp_path / "t.dv2"
    p.write_bytes(dv2(files))
    with archive.Archive(p) as ar:
        assert len(ar) == 2
        assert [e.is_compressed for e in ar] == [True, False]
        assert {e.path: ar.read(e) for e in ar} == files


def test_archive_refuses(tmp_path):
    p = tmp_path / "v4.dv2"
    p.write_bytes(struct.pack("<I", 4) + b"\0" * 30)
    with pytest.raises(archive.UnsupportedVersion):
        archive.Archive(p)
    p.write_bytes(dv2({"a": b"1"})[:-1])
    with archive.Archive(p) as ar, pytest.raises(archive.ArchiveError):
        ar.read(ar.entries[0])
    with pytest.raises(archive.ArchiveError):
        archive.safe_destination(tmp_path, "../escape")


def test_binxml_parse():
    root = binxml.parse(binxml.payload(nif(DOC)))
    assert (root.name_hash, root.text, root.attributes, root.narrow) == (ROOT, "t", [(NAME, "a")], True)
    assert [c.text for c in root.children] == ["x", "y"]          # stream order


@pytest.mark.parametrize("bad", [DOC + b"\0", DOC[:-1], DOC[:12 + 8] + b"\xf0" + DOC[21:]])
def test_binxml_refuses(bad):
    with pytest.raises(binxml.BinXmlError):
        binxml.parse(bad)


def test_names():
    assert names.name_of(NAME) == "Name"
    assert names.name_of(ROOT) is None
    # every recovered name hashes to the key it is filed under
    assert all(binxml.hash_of(v) == k for k, v in names.NAMES.items())


def test_plain_engine_order_and_unknown():
    unknown = {}
    tree = unpack.plain(binxml.parse(DOC), unknown, "x.xml")
    assert tree["name"] == "#11111111" and unknown == {"#11111111": "x.xml"}
    assert [c["text"] for c in tree["children"]] == ["y", "x"]   # engine order: reversed


def test_unpack_end_to_end(tmp_path):
    packed = tmp_path / "Packed"
    packed.mkdir()
    (packed / "GUI.dv2").write_bytes(dv2({"a.xml": nif(DOC), "b.xml": b"<plain/>"}))
    meta = unpack.unpack(packed, tmp_path / "out")
    assert (meta["files"], meta["documents"]) == (2, 1)
    assert list(meta["unreadable"]) == ["b.xml"]
    assert json.loads((tmp_path / "out/docs/a.xml.json").read_text())["attrs"] == {"Name": "a"}


def test_rewrap_replaces_the_block_and_its_size():
    old, new = block([], b"", 0, 0), block(["x"], b"", 0, 0)
    out = binxml.rewrap(nif(old), new)
    assert binxml.payload(out) == new
    assert nifmod.parse_header(out).sizes == [len(new)]
    assert binxml.rewrap(out, old) == nif(old)


def test_binxml_build_round_trip_and_widens_counts():
    root = binxml.parse(DOC)
    assert binxml.build(binxml.Document(root)) == DOC
    root.children = [binxml.Node(ITEM, text=str(i)) for i in range(300)]
    back = binxml.parse(binxml.build(binxml.Document(root)))       # 300 children: no longer one byte
    assert [c.text for c in back.children] == [str(i) for i in range(300)] and not back.narrow


def test_wwise_bank_event_to_media():
    from dv2lib import wwise

    def chunk(tag, body):
        return tag + struct.pack("<I", len(body)) + body

    def obj(kind, body):
        return struct.pack("<II", kind, len(body)) + body

    node = (b"\0\0" + struct.pack("<II", 0, 0) + bytes([50, 0, 0, 246]) + struct.pack("<12fI", *[0.0] * 12, 0)
            + b"\0" + bytes([1, 0]) + struct.pack("<H", 0) + bytes([0, 0, 0]) + b"\0" + struct.pack("<HH", 0, 0))
    sound = obj(2, struct.pack("<IIIIIIIB", 3, 0x40001, 0, 7, 9, 0, 4, 0) + node + struct.pack("<3h", 1, 0, 0))
    play = obj(3, struct.pack("<IIIiiiI", 2, 0x4011, 3, 0, 0, 0, 33) + struct.pack("<iiiB", 0, 0, 0, 4)
               + bytes(16) + struct.pack("<II", 0, 9))
    event = obj(4, struct.pack("<III", wwise.id_of("Play_It"), 1, 2))
    bank = (chunk(b"BKHD", struct.pack("<4I", 48, 9, 0, 0) + bytes(12))
            + chunk(b"DIDX", struct.pack("<III", 7, 0, 4)) + chunk(b"DATA", b"RIFF")
            + chunk(b"HIRC", struct.pack("<I", 3) + sound + play + event))
    b = wwise.read(bank)
    ev = b.objects[wwise.id_of("play_it")]
    act = b.objects[ev["actions"][0]]
    assert (act["action"], act["fade_curve"], act["file"]) == ("Play", "Linear", 9)
    assert b.media[b.objects[act["target"]]["source"]["source"]] == b"RIFF"
    assert wwise.id_of("aleroth_AD_heal2") == 741412071        # measured: the bank's own STID entry


def test_savestate_write_reads_back():
    """A savegame written from a header, three sections and a two-block story reads back the same,
    with a bool byte that is neither 0 nor 1 kept as it was."""
    from dv2lib import savegame, savestate
    header = savegame.Header(0, -1, "", 3, 2, 1, 0, "", 3, 1, 1, "004_Tutorial", "Main", "",
                             (1.0, 2.0, 3.0), "Episode_1_Extended", 0)
    sections = {"SaveLoadPreMisc - CRpgStats_V2_TimerManager": {"Timers": [{"UUID": "T", "Duration": 1.5}]},
                "SaveLoadPreMisc - CGameLogic_SyncData": {"RenderShadows": 32, "HideInShadows": False,
                                                          "TimeName": "Noon"},
                "SaveLoadStory": {"OsirisStoryStarted": True, "OsirisChunkBuffer": 1024}}
    story = bytes(range(256)) * 6
    data = savestate.write(header, sections, story)
    assert savestate.read(data) == {**sections, "SaveLoadStory": {**sections["SaveLoadStory"], "StoryBytes": 1536}}
    assert savegame.story_of(data) == story
