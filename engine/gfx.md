# Scaleform movies

A movie (`GUI/Win32/*.gfx`) is a SWF file under the signature `GFX`, or `CFX` when everything after the 8-byte file header is zlib-compressed; the loader also takes `FWS` and `CWS`, refuses a GFX file that is not version 2.x and needs an `ExporterInfo` tag in it — GFxSWFProcessInfo::Initialize @eb18f0 decomp

After the file header come the frame rectangle, the frame rate (8.8 fixed) and the frame count, then the tags; a tag header is a u16 of code (top 10 bits) and length (low 6), a length of 63 meaning a u32 length follows — GFxSWFProcessInfo::Initialize @eb18f0 decomp

Tags 0–99 are loaded through `GFx_SWF_TagLoaderTable` @1403c68, tags 1000–1005 through `GFx_GFX_TagLoaderTable` @1403dbc: 1000 ExporterInfo, 1001 DefineExternalImage, 1002 FontTextureInfo, 1003 DefineExternalGradientImage, 1004 DefineGradientMap, 1005 DefineFont — GFx_GFX_TagLoaderTable @1403dbc, GFx_SWF_TagLoaderTable @1403c68 decomp

ExporterInfo is a u16 version, a u32 of flags when the version is 0x10A or above, a u16 bitmap format, then the prefix and the SWF name as length-prefixed strings — GFxExporterInfoImpl::ReadExporterInfoTag @eb17c0 decomp

DefineExternalImage is u16 id, u16 format, u16 width, u16 height, then the export name and the file name (a `.dds` next to the movie) as length-prefixed strings — GFx_DefineExternalImageLoader @ebf8c0 decomp

DefineExternalGradientImage is u16 gradient id, u16 format, u16 size, then the file name as a length-prefixed string; the loader keys the gradient as `id | 0x50000` — GFx_DefineExternalGradientImageLoader @ebfa80 decomp

ImportAssets2 is the URL, then the symbol count, then two bytes the loader skips, then per symbol a u16 id and a name; the count comes before the two bytes, not after them as in the SWF specification — GFx_ImportLoader @ec1e30 decomp

DefineEditText's sixteen flag bits are read in SWF order; the font class bit is read but its string is not, the no-select and use-outlines bits are kept inverted as selectable and use-device-font — GFxEditTextCharacterDef::Read @eda8c0 decomp

PlaceObject2 and PlaceObject3 read a flag byte (0x02 character, 0x04 matrix, 0x08 colour transform, 0x10 ratio, 0x20 name, 0x40 clip depth, 0x80 clip actions), PlaceObject3 a second one (0x01 filters, 0x02 blend mode, 0x04 bitmap cache, one byte read and dropped), then the depth; a blend mode of 0 or above 14 becomes 1; clip-action event flags are 16 bits below SWF 6 except in PlaceObject3, 32 bits otherwise — GFxPlaceObject2::Read @f2ac10 decomp

A filter is a type byte, then DropShadow: colour, blur x, blur y, angle, distance (16.16 each), strength (8.8), a flag byte; Glow: colour, blur x, blur y, strength, a flag byte; Blur: blur x, blur y, a flag byte; Bevel is skipped as 27 bytes — GFx_LoadFilters @fcd4c0 decomp

DefineFont3 reads its flags, language, name and glyph count; with glyphs it reads the offset table (u32 entries when the wide-offsets flag is set) and the code-table offset, each glyph a style-less shape between two offsets; it then seeks to the code table and reads the codes and, with the layout flag, ascent, descent, leading, advances, glyph bounds and kerning pairs (u16 codes when wide); a font with no glyphs still reads the code-table offset and stops at the tag end if that offset reaches it, and nothing after the layout is read — GFxFontData::Read @f3aac0, GFxFontData::ReadCodeTable @f3a470 decomp

CSMTextSettings is the text id, 2 bits of flash type, 3 bits of grid fit, then thickness and sharpness as floats — GFx_CSMTextSettings @edb520 decomp

FileAttributes holds its flags in the first byte (0x10 has metadata, 0x01 use network) — GFx_FileAttributesLoader @ebf740 decomp

