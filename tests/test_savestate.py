import struct

import pytest

from dv2lib import savestate


def section(reader, data, expected, version=(3, 6)):
    v = savestate.Visitor(data, False, version)
    assert reader(v, savestate.ABSENT) == expected
    assert v.q == len(data)
    w = savestate.Visitor(None, False, version)
    reader(w, expected)
    assert w.d == data


# CDialogLogManager::GameSaveLoad @816f4e dc
def test_dialog_logs():
    section(savestate.dialog_logs,
            bytes.fromhex('00002041 01000000 0000c03f 01000000 41 01000000 42 01000000 43 01 00'),
            {'CurrentTime': 10.0, 'Entries': [{'#d8198334': 1.5, '#e4784588': 'A',
             '#05d8b24b': 'B', 'Text': 'C', '#ea02f348': True, '#00000000': False}]})


# CDialogLogManager::GameSaveLoad @816faa dc
def test_dialog_logs_before_2_25():
    section(savestate.dialog_logs,
            bytes.fromhex('00002041 01000000 0000c03f 01000000 41 01000000 42 01000000 43 01'),
            {'CurrentTime': 10.0, 'Entries': [{'#d8198334': 1.5, '#e4784588': 'A',
             '#05d8b24b': 'B', 'Text': 'C', '#ea02f348': True}]}, (2, 24))


# CRpgStats_V2_LoadBinaryVisitor::GetSetAmountOfChildren @98b7a0 decomp
@pytest.mark.parametrize('counter', [None, 'int'])
def test_count_exceeds_remaining_bytes(counter):
    v = savestate.Visitor(bytes.fromhex('ffffff7f 00'), False, (3, 6))
    with pytest.raises(savestate.StateError, match='offset 0'):
        v.each(savestate.ABSENT, getattr(v, counter) if counter else None)


def test_string_exceeds_remaining_bytes():
    v = savestate.Visitor(bytes.fromhex('05000000 41'), False, (3, 6))
    with pytest.raises(savestate.StateError, match='offset 4'):
        v.string()


# CGameLogic_DialogControl::GameSaveLoad @705444 dc
def test_dialog_control():
    section(savestate.dialog_control,
            bytes.fromhex('01000000 01000000 41 01000000 42 feffffff 0000c03f 00002040 01'),
            {'Dialogs': [{'#00000000': ['A', 'B', -2, 1.5, 2.5, True]}]})


# CRpgStats_V2_QuestManager::GameSaveLoad @8aa536 dc, CRpgStats_V2_Quest::GameSaveLoad @8a9974 dc
@pytest.mark.parametrize('version,tail', [((2, 24), b''), ((2, 25), b'\x01')])
def test_quests(version, tail):
    expected = {'Quests': [{'PrototypeName': 'Q', '#af0cbf8c': 7, '#12e4a2e2': 'S'},
                           {'PrototypeName': '', '#af0cbf8c': -1}]}
    if tail:
        expected['Quests'][0]['#00000000'] = True
    section(savestate.quests, bytes.fromhex('02000000 01000000 51 07000000 01000000 53')
            + tail + bytes.fromhex('00000000 ffffffff'), expected, version)


# CRpgStats_V2_LoadSaveManager::GameSaveLoadRegionCache @84f263 dc, CRpgStats_V2_LoadSaveManager::GameSaveLoadCacheData @84eba0 dc, CRpgStats_V2_LoadSaveManager::SCacheMemoryData::GameSaveLoad @847e70 dc
def test_region_cache():
    section(savestate.region_cache,
            bytes.fromhex('01000000 52 01000000 53 01000000 01 01000000 43 03000000 06000000'
                          '02000000 02000000 aabb 00 00 00'),
            {'RegionName': 'R', 'SubRegionName': 'S', '#c03439af': 1,
             'Cache': [[{'#c0315815': 'C', '#00000000': [3, 6], '#6a90aba8': 'qrs='}],
                       None, None, None]})


