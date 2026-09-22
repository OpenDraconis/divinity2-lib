"""The engine state in a savegame's stream: every section besides the story.

`CRpgStats_V2_LoadSaveEntry::SaveLoadInternal` @7e8180 (GUP) writes the sections in a
fixed order, each after a named checkpoint (`CheckPointTest`), and each manager's
`GameSaveLoad` writes its values in order through `CRpgStats_V2_LoadBinaryVisitor`, which
writes no tags. The Developer's Cut adds sections and fields the 1.03 build does not
have; a reader that disagrees with the shipped saves stops at the section's end instead of
guessing.

Field names are the engine's `ms_kLoadSaveEntry_*` names, or the member the value is read
into where the entry is `Empty`. Function names and addresses are GUP (`Divinity2GUP.pdb`)
unless marked DC.
"""
from __future__ import annotations

import struct

from . import Dv2Error
from . import savegame


class StateError(Dv2Error, ValueError):
    pass


class Visitor:
    """`CRpgStats_V2_LoadBinaryVisitor`: little-endian, no tags."""

    def __init__(self, data: bytes, objects: bool, version: tuple[int, int]):
        self.d, self.q, self.objects, self.version = data, 0, objects, version

    def _take(self, fmt: str):
        v = struct.unpack_from(fmt, self.d, self.q)
        self.q += struct.calcsize(fmt)
        return v

    def int(self) -> int:                       # LoadSaveImpl(int*) @98b0e0
        return self._take("<i")[0]

    def uint(self) -> int:                      # (uint*) @98b6a0, (ulong*) @98b700
        return self._take("<I")[0]

    def short(self) -> int:                     # (ushort*) @98b6d0
        return self._take("<H")[0]

    def float(self) -> float:                   # (float*) @98b110
        return self._take("<f")[0]

    def bool(self) -> bool:                     # (bool*) @98b1a0: one byte
        return self._take("<B")[0] != 0

    def string(self) -> str:                    # (std::string*) @98b490, (NiFixedString*) @98b590
        n = self.uint()
        v = self.d[self.q:self.q + n].decode("latin-1")
        self.q += n
        return v

    chars = string                              # (char*) @98b140: u32 length, the bytes

    def buffer(self, n: int) -> bytes:
        """(TLoadSaveCharBuffer*) @98b730: a u32 the loader ignores, then `n` bytes the caller
        knows the length of."""
        self.uint()
        b = self.d[self.q:self.q + n]
        self.q += n
        return b

    def point3(self) -> list[float]:            # (NiPoint3*) @98b1d0
        return list(self._take("<3f"))

    def point2(self) -> list[float]:            # (NiPoint2*) @98b250
        return list(self._take("<2f"))

    def color(self) -> list[float]:             # (NiColor*) @98b2b0
        return list(self._take("<3f"))

    def colora(self) -> list[float]:            # (NiColorA*) @98b330
        return list(self._take("<4f"))

    def bound(self) -> list[float]:             # (NiBound*) @98b3c0: centre, radius
        return list(self._take("<4f"))

    def matrix3(self) -> list[float]:           # (NiMatrix3*) @98af50
        return list(self._take("<9f"))

    def count(self) -> int:                     # GetSetAmountOfChildren @98b7a0
        return self.uint()

    def since(self, major: int, minor: int) -> bool:
        """`GetVersionNumber` compared as the managers compare it: the save's (major, minor)
        from its header, 3.2 in both shipped saves (`CGameLogic_PlayerControl` stores it back
        as `OriginalVersion`)."""
        return self.version >= (major, minor)

    def begin(self) -> None:
        """`BeginObject` @98bee0: a u32 checksum when the save uses save-load objects
        (header byte); `EndObject` @98bdc0 reads nothing."""
        if self.objects:
            self.uint()


# --- PreMisc (`SaveLoadPreMisc` @7e6b80) --------------------------------------------------

def trophies(v: Visitor) -> dict:
    """`CRpgStats_V2_TrophiesManager::GameSaveLoad` @97b920, `CRpgStats_V2_Trophy::GameSaveLoad`
    @97b2a0."""
    v.begin()
    out = []
    for _ in range(v.count()):
        handle, prototype = v.int(), v.string()
        v.begin()
        out.append({"Handle": handle, "PrototypeUUID": prototype, "Count": v.int(), "Name": v.string(),
                    "Picture": v.string(), "Prototype": v.string(), "Background": v.string()})
    return {"Trophies": out}


def timers(v: Visitor) -> dict:
    """`CRpgStats_V2_TimerManager::GameSaveLoad` @915250: no object checksum; a timer with a
    name and a duration above 0 is started again with `AddTimer`."""
    return {"Timers": [{"UUID": v.string(), "Duration": v.float()} for _ in range(v.count())]}


def sync_data(v: Visitor) -> dict:
    """`CGameLogic_SyncData::GameSaveLoad` @778cf0."""
    v.begin()
    return {"RenderShadows": v.bool(), "HideInShadows": v.bool(), "TimeName": v.string()}


def names(v: Visitor) -> dict:
    """`CRpgStats_V2_NameManager::GameSaveLoad` @984a00 (DC 8c1330), for characters and items."""
    v.begin()
    return {"Names": [{"UUID": v.string(), "Name": v.string()} for _ in range(v.count())]}


def item_sets(v: Visitor) -> dict:
    """`CGameLogic_ItemSets::GameSaveLoad` @92d9b0 (DC 8475d0): three weapon sets."""
    v.begin()
    out = []
    for _ in range(v.count()):
        v.begin()
        out.append({"LeftHandHandle": v.int(), "RightHandHandle": v.int()})
    return {"ItemSets": out}


