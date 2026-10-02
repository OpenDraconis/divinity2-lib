from __future__ import annotations

import base64
import dataclasses
import struct

from . import Dv2Error
from . import savegame


USAGE = """python -m dv2lib.savestate to-json <save.dsg> <out.json>
    python -m dv2lib.savestate to-dsg <in.json> <out.dsg>
    python -m dv2lib.savestate round-trip <save.dsg>..."""


class StateError(Dv2Error, ValueError):
    pass


class _Absent:
    def __getitem__(self, key):
        return self

    def __iter__(self):
        return iter(())

    def __len__(self) -> int:
        return 0

    def __contains__(self, key) -> bool:
        return False


ABSENT = _Absent()


class Visitor:
    def __init__(self, data: bytes | None, objects: bool, version: tuple[int, int], story: bytes = b""):
        self.reading = data is not None
        self.d = data if self.reading else bytearray()
        self.q, self.objects, self.version, self.story = 0, objects, version, story

    def _io(self, fmt: str, values):
        if self.reading:
            v = struct.unpack_from(fmt, self.d, self.q)
            self.q += struct.calcsize(fmt)
            return v
        self.d += struct.pack(fmt, *values)
        return tuple(values)

    def raw(self, n: int, b: bytes = b"") -> bytes:
        if self.reading:
            b = bytes(self.d[self.q:self.q + n])
            self.q += n
            return b
        self.d += b
        return b

    # CRpgStats_V2_LoadBinaryVisitor::LoadSaveImpl @98b0e0 decomp
    def int(self, x=0) -> int:
        return self._io("<i", (x,))[0]

    # CRpgStats_V2_LoadBinaryVisitor::LoadSaveImpl @98b6a0 decomp
    def uint(self, x=0) -> int:
        return self._io("<I", (x,))[0]

    # CRpgStats_V2_LoadBinaryVisitor::LoadSaveImpl @98b6d0 decomp
    def short(self, x=0) -> int:
        return self._io("<H", (x,))[0]

    # CRpgStats_V2_LoadBinaryVisitor::LoadSaveImpl @98b110 decomp
    def float(self, x=0.0) -> float:
        return self._io("<f", (x,))[0]

    # CRpgStats_V2_LoadBinaryVisitor::LoadSaveImpl @98b1a0 decomp
    def bool(self, x=False) -> bool | int:
        b = self._io("<B", (x if type(x) is int else 1 if x else 0,))[0]
        return b if b > 1 else b == 1

    # CRpgStats_V2_LoadBinaryVisitor::LoadSaveImpl @98b490 decomp
    def string(self, x="") -> str:
        b = b"" if self.reading else x.encode("latin-1")
        return self.raw(self.uint(len(b)), b).decode("latin-1")

    chars = string

    # CRpgStats_V2_LoadBinaryVisitor::LoadSaveImpl @98b730 decomp
    def buffer(self, n: int, b: bytes = b"") -> bytes:
        self.uint(n)
        return self.raw(n, b)

    # CRpgStats_V2_LoadBinaryVisitor::LoadSaveImpl @98b1d0 decomp
    def point3(self, x=(0.0,) * 3) -> list[float]:
        return list(self._io("<3f", x))

    # CRpgStats_V2_LoadBinaryVisitor::LoadSaveImpl @98b250 decomp
    def point2(self, x=(0.0,) * 2) -> list[float]:
        return list(self._io("<2f", x))

    # CRpgStats_V2_LoadBinaryVisitor::LoadSaveImpl @98b2b0 decomp
    def color(self, x=(0.0,) * 3) -> list[float]:
        return list(self._io("<3f", x))

    # CRpgStats_V2_LoadBinaryVisitor::LoadSaveImpl @98b330 decomp
    def colora(self, x=(0.0,) * 4) -> list[float]:
        return list(self._io("<4f", x))

    # CRpgStats_V2_LoadBinaryVisitor::LoadSaveImpl @98b3c0 decomp
    def bound(self, x=(0.0,) * 4) -> list[float]:
        return list(self._io("<4f", x))

    # CRpgStats_V2_LoadBinaryVisitor::LoadSaveImpl @98af50 decomp
    def matrix3(self, x=(0.0,) * 9) -> list[float]:
        return list(self._io("<9f", x))

    # CRpgStats_V2_LoadBinaryVisitor::GetSetAmountOfChildren @98b7a0 decomp
    def count(self, seq) -> int:
        return self.uint(len(seq))

    def each(self, seq, counter=None) -> list:
        n = self.count(seq) if counter is None else counter(len(seq))
        return [ABSENT] * n if self.reading else list(seq)

    def many(self, seq, kind: str, counter=None) -> list:
        return [getattr(self, kind)(x) for x in self.each(seq, counter)]

    def record(self, d, **kinds: str) -> dict:
        return {k: getattr(self, kind)(d[k]) for k, kind in kinds.items()}

    def since(self, major: int, minor: int) -> bool:
        return self.version >= (major, minor)

    # CRpgStats_V2_LoadBinaryVisitor::BeginObject @98bee0 decomp, CRpgStats_V2_LoadBinaryVisitor::EndObject @98bdc0 decomp
    def begin(self, checksum: int = 0) -> None:
        if self.objects:
            self.uint(checksum)


def _fixed(v: Visitor, seq, n: int, kind: str) -> list:
    return [getattr(v, kind)(seq[i]) for i in range(n)]


# CRpgStats_V2_TrophiesManager::GameSaveLoad @97b920 decomp, CRpgStats_V2_Trophy::GameSaveLoad @97b2a0 decomp
def trophies(v: Visitor, d) -> dict:
    v.begin()
    out = []
    for t in v.each(d["Trophies"]):
        rec = v.record(t, Handle="int", PrototypeUUID="string")
        v.begin()
        rec.update(v.record(t, Count="int", Name="string", Picture="string", Prototype="string",
                            Background="string"))
        out.append(rec)
    return {"Trophies": out}


# CRpgStats_V2_TimerManager::GameSaveLoad @915250 decomp
def timers(v: Visitor, d) -> dict:
    return {"Timers": [v.record(t, UUID="string", Duration="float") for t in v.each(d["Timers"])]}


# CGameLogic_SyncData::GameSaveLoad @778cf0 decomp
def sync_data(v: Visitor, d) -> dict:
    v.begin()
    return v.record(d, RenderShadows="bool", HideInShadows="bool", TimeName="string")


# CRpgStats_V2_NameManager::GameSaveLoad @984a00 decomp
def names(v: Visitor, d) -> dict:
    v.begin()
    return {"Names": [v.record(n, UUID="string", Name="string") for n in v.each(d["Names"])]}


# CGameLogic_ItemSets::GameSaveLoad @92d9b0 decomp
def item_sets(v: Visitor, d) -> dict:
    v.begin()
    out = []
    for s in v.each(d["ItemSets"]):
        v.begin()
        out.append(v.record(s, LeftHandHandle="int", RightHandHandle="int"))
    return {"ItemSets": out}


