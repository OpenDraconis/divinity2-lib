from __future__ import annotations

import struct
from dataclasses import dataclass, field

from . import Dv2Error, codec

VERSIONS = (44, 48)

HIRC_TYPES = {1: "State", 2: "Sound", 3: "Action", 4: "Event", 5: "RanSeqCntr", 6: "SwitchCntr",
              7: "ActorMixer", 8: "Bus", 9: "LayerCntr", 10: "Segment", 11: "Track",
              12: "MusicSwitch", 13: "MusicRanSeq", 14: "Attenuation", 15: "DialogueEvent",
              16: "FeedbackBus", 17: "FeedbackNode"}

ACTION_TYPES = {
    0x1010: "Stop_E", 0x1011: "Stop_E_O", 0x1020: "Stop_ALL", 0x1021: "Stop_ALL_O",
    0x1040: "Stop_AE", 0x1041: "Stop_AE_O", 0x2010: "Pause_E", 0x2011: "Pause_E_O",
    0x2020: "Pause_ALL", 0x2021: "Pause_ALL_O", 0x2040: "Pause_AE", 0x2041: "Pause_AE_O",
    0x3010: "Resume_E", 0x3011: "Resume_E_O", 0x3020: "Resume_ALL", 0x3021: "Resume_ALL_O",
    0x3040: "Resume_AE", 0x3041: "Resume_AE_O", 0x4011: "Play", 0x5011: "PlayAndContinue",
    0x6010: "Mute_M", 0x6011: "Mute_O", 0x7010: "Unmute_M", 0x7011: "Unmute_O",
    0x7020: "Unmute_ALL", 0x7021: "Unmute_ALL_O", 0x7040: "Unmute_AE", 0x7041: "Unmute_AE_O",
    0x8010: "SetPitch_M", 0x8011: "SetPitch_O", 0x9010: "ResetPitch_M", 0x9011: "ResetPitch_O",
    0x9020: "ResetPitch_ALL", 0x9021: "ResetPitch_ALL_O", 0x9040: "ResetPitch_AE",
    0x9041: "ResetPitch_AE_O", 0xA010: "SetVolume_M", 0xA011: "SetVolume_O",
    0xB010: "ResetVolume_M", 0xB011: "ResetVolume_O", 0xB020: "ResetVolume_ALL",
    0xB021: "ResetVolume_ALL_O", 0xB040: "ResetVolume_AE", 0xB041: "ResetVolume_AE_O",
    0xC010: "SetLFE_M", 0xC011: "SetLFE_O", 0xD010: "ResetLFE_M", 0xD011: "ResetLFE_O",
    0xD020: "ResetLFE_ALL", 0xD021: "ResetLFE_ALL_O", 0xD040: "ResetLFE_AE",
    0xD041: "ResetLFE_AE_O", 0xE010: "SetLPF_M", 0xE011: "SetLPF_O", 0xF010: "ResetLPF_M",
    0xF011: "ResetLPF_O", 0xF020: "ResetLPF_ALL", 0xF021: "ResetLPF_ALL_O",
    0xF040: "ResetLPF_AE", 0xF041: "ResetLPF_AE_O", 0x10010: "UseState_E",
    0x11010: "UnuseState_E", 0x12020: "SetState", 0x20081: "StopEvent", 0x30081: "PauseEvent",
    0x40081: "ResumeEvent", 0x50100: "Duck", 0x60001: "SetSwitch", 0x61001: "SetRTPC",
    0x70010: "BypassFX_M", 0x70011: "BypassFX_O", 0x80010: "ResetBypassFX_M",
    0x80011: "ResetBypassFX_O", 0x80020: "ResetBypassFX_ALL", 0x80021: "ResetBypassFX_ALL_O",
    0x80040: "ResetBypassFX_AE", 0x80041: "ResetBypassFX_AE_O", 0x90010: "Break_E",
    0x90011: "Break_E_O", 0xA0000: "Trigger", 0xA0001: "Trigger_O"}

CURVES = {0: "Log3", 1: "Log2", 2: "Log1", 3: "InvSCurve", 4: "Linear", 5: "SCurve", 6: "Exp1",
          7: "Exp2", 8: "Exp3", 9: "Constant"}
