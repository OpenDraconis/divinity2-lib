from __future__ import annotations

import struct
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from xml.sax.saxutils import quoteattr

from . import Dv2Error
from .savegame import checksum

PROFILE_FILE = "settings.dv2"
GRAPHIC_FILE = "graphicoptions.xml"
VERSION = (0, 16)
KEYCODES = 70


class SettingsError(Dv2Error, ValueError):
    pass


GRAPHIC_ATTRIBUTES = (
    "Fullscreen", "RenderMethod", "ScreenWidth", "ScreenHeight", "RenderRefraction", "DynamicReflections",
    "ShadowQuality", "RenderShadows", "TextureQuality", "AnisotropicSamples", "UseHDR", "UseVSync", "AnisoType",
    "AnimationTimeSlicing", "ShadowTimeSlicing", "QualityModeIndex", "StaticAssetHighQuality", "RenderLightShafts",
    "RenderDOF", "VegetationQualityLevel", "DynamicAssetQualityIndex", "DynamicAssetQualityMultiplier",
    "TreeQualityLevel", "TreeQualityMultiplier", "UseScreenSpaceAA", "UseMultiCore", "LockStepMode", "FPSCap",
    "DynamicLightQuality",
)


# CGraphicSettings::SaveXML @6a40d0 dc
def read_graphic_options(text: str) -> dict[str, str]:
    try:
        root = ET.fromstring(text)
    except ET.ParseError as e:
        raise SettingsError(f"{GRAPHIC_FILE}: {e}") from e
    node = root.find("pointer/GraphicSettings")
    if root.tag != "root" or node is None:
        raise SettingsError(f"{GRAPHIC_FILE}: no root/pointer/GraphicSettings")
    return dict(node.attrib)


def write_graphic_options(attributes: dict[str, str]) -> str:
    items = "".join(f" {k}={quoteattr(v)}" for k, v in attributes.items())
    return f"<root>\n  <pointer>\n    <GraphicSettings{items}/>\n  </pointer>\n</root>\n"


@dataclass
class Keycode:
    type: int = 0
    code: int = 0
    modifier: int = 0


@dataclass
class ProfileSettings:
    major: int = 0
    minor: int = 0
    magic_value: str = ""
    string_0: str = ""
    camera_y_inverted: int = 0
    fly_y_inverted: int = 0
    music_volume: float = 0.0
    effects_volume: float = 0.0
    speech_volume: float = 0.0
    rumble_intensity: float = 0.0
    auto_pause: float = 0.0
    brightness: float = 0.0
    show_damage_values: int = 0
    mouse_sensitivity: float = 0.0
    float_4c: float = 0.0
    float_58: float = 0.0
    bool_ac: int = 0
    bool_b8: int = 0
    bool_c4: int = 0
    difficulty_level: int = 0
    keycodes: list[Keycode] = field(default_factory=list)


BOOLS_BEFORE = ("camera_y_inverted", "fly_y_inverted")
FLOATS = ("music_volume", "effects_volume", "speech_volume", "rumble_intensity", "auto_pause", "brightness")
BOOLS_AFTER = ("bool_ac", "bool_b8", "bool_c4")
STRINGS = ("magic_value", "string_0")


class _Reader:
    def __init__(self, data: bytes, at: int):
        self.d, self.q = data, at

    def take(self, fmt: str):
        size = struct.calcsize(fmt)
        if self.q + size > len(self.d):
            raise SettingsError(f"{PROFILE_FILE} ends inside a value at {self.q}")
        v = struct.unpack_from(fmt, self.d, self.q)[0]
        self.q += size
        return v

    def string(self) -> str:
        n = self.take("<I")
        if self.q + n > len(self.d):
            raise SettingsError(f"{PROFILE_FILE}: string of {n} bytes at {self.q} runs past the end")
        v = self.d[self.q:self.q + n].decode("latin-1")
        self.q += n
        return v


# GameLogic_ProfileSettings::TProfileSettings::SaveLoad @9b3e90 dc, CGameLogic_ProfileSettingsManager::LoadSettingsWin32 @88a3b0 dc
def read_profile(data: bytes) -> ProfileSettings:
    if len(data) < 12:
        raise SettingsError(f"{PROFILE_FILE} has {len(data)} bytes")
    total4, total12 = struct.unpack_from("<I", data, 0)[0], struct.unpack_from("<I", data, 8)[0]
    if total4 != len(data) - 4 or total12 != len(data) - 12:
        raise SettingsError(f"size fields {total4}, {total12} do not fit {len(data)} bytes")
    got, want = checksum(data[12:]), struct.unpack_from("<I", data, 4)[0]
    if got != want:
        raise SettingsError(f"checksum {got:#010x}, the file says {want:#010x}")
    r = _Reader(data, 12)
    p = ProfileSettings(r.take("<I"), r.take("<I"))
    if (p.major, p.minor) != VERSION:
        raise SettingsError(f"version {p.major}.{p.minor} is not read, only {VERSION[0]}.{VERSION[1]}")
    for name in STRINGS:
        setattr(p, name, r.string())
    for name in BOOLS_BEFORE:
        setattr(p, name, r.take("<B"))
    for name in FLOATS:
        setattr(p, name, r.take("<f"))
    p.show_damage_values = r.take("<B")
    for name in ("mouse_sensitivity", "float_4c", "float_58"):
        setattr(p, name, r.take("<f"))
    for name in BOOLS_AFTER:
        setattr(p, name, r.take("<B"))
    p.difficulty_level = r.take("<i")
    p.keycodes = [Keycode(r.take("<i"), r.take("<I"), r.take("<I")) for _ in range(KEYCODES)]
    if r.q != len(data):
        raise SettingsError(f"{len(data) - r.q} bytes follow the last keycode")
    return p


def write_profile(profile: ProfileSettings) -> bytes:
    if len(profile.keycodes) != KEYCODES:
        raise SettingsError(f"{len(profile.keycodes)} keycodes, {KEYCODES} expected")
    out = [struct.pack("<II", *VERSION)]
    for name in STRINGS:
        raw = getattr(profile, name).encode("latin-1")
        out.append(struct.pack("<I", len(raw)) + raw)
    out += [struct.pack("<B", getattr(profile, n)) for n in BOOLS_BEFORE]
    out += [struct.pack("<f", getattr(profile, n)) for n in FLOATS]
    out.append(struct.pack("<B", profile.show_damage_values))
    out += [struct.pack("<f", getattr(profile, n)) for n in ("mouse_sensitivity", "float_4c", "float_58")]
    out += [struct.pack("<B", getattr(profile, n)) for n in BOOLS_AFTER]
    out.append(struct.pack("<i", profile.difficulty_level))
    out += [struct.pack("<iII", k.type, k.code, k.modifier) for k in profile.keycodes]
    body = b"".join(out)
    return struct.pack("<III", len(body) + 8, checksum(body), len(body)) + body
