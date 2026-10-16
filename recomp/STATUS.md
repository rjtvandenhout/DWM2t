# Native recomp status

| Milestone | Goal | Status |
|---|---|---|
| M0 | Native EXE pipeline + statically translated helpers | ✅ complete |
| M1 | Complete LR35902 decoder/frontend | ✅ complete |
| M2 | Bank 0 fully statically translated to native C++ | ✅ complete |
| M3 | Memory map, MBC5, interrupts, timers and joypad | ✅ complete |
| M4 | PPU/OAM compatibility renderer and native window | ✅ complete |
| M5 | Original title screen through recompiled code | ✅ complete |
| M6 | Live input + real map movement + save RAM | ✅ complete |
| M7 | Battles + audio + original save/continue | ⏳ next |
| M8 | Fully playable native release | ⏳ |

Restore branches live under `restore/recomp-mN`.
Continuation notes live under `recomp/handoff/`.

Repository-history and CI-baseline notes live in
`recomp/HISTORY_AUDIT.md`. Historical restore snapshots remain immutable; the
files on `recomp/native-pc` are the current source of truth.

## M5 retained acceptance evidence

The permanent M5 regression still reaches the original title at:

```text
frame=1921
hash=0x49c67a53ef4f8a80
stable_frames=30
C5DB=5
C5DC=0
```

## M6 acceptance evidence

Implementation CI run `38842905661` passed at
`1cca3634ef0093f51c3bbf2d7c3e578eed5ab268`.

The final milestone-record CI run `38843223801` also passed at
`70628e9a6f210f494ace326c51d1ac295a36c023`.

Verified:

- original boot/title/menu/new-game execution reaches the real opening ship map;
- all scripted input is delivered through Game Boy P1 semantics;
- Right input visibly moves the player on the ship;
- movement framebuffer hashes change
  `0xd926fc62969f3bb4 -> 0xea72400372e2d1c5`;
- 69 bytes of game-owned WRAM change during the accepted movement sample;
- exact 32 KiB MBC5 SRAM survives save/reload/update/reload;
- `--play` provides a live Win32 frame loop with keyboard input;
- the Windows smoke test creates the real window, maps key down/up into P1,
  advances native frames and renders successfully;
- HALT is handled as normal wait-for-interrupt behavior in the live loop;
- missing AOT code remains explicit and no generic LR35902 runtime interpreter
  is used.

Accepted AOT ROMX set:

```text
1, 2, 4, 7, 15, 16, 18, 19, 20, 22, 23, 31, 40, 52, 53,
95, 96, 105, 127, 132, 133, 135
```

Restore point: `restore/recomp-m6`.

M7 instructions: `recomp/handoff/M6_NEXT.md`.
