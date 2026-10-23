# Kynapse path data

## Container

`World/<region>/<Main or Subregions/name>/AI/*.hpd` is a `Kynogon HPD` file: the text `Kynogon HPD` and a zero, a u32 version (2), then the 140-byte `HPDHEADER_v2` read at 0x10, `nbEntries` `HPDENTRY` of 48 bytes at 0x9c, `nbPODEntries` `PODEntry` of 8 bytes, and the entries' data — Kaim::Mpd::CGraphManagerContext::VersionHeaderUpdate @d019d0, Kaim::Mpd::CGraphManagerContext::HeaderUpdate @d01a90, Kaim::Mpd::CGraphManagerContext::IndexUpdate @d01d60, Kaim::Mpd::CGraphManagerContext::PODIndexUpdate @d02020, HPDVERSIONHEADER::CheckHeaderText @d0d800 decomp, EgoPort re/FLYING_NPC_FINDINGS.md (alex2001212)

`HPDHEADER_v2`: file version 2, entry count, project type (1 in every file), the origin and edge length of `BalancedDirect` (four floats, 0 in every file), four `HPDADDITIONNALDATADESC` for nodes and four for edges (id, offset, size; nodes carry one, id 2, offset 0, size 8, edges none), the concrete node size (36), the concrete edge size (12), `aiMeshesManagement` and the path object count — gup-types.tsv `HPDHEADER_v2`, `HPDADDITIONNALDATADESC` decomp

`HPDENTRY`: unique id, the bounding box as min and max of x, y and z, the level (0 in every file), the data size, the data offset from the end of the index (0 in every file), two tags (`m_tag1`, `m_tag2`, garbage the loader overwrites) — gup-types.tsv `HPDENTRY`, Kaim::Mpd::CGraphManagerContext::SwapIndexEndianness @d01900 decomp

`PODEntry`: u32 path object uid, u16 mask, u16 type — gup-types.tsv `PODEntry`

## Slot

An entry of level 0 is a concrete slot: `CONCRETEHEADER` (node count, edge count), the nodes, the edges — Kaim::Mpd::CConcreteSlot::MapPointersLoaded @d0d850, gup-types.tsv `CONCRETEHEADER` decomp

A node is `CONCRETENODE` (unique id, position x, height and z, `abstract`, `nextCopy`, `firstOut`; 28 bytes) followed by the additional data of descriptor id 2 (8 bytes); an edge is cost, start node index, end node index — gup-types.tsv `CONCRETENODE`, `CONCRETEEDGE`, Kaim::Mpd::CGraphManagerContext::GetNodeAdditionnalDataSize @d05ff0 decomp

Positions are in Kynapse's space, x = game x, height = game z, z = -game y; `abstract` is 0x80000000 for every node; the first node's `nextCopy` holds the slot's longest edge as a float, which the loader reads and clears; `firstOut` is the index of the node's first edge plus one, the edges being sorted by start node; the cost is 0x80000000 and the edge length x 16; a node whose id has bit 31 set is a duplicate (`m_duplicatedNodes`); the two 32-bit words of the additional data are not named by the decompilation — Kaim::Mpd::CConcreteSlot::MapPointersLoaded @d0d850 decomp, EgoPort re/FLYING_NPC_FINDINGS.md (alex2001212)

With `aiMeshesManagement` 1 the last 8 bytes of the slot are a u32 `back` and a u32 (0 in every file); the AI mesh starts `back` bytes before them and ends at them, directly after the edges — Kaim::Mpd::CGraphManagerContext::FinalizeSlotFixing @d03180 decomp

## AI mesh

