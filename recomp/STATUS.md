# Native recomp status

The full-ROM Cobi/CGB player has passed the recorded main campaign, seven
postgame checkpoints and final native Windows package gates. The [current result
and playing guide](handoff/FULL_ROM_RESULT_2026-10-29.md) identifies the exact
game source, separate validation tooling, downloadable player and evidence.
These checks do not establish every optional path or random world. The
[implementation inventory](handoff/FULL_ROM_IMPLEMENTATION_2026-10-26.md) retains
the earlier failed tests and the reference migration.

The M0–M8 milestone snapshots remain available as immutable
`restore/recomp-mN` branches; see [exact commits](RESTORE_POINTS.md).

| Milestone | Goal | Status |
| --- | --- | --- |
| M0 | Native EXE pipeline | Complete |
| M1 | Complete LR35902 decoder/frontend | Complete |
| M2 | Fixed bank 0 statically translated | Complete |
| M3 | Memory map, MBC5, interrupts, timers and joypad | Complete |
| M4 | PPU/OAM renderer and native window | Complete |
| M5 | Original title screen through recompiled code | Complete |
| M6 | Live input, original movement and SRAM persistence | Complete |
| M7 | Genuine battles, audio, original Save/Continue | Complete; original regressions retained in M8 |
| M8 | Complete native Windows main campaign and verified package | Accepted |

## Historical accepted M8 evidence — 2026-10-25

Original controller input completes Oasis, Sea, Ice, Sky and Limbo, defeats
Darck, recovers the MagicPlug, plays the complete credits and reaches THE END.
Original ending Save and fresh Continue preserve all 17 owned monsters and all
107 quest bytes. Fixed bank 0 and all 255 switchable banks are statically
compiled, with no runtime opcode-interpreter fallback.

- All 38 later-story Windows checkpoints pass: 4,446,466 frames in 36m02s with
  four workers. Independent audit verifies all 38 actual parent links and all
  115 archived original Journals.
- All 18 original native tests execute and pass with zero failures/skips.
  Real WinMM playback and streaming pass on the signed virtual CI endpoint.
- The final package passes 21 checks through actual Play.cmd, followed by
  original ending Journal, two normal shutdowns and fresh-process reload.
- Windows and POSIX persistence/fault suites pass. The final player EXE is
  byte-identical to the independently built, tested production executable.

Game/build source: `3d573873ae8122cbb10fcd5d0f7ae7a33a7609ba`.
Accepted validation tools: `8859ef67289ce90712a44b9c17174de4519a59b3`.
Immutable M8 snapshot: `e44b41394c23f63f55b6d5255bc065696ba554c2`.
Successful final validation: [40183484388](https://github.com/rjtvandenhout/DWM2t/actions/runs/40183484388).

[Completion record and hashes](milestones/M8_RESULT.md),
[progress and screenshots](handoff/M8_PROGRESS_2026-10-25.md), and
[playing/recovery instructions](handoff/M8_NEXT.md) contain the full handoff.
Older failed/skipped attempts remain preserved and explicitly unaccepted.
Physical speaker audibility and optional postgame paths are not exhaustively
verified by CI.

## Historical supplemental postgame checks

The accepted executable passes seven further native Windows original-P1
checkpoints (270,152 frames in 2m07s with four isolated processes): key appraisal, QuietSea generation and world boss,
cache/re-entry, a three-floor dungeon, two postgame egg gifts, two NPC breeds and direct Journal
Continue inside a random world. Full owned, quest, key, seed and cache comparisons
are recorded in the [postgame report with screenshots](handoff/POSTGAME_PROGRESS_2026-10-25.md).
Finite source checks cover all 10 terrains, 100 key levels, 48 recipes and 833
map assets. Collection-gated reward playthroughs remain pending, and the runtime
had no serial-peer transport at that accepted baseline. The new source adds a
local two-player cable; its original transaction coverage is reported separately
in the new implementation inventory. These historical supplemental checks leave
the verified player and M0–M8 snapshots unchanged.

## Maintenance boundary

Immutable M0–M8 snapshots and the original ROM remain unchanged. The later
reference migration is limited to 375 measured PCM boundaries, one raster
screenshot, 45 manifest route hashes and seven wrapper hashes; the original
controller inputs and other state assertions remain guarded. Routine CI checks
tooling and filesystem contracts; a newly built executable still requires the
full manual campaign/package gates before it can be labeled verified.
Build-only outputs remain `UNTESTED_CANDIDATE`.

M7's immutable restore remains `3bb1e18170fc928f372f9cc72cc433d85c0666ca`.
Its original values and accepted battle mode remain documented in
[M7_RESULT.md](milestones/M7_RESULT.md). Historical discovery and earlier
milestone handoffs remain as evidence, rather than current branch instructions.