# CRpgStats_V2_LoadSaveManager::GameSaveLoadRegionCache @84f2a2 dc
def test_empty_region_cache_preserves_names():
    section(savestate.region_cache, bytes.fromhex('01000000 52 01000000 53 00000000'),
            {'RegionName': 'R', 'SubRegionName': 'S', '#c03439af': 0, 'Cache': []})


# CRpgStats_V2_LoadSaveEntry::SaveLoadScreenshotData @6e32de dc
def test_header_screenshot():
    from dv2lib import savegame
    data = (bytes(12) + struct.pack('<iIIIIQIIBBIII3fI', -1, 0, 3, 6, 1, 0, 0, 1, 1, 0,
                                   0, 0, 0, 1.0, 2.0, 3.0, 0)
            + bytes.fromhex('0001 02000000 0000c843 00009643 02000000 aabb'))
    data = savegame.pack(data + bytes(4), bytes(4))
    h, _ = savegame.read_header(data)
    assert h.screenshot == 'qrs='
    assert (h.screenshot_width, h.screenshot_height) == (400.0, 300.0)
    assert savegame.header_bytes(h)[12:-4] == data[12:len(data) - h.zlib_length - 4]


# CGameLogic_Projectile_Manager::GameSaveLoad @7d3658 dc, CGameLogic_Projectile::GameSaveLoad @8f01f0 dc
def test_projectiles():
    rec = {'#af0cbf8c': 7, '#39e43414': 1.0, '#26582c7b': 2.0, '#ac86195d': 3.0,
           'MagicalDamage': 4.0, 'RangedDamage': 5.0, '#270a759c': 6.0, '#43863bc9': True,
           '#f0652c21': 8, '#1a05cf2b': 9, 'ExplodeAtEnd': False, 'ExplosionRadius': 10.0,
           '#9ffddc22': True, '#bbc38556': 11.0, '#0129e873': 12, '#499aff9e': 13,
           '#d5948edd': 14, '#d21427b3': 'A', '#d83d70b0': 'B', '#90c39729': 'C',
           '#5d40f5b9': 15.0, '#5d40f5ba': 16.0, '#5d40f5bb': 17.0,
           '#9899f169': 18, 'TargetHandle': 19, '#4a0d2199': 20,
           '#1c1c3de7': 'D', '#a48f2897': 'E',
           'Statuses': [{'Status': 21, '#54b9b24a': 22.0, '#dc0dadd3': True, 'Chance': 23}],
           '#00000000': [[24.0, 25.0, 26.0, 27.0, 28.0, 29.0, 30.0, 31.0, 32.0, 33.0,
                          34.0, 35.0, 36.0], [37.0, 38.0, 39.0], [40.0, 41.0, 42.0],
                         [43.0, 44.0, 45.0]],
           'Avoid': [{'#d6a08675': 46, '#e32ab55f': 47}], 'EnchantmentUUID': 'F'}
    data = (struct.pack('<II6fBiiBfBfiii', 2, 7, 1, 2, 3, 4, 5, 6, 1, 8, 9, 0, 10, 1, 11, 12, 13, 14)
            + bytes.fromhex('01000000 41 01000000 42 01000000 43')
            + struct.pack('<3fiii', 15, 16, 17, 18, 19, 20)
            + bytes.fromhex('01000000 44 01000000 45')
            + struct.pack('<IifBi22fIii', 1, 21, 22, 1, 23, *range(24, 46), 1, 46, 47)
            + bytes.fromhex('01000000 46 ffffffff'))
    section(savestate.projectiles, data, {'Projectiles': [rec, {'#af0cbf8c': -1}]})


# CRpgStats_V2_GameEventManager::GameSaveLoad @7b6336 dc
def test_game_events():
    section(savestate.game_events,
            bytes.fromhex('01000000 78563412 04000000 01000000 feffffff 02000000 0000c03f'
                          '03000000 01000000 41 04000000 ffffffff'),
            {'Events': [{'#00000000': 0x12345678,
                         'Arguments': [{'#00000000': [1, -2]}, {'#00000000': [2, 1.5]},
                                       {'#00000000': [3, 'A']}, {'#00000000': [4, 0xffffffff]}]}]})