def player_control(v: Visitor, d) -> dict:
    v.begin()
    looks = lambda x: v.record(x, faceModel="string", hairModel="string", skinTone="string", eyesModel="string")
    out = {"MaleLooks": looks(d["MaleLooks"]), "FemaleLooks": looks(d["FemaleLooks"]),
           "AllowSilverEyes": v.bool(d["AllowSilverEyes"]), "Handles": v.many(d["Handles"], "int"),
           **v.record(d, FearOfTheDragonStage="int", TimeSinceFearOfTheDragon="float"),
           "FearOfTheDragonFleeList": v.many(d["FearOfTheDragonFleeList"], "int"),
           **v.record(d, InTownArea="bool", JumpBackFallOffSystemActive="bool",
                      JumpBackFallOffSystemUseTerrain="bool", SlowDragonMode="bool", AllowDragonStone="bool",
                      RequestedDelayedMorph="bool", InDreamScene="bool", TimeTillNextPetCheck="int",
                      ItemInMouseAnchor="int")}
    if v.since(1, 0x23):
        out["unnamed_6f5bae"] = v.int(d["unnamed_6f5bae"])
    if v.since(1, 0x24):
        out["OriginalVersion"] = _fixed(v, d["OriginalVersion"], 2, "int")
    if v.since(2, 3):
        out["unnamed_6f5cb6"] = _fixed(v, d["unnamed_6f5cb6"], 2, "int")
    if v.since(2, 0x18):
        out["unnamed_6f5cef"] = v.bool(d["unnamed_6f5cef"])
    if v.since(2, 0xD):
        out["unnamed_6f5d26"] = v.float(d["unnamed_6f5d26"])
        out["unnamed_6f5d4a"] = [v.record(x, name="string", position="point3", value="float")
                                 for x in v.each(d["unnamed_6f5d4a"])]
    if v.since(2, 0xA):
        out["unnamed_6f61c2"] = v.int(d["unnamed_6f61c2"])
    if v.since(2, 4):
        out["unnamed_6f61f1"] = v.bool(d["unnamed_6f61f1"])
    if v.since(2, 0x14):
        out["unnamed_6f6220"] = v.bool(d["unnamed_6f6220"])
    out["GameStats"] = v.record(d["GameStats"], MonsterLevel="int", TotalGold="int", MindReads="int",
                                Monsters="int", TimePlayed="float")
    if v.since(2, 0x11):
        out.update(v.record(d, CharTeleportDestination="point3", CharTeleportOrientation="point3"))
    return out


def encounter(v: Visitor, d) -> dict:
    out = []
    for x in v.each(d["Encounters"], v.int):
        e = v.record(x, float="float", int="int")
        if v.since(2, 0x1B):
            e["bool"] = v.bool(x["bool"])
        out.append(e)
    return {"Encounters": out}


# CGameLogic_PlayerControl_UserInterface::GameSaveLoad @809510 decomp
def pc_user_interface(v: Visitor, d) -> dict:
    out = []
    for i in range(7):
        v.begin()
        out.append([v.record(x, InventoryPosHelper="string", int="int")
                    for x in v.each(d["InventoryPosHelpers"][i])])
    return {"InventoryPosHelpers": out}


def _empty_list(v: Visitor, seq, what: str, reader: str) -> list:
    n = v.count(seq)
    if n:
        raise StateError(f"{what}: {n} elements; the element layout ({reader}) is not read yet")
    return []


# CDialogLogManager::GameSaveLoad @9187c0 decomp
def dialog_logs(v: Visitor, d) -> dict:
    v.begin()
    return {"CurrentTime": v.float(d["CurrentTime"]),
            "Entries": _empty_list(v, d["Entries"], "DialogLogs",
                                   "DC 816f5a: TimeStamp, Locutor, Owner, Text, bIsNew, [2.25] bool")}


# CRpgStats_V2_QuestManager::GameSaveLoad @96f3f0 decomp
def quests(v: Visitor, d) -> dict:
    v.begin()
    return {"Quests": _empty_list(v, d["Quests"], "Quests", "DC 8aa542: PrototypeName, Handle, Quest 8a9ef0")}


def region_cache(v: Visitor, d) -> dict:
    v.begin()
    if d["Cache"]:
        raise StateError("RegionCache: the cache data (GameSaveLoadCacheData DC 84eba0) is not read yet")
    end = v.record({"RegionName": "", "SubRegionName": "", "CacheSize": 0},
                   RegionName="string", SubRegionName="string", CacheSize="uint")
    if end["CacheSize"]:
        raise StateError(f"RegionCache {end}: the cache data (GameSaveLoadCacheData DC 84eba0) is not read yet")
    return {"Cache": []}


# CGameLogic_Projectile_Manager::GameSaveLoad @8b8840 decomp
def projectiles(v: Visitor, d) -> dict:
    v.begin()
    return {"Projectiles": _empty_list(v, d["Projectiles"], "Projectiles", "DC 7d3658: Handle, Projectile 8f01f0")}


# CRpgStats_V2_GameEventManager::GameSaveLoad @897120 decomp
def game_events(v: Visitor, d) -> dict:
    v.begin()
    return {"Events": _empty_list(v, d["Events"], "GameEvents", "DC 7b6336: argument descriptions")}


# CGameLogic_DialogControl::GameSaveLoad @802040 decomp
def dialog_control(v: Visitor, d) -> dict:
    v.begin()
    return {"Dialogs": _empty_list(v, d["Dialogs"], "DialogControl", "GUP 802040: 2 strings, int, 2 floats, bool")}


# CRpgStats_V2_EffectArea_Manager::GameSaveLoad @9118e0 decomp
def effect_areas(v: Visitor, d) -> dict:
    v.begin()
    out = []
    for i, a in enumerate(v.each(d["EffectAreas"])):
        kind = v.int(a["Type"])
        if kind:
            raise StateError(f"EffectArea slot {i}: type {kind}; the area layout (vtable +0x28) is not read yet")
        out.append({"Type": kind})
    return {"EffectAreas": out}


def _mapped_button(v: Visitor, b) -> dict:
    v.begin()
    return v.record(b, m_eType="int", m_Handle="int", m_sIconName="string")


# CGameLogic_ButtonMappings::GameSaveLoad @92c6f0 decomp
def button_mappings(v: Visitor, d) -> dict:
    v.begin()
    return {"Human": [_mapped_button(v, b) for b in v.each(d["Human"])],
            "Dragon": [_mapped_button(v, b) for b in v.each(d["Dragon"])]}


def map_coordinates(v: Visitor, d) -> dict:
    out = {}
    for r in v.each(list(d["Regions"])):
        region = v.string(r)
        out[region] = v.many(d["Regions"][r], "string")
    return {"Regions": out}


