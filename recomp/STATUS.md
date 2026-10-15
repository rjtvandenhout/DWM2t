# Native recomp status

| Milestone | Goal | Status |
|---|---|---|
| M0 | Native EXE pipeline + two statically translated helpers | ✅ complete |
| M1 | Complete LR35902 decoder/frontend | ✅ complete |
| M2 | Bank 0 fully statically translated to native C++ | ✅ complete |
| M3 | Memory map, MBC5, interrupts, timers and joypad | ⏳ next |
| M4 | PPU/OAM compatibility renderer and native window | ⏳ |
| M5 | Original title screen through recompiled code | ⏳ |
| M6 | Input + overworld | ⏳ |
| M7 | Battles + audio + saves | ⏳ |
| M8 | Fully playable native release | ⏳ |

Restore branches live under `restore/recomp-mN`.
Continuation notes live under `recomp/handoff/`.

## M2 acceptance evidence

Windows CI run `38819460960` passed the complete milestone:

- LR35902 frontend validation: PASS
- Bank 0 translation audit: 16,384 / 16,384 entry addresses
- native Windows build: PASS
- `$0949` memset regression: PASS
- `$095B` RNG/table regression: PASS
- `$1679` memcpy regression: PASS
- arithmetic / DAA flag-edge checks: PASS
- Windows artifact upload: PASS

The immutable M2 restore point is `restore/recomp-m2` at
`e68bd3e1136f93982a33d755d20bd3b093a6f7b5`.
