# Wwise sound banks

A bank (`.bnk`, bank generator versions 44 and 48) is a row of chunks, each a four-byte tag and a 32-bit size: `BKHD` is the header, `DIDX` indexes the media that `DATA` holds, `HIRC` holds the objects (sounds, containers, actions, events), `STID` names banks; `STMG`, `FXPR`, `ENVS` occur only in `Init.bnk` — CAkBankMgr::ProcessBankHeader @dbb7b0, CAkBankMgr::LoadMediaIndex @dbbc30 decomp

`ProcessBankHeader` refuses any version other than 44 — CAkBankMgr::ProcessBankHeader @dbb7b0 decomp

From version 47 a source has no `AkAudioFormat`, and every effect ends with a list of bank data — CAkBankMgr::LoadSource @dbc790 decomp

`STMG`'s leading field is the volume threshold in dB below which a voice is under the below-threshold behaviour; `CAkBankMgr::ProcessGlobalSettingsChunk` reads it first and passes it to `AK::SoundEngine::SetVolumeThresholdInternal` at priority 2 (bank data); `SetVolumeThreshold` @d8c970 is never called outside that path — CAkBankMgr::ProcessGlobalSettingsChunk @dbebb0, AK::SoundEngine::SetVolumeThresholdInternal @d8b510 decomp

An event is found by the Wwise ID of its name: the name lower-cased then FNV-1 32 over the bytes, A-Z lower-cased and nothing else — AK::SoundEngine::GetIDFromString @d8cc00, FUN_00d8cba0 @d8cba0 decomp

Object readers: `CAkParameterNodeBase::SetNodeBaseParams` @e07ef0 and what it calls, `CAkParameterNode::SetPositioningParams` @e03010, `CAkParentNode<CAkParameterNode>::SetChildren` @dfa440, `CAkSound::SetInitialValues` @df9740, `CAkRanSeqCntr::SetInitialValues` @dfc230 (the byte after the mode is not read there), `CAkActorMixer::SetInitialValues` @dffba0, `CAkLayerCntr::SetInitialValues` @dff6f0, `CAkLayer::SetInitialValues` @e092c0, `CAkEvent::SetInitialValues` @df9170, `CAkActionExcept::SetExceptParams` @e209e0, `CAkAction::SetInitialValues` @df2b00 then the class's `SetActionParams`, `CAkAttenuation::SetInitialValues` @e00390 — CAkParameterNodeBase::SetNodeBaseParams @e07ef0, CAkEvent::SetInitialValues @df9170 decomp

`CAkParameterNodeBase::SetInitialRTPC` @e06d80 reads 20 bytes, then 12 per point; the RTPC ID is the u32 at +5; `CAkAttenuation::SetInitialValues` passes it with the parameter, curve and scaling after it — CAkParameterNodeBase::SetInitialRTPC @e06d80, CAkAttenuation::SetInitialValues @e00390 decomp

A Play action's file ID follows its sub-section, not inside it — CAkAction::SetInitialValues @df2b00 decomp

The Compressor and Peak Limiter params blocks are 22 bytes with plugin IDs `COMPRESSOR_FX` and `PEAK_LIMITER_FX` (the low 16 bits of `fx`): threshold, ratio, attack (compressor) or look-ahead (limiter), release, an output gain in dB (raised to linear by the engine, `10**(dB/20)`, at load), then `bProcessLFE` and `bChannelLink` — CAkCompressorFXParams::SetParamsBlock @d94ec0, CAkPeakLimiterFXParams::SetParamsBlock @d93f70 decomp

A bus has its own, shorter, older field order than `SetNodeBaseParams`; `duck` and `to_duck` are `CAkBus::AddDuck`'s five arguments per entry (bus, dB, fade-out ms, fade-in ms, curve) — CAkBus::SetInitialValues @df5b40, CAkBus::AddDuck @df5aa0, CAkBus::Duck @df5ea0, CAkBus::UpdateDuckedBus @df5fc0 decomp

## Measured

-96.3 dB is `Init.bnk`'s volume threshold — `python3 -c "from dv2lib import wwise;print(wwise.read(open('$HOME/dv2-extract/Sound/Soundbanks/Win32/2009_1/Init.bnk','rb').read()).volume_threshold_db)"` from `~/divinity2-lib`

741412071 is the Wwise ID of `aleroth_AD_heal2` — `python3 -c "from dv2lib import wwise;print(wwise.id_of('aleroth_AD_heal2'))"` from `~/divinity2-lib`

1411 banks of version 48 and 12 of version 44 — `cd ~/divinity2-lib && python3 -c "from dv2lib import corpus,locate;from collections import Counter;p=locate.packed_of(locate.find_game());print(Counter(int.from_bytes(corpus.read(e)[8:12],'little') for e in corpus.index(p,lambda k:k.endswith('.bnk')).values()))"`