def player_control(v: Visitor) -> dict:
    """`CGameLogic_PlayerControl::GameSaveLoad` (GUP @7f5d70, DC 6f56e0, read from the DC x86:
    the DC names the third looks field `skinTone` and adds the fields after `OriginalVersion`).
    Values whose entry is `Empty` or reused are named by what the DC code does with them."""
    v.begin()
    looks = lambda: {"faceModel": v.string(), "hairModel": v.string(), "skinTone": v.string(),
                     "eyesModel": v.string()}
    out = {"MaleLooks": looks(), "FemaleLooks": looks(), "AllowSilverEyes": v.bool(),
           "Handles": [v.int() for _ in range(v.count())],
           "FearOfTheDragonStage": v.int(), "TimeSinceFearOfTheDragon": v.float(),
           "FearOfTheDragonFleeList": [v.int() for _ in range(v.count())],
           "InTownArea": v.bool(), "JumpBackFallOffSystemActive": v.bool(),
           "JumpBackFallOffSystemUseTerrain": v.bool(), "SlowDragonMode": v.bool(),
           "AllowDragonStone": v.bool(), "RequestedDelayedMorph": v.bool(),
           "InDreamScene": v.bool(), "TimeTillNextPetCheck": v.int(), "ItemInMouseAnchor": v.int()}
    if v.since(1, 0x23):
        out["unnamed_6f5bae"] = v.int()
    if v.since(1, 0x24):
        out["OriginalVersion"] = [v.int(), v.int()]
    # DC 6f5c34: the follow camera's yaw only while the unnamed DC global 0x14f18fc is set; it
    # was not when the shipped saves were written (their section lengths leave no room for it).
    if v.since(2, 3):
        out["unnamed_6f5cb6"] = [v.int(), v.int()]
    if v.since(2, 0x18):
        out["unnamed_6f5cef"] = v.bool()
    if v.since(2, 0xD):
        out["unnamed_6f5d26"] = v.float()
        out["unnamed_6f5d4a"] = [{"name": v.string(), "position": v.point3(), "value": v.float()}
                                 for _ in range(v.count())]
    if v.since(2, 0xA):
        out["unnamed_6f61c2"] = v.int()
    if v.since(2, 4):
        out["unnamed_6f61f1"] = v.bool()
    if v.since(2, 0x14):
        out["unnamed_6f6220"] = v.bool()
    out["GameStats"] = {"MonsterLevel": v.int(), "TotalGold": v.int(), "MindReads": v.int(),
                        "Monsters": v.int(), "TimePlayed": v.float()}
    if v.since(2, 0x11):
        out["CharTeleportDestination"] = v.point3()
        out["CharTeleportOrientation"] = v.point3()
    return out


def encounter(v: Visitor) -> dict:
    """`CGameLogic_Encounter`, DC only (800e20)."""
    out = []
    for _ in range(v.int()):
        e = {"float": v.float(), "int": v.int()}
        if v.since(2, 0x1B):
            e["bool"] = v.bool()
        out.append(e)
    return {"Encounters": out}


def pc_user_interface(v: Visitor) -> dict:
    """`CGameLogic_PlayerControl_UserInterface::GameSaveLoad` @809510 (DC 71d500) -> the PC
    interface (DC 908b30): seven `CGameLogic_InventoryPosHelper::GameSaveLoad` (DC a18680)."""
    out = []
    for _ in range(7):
        v.begin()
        out.append([{"InventoryPosHelper": v.string(), "int": v.int()} for _ in range(v.count())])
    return {"InventoryPosHelpers": out}


def _empty_list(v: Visitor, what: str, reader: str) -> list:
    """A manager's object list whose element layout is not read yet: empty in both shipped
    saves; any element raises instead of being skipped."""
    n = v.count()
    if n:
        raise StateError(f"{what}: {n} elements; the element layout ({reader}) is not read yet")
    return []


def dialog_logs(v: Visitor) -> dict:
    """`CDialogLogManager::GameSaveLoad` @9187c0 (DC 816dd0)."""
    v.begin()
    return {"CurrentTime": v.float(),
            "Entries": _empty_list(v, "DialogLogs", "DC 816f5a: TimeStamp, Locutor, Owner, Text, bIsNew, [2.25] bool")}


def quests(v: Visitor) -> dict:
    """`CRpgStats_V2_QuestManager::GameSaveLoad` @96f3f0 (DC 8aa3f0)."""
    v.begin()
    return {"Quests": _empty_list(v, "Quests", "DC 8aa542: PrototypeName, Handle, Quest 8a9ef0")}


def region_cache(v: Visitor) -> dict:
    """`CRpgStats_V2_LoadSaveManager::GameSaveLoadRegionCache` (DC 84f190): region, sub-region and
    cache size until a size of 0."""
    v.begin()
    out = []
    while True:
        entry = {"RegionName": v.string(), "SubRegionName": v.string(), "CacheSize": v.uint()}
        if entry["CacheSize"] == 0:
            return {"Cache": out}
        raise StateError(f"RegionCache {entry}: the cache data (GameSaveLoadCacheData DC 84eba0) is not read yet")


def projectiles(v: Visitor) -> dict:
    """`CGameLogic_Projectile_Manager::GameSaveLoad` @8b8840 (DC 7d35a0)."""
    v.begin()
    return {"Projectiles": _empty_list(v, "Projectiles", "DC 7d3658: Handle, Projectile 8f01f0")}


def game_events(v: Visitor) -> dict:
    """`CRpgStats_V2_GameEventManager::GameSaveLoad` @897120 (DC 7b61e0): the queued story events."""
    v.begin()
    return {"Events": _empty_list(v, "GameEvents", "DC 7b6336: argument descriptions")}


def dialog_control(v: Visitor) -> dict:
    """`CGameLogic_DialogControl::GameSaveLoad` @802040 (DC 705300): running dialogs."""
    v.begin()
    return {"Dialogs": _empty_list(v, "DialogControl", "GUP 802040: 2 strings, int, 2 floats, bool")}


def effect_areas(v: Visitor) -> dict:
    """`CRpgStats_V2_EffectArea_Manager::GameSaveLoad` @9118e0 (DC 806da0): one slot per area; a
    slot of type 0 is empty, any other type loads the area through its vtable +0x28."""
    v.begin()
    out = []
    for i in range(v.count()):
        kind = v.int()
        if kind:
            raise StateError(f"EffectArea slot {i}: type {kind}; the area layout (vtable +0x28) is not read yet")
        out.append({"Type": kind})
    return {"EffectAreas": out}


def _mapped_button(v: Visitor) -> dict:
    """`CGameLogic_MappedButton::GameSaveLoad` (DC 8d2800)."""
    v.begin()
    return {"m_eType": v.int(), "m_Handle": v.int(), "m_sIconName": v.string()}


def button_mappings(v: Visitor) -> dict:
    """`CGameLogic_ButtonMappings::GameSaveLoad` @92c6f0 (DC 845c50): the human map, then the dragon
    map (`MapButton` @92c510 picks MT_HUMAN 1 / MT_DRAGON 0)."""
    v.begin()
    return {"Human": [_mapped_button(v) for _ in range(v.count())],
            "Dragon": [_mapped_button(v) for _ in range(v.count())]}


def map_coordinates(v: Visitor) -> dict:
    """`CGameLogic_MapCoordinatesManager`, DC only (865da0, 865290): region -> its sub-regions. The
    fog buffer (863ac0) is read only from saves before 2.5."""
    out = {}
    for _ in range(v.count()):
        region = v.string()
        out[region] = [v.string() for _ in range(v.count())]
    return {"Regions": out}


