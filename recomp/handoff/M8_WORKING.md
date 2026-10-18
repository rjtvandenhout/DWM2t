# M8 working record (not an acceptance/completion record)

Approved scope: finish the original game through ending/credits, retain every
M1-M7 regression, verify later original Saves and fresh Continue, and package
the final native Windows release. Only repository/original game output may
inform implementation. No fabricated game state or runtime interpreter.

## Baseline

- Branch: `work/recomp-m8`, starting at clean M7 `bc79ec91342031451103145e4fd830d9b7fe00dd`.
- Immutable M7 restore stays at `3bb1e18170fc928f372f9cc72cc433d85c0666ca`.
- M7 was revalidated immediately before M8: all twelve tests passed in 139.29 s.
- Accepted input/save fixtures and all exact M7 constants remain unchanged.
- No `restore/recomp-m8`, `M8_RESULT.md`, or final-release claim until full acceptance.

## Work sequence

User-approved continuation rule: after completing a world or proving that an
important boss fight fully works, summarize the evidence and ask whether to
continue immediately or stop for now. Wait for the user's explicit decision
before progressing beyond that milestone. Smaller tooling/build checkpoints
do not require a pause. Keep all further project-authored text in English.

1. Extend finite P1-only route support for complete battles and later Continue
   without assuming the introductory quest flags are still unchanged.
2. Extend original play through Oasis and subsequent worlds/systems, retaining
   checkpoints created by original Journal Save and replayable P1 transcripts.
3. Add only reached or directly required native banks/fragments; verify every
   runtime fix against retained exact regressions.
4. Prove the original ending/credits and late-game fresh Continue. Run all
   retained and new gates together; package and create final restore only then.

## Chronological discovery record

### English-language prerequisite (2026-10-18)

Project-authored Dutch text in the active M7 PowerShell validator and the
packaging launcher was translated. Validator changes are string-only and
PowerShell parsing passes. English README/report translations were added to
the previous output packages; original reports/logs remain historical evidence.
The separate `outputs/M7-English` package contains the accepted byte-identical
M7 game/save and a rebuilt English launcher. No original game text was changed.

### P1-only M8 tooling

`--m8-probe <save|-> <output>` starts a new runtime and original Continue.
It accepts appended commands from `<output>/commands.txt`. `--m8-resume
<save|-> <trace> <output>` reconstructs a session by replaying its recorded
controller inputs from a new runtime, not by loading CPU/WRAM savestates.
`--m8-replay <save|-> <trace> <output>` is the finite verification path.
New output directories are required to avoid overwriting traces/evidence.

Commands: button/hold/release, `walk DIRECTION frames [release]`, `battle`,
`flee` (still experimental), `talk [budget] [period]`, `journal UNIQUE_NAME`,
`snapshot`, `quit`. Only P1 changes game state; snapshots/assertions are read-only.
Journal requires original save acceptance, nonzero SRAM changes, field return,
then a fresh-runtime Continue comparison before reporting a checkpoint pass.
Movement stops when the original field leaves idle mode. Recruitment naming
requires explicit input rather than unlimited default confirmations.

`inspect_map.py` reads/decompresses the original map tables at bank-0
$19B7/$0CF5 and bank-17 $44B8. The observed Oasis region 1,0 graphics matched
all 360 runtime tile bytes exactly. This is read-only data inspection, not a
runtime CPU interpreter. No external game information was used.

`recomp/build/m8_oasis01` resumes original M7 Save through Continue. Its P1
transcript reaches Oasis and completes a real CactiBall encounter, returning
to world 0x20, region 1,0, position 0x10,0x50 at frame 10352. Subsequent travel
has reached region 0,1, position 0x50,0x40. This is route discovery, not M8
acceptance. Diagnostic mark/back are not valid acceptance fixtures.

Full M8 original-game playthrough and ending/credits remain unproven.

