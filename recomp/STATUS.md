# Native recomp status

| Milestone | Goal | Status |
|---|---|---|
| M0 | Native EXE pipeline + two statically translated helpers | ✅ complete |
| M1 | Complete LR35902 decoder/frontend | ✅ complete |
| M2 | Bank 0 fully statically translated to native C++ | ✅ complete |
| M3 | Memory map, MBC5, interrupts, timers and joypad | ✅ complete |
| M4 | PPU/OAM compatibility renderer and native window | ✅ complete |
| M5 | Original title screen through recompiled code | ✅ complete |
| M6 | Input + overworld + save RAM | ⏳ next |
| M7 | Battles + audio + remaining runtime | ⏳ |
| M8 | Fully playable native release | ⏳ |

Restore branches live under `restore/recomp-mN`.
Continuation notes live under `recomp/handoff/`.

## M3 acceptance evidence

Windows CI run `38821080893` passed at
`8ec0c1e80b5cea3df8f9581d1424fae319ec67d6`.

Verified in the native Windows executable:

- exact 4 MiB ROM image embedded from checked-in matching source;
- MBC5 ROM/RAM banking;
- WRAM/VRAM/OAM/HRAM mapping and OAM DMA;
- timers and interrupts;
- joypad matrix and IRQ;
- HALT-bug trigger behavior;
- native Bank 2 -> Bank 0 -> Bank 2 execution;
- instruction machine-cycle accounting.

Restore point: `restore/recomp-m3`.

## M4 acceptance evidence

Windows CI run `38821625108` passed at
`29c4c8249f5a77a17ea8194d624d20af52da3e6b`.

Verified:

- deterministic 160x144 CGB framebuffer;
- BG/window tile rendering;
- VRAM-bank attributes and X/Y flip;
- OAM sprite transparency/priority;
- CGB BGR555 palette conversion;
- Win32 native presentation;
- renderer regression FNV-1a `0x284882dc2a98916f`.

Restore point: `restore/recomp-m4`.

## M5 acceptance evidence

Windows CI run `38825575292` passed at
`9d0b9830ea6542def717a8cde726691cd0421cc2`.

The executable boots the original DWM2 Cobi cartridge path from `$0100`
using only embedded matching source data and ahead-of-time translated game code.
It reaches the real title screen at frame 1921 with:

```text
framebuffer FNV-1a: 0x49c67a53ef4f8a80
stable frames:      30
C5DB game state:    5
C5DC substate:      0
```

The regression fails on a missing native ROMX bank, CPU trap, unexpected STOP,
or failure to reach the accepted title framebuffer within the bounded boot
budget.

Native title-path ROMX banks currently compiled ahead-of-time:

```text
1, 2, 7, 127
```

The fixed HRAM OAM-DMA helper copied by the original game is also represented by
an ahead-of-time native translation rather than a runtime opcode interpreter.

Restore point: `restore/recomp-m5`.