def battle_tower(v: Visitor) -> dict:
    """`CRpgStats_V2_BattleTower::GameSaveLoad` @8fb9d0 (DC 7bd5a0) and its four platforms, always
    in this order: necromancer's alcove (DC 9cad60), 9cf9d0, training arena (DC 9d06f0),
    9ce4c0."""
    v.begin()
    out = {"LastRegion": v.string(), "LastSubRegion": v.string(), "LastPosition": v.point3(),
           "LastFlyingState": v.bool()}
    if v.since(1, 0x26):
        out["unnamed_7bd62a"] = v.int()
    if v.since(1, 0x27):
        out["unnamed_7bd65b"] = v.int()
    out["ActivePlatform"] = v.int()
    v.begin()
    alcove = {"DefaultLimbsCreated": v.bool(), "UpgradeLevel": v.int(), "SummonedCreatureHandle": v.int()}
    if v.since(1, 0x1C):
        alcove["SummonedCreatureBonusType"] = v.int()
    if v.since(1, 0x1A):
        alcove.update({"SelectedHead": v.uint(), "SelectedBody": v.uint(), "SelectedArms": v.uint(),
                       "SelectedLegs": v.uint()})
        for limb in ("Heads", "Bodies", "Arms", "Legs"):
            if v.count():
                raise StateError(f"BattleTower alcove {limb}: the limb layout (DC 9caed0..) is not read yet")
            alcove[limb] = []
    out["NecromancersAlcove"] = alcove
    formulas = lambda: [{"name": v.string(), "Formula": v.int()} for _ in range(v.count())]
    v.begin()
    out["Platform_9cf9d0"] = {"UpgradeLevel": v.int(), "Formulas": formulas()}
    v.begin()
    out["TrainingArena"] = {"UpgradeLevel": v.int()}
    v.begin()
    out["Platform_9ce4c0"] = {"UpgradeLevelWeapons": v.int(), "UpgradeLevelArmor": v.int(),
                              "UpgradeLevelJewelry": v.int(), "Formulas": formulas()}
    return out


def alignment(v: Visitor) -> dict:
    """`CRpgstats_V2_Alignment::GameSaveLoad` @964b10 (DC 887980): the groups with their parents,
    then the four maps `CRpgstats_V2_AlignmentMap::GameSaveLoad` @a76590 (DC a07ce0), keyed by a
    character handle (C) or a faction name (F); a value below 25 is enemy, -1 removes an
    override (div-api.md "faction")."""
    v.begin()
    out = {"Groups": [{"GroupName": v.string(), "ParentNames": [v.string() for _ in range(v.count())]}
                      for _ in range(v.count())]}
    for tag, first, second in (("C_C_Alignment", v.int, v.int), ("F_C_Alignment", v.string, v.int),
                               ("C_F_Alignment", v.int, v.string), ("F_F_Alignment", v.string, v.string)):
        v.begin()
        out[tag] = [{"First": first(), "Values": [{"Second": second(), "Value": v.int()} for _ in range(v.count())]}
                    for _ in range(v.count())]
    return out


def waypoints(v: Visitor) -> dict:
    """`CRpgStats_V2_WayPointManager::GameSaveLoad` @93b990 (DC 8620a0, reached through the
    manager's vtable +0x3c), each `CRpgStats_V2_WayPoint::GameSaveLoad` @a1ac30."""
    v.begin()
    out = []
    for _ in range(v.count()):
        handle, uuid = v.int(), v.string()
        v.begin()
        out.append({"Handle": handle, "UUID": uuid, "IsActive": v.bool(), "Discovered": v.bool(),
                    "ItemUUID": v.string(), "Name": v.string(), "TriggerUUID": v.string()})
    return {"WayPoints": out}


def map_markers(v: Visitor) -> dict:
    """`CGameLogic_MapMarker_Manager::GameSaveLoad` @9399c0 (DC 85ffa0), each
    `CGameLogic_MapMarker::GameSaveLoad` @939430 (DC 85f9c0, which adds `mItemHandle` from 2.x)."""
    v.begin()
    out = []
    for _ in range(v.count()):
        handle = v.int()
        v.begin()
        m = {"Handle": handle, "UUID": v.string(), "RegionName": v.string(), "SubRegionName": v.string(),
             "Position": v.point2(), "ShowOnWorldMap": v.bool(), "ShowOnRegionMap": v.bool(),
             "ShowOnDetailMap": v.bool(), "Show": v.bool(), "PlayerMarker": v.bool(), "Icon": v.string(),
             "Label": v.string()}
        if v.since(2, 0):
            m["mItemHandle"] = v.int()
        out.append(m)
    return {"MapMarkers": out}


def _effect(v: Visitor) -> dict:
    """`CGameLogic_Effect::GameSaveLoad` @89a7b0: every entry is named `Scale` in the engine; the two
    strings hold a region and a sub-region in the shipped saves (by their values)."""
    v.begin()
    return {"string1": v.string(), "string2": v.string(), "Scale": v.float(), "Translate": v.point3(),
            "Rotate": v.matrix3()}


def perpetual_state(v: Visitor) -> dict:
    """`CRpgStats_V2_PerpetualStateManager::GameSaveLoad` @89c150 (DC 882e70), read from the DC x86:
    character effects (881c90), item effects (882b40), custom animations (882480, GUP
    `GameSaveLoadCustomAnimationList`), the culled scenery (882600, GUP
    `GameSaveLoadCulledSceneryList`: `EngineScenerySetOn/OffStage`), hit effect parameters (880d30),
    trigger effects (881680), story lights (881940: `EngineSetLightOnStage`), story soundbanks
    (880bd0), effect preloads (880e60), the Lua game time (880b70), the active subtitle and the
    rift timer. The engine's load and save paths differ in 882600 and 881940; the shipped saves
    carry one culled-scenery list plus one of names, and one light list."""
    v.begin()
    out = {"CharacterEffects": [{"Handle": v.int(), "PrototypeUUID": v.string(),
                                 **({"CallerType": v.int()} if v.since(2, 6) else {}),
                                 "CallerName": v.string(), "Effect": _effect(v)} for _ in range(v.count())],
           "ItemEffects": [{"UUID": v.string(), "FileID": v.string(), "AnimationID": v.int(),
                            "IsACharacter": v.bool(), "Scale": v.float(), "Translate": v.point3(),
                            "Rotate": v.matrix3()} for _ in range(v.count())],
           "CustomAnimations": [{"AnimationName": v.string(), "CharacterHandle": v.int()}
                                for _ in range(v.count())],
           "CulledScenery": [{"SceneryUUID": v.string(), "IsCulled": v.bool()} for _ in range(v.count())]}
    if v.since(1, 0x17):
        out["CulledSceneryNames"] = [v.string() for _ in range(v.count())]
    if v.since(2, 8):
        out["HitEffectParams"] = {"bool1": v.bool(), "bool2": v.bool(), "bool3": v.bool(), "int": v.int(),
                                  "bool4": v.bool(), "floats": [v.float() for _ in range(4)],
                                  "color1": v.color(), "color2": v.color(), "uint": v.uint()}
    if v.since(2, 6):
        out["TriggerEffects"] = [{"Handle": v.int(), "CallerType": v.int(), "CallerName": v.string(),
                                  "Effect": _effect(v)} for _ in range(v.count())]
    if v.since(1, 0x28):
        out["StoryLights"] = [{"Name": v.string(), "RegionName": v.string(), "SubRegionName": v.string(),
                               "Active": v.bool()} for _ in range(v.count())]
    if v.since(1, 0x10):
        out["StorySoundbanks"] = [{"SoundbankName": v.string(), "IsLocal": v.bool()} for _ in range(v.count())]
    if v.since(2, 0x12):
        out["EffectPreloads"] = [{"PrototypeUUID": v.string()} for _ in range(v.count())]
    if v.since(2, 0x15):
        out["LuaGameTime"] = v.float()
    if v.since(1, 9):
        out["ActiveSubtitle"] = v.string()
    if v.since(1, 0xE):
        out["RiftTimerTimeLeft"] = v.float()
    if v.since(2, 3):
        out["unnamed_882ffb"] = [v.int(), v.int()]
    return out