# CRpgStats_V2_Platform_NecromancersAlcove::GameSaveLoad @9cb027 dc, CRpgStats_V2_LoadSaveEntry::SaveLoadBattleTower @6e303a dc
def test_battle_tower_limbs():
    section(savestate.battle_tower,
            bytes(8) + struct.pack('<3fBiiiBiii4II5i', 1, 2, 3, 1, 4, 5, 6, 0, 7, 8, 9,
                                   10, 11, 12, 13, 1, 14, 15, 16, 17, 18)
            + bytes.fromhex('01000000 41') + struct.pack('<IiIiIi', 1, 19, 1, 20, 1, 21)
            + struct.pack('<iIiiiiI', 22, 0, 23, 24, 25, 26, 0),
            {'LastRegion': '', 'LastSubRegion': '', 'LastPosition': [1.0, 2.0, 3.0],
             'LastFlyingState': True, 'unnamed_7bd62a': 4, 'unnamed_7bd65b': 5, 'ActivePlatform': 6,
             'NecromancersAlcove': {'DefaultLimbsCreated': False, 'UpgradeLevel': 7,
              'SummonedCreatureHandle': 8, 'SummonedCreatureBonusType': 9, 'SelectedHead': 10,
              'SelectedBody': 11, 'SelectedArms': 12, 'SelectedLegs': 13,
              'Heads': [{'#5dcf8ade': 14, '#782aa2c2': 15, '#782aa2c3': 16, '#110a105a': 17,
                         '#110a105b': 18, '#1206f7a8': 'A'}],
              'Bodies': [19], 'Arms': [20], 'Legs': [21]},
             'Platform_9cf9d0': {'UpgradeLevel': 22, 'Formulas': []},
             'TrainingArena': {'UpgradeLevel': 23},
             'Platform_9ce4c0': {'UpgradeLevelWeapons': 24, 'UpgradeLevelArmor': 25,
                                 'UpgradeLevelJewelry': 26, 'Formulas': []}})


# COsirisManager::GameSaveLoad @736f10 dc
def test_story_span_without_objects():
    from dv2lib import savegame
    stream = b'SaveLoadStory' + bytes.fromhex('01 00040000 03000000 03000000 414243')
    assert savegame.story_span(stream, False) == (18, 29, b'ABC')


# CRpgstats_V2_Status::GameSaveLoad @9173c0 dc, CRpgstats_V2_Status_Manager::MakeNewStatus @912710 dc
@pytest.mark.parametrize('kind', [1, 2, 3, 4, 5, 16, 17, 19, 20, 27, 28, 29, 30, 31, 32,
                                 33, 34, 35, 36, 37, 38, 40, 42, 43, 57, 58, 59, 60, 61, 62, 63, 64])
def test_status_base(kind):
    section(savestate.statuses,
            struct.pack('<Iii f B iii ff B ii', 2, kind, 7, 1.5, 1, 8, 9, 10, 2.5, 3.5, 0, 11, 12)
            + bytes(4),
            {'Statuses': [{'Type': kind, '#ba3a1e19': 7, 'Duration': 1.5, '#00000000': [True, 11],
                           '#ebad33f8': 8, 'Status': 9, 'StatusType': 10, '#dd390402': 2.5,
                           '#a61e7437': 3.5, '#f8097c2e': False, '#9899f169': 12}, 0]})


def status_case(kind, suffix, extra, version=(3, 6)):
    rec = {'Type': kind, '#ba3a1e19': 7, 'Duration': 1.5, '#00000000': [True, 11],
           '#ebad33f8': 8, 'Status': 9, 'StatusType': 10, '#dd390402': 2.5,
           '#a61e7437': 3.5, '#f8097c2e': False, '#9899f169': 12, **extra}
    section(savestate.statuses,
            struct.pack('<Iii f B iii ff B ii', 1, kind, 7, 1.5, 1, 8, 9, 10, 2.5, 3.5, 0, 11, 12)
            + suffix, {'Statuses': [rec]}, version)