Subsequent pure-P1 discovery in `m8_oasis02` through `m8_oasis05` completed
another battle, recruited an original monster through the naming/Yes menus,
and reached the town at world 33, region 0,0, position 80,128, party size 2.
The full controller-only trace replayed from the original M7 SRAM with state
assertions. Outdoor Journal correctly says "You can't save here" and was
rejected. Town Journal changed 174 SRAM bytes, but the first helper attempt
ended in field-menu mode 1:2, not idle 1:0, and was therefore NOT accepted.
Menu-close retry support is being validated; no later-save pass is claimed yet.

### Verified first later checkpoint

The retry in `recomp/build/m8_oasis06` succeeded through original Journal,
then a new Runtime loaded only the resulting 32768-byte file. All 304 party/
inventory bytes and ten quest/location fields matched (zero mismatches).
Party size 2 is part of that 304-byte comparison. Final source frame 29449,
world 33, region 0,0, position 80,128. SRAM FNV `0x79f780ede66cc6d1`;
save SHA256 `BCD5CD10221F95A1C032579B1B315F9F60A084D4137AF8D38DF3DB899C32AB0F`.
This early-Oasis save is genuine later progress, not late-game/ending proof.

The pure controller/assertion transcript is pinned as
`tests/m8_oasis_town_p1.txt`. The new `M8_oasis_checkpoint` test regenerates
that progress from the accepted M7 Journal save, checks the exact checkpoint,
then verifies fresh Continue. CTest sets up that seed through the unchanged
M7 save/Continue test. `M8_trace_contract` checks twelve fail-closed/protection
cases; all twelve tool-contract cases passed independently.

The M1-M7 suite passed again in 131.07 seconds with the M8 driver compiled.
Both existing acceptance save hashes were preserved. A subsequent expanded
14-check run is in progress. The `check-m7` target continues to select exactly
the retained twelve tests; `check-m8-development` includes partial M8 checks
and does not certify full M8 completion.

### Inn code expansion

Original P1 conversation with the world-34 innkeeper reached missing native
41:$4001 (`m8_oasis06`, frame 29954, selector 0A), then 151:$4026 through
41:$4008 (`m8_inn01`, frame 2900 after fresh Continue). Both banks were added
to AOT because of those concrete failures, not guessed game coverage. Bank 41
compiled/linked; bank 151 is being compiled. No runtime fallback was added.
The failure traces contain an explicit non-replayable failure marker rather
than silently pretending the partial failed frame completed successfully.

Bank 151 compiled/linked and the inn welcome dialogue now executes. Continuing
that original dialogue reached 28:$4075 at frame 2993 (`m8_inn02`); this exact
native bank is being added next. Healing has not yet been proven.

The first expanded run passed every retained M1-M7 test and M8 tool contracts,
but failed the new Oasis test because the initial fixture capture itself had
been truncated. The fixture was regenerated with every one of the 29,449 P1
frames retained and redundant read-only assertions omitted. The corrected
finite native `--m8-oasis-test` then passed, reproducing exact original Journal
SRAM and fresh Continue. A combined all-green run is still required after the
new inn banks are linked. This failed run is not described as all-green.

### Inn proof and combined regression

Further P1 inn execution reached 240:$4001 at frame 2999 (`m8_inn03`).
Banks 28 and 240 were compiled and linked alongside 41 and 151. The inn then
completed in `m8_inn04`, frame 3580: original SRAM monster-record HP changed
18->25 (maximum 25), while the recruited monster stayed 16/16. No host writes
were used for healing. A subsequent original Journal inside the inn changed
38 SRAM bytes, produced an exact 32768-byte file, and passed a new-runtime
Continue comparison (304 party/inventory bytes, ten quest/location fields).

Inn checkpoint: frame 4924; world 34, region 0,0, position 80,80; party size 2.
SRAM FNV `0x520c04981e15a459`; save SHA256
`C42458D17E1B0EE448F771A44874DA0A906910DECA336DF0483D7786B0505697`.
Its full 4924-frame P1 trace is pinned as `tests/m8_inn_heal_p1.txt`. The new
`--m8-inn-test` requires the exact original town checkpoint, verifies healing,
replays the original Journal, and verifies fresh Continue. The Oasis CTest
driver now chains this inn proof after regenerating the town checkpoint.