def lua_variables(v: Visitor) -> dict:
    """`CLuaVariableManager::GameSaveLoad` @8f5e60 (DC 7b16a0), read from the DC x86: five value
    lists (`CLuaVariableList<int|double|char*|int*|NiPoint3,32>`, DC 7b26d0..7b2b90: real size,
    size, real free size, free size, one buffer of `size` values when allocated (DC 7b2380), the
    free indices), eight optional key tables (`CLuaVariableManager_Key2Table::GameSaveLoad`
    @8f5900, DC 7b1010: count, capacity, per slot a key and a length n with 2n+1 ints), and the
    name pool (DC 9c06f0: used size, 512 ints, 769 buckets of index lists (9c04c0), an int and a
    0x8000-byte buffer from 2.23, 0x4000 before). Values are kept as their bytes."""
    import base64
    v.begin()
    out = {"Lists": {}}
    for name, size in (("int", 4), ("double", 8), ("char*", None), ("int*", 12), ("NiPoint3", None)):
        real, n, real_free, n_free = v.int(), v.int(), v.int(), v.int()
        lst = {"RealListSize": real, "ListSize": n, "RealFreeListSize": real_free, "FreeListSize": n_free}
        if real:
            if name == "char*":
                lst["Values"] = [{"uint": v.uint(), "chars": v.string()} for _ in range(n)]
            else:
                length = v.uint()          # the buffer's own u32 is its byte length in both saves
                lst["Values"] = base64.b64encode(v.d[v.q:v.q + length]).decode()
                v.q += length
        if real_free:
            lst["Free"] = [v.int() for _ in range(n_free)]
        out["Lists"][name] = lst
    out["Tables"] = []
    for _ in range(8):
        if not v.bool():
            out["Tables"].append(None)
            continue
        count, capacity = v.int(), v.int()
        slots = []
        for _ in range(count):
            key, n = v.uint(), v.uint()
            slots.append({"key": key, "values": [v.int() for _ in range(2 * n + 1)] if n else []})
        out["Tables"].append({"count": count, "capacity": capacity, "slots": slots})
    pool = {"used": v.int(), "offsets": [v.int() for _ in range(512)],
            "buckets": [[v.int() for _ in range(v.uint())] for _ in range(0x301)], "top": v.int()}
    pool["names"] = v.buffer(0x8000 if v.since(2, 0x17) else 0x4000).rstrip(b"\0").decode("latin-1").split("\0")
    out["NamePool"] = pool
    return out


def story(v: Visitor) -> dict:
    """`COsirisManager::GameSaveLoad` @80b270 (DC 736f10): the story as blocks of
    `OsirisChunkBuffer` bytes; `savegame.story_of` and `osiris_story` read the story itself."""
    v.begin()
    out = {"OsirisStoryStarted": v.bool(), "OsirisChunkBuffer": v.int()}
    total = 0
    while True:
        _, n = v.uint(), v.uint()
        v.q += n
        total += n
        if n < out["OsirisChunkBuffer"]:
            break
    out["StoryBytes"] = total
    return out


# --- Triggers (`CRpgStats_V2_TriggerManager::GameSaveLoad` @816f40, DC 7305c0) ----------------

#: ETriggerType (gup-enums.tsv); 21 and 22 are the Developer's Cut's encounter point and zone
#: (DC factory 72e7c0: jump table 0x72ea10, constructors 9756f0 and 970aa0).
TRIGGER_TYPES = {1: "TriggerSphere", 2: "TriggerPoint", 3: "TriggerTeleport", 4: "TriggerArea",
                 5: "TriggerOrientation", 8: "TriggerSound", 9: "TriggerTrapArea", 10: "TriggerEffectArea",
                 11: "TriggerRepel", 12: "TriggerPlayerSpawnPoint", 13: "TriggerPointSound",
                 14: "TriggerAntiDragon", 15: "TriggerTownArea", 16: "TriggerStartVisualEffectArea",
                 17: "TriggerStopVisualEffectArea", 18: "TriggerVisualEffectPoint",
                 19: "TriggerAutoSaveCheckpoint", 20: "TriggerPainArea", 21: "TriggerPointEncounter",
                 22: "TriggerEncounterZone"}


def _trigger(v: Visitor) -> dict:
    """`CRpgStats_V2_Trigger::GameSaveLoad` @8997b0 (DC 9783b0)."""
    return {"RegionName": v.string(), "SubRegionName": v.string(), "IsActive": v.bool()}


def _trigger_point(v: Visitor) -> dict:
    """`CRpgStats_V2_Trigger_Point::GameSaveLoad` @780110 (DC 977b20)."""
    return {**_trigger(v), "Translate": v.point3()}


def _trigger_orientation(v: Visitor) -> dict:
    """`CRpgStats_V2_Trigger_Orientation::GameSaveLoad` @780a10 (DC 976800)."""
    return {**_trigger_point(v), "Rotate": v.matrix3()}


def _trigger_area(v: Visitor) -> dict:
    """`CRpgStats_V2_Trigger_Area::InheritedGameSaveLoad` @9c8900 (DC 9358d0): the base, the shape
    (`CPolyArea::GameSaveLoad` @77ef60 through the shape's vtable +0x30: `CAreaPoint` @77c730 per
    point, bottom, top), then the area's state and four handle lists. GUP names the first two
    `CharacterInsideList` and `ItemInsideList`; the other two are written through offsets, +0x44
    and +0x54 (x86 9c8c00, 9c8d10), the lists `RegisterCharacter` @9c8780 (`lea [ecx+0x44]`) and
    `RegisterItem` add to."""
    out = _trigger(v)
    out["Points"] = [{"ID": v.string(), "Point": v.point3()} for _ in range(v.count())]
    out["Bottom"], out["Top"] = v.float(), v.float()
    if v.since(1, 0x13):
        out["SoundEventName"] = v.string()
    out["ForceFullCheck"] = v.bool()
    out["CheckItems"] = v.bool()
    for name in ("CharacterInsideList", "ItemInsideList", "CharacterToCheckList", "ItemToCheckList"):
        out[name] = [v.int() for _ in range(v.count())]
    return out


