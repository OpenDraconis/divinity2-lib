from __future__ import annotations

import dataclasses
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


def read_graphic_options(text: str) -> dict[str, str]:
    return {}


def write_graphic_options(attributes: dict[str, str]) -> str:
    return ""


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


def read_profile(data: bytes) -> ProfileSettings:
    return ProfileSettings()


def write_profile(profile: ProfileSettings) -> bytes:
    return b""