# CRpgStats_V2_BattleTower::GameSaveLoad @8fb9d0 decomp
def battle_tower(v: Visitor, d) -> dict:
    v.begin()
    out = v.record(d, LastRegion="string", LastSubRegion="string", LastPosition="point3", LastFlyingState="bool")
    if v.since(1, 0x26):
        out["unnamed_7bd62a"] = v.int(d["unnamed_7bd62a"])
    if v.since(1, 0x27):
        out["unnamed_7bd65b"] = v.int(d["unnamed_7bd65b"])
    out["ActivePlatform"] = v.int(d["ActivePlatform"])
    a = d["NecromancersAlcove"]
    v.begin()
    alcove = v.record(a, DefaultLimbsCreated="bool", UpgradeLevel="int", SummonedCreatureHandle="int")
    if v.since(1, 0x1C):
        alcove["SummonedCreatureBonusType"] = v.int(a["SummonedCreatureBonusType"])
    if v.since(1, 0x1A):
        alcove.update(v.record(a, SelectedHead="uint", SelectedBody="uint", SelectedArms="uint", SelectedLegs="uint"))
        for limb in ("Heads", "Bodies", "Arms", "Legs"):
            if v.count(a[limb]):
                raise StateError(f"BattleTower alcove {limb}: the limb layout (DC 9caed0..) is not read yet")
            alcove[limb] = []
    out["NecromancersAlcove"] = alcove
    formulas = lambda f: [v.record(x, name="string", Formula="int") for x in v.each(f)]
    p = d["Platform_9cf9d0"]
    v.begin()
    out["Platform_9cf9d0"] = {"UpgradeLevel": v.int(p["UpgradeLevel"]), "Formulas": formulas(p["Formulas"])}
    v.begin()
    out["TrainingArena"] = v.record(d["TrainingArena"], UpgradeLevel="int")
    p = d["Platform_9ce4c0"]
    v.begin()
    out["Platform_9ce4c0"] = {**v.record(p, UpgradeLevelWeapons="int", UpgradeLevelArmor="int",
                                         UpgradeLevelJewelry="int"), "Formulas": formulas(p["Formulas"])}
    return out


# CRpgstats_V2_Alignment::GameSaveLoad @964b10 decomp, CRpgstats_V2_AlignmentMap::GameSaveLoad @a76590 decomp
def alignment(v: Visitor, d) -> dict:
    v.begin()
    out = {"Groups": [{"GroupName": v.string(g["GroupName"]), "ParentNames": v.many(g["ParentNames"], "string")}
                      for g in v.each(d["Groups"])]}
    for tag, first, second in (("C_C_Alignment", "int", "int"), ("F_C_Alignment", "string", "int"),
                               ("C_F_Alignment", "int", "string"), ("F_F_Alignment", "string", "string")):
        v.begin()
        out[tag] = [{"First": getattr(v, first)(e["First"]),
                     "Values": [{"Second": getattr(v, second)(x["Second"]), "Value": v.int(x["Value"])}
                                for x in v.each(e["Values"])]}
                    for e in v.each(d[tag])]
    return out


# CRpgStats_V2_WayPointManager::GameSaveLoad @93b990 decomp, CRpgStats_V2_WayPoint::GameSaveLoad @a1ac30 decomp
def waypoints(v: Visitor, d) -> dict:
    v.begin()
    out = []
    for w in v.each(d["WayPoints"]):
        rec = v.record(w, Handle="int", UUID="string")
        v.begin()
        rec.update(v.record(w, IsActive="bool", Discovered="bool", ItemUUID="string", Name="string",
                            TriggerUUID="string"))
        out.append(rec)
    return {"WayPoints": out}


# CGameLogic_MapMarker_Manager::GameSaveLoad @9399c0 decomp, CGameLogic_MapMarker::GameSaveLoad @939430 decomp
def map_markers(v: Visitor, d) -> dict:
    v.begin()
    out = []
    for x in v.each(d["MapMarkers"]):
        m = v.record(x, Handle="int")
        v.begin()
        m.update(v.record(x, UUID="string", RegionName="string", SubRegionName="string", Position="point2",
                          ShowOnWorldMap="bool", ShowOnRegionMap="bool", ShowOnDetailMap="bool", Show="bool",
                          PlayerMarker="bool", Icon="string", Label="string"))
        if v.since(2, 0):
            m["mItemHandle"] = v.int(x["mItemHandle"])
        out.append(m)
    return {"MapMarkers": out}


# CGameLogic_Effect::GameSaveLoad @89a7b0 decomp
def _effect(v: Visitor, e) -> dict:
    v.begin()
    return v.record(e, string1="string", string2="string", Scale="float", Translate="point3", Rotate="matrix3")


def _character_effect(v: Visitor, e) -> dict:
    out = v.record(e, Handle="int", PrototypeUUID="string")
    if v.since(2, 6):
        out["CallerType"] = v.int(e["CallerType"])
    out["CallerName"] = v.string(e["CallerName"])
    out["Effect"] = _effect(v, e["Effect"])
    return out


# CRpgStats_V2_PerpetualStateManager::GameSaveLoad @89c150 decomp
def perpetual_state(v: Visitor, d) -> dict:
    v.begin()
    out = {"CharacterEffects": [_character_effect(v, e) for e in v.each(d["CharacterEffects"])],
           "ItemEffects": [v.record(e, UUID="string", FileID="string", AnimationID="int", IsACharacter="bool",
                                    Scale="float", Translate="point3", Rotate="matrix3")
                           for e in v.each(d["ItemEffects"])],
           "CustomAnimations": [v.record(e, AnimationName="string", CharacterHandle="int")
                                for e in v.each(d["CustomAnimations"])],
           "CulledScenery": [v.record(e, SceneryUUID="string", IsCulled="bool") for e in v.each(d["CulledScenery"])]}
    if v.since(1, 0x17):
        out["CulledSceneryNames"] = v.many(d["CulledSceneryNames"], "string")
    if v.since(2, 8):
        h = d["HitEffectParams"]
        out["HitEffectParams"] = {**v.record(h, bool1="bool", bool2="bool", bool3="bool", int="int", bool4="bool"),
                                  "floats": _fixed(v, h["floats"], 4, "float"),
                                  **v.record(h, color1="color", color2="color", uint="uint")}
    if v.since(2, 6):
        out["TriggerEffects"] = [{**v.record(e, Handle="int", CallerType="int", CallerName="string"),
                                  "Effect": _effect(v, e["Effect"])} for e in v.each(d["TriggerEffects"])]
    if v.since(1, 0x28):
        out["StoryLights"] = [v.record(e, Name="string", RegionName="string", SubRegionName="string", Active="bool")
                              for e in v.each(d["StoryLights"])]
    if v.since(1, 0x10):
        out["StorySoundbanks"] = [v.record(e, SoundbankName="string", IsLocal="bool")
                                  for e in v.each(d["StorySoundbanks"])]
    if v.since(2, 0x12):
        out["EffectPreloads"] = [v.record(e, PrototypeUUID="string") for e in v.each(d["EffectPreloads"])]
    if v.since(2, 0x15):
        out["LuaGameTime"] = v.float(d["LuaGameTime"])
    if v.since(1, 9):
        out["ActiveSubtitle"] = v.string(d["ActiveSubtitle"])
    if v.since(1, 0xE):
        out["RiftTimerTimeLeft"] = v.float(d["RiftTimerTimeLeft"])
    if v.since(2, 3):
        out["unnamed_882ffb"] = _fixed(v, d["unnamed_882ffb"], 2, "int")
    return out