# CRpgstats_V2_Status_Poisoned::GameSaveLoad @a5e230 dc
def test_status_poisoned():
    status_case(7, struct.pack('<ii3f', 13, 14, 4.5, 5.5, 6.5),
                {'#7c790bbc': 13, '#b44274e5': 14, '#4d70bb44': 4.5,
                 'DamagePerTick': 5.5, '#e9793934': 6.5})


# CRpgstats_V2_Status_Charmed::GameSaveLoad @a6ac90 dc
@pytest.mark.parametrize('version', [(1, 31), (1, 32)])
def test_status_charmed(version):
    tail = struct.pack('<i', 13)
    extra = {'#a8584f04': 13}
    if version >= (1, 32):
        tail += struct.pack('<ii', -2, -3)
        extra['#00000000'] = [True, 11, -2, -3]
    status_case(6, tail, extra, version)


# CRpgstats_V2_Status_Shielded::GameSaveLoad @983120 dc
@pytest.mark.parametrize('version', [(1, 11), (1, 12)])
def test_status_shielded(version):
    tail = b'' if version < (1, 12) else struct.pack('<ff', 4.5, 5.5)
    status_case(15, tail, {'#00000000': [True, 11, 4.5, 5.5]} if tail else {}, version)


# CRpgStats_V2_Status_DragonSpirit::GameSaveLoad @9834e0 dc, CRpgstats_V2_Status_Healing::GameSaveLoad @a66170 dc, CRpgstats_V2_Status_WizardTowered::GameSaveLoad @a57710 dc
@pytest.mark.parametrize('kind', [8, 18, 39])
def test_status_healing(kind):
    status_case(kind, struct.pack('<f', 4.5), {'#65589fd1': 4.5})


# CRpgstats_V2_Status_Bleeding::GameSaveLoad @999550 dc
def test_status_bleeding():
    status_case(21, struct.pack('<f', 4.5), {'#1003ee13': 4.5})


# CRpgstats_V2_Status_Drinking::GameSaveLoad @a68d30 dc, CRpgstats_V2_Status_Rejuvinating::GameSaveLoad @a688d0 dc
@pytest.mark.parametrize('kind', [12, 13])
def test_status_drinking(kind):
    status_case(kind, struct.pack('<ff', 4.5, 5.5), {'#102b7b8f': 4.5, '#83cd79ea': 5.5})


# CRpgstats_V2_Status_Eating::GameSaveLoad @a68490 dc
def test_status_eating():
    status_case(14, struct.pack('<ff', 4.5, 5.5), {'#395fb991': 4.5, '#d828652c': 5.5})


# CRpgstats_V2_Status_HideInShadows::GameSaveLoad @a65940 dc
def test_status_hide_in_shadows():
    status_case(9, struct.pack('<ff', 4.5, 5.5), {'#27706fb1': 4.5, '#fb58eb3f': 5.5})


# CRpgstats_V2_Status_Polymorphed::GameSaveLoad @99ade0 dc
def test_status_polymorphed():
    status_case(10, bytes.fromhex('0d000000 01000000 41 0e000000'),
                {'#0035dbf7': 13, '#caae2696': 'A', '#d4553f3a': 14})


# CRpgstats_V2_Status_DragonPolymorphed::GameSaveLoad @99a7b0 dc
def test_status_dragon_polymorphed():
    status_case(11, struct.pack('<ii', 13, 14), {'#0035dbf7': 13, '#d4553f3a': 14})


# CRpgstats_V2_Status_EffectAffected::GameSaveLoad @997eb0 dc
def test_status_effect_affected():
    status_case(65, bytes.fromhex('00009040 01000000 41 01000000 42 01000000 43'),
                {'#e2a3abf2': 4.5, '#99957593': 'A', '#76a44e71': 'B', '#7fc374ea': 'C'})


# CRpgstats_V2_Status::SaveLoadModifierList @9174e0 dc, CRpgStats_V2_Modifier::GameSaveLoad @985cf0 dc
@pytest.mark.parametrize('kind', [22, 23, 24, 25, 26, 41, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56])
def test_status_modifiers(kind):
    status_case(kind, bytes.fromhex('01000000 01000000 41 00009040 01 0d000000'),
                {'StatModifiers': [{'Type': 'A', 'Value': 4.5, 'Percentile': True, 'ConditionOfSet': 13}]})