SCALINGS = {0: "None", 1: "db_255", 2: "dB_96_3"}
RTPC_PARAMETERS = {0: "Volume", 1: "LFE", 2: "Pitch", 3: "LPF", 4: "PlayMechanismSpecialTransitionsValue",
                   8: "Priority", 9: "MaxNumInstances", 10: "Positioning_Radius_LPF",
                   11: "Positioning_Divergence_Center_PCT", 12: "Positioning_Cone_Attenuation_ON_OFF",
                   13: "Positioning_Cone_Attenuation", 14: "Positioning_Cone_LPF",
                   20: "Position_PAN_RL", 21: "Position_PAN_FR", 22: "Position_Radius_SIM_ON_OFF",
                   23: "Position_Radius_SIM_Attenuation", 24: "BypassFX0", 25: "BypassFX1",
                   26: "BypassFX2", 27: "BypassFX3", 28: "BypassAllFX", 29: "FeedbackVolume",
                   30: "FeedbackLowpass", 31: "FeedbackPitch"}
POSITIONING = {0: "Undefined", 1: "2D", 2: "3DUserDef", 3: "3DGameDef"}
PATH_MODES = {0: "StepSequence", 1: "StepRandom", 2: "ContinuousSequence", 3: "ContinuousRandom"}
SOURCE_TYPES = {0: "Data", 1: "Streaming", 2: "PrefetchStreaming"}


class WwiseError(Dv2Error):
    pass


def id_of(name: str) -> int:
    h = 0x811C9DC5
    for c in codec.encode(name):
        h = ((h * 0x01000193) & 0xFFFFFFFF) ^ (c + 32 if 65 <= c <= 90 else c)
    return h


@dataclass
class Bank:
    version: int
    id: int
    language: int
    feedback: bool
    header_rest: bytes
    media: dict[int, bytes] = field(default_factory=dict)
    objects: dict[int, dict] = field(default_factory=dict)
    bank_names: dict[int, str] = field(default_factory=dict)
    other: dict[str, bytes] = field(default_factory=dict)
    volume_threshold_db: float | None = None

    def events(self) -> dict[int, dict]:
        return {i: o for i, o in self.objects.items() if o["type"] == "Event"}


class _Reader:
    def __init__(self, data: bytes, pos: int = 0):
        self.data, self.pos = data, pos

    def take(self, fmt: str):
        v = struct.unpack_from("<" + fmt, self.data, self.pos)
        self.pos += struct.calcsize("<" + fmt)
        return v if len(v) > 1 else v[0]

    def raw(self, n: int) -> bytes:
        if self.pos + n > len(self.data):
            raise WwiseError(f"read past the end at {self.pos:#x}")
        b = self.data[self.pos:self.pos + n]
        self.pos += n
        return b

    def u8(self): return self.take("B")
    def s8(self): return self.take("b")
    def u16(self): return self.take("H")
    def u32(self): return self.take("I")
    def s32(self): return self.take("i")
    def f32(self): return self.take("f")

    def points(self, n: int) -> list[dict]:
        return [{"from": self.f32(), "to": self.f32(), "interp": CURVES.get(i := self.u32(), i)}
                for _ in range(n)]