Before adding this final inn-test chain, all 14 combined development checks
passed in 202.18 seconds (`m8-development-14-checks-03.log`). The updated chain
is being revalidated; that earlier green run is not passed off as a test of
unbuilt changes. The retained M7 acceptance saves still have their original
SHA256 values. There are now 49 registered native ROMX banks.

Original village dialogue identifies world 33 as Kalka. Observed NPC dialogue
mentions a thieving band and says it knows nothing about a navel plug. These
are original on-screen observations only; no external game guide was used.
The idle exploration session was cleanly quit. Resume actual progress from
`recomp/build/m8_inn04/oasis_after_inn.sav` using a NEW output directory:

```powershell
recomp/build/DWM2tRecomp.exe --m8-probe recomp/build/m8_inn04/oasis_after_inn.sav recomp/build/m8_next01
```

That is an original Save/fresh Continue, not a diagnostic savestate. Remaining
work still includes further Oasis progression, all later worlds/systems,
ending/credits, later-game saves, full acceptance and final release/restore.

## Current verified development checkpoint (2026-10-18)

All 14 combined tests, INCLUDING the final inn-healing/second-Journal/fresh-
Continue chain, passed in 260.97 seconds. Evidence:
`recomp/build/m8-development-14-checks-04.log` and
`recomp/build/Testing/Temporary/LastTest.log`. The regenerated inn save is
byte-identical to the observed original checkpoint (SHA256 C42458D1...05697).
Both existing M6/M7 acceptance saves retained their original hashes.

The packaged development EXE is Windows x64 (PE machine 8664), 233263104 bytes,
SHA256 `EDC52071A4A229AEB1E853594F7B374DFE1A5A9182204BE347C13BBB7DF56774`.
`outputs/M8-development` contains that exact binary, a separate original inn
test save, English instructions, and the local test report/evidence. The
package EXE additionally passed M3/M4 self-tests. It is NOT the final release.
The M7 English validator cleanup is commit `890f5f1`; M7 restore remains
`3bb1e18170fc928f372f9cc72cc433d85c0666ca`, also checked remotely.

Full M8 is still incomplete. No ending/credits proof, `M8_RESULT.md`, or
`restore/recomp-m8` exists. Do not describe these 14 partial development tests
as final M8 acceptance or as a successful hosted GitHub Actions run.

### Asiya/canal development evidence (ongoing)

The original king's request, the town well complaint (selector 0F), the report
to the king, the canal-manager scene in world 42 and walking into the canal
(world 43) all executed. New original Journal checkpoints passed fresh
Continue for 304 party bytes, 56 quest-flag bytes and five location fields:

- `m8_asiya05/asiya_king_request.sav`: FNV `3b7c45f1713eb77e`,
  SHA256 `2CA33149B19F9CF0B2CAFD8A139B7A1B75CFFCC33C63C5F6E0663F0B6A76224A`.
- `m8_asiya06/asiya_water_reported.sav`: FNV `e5873b72c24a1e6a`,
  SHA256 `C6FAE888C6100528C5408C67B259E28F2F1B550BF3FA66F227D07631748270EB`.
- `m8_asiya06/kalka_canal_preparation.sav`: FNV `3de20fbe8f08b6c3`,
  SHA256 `BFD205B39C77C7B21BDDD0DB310ED6BF36F8969D833E7514A17FF736A80F6E5F`.
  Original inn healing restored all three monsters to 33/33, 21/21, 17/17.

The dam creature is at world 43, region 1,2, position 48,96 (selector 37).
Original confrontation produces a real mode-4 battle with enemy HP 98.
Its Fight command reached 226:$5426, which directly calls 5:$772B; both
native banks were added. `m8_dam01` replayed all 28,353 entry-route frames
and proved enemy HP 98->85->76->68->56->52 and party damage. The underprepared
party lost and the original defeat return executed. This is NOT a passing
boss milestone. Subsequent retry/flee experiments do not claim victory.

