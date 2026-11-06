# Profile settings

The Developer's Cut keeps the player's options in two files of the profile folder.

## Location

The profile folder is `Divinity 2\Profile\` below the user's local application data folder (`CSIDL_LOCAL_APPDATA`, 0x1c); the path is built as `%sProfile\` — profile folder getter @654110, folder lookup @653a90 dc

Under Proton it is `<steam library>/steamapps/compatdata/219780/pfx/drive_c/users/steamuser/AppData/Local/Divinity 2/Profile/` — Measured below

## graphicoptions.xml

Plain text XML, LF line ends: `<root>`, `<pointer>` and one `GraphicSettings` element, indented by two spaces per level, the attributes on one line, the element closed with `/>`, the file ends with a line feed — CGraphicSettings::SaveXML @6a40d0 dc, Measured below

The attributes, in this order, all written as integers: `Fullscreen`, `RenderMethod`, `ScreenWidth`, `ScreenHeight`, `RenderRefraction`, `DynamicReflections`, `ShadowQuality`, `RenderShadows`, `TextureQuality`, `AnisotropicSamples`, `UseHDR`, `UseVSync`, `AnisoType`, `AnimationTimeSlicing`, `ShadowTimeSlicing`, `QualityModeIndex`, `StaticAssetHighQuality`, `RenderLightShafts`, `RenderDOF`, `VegetationQualityLevel`, `DynamicAssetQualityIndex`, `DynamicAssetQualityMultiplier`, `TreeQualityLevel`, `TreeQualityMultiplier`, `UseScreenSpaceAA`, `UseMultiCore`, `LockStepMode`, `FPSCap`, `DynamicLightQuality` — CGraphicSettings::SaveXML @6a40d0 dc

`CGraphicSettings::Save` @6a4df0 writes the file named by `GetSaveFile` @6a3a10 in the profile folder — CGraphicSettings::Save @6a4df0, CGraphicSettings::GetSaveFile @6a3a10 dc

## settings.dv2

Three u32 then the payload: the payload size plus 8, the checksum of the payload, the payload size — CGameLogic_ProfileSettingsManager::SaveSettingsWin32 @88a1d0 dc, Measured below

The checksum is the one of the savegame container ([savegame.md](savegame.md)): `h = h * 33 + signed byte`, a result of 0xffffffff becomes 0 — CalculateCheckSum @8e2970 dc, Measured below

The payload is the `SaveLoad` visitor stream without tags, little-endian, as in [savegame.md](savegame.md): u32 major, u32 minor (the current version is 0.16; a file with a major above 0 is not read, one with 0.0 is refused), then the fields below — GameLogic_ProfileSettings::TProfileSettings::SaveLoad @9b3e90 dc

Fields at 0.16, in stream order (`this` offsets in the settings object; bool is one byte, int and float four): string `magic_value` (a global string), string `string_0` (+0x0, from minor 15), bool +0x1c, bool +0x28, float +0x64, float +0x70, float +0x7c, float +0x34, float +0x88, float +0xd0, bool +0x94, float +0x40, float +0x4c and float +0x58 (from minor 16), bool +0xac (from minor 12), bool +0xb8 (from minor 13), bool +0xc4 (from minor 14), int +0xa0 (from minor 10), then 70 keycodes of the keyboard block unless `GlobalSwitches` byte 0x14f18fc is set — TProfileSettings::SaveLoad @9b3e90 dc

A keycode is `int` type, `uint` input code, `uint` modifier; the type 4 holds a DirectInput scan code, 2 a mouse button, 0 nothing — TProfileSettings::LoadSaveKeycode @9b3e10 dc, Measured below

Field meaning: bool +0x1c and +0x28 are the camera Y and flight Y inversion, +0x64, +0x70, +0x7c the music, effects and speech volume, +0x34 the rumble intensity, +0x88 the autopause value (its setter @a82910 stores the value over 5 times 2), +0xd0 the brightness, +0x94 the show-damage flag, +0x40 the mouse sensitivity (the value read by `GetMouseSensitivity` @a82650), +0xa0 the difficulty level. These follow the GUP order of the same function and the setters' order in the DC (the volumes' setters @a82790, @a827f0, @a82850, then rumble @a828b0, autopause @a82910, each 0x60 apart). The floats +0x4c and +0x58 and the bools +0xac, +0xb8, +0xc4 have no recovered name — TProfileSettings::TProfileSettings @9b5850 dc, GameLogic_ProfileSettings::TProfileSettings::SaveLoad @a342a0 decomp

A member of the settings object holds its value at its offset, its setter at +4 and its getter at +8 — TProfileSettings::TProfileSettings @9b5850 dc

## Measured

The file names — `objdump -s --start-address=0x132a08c --stop-address=0x132a0a0 $DV2_MEASURE/pdb/Divinity2.exe`, `--start-address=0x1314c3c --stop-address=0x1314c50`

The Steam install's `graphicoptions.xml` has 29 attributes in the order above, LF line ends, and ends with `</root>` and a line feed — `cat "$HOME/.local/share/Steam/steamapps/compatdata/219780/pfx/drive_c/users/steamuser/AppData/Local/Divinity 2/Profile/graphicoptions.xml"`

The Steam install's `settings.dv2` is 914 bytes: size fields 0x38e and 0x386, checksum 0x2d032d69, version 0.16, two empty strings, 70 keycodes, no byte left over — `python3 -c "import dv2lib.settings as s; print(s.read_profile(open('<profile folder>/settings.dv2','rb').read()))"` and `od -A d -t x1z <profile folder>/settings.dv2`

The first six keycodes of that file are keyboard 0x11, 0x1f, 0x1e, 0x20, then mouse buttons 0 and 1 — `python3 -c "import dv2lib.settings as s; print(s.read_profile(open('<profile folder>/settings.dv2','rb').read()).keycodes[:6])"`
