# M8 validated branch integration - 2026-10-23

This merge consolidates verified test/fixture/document additions onto
`work/recomp-m8`. It is not full M8 acceptance and does not move any restore.

## Exact inputs

- Active baseline: 697647033b4ce6b00dd8e11759cb85e1ae469a65.
- Production/save validation: bfc591146659964740f6958add5f8e8b8ed14d5f.
- Sea World/village validation: 8fc6e64cca83fd63a99f8b3544e3992c304d25cd.
- M7 restore: 3bb1e18170fc928f372f9cc72cc433d85c0666ca (unchanged).

Both side branches descend from the active baseline. Their file sets do not
overlap: one adds native save and production startup contracts/workflow; the
other adds original Sea World fixtures, pinned validators and its workflow.
The merge includes both parent histories and the exact verified file blobs.
Only this integration record and the current status summary are additionally
updated. Game runtime, ROM bank bytes, CPU timing, APU implementation, original
acceptance fixtures and constants are unchanged by this integration.

## Executed evidence

Hosted run 39836316030 successfully built source 6976470 with all 255 ROMX
banks and ran the retained development suite. The exact development EXE is
725318144 bytes, SHA256
4a12bd3197b414c888f50c606ccf3cb2ede030543f8058df83e0fcd67359e95d.
Audio-device availability/skips must be read from the original test report;
this does not certify subjective audio output on a hosted runner.

Run 39840204359 passed the real Windows save-protection and production-startup
workflow at bfc5911. It uses a separately built production entry point. Do not
confuse that executable with the diagnostic player used for story replay.

Run 39876912500 passed both pinned original Sea World routes at 8fc6e64 on
Windows, using the exact development EXE above. The new 8299-frame village
route preserves the active party, farms the new recruit, heals all members,
writes the original Journal and verifies a fresh Runtime loading SRAM only.
Village save: acf128eeeb75c5cb130c58bf692f39eb20c2129306bcb647bde784e7a14a770a.
Artifact 12467988802 (village evidence) has archive SHA256
94b120db9787380aa99d3ad577cb6ad21be6375c1789e6f2cafcf9ca5ce3099f.
The initial Sea World route remains unchanged and is regenerated first.

## Execution boundary

This integration is marked [skip ci] to avoid rebuilding the identical game
runtime merely to combine already-executed independent test additions. The
three runs above retain their original commits and binary identities; no
fresh combined run is implied. The existing workflows remain available for
explicit reruns and future source changes. Do not relabel previous logs as
results of an unexecuted integration commit.

New discovery continues from a copy of the village Journal. The original
village dance requirement has been inspected in matching ROM code: active
monster skill 0x76..0x7D or 0x92 is required (18:7E0F, called by 4:5AA5).
An existing farm creature has a qualifying skill; use original farm menus,
not host-written party/skill/quest state. New discovery is not accepted until
its own original Journal, finite replay and fresh Continue have been checked.

Remaining M8 scope: complete Sea World and later original worlds/systems,
ending/credits, later saves, final combined regression and packaged-player
validation. No M8_RESULT.md, restore/recomp-m8 or final-release claim is made.