def _unb64(x) -> bytes:
    return b"" if x is ABSENT else base64.b64decode(x)


# CLuaVariableManager::GameSaveLoad @8f5e60 decomp, CLuaVariableManager_Key2Table::GameSaveLoad @8f5900 decomp
def lua_variables(v: Visitor, d) -> dict:
    v.begin()
    out = {"Lists": {}}
    for name in ("int", "double", "char*", "int*", "NiPoint3"):
        src = d["Lists"][name]
        lst = v.record(src, RealListSize="int", ListSize="int", RealFreeListSize="int", FreeListSize="int")
        if lst["RealListSize"]:
            if name == "char*":
                lst["Values"] = [v.record(src["Values"][i], uint="uint", chars="string")
                                 for i in range(lst["ListSize"])]
            else:
                b = _unb64(src["Values"])
                lst["Values"] = base64.b64encode(v.raw(v.uint(len(b)), b)).decode()
        if lst["RealFreeListSize"]:
            lst["Free"] = _fixed(v, src["Free"], lst["FreeListSize"], "int")
        out["Lists"][name] = lst
    out["Tables"] = []
    for i in range(8):
        t = d["Tables"][i]
        if not v.bool(t is not None):
            out["Tables"].append(None)
            continue
        table = v.record(t, count="int", capacity="int")
        slots = []
        for j in range(table["count"]):
            s = t["slots"][j]
            key, n = v.uint(s["key"]), v.uint((len(s["values"]) - 1) // 2 if s["values"] else 0)
            slots.append({"key": key, "values": _fixed(v, s["values"], 2 * n + 1, "int") if n else []})
        out["Tables"].append({**table, "slots": slots})
    p = d["NamePool"]
    pool = {"used": v.int(p["used"]), "offsets": _fixed(v, p["offsets"], 512, "int"),
            "buckets": [v.many(p["buckets"][i], "int") for i in range(0x301)], "top": v.int(p["top"])}
    size = 0x8000 if v.since(2, 0x17) else 0x4000
    names = "\0".join(p["names"]).encode("latin-1").ljust(size, b"\0")
    pool["names"] = v.buffer(size, names).rstrip(b"\0").decode("latin-1").split("\0")
    out["NamePool"] = pool
    return out


# COsirisManager::GameSaveLoad @80b270 decomp
def story(v: Visitor, d) -> dict:
    v.begin()
    out = v.record(d, OsirisStoryStarted="bool", OsirisChunkBuffer="int")
    if not v.reading:
        v.d += savegame.blocks(v.story)
        out["StoryBytes"] = len(v.story)
        return out
    total = 0
    while True:
        _, n = v.uint(), v.uint()
        v.q += n
        total += n
        if n < out["OsirisChunkBuffer"]:
            break
    out["StoryBytes"] = total
    return out


# CRpgStats_V2_TriggerManager::GameSaveLoad @816f40 decomp
TRIGGER_TYPES = {1: "TriggerSphere", 2: "TriggerPoint", 3: "TriggerTeleport", 4: "TriggerArea",
                 5: "TriggerOrientation", 8: "TriggerSound", 9: "TriggerTrapArea", 10: "TriggerEffectArea",
                 11: "TriggerRepel", 12: "TriggerPlayerSpawnPoint", 13: "TriggerPointSound",
                 14: "TriggerAntiDragon", 15: "TriggerTownArea", 16: "TriggerStartVisualEffectArea",
                 17: "TriggerStopVisualEffectArea", 18: "TriggerVisualEffectPoint",
                 19: "TriggerAutoSaveCheckpoint", 20: "TriggerPainArea", 21: "TriggerPointEncounter",
                 22: "TriggerEncounterZone"}
_TRIGGER_KINDS = {name: kind for kind, name in TRIGGER_TYPES.items()}


# CRpgStats_V2_Trigger::GameSaveLoad @8997b0 decomp
def _trigger(v: Visitor, t) -> dict:
    return v.record(t, RegionName="string", SubRegionName="string", IsActive="bool")


# CRpgStats_V2_Trigger_Point::GameSaveLoad @780110 decomp
def _trigger_point(v: Visitor, t) -> dict:
    return {**_trigger(v, t), "Translate": v.point3(t["Translate"])}


# CRpgStats_V2_Trigger_Orientation::GameSaveLoad @780a10 decomp
def _trigger_orientation(v: Visitor, t) -> dict:
    return {**_trigger_point(v, t), "Rotate": v.matrix3(t["Rotate"])}


# CRpgStats_V2_Trigger_Area::InheritedGameSaveLoad @9c8900 decomp, CPolyArea::GameSaveLoad @77ef60 decomp
def _trigger_area(v: Visitor, t) -> dict:
    out = _trigger(v, t)
    out["Points"] = [v.record(p, ID="string", Point="point3") for p in v.each(t["Points"])]
    out.update(v.record(t, Bottom="float", Top="float"))
    if v.since(1, 0x13):
        out["SoundEventName"] = v.string(t["SoundEventName"])
    out.update(v.record(t, ForceFullCheck="bool", CheckItems="bool"))
    for name in ("CharacterInsideList", "ItemInsideList", "CharacterToCheckList", "ItemToCheckList"):
        out[name] = v.many(t[name], "int")
    return out


def _extend(base, extra):
    return lambda v, t: {**base(v, t), **extra(v, t)}


def _point_sound(v: Visitor, t) -> dict:
    out = {"SoundEventName": v.string(t["SoundEventName"])}
    if v.since(2, 0xB):
        out["unnamed_97647e"] = v.bool(t["unnamed_97647e"])
    return out


TRIGGER_READERS = {
    2: (True, _trigger_point),
    3: (True, _extend(_trigger_point, lambda v, t: v.record(
        t, Center="point3", ToCenter="point3", RigidBodyName="string", DestinationRegion="string",
        DestinationSubRegion="string"))),
    4: (True, _trigger_area),
    5: (True, _trigger_orientation),
    8: (True, _extend(_trigger_area, lambda v, t: {"SoundbankNames": v.many(t["SoundbankNames"], "string")})),
    9: (True, _extend(_trigger_area, lambda v, t: v.record(t, TrapHandle="int", NPCCanTrigger="bool"))),
    10: (True, _extend(_trigger_area, lambda v, t: v.record(
        t, DamagePerTick="float", TickInterval="float", ExposureTime="float", EffectAreaType="int",
        EffectAreaHandle="int"))),
    11: (True, _extend(_trigger_area, lambda v, t: v.record(t, FactionName="string"))),
    12: (True, _trigger_orientation),
    13: (True, _extend(_trigger_point, _point_sound)),
    14: (True, _extend(_trigger_point, lambda v, t: v.record(
        t, OuterRingRadius="float", InnerRingRadius="float", ValidRadii="bool", DeviceEnabled="bool",
        TimeSinceLastDamage="float", unnamed_float="float", unnamed_bool="bool"))),
    15: (True, _trigger_area),
    16: (False, _trigger_area),
    17: (False, _trigger_area),
    18: (True, _trigger_orientation),
    19: (True, _extend(_trigger_area, lambda v, t: v.record(t, SavePerformed="bool"))),
    20: (True, _extend(_trigger_area, lambda v, t: v.record(t, TimeSinceLastDamage="float"))),
    21: (True, _extend(_trigger_point, lambda v, t: {"string": v.string(t["string"]),
                                                     "Handles": v.many(t["Handles"], "int", v.int),
                                                     "bools": _fixed(v, t["bools"], 4, "bool")})),
    22: (True, _trigger_area),
}


def triggers(v: Visitor, d) -> dict:
    v.begin()
    out = []
    for t in v.each(d["Triggers"]):
        handle, uuid = v.int(t["Handle"]), v.string(t["UUID"])
        kind = v.int(_TRIGGER_KINDS.get(t["Type"], t["Type"]))
        if kind not in TRIGGER_READERS:
            raise StateError(f"trigger {uuid}: type {kind} has no reader")
        checksum, reader = TRIGGER_READERS[kind]
        if checksum:
            v.begin()
        out.append({"Handle": handle, "UUID": uuid, "Type": TRIGGER_TYPES.get(kind, kind), **reader(v, t)})
    return {"Triggers": out}


# CDialogManager::GameSaveLoad @874300 decomp, CRpgStats_V2_EventManager::GameSaveLoad @80c0d0 decomp, CRpgStats_V2_GlobalEventManager::SetEventState @80bc20 decomp
def dialogs(v: Visitor, d) -> dict:
    v.begin()
    out = {}
    for name in ("GlobalFlags", "LocalFlags"):
        v.begin()
        out[name] = [v.record(e, UUID="string", State="bool") for e in v.each(d[name])]
    return out


# CRpgStats_V2_InventoryManager::GameSaveLoad @96ca40 decomp, CRpgStats_V2_Inventory::GameSaveLoad @8c7cc0 decomp
def inventories(v: Visitor, d) -> dict:
    v.begin()
    out = []
    for r in v.each(d["Inventories"]):
        rec = v.record(r, Handle="int", PrototypeUUID="string", IsLocal="bool")
        v.begin()
        rec.update(v.record(r, PrototypeHandle="int", OwnerType="int", OwnerHandle="int", MaxSlots="int",
                            MaxEquipmentSlots="int"))
        rec["Items"] = [v.record(x, Slot="int", Handle="int") for x in v.each(r["Items"])]
        out.append(rec)
    return {"Inventories": out}


# CRpgStats_V2_Item_Mover::GameSaveLoad @a43920 decomp
def _item_mover(v: Visitor, m) -> dict:
    return {**v.record(m, ItemMove_Moving="bool", ItemMove_Destination="point3", ItemMove_Velocity="float",
                       ItemMove_MaxVelocity="float", ItemMove_MovingWithSineSpeed="bool",
                       ItemMove_TravelDistance="float", ItemMove_OnArrivalText="string"),
            "Targets": [v.record(x, TargetType="int", TargetHandle="int") for x in v.each(m["Targets"])]}


# CRpgStats_V2_ItemStateManagerFactory::CreateManager @a4f880 decomp
STATE_FUNCTIONS = {"Door", "CheckDoor", "Openable", "Destructible", "OpenableDestructible"}


# CRpgStats_V2_Modifier::GameSaveLoad @a0bcf0 decomp
def _modifier(v: Visitor, m) -> dict:
    v.begin()
    return v.record(m, Type="string", Value="float", Percentile="bool", ConditionOfSet="int")


# CRpgStats_V2_Item::GameSaveLoad @8df8b0 decomp
def _item(v: Visitor, r) -> dict:
    v.begin()
    rec = v.record(r, RegionName="string", SubRegionName="string", ContainingInventoryHandle="int")
    if rec["ContainingInventoryHandle"] == -1:
        rec.update(v.record(r, Translate="point3", Rotate="matrix3", LinearVelocity="point3",
                            AngularVelocity="point3", m_bObjectMovedSinceCreation="bool",
                            m_bStartPositionInitialized="bool", m_bFarEnoughFromStartPosition="bool",
                            StartPosition="point3"))
    rec.update(v.record(r, InventoryPrototype="string", iIsLootBag="int", m_bVandalized="bool",
                        m_bForceUpdateForStory="bool", m_fStoryRippleTimer="float", Amount="int",
                        m_bUseAlternateVisual="bool", m_AlternateVisualUUID="string", m_bCanPickUp="bool",
                        m_bCanUseInInventory="bool", m_sBoundToUUID="string", m_bBound="bool",
                        m_sTriggerUUID="string", Function="string", m_CooldownTimeLeft="float",
                        InventoryHandle="int", TreasurePrototype="string", TreasureGenerated="bool",
                        Drops="bool", Effective="bool", OnStage="bool", m_bLocked="bool",
                        m_sPortalName="string", m_bPhysicsFrozen="bool", DestroyOnUse="bool",
                        SelfActivationTime="float", InteractionDistance="float", TrapHandle="int",
                        ItemOwnerUUID="string", ItemName="string", HighlightAutomatically="bool",
                        HighlightOnMouseOver="bool", BlocksCamera="bool", BookContentUUID="string",
                        MaxEnchantmentSlots="int", CanDrop="bool", CanWalkThrough="bool",
                        LockPickLevel="int", CanInteract="bool", IsGeneratedByTreasure="bool"))
    if v.since(2, 0x11):
        rec.update(v.record(r, ForceLoaded="bool", Visible="bool"))
    if v.since(1, 0xA):
        rec["m_bMagicalAttributesGenerated"] = v.bool(r["m_bMagicalAttributesGenerated"])
    if v.since(2, 5):
        rec["RenderToShadow"] = v.bool(r["RenderToShadow"])
    if v.since(2, 0x13):
        rec["unnamed_8d5a46"] = v.bool(r["unnamed_8d5a46"])
    if v.since(2, 0x1B):
        rec["unnamed_8d5a78"] = v.int(r["unnamed_8d5a78"])
    rec["ItemUniqueness"] = v.string(r["ItemUniqueness"])
    if rec["Function"] in STATE_FUNCTIONS:
        rec["OpenDoor"] = v.int(r["OpenDoor"])
    rec["m_sFunctionParameter"] = v.string(r["m_sFunctionParameter"])
    rec["Enchantments"] = v.many(r["Enchantments"], "string")
    rec["m_fBaseGoldValue"] = v.float(r["m_fBaseGoldValue"])
    rec["MagicGoldValues"] = v.many(r["MagicGoldValues"], "float")
    rec.update(v.record(r, EffectBaseType="string", EffectChangeType="string", Level="float",
                        NamePrefix="string", NameSuffix="string"))
    rec["Mover"] = _item_mover(v, r["Mover"])
    modifiers = []
    for m in v.each(r["Modifiers"]):
        handle = v.int(m["Handle"])
        modifiers.append({"Handle": handle, **(_modifier(v, m) if handle != -1 else {})})
    rec["Modifiers"] = modifiers
    rec["Charms"] = v.many(r["Charms"], "string")
    rec["Skills"] = [v.record(s, skillUUID="string", skillLevel="int") for s in v.each(r["Skills"])]
    if v.bool("TouchingList" in r):
        v.begin()
        rec["TouchingList"] = [v.record(t, UUID="string", Type="int") for t in v.each(r["TouchingList"])]
    return rec


# CRpgStats_V2_ItemManager::GameSaveLoad @8a6ac0 decomp, CRpgStats_V2_ItemManager::CalculateCheckSum @8a3d80 decomp
def items(v: Visitor, d) -> dict:
    v.begin(sum("UUID" in r for r in d["Items"]))
    slots = v.each(d["Items"])
    out = {"Quota": v.int(d["Quota"]) if v.since(1, 0x16) else None, "Items": []}
    for r in slots:
        rec = v.record(r, Handle="int", PrototypeUUID="string")
        if rec["Handle"] != -1 and rec["PrototypeUUID"]:
            rec.update(v.record(r, UUID="string", IsLocal="bool"))
            rec.update(_item(v, r))
        out["Items"].append(rec)
    return out


# CRpgStats_V2_Stat_Collection::GameSaveLoad @a0cc00 decomp, CRpgStats_V2_Stat::GameSaveLoad @a0b930 decomp
def _stat_collection(v: Visitor, s) -> list:
    v.begin()
    out = []
    for x in v.each(s):
        kind = v.int(-1 if x is None else x["Type"])
        if kind == -1:
            out.append(None)
            continue
        v.begin()
        out.append({"Type": kind, **v.record(x, Value="float", Min="float", Max="float")})
    return out


# CRpgStats_V2_CharacterState::GameSaveLoad @99b810 decomp, CRpgstats_V2_Reputation::GameSaveLoad @a4f4d0 decomp, CRpgstats_V2_Status_Manager::GameSaveLoad @9b05e0 decomp
def _character_state(v: Visitor, s) -> dict:
    v.begin()
    rec = {"CHXP": v.bool(s["CHXP"])} if v.since(1, 0x15) else {}
    rec.update(v.record(s, Laddering="bool", CanMorph="bool", LowJump="bool", IsRunning="bool", CombatMode="int",
                        StatPoints="int", SkillPoints="int", DragonSkillPoints="int", EnemyHandle="int",
                        TimeSinceLastHit="float", TimeSinceLastHitAnim="float", TimeSinceLastDamage="float",
                        XP="int", Gold="int"))
    if v.since(1, 0x11):
        rec["XPDebt"] = v.int(s["XPDebt"])
    if v.since(1, 0x15):
        rec["CJUMP"] = v.bool(s["CJUMP"])
    rep = s["Reputation"]
    v.begin()
    rec["Reputation"] = {"Characters": [v.record(x, Handle="int", Value="int") for x in v.each(rep["Characters"])],
                         "Factions": [v.record(x, Faction="string", Value="int") for x in v.each(rep["Factions"])]}
    v.begin()
    held = v.each(s["Statuses"])
    if not v.since(1, 0xB):
        rec["StatusHandle"] = v.int(s["StatusHandle"])
    statuses = []
    for x in held:
        status = v.int(x)
        if status:
            raise StateError(f"status {status}: its typed record (DC 912710, vtable +0x5c) is not read yet")
        statuses.append(status)
    rec["Statuses"] = statuses
    rec["Timers"] = [v.record(x, Handle="int", Time="float") for x in v.each(s["Timers"])]
    return rec


# CRpgStats_V2_Character::GameSaveLoadAIController @830c50 decomp
def _ai_controller(v: Visitor, c, kind: int) -> dict | None:
    if not v.bool(c is not None):
        return None
    if kind == 2:
        return {**v.record(c, BusyInScript="bool", ProcessingEvent="bool", ProcessedEvent="string"),
                "Events": v.many(c["Events"], "string")}
    if kind == 3:
        if v.bool(c["HaveState"]):
            raise StateError(f"Osiris AI state {v.int()}: its typed record (DC 98cb50, vtable +0x14) is not read yet")
        return {"HaveState": False}
    if kind == 6:
        return v.record(c, **{name: "bool" for name in ("Stunned", "Cowering", "Blind", "Fleeing", "Polymorphed",
                                                        "Confused", "Awed", "Retreating", "Dying", "Assembling",
                                                        "OnElevator")})
    return {}


AI_CONTROLLERS = ("Combat", "Dialog", "EventManager", "Osiris", "Repel", "Lua", "Status", "UserInput")


# CRpgStats_V2_Character::GameSaveLoad @846580 decomp, CRpgStats_V2_Character_Relations::GameSaveLoad @a07940 decomp
def _character(v: Visitor, r) -> dict:
    v.begin()
    rec = v.record(r, RegionName="string", SubRegionName="string", Translate="point3", Rotate="matrix3",
                   Velocity="point3", StartPosition="point3", Orientation="point3", Script="string",
                   IsInTeam="bool", TeamID="uint", Dialog="string", Trainer="string", Name="string",
                   StoryPriority="bool", LightTypeLightOn="bool", LightTypeIntensity="float",
                   LightTypeSpecularLevel="float", LightTypeCastShadows="bool",
                   LightTypeMaxAttenuationRadius="float", LightTypeMinAttenuationRadius="float",
                   LightTypeRed="float", LightTypeGreen="float", LightTypeBlue="float", TreasureID="string",
                   TreasureGenerated="bool")
    if v.since(1, 0x1E):
        rec["m_UnsummonSkill"] = v.int(r["m_UnsummonSkill"])
    if v.since(2, 2):
        rec["unnamed_75907f"] = v.bool(r["unnamed_75907f"])
    rec.update(v.record(r, InventoryHandle="int", DragonMorphInventoryHandle="int", IsPlayer="bool",
                        IsFlying="bool", MeleeWeaponHandle="int", RangedWeaponHandle="int", OwnerHandle="int",
                        OwnerType="int", OnStage="bool", Ghost="bool", ControlType="int", FreezePhysics="bool",
                        mCanAttack="bool", mCanBeAttacked="bool", mEvasive="bool", mCanDie="bool",
                        mCanReceiveDmg="bool", mCanTrade="bool", mInDialog="bool", weaponanimbank="uint",
                        actionanimbank="uint", postureanimbank="uint", InteractionDistance="float",
                        VisualPrototypeUUID="string"))
    if v.since(1, 0x14):
        rec.update(v.record(r, VisualPrototypeUUIDOverride="string", CullingRange="int"))
    rec["Skills"] = [v.record(s, PrototypeHandle="int", SkillLevel="int", SkillBonus="int", SkillLimit="int",
                              Cooldown="float") for s in v.each(r["Skills"])]
    rec["mQuestNPCStatus"] = v.uint(r["mQuestNPCStatus"])
    rec["Quests"] = v.many(r["Quests"], "int")
    rec["State"] = _character_state(v, r["State"])
    v.begin()
    rec["FactionName"] = v.string(r["FactionName"])
    rec["Stats"] = _stat_collection(v, r["Stats"])
    rec.update(v.record(r, Level="int", CurrentHP="float", CurrentEnd="float"))
    if v.since(2, 2):
        rec.update(v.record(r, **{f"unnamed_{at}": "float"
                                  for at in ("7595f2", "759605", "759618", "75962b", "75963e", "759651")}))
    rec["BackupStats"] = _stat_collection(v, r["BackupStats"])
    rec.update(v.record(r, StatsBackedUp="bool", PhysicsHeight="float", PhysicsRadius="float",
                        CullingDistance="float"))
    rec["AIControllers"] = {name: _ai_controller(v, r["AIControllers"][name], kind)
                            for kind, name in enumerate(AI_CONTROLLERS)}
    return rec


# CRpgStats_V2_CharacterManager::GameSaveLoad @8106a0 decomp
def characters(v: Visitor, d) -> dict:
    v.begin()
    slots = v.each(d["Characters"])
    out = {"Quota": v.int(d["Quota"]) if v.since(1, 0x16) else None, "Characters": []}
    for r in slots:
        rec = v.record(r, Handle="int", PrototypeUUID="string")
        if rec["Handle"] != -1 and rec["PrototypeUUID"]:
            rec.update(v.record(r, UUID="string", IsLocal="bool"))
            rec.update(_character(v, r))
        out["Characters"].append(rec)
    return out


# CRpgStats_V2_FlyingFortress_Manager_Building::GameSaveLoad @8adcd0 decomp, CRpgStats_V2_FlyingFortress_Building::GameSaveLoad @a03870 decomp
def fortresses(v: Visitor, d) -> dict:
    v.begin()
    slots = v.each(d["Buildings"])
    out = {"Quota": v.int(d["Quota"]) if v.since(1, 0x16) else None, "Buildings": []}
    for b in slots:
        rec = v.record(b, BuildingHandle="int", PrototypeUUID="string", UUID="string", IsLocal="bool")
        v.begin()
        rec.update(v.record(b, RegionName="string", SubRegionName="string", Translate="point3", Rotate="matrix3",
                            Velocity="point3", Orientation="point3", CharacterOrientation="point3",
                            Priority_Forced_Low="bool", TeleportationTargetHandle="int",
                            TeleportationTarget="string", CurrentHitpoints="float", FactionName="string"))
        if v.since(1, 0x21):
            rec["unnamed_8f6a31"] = v.uint(b["unnamed_8f6a31"])
        if v.since(2, 3):
            rec["Mover"] = _item_mover(v, b["Mover"])
            rec["unnamed_8f6a78"] = v.bool(b["unnamed_8f6a78"])
        if v.since(2, 0xC):
            rec["unnamed_8f6aa1"] = v.bool(b["unnamed_8f6aa1"])
        out["Buildings"].append(rec)
    return out


# CRpgStats_V2_TrapManager::GameSaveLoad @902150 decomp, CRpgStats_V2_TrapScript::GameSaveLoad @a11740 decomp
def traps(v: Visitor, d) -> dict:
    v.begin()
    out = []
    for t in v.each(d["Traps"]):
        rec = v.record(t, BackReference="int", UUID="string")
        v.begin()
        rec.update(v.record(t, mCurrentFrameNumber="int", mHighestFrameNumber="int", mIsBroken="bool",
                            mIsExecutingFrame="bool"))
        if v.since(1, 0x18):
            rec.update(v.record(t, unnamed_98f21e="bool", unnamed_98f22e="string", unnamed_98f23e="string"))
        rec["Frames"] = [v.record(f, frameNumber="int", command="int", param1="string", param2="string",
                                  param3="string", param4="string") for f in v.each(t["Frames"])]
        rec["Commands"] = _empty_list(v, t["Commands"], f"trap {rec['UUID']} commands",
                                      "DC 98f475: Command, typed record 98dfc0")
        out.append(rec)
    return {"Traps": out}


# CRpgStats_V2_SkillTrainerManager::GameSaveLoad @78bdb0 decomp, CRpgStats_V2_SkillTrainer::GameSaveLoad @78ba80 decomp
def skill_trainers(v: Visitor, d) -> dict:
    v.begin()
    out = []
    for t in v.each(d["SkillTrainers"]):
        rec = v.record(t, SkillTrainerHandle="int", UUID="string")
        v.begin()
        lessons = []
        for x in v.each(t["Lessons"]):
            lesson = {"Lesson": v.bool(x["Lesson"])}
            if v.since(1, 0x1B):
                lesson.update(v.record(x, skill="string", int1="int", description="string", int2="int", int3="int"))
            lessons.append(lesson)
        rec["Lessons"] = lessons
        out.append(rec)
    return {"SkillTrainers": out}


def _treasure_group(v: Visitor, g) -> dict:
    v.begin()
    return v.record(g, Group="string", Frequency="int", MinRarity="int", MaxRarity="int", MinCharmAmount="int",
                    MaxCharmAmount="int", RarityChance="float", ItemUniqueness="string")


# CRpgStats_V2_TreasureManager::GameSaveLoad @9822a0 decomp, CRpgStats_V2_TreasureGroup_Collection::GameSaveLoad @a4ad40 decomp
def treasures(v: Visitor, d) -> dict:
    v.begin()
    out = []
    for t in v.each(d["Treasures"]):
        rec = v.record(t, Handle="int", UUID="string")
        v.begin()
        rec.update(v.record(t, MinAmount="int", MaxAmount="int"))
        v.begin()
        groups = []
        for g in v.each(t["Groups"]):
            valid = v.bool(g is not None)
            groups.append(_treasure_group(v, g) if valid else None)
        rec["Groups"] = groups
        out.append(rec)
    return {"Treasures": out}


READERS = {
    "SaveLoadPreMisc - CRpgStats_V2_TrophiesManager": trophies,
    "SaveLoadPreMisc - CRpgStats_V2_TimerManager": timers,
    "SaveLoadPreMisc - CGameLogic_SyncData": sync_data,
    "SaveLoadPreMisc - CRpgStats_V2_CharacterNameManager": names,
    "SaveLoadPreMisc - CRpgStats_V2_ItemNameManager": names,
    "SaveLoadPreMisc - CGameLogic_ItemSets": item_sets,
    "SaveLoadPreMisc - CGameLogic_PlayerControl": player_control,
    "SaveLoadPreMisc - CGameLogic_Encounter": encounter,
    "SaveLoadPreMisc - CGameLogic_PlayerControl_UserInterface": pc_user_interface,
    "SaveLoadDialogLogs": dialog_logs,
    "SaveLoadQuests": quests,
    "SaveLoadRegionCache": region_cache,
    "SaveLoadProjectiles": projectiles,
    "SaveLoadPreMisc - CRpgStats_V2_GameEventManager": game_events,
    "SaveLoadPostMisc - CGameLogic_DialogControl": dialog_control,
    "SaveLoadPreMisc - CRpgStats_V2_EffectArea_Manager": effect_areas,
    "SaveLoadPreMisc - CGameLogic_ButtonMappings": button_mappings,
    "SaveLoadPreMisc - CGameLogic_MapCoordinatesManager": map_coordinates,
    "SaveLoadBattleTower": battle_tower,
    "SaveLoadPreMisc - CRpgstats_V2_Alignment": alignment,
    "SaveLoadPreMisc - CRpgStats_V2_WayPointManager": waypoints,
    "SaveLoadPreMisc - CGameLogic_MapMarker_Manager": map_markers,
    "SaveLoadPostMisc - CRpgStats_V2_PerpetualStateManager": perpetual_state,
    "SaveLoadPreMisc - CLuaVariableManager": lua_variables,
    "SaveLoadStory": story,
    "SaveLoadTriggers": triggers,
    "SaveLoadDialogs": dialogs,
    "SaveLoadInventories": inventories,
    "SaveLoadItems": items,
    "SaveLoadCharacters": characters,
    "SaveLoadFortresses": fortresses,
    "SaveLoadPreMisc - CRpgStats_V2_TrapManager": traps,
    "SaveLoadPreMisc - CRpgStats_V2_SkillTrainerManager": skill_trainers,
    "SaveLoadPreMisc - CRpgStats_V2_TreasureManager": treasures,
}


def _checkpoints(stream: bytes) -> list[tuple[int, str]]:
    out, at = [], stream.find(b"SaveLoad")
    while at >= 0:
        n = struct.unpack_from("<I", stream, at - 4)[0]
        name = stream[at:at + n]
        if n < 128 and name.isascii():
            out.append((at - 4, name.decode()))
        at = stream.find(b"SaveLoad", at + 8)
    return out


def read(data: bytes) -> dict:
    header = savegame.check(data)
    _, stream = savegame.split(data)
    marks = _checkpoints(stream)
    sections = {}
    for i, (at, name) in enumerate(marks):
        start = at + 4 + len(name)
        end = marks[i + 1][0] if i + 1 < len(marks) else len(stream)
        key = name if name not in sections else f"{name} #{i}"
        reader = READERS.get(name)
        if reader is None:
            sections[key] = {"unread": end - start}
            continue
        v = Visitor(stream[start:end], bool(header.saveload_objects), (header.major, header.minor))
        sections[key] = reader(v, ABSENT)
        if v.q != end - start:
            raise StateError(f"{name}: read {v.q} of {end - start} bytes")
    return sections


def write_stream(sections: dict, story_bytes: bytes, objects: bool, version: tuple[int, int]) -> bytes:
    out = bytearray(4)
    for key, d in sections.items():
        name = key.split(" #")[0]
        if name not in READERS:
            raise StateError(f"{name}: no reader, so no writer")
        v = Visitor(None, objects, version, story_bytes)
        READERS[name](v, d)
        out += struct.pack("<I", len(name)) + name.encode() + v.d
    struct.pack_into("<I", out, 0, len(out) - 4)
    return bytes(out)


def write(header: savegame.Header, sections: dict, story_bytes: bytes) -> bytes:
    stream = write_stream(sections, story_bytes, bool(header.saveload_objects), (header.major, header.minor))
    return savegame.pack(savegame.header_bytes(header), stream)


def to_json(data: bytes) -> dict:
    header, _ = savegame.read_header(data)
    return {"Header": dataclasses.asdict(header), **read(data),
            "Story": base64.b64encode(savegame.story_of(data)).decode()}


def from_json(obj: dict) -> bytes:
    sections = {k: v for k, v in obj.items() if k not in ("Header", "Story")}
    return write(savegame.Header(**obj["Header"]), sections, base64.b64decode(obj["Story"]))


def round_trip(data: bytes) -> list[str]:
    import json
    again = from_json(json.loads(json.dumps(to_json(data))))
    savegame.check(again)
    (h0, at0), (h1, at1) = savegame.read_header(data), savegame.read_header(again)
    diffs = []
    if data[12:at0 - 4] != again[12:at1 - 4]:
        diffs.append("header")
    s0, s1 = savegame.split(data)[1], savegame.split(again)[1]
    if s0 != s1:
        at = next((i for i, (a, b) in enumerate(zip(s0, s1)) if a != b), min(len(s0), len(s1)))
        name = [n for q, n in _checkpoints(s0) if q <= at][-1:]
        diffs.append(f"stream: {len(s0)} and {len(s1)} bytes, first difference at {at} {name}")
    return diffs


def main(argv: list[str]) -> int:
    import json
    import sys
    from pathlib import Path
    if argv[:1] == ["to-json"] and len(argv) == 3:
        Path(argv[2]).write_text(json.dumps(to_json(Path(argv[1]).read_bytes()), ensure_ascii=False),
                                 encoding="utf-8")
        return 0
    if argv[:1] == ["to-dsg"] and len(argv) == 3:
        Path(argv[2]).write_bytes(from_json(json.loads(Path(argv[1]).read_text(encoding="utf-8"))))
        return 0
    if argv[:1] == ["round-trip"] and len(argv) > 1:
        bad = 0
        for path in argv[1:]:
            diffs = round_trip(Path(path).read_bytes())
            print(path, "identical" if not diffs else "; ".join(diffs))
            bad += bool(diffs)
        return 1 if bad else 0
    print(USAGE, file=sys.stderr)
    return 2


if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv[1:]))