def _extend(base, extra):
    return lambda v: {**base(v), **extra(v)}


#: type -> (object checksum, reader), from each class's `GameSaveLoad` (vtable +0x2c; the DC
#: addresses are the DC vtables' entries). The visual effect areas (DC 971fb0, 971b20) write no
#: checksum of their own; the shipped saves agree.
TRIGGER_READERS = {
    2: (True, _trigger_point),
    3: (True, _extend(_trigger_point, lambda v: {"Center": v.point3(), "ToCenter": v.point3(),
                                                 "RigidBodyName": v.string(), "DestinationRegion": v.string(),
                                                 "DestinationSubRegion": v.string()})),     # @a010b0
    4: (True, _trigger_area),
    5: (True, _trigger_orientation),
    8: (True, _extend(_trigger_area, lambda v: {"SoundbankNames": [v.string() for _ in range(v.count())]})),  # @a00940
    9: (True, _extend(_trigger_area, lambda v: {"TrapHandle": v.int(), "NPCCanTrigger": v.bool()})),          # @9ff760
    10: (True, _extend(_trigger_area, lambda v: {"DamagePerTick": v.float(), "TickInterval": v.float(),
                                                 "ExposureTime": v.float(), "EffectAreaType": v.int(),
                                                 "Handle": v.int()})),                                    # @9fefe0
    11: (True, _extend(_trigger_area, lambda v: {"FactionName": v.string()})),                           # @9ff500
    12: (True, _trigger_orientation),                                                                   # @9ae570
    13: (True, _extend(_trigger_point, lambda v: {"SoundEventName": v.string(),
                                                  **({"unnamed_97647e": v.bool()} if v.since(2, 0xB) else {})})),  # DC 976410
    14: (True, _extend(_trigger_point, lambda v: {"OuterRingRadius": v.float(), "InnerRingRadius": v.float(),
                                                  "ValidRadii": v.bool(), "DeviceEnabled": v.bool(),
                                                  "TimeSinceLastDamage": v.float(), "unnamed_float": v.float(),
                                                  "unnamed_bool": v.bool()})),                            # @9fe520
    15: (True, _trigger_area),                                                                          # @9fe2c0
    16: (False, _trigger_area),
    17: (False, _trigger_area),
    18: (True, _trigger_orientation),                                                                   # @9fcc60
    19: (True, _extend(_trigger_area, lambda v: {"SavePerformed": v.bool()})),                          # @9fc9e0
    20: (True, _extend(_trigger_area, lambda v: {"TimeSinceLastDamage": v.float()})),                   # @9fc4c0
    # DC 9759a0 from 2.22: a name, a handle list, then two bools and (2.16) two more.
    21: (True, _extend(_trigger_point, lambda v: {"string": v.string(), "Handles": [v.int() for _ in range(v.int())],
                                                  "bools": [v.bool(), v.bool(), v.bool(), v.bool()]})),
    22: (True, _trigger_area),                                                                          # DC 970ad0
}


def triggers(v: Visitor) -> dict:
    """Every trigger: handle, UUID, type, then the type's own record."""
    v.begin()
    out = []
    for _ in range(v.count()):
        handle, uuid, kind = v.int(), v.string(), v.int()
        if kind not in TRIGGER_READERS:
            raise StateError(f"trigger {uuid}: type {kind} has no reader")
        checksum, reader = TRIGGER_READERS[kind]
        if checksum:
            v.begin()
        out.append({"Handle": handle, "UUID": uuid, "Type": TRIGGER_TYPES.get(kind, kind), **reader(v)})
    return {"Triggers": out}


def dialogs(v: Visitor) -> dict:
    """`CDialogManager::GameSaveLoad` @874300 (DC 7f1af0): `m_ptrGlobalEventManager` and
    `m_ptrLocalEventManager`, named by their tags, each through `CRpgStats_V2_EventManager::GameSaveLoad`
    @80c0d0 (DC 737d50): the `CRpgStats_V2_Event` UUID and its `State`. The global ones are what
    `SetGlobalEvent` / `ClearGlobalEvent` change (`CRpgStats_V2_GlobalEventManager::SetEventState`
    @80bc20). The local list is empty in both shipped saves."""
    v.begin()
    out = {}
    for name in ("GlobalFlags", "LocalFlags"):
        v.begin()
        out[name] = [{"UUID": v.string(), "State": v.bool()} for _ in range(v.count())]
    return out


def inventories(v: Visitor) -> dict:
    """`CRpgStats_V2_InventoryManager::GameSaveLoad` @96ca40 (DC 8a77b0): handle, prototype and
    `IsLocal` per inventory, then `CRpgStats_V2_Inventory::GameSaveLoad` @8c7cc0 (DC 893480): the
    owner and the occupied slots as (slot, item handle)."""
    v.begin()
    out = []
    for _ in range(v.count()):
        rec = {"Handle": v.int(), "PrototypeUUID": v.string(), "IsLocal": v.bool()}
        v.begin()
        rec.update({"PrototypeHandle": v.int(), "OwnerType": v.int(), "OwnerHandle": v.int(),
                    "MaxSlots": v.int(), "MaxEquipmentSlots": v.int(),
                    "Items": [{"Slot": v.int(), "Handle": v.int()} for _ in range(v.count())]})
        out.append(rec)
    return {"Inventories": out}


def _item_mover(v: Visitor) -> dict:
    """`CRpgStats_V2_Item_Mover::GameSaveLoad` @a43920 (DC a16cc0 for a fortress, 9e3f90 for an
    item): no object checksum."""
    return {"ItemMove_Moving": v.bool(), "ItemMove_Destination": v.point3(), "ItemMove_Velocity": v.float(),
            "ItemMove_MaxVelocity": v.float(), "ItemMove_MovingWithSineSpeed": v.bool(),
            "ItemMove_TravelDistance": v.float(), "ItemMove_OnArrivalText": v.string(),
            "Targets": [{"TargetType": v.int(), "TargetHandle": v.int()} for _ in range(v.count())]}


#: `CRpgStats_V2_ItemStateManagerFactory::CreateManager` @a4f880 (DC a12610): the functions that
#: give an item a state manager, and with it the `OpenDoor` value in its save.
STATE_FUNCTIONS = {"Door", "CheckDoor", "Openable", "Destructible", "OpenableDestructible"}


