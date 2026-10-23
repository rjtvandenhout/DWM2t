# Native recomp status

| Milestone | Goal | Status |
|---|---|---|
| M0 | Native EXE pipeline | Complete |
| M1 | Complete LR35902 decoder/frontend | Complete |
| M2 | Fixed bank 0 statically translated | Complete |
| M3 | Memory map, MBC5, interrupts, timers and joypad | Complete |
| M4 | PPU/OAM renderer and native window | Complete |
| M5 | Original title screen through recompiled code | Complete |
| M6 | Live input, original movement and SRAM persistence | Complete |
| M7 | Genuine battles, audio, original Save/Continue | Accepted locally on Windows |
| M8 | Fully playable native release | In progress: complete native build and later Sea World checkpoints verified; ending unproven |

Active branch: `work/recomp-m8`. Historical recovery branches are immutable.
M7 restore remains `3bb1e18170fc928f372f9cc72cc433d85c0666ca`.
Do not create an accepted M8 result/restore before full-game validation.

## Current verified evidence (2026-10-23)

Testing resumed after the user's earlier implementation-only request.
Hosted runners now work; the old pre-run infrastructure failures are history.

- Run `39836316030`, source `697647033b4ce6b00dd8e11759cb85e1ae469a65`:
  complete 255-ROMX Windows development executable built; retained development
  suite and handoff completed successfully. Device-dependent audio skips are
  not physical-audio passes. Keep the actual native-results.xml report.
- Run `39840204359`, source `bfc591146659964740f6958add5f8e8b8ed14d5f`:
  actual Windows SRAM filesystem contracts, independent production-player
  build and real CLI/Unicode-profile/window/save-lock startup checks passed.
- Run `39846303155`: the exact tested development EXE passed original Sea
  World arrival, a field battle/recruitment, Journal and fresh Continue.
- Run `39876912500`, source `8fc6e64cca83fd63a99f8b3544e3992c304d25cd`:
  both that unchanged route and a new 8299-frame village/inn route passed on
  Windows. Enemy HP 19->0, farm recruitment, healing to 60/44/32 HP, exact
  Journal and fresh Continue are asserted. All 154 checked persistent bytes
  across seven occupied active/farm creature records survived loading.

The validated source branches are integrated without changing runtime code,
ROM banks, old acceptance constants or original controller fixtures. See
`handoff/M8_INTEGRATION_2026-10-23.md` for source/run boundaries and
`handoff/M8_SEA_WORLD_2026-10-23.md` for reproducible later checkpoints.
The latest Windows-verified village Journal is
`acf128eeeb75c5cb130c58bf692f39eb20c2129306bcb647bde784e7a14a770a`.

These results do not prove a Sea World boss, subsequent worlds or the ending.
No full M8 acceptance or final release is claimed. The integration itself is
source/test/document consolidation, not a new execution of the complete suite.

## M7 review and further M8 regression (2026-10-23)

The M7 headless gates were independently re-executed on the pinned Windows EXE
through Wine, all five returning zero with the accepted values. The retained
native-Windows report also confirms all twelve M1-M7 checks. New controller-only
routes retrieve Eggplaton through original farm menus and return to the Sea
World village with all three members alive, preserving seven owned records.
All three new Journal/fresh-Continue checkpoints pass the complete local Wine
chain and native Windows run `39890528113` at commit `67d991e`. See `handoff/M8_DANCER_2026-10-23.md` for exact hashes and limitations.
This does not complete the mermaid quest, Sea World, later worlds or the ending.

## Production implementation

`recomp/player` supplies a production-only Windows entry point, complete
255-bank AOT coverage, normal launch, Unicode save paths, profiles, save
locking/backups and read-only failure diagnostics. Original cartridge
execution, CPU timing, rendering and APU logic are retained.
Host SRAM uses temporary-file write/flush/replacement instead of truncating
an existing save. The build-only candidate script creates isolated snapshots,
complete builds, manifests and English packages. Candidate packages remain
marked UNTESTED because full-game acceptance is still open; their startup
validation above does not silently promote them to a finished release.

## Retained historical acceptance

M6 implementation CI: `38842905661` at `1cca3634ef0093f51c3bbf2d7c3e578eed5ab268`.
M6 milestone CI: `38843223801` at `70628e9a6f210f494ace326c51d1ac295a36c023`.
M4 framebuffer hash: `0x284882dc2a98916f`.
M5: frame 1921, hash `0x49c67a53ef4f8a80`, 30 stable frames, mode 5:0.
M6 movement: `0xd926fc62969f3bb4 -> 0xea72400372e2d1c5`, 69 WRAM changes;
exact 32 KiB SRAM round trip and real Windows input/window checks passed.

M7's twelve local gates passed twice on 2026-10-18 under explicitly authorized
local Windows validation. A genuine battle is mode 4, not menu mode 2.
Original attack: enemy HP 9->6, Slash HP 25->20 in 282 frames; equal-time
no-input control unchanged. Journal changed 317 SRAM bytes; fresh Continue
restored 304 party/inventory bytes and eleven quest/location fields.
SRAM FNV: `0x81daa8e19c019ce4`. Timed original audio: 2,138,926 sample values,
hash `0x03b50ed7ed79bda0`. Full record: `milestones/M7_RESULT.md`.

The historical M8 chronology is `handoff/M8_WORKING.md`: Oasis, dam/CurseLamp,
recruitment/farm, feeding/audio and Kids Class/PirateKey. Earlier local passes
and earlier blocked hosted attempts remain historical records, not statements
about the newest test run. Current verified progress is summarized above.