The mesh is `KynogonRuntimeMesh` and a zero (the 20th byte is padding), a u32 version (2) and a u32 pointer (0) the loader fills in, then the 52-byte `CAiMeshHeader` at 0x1c: id (-1), the inverse of the local map size, pitch, the x range (`RIGHT_MIN`, `RIGHT_MAX`), the z range (`FRONT_MIN`, `FRONT_MAX`), the cell counts `AMAX` along x and `BMAX` along z, the radius, the offset of the column table (0x50), the neighbour mesh count (0) and offset — Kaim::CAiMesh::LoadAiMesh @d158d0, gup-types.tsv `CAiMeshHeader` decomp

The column table holds `AMAX` x `BMAX` + 1 offsets from the start of the mesh, column index = `BMAX` x a + b; the last one points at the final 4 bytes of the mesh, a word the loader never reads as an offset when it is 0xffffffff and that differs between files (0 in 99 of 159); a column is a count, that many `CLmHeader` (local map offset, lowest and highest altitude; 12 bytes) and, when the count is not 0, the u32 end offset of its last local map — Kaim::CAiMeshHeader::GetColumn @d0e280, Kaim::CAiMeshHeader::GetMap @d0e600, `anonymous namespace'::ReadColumnBuffer @d15780 decomp

The column of a position is found from the ranges and the cell size (`GetColumnCandidates` clamps the cell index and takes up to four candidate columns around it); a local map of it contains the point when the altitude is within its header's range and `CLocalMap::IsInside` finds it within the outline made of the outer obstacle polylines and the outgoing links — Kaim::CAiMeshHeader::GetColumnCandidates @d17c60, Kaim::CAiMeshHeader::GetMapFromPos @d19040, Kaim::CLocalMap::IsInside @d18190 decomp

A `CLocalMap` (80 bytes): mesh id (-1), cell a, cell b and index c in the column, radius, pitch, highest and lowest altitude, then count and offset (from the start of the local map, 0xffffffff when the count is 0) of the incoming links, outgoing links, multi-mesh links, incoming obstacles, outgoing obstacles and shapes — gup-types.tsv `CLocalMap`, Kaim::CLocalMap::InLinks @d15520 .. Kaim::CLocalMap::Shapes @d15590 decomp

A `CLmLink` is two points, a local map offset and a size (32 bytes); a `CLmMultiMeshLink` adds a mask vector (44 bytes); an obstacle list is count + 1 offsets followed by the polylines of 12-byte points between them; the shapes are count + 1 entries of 16 bytes (offset of its points, an orientation vector; the last entry only ends the last shape), then the points — gup-types.tsv `CLmLink`, `CLmMultiMeshLink`, `CLmShape`, `anonymous namespace'::ReadLocalMapBuffer @d15640 decomp

## Measured

Every one of the 183 `Kynogon HPD` files under `World` is read and written again byte for byte with every byte written by a named field (159 with an AI mesh, 24 flying graphs without one; 9 files under `AI/Scene` are not `Kynogon HPD` and are not read) — `find ~/dv2-extract/World -name '*.hpd' -print0 | xargs -0 python3 -m dv2lib.kynapse round-trip | awk '{print $2}' | sort | uniq -c`

All 183 files have one entry, level 0, offset 0, project type 1, every node's `abstract` 0x80000000; all 159 meshes have id -1, the column table at 0x50 and no neighbour mesh; the cell size is 25 m in 156 meshes, 20.1 m in 2 and 20 m in 1 — `python3 -c "import glob,os,collections;from dv2lib import kynapse as k;print(collections.Counter(round(k.read(d).slots[0].mesh.local_map_size,1) for p in glob.glob(os.path.expanduser('~/dv2-extract/World/**/*.hpd'),recursive=True) for d in [open(p,'rb').read()] if d[:12]==k.MAGIC and k.read(d).slots[0].mesh))"`

004_Tutorial `Main/AI/walk.hpd` is 471 nodes, 1488 edges, 210 local maps in 25 x 26 cells of 20.1 m, radius 0.4, pitch 0.3 — `python3 -m dv2lib.kynapse info ~/dv2-extract/World/004_Tutorial/Main/AI/walk.hpd`
