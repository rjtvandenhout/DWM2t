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
