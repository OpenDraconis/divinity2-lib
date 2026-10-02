# Osiris story

`COsiris::_ReadHeader` calls `COsiSmartBuf::SetBufferBigEndian` with whether a header byte equals 1 — COsiris::_ReadHeader @d61c90 decomp

Every string is NUL-terminated and XOR-ed byte by byte with the key 0xAD, set by `_ReadHeader` once the header is past; integers are not obfuscated — COsiSmartBuf::read @1087bd0, COsiSmartBuf::AllocAndRead @10881a0 decomp

`endian_read` is never XOR-ed — COsiSmartBuf::endian_read @1087aa0 decomp

Rete nodes are read as a u8 type, a u32 index, then a body chosen by a switch over the type values 1 to 8 — COsiris::_ReadReteNodes @d61f40 decomp

`_ReadHeader` reads a 0x80-byte version block and then sets `ScrambleByte` to 0xad — COsiris::_ReadHeader @d61c90 decomp

## Measured

Every shipped story parses to its last byte — `python3 -c "from dv2lib import corpus,locate,story;p=locate.packed_of(locate.find_game());[story.load(p,e) for e in story.episodes(p)];print('ok')"` from `~/divinity2-lib`
