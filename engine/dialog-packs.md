# Dialog animation packs

A dialog names two animation packs after its `name` attribute, not its file: `<name>.dialog`, the body clips (`m_psDialogAnimationPackName`), and `<name><language>.dialog`, the lip-sync clips on layer 1 (`m_psDialogLipsynchAnimationPackName`) — CGameDialogIO_V20::ReadXML @ad9760 decomp

`RequestAnimations` loads the body pack and `RequestLipsynchAnimations` the lip-sync pack, both from `Dialogs\` — CGameDialog::RequestAnimations @9bfd10, CGameDialog::RequestLipsynchAnimations @9bfd70, MdlMan::CDataManager::RequestLoadDialog @c8ba50 decomp

The default language is named by `CGameLogic::GetDialogLanguageRegionName`; other languages take `CGameLogic_TranslationSystem::GetLanguageName` — CGameLogic::GetDialogLanguageRegionName @75d190, CGameLogic_TranslationSystem::GetLanguageName @7df560 decomp
