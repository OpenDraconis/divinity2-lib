# Archives (.dv2)

## Measured

A version 5 header is u32 version, u32 unknown_a, u32 unknown_b, u8 align_32k, u8 unknown_d, u32 data_start, u32 string_space, followed by the path table — `python3 -c "import struct,sys;print(struct.unpack('<IIIBBII',open(sys.argv[1],'rb').read(22)))" ~/.local/share/Steam/steamapps/common/divinity2_dev_cut/Data/Win32/Packed/Patch.dv2`

Header field tuples (version, unknown_a, unknown_b, align_32k, unknown_d): (5,1,4,1,1) in 500 archives and (5,1,4,0,1) in 33 — `python3 -c "from dv2lib import corpus,locate,archive;from collections import Counter;p=locate.packed_of(locate.find_game());print(Counter((a.header.version,a.header.unknown_a,a.header.unknown_b,a.header.align_32k,a.header.unknown_d) for a in map(archive.Archive,corpus.archives(p))))"` from `~/divinity2-lib`, `DV2_GAME` set

533 shipped archives — `python3 -c "from dv2lib import corpus,locate;print(len(corpus.archives(locate.packed_of(locate.find_game()))))"`

`align_32k` 0: `data_start` and every entry offset are multiples of 32768, in all 33 such archives — `python3 -c "from dv2lib import corpus,locate,archive;from collections import Counter;p=locate.packed_of(locate.find_game());print(Counter((a.header.align_32k,a.header.data_start%32768==0,all(e.offset%32768==0 for e in a)) for a in map(archive.Archive,corpus.archives(p))))"`

`Patch.dv2` has `align_32k` 0 — `python3 -c "from dv2lib import archive,locate;print(archive.Archive(locate.packed_of(locate.find_game())/'Patch.dv2').header)"`