# CRpgStats_V2_Character_AIController_Osiris::CreateExecutor @98cb50 dc
@pytest.mark.parametrize('kind,tail,expected', [
    (1, '0d000000 01000000 41', {'TargetHandle': 13, 'DialogName': 'A'}),
    (2, '01000000 41 01000000 42', {'AnimationName': 'A', 'TextEvent': 'B'}),
    (3, '0d000000 01000000 41', {'TargetHandle': 13, 'TextEvent': 'A'}),
    (4, '0d000000 01000000 41 01', {'TriggerHandle': 13, 'TextEvent': 'A', 'IsRunning': True}),
    (5, '0d000000 00009040 0000b040 0000d040', {'#00000000': [13, 4.5, 5.5, 6.5]}),
    (6, '', {}), (7, '0d000000', {'DesiredCombatMode': 13}),
    (8, '0d000000 01000000 41', {'TargetHandle': 13, 'TextEvent': 'A'}),
    (9, '0d000000 0e000000 01000000 41 01',
     {'TargetHandle': 13, 'TriggerHandle': 14, 'TextEvent': 'A', 'IsRunning': True})])
def test_osiris_ai(kind, tail, expected):
    section(savestate.osiris_ai, b'\x01' + struct.pack('<i', kind) + bytes.fromhex(tail),
            {'HaveState': True, 'State': {'Type': kind, **expected}})


# RpgStats_V2_OsirisControllerExecutor::KeepFollowing::GameSaveLoad @98be1a dc
def test_osiris_ai_before_1_40():
    section(savestate.osiris_ai, bytes.fromhex('01 05000000 0d000000'),
            {'HaveState': True, 'State': {'Type': 5, '#00000000': [13]}}, (1, 39))


# CRpgStats_V2_TrapScript::CreateEmptyTrapFrame @98dfc0 dc, CRpgStats_V2_TrapFrame::GameSaveLoad @a7b820 dc
@pytest.mark.parametrize('kind,tail,extra', [
    (1, '0d000000', {'#c443d3ed': 13}), (2, '0d000000', {'#c443d3ed': 13}),
    (3, '0d000000', {'#c443d3ed': 13}), (4, '0d000000', {'#c443d3ed': 13}),
    (5, '0d000000', {'#dcd41b30': 13}), (6, '0d000000', {'#dcd41b30': 13}),
    (7, '01000000 41', {'#6c135870': 'A'}), (8, '01000000 41', {'#6c135870': 'A'}),
    (9, '00009040 0000b040 0000d040 0000f040 0d000000',
     {'#d87c758f': [4.5, 5.5, 6.5], '#59d1749c': 7.5, '#48e07f9e': 13}),
    (10, '0d000000 0e000000 01 0f000000',
     {'#dcd41b30': 13, '#0629104e': 14, '#62be3a24': True, '#00000000': 15}),
    (11, '01000000 41 01000000 42', {'#28cc4e58': 'A', '#07ccbb7b': 'B'}),
    (12, '01000000 41 00009040 0000b040', {'#28cc4e58': 'A', '#045f63de': 4.5, '#6c43616c': 5.5}),
    (13, '0d000000 0e000000 0f000000', {'#dcd41b30': 13, '#f40a67c1': 14, '#00000000': 15}),
    (14, '01000000 41 0d000000', {'#d1b43340': 'A', '#63715e08': 13}),
    (15, '0d000000 00009040 0000b040', {'#a6ee6d82': 13, '#a5b230af': 4.5, '#96d5d511': 5.5})])
def test_trap_commands(kind, tail, extra):
    section(savestate.trap_commands,
            struct.pack('<IiBf', 2, kind, 1, 1.5) + bytes.fromhex(tail) + bytes(4),
            {'Commands': [{'Type': kind, '#0c933c43': True, '#1c4b202e': 1.5, **extra}, {'Type': 0}]})


