# Savegame

## Engine state

`CRpgStats_V2_LoadSaveEntry::SaveLoadInternal` @7e8180 writes the sections in a fixed order, each after a named checkpoint (`CheckPointTest`); each manager's `GameSaveLoad` reads or writes its values in order through one visitor, `CRpgStats_V2_LoadBinaryVisitor` or `CRpgStats_V2_SaveBinaryVisitor`, which writes no tags — CRpgStats_V2_LoadSaveEntry::SaveLoadInternal @7e8180 decomp

Visitor primitives, little-endian, no tags (@98cbe0): LoadSaveImpl(int*) @98b0e0; LoadSaveImpl(uint*) @98b6a0, LoadSaveImpl(ulong*) @98b700; LoadSaveImpl(ushort*) @98b6d0; LoadSaveImpl(float*) @98b110; LoadSaveImpl(bool*) @98b1a0 (one byte); LoadSaveImpl(std::string*) @98b490, LoadSaveImpl(NiFixedString*) @98b590, LoadSaveImpl(char**) @98b140 (u32 length, the bytes); LoadSaveImpl(TLoadSaveCharBuffer*) @98b730 (a u32 the loader ignores, then n bytes); LoadSaveImpl(NiPoint3*) @98b1d0; LoadSaveImpl(NiPoint2*) @98b250; LoadSaveImpl(NiColor*) @98b2b0; LoadSaveImpl(NiColorA*) @98b330; LoadSaveImpl(NiBound*) @98b3c0 (centre, radius); LoadSaveImpl(NiMatrix3*) @98af50; `GetSetAmountOfChildren` @98b7a0 (a u32) — CRpgStats_V2_LoadBinaryVisitor, CRpgStats_V2_SaveBinaryVisitor @98cbe0 decomp

`BeginObject` @98bee0 is a u32, the object's `CalculateCheckSum`, when the save uses save-load objects (header byte); `EndObject` @98bdc0 reads nothing — BeginObject @98bee0, EndObject @98bdc0 decomp

The save's version (major, minor) is compared through `GetVersionNumber` — CRpgStats_V2_SaveLoadVisitor::GetVersionNumber @88b340 decomp

Sections and the function that reads each; `dc` marks the Developer's Cut address where it differs:

trophies: `CRpgStats_V2_TrophiesManager::GameSaveLoad` @97b920, `CRpgStats_V2_Trophy::GameSaveLoad` @97b2a0 — CRpgStats_V2_TrophiesManager::GameSaveLoad @97b920 decomp, CRpgStats_V2_Trophy::GameSaveLoad @97b2a0 decomp

timers: `CRpgStats_V2_TimerManager::GameSaveLoad` @915250 (no object checksum; a timer with a name and a duration above 0 is started again with `AddTimer`) — CRpgStats_V2_TimerManager::GameSaveLoad @915250 decomp

sync data: `CGameLogic_SyncData::GameSaveLoad` @778cf0 — CGameLogic_SyncData::GameSaveLoad @778cf0 decomp

names of characters and items: `CRpgStats_V2_NameManager::GameSaveLoad` @984a00 (@8c1330 dc) — CRpgStats_V2_NameManager::GameSaveLoad @984a00 decomp, CRpgStats_V2_NameManager::GameSaveLoad @8c1330 dc

item sets (three weapon sets): `CGameLogic_ItemSets::GameSaveLoad` @92d9b0 (@8475d0 dc) — CGameLogic_ItemSets::GameSaveLoad @92d9b0 decomp, CGameLogic_ItemSets::GameSaveLoad @8475d0 dc

player control: `CGameLogic_PlayerControl::GameSaveLoad` @7f5d70 (@6f56e0 dc); DC names the third looks field `skinTone` and adds fields after `OriginalVersion`; @6f5c34 dc writes the follow camera's yaw only while the unnamed DC global 0x14f18fc is set — CGameLogic_PlayerControl::GameSaveLoad @7f5d70 decomp, CGameLogic_PlayerControl::GameSaveLoad @6f56e0 dc

