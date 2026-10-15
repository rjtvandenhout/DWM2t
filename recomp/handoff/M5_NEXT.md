# M5 handoff: original DWM2 title screen reached natively

## Restore point

```text
restore/recomp-m5
9d0b9830ea6542def717a8cde726691cd0421cc2
```

## M5 guarantees

- CGB execution starts from the cartridge entry path at `$0100`;
- no external ROM file is required;
- the exact 4 MiB matching game image is generated from checked-in source banks;
- Bank 0 and title-path ROMX banks execute through ahead-of-time native translations;
- current title-path ROMX set is `1, 2, 7, 127`;
- the fixed DWM2 HRAM DMA fragment at `$FF80-$FF89` has an explicit AOT translation;
- original splash/credits/logo/title code runs under hardware timing;
- the CGB renderer consumes VRAM/OAM/palette state produced by the original game;
- the stable original title framebuffer hash is `0x49c67a53ef4f8a80`;
- CI reaches that title at frame 1921 after 30 stable matching frames;
- CI fails on missing translated code, CPU trap, STOP, or title timeout;
- `--title-window` can show the reached title screen in the native Win32 presenter.

## Instructions for M6

M6 is the **live input + title/menu transition + overworld + save-RAM** milestone.
Do not skip directly to battle/audio work.

1. Keep the M5 title regression unchanged as a permanent boot-path test.
2. Upgrade the Win32 presenter from a static-frame viewer to a live frame loop.
3. Map keyboard/controller host input to the existing joypad abstraction. At
   minimum support D-pad, A, B, Start and Select.
4. Drive host input only through the Game Boy P1/joypad path. Do not advance
   title/menu state by directly editing WRAM variables.
5. Add a deterministic scripted-input harness for CI. Use it to press Start/A
   through the real title/menu flow.
6. Whenever the real execution path reports `MissingBank`, add that ROMX bank
   to the AOT bank set and document why it is reached. Never introduce a generic
   runtime opcode interpreter as a fallback.
7. Generalize fixed copied-code handling if DWM2 copies additional executable
   fragments into WRAM/HRAM. Every accepted copied fragment must be signature
   checked and translated explicitly.
8. Implement cartridge SRAM persistence behind the MBC5 RAM mapping. The
   interactive Windows build should load/save a `.sav` file; CI should use a
   deterministic temporary/in-memory save fixture.
9. Follow the original new-game or continue path into an actual overworld map.
   Do not synthesize an overworld state from host code.
10. Keep rendering at VBlank boundaries and keep hardware cycle accounting live
    while waiting for host input.
11. Add a scripted overworld regression that:
    - reaches a real map from boot;
    - records the player/map position;
    - sends a legal directional input through the joypad path;
    - observes the original game update position and animation state;
    - captures a framebuffer before/after movement.
12. Verify save-RAM writes survive an explicit save/reload test through the
    persistence layer.
13. Make the normal native window loop interactive enough to navigate the title
    and move in the reached overworld.
14. Do not add audio yet. Audio and battle completion belong to M7.
15. Mark M6 complete only after Windows CI passes the M5 boot regression, menu
    progression, overworld movement and save persistence regressions.
16. Create `restore/recomp-m6`, `M6_RESULT.md`, and `M6_NEXT.md`.

## M6 acceptance rule

M6 is not complete merely because a framebuffer resembling an overworld map is
visible. The player must reach and move in that map through original game code
and Game Boy input semantics.
