from pathlib import Path

import pytest

from dv2lib import dialog

EPISODE = Path.home() / 'dv2-extract/Episodes/Episode_1_Extended'


# CGameDialogIO_V20::ReadXML @ad9760, CGameDialogIO_V20::ProcessFlag @ad94d0, CBaseNode::AddConnection @a22ce0 decomp
def test_debug_dialog():
    path = EPISODE / 'Dialogs/DebugDialog.xml'
    if not path.exists():
        pytest.skip(f'{path} missing: python -m dv2lib unpack')
    d = dialog.read(path.read_bytes())
    assert (d.name, d.automated, len(d.nodes), len(d.flags)) == ('DebugDialog', False, 131, 57)
    assert [g.cue for g in d.greetings] == ['Hello. Here you can choose to go to every quest in Broken Valley. Select a quest!']
    assert sorted(c.cue for c in d.greetings[0].connections) == ['Battletower Interfaces', 'Close Dialog', 'Debug', 'Teleports.']


# CGameDialog::IsGlobalEvent @9bfed0 decomp
def test_global_events():
    path = EPISODE / 'story/globalevents.xml'
    if not path.exists():
        pytest.skip(f'{path} missing: python -m dv2lib unpack')
    events = dialog.global_events(path.read_bytes())
    assert len(events) == 1369 and 'Gold_DZ_GotDrudenaeHint' in events
