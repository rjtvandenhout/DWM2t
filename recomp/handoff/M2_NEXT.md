# M2 handoff: Bank 0 fully statically translated

Use this note only after the M2 Windows workflow is green and
`restore/recomp-m2` has been created at that exact passing commit.

## M2 guarantees

- M1's complete LR35902 frontend remains intact.
- Every fixed ROM Bank 0 address `$0000-$3FFF` has a build-time C++ translation entry.
- Normal Bank 0 execution performs no runtime LR35902 opcode decode.
- The exact 16 KiB Bank 0 image is embedded for reads of ROM constants/tables.
- The C++ semantic backend covers base and CB instruction families.
- Cross-bank execution exits cleanly as `StepResult::LeftBank0`.
- Known Bank 0 routines `$0949`, `$095B` and `$1679` are native regression tests.
- Windows CI builds and executes the native self-test.

## Instructions for M3

M3 is the hardware/runtime milestone. Keep the static recompiler architecture
from M2 and add Game Boy behavior behind the memory/runtime interfaces.

Work in this order:

1. Replace the flat compatibility memory with a mapped Bus while preserving the
   current `read8/write8` interface.
2. Add the full 4 MiB fixed ROM image at build time or generated native data so
   ROMX banks can execute without shipping/reading the original ROM file.
3. Implement MBC5 ROM bank registers used by DWM2, including the 9-bit ROM-bank
   selection behavior and external RAM enable/banking.
4. Add WRAM, HRAM, VRAM, OAM and cartridge SRAM mapping.
5. Implement IE/IF and interrupt dispatch/priority, including VBlank entry and
   RETI/IME behavior.
6. Add DIV/TIMA/TMA/TAC timer behavior with cycle accounting.
7. Add joypad register behavior and a host input abstraction.
8. Add instruction cycle metadata to the generated calls so hardware advances by
   authentic LR35902 machine cycles.
9. Handle HALT wakeup/HALT-bug behavior now that interrupt state exists.
10. Extend dispatch from fixed Bank 0 to the selected ROMX bank without runtime
    opcode decoding. Generate native translation units bank-by-bank.
11. Add differential tests for bank switching, stack/interrupt entry, timer
    overflow and joypad reads.
12. Keep M3 headless. Do not add the window/PPU renderer until M4.
13. Declare M3 complete only after Windows CI passes.
14. Create `restore/recomp-m3` and write `M3_NEXT.md`.

## Important design constraint

Do not turn M3 into a bundled Game Boy emulator. Hardware register behavior is a
compatibility runtime, but game instructions must continue to come from the
ahead-of-time generated native translations.
