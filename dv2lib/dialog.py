from __future__ import annotations

# CGameLogic::GetDialogLanguageRegionName @75d190, CGameLogic_TranslationSystem::GetLanguageName decomp
LANGUAGES = {"English": "English(US)", "French": "French(France)",
             "Spanish": "Spanish(Spain)", "Portuguese": "English(US)"}


# CGameDialogIO_V20::ReadXML @ad9760, RequestAnimations @9bfd10, RequestLipsynchAnimations @9bfd70 decomp
def packs(episode: str, name: str, language: str = "English") -> tuple[str, str]:
    folder = f"Win32\\Characters\\{episode}\\Dialogs\\"
    return f"{folder}{name}.dialog", f"{folder}{name}{LANGUAGES.get(language, language)}.dialog"
