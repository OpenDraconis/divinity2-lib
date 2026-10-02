# Names behind hashes

A hash a loader asks for may be carried by no shipped file: `ClassicFogColor`, `fClassicFogDepth`, `fPPBrightness` (CAtmosphere::LoadXML), `fPPContrast`, `fPPHue`, `fPPSaturation` (CSky::LoadXML), `fCloudBrightness`, `fCloudDensity`, `ShadowColor` (CCloudDome::LoadXML), `CloudColor` (CCloudColorSetting::GetName), `fSplitWeight` (CCascadedShadowMap::SaveXML) — CAtmosphere::LoadXML @6d1620, CSky::LoadXML @727880, CCloudDome::LoadXML @724020, CCloudColorSetting::GetName @4642b0, CCascadedShadowMap::SaveXML @71c4c0 decomp

Numbered names are built by their loader: `AlternateSpawnPoint<i>` (`CRpgStats_V2_Trigger_VisualEffectPoint::LoadXML` @9fd510), `VisualEffectUUID<i>` (`CRpgStats_V2_Trigger_StartVisualEffectArea::LoadXML` @9fdfd0, `StopVisualEffectArea::LoadXML` @9fdb60) — CRpgStats_V2_Trigger_VisualEffectPoint::LoadXML @9fd510, CRpgStats_V2_Trigger_StartVisualEffectArea::LoadXML @9fdfd0 decomp

Cue tags are `"Cue" + language` (`CueSpanish`, `CueItalian`) — CBaseNode::GetLanguageCueTag @a22460 decomp

The dialog loader compares `Shot` (CGameDialogIO_V20::ReadXML @ad9760), `xsi:type` (CNodeV20::ProcessAnimationData @a271c0, ProcessCameraData @a25f20), `im` and `fsm` (CNodeV20::ProcessCameraData @a25f20); the two track elements `AnimationTracks` and `AnimationTrack` are walked by position — CGameDialogIO_V20::ReadXML @ad9760, CNodeV20::ProcessAnimationData @a271c0, CNodeV20::ProcessCameraData @a25f20 decomp

`watersettings.xml` names the fields of `CWaterRenderer`: `m_fWaveSize`, `m_fShininess`, `m_vWaterColor`, `m_fWaveSpeed`, `m_bRenderDebug`, `m_fFogModifier`, `m_fWaveStrength`, `m_fTexScale`, `m_fAlphaModifier`, `m_bDoUpdate`, `m_fSunStrength` — CWaterRenderer::Load @6c9530 decomp

A name needs the engine function that asks for it where the hash has several names; `Km` and `Kr` are read by CSky::LoadXML, `sky` by CAtmosphere::LoadXML, `Sun` by CLightManager::LoadXML, `sub` by CTerrainPatchDataManager::LoadXML, `XP` by CRpgStats_V2_CharacterState::LoadXML, `gamelogic_init` by CGameLogic_Init::LoadXML — CSky::LoadXML @727880, CAtmosphere::LoadXML @6d1620, CLightManager::LoadXML @6b73b0, CTerrainPatchDataManager::LoadXML @735c30, CRpgStats_V2_CharacterState::LoadXML @99b4e0, CGameLogic_Init::LoadXML @7e5860 decomp

`gamecontrolsettings.xml` is read by `GameControlSettings::LoadXML`: `GamePadSensitivityHumanPitch`, `GamePadSensitivityHumanYaw`, `HumanMinPitch`, `InvertY`, `InvertFlyY` — GameControlSettings::LoadXML @98e300 decomp

## Measured

1169 names in the table — `python3 -c "from dv2lib import names;print(len(names.NAMES))"` from `~/divinity2-lib`

49 hashes in the shipped documents have no name — `python3 -c "import json;print(len(json.load(open('$HOME/dv2-extract/unpack.json'))['unknown_hashes']))"`

All 1169 table names equal their key under `h = h*33 + c` (32-bit, latin-1 bytes, case-sensitive); the command prints True — `python3 -c "from dv2lib import larian_hash,names;print(all(larian_hash.name_hash(n)==h for h,n in names.NAMES.items()))"` from `~/divinity2-lib`