def read(data: bytes) -> Bank:
    r = _Reader(data)
    tag, size = r.raw(4), r.u32()
    if tag != b"BKHD":
        raise WwiseError("not a Wwise bank: no BKHD")
    version, bank_id, language, feedback = r.take("4I")
    if version not in VERSIONS:
        raise WwiseError(f"bank version {version}; this reader knows {VERSIONS}")
    bank = Bank(version, bank_id, language, feedback != 0, r.raw(size - 16))
    index, blob = [], b""
    while r.pos < len(data):
        tag, size = r.raw(4).decode("latin-1"), r.u32()
        end = r.pos + size
        if tag == "DIDX":
            index = [r.take("3I") for _ in range(size // 12)]
        elif tag == "DATA":
            blob = r.raw(size)
        elif tag == "HIRC":
            for _ in range(r.u32()):
                obj = _object(r, bank)
                bank.objects[obj["id"]] = obj
        elif tag == "STID":
            r.u32()
            for _ in range(r.u32()):
                i = r.u32()
                bank.bank_names[i] = r.raw(r.u8()).decode("latin-1")
        elif tag == "STMG":
            bank.other[tag] = raw = r.raw(size)
            if len(raw) >= 4:
                bank.volume_threshold_db = struct.unpack_from("<f", raw)[0]
        else:
            bank.other[tag] = r.raw(size)
        if r.pos != end:
            raise WwiseError(f"chunk {tag} read to {r.pos:#x}, ends at {end:#x}")
    for media_id, offset, length in index:
        bank.media[media_id] = blob[offset:offset + length]
    return bank


def _object(r: _Reader, bank: Bank) -> dict:
    kind, size = r.u32(), r.u32()
    end = r.pos + size
    obj = {"type": HIRC_TYPES.get(kind, kind), "id": r.u32()}
    body = _BODIES.get(kind)
    if body is None:
        obj["raw"] = r.raw(end - r.pos)
    else:
        body(r, obj, bank)
    if r.pos != end:
        raise WwiseError(f"{obj['type']} {obj['id']} read to {r.pos:#x}, ends at {end:#x}")
    return obj


# CAkBankMgr::LoadSource @dbc790 decomp
def _source(r: _Reader, version: int) -> dict:
    plugin, stream = r.u32(), r.u32()
    s = {"plugin": plugin, "stream": SOURCE_TYPES.get(stream, stream)}
    if version <= 46:
        s["sample_rate"], s["format"] = r.u32(), r.u32()
    s["source"], s["file"] = r.u32(), r.u32()
    if stream != 1:
        s["file_offset"], s["size"] = r.u32(), r.u32()
    s["language_specific"] = r.u8() != 0
    if plugin & 0xF in (2, 5):
        s["params"] = r.raw(r.u32())
    return s


COMPRESSOR_FX, PEAK_LIMITER_FX = 0x6C0003, 0x6E0003


# CAkCompressorFXParams::SetParamsBlock @d94ec0, CAkPeakLimiterFXParams::SetParamsBlock @d93f70 decomp
def _fx_params(kind: int, raw: bytes) -> dict | None:
    if kind not in (COMPRESSOR_FX, PEAK_LIMITER_FX) or len(raw) < 22:
        return None
    threshold, ratio, third, release, output_gain_db = struct.unpack_from("<5f", raw)
    p = {"threshold": threshold, "ratio": ratio, "release": release,
         "output_gain_db": output_gain_db, "process_lfe": raw[20] != 0, "channel_link": raw[21] != 0}
    p["attack" if kind == COMPRESSOR_FX else "look_ahead"] = third
    return p


# CAkParameterNodeBase::SetNodeBaseParams @e07ef0 decomp
def _fx_list(r: _Reader, bank: Bank, count: int) -> list[dict]:
    fx = []
    for _ in range(count):
        e = {"index": r.u8(), "fx": r.u32(), "rendered": r.u8() != 0}
        e["params"] = r.raw(r.u32())
        if bank.version >= 47:
            e["bank_data"] = [r.take("2I") for _ in range(r.u32())]
        params = _fx_params(e["fx"], e["params"])
        if params is not None:
            e["decoded"] = params
        fx.append(e)
    return fx


# CAkParameterNodeBase::SetNodeBaseParams @e07ef0 decomp
def _node_base(r: _Reader, bank: Bank) -> dict:
    n = {"override_fx": r.u8() != 0, "fx": []}
    count = r.u8()
    if count:
        n["fx_bypass"] = r.u8()
        n["fx"] = _fx_list(r, bank, count)
    n["override_bus"], n["parent"] = r.u32(), r.u32()
    n["priority"], n["priority_override_parent"] = r.s8(), r.u8() != 0
    n["priority_apply_dist_factor"], n["priority_dist_offset"] = r.u8() != 0, r.s8()
    for p in ("volume", "lfe", "pitch", "lpf"):
        n[p], n[p + "_min"], n[p + "_max"] = r.f32(), r.f32(), r.f32()
    n["state_group"] = r.u32()
    n["positioning"] = _positioning(r)
    n["virtual_queue"], n["kill_newest"], n["max_instances"] = r.u8(), r.u8() != 0, r.u16()
    n["below_threshold"], n["max_instances_override_parent"] = r.u8(), r.u8() != 0
    n["virtual_voices_override_parent"] = r.u8() != 0
    n["state_sync"] = r.u8()
    n["states"] = [{"state": r.u32(), "custom": r.u8(), "state_instance": r.u32()}
                   for _ in range(r.u16())]
    n["rtpc"] = _rtpcs(r)
    if bank.feedback:
        n["feedback_bus"] = r.u32()
        if n["feedback_bus"]:
            n["feedback"] = r.take("3f"), r.take("3f")
    return n


# CAkParameterNode::SetPositioningParams @e03010 decomp
def _positioning(r: _Reader) -> dict | None:
    if not r.u8():
        return None
    p = {"center_pct": r.u32(), "pan_rl": r.f32(), "pan_fr": r.f32()}
    if not r.u8():
        p["type"], p["panner"] = "2D", r.u8() != 0
        return p
    kind = r.u32()
    p["type"], p["attenuation"], p["spatialized"] = POSITIONING.get(kind, kind), r.u32(), r.u8() != 0
    if kind == 3:
        p["dynamic"] = r.u8() != 0
    elif kind == 2:
        mode = r.u32()
        p["path_mode"], p["looping"], p["transition_ms"] = PATH_MODES.get(mode, mode), r.u8() != 0, r.s32()
        p["follow_orientation"] = r.u8() != 0
        p["vertices"] = [r.take("3fi") for _ in range(r.u32())]
        items = r.u32()
        p["playlist"] = [r.take("2I") for _ in range(items)]
        p["ranges"] = [r.take("2f") for _ in range(items)]
    return p


# CAkParameterNodeBase::SetInitialRTPC @e06d80 decomp
def _rtpcs(r: _Reader) -> list[dict]:
    out = []
    for _ in range(r.u16()):
        fx, fx_rendered, rtpc, param, curve, scaling, n = r.take("IBIIIBH")
        out.append({"rtpc": rtpc, "fx": fx, "fx_rendered": fx_rendered != 0,
                    "parameter": RTPC_PARAMETERS.get(param, param), "curve": curve,
                    "scaling": SCALINGS.get(scaling, scaling), "points": r.points(n)})
    return out


# CAkParentNode<CAkParameterNode>::SetChildren @dfa440 decomp
def _children(r: _Reader) -> list[int]:
    return [r.u32() for _ in range(r.u32())]


# CAkSound::SetInitialValues @df9740 decomp
def _sound(r, o, bank):
    o["source"] = _source(r, bank.version)
    o["node"] = _node_base(r, bank)
    o["loop"], o["loop_min"], o["loop_max"] = r.take("3h")


# CAkRanSeqCntr::SetInitialValues @dfc230 decomp
def _ranseq(r, o, bank):
    o["node"] = _node_base(r, bank)
    o["loop"] = r.u16()
    o["transition"], o["transition_min"], o["transition_max"] = r.take("3f")
    o["avoid_repeat"], o["transition_mode"], o["random_mode"], o["mode"] = r.take("H3B")
    o["mode"] = {0: "Random", 1: "Sequence"}.get(o["mode"], o["mode"])
    o["random_mode"] = {0: "Normal", 1: "Shuffle"}.get(o["random_mode"], o["random_mode"])
    o["using_weight"], o["reset_playlist"], o["restart_backward"], o["continuous"], o["global"] = \
        (b != 0 for b in r.take("5B"))
    o["children"] = _children(r)
    o["playlist"] = [{"id": r.u32(), "weight": r.u8()} for _ in range(r.u16())]


# CAkActorMixer::SetInitialValues @dffba0 decomp
def _actor_mixer(r, o, bank):
    o["node"] = _node_base(r, bank)
    o["children"] = _children(r)


# CAkLayerCntr::SetInitialValues @dff6f0, CAkLayer::SetInitialValues @e092c0 decomp
def _layer_cntr(r, o, bank):
    o["node"] = _node_base(r, bank)
    o["children"] = _children(r)
    o["layers"] = []
    for _ in range(r.u32()):
        layer = {"id": r.u32(), "rtpc": _rtpcs(r), "crossfade_rtpc": r.u32(), "crossfade_default": r.f32()}
        layer["children"] = [{"child": r.u32(), "points": r.points(r.u32())} for _ in range(r.u32())]
        o["layers"].append(layer)


# CAkEvent::SetInitialValues @df9170 decomp
def _event(r, o, bank):
    o["actions"] = [r.u32() for _ in range(r.u32())]


# CAkActionExcept::SetExceptParams @e209e0 decomp
def _except(r) -> list[int]:
    return [r.u32() for _ in range(r.u32())]


# CAkAction::SetInitialValues @df2b00 decomp
def _action(r, o, bank):
    kind = r.u32()
    o["action"] = ACTION_TYPES.get(kind, kind)
    o["target"] = r.u32()
    o["delay_ms"], o["delay_min"], o["delay_max"] = r.take("3i")
    sub = r.u32()
    if not sub:
        return
    end = r.pos + sub
    group = kind >> 12
    if group == 0x70 or group == 0x80:
        o["bypass"], o["target_mask"] = r.u8() != 0, r.u8()
        o["exceptions"] = _except(r)
    elif group in (0x10, 0x11, 0x12, 0x20, 0x30, 0x40, 0x50, 0x60, 0x61, 0x90, 0xA0):
        o["params"] = r.raw(sub)
    else:
        o["fade_ms"], o["fade_min"], o["fade_max"] = r.take("3i")
        curve = r.u8() & 0x1F
        o["fade_curve"] = CURVES.get(curve, curve)
        specific = r.raw(16)
        if group in (0x8, 0xA, 0xC, 0xE):
            meaning, o["value"], o["value_min"], o["value_max"] = struct.unpack("<I3f", specific)
            o["meaning"] = {0: "Default", 1: "Independent", 2: "Offset"}.get(meaning, meaning)
        elif group in (0x2, 0x3):
            o["include_pending"] = struct.unpack_from("<I", specific)[0] != 0
        elif any(specific):
            o["specific"] = specific
        o["exceptions"] = _except(r)
    if r.pos != end:
        raise WwiseError(f"action {o['id']} ({o['action']}) params read to {r.pos:#x}, end {end:#x}")
    if group in (0x4, 0x5):
        o["file"] = r.u32()


# CAkAttenuation::SetInitialValues @e00390 decomp
def _attenuation(r, o, bank):
    if r.u8():
        o["cone"] = {"inside_deg": r.f32(), "outside_deg": r.f32(), "outside_volume": r.f32(),
                     "lowpass": r.f32()}
    o["curve_to_use"] = list(r.take("5b"))
    o["curves"] = []
    for _ in range(r.u8()):
        scaling, n = r.u8(), r.u16()
        o["curves"].append({"scaling": SCALINGS.get(scaling, scaling), "points": r.points(n)})
    o["rtpc"] = _rtpcs(r)


# CAkBus::SetInitialValues @df5b40, CAkBus::AddDuck @df5aa0 decomp
def _bus(r, o, bank):
    o["override_bus"] = r.u32()
    o["volume"], o["lfe"], o["pitch"], o["lpf"] = r.f32(), r.f32(), r.f32(), r.f32()
    o["kill_newest"] = r.u8() != 0
    o["max_instances"] = r.u16()
    o["max_instances_override_parent"] = r.u8() != 0
    o["priority_apply_dist_factor"], o["priority_override_parent"] = r.u8(), r.u8()
    o["state_group"] = r.u32()
    o["recovery_time"] = r.s32()
    o["max_duck_volume"] = r.f32()
    o["state_sync_type"] = r.u32()
    o["ducks"] = [{"bus": r.u32(), "volume": r.f32(), "fade_out": r.s32(), "fade_in": r.s32(),
                   "curve": CURVES.get(c := r.u8(), c)} for _ in range(r.u32())]
    o["fx"] = []
    if bank.version >= 46:
        count = r.u8()
        if count:
            o["fx_bypass"] = r.u8()
            o["fx"] = _fx_list(r, bank, count)
    o["rtpc"] = _rtpcs(r)
    o["states"] = [{"state": r.u32(), "custom": r.u8(), "state_instance": r.u32()}
                   for _ in range(r.u32())]
    if bank.feedback:
        o["feedback_bus"] = r.u32()
        if o["feedback_bus"]:
            o["feedback"] = r.take("3f"), r.take("3f")


_BODIES = {2: _sound, 3: _action, 4: _event, 5: _ranseq, 7: _actor_mixer, 8: _bus, 9: _layer_cntr,
           14: _attenuation}