# CRpgStats_V2_TrapFrame_ChangeTrapState::GameSaveLoad @a7abbb dc, CRpgStats_V2_TrapFrame_ExecuteFrameOnTrap::GameSaveLoad @a7a03b dc
@pytest.mark.parametrize('kind,tail,extra', [
    (10, '0d000000 0e000000 01', {'#dcd41b30': 13, '#0629104e': 14, '#62be3a24': True}),
    (13, '0d000000 0e000000', {'#dcd41b30': 13, '#f40a67c1': 14})])
def test_trap_commands_before_1_24(kind, tail, extra):
    section(savestate.trap_commands, struct.pack('<IiBf', 1, kind, 1, 1.5) + bytes.fromhex(tail),
            {'Commands': [{'Type': kind, '#0c933c43': True, '#1c4b202e': 1.5, **extra}]}, (1, 23))


# CRpgStats_V2_EffectArea::GameSaveLoad @a78d20 dc, CRpgStats_V2_EffectArea_FireArea::GameSaveLoad @9ef9e0 dc, CRpgStats_V2_EffectArea_PoisonArea::GameSaveLoad @9f0240 dc
@pytest.mark.parametrize('kind', [2, 3])
def test_effect_area(kind):
    section(savestate.effect_areas, struct.pack('<IifBfffBi', 2, kind, 1.5, 1, 2.5, 3.5, 4.5, 0, 0),
            {'EffectAreas': [{'Type': kind, '#dd390402': 1.5, '#f8097c2e': True,
                              'TickInterval': 2.5, 'DamagePerTick': 3.5, 'ExposureTime': 4.5,
                              '#002854e2': False}, {'Type': 0}]})


# CRpgStats_V2_EffectArea_Firewall::GameSaveLoad @9edea0 dc
def test_effect_area_firewall():
    section(savestate.effect_areas, struct.pack('<IifBfffB15f', 1, 1, 1.5, 1, 2.5, 3.5, 4.5, 0,
                                               *range(5, 20)),
            {'EffectAreas': [{'Type': 1, '#dd390402': 1.5, '#f8097c2e': True,
                             'TickInterval': 2.5, 'DamagePerTick': 3.5, 'ExposureTime': 4.5,
                             '#002854e2': False, '#00000000': [[5.0, 6.0, 7.0],
                              [8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0]],
                             '#613d1424': 17.0, '#5f2e977f': 18.0, '#576803e9': 19.0}]})


# CRpgStats_V2_LoadSaveEntry::SaveLoadPreMisc @6e28c1 dc
def test_developers_cut_protection():
    section(savestate.READERS['SaveLoadPreMisc - Developers Cut Protection'],
            bytes.fromhex('02000000'), {'#00000000': 2})


# CRpgStats_V2_InventoryManager::GameSaveLoad @8a77b0 dc
def test_inventory_empty_slot():
    section(savestate.inventories,
            bytes.fromhex('01000000 ffffffff 01000000 41'),
            {'Inventories': [{'Handle': -1, 'PrototypeUUID': 'A'}]})


# CLuaVariableManager::GameSaveLoad @8f5e60 decomp
@pytest.mark.parametrize('data,offset', [
    (bytes(32) + struct.pack('<iiii', 1, 0x7fffffff, 0, 0), 48),
    (bytes(80) + b'\x01' + struct.pack('<ii', 0x7fffffff, 0), 89)])
def test_lua_counts_exceed_remaining_bytes(data, offset):
    v = savestate.Visitor(data, False, (3, 6))
    with pytest.raises(savestate.StateError, match=f'offset {offset}'):
        savestate.lua_variables(v, savestate.ABSENT)


# COsirisManager::GameSaveLoad @736f10 dc
def test_story_block_exceeds_remaining_bytes():
    v = savestate.Visitor(bytes.fromhex('01 00040000 00040000 ffffff7f'), False, (3, 6))
    with pytest.raises(savestate.StateError, match='offset 13'):
        savestate.story(v, savestate.ABSENT)
