# M8 original support-party and training checkpoints (2026-10-24)

The user requested continuation through the whole game. This records additional
verified preparation, not completion of Sea World or the ending. M1-M7 fixtures,
ROM bytes, the native game runtime and restore branches are unchanged.

The retained development EXE is still source 697647033b4ce6b00dd8e11759cb85e1ae469a65,
725318144 bytes, SHA256 4a12bd3197b414c888f50c606ccf3cb2ede030543f8058df83e0fcd67359e95d.
The input is the Windows-validated living-dancer Journal from the previous chain,
SHA256 5632ab2d6c200ca3c93f768d8d56843f2a9c32fe4f437f9572b4ea843a86e333.

| Original controller route | Frames | Levels (records 0,1,4) | HP | Owned | Journal SHA256 |
|---|---:|---|---|---:|---|
| m8_farm_support_p1.txt | 40825 | 6,8,5 | 60,44,54 | 8 | c92dda4a93ca169af62704e17b33bb9aef3f75f1dc5779ed3e70a67dacf92249 |
| m8_gate_training_p1.txt | 395984 | 10,12,12 | 97,60,69 | 9 | eea6fd3aa19fc34f3bef52ea38af5e1e8fc7f19c0e0bb28e8460fc4d44225a03 |

The first route includes ordinary encounters, recruitment/naming, an original
battle defeat and Warubou's recovery, then Tara's Drop off/Pick up menus. It
stores Ellan safely and retrieves Phes (CurseLamp) alongside Slash and Spotslime.
The defeat is preserved in the transcript; it is not described as a victory.
All seven previously owned monsters remain, with a new ArmyAnt on the farm.

The second route uses ordinary Sea World encounters near the Magic Door and
original GreatLog-key travel to restore the party. It also uses an original Herb,
sells one surplus LoveWater for 40 G through the shop UI, and recruits an Antbear
sent to the farm. No CPU, WRAM, SRAM, party, skill or quest state is supplied by
host-side code. The final original Journal is in GreatLog's cave, world 5,
region 1,0, position 80,64; all three active members are alive at maximum HP.
The old dancer remains owned on the farm for the later quest.

Both finite routes regenerate their exact original Journals and pass fresh
Runtime Continue on the pinned Windows EXE under Wine. The new validator checks
all original native acceptance markers, exact input/output hashes and frames,
all owned statuses, the seven prior species, levels and living HP, 32 persistent
bytes per owned monster (256/288 bytes), 56 quest bytes and the wallet. The
additional wallet witness checks original C617..C619 before and after Continue;
40 G from the actual shop transaction survives. Original name-cache padding is
allowed to refresh, while species, skills and persistent stats must match.
The compact fixtures preserve the expanded P1 stream exactly; redundant
read-only observations alone are omitted. Explicit LF checkout attributes
preserve the byte hashes on Windows.

Compatibility evidence: evidence/2026-10-24/party-preparation-wine.json and the
two unmodified native logs. Both native exits are zero.

Native Windows run 40098604498 at commit 574865ee94d022acbc878d91432480545f84cb8f
also PASSED, including all unchanged Sea World/dancer routes and both new routes.
The downloaded artifact Journals were independently hashed again and match Wine.
Report: evidence/2026-10-24/party-preparation-windows.json. Artifact 12562252552,
130174 bytes; archive SHA256
bee975476c8093c87cdf80007ddb887cfd56c7855f6ac20d80654a25a07e23a5.
PR ROM verification run 40098607722 passed both build paths.
The existing pinned Windows workflow includes this chain after the previous
Sea World/dancer routes and uploads its small evidence artifact. It reuses the
validated EXE rather than recompiling identical game code.

Run test_m8_party_preparation.py with --exe, --seed, --support-route,
--training-route and a new --output directory. Linux additionally requires
an explicit --wine launcher and is labelled Wine on Linux in the report.

Continue from a copy of training/native/checkpoint.sav. HoodSquid, later quests,
remaining worlds, ending/credits, the final combined checks and packaged-player
validation remain outstanding. Exploration after this checkpoint is not yet
acceptance evidence. Do not create M8_RESULT.md or restore/recomp-m8 yet.