All 14 combined local development tests passed in 188.21 seconds after banks
5/137/149/226 and the 56-byte quest check (`m8-development-dam-14-checks-01.log`).
Existing M6/M7 acceptance saves retained their exact hashes. This result
predates bank 30 and the later checkpoint/creature-stat test extensions.

`m8_training01` earns normal battle experience near the Kalka canal entrance,
returns to the inn before the weakest member dies, and uses original Journal
after each cycle. Three separate 32768-byte saves and fresh Continue passed:
`training_cycle_01.sav`, `_02.sav`, `_03.sav` (last FNV `e3ed777cd9f7c95d`).
Further combat raised Slash and the second monster to level 3 and produced
another original recruitment offer. The original send-to-farm > Info menu
reached 30:$7163 at frame 39569. Bank 30 was added; `m8_training02` replays
the complete 39,568-frame prefix before trying Info again. No farm exchange
has yet been confirmed. No world or important boss has passed yet, so the
user's milestone pause has not been triggered.

Three finite P1 fixtures now pin inn->Asiya, recruitment/castle/king Journal,
and water-report/canal-preparation Journal (7194/26188/15883 frames). The M8
CTest driver chains these after its retained Oasis and inn proofs using
`--m8-checkpoint-test`. Fresh Continue additionally checks each active
monster's persistent status/level/experience/HP/MP/stats (22 bytes per member).
The expanded 14-check run is in progress in
`m8-development-asiya-chain-14-checks-02.log`; do not claim it passed yet.

## Continuation from tested 0e2b236

The executable and original inn save hashes matched the tested baseline before
new work. `m8_next01` follows original village dialogue south through Oasis to
Asiya (world 36) and its inn (world 35). The original Journal there produced
32768 bytes; fresh Continue matched the checked party/quest/location fields.
Save: `recomp/build/m8_next01/asiya_arrival.sav`, SHA256
`E1366BBCCBB10F563B5F1E5779905A37D689B04605B7395257775742BB5903D1`.
This is another early-game checkpoint, not world completion.

Original NPC dispatch 4:$63ED requires three healthy party monsters before
the circus route can progress; the current party contains two. Original text
and map/NPC tables are being used to find that route, not an external guide.
An actual information-menu execution reached 149:$4650 (`m8_next01`, frame
8780), so that native bank is being added. No missing-bank failure is counted
as a pass, and no host-written party/quest state is used to bypass the gate.

### Three-monster party and castle entry

Bank 149 compiled and linked. From the Asiya Journal seed, `m8_asiya03`
records two real field encounters. The second produced an original recruitment
offer; A/name, Start/END, A and Yes completed it. Party count changed 2->3 at
frame 9672, without host-written party state. The returning party's original
Journal changed 127 SRAM bytes and produced `m8_asiya03/asiya_party_three.sav`
(32768 bytes, FNV `2b63a58fb2c71006`, SHA256
`A9B92496C5C73F94566FADA517BF89EF42DD002C3CAB523BA762DB4C49818A8E`).
Fresh Continue passed; a read-only comparison also found no differences in
the full 56-byte quest-flag block. M8 Continue verification now explicitly
checks those 56 bytes plus five location fields and 304 party bytes. M7's
acceptance implementation and fixtures are unchanged.

The original circus gate accepted the living three-monster party, transferred
it into castle world 37, and original walking reached the throne room (38).
Talking to the king reached missing native bank 137:$4001 at frame 22821.
That bank was compiled and linked. This is not boss/world completion.
The first replay-extraction attempt accidentally omitted B holds and correctly
failed its screen assertion. The corrected prefix retains all P1 buttons,
ends at frame 22621 before the failed story command, and is being replayed in
`m8_asiya05`. No failed trace is presented as a passing result.