def _modifier(v: Visitor) -> dict:
    """`CRpgStats_V2_Modifier::GameSaveLoad` @a0bcf0 (DC 985cf0)."""
    v.begin()
    return {"Type": v.string(), "Value": v.float(), "Percentile": v.bool(), "ConditionOfSet": v.int()}


def _item(v: Visitor) -> dict:
    """`CRpgStats_V2_Item::GameSaveLoad` @8df8b0 (DC 8dc680): its parts in order.

    - Position @8d9540 (DC 8d4770): the transform only when in no inventory.
    - Misc @8d9f00 (DC 8d5640). The `Empty` entries are named by the member GUP reads them into
      (its offsets match `gup-types.tsv` + 4 past `LockpickLevel`); the two only DC has are not named.
      `OpenDoor` is written only when the item has a state manager, which `CreateFromSaveGame`
      @8a5630 builds from the prototype's `Function` (DC 8ddc60), the same string the item keeps
      as its own: nothing else assigns it (DC 8dc1ac, 8ddcca, 8e1efb).
    - Enchantments @8deda0, ItemPricing @8dd6f0, MagicalEffect @8d7f20; the mover
      (DC 9e3f90) and the modifier collection @a0d1a0 (DC 987020), which the constructor
      always creates (DC 8d9bdd, 8d9c19); Charms @8dd7e0, Skills @8dd970, TouchList @8d8a80
      (`CRpgStats_V2_Item_Physics_CollidingList::GameSaveLoad` @a4d2f0, DC 9f4010)."""
    v.begin()
    rec = {"RegionName": v.string(), "SubRegionName": v.string(), "ContainingInventoryHandle": v.int()}
    if rec["ContainingInventoryHandle"] == -1:
        rec.update({"Translate": v.point3(), "Rotate": v.matrix3(), "LinearVelocity": v.point3(),
                    "AngularVelocity": v.point3(), "m_bObjectMovedSinceCreation": v.bool(),
                    "m_bStartPositionInitialized": v.bool(), "m_bFarEnoughFromStartPosition": v.bool(),
                    "StartPosition": v.point3()})
    rec.update({"InventoryPrototype": v.string(), "iIsLootBag": v.int(), "m_bVandalized": v.bool(),
                "m_bForceUpdateForStory": v.bool(), "m_fStoryRippleTimer": v.float(), "Amount": v.int(),
                "m_bUseAlternateVisual": v.bool(), "m_AlternateVisualUUID": v.string(), "m_bCanPickUp": v.bool(),
                "m_bCanUseInInventory": v.bool(), "m_sBoundToUUID": v.string(), "m_bBound": v.bool(),
                "m_sTriggerUUID": v.string(), "Function": v.string(), "m_CooldownTimeLeft": v.float(),
                "InventoryHandle": v.int(), "TreasurePrototype": v.string(), "TreasureGenerated": v.bool(),
                "Drops": v.bool(), "Effective": v.bool(), "OnStage": v.bool(), "m_bLocked": v.bool(),
                "m_sPortalName": v.string(), "m_bPhysicsFrozen": v.bool(), "DestroyOnUse": v.bool(),
                "SelfActivationTime": v.float(), "InteractionDistance": v.float(), "TrapHandle": v.int(),
                "ItemOwnerUUID": v.string(), "ItemName": v.string(), "HighlightAutomatically": v.bool(),
                "HighlightOnMouseOver": v.bool(), "BlocksCamera": v.bool(), "BookContentUUID": v.string(),
                "MaxEnchantmentSlots": v.int(), "CanDrop": v.bool(), "CanWalkThrough": v.bool(),
                "LockPickLevel": v.int(), "CanInteract": v.bool(), "IsGeneratedByTreasure": v.bool()})
    if v.since(2, 0x11):
        rec.update({"ForceLoaded": v.bool(), "Visible": v.bool()})
    if v.since(1, 0xA):
        rec["m_bMagicalAttributesGenerated"] = v.bool()
    if v.since(2, 5):
        rec["RenderToShadow"] = v.bool()
    if v.since(2, 0x13):
        rec["unnamed_8d5a46"] = v.bool()
    if v.since(2, 0x1B):
        rec["unnamed_8d5a78"] = v.int()
    rec["ItemUniqueness"] = v.string()
    if rec["Function"] in STATE_FUNCTIONS:
        rec["OpenDoor"] = v.int()
    rec["m_sFunctionParameter"] = v.string()
    rec["Enchantments"] = [v.string() for _ in range(v.count())]
    rec["m_fBaseGoldValue"] = v.float()
    rec["MagicGoldValues"] = [v.float() for _ in range(v.count())]
    rec.update({"EffectBaseType": v.string(), "EffectChangeType": v.string(), "Level": v.float(),
                "NamePrefix": v.string(), "NameSuffix": v.string()})
    rec["Mover"] = _item_mover(v)
    modifiers = []
    for _ in range(v.count()):
        handle = v.int()
        modifiers.append({"Handle": handle, **(_modifier(v) if handle != -1 else {})})
    rec["Modifiers"] = modifiers
    rec["Charms"] = [v.string() for _ in range(v.count())]
    rec["Skills"] = [{"skillUUID": v.string(), "skillLevel": v.int()} for _ in range(v.count())]
    if v.bool():
        v.begin()
        rec["TouchingList"] = [{"UUID": v.string(), "Type": v.int()} for _ in range(v.count())]
    return rec


def items(v: Visitor) -> dict:
    """`CRpgStats_V2_ItemManager::GameSaveLoad` @8a6ac0 (DC 7e7b90): every handle slot; a slot
    carries an item only when its handle is not -1 and its prototype is not empty (DC 7e7d4a)."""
    v.begin()
    n = v.count()
    out = {"Quota": v.int() if v.since(1, 0x16) else None, "Items": []}
    for _ in range(n):
        rec = {"Handle": v.int(), "PrototypeUUID": v.string()}
        if rec["Handle"] != -1 and rec["PrototypeUUID"]:
            rec.update({"UUID": v.string(), "IsLocal": v.bool()})
            rec.update(_item(v))
        out["Items"].append(rec)
    return out


def _stat_collection(v: Visitor) -> list:
    """`CRpgStats_V2_Stat_Collection::GameSaveLoad` @a0cc00 (DC 986b70): one slot per stat type
    (39 written), -1 for an empty one, else `CRpgStats_V2_Stat::GameSaveLoad` @a0b930 (DC 985930)."""
    v.begin()
    out = []
    for _ in range(v.count()):
        kind = v.int()
        if kind == -1:
            out.append(None)
            continue
        v.begin()
        out.append({"Type": kind, "Value": v.float(), "Min": v.float(), "Max": v.float()})
    return out


