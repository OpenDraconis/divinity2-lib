import struct

import pytest

from dv2lib import savegame, settings

GRAPHIC_TEXT = (
    '<root>\n  <pointer>\n    <GraphicSettings Fullscreen="1" RenderMethod="1" ScreenWidth="2880" '
    'ScreenHeight="1920" RenderRefraction="1" DynamicReflections="1" ShadowQuality="2" RenderShadows="1" '
    'TextureQuality="2" AnisotropicSamples="4" UseHDR="1" UseVSync="1" AnisoType="1" AnimationTimeSlicing="0" '
    'ShadowTimeSlicing="1" QualityModeIndex="2" StaticAssetHighQuality="0" RenderLightShafts="1" RenderDOF="1" '
    'VegetationQualityLevel="2" DynamicAssetQualityIndex="1" DynamicAssetQualityMultiplier="1" '
    'TreeQualityLevel="1" TreeQualityMultiplier="1" UseScreenSpaceAA="0" UseMultiCore="1" LockStepMode="0" '
    'FPSCap="30" DynamicLightQuality="2"/>\n  </pointer>\n</root>\n'
)

KEYS = [(4, 17, 0), (4, 31, 0), (4, 30, 0), (4, 32, 0), (2, 0, 0), (2, 1, 0), (4, 58, 0), (4, 57, 0), (4, 15, 0), (4, 16, 0), (4, 23, 0), (0, 0, 0), (4, 22, 0), (4, 37, 0), (4, 38, 0), (4, 50, 0), (4, 64, 0), (4, 68, 0), (4, 28, 0), (4, 59, 0), (4, 60, 0), (4, 61, 0), (4, 2, 0), (4, 3, 0), (4, 4, 0), (4, 5, 0), (4, 6, 0), (4, 7, 0), (4, 8, 0), (4, 9, 0), (4, 63, 0), (4, 67, 0), (4, 19, 0), (4, 21, 0), (4, 42, 0), (4, 121, 0), (4, 126, 0), (4, 123, 0), (4, 124, 0), (0, 0, 0), (4, 18, 0), (0, 0, 0), (4, 82, 0)] + [(0, 0, 0)] * 10 + [(4, 33, 0)] + [(0, 0, 0)] * 15 + [(4, 54, 0)]


def sample(keys=KEYS, strings=(b"", b"")):
    body = struct.pack("<II", 0, 16)
    for s in strings:
        body += struct.pack("<I", len(s)) + s
    body += bytes([0, 0]) + struct.pack("<6f", 0.8, 0.8, 0.8, 1.0, 0.0, 0.5) + bytes([1])
    body += bytes.fromhex("0100003f") + struct.pack("<2f", 0.5, 0.5) + bytes([1, 1, 1]) + struct.pack("<I", 1)
    body += b"".join(struct.pack("<iII", *k) for k in keys)
    return struct.pack("<III", len(body) + 8, savegame.checksum(body), len(body)) + body


def test_graphic_options_attributes_in_the_order_of_save_xml():
    attrs = settings.read_graphic_options(GRAPHIC_TEXT)
    assert list(attrs)[:3] == ["Fullscreen", "RenderMethod", "ScreenWidth"]
    assert len(attrs) == 29
    assert attrs["FPSCap"] == "30"


def test_graphic_options_round_trip_is_the_text_the_dc_wrote():
    assert settings.write_graphic_options(settings.read_graphic_options(GRAPHIC_TEXT)) == GRAPHIC_TEXT


def test_graphic_options_keep_an_unknown_attribute():
    text = GRAPHIC_TEXT.replace('DynamicLightQuality="2"', 'DynamicLightQuality="2" Extra="x"')
    attrs = settings.read_graphic_options(text)
    assert attrs["Extra"] == "x"
    assert settings.write_graphic_options(attrs) == text


def test_profile_sample_has_the_size_and_checksum_of_the_dc_file():
    data = sample()
    assert len(data) == 914
    assert data[4:8] == bytes.fromhex("692d032d")


def test_profile_reads_the_fields_in_the_dc_order():
    p = settings.read_profile(sample())
    assert (p.major, p.minor) == (0, 16)
    assert [p.music_volume, p.effects_volume, p.speech_volume, p.rumble_intensity] == pytest.approx([0.8, 0.8, 0.8, 1.0])
    assert (p.auto_pause, p.brightness) == (0.0, 0.5)
    assert p.mouse_sensitivity == pytest.approx(0.5)
    assert (p.camera_y_inverted, p.fly_y_inverted, p.show_damage_values, p.difficulty_level) == (0, 0, 1, 1)
    assert len(p.keycodes) == 70
    assert p.keycodes[0] == settings.Keycode(4, 0x11, 0)
    assert p.keycodes[-1] == settings.Keycode(4, 0x36, 0)


def test_profile_round_trip_is_the_bytes_the_dc_wrote():
    data = sample()
    assert settings.write_profile(settings.read_profile(data)) == data


def test_profile_keeps_a_string():
    data = sample(strings=(b"magic", b"other"))
    p = settings.read_profile(data)
    assert (p.magic_value, p.string_0) == ("magic", "other")
    assert settings.write_profile(p) == data


@pytest.mark.parametrize("bad", [
    lambda d: d[:-1],
    lambda d: d + b"\0",
    lambda d: d[:8] + struct.pack("<I", 0) + d[12:],
    lambda d: d[:4] + struct.pack("<I", 1) + d[8:],
    lambda d: d[:12] + struct.pack("<II", 0, 15) + d[20:],
    lambda d: d[:12] + struct.pack("<II", 1, 16) + d[20:],
])
def test_profile_refuses(bad):
    with pytest.raises(settings.SettingsError):
        settings.read_profile(bad(sample()))


def test_graphic_attribute_table_is_the_file_order():
    assert list(settings.read_graphic_options(GRAPHIC_TEXT)) == list(settings.GRAPHIC_ATTRIBUTES)
