# Postgame and random Magic Key checks

The accepted M8 player and `restore/recomp-m8` remain unchanged. These checks
use the accepted complete-AOT diagnostic from source `3d573873ae81`, executable
SHA256 `f93b7f96212559f65f05e09f8443a224bbda7d124047047fbf53510e16ae0321`.
The initial input is a copy of the genuine ending Journal `0649c4ef…`. Every
game action is original P1. Observational RAM/SRAM captures are never input
seeds, and no game state, RNG, party, flags or generated worlds are edited.

## Actual play and persistence

Six original Journal checkpoints are pinned in
[`m8_postgame_supplemental.json`](../tests/m8_postgame_supplemental.json),
totalling 228,921 recorded P1 frames. All six pass on native Windows in
[run 40202234497](https://github.com/rjtvandenhout/DWM2t/actions/runs/40202234497),
including all six actual parent/input links, exact original Save hashes and
fresh Continue. Independent Wine checks also pass. The native run uses tooling
source `0bbb41e68d00` and the unchanged accepted game executable; it does not
rebuild or replace the player. Its complete evidence artifact is only 416,187
bytes ([receipt](evidence/2026-10-25-postgame/native-windows-6-stage-artifact.json)).

| Check | Observed result |
| --- | --- |
| Unappraised key | Original Use refuses it; Key Shop charges the correct 90G. |
| QuietSea first use | Original level-8 key, stored seed `16C0`, terrain class 8, recipe 13, 4×4 surface. |
| Generated interiors | Castle, shop, three dungeon floors, stairs and final reward load through original movement. |
| QuietSea world boss | Pumpoise and two allies defeated; party survives at 219/179/207 HP. Original world completion, all four area flags and key clear marker are set. |
| Cache and fresh re-entry | Same key loads the exact saved 404-byte descriptor; seed and cleared state persist. The cleared boss is absent on an actual revisit. |
| Dungeon treasures | Original TinyMedal and SteelFang obtained; chest states persist. |
| In-world Journal | Original PLAN Save inside the castle; fresh Continue restores random context `[0,0,131,0]` and original field mode `1:5`. |
| Newlywed gift | Original WhipBird egg, 18 owned; shared claim flag `CD` set. |
| Evaluator gift | Original introduction and certified Lionex egg, 19 owned; flags `28/29` set. |
| Granddaughter duel | Original post-ending battle reached; the attempt loses. No victory is claimed. |
| Arena B and collection gates | Actual fee/refusal and original King, Kameha, old-man and Warubou gates inspected. B/A/S victories are not claimed. |

The random-world and character-event routes are independent original Save
branches. Their data is never merged. The six-stage replay audits every actual
new parent Journal used for a child checkpoint.

Every checked Journal compares all 107 quest bytes, all 128 key-record bytes,
64 seed bytes, every owned 165-byte monster record, and all 20 cache slots in
both working and backup SRAM before/after fresh Continue. Original egg owner
names canonicalize four padding bytes per new egg from `00` to `F0`; each exact
transition is pinned and source-backed, with every other byte still compared.
The in-world checkpoint additionally compares context `CC42..CC45` and the
complete 404-byte descriptor against the saved cache.

![Original QuietSea appraisal](evidence/2026-10-25-postgame/screenshots/key-appraised.png)

![Original generated QuietSea surface](evidence/2026-10-25-postgame/screenshots/quietsea-surface.png)

![Original random-world boss](evidence/2026-10-25-postgame/screenshots/quietsea-world-boss.png)

![Original world-clear message](evidence/2026-10-25-postgame/screenshots/quietsea-cleared.png)

![Original newlywed egg gift](evidence/2026-10-25-postgame/screenshots/newlywed-thanks.png)

![Original certified egg gift](evidence/2026-10-25-postgame/screenshots/certified-egg-confirmation.png)

## Finite generator/source audit

The source audit checks every legal terrain class and key level, all 48 recipes
(264 structure records), 64 surface templates, 180 selectable dungeon layouts,
83 populated interior screens and 833 distinct compressed assets. It verifies
visual/CGB attribute pointers, layout/stair bounds, the shared floor buffer,
key/cache record bounds and the original 65,536-state LCG period. All checked
source predicates pass. All 833 asset outputs agree between independent readers
after the map-decoder repair.

This is finite source coverage, not an end-to-end playthrough of all seeds.
Individual rejection predicates have finite bounds; termination of the outer
variable-length generator retry loop for every seed is not proved. Cache-full,
first/middle/last key deletion, a second genuinely obtained random key, every
terrain class in play, and every random boss/reward combination remain dynamic
coverage gaps.

Reproduce the finite checks with:

```sh
python3 recomp/tools/inspect_magic_keys.py --check
python3 recomp/tools/inspect_items.py --check
python3 recomp/tools/test_inspect_map.py
python3 recomp/tools/audit_magic_worlds.py --output /tmp/new-magic-world-audit.json
```

Providing `--diagnostic PATH` also checks the actual accepted executable,
identity and source manifest. The complete native/ROM source comparison is
unchanged; there is no game-binary patch in this work.

## Findings repaired

The previous suffix CSV used a 56-byte row stride. The original selector uses
60 bytes: 56 names plus four padding bytes. This corrupted 487 stored suffix
thresholds. The reproducible reader now exports the original thresholds, all
names, and exact selector bins for all 2,000 accepted-roll cases. Threshold
differences are kept distinct from inclusive `>=` selector counts.

The Python map reader failed to wrap dictionary references across 4 KB and did
not apply the original eight-bit extended-length counter. These observation
errors affected 173 of the 833 random-world assets. The repaired reader matches
all captured tiles, with original-asset and boundary regression checks. Neither
finding required changing the accepted C++ runtime.

The item CSV used 15-byte records instead of the original 13, omitted empty
runtime record 0 when assigning names, and read beyond the 99-record table.
It is replaced by a lossless original export with neutral byte fields and
separately verified resale lookups. For example, original SteelFang runtime
ID 69 has resale base 500G and the inspected merchant offers 75%, or 375G.
This does not fund Arena B's 500G fee from the current 11G wallet.

## Remaining postgame scope

The [source inventory](POSTGAME_CONTENT_AUDIT_2026-10-25.md) covers the fixed postgame keys, character rewards, Arena
tiers, King bounties, breeding offers and catalogue gates. The ending Save has
22 acquired catalogue species; the character branch reaches 24. Later rewards
require 50, 100, 120, 140, 150, 160, 250 or 290 species and suitable real parents.
Those gates and their source paths are checked; their reward playthroughs are
not complete.

Counterpart keys and link-only content require an original exchange. The current
runtime has generic storage for serial registers but no implemented peer/serial
transfer transport. Full linked postgame completion therefore remains a runtime
feature gap; a serial interrupt vector alone does not provide that feature.

Raw comparisons, source citations and screenshot provenance are retained in
[`evidence/2026-10-25-postgame`](evidence/2026-10-25-postgame/). The original
main-story acceptance and existing M0–M8 restore commits retain their earlier
scope and hashes.