## Latest stopping point: dam-boss victory (milestone decision required)

This section supersedes the earlier ongoing-work notes above. The king's
canal/dam creature has now been defeated through original P1 gameplay.
Training and the original recruitment/farm exchange produced a stronger
party. The existing level-6 CactiBall was sent to the original farm, not
deleted; the new recruit joined the active party. Bank 30's Info path passed.
`m8_training02` reconstructs all earlier training by P1 replay from the
preserved canal-preparation Journal save, not from CPU/WRAM snapshots.

Scripted battle: frame 52036, world 43, region 1,2, position 32,96,
selector 37, mode 4, party HP 30/24/24, boss HP 98. Normal Fight turns
reduced boss HP 98->78->50->33->13->0 by frame 55037. All three members
survived (9/16/24 HP). Original rewards/level-ups and post-fight dialogue
completed; CBE1 changed 00->18 (quest flags 0x53 and 0x54). No subsequent story
objective was started. Returning to Kalka included one normal field battle,
original inn healing and PLAN > Journal.

Victory save: `recomp/build/m8_training02/dam_boss_victory.sav`, exactly
32768 bytes, original Journal changed 52 bytes, FNV `51c23bf4c4399ebc`, SHA256
`400DF427C538F0776C1F9066813EC90005E20D78EB8FF2C11AACBC13D3DA29CE`.
Original route ends at frame 66305, Kalka inn (world 34, region 0,0, 80,80).
Fresh Runtime Continue passed with zero mismatches in 304 party bytes,
56 quest-flag bytes, five location fields and 66 persistent creature bytes.
The active party is healed; all older saves remain separate.

`tests/m8_dam_boss_victory_p1.txt` retains all 66,305 controller frames and
asserts battle-entry HP 98, boss HP zero with every member alive, and the
final flags/Journal/screen hashes. Independent `--m8-checkpoint-test` replay
passed in `recomp/build/m8_boss_regression01`, reproducing the byte-identical
victory save and another fresh Continue. This route is now chained after
the three Asiya/canal fixtures in the development CTest driver.

All 14 development gates including the three Asiya/canal fixtures and the
66-byte creature comparison passed in 279.90 seconds before adding the final
boss fixture (`m8-development-asiya-chain-14-checks-02.log`). The final retained
suite rerun passed all 14 checks in 292.99 seconds
(`m8-development-dam-victory-14-checks-03.log`). This run used the earlier
three-story-route test list: the initial terminal reconfiguration lacked the
Visual Studio environment, was corrected, and the independent new boss gate
passed. The final registered four-story-route M8 CTest chain passed separately:
both M8 tests passed in 287.94 seconds (`m8-complete-dam-chain-checks-04.log`).
It regenerates every seed from the accepted M7 Journal and retains 149,943
recorded P1 frames across all six M8 routes, plus separate fresh Continue
verification. The final victory save is byte-identical to discovery and
the independent boss replay. Do not describe
the 292.99-second run as already including the newly registered boss route.
No result here is a hosted GitHub Actions pass or full M8 acceptance.

A separate Windows-x64 development package is in
`outputs/M8-dam-boss-checkpoint`, with an independent M8-test.sav, untouched
evidence/original-journal.sav, English launcher/instructions and evidence.
EXE SHA256 `4AEBA6723D4C4D47D7AD4135C2B3CB5D7AAE54C1E62FB31A8D47529660CC172B`;
255736832 bytes; PE machine 8664. The packaged binary passed M3/M4 self-tests.
Do not replace the user's earlier output packages or saves.

STOP gameplay at this fully working important boss milestone and ask whether
to continue immediately or stop for now. Wait for the user's explicit answer.
Remaining scope: the rest of Oasis, later worlds, ending/credits, later saves,
all regressions/final release. Do not create restore/recomp-m8 or M8_RESULT.md
or describe M8 as complete. M7 restore stays 3bb1e18170fc928f372f9cc72cc433d85c0666ca.
