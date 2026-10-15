# DWM2t native static recomp

This is the native-PC recompilation track for **Dragon Warrior Monsters 2:
Cobi's Journey**.

The matching RGBDS decompilation remains the source of truth. The native build
reads the checked-in Game Boy machine-code bytes at **build time**, translates
the required game code to C++, and lets the host compiler produce native x86-64
code.

The project does not load an external ROM file for the native build. The exact
4 MiB matching ROM image is generated from `src/banks/` and embedded at build
time for game-data reads and hardware mapping.

## Current milestone: M5

M5 is the first visual proof that the original game itself is running through
the native recomp path.

The executable now boots from the real CGB cartridge entry point `$0100`,
executes the original splash/intro sequence, and reaches the original
**Dragon Warrior Monsters 2: Cobi's Journey** title screen.

Accepted title regression:

```text
frame reached:       1921
framebuffer FNV-1a:  0x49c67a53ef4f8a80
stable frames:       30
game state C5DB:     5
substate C5DC:       0
```

That framebuffer is produced by original DWM2 code writing VRAM, OAM, palettes,
scroll/window registers and game state. It is not a host-side reconstruction of
the title artwork.

### Native title path

The title boot currently needs these ROMX banks translated ahead of time:

```text
1 2 7 127
```

A fixed OAM-DMA routine copied by the game to HRAM `$FF80-$FF89` is also
compiled as a known native code fragment. Missing ROMX banks remain a hard
runtime failure instead of silently falling back to an LR35902 interpreter.

## Windows build

Requirements:

- CMake 3.24+
- Python 3
- Visual Studio 2022 Build Tools with the C++ workload

From the repository root:

```powershell
cmake -S recomp -B recomp/build -A x64
cmake --build recomp/build --config Release --parallel 4
```

Run the retained hardware/renderer regression suite:

```powershell
.\recomp\build\Release\DWM2tRecomp.exe --self-test --bmp recomp\build\m4_renderer_test.bmp
```

Boot the real game and verify the accepted title screen:

```powershell
.\recomp\build\Release\DWM2tRecomp.exe --title-test recomp\build\m5_title_screen.bmp
```

Show the real title framebuffer in the native Win32 window:

```powershell
.\recomp\build\Release\DWM2tRecomp.exe --title-window
```

The exploratory boot tracer remains available when extending the game path:

```powershell
.\recomp\build\Release\DWM2tRecomp.exe --title-probe recomp\build\title_probe
```

## Milestone architecture

```text
matching RGBDS banks
        |
        +--> exact .gbc reference build
        |
        +--> build-time LR35902 analysis / AOT translation
                    |
                    v
             generated C++
                    |
                    v
              MSVC / clang
                    |
                    v
             DWM2tRecomp.exe
                    |
        +-----------+-----------+
        |           |           |
    mapped GB    CGB software  native host
     hardware      renderer      window/input
```

## Roadmap

1. **M0** native EXE pipeline. ✅
2. **M1** complete LR35902 frontend. ✅
3. **M2** all fixed Bank 0 addresses statically translated. ✅
4. **M3** memory map, MBC5, interrupts, timers and joypad. ✅
5. **M4** CGB renderer and native window. ✅
6. **M5** original title screen from recompiled game code. ✅
7. **M6** live input, title/menu transition, overworld and save RAM.
8. **M7** battles, audio and remaining runtime behavior.
9. **M8** fully playable native PC release and optional enhanced patches.

## Project rules

- The matching RGBDS build is the behavioral/source reference.
- Accepted milestones get immutable `restore/recomp-mN` branches.
- Every milestone leaves continuation instructions under `recomp/handoff/`.
- Missing native code is surfaced explicitly. It is not hidden behind an
  instruction interpreter.
- Hardware compatibility behavior is allowed in the runtime; game instructions
  remain ahead-of-time translated.
