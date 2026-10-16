# M6 handoff: live input, real map movement and SRAM persistence

## Restore point

```text
restore/recomp-m6
```

## M6 guarantees

- M4 renderer and M5 original-title regressions remain permanent and green;
- execution still begins at the real cartridge path from `$0100`;
- no external ROM file or host-injected title/map framebuffer is required;
- title/menu/new-game progression is driven through Game Boy P1 input semantics;
- the accepted M6 path reaches the real opening ship map through original code;
- Right input through P1 visibly moves the player on that map;
- accepted movement hashes are
  `0xd926fc62969f3bb4 -> 0xea72400372e2d1c5`;
- accepted M6 AOT ROMX set is
  `1,2,4,7,15,16,18,19,20,22,23,31,40,52,53,95,96,105,127,132,133,135`;
- missing native code still fails explicitly; there is no generic runtime
  interpreter fallback;
- 32 KiB MBC5 SRAM load/save, dirty tracking, autosave and exit flush exist;
- deterministic save/reload persistence is covered by CI;
- `--play [save-path]` provides the live Win32 game loop;
- Arrow keys/Z/X/Enter/Backspace map to D-pad/A/B/Start/Select;
- Win32 keyboard messages are verified to reach the P1 state in Windows CI;
- HALT is treated as a normal wait-for-interrupt state in the live loop.

## Instructions for M7

M7 is the **battle + audio + real in-game save/continue** milestone. Do not
broaden it into full-game completion; that belongs to M8.

1. Keep every M4, M5 and M6 regression unchanged as permanent tests.
2. Continue normal play from the original M6 path. Do not synthesize battle,
   map, party or save state from host code.
3. Whenever execution reports `MissingBank`, add only the required ROMX bank
   to the AOT set and document why it was reached. Do not add a runtime opcode
   interpreter fallback.
4. If more executable code is copied into HRAM/WRAM, signature-check each
   accepted fragment and provide an explicit native translation.
5. Extend scripted P1 input from the opening map through original story/gameplay
   until a real battle is entered.
6. Add a deterministic battle regression that:
   - reaches a genuine battle from original game execution;
   - captures the battle framebuffer;
   - selects at least one legal command through P1;
   - observes original battle code advance at least one turn/action;
   - records deterministic game-owned state/framebuffer evidence before/after.
7. Implement the Game Boy Color APU registers and timing needed by DWM2:
   square 1, square 2, wave, noise, frame sequencer, length/envelope/sweep and
   NR50/NR51/NR52 routing.
8. Feed APU output to a native host audio backend for `--play`. Keep emulated
   APU timing independent of host audio buffering.
9. Add deterministic CI audio evidence without depending on a physical audio
   device, for example a bounded PCM/hash regression that proves original game
   writes produce non-silent, stable audio samples.
10. Keep the M6 SRAM persistence layer. Add an **original in-game save** test:
    navigate to a legitimate save point/action, let original game code write
    SRAM, restart a fresh runtime with that `.sav`, choose Continue through
    P1, and verify restored game-owned state.
11. Do not treat the synthetic M6 SRAM fixture alone as M7 save acceptance.
12. Keep the live Win32 loop responsive while audio, input, PPU and CPU timing
    run together.
13. Mark M7 complete only when Windows CI passes all retained M4-M6 tests plus
    battle progression, deterministic audio and real in-game save/continue.
14. Create `restore/recomp-m7`, `M7_RESULT.md`, and `M7_NEXT.md`.

## M7 acceptance rule

M7 is not complete because a battle-looking framebuffer or an audio buffer
exists. A real battle must advance through original game logic, original game
audio writes must produce timed host/CI audio output, and a save created by
original game code must survive a fresh-runtime Continue path.
