# Native recomp status

| Milestone | Goal | Status |
|---|---|---|
| M0 | Native EXE pipeline + two statically translated helpers | ✅ complete |
| M1 | Complete LR35902 decoder/frontend | ✅ complete |
| M2 | Bank 0 fully statically translated to native C++ | 🧪 validation |
| M3 | Memory map, MBC5, interrupts, timers and joypad | ⏳ next |
| M4 | PPU/OAM compatibility renderer and native window | ⏳ |
| M5 | Original title screen through recompiled code | ⏳ |
| M6 | Input + overworld | ⏳ |
| M7 | Battles + audio + saves | ⏳ |
| M8 | Fully playable native release | ⏳ |

Restore branches live under `restore/recomp-mN`.
Continuation notes live under `recomp/handoff/`.

## Acceptance rule

A milestone is only marked complete after its Windows CI build and self-test pass.
M2 specifically requires all 16,384 fixed Bank 0 entry addresses to have build-time
native translations and the Bank 0 regression routines to execute correctly.
