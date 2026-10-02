# Archives (.dv2)

## Measured

A version 5 header is u32 version, u32 unknown_a, u32 unknown_b, u8 align_32k, u8 unknown_d, u32 data_start, u32 string_space, followed by the path table — `python3 -c "import struct,sys;print(struct.unpack('<IIIBBII',open(sys.argv[1],'rb').read(22)))" ~/.local/share/Steam/steamapps/common/divinity2_dev_cut/Data/Win32/Packed/Patch.dv2`

Header field tuples (version, unknown_a, unknown_b, align_32k, unknown_d): (5,1,4,1,1) in 500 archives and (5,1,4,0,1) in 33 — `python3 -c "from dv2lib import corpus,locate,archive;from collections import Counter;p=locate.packed_of(locate.find_game());print(Counter((a.header.version,a.header.unknown_a,a.header.unknown_b,a.header.align_32k,a.header.unknown_d) for a in map(archive.Archive,corpus.archives(p))))"` from `~/divinity2-lib`, `DV2_GAME` set

533 shipped archives — `python3 -c "from dv2lib import corpus,locate;print(len(corpus.archives(locate.packed_of(locate.find_game()))))"`
