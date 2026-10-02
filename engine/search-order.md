# Search order

The first archive that holds a path serves it, per path and not per archive: `Patch.dv2` overrides region files — CSoundBankManager::Init @86d860 decomp

`CSoundBankManager::Init` mounts one more archive, `Soundbanks.dv2`, before it loads `Init.bnk`; the executable spells it `"Win32"` + `"\\Packed\\Soundbanks.dv2"`, so the grep above misses it. It is searched after the 31 — CSoundBankManager::Init @86d860 decomp

## Measured

31 distinct `Win32\Packed\*.dv2` names in the executable, the order it names them being the search order — `grep -a -o 'Win32\\Packed\\[ -~]*\.dv2' ~/.local/share/Steam/steamapps/common/divinity2_dev_cut/bin/Divinity2-debug.exe | sort -u | wc -l`

533 archives consulted — `python3 -c "from dv2lib import corpus,locate;print(len(corpus.archives(locate.packed_of(locate.find_game()))))"` from `~/divinity2-lib`

35079 winning paths — `python3 -c "from dv2lib import corpus,locate;print(len(corpus.index(locate.packed_of(locate.find_game()))))"`

1824 paths held by more than one archive — `python3 -c "from dv2lib import corpus,locate,archive;from collections import Counter;p=locate.packed_of(locate.find_game());c=Counter(e.path.lower() for f in corpus.archives(p) for e in archive.Archive(f));print(sum(v>1 for v in c.values()))"`
