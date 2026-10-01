r"""The animation packs a dialog loads.

`CGameDialogIO_V20::ReadXML` @ad9760 names two packs after the dialog's `name`
attribute, not its file: `<name>.dialog`, the body clips
(`m_psDialogAnimationPackName`), and `<name><language>.dialog`, the lip-sync
clips on layer 1 (`m_psDialogLipsynchAnimationPackName`). `RequestAnimations`
@9bfd10 and `RequestLipsynchAnimations` @9bfd70 load them from `Dialogs\`
(`MdlMan::CDataManager::RequestLoadDialog` @c8ba50).

The archives keep them per episode, `Win32\Characters\<episode>\Dialogs\`
(`Episode_*/Dialogs.dv2`, 183 of the 1,943 in `Patch.dv2`); how the engine
maps `Dialogs\` to the episode was not found, so the dialog's own episode is
used. 5 of the 43 packs both episodes ship differ.
"""
from __future__ import annotations

#: `CGameLogic::GetDialogLanguageRegionName` @75d190; other languages take
#: `CGameLogic_TranslationSystem::GetLanguageName`.
LANGUAGES = {"English": "English(US)", "French": "French(France)",
             "Spanish": "Spanish(Spain)", "Portuguese": "English(US)"}


def packs(episode: str, name: str, language: str = "English") -> tuple[str, str]:
    """The body pack and the lip-sync pack of dialog `name`, as the archives spell their paths."""
    folder = f"Win32\\Characters\\{episode}\\Dialogs\\"
    return f"{folder}{name}.dialog", f"{folder}{name}{LANGUAGES.get(language, language)}.dialog"
