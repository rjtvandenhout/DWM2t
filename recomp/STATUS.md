# Native recomp status

| Milestone | Goal | Status |
|---|---|---|
| M0 | Native EXE pipeline + two statically translated helpers | ✅ complete |
| M1 | Complete LR35902 decoder/frontend | ✅ complete |
| M2 | Bank 0 fully statically translated to native C++ | ✅ complete |
| M3 | Memory map, MBC5, interrupts, timers and joypad | ✅ complete |
| M4 | PPU/OAM compatibility renderer and native window | ✅ complete |
| M5 | Original title screen through recompiled code | ⏳ next |
| M6 | Input + overworld | ⏳ |
| M7 | Battles + audio + saves | ⏳ |
| M8 | Fully playable native release | ⏳ |

Restore branches live under `restore/recomp-mN`.
Continuation notes live under `recomp/handoff/`.

## M3 acceptance evidence

Windows CI run `38821080893` passed at
`8ec0c1e80b5cea3df8f9581d1424fae319ec67d6`.

Verified in the native Windows executable:

- exact 4 MiB ROM image embedded from checked-in matching source;
- MBC5 ROM bank selection and cartridge RAM banking;
- WRAM/VRAM bank mapping and OAM DMA;
- timer overflow/reload and timer interrupt;
- joypad matrix and joypad interrupt;
- interrupt priority/stack entry with 5 M-cycle service timing;
- HALT-bug trigger behavior;
- ahead-of-time Bank 2 -> Bank 0 -> Bank 2 execution;
- per-instruction machine-cycle advancement.

Restore point: `restore/recomp-m3`.


## M4 acceptance evidence

Windows CI run `38821625108` passed at
`29c4c8249f5a77a17ea8194d624d20af52da3e6b`.

- CGB BG/window tile rendering: PASS
- VRAM-bank attributes and X/Y flip paths: PASS
- OAM sprite transparency/priority path: PASS
- deterministic BGR555 -> RGBA conversion: PASS
- Win32 presentation layer compiled into the native executable
- deterministic renderer FNV-1a: `0x284882dc2a98916f`
- BMP regression artifact produced in CI

Restore point: `restore/recomp-m4`.
