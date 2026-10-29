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

## Current full-ROM player

The Cobi/CGB player has passed the recorded main campaign, seven postgame
checkpoints, native Windows tests and production package checks. Fixed bank 0
and all 255 switchable ROM banks are statically compiled, with no runtime
opcode interpreter. The implementation also includes local two-player hosting,
per-line scrolling and CPU/memory edge handling.

[Download the verified player and ending save](https://github.com/rjtvandenhout/DWM2t/actions/runs/40821196055/artifacts/12875666985).
Extract the Actions download and then the inner player ZIP; start `Play.cmd` or
`DWM2tRecomp.exe` from the resulting `DWM2t-M8` folder. The
[current result and playing guide](handoff/FULL_ROM_RESULT_2026-10-29.md)
provides save import steps, controls, exact hashes and screenshots.

The original game/build source is `1351bcd058e491455a477045a2ff86bbc3bd7b1c`;
the successful continuation uses validation and packaging tools from
`2e4057a190e626c4f1fe8118668f45a0d89bafb3`. The earlier archived build run and
later validation run have separate identities; see the current result. The
38 story stages and seven postgame stages are recorded coverage, not a proof of
every optional path or generated world. Tara and SGB presentation are outside
this Cobi/CGB result.

The prior accepted [M8 completion record](milestones/M8_RESULT.md),
[playthrough screenshots](handoff/M8_PROGRESS_2026-10-25.md),
[postgame report](handoff/POSTGAME_PROGRESS_2026-10-25.md) and
[immutable M0–M8 restore points](RESTORE_POINTS.md) retain their original
identities. Original breeding produced Liset, Derzo and Garon; Squiz was
reserved until his Sea story role finished. The original Actions storage cleanup
is recorded in [the storage audit](handoff/ACTIONS_STORAGE_2026-10-24.md).

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

For playing, use the verified package above. The commands below create developer
diagnostic builds. The default compiles fixed bank 0 and all 255 ROMX banks.

Requirements:

- CMake 3.24+
- Python 3
- Visual Studio Build Tools with the C++ workload

From the repository root:

```powershell
cmake -S recomp -B recomp/build -A x64
cmake --build recomp/build --config Release --parallel 4
```

For an isolated complete AOT build, use a separate directory. Full compilation
needs substantial time, RAM and disk space. From an x64 Visual Studio developer
prompt, with Ninja installed:

```powershell
cmake -S recomp -B recomp/build-all -G Ninja -DCMAKE_BUILD_TYPE=Release -DDWM2T_ALL_ROMX=ON -DDWM2T_OUTPUT_NAME=DWM2tRecompFull
cmake --build recomp/build-all --parallel 4
ctest --test-dir recomp/build-all --parallel 4 --output-on-failure
```

This remains ahead-of-time native code with no runtime instruction-interpreter
fallback. Compiling every bank is not proof of full-game playability or M8
completion; the original gameplay, ending and Save/Continue gates still apply.
The extended Kids Class regression is enabled only with `DWM2T_ALL_ROMX=ON`.
An explicit `-DDWM2T_ALL_ROMX=OFF` retains the limited discovery build for earlier
Oasis/home development. CMake prints its coverage mode, and the production
packager continues to require all 255 ROMX banks.

Run the live game:

```powershell
.\recomp\build\Release\DWM2tRecomp.exe --play
```

Or choose an explicit save file:

```powershell
.\recomp\build\Release\DWM2tRecomp.exe --play my-save.sav
```

Controls:

Live audio defaults to 5% linear-amplitude playback volume with mild host-only
smoothing. These numbers are not perceived-loudness percentages; use 1% for
an especially loud headset setup. Windows playback prebuffers about 50 ms
of original PCM to tolerate scheduling jitter without changing game timing.
The unclipped original mix is attenuated before conversion to Windows PCM;
the retained APU regression capture and game timing remain unchanged.
Use `--audio-volume 0` through `--audio-volume 100` to adjust loudness.
`--audio-raw` disables smoothing, not volume control. For example:

```powershell
.\recomp\build\Release\DWM2tRecomp.exe --play my-save.sav --audio-volume 1
```

`--audio-devices` lists local outputs. If the Windows default mapper fails,
the program tries enumerated devices; `--audio-device N` selects one explicitly.
No Windows device, mixer or system-volume settings are changed.

Keyboard controls:

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
9. **M8** native Windows release validated through the complete original main campaign. ✅

Optional enhanced patches remain separate future work.

## Project rules

- The matching RGBDS build is the behavioral/source reference.
- Accepted milestones get immutable `restore/recomp-mN` branches.
- Every milestone leaves continuation instructions under `recomp/handoff/`.
- Missing native code is surfaced explicitly rather than hidden behind an
  instruction interpreter.
- Hardware compatibility behavior belongs in the runtime; original game
  instructions remain ahead-of-time translated.