encounters (Developer's Cut only): the count is an int — CGameLogic_Encounter @800e20 dc

player interface: `CGameLogic_PlayerControl_UserInterface::GameSaveLoad` @809510 (@71d500 dc), the PC interface (@908b30 dc), seven `CGameLogic_InventoryPosHelper::GameSaveLoad` (@a18680 dc) — CGameLogic_PlayerControl_UserInterface::GameSaveLoad @809510 decomp, CGameLogic_PlayerControl_UserInterface::GameSaveLoad @71d500 dc, CGameLogic_InventoryPosHelper::GameSaveLoad @a18680 dc

dialog log: `CDialogLogManager::GameSaveLoad` @9187c0 (@816dd0 dc) — CDialogLogManager::GameSaveLoad @9187c0 decomp, CDialogLogManager::GameSaveLoad @816dd0 dc

quests: `CRpgStats_V2_QuestManager::GameSaveLoad` @96f3f0 (@8aa3f0 dc) — CRpgStats_V2_QuestManager::GameSaveLoad @96f3f0 decomp, CRpgStats_V2_QuestManager::GameSaveLoad @8aa3f0 dc

region cache: `CRpgStats_V2_LoadSaveManager::GameSaveLoadRegionCache` (@84f190 dc), region, sub-region and cache size until a size of 0 — CRpgStats_V2_LoadSaveManager::GameSaveLoadRegionCache @84f190 dc

projectiles: `CGameLogic_Projectile_Manager::GameSaveLoad` @8b8840 (@7d35a0 dc) — CGameLogic_Projectile_Manager::GameSaveLoad @8b8840 decomp, CGameLogic_Projectile_Manager::GameSaveLoad @7d35a0 dc

game events: `CRpgStats_V2_GameEventManager::GameSaveLoad` @897120 (@7b61e0 dc), the queued story events — CRpgStats_V2_GameEventManager::GameSaveLoad @897120 decomp, CRpgStats_V2_GameEventManager::GameSaveLoad @7b61e0 dc

running dialogs: `CGameLogic_DialogControl::GameSaveLoad` @802040 (@705300 dc) — CGameLogic_DialogControl::GameSaveLoad @802040 decomp, CGameLogic_DialogControl::GameSaveLoad @705300 dc

effect areas: `CRpgStats_V2_EffectArea_Manager::GameSaveLoad` @9118e0 (@806da0 dc), one slot per area; a slot of type 0 is empty, any other type loads the area through its vtable +0x28 — CRpgStats_V2_EffectArea_Manager::GameSaveLoad @9118e0 decomp, CRpgStats_V2_EffectArea_Manager::GameSaveLoad @806da0 dc

button mappings: `CGameLogic_MappedButton::GameSaveLoad` (@8d2800 dc), `CGameLogic_ButtonMappings::GameSaveLoad` @92c6f0 (@845c50 dc), the human map then the dragon map (`MapButton` @92c510 picks MT_HUMAN 1 / MT_DRAGON 0) — CGameLogic_MappedButton::GameSaveLoad @8d2800 dc, CGameLogic_ButtonMappings::GameSaveLoad @92c6f0 decomp, CGameLogic_ButtonMappings::GameSaveLoad @845c50 dc

map coordinates (Developer's Cut only): region to sub-regions; the fog buffer (@863ac0 dc) is read only from saves before 2.5 — CGameLogic_MapCoordinatesManager @865da0 dc, CGameLogic_MapCoordinatesManager @865290 dc

battle tower: `CRpgStats_V2_BattleTower::GameSaveLoad` @8fb9d0 (@7bd5a0 dc) and its four platforms in this order: necromancer's alcove (@9cad60 dc), 9cf9d0, training arena (@9d06f0 dc), 9ce4c0 — CRpgStats_V2_BattleTower::GameSaveLoad @8fb9d0 decomp, CRpgStats_V2_BattleTower::GameSaveLoad @7bd5a0 dc

alignment: `CRpgstats_V2_Alignment::GameSaveLoad` @964b10 (@887980 dc), the groups with their parents, then four maps `CRpgstats_V2_AlignmentMap::GameSaveLoad` @a76590 (@a07ce0 dc) keyed by a character handle (C) or a faction name (F); a value below 25 is enemy, -1 removes an override — CRpgstats_V2_Alignment::GameSaveLoad @964b10 decomp, CRpgstats_V2_Alignment::GameSaveLoad @887980 dc, CRpgstats_V2_AlignmentMap::GameSaveLoad @a76590 decomp, CRpgstats_V2_AlignmentMap::GameSaveLoad @a07ce0 dc

waypoints: `CRpgStats_V2_WayPointManager::GameSaveLoad` @93b990 (@8620a0 dc, through the manager's vtable +0x3c), each `CRpgStats_V2_WayPoint::GameSaveLoad` @a1ac30 — CRpgStats_V2_WayPointManager::GameSaveLoad @93b990 decomp, CRpgStats_V2_WayPoint::GameSaveLoad @a1ac30 decomp

map markers: `CGameLogic_MapMarker_Manager::GameSaveLoad` @9399c0 (@85ffa0 dc), each `CGameLogic_MapMarker::GameSaveLoad` @939430 (@85f9c0 dc, which adds `mItemHandle` from 2.x) — CGameLogic_MapMarker_Manager::GameSaveLoad @9399c0 decomp, CGameLogic_MapMarker_Manager::GameSaveLoad @85ffa0 dc, CGameLogic_MapMarker::GameSaveLoad @939430 decomp

effects: `CGameLogic_Effect::GameSaveLoad` @89a7b0, every entry named `Scale` in the engine — CGameLogic_Effect::GameSaveLoad @89a7b0 decomp

perpetual state: `CRpgStats_V2_PerpetualStateManager::GameSaveLoad` @89c150 (@882e70 dc): character effects (881c90), item effects (882b40), custom animations (882480, GUP `GameSaveLoadCustomAnimationList`), culled scenery (882600, GUP `GameSaveLoadCulledSceneryList`: `EngineScenerySetOn/OffStage`), hit effect parameters (880d30), trigger effects (881680), story lights (881940: `EngineSetLightOnStage`), story soundbanks (880bd0), effect preloads (880e60), the Lua game time (880b70), the active subtitle and the rift timer; the load and save paths differ in 882600 and 881940 — CRpgStats_V2_PerpetualStateManager::GameSaveLoad @89c150 decomp, CRpgStats_V2_PerpetualStateManager::GameSaveLoad @882e70 dc

Lua variables: `CLuaVariableManager::GameSaveLoad` @8f5e60 (@7b16a0 dc): five value lists (`CLuaVariableList<int|double|char*|int*|NiPoint3,32>`, @7b26d0 dc..7b2b90: real size, size, real free size, free size, one buffer of `size` values when allocated (@7b2380 dc), the free indices), eight optional key tables (`CLuaVariableManager_Key2Table::GameSaveLoad` @8f5900, @7b1010 dc: count, capacity, per slot a key and a length n with 2n+1 ints), and the name pool (@9c06f0 dc: used size, 512 ints, 769 buckets of index lists (9c04c0), an int and a 0x8000-byte buffer from 2.23, 0x4000 before) — CLuaVariableManager::GameSaveLoad @8f5e60 decomp, CLuaVariableManager::GameSaveLoad @7b16a0 dc, CLuaVariableManager_Key2Table::GameSaveLoad @8f5900 decomp

story: `COsirisManager::GameSaveLoad` @80b270 (@736f10 dc) — COsirisManager::GameSaveLoad @80b270 decomp, COsirisManager::GameSaveLoad @736f10 dc

triggers: `CRpgStats_V2_Trigger::GameSaveLoad` @8997b0 (@9783b0 dc); `_Point` @780110 (@977b20 dc); `_Orientation` @780a10 (@976800 dc); `_Area::InheritedGameSaveLoad` @9c8900 (@9358d0 dc): the base, the shape (`CPolyArea::GameSaveLoad` @77ef60 through the shape's vtable +0x30: `CAreaPoint::GameSaveLoad` @77c730 per point, bottom, top), the area's state and four handle lists, the third and fourth written through offsets +0x44 and +0x54 (x86 9c8c00, 9c8d10); factory @72e7c0 dc (jump table 0x72ea10, constructors 9756f0 and 970aa0); ETriggerType is in gup-enums.tsv, 21 and 22 are the Developer's Cut's encounter point and zone; type 21 is @9759a0 dc from 2.22; the visual effect areas (@971fb0 dc, 971b20) write no checksum of their own — CRpgStats_V2_Trigger::GameSaveLoad @8997b0 decomp, CRpgStats_V2_Trigger::GameSaveLoad @9783b0 dc, _Area::InheritedGameSaveLoad @9c8900 decomp, _Area::InheritedGameSaveLoad @9358d0 dc, CPolyArea::GameSaveLoad @77ef60 decomp, CAreaPoint::GameSaveLoad @77c730 decomp

dialog events: `CDialogManager::GameSaveLoad` @874300 (@7f1af0 dc): `m_ptrGlobalEventManager` and `m_ptrLocalEventManager`, each through `CRpgStats_V2_EventManager::GameSaveLoad` @80c0d0 (@737d50 dc): the event UUID and its `State`; global ones are what `SetGlobalEvent` and `ClearGlobalEvent` change (`CRpgStats_V2_GlobalEventManager::SetEventState` @80bc20) — CDialogManager::GameSaveLoad @874300 decomp, CDialogManager::GameSaveLoad @7f1af0 dc, CRpgStats_V2_EventManager::GameSaveLoad @80c0d0 decomp, CRpgStats_V2_EventManager::GameSaveLoad @737d50 dc, CRpgStats_V2_GlobalEventManager::SetEventState @80bc20 decomp

inventories: `CRpgStats_V2_InventoryManager::GameSaveLoad` @96ca40 (@8a77b0 dc): handle, prototype and `IsLocal` per inventory, then `CRpgStats_V2_Inventory::GameSaveLoad` @8c7cc0 (@893480 dc): the owner and the occupied slots as (slot, item handle) — CRpgStats_V2_InventoryManager::GameSaveLoad @96ca40 decomp, CRpgStats_V2_InventoryManager::GameSaveLoad @8a77b0 dc, CRpgStats_V2_Inventory::GameSaveLoad @8c7cc0 decomp, CRpgStats_V2_Inventory::GameSaveLoad @893480 dc

item mover: `CRpgStats_V2_Item_Mover::GameSaveLoad` @a43920 (@a16cc0 dc for a fortress, 9e3f90 for an item), no object checksum — CRpgStats_V2_Item_Mover::GameSaveLoad @a43920 decomp

items: `CRpgStats_V2_Item::GameSaveLoad` @8df8b0 (@8dc680 dc): Position @8d9540 (@8d4770 dc; the transform only when in no inventory), Misc @8d9f00 (@8d5640 dc), Enchantments @8deda0, ItemPricing @8dd6f0, MagicalEffect @8d7f20, the mover, `CRpgStats_V2_Modifier_Collection::GameSaveLoad` @a0d1a0 (@987020 dc), Charms @8dd7e0, Skills @8dd970, TouchList @8d8a80 (`CRpgStats_V2_Item_Physics_CollidingList::GameSaveLoad` @a4d2f0, @9f4010 dc); `OpenDoor` is written only when the item has a state manager, which `CRpgStats_V2_ItemManager::CreateFromSaveGame` @8a5630 builds from the prototype's `Function` (@8ddc60 dc); `CRpgStats_V2_ItemStateManagerFactory::CreateManager` @a4f880 (@a12610 dc); `CRpgStats_V2_Modifier::GameSaveLoad` @a0bcf0 (@985cf0 dc) — CRpgStats_V2_Item::GameSaveLoad @8df8b0 decomp, CRpgStats_V2_Item::GameSaveLoad @8dc680 dc, CRpgStats_V2_Modifier_Collection::GameSaveLoad @a0d1a0 decomp, CRpgStats_V2_Modifier_Collection::GameSaveLoad @987020 dc, CRpgStats_V2_Item_Physics_CollidingList::GameSaveLoad @a4d2f0 decomp, CRpgStats_V2_ItemManager::CreateFromSaveGame @8a5630 decomp, CRpgStats_V2_ItemStateManagerFactory::CreateManager @a4f880 decomp, CRpgStats_V2_ItemStateManagerFactory::CreateManager @a12610 dc, CRpgStats_V2_Modifier::GameSaveLoad @a0bcf0 decomp, CRpgStats_V2_Modifier::GameSaveLoad @985cf0 dc

item manager: `CRpgStats_V2_ItemManager::GameSaveLoad` @8a6ac0 (@7e7b90 dc): every handle slot; a slot carries an item only when its handle is not -1 and its prototype is not empty (@7e7d4a dc); the manager's checksum is `CRpgStats_V2_ItemManager::CalculateCheckSum` @8a3d80, the number of items `ShouldBeSaved` — CRpgStats_V2_ItemManager::GameSaveLoad @8a6ac0 decomp, CRpgStats_V2_ItemManager::GameSaveLoad @7e7b90 dc, CRpgStats_V2_ItemManager::CalculateCheckSum @8a3d80 decomp

stats: `CRpgStats_V2_Stat_Collection::GameSaveLoad` @a0cc00 (@986b70 dc), one slot per stat type (39 written), -1 for an empty one, else `CRpgStats_V2_Stat::GameSaveLoad` @a0b930 (@985930 dc) — CRpgStats_V2_Stat_Collection::GameSaveLoad @a0cc00 decomp, CRpgStats_V2_Stat_Collection::GameSaveLoad @986b70 dc, CRpgStats_V2_Stat::GameSaveLoad @a0b930 decomp, CRpgStats_V2_Stat::GameSaveLoad @985930 dc

character state: `CRpgStats_V2_CharacterState::GameSaveLoad` @99b810 (@8cc8d0 dc), with `CRpgstats_V2_Reputation::GameSaveLoad` @a4f4d0 (@a11f60 dc) and `CRpgstats_V2_Status_Manager::GameSaveLoad` @9b05e0 (@9149d0 dc) — CRpgStats_V2_CharacterState::GameSaveLoad @99b810 decomp, CRpgStats_V2_CharacterState::GameSaveLoad @8cc8d0 dc, CRpgstats_V2_Reputation::GameSaveLoad @a4f4d0 decomp, CRpgstats_V2_Reputation::GameSaveLoad @a11f60 dc, CRpgstats_V2_Status_Manager::GameSaveLoad @9b05e0 decomp, CRpgstats_V2_Status_Manager::GameSaveLoad @9149d0 dc

AI controller: `CRpgStats_V2_Character::GameSaveLoadAIController` @830c50 (@752a90 dc): whether the controller exists, then its `GameSaveLoad` (vtable +0x14; classes from `SetAIController`, @752820 dc); Combat, Dialog, Repel, Lua and UserInput write nothing; EventManager @9dc580 (@9517b0 dc), Osiris @98cd60 dc, Status @98d860 dc — CRpgStats_V2_Character::GameSaveLoadAIController @830c50 decomp, CRpgStats_V2_Character::GameSaveLoadAIController @752a90 dc

characters: `CRpgStats_V2_Character::GameSaveLoad` @846580 (@76ae20 dc): Position @83a6c0, Story @836de0, Various @836ed0, Skills @8459e0, Quests @845b60, the character state and relations (`CRpgStats_V2_Character_Relations::GameSaveLoad` @a07940), Stats @8374a0, the backed-up stats, Physics @837540, Priority @9dad30 and `CRpgStats_V2_Character::GameSaveLoadAIControllers` @832080; the constructor (@75e020 dc) creates every part, so each is always written — CRpgStats_V2_Character::GameSaveLoad @846580 decomp, CRpgStats_V2_Character::GameSaveLoad @76ae20 dc, CRpgStats_V2_Character_Relations::GameSaveLoad @a07940 decomp, CRpgStats_V2_Character::GameSaveLoadAIControllers @832080 decomp

character manager: `CRpgStats_V2_CharacterManager::GameSaveLoad` @8106a0 (@727650 dc, called for the `SaveLoadCharacters` checkpoint, @6e2c3d dc): the same slots as the items'; its checksum (@80daa0) is 0 — CRpgStats_V2_CharacterManager::GameSaveLoad @8106a0 decomp

flying fortress: `CRpgStats_V2_FlyingFortress_Manager_Building::GameSaveLoad` @8adcd0 (@7d79e0 dc), each `CRpgStats_V2_FlyingFortress_Building::GameSaveLoad` @a03870 (@8f68c0 dc) — CRpgStats_V2_FlyingFortress_Manager_Building::GameSaveLoad @8adcd0 decomp, CRpgStats_V2_FlyingFortress_Manager_Building::GameSaveLoad @7d79e0 dc, CRpgStats_V2_FlyingFortress_Building::GameSaveLoad @a03870 decomp, CRpgStats_V2_FlyingFortress_Building::GameSaveLoad @8f68c0 dc

traps: `CRpgStats_V2_TrapManager::GameSaveLoad` @902150 (@7cedb0 dc), each `CRpgStats_V2_TrapScript::GameSaveLoad` @a11740 (@98f180 dc): state, the script's frames, and the commands running (typed records @98dfc0 dc) — CRpgStats_V2_TrapManager::GameSaveLoad @902150 decomp, CRpgStats_V2_TrapManager::GameSaveLoad @7cedb0 dc, CRpgStats_V2_TrapScript::GameSaveLoad @a11740 decomp, CRpgStats_V2_TrapScript::GameSaveLoad @98f180 dc

skill trainers: `CRpgStats_V2_SkillTrainerManager::GameSaveLoad` @78bdb0 (@8a0950 dc), each `CRpgStats_V2_SkillTrainer::GameSaveLoad` @78ba80 (@8a0640 dc): its lessons — CRpgStats_V2_SkillTrainerManager::GameSaveLoad @78bdb0 decomp, CRpgStats_V2_SkillTrainerManager::GameSaveLoad @8a0950 dc, CRpgStats_V2_SkillTrainer::GameSaveLoad @78ba80 decomp, CRpgStats_V2_SkillTrainer::GameSaveLoad @8a0640 dc

treasures: `CRpgStats_V2_TreasureManager::GameSaveLoad` @9822a0 (@8beb90 dc): per treasure its amounts (@8be2b0 dc) and `CRpgStats_V2_TreasureGroup_Collection::GameSaveLoad` @a4ad40 (@a0ade0 dc), a group written only when `ValidGroup`; `CRpgStats_V2_TreasureGroup::GameSaveLoad` (@a0a820 dc) — CRpgStats_V2_TreasureManager::GameSaveLoad @9822a0 decomp, CRpgStats_V2_TreasureManager::GameSaveLoad @8beb90 dc, CRpgStats_V2_TreasureGroup_Collection::GameSaveLoad @a4ad40 decomp, CRpgStats_V2_TreasureGroup_Collection::GameSaveLoad @a0ade0 dc, CRpgStats_V2_TreasureGroup::GameSaveLoad @a0a820 dc

The story is written as blocks of at most 0x400 bytes; `COsiSmartBuf`'s destructor @1087a10 writes the last block only when it is not empty — COsirisManager::GameSaveLoad @80b270 decomp

## Measured

Both shipped initial savegames read, written through JSON and read again give the same decompressed stream and header (sizes and checksum aside) — `python -m dv2lib.savestate round-trip ~/dv2-extract/Win32/Episodes/Episode_1_Extended/Story/init_savegame.dsg ~/dv2-extract/Win32/Episodes/Episode_2/Story/init_savegame.dsg` from `~/divinity2-lib`
