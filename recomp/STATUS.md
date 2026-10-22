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
| M8 | Fully playable native release | Candidate implementation prepared; final testing/ending proof deferred |

Active branch: `work/recomp-m8`. Historical recovery branches are immutable.
M7 restore remains `3bb1e18170fc928f372f9cc72cc433d85c0666ca`.
Do not create an accepted M8 result/restore before full-game validation.

## Current implementation pass (2026-10-22)

The user asked to finish implementation and leave testing for later.
The new `recomp/player` target supplies a production-only Windows entry point,
complete 255-bank AOT coverage, normal launch by default, Unicode save paths,
profiles, native save locking/backups and read-only failure diagnostics.
Original cartridge execution, CPU timing, renderer and APU logic are retained.

Host SRAM persistence now uses temporary-file write/flush/replacement instead
of truncating the current file first. A build-only candidate script/manual
workflow creates isolated source snapshots, complete native builds, manifests
and English packages without running the game or any tests. Packages are
explicitly UNTESTED and contain no user/acceptance saves.

**This pass has not built the new Windows player or run tests.** It does not
certify later worlds, every command, the ending or complete M8. Instructions:
`RELEASE_CANDIDATE.md`; deferred checks: `handoff/M8_TEST_LATER.md`.

## Retained historical acceptance

M6 implementation CI: `38842905661` at `1cca3634ef0093f51c3bbf2d7c3e578eed5ab268`.
M6 milestone CI: `38843223801` at `70628e9a6f210f494ace326c51d1ac295a36c023`.
M4 framebuffer hash: `0x284882dc2a98916f`.
M5: frame 1921, hash `0x49c67a53ef4f8a80`, 30 stable frames, mode 5:0.
M6 movement: `0xd926fc62969f3bb4 -> 0xea72400372e2d1c5`, 69 WRAM changes;
exact 32 KiB SRAM round trip and real Windows input/window checks passed.

M7's twelve local gates passed twice on 2026-10-18. Hosted CI was unavailable;
local Windows acceptance was explicitly authorized. A genuine battle is mode
4, not menu mode 2. Original P1 attack: enemy HP 9->6, Slash HP 25->20 in 282
frames; equal-time no-input control unchanged. Original Journal changed 317
SRAM bytes; fresh Continue restored 304 party/inventory bytes and eleven
quest/location fields. SRAM FNV: `0x81daa8e19c019ce4`. Timed original audio:
2,138,926 sample values, hash `0x03b50ed7ed79bda0`. Full record:
`milestones/M7_RESULT.md`. These old results are not new-source test results.

## Recorded M8 development progress

The full chronological record is `handoff/M8_WORKING.md`. Original Oasis,
dam/CurseLamp victories, recruitment/farm operations, Journal checkpoints,
feeding and host-audio corrections were recorded there. Kids Class was won
through its three original rounds and PirateKey was obtained. The 255-ROMX
build at that checkpoint passed all 18 local development checks; no hosted
CI/full-ending result was claimed. Later worlds/ending remain unproven.

Safe-resume tooling was subsequently committed, with its local mocked-process
checks and blocked hosted validation documented in
`handoff/M8_SAFE_RESUME_VALIDATION_2026-10-22.md`. The source implementation
pass above changes host/player/release code only; all existing gameplay
fixtures, exact acceptance constants and restore points remain untouched.