A shape is read by its styles then its edge records; a font glyph is a shape without styles — GFxConstShapeWithStyles::Read @f1c1d0, GFxConstShapeNoStyles::Read, GFxFillStyle::Read @fc4480, GFxLineStyle::Read @fc4af0, GFxGradientRecord::Read @fc2ec0 decomp

A morph shape holds start and end bounds, an offset, morph fill and line styles, then the start and end edges — GFxMorphCharacterDef::Read @f310b0, GFxMorphCharacterDef::ReadMorphFillStyle @f30710 decomp

Matrices, colour transforms, rectangles and colours are read bit-packed as in SWF — GFxStream::ReadMatrix @ec47e0, GFxStream::ReadCxformRgb @ec48c0, GFxStream::ReadCxformRgba @ec49b0, GFxStream::ReadRect @ec4ac0, GFxStream::ReadRgba @ec4bc0 decomp

An action is an opcode byte, with a u16 length and operands when the opcode is 0x80 or above; the game's disassembler names 99 opcodes and gives each an operand format (none, strings, bytes, u8, u16, s16, push values, constant pool, function, function2) in the table at 0x1405008 — GFxDisasm::LogDisasm @ef8c80 decomp

## Measured

66 movies, 48 of SWF version 8 and 18 of version 9, all `CFX` — `cd ~/divinity2-lib && python3 -c "import glob,os,collections;from dv2lib import gfx;print(collections.Counter((m.signature,m.version) for m in (gfx.read(open(p,'rb').read()) for p in glob.glob(os.path.expanduser('~/dv2-extract/GUI/Win32/*.gfx')))))"`

Every tag of every movie, nested sprites and actions included, reads to its last byte; 25 tag types occur: 4192 PlaceObject2, 2394 ShowFrame, 1281 End, 1215 DefineSprite, 581 DoAction, 537 DefineShape, 449 DefineExternalImage, 362 DefineEditText, 256 DefineShape3, 193 PlaceObject3, 171 CSMTextSettings, 164 DefineExternalGradientImage, 151 ExportAssets, 66 each of ExporterInfo, FileAttributes and SetBackgroundColor, 54 ImportAssets2, 30 DefineShape2, 27 DefineShape4, 25 RemoveObject2, 19 FrameLabel, 15 DefineFont3, 1 each of DefineMorphShape, Metadata and DefineScalingGrid — `cd ~/divinity2-lib && python3 -c "import glob,os,collections;from dv2lib import gfx;c=collections.Counter();w=lambda ts:[(c.update([t.name]),t.code==39 and w(t.fields['tags'])) for t in ts];[w(gfx.read(open(p,'rb').read()).tags) for p in glob.glob(os.path.expanduser('~/dv2-extract/GUI/Win32/*.gfx'))];print(c.most_common())"`

The movies' actions use 44 of the 99 opcodes; 189 placements carry filters (149 DropShadow, 56 Glow), 3 a blend mode (9 twice, 4 once), none clip actions — `cd ~/divinity2-lib && python3 -c "import glob,os,collections;from dv2lib import gfx;o=set();f=collections.Counter();w=lambda ts:[(t.code==12 and o.update(a['name'] for a in t.fields['actions']),[f.update([x['type']]) for x in t.fields.get('filters',[])],t.code==39 and w(t.fields['tags'])) for t in ts];[w(gfx.read(open(p,'rb').read()).tags) for p in glob.glob(os.path.expanduser('~/dv2-extract/GUI/Win32/*.gfx'))];print(len(o),f)"`

controlMapping.gfx's font 5 (Times New Roman) has no glyphs and 5210 bytes after its code table that the game's reader never reaches — `cd ~/divinity2-lib && python3 -c "import os;from dv2lib import gfx;m=gfx.read(open(os.path.expanduser('~/dv2-extract/GUI/Win32/controlMapping.gfx'),'rb').read());print([(t.fields['id'],t.fields['name'],len(t.fields['glyphs']),len(t.fields['unread'])) for t in m.of('DefineFont3')])"`
