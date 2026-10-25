# M3 handoff: headless hardware runtime complete

Use this as the authoritative continuation plan for M4.

## Restore point

```text
restore/recomp-m3
8ec0c1e80b5cea3df8f9581d1424fae319ec67d6
```

## M3 guarantees

- the game ROM is embedded from source, not loaded from an external .gbc file;
- fixed Bank 0 and ROMX Bank 2 execute as ahead-of-time native translations;
- MBC5, SRAM, WRAM, VRAM, OAM DMA, HRAM and IO mapping exist;
- DIV/TIMA/TMA/TAC advance from native instruction machine cycles;
- IE/IF interrupt entry and IME behavior are wired into Runtime;
- joypad matrix/IRQ exists behind a host-independent button mask;
- VBlank/STAT timing advances with the same hardware clock;
- HALT wakeup and the HALT-bug trigger are represented.

## Instructions for M4

M4 is visual infrastructure only. Do not skip ahead to the title-screen proof.

1. Add a software CGB renderer with a fixed 160x144 RGBA framebuffer.
2. Render BG and window from VRAM tile data/tile maps with SCX/SCY/WX/WY.
3. Implement CGB tile attributes: palette, VRAM bank, X/Y flip and BG priority.
4. Render OAM sprites, including 8x8/8x16 mode, transparency, priority and CGB OBJ palettes.
5. Convert CGB BGR555 palette RAM to host RGBA deterministically.
6. Add a deterministic framebuffer hash and BMP writer for regression artifacts.
7. Add a synthetic renderer self-test that exercises banked tiles, flips, window,
   sprite transparency and palette conversion without relying on game boot.
8. Add a minimal Win32 presentation layer. CI must remain headless by default.
9. Add `--window-test` or equivalent for a manual native-window smoke test.
10. Keep all gameplay execution AOT. The renderer may read hardware state but
    must not decode/interpret LR35902 instructions.
11. Only mark M4 complete after Windows CI builds and the renderer regression passes.
12. Create `restore/recomp-m4`, `M4_RESULT.md`, and `M4_NEXT.md`.

## M5 preparation, but not M4 work

After M4 is green, use missing-bank instrumentation to extend native ROMX
translation only for banks actually reached by the CGB startup/title path.
Start with the known state-5/title handler in Bank 7 and follow runtime evidence.
Do not claim M5 from a synthetic or reconstructed title image. M5 requires the
framebuffer to be produced by original DWM2 code writing VRAM/OAM/palettes.
