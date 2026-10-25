# M4 handoff: native visual runtime complete

## Restore point

```text
restore/recomp-m4
29c4c8249f5a77a17ea8194d624d20af52da3e6b
```

## M4 guarantees

- a deterministic 160x144 CGB framebuffer exists;
- BG and window tilemaps, tile-bank attributes, flips and palettes render;
- OAM sprites render with transparency and BG/OBJ priority;
- framebuffer output can be hashed and written as a BMP;
- a minimal native Win32 presenter exists;
- CI remains headless and validates the renderer.

## Instructions for M5

M5 must prove an **original DWM2 title frame produced by original game code**.
A hand-rebuilt title image does not count.

1. Generalize the ROMX generator/dispatcher to a selectable set of AOT banks.
2. Start from the real CGB cartridge entry point at `$0100`.
3. Run with no external ROM file. Use the embedded matching 4 MiB source image.
4. Whenever Runtime reports `MissingBank`, add that bank to the AOT bank set
   only if the missing bank is on the actual boot/title path.
5. The known initial game state is `$C5DB = 5`; its foreground handler enters
   Bank 7 at `$486E`, and its VBlank handler enters Bank 7 at `$4F7B`.
6. Preserve hardware timing. Do not bypass title code by directly copying title
   graphics into VRAM from host C++.
7. Add missing IO behavior only when runtime evidence shows the original code
   needs it.
8. Capture rendered framebuffers at VBlank boundaries.
9. Detect a stable title-state framebuffer from game execution, write it to BMP,
   and record its deterministic hash.
10. Fail on trap, missing translated bank, or failure to reach the title state.
11. Make the Windows executable able to show the real reached framebuffer.
12. Mark M5 complete only after green Windows CI produces both the executable and
    title-screen BMP from the game-code boot path.
13. Create `restore/recomp-m5`, `M5_RESULT.md`, and `M5_NEXT.md`.

M5 completed these requirements at restore point `restore/recomp-m5`.