def _character_state(v: Visitor) -> dict:
    """`CRpgStats_V2_CharacterState::GameSaveLoad` @99b810 (DC 8cc8d0), with
    `CRpgstats_V2_Reputation::GameSaveLoad` @a4f4d0 (DC a11f60) and
    `CRpgstats_V2_Status_Manager::GameSaveLoad` @9b05e0 (DC 9149d0). `XPDebt` is named by the member
    GUP reads it into."""
    v.begin()
    rec = {"CHXP": v.bool()} if v.since(1, 0x15) else {}
    rec.update({"Laddering": v.bool(), "CanMorph": v.bool(), "LowJump": v.bool(), "IsRunning": v.bool(),
                "CombatMode": v.int(), "StatPoints": v.int(), "SkillPoints": v.int(), "DragonSkillPoints": v.int(),
                "EnemyHandle": v.int(), "TimeSinceLastHit": v.float(), "TimeSinceLastHitAnim": v.float(),
                "TimeSinceLastDamage": v.float(), "XP": v.int(), "Gold": v.int()})
    if v.since(1, 0x11):
        rec["XPDebt"] = v.int()
    if v.since(1, 0x15):
        rec["CJUMP"] = v.bool()
    v.begin()
    rec["Reputation"] = {"Characters": [{"Handle": v.int(), "Value": v.int()} for _ in range(v.count())],
                         "Factions": [{"Faction": v.string(), "Value": v.int()} for _ in range(v.count())]}
    v.begin()
    n = v.count()
    if not v.since(1, 0xB):
        rec["StatusHandle"] = v.int()
    statuses = []
    for _ in range(n):
        status = v.int()
        if status:
            raise StateError(f"status {status}: its typed record (DC 912710, vtable +0x5c) is not read yet")
        statuses.append(status)
    rec["Statuses"] = statuses
    rec["Timers"] = [{"Handle": v.int(), "Time": v.float()} for _ in range(v.count())]
    return rec


def _ai_controller(v: Visitor, kind: int) -> dict | None:
    """`CRpgStats_V2_Character::GameSaveLoadAIController` @830c50 (DC 752a90): whether the
    controller exists, then its `GameSaveLoad` (vtable +0x14; the classes from `SetAIController`,
    DC 752820). Combat, Dialog, Repel, Lua and UserInput write nothing."""
    if not v.bool():
        return None
    if kind == 2:       # EventManager @9dc580, DC 9517b0
        return {"BusyInScript": v.bool(), "ProcessingEvent": v.bool(), "ProcessedEvent": v.string(),
                "Events": [v.string() for _ in range(v.count())]}
    if kind == 3:       # Osiris, DC 98cd60
        if v.bool():
            raise StateError(f"Osiris AI state {v.int()}: its typed record (DC 98cb50, vtable +0x14) is not read yet")
        return {"HaveState": False}
    if kind == 6:       # Status, DC 98d860
        return {name: v.bool() for name in ("Stunned", "Cowering", "Blind", "Fleeing", "Polymorphed", "Confused",
                                            "Awed", "Retreating", "Dying", "Assembling", "OnElevator")}
    return {}


AI_CONTROLLERS = ("Combat", "Dialog", "EventManager", "Osiris", "Repel", "Lua", "Status", "UserInput")


def _character(v: Visitor) -> dict:
    """`CRpgStats_V2_Character::GameSaveLoad` @846580 (DC 76ae20): Position @83a6c0, Story @836de0,
    Various @836ed0, Skills @8459e0, Quests @845b60, the character state and relations, Stats
    @8374a0, the backed-up stats, Physics @837540, Priority @9dad30 and the AI controllers @832080.
    The constructor (DC 75e020) creates every part, so each is always written. `m_UnsummonSkill`
    is named by the member GUP reads it into; the fields only DC has are not named."""
    v.begin()
    rec = {"RegionName": v.string(), "SubRegionName": v.string(), "Translate": v.point3(), "Rotate": v.matrix3(),
           "Velocity": v.point3(), "StartPosition": v.point3(), "Orientation": v.point3(),
           "Script": v.string(), "IsInTeam": v.bool(), "TeamID": v.uint(), "Dialog": v.string(), "Trainer": v.string(),
           "Name": v.string(),
           "StoryPriority": v.bool(), "LightTypeLightOn": v.bool(), "LightTypeIntensity": v.float(),
           "LightTypeSpecularLevel": v.float(), "LightTypeCastShadows": v.bool(),
           "LightTypeMaxAttenuationRadius": v.float(), "LightTypeMinAttenuationRadius": v.float(),
           "LightTypeRed": v.float(), "LightTypeGreen": v.float(), "LightTypeBlue": v.float(),
           "TreasureID": v.string(), "TreasureGenerated": v.bool()}
    if v.since(1, 0x1E):
        rec["m_UnsummonSkill"] = v.int()
    if v.since(2, 2):
        rec["unnamed_75907f"] = v.bool()
    rec.update({"InventoryHandle": v.int(), "DragonMorphInventoryHandle": v.int(), "IsPlayer": v.bool(),
                "IsFlying": v.bool(), "MeleeWeaponHandle": v.int(), "RangedWeaponHandle": v.int(),
                "OwnerHandle": v.int(), "OwnerType": v.int(), "OnStage": v.bool(), "Ghost": v.bool(),
                "ControlType": v.int(), "FreezePhysics": v.bool(), "mCanAttack": v.bool(), "mCanBeAttacked": v.bool(),
                "mEvasive": v.bool(), "mCanDie": v.bool(), "mCanReceiveDmg": v.bool(), "mCanTrade": v.bool(),
                "mInDialog": v.bool(), "weaponanimbank": v.uint(), "actionanimbank": v.uint(),
                "postureanimbank": v.uint(), "InteractionDistance": v.float(), "VisualPrototypeUUID": v.string()})
    if v.since(1, 0x14):
        rec.update({"VisualPrototypeUUIDOverride": v.string(), "CullingRange": v.int()})
    rec["Skills"] = [{"PrototypeHandle": v.int(), "SkillLevel": v.int(), "SkillBonus": v.int(), "SkillLimit": v.int(),
                      "Cooldown": v.float()} for _ in range(v.count())]
    rec["mQuestNPCStatus"] = v.uint()
    rec["Quests"] = [v.int() for _ in range(v.count())]
    rec["State"] = _character_state(v)
    v.begin()                                   # `CRpgStats_V2_Character_Relations::GameSaveLoad` @a07940
    rec["FactionName"] = v.string()
    rec["Stats"] = _stat_collection(v)
    rec.update({"Level": v.int(), "CurrentHP": v.float(), "CurrentEnd": v.float()})
    if v.since(2, 2):
        rec.update({f"unnamed_{at}": v.float() for at in ("7595f2", "759605", "759618", "75962b", "75963e", "759651")})
    rec["BackupStats"] = _stat_collection(v)
    rec.update({"StatsBackedUp": v.bool(), "PhysicsHeight": v.float(), "PhysicsRadius": v.float(),
                "CullingDistance": v.float()})
    rec["AIControllers"] = {name: _ai_controller(v, kind) for kind, name in enumerate(AI_CONTROLLERS)}
    return rec


