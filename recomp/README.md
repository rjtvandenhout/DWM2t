# DWM2t native static recomp

This is the native-PC recompilation track for **Dragon Warrior Monsters 2:
Cobi's Journey**.

The matching RGBDS decompilation remains the source of truth. The native build
reads checked-in Game Boy machine-code bytes at build time, ahead-of-time
translates the required game code to C++, and lets the host compiler produce
native x86-64 code.

The project does not load an external ROM file in the native build. The exact
4 MiB matching image is generated from `src/banks/` and embedded for original
game-data reads and hardware mapping.

## Current milestone: M7 complete; M8 in progress

M7 adds genuine original P1 battles and player-attack damage, deterministic
game audio with live WinMM output, original PLAN > Journal Save, and Continue
in a new runtime carrying only the exact 32 KiB save file. All twelve local
Windows gates passed twice. Hosted Actions' quota is exhausted; local acceptance
was explicitly authorized, and the hosted workflow now runs the same CTest set.

Run the offline build/validation cycle from the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File recomp/tools/check_m7_local.ps1
```

See `milestones/M7_RESULT.md`, `handoff/M7_LOCAL_WINDOWS.md`, and
`handoff/M7_NEXT.md`. Recovery: `restore/recomp-m7`. Full-game playability is
still the final M8 milestone. Ordinary menu mode C5DB=2 is not battle proof;
the accepted real battle mode is C5DB=4.

M8 now proves the original Oasis quest through the dam boss, WaterCall,
Mirage Lake's CurseLamp battle, recruitment/farm handling and the original
aftermath/return home. Nine chained controller-only routes retain original
Journal saves and fresh Continue checks, including battle HP and audio
assertions. This does **not** prove later worlds, the ending or complete M8.
English development notes and exact current evidence are in
`handoff/M8_WORKING.md`. The active branch is `work/recomp-m8`; the M7 restore
remains immutable. The M7 validator and current packaging messages are English;
quoted historical test evidence and original game text are retained unchanged.

After building, run the expanded development checks from the repository root:

```powershell
ctest --test-dir recomp/build --parallel 4 --output-on-failure
```

Or build the `check-m8-development` target from the developer prompt. All-green
development checks are necessary but not sufficient for final M8 acceptance:
the full original playthrough/ending and later-game checks are still required.

## Retained M6 interactive baseline

M6 turns the M5 title-screen proof into the first interactive slice of the
original game.

The native executable now:

- boots the original CGB cartridge path from `$0100`;
- retains the deterministic M5 title regression;
- drives title/menu/new-game progression only through Game Boy P1 input;
- reaches the real opening ship map through original game code;
- moves the player on that map with D-pad input;
- runs a live Win32 frame loop at Game Boy frame cadence;
- maps host keyboard input to D-pad/A/B/Start/Select;
- loads and saves the cartridge's exact 32 KiB MBC5 SRAM image;
- autosaves dirty SRAM and flushes it on exit;
- treats LR35902 HALT as a normal wait-for-interrupt state in the live loop.

Accepted movement regression:

```text
before framebuffer: 0xd926fc62969f3bb4
after framebuffer:  0xea72400372e2d1c5
WRAM bytes changed: 69
frame:              3757
```

The accepted M6 AOT ROMX set is:

```text
1 2 4 7 15 16 18 19 20 22 23 31 40 52 53 95 96 105 127 132 133 135
```

Missing native ROMX code remains a hard runtime failure. There is no generic
runtime LR35902 interpreter fallback.

## Windows build

Requirements:

- CMake 3.24+
- Python 3
- Visual Studio Build Tools with the C++ workload

From the repository root:

```powershell
cmake -S recomp -B recomp/build -A x64
cmake --build recomp/build --config Release --parallel 4
```

Run the live game:

```powershell
.\recomp\build\Release\DWM2tRecomp.exe --play
```

Or choose an explicit save file:

```powershell
.\recomp\build\Release\DWM2tRecomp.exe --play my-save.sav
```

Controls:

```text
Arrow keys  D-pad
Z           A
X           B
Enter       Start
Backspace   Select
```

Permanent regression commands include:

```powershell
.\recomp\build\Release\DWM2tRecomp.exe --self-test --bmp recomp\build\m4_renderer_test.bmp
.\recomp\build\Release\DWM2tRecomp.exe --title-test recomp\build\m5_title_screen.bmp
.\recomp\build\Release\DWM2tRecomp.exe --m6-probe recomp\build\m6_probe
.\recomp\build\Release\DWM2tRecomp.exe --m6-sram-test recomp\build\m6_test.sav
.\recomp\build\Release\DWM2tRecomp.exe --m6-window-smoke recomp\build\m6_test.sav
```

## Milestone architecture

```text
matching RGBDS banks
        |
        +--> exact embedded 4 MiB game image
        |
        +--> build-time LR35902 AOT translation
                    |
                    v
             generated native C++
                    |
                    v
              MSVC / clang
                    |
                    v
             DWM2tRecomp.exe
                    |
        +-----------+-----------+-----------+
        |           |           |           |
    mapped GB    CGB software  Win32      .sav SRAM
     hardware      renderer    input/UI   persistence
```

## Roadmap

1. **M0** native EXE pipeline. ✅
2. **M1** complete LR35902 frontend. ✅
3. **M2** all fixed Bank 0 addresses statically translated. ✅
4. **M3** memory map, MBC5, interrupts, timers and joypad. ✅
5. **M4** CGB renderer and native window. ✅
6. **M5** original title screen from recompiled game code. ✅
7. **M6** live input, title/menu transition, real map movement and save RAM. ✅
8. **M7** real battles, audio and original in-game save/continue. ✅
9. **M8** fully playable native PC release and optional enhanced patches.

## Project rules

- The matching RGBDS build is the behavioral/source reference.
- Accepted milestones get immutable `restore/recomp-mN` branches.
- Every milestone leaves continuation instructions under `recomp/handoff/`.
- Missing native code is surfaced explicitly rather than hidden behind an
  instruction interpreter.
- Hardware compatibility behavior belongs in the runtime; original game
  instructions remain ahead-of-time translated.
