# Binary XML

Most `.xml` files are a tree with every element and attribute name replaced by a 32-bit hash, inside a NIF container — xml::dom::CStreamableNode::LoadBinary @10e1810 decomp

A document is a NIF file (NIF 20.3.0.9) holding one `xml::dom::CStreamableNode` block — CStreamableNode nif

The block is three u32 counts (nodes, attributes, strings), a table of NUL-terminated strings, then the nodes depth first; the last string is NUL-terminated too, so the split leaves an empty final element that is not a string — xml::dom::CStreamableNode::LoadBinary @10e1810 decomp

The NIF header at 20.3.0.9: a version line, version, endianness, user version, block count, block type names, a block type index and a size per block, the string table, then the groups — NIF header nif

Children are stored in reverse: `xml::dom::CStreamableNode::LoadBinary` pushes child slots 0..n-1 onto the head of a work list and pops from the head, so the first child in the stream fills the last slot. `CRpgStats_V2_Scenery::LoadXML` then takes `children[0]` as the position — xml::dom::CStreamableNode::LoadBinary @10e1810, CRpgStats_V2_Scenery::LoadXML @9952a0 decomp

## Measured

3972 binary-XML documents and 124 `.xml` files that are not binary XML — `python3 -c "import json;m=json.load(open('$HOME/dv2-extract/unpack.json'));print(m['documents'],len(m['unreadable']))"` after `python -m dv2lib unpack ~/dv2-extract`