def characters(v: Visitor) -> dict:
    """`CRpgStats_V2_CharacterManager::GameSaveLoad` @8106a0 (DC 727650, called for the
    `SaveLoadCharacters` checkpoint, DC 6e2c3d): the same slots as the items'."""
    v.begin()
    n = v.count()
    out = {"Quota": v.int() if v.since(1, 0x16) else None, "Characters": []}
    for _ in range(n):
        rec = {"Handle": v.int(), "PrototypeUUID": v.string()}
        if rec["Handle"] != -1 and rec["PrototypeUUID"]:
            rec.update({"UUID": v.string(), "IsLocal": v.bool()})
            rec.update(_character(v))
        out["Characters"].append(rec)
    return out


def fortresses(v: Visitor) -> dict:
    """`CRpgStats_V2_FlyingFortress_Manager_Building::GameSaveLoad` @8adcd0 (DC 7d79e0), each
    `CRpgStats_V2_FlyingFortress_Building::GameSaveLoad` @a03870 (DC 8f68c0)."""
    v.begin()
    n = v.count()
    out = {"Quota": v.int() if v.since(1, 0x16) else None, "Buildings": []}
    for _ in range(n):
        rec = {"BuildingHandle": v.int(), "PrototypeUUID": v.string(), "UUID": v.string(), "IsLocal": v.bool()}
        v.begin()
        rec.update({"RegionName": v.string(), "SubRegionName": v.string(), "Translate": v.point3(),
                    "Rotate": v.matrix3(), "Velocity": v.point3(), "Orientation": v.point3(),
                    "CharacterOrientation": v.point3(), "Priority_Forced_Low": v.bool(),
                    "TeleportationTargetHandle": v.int(), "TeleportationTarget": v.string(),
                    "CurrentHitpoints": v.float(), "FactionName": v.string()})
        if v.since(1, 0x21):
            rec["unnamed_8f6a31"] = v.uint()
        if v.since(2, 3):
            rec["Mover"] = _item_mover(v)
            rec["unnamed_8f6a78"] = v.bool()
        if v.since(2, 0xC):
            rec["unnamed_8f6aa1"] = v.bool()
        out["Buildings"].append(rec)
    return out


def traps(v: Visitor) -> dict:
    """`CRpgStats_V2_TrapManager::GameSaveLoad` @902150 (DC 7cedb0), each
    `CRpgStats_V2_TrapScript::GameSaveLoad` @a11740 (DC 98f180): state, the script's frames, and the
    commands running (empty in both shipped saves; their typed records, DC 98dfc0, are not read)."""
    v.begin()
    out = []
    for _ in range(v.count()):
        rec = {"BackReference": v.int(), "UUID": v.string()}
        v.begin()
        rec.update({"mCurrentFrameNumber": v.int(), "mHighestFrameNumber": v.int(), "mIsBroken": v.bool(),
                    "mIsExecutingFrame": v.bool()})
        if v.since(1, 0x18):
            rec.update({"unnamed_98f21e": v.bool(), "unnamed_98f22e": v.string(), "unnamed_98f23e": v.string()})
        rec["Frames"] = [{"frameNumber": v.int(), "command": v.int(), "param1": v.string(), "param2": v.string(),
                          "param3": v.string(), "param4": v.string()} for _ in range(v.count())]
        rec["Commands"] = _empty_list(v, f"trap {rec['UUID']} commands", "DC 98f475: Command, typed record 98dfc0")
        out.append(rec)
    return {"Traps": out}


def skill_trainers(v: Visitor) -> dict:
    """`CRpgStats_V2_SkillTrainerManager::GameSaveLoad` @78bdb0 (DC 8a0950), each
    `CRpgStats_V2_SkillTrainer::GameSaveLoad` @78ba80 (DC 8a0640): its lessons."""
    v.begin()
    out = []
    for _ in range(v.count()):
        rec = {"SkillTrainerHandle": v.int(), "UUID": v.string()}
        v.begin()
        lessons = []
        for _ in range(v.count()):
            lesson = {"Lesson": v.bool()}
            if v.since(1, 0x1B):
                lesson.update({"skill": v.string(), "int1": v.int(), "description": v.string(), "int2": v.int(),
                               "int3": v.int()})
            lessons.append(lesson)
        rec["Lessons"] = lessons
        out.append(rec)
    return {"SkillTrainers": out}


def _treasure_group(v: Visitor) -> dict:
    """`CRpgStats_V2_TreasureGroup::GameSaveLoad` (DC a0a820)."""
    v.begin()
    return {"Group": v.string(), "Frequency": v.int(), "MinRarity": v.int(), "MaxRarity": v.int(),
            "MinCharmAmount": v.int(), "MaxCharmAmount": v.int(), "RarityChance": v.float(),
            "ItemUniqueness": v.string()}


def treasures(v: Visitor) -> dict:
    """`CRpgStats_V2_TreasureManager::GameSaveLoad` @9822a0 (DC 8beb90): per treasure its amounts
    (DC 8be2b0) and `CRpgStats_V2_TreasureGroup_Collection::GameSaveLoad` @a4ad40 (DC a0ade0), a
    group written only when `ValidGroup`."""
    v.begin()
    out = []
    for _ in range(v.count()):
        rec = {"Handle": v.int(), "UUID": v.string()}
        v.begin()
        rec["MinAmount"], rec["MaxAmount"] = v.int(), v.int()
        v.begin()
        groups = []
        for _ in range(v.count()):
            valid = v.bool()
            groups.append(_treasure_group(v) if valid else None)
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
    """(offset of the name's length, name) of every checkpoint, found by their prefix. Used
    only to report where an unread section ends; reading itself is sequential."""
    out, at = [], stream.find(b"SaveLoad")
    while at >= 0:
        n = struct.unpack_from("<I", stream, at - 4)[0]
        name = stream[at:at + n]
        if n < 128 and name.isascii():
            out.append((at - 4, name.decode()))
        at = stream.find(b"SaveLoad", at + 8)
    return out


def read(data: bytes) -> dict:
    """Every section of a savegame, by checkpoint name, in stream order. A section without a
    reader is `{"unread": bytes}` so the gap is visible; a reader that does not end where the
    next checkpoint begins raises."""
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
        sections[key] = reader(v)
        if v.q != end - start:
            raise StateError(f"{name}: read {v.q} of {end - start} bytes")
    return sections
