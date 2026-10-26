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

## Current milestone: M8 complete

The 2026-10-26 implementation pass adds local two-player serial hosting, original
per-line scrolling and CPU/memory edge fixes. Full-ROM AOT is now the default.
New binary validation is pending; the download below is still the accepted M8
baseline. See the [whole-ROM inventory](handoff/FULL_ROM_IMPLEMENTATION_2026-10-26.md).

The original main campaign is accepted on native Windows x64 on 2026-10-25:
Oasis, Sea, Ice, Sky and Limbo, Darck, MagicPlug, the complete credits, THE END,
original ending Save and fresh Continue. Fixed bank 0 and all 255 switchable
ROM banks are statically compiled, with no runtime opcode interpreter.

[Download the verified package and view the successful final run](https://github.com/rjtvandenhout/DWM2t/actions/runs/40183484388).
Extract the full package and run `DWM2t-M8/Play.cmd`.
`DWM2tRecomp.exe` also starts directly with the same default save; the launcher
adds integrity checks, logs and convenient import options.
[Completion record and exact hashes](milestones/M8_RESULT.md),
[controls, ending-save import and recovery](handoff/M8_NEXT.md), and
[progress with original screenshots](handoff/M8_PROGRESS_2026-10-25.md).

All 38 later-story Windows checkpoints pass: 4,446,466 recorded frames in
36m02s with four workers. Every child Journal matches its actual newly replayed
parent; independent audits verify all 38 links and all 115 archived Journals.
The final native suite executes and passes all 18 original tests with zero
failures/skips. Actual Play.cmd passes 21 package checks; original ending GUI
Journal and fresh-process reload preserve all 17 monsters and all 107 quest
bytes, with two normal shutdowns. Windows/POSIX persistence fault gates pass.

The independently built diagnostic and production binaries share exact source
`3d573873ae8122cbb10fcd5d0f7ae7a33a7609ba` and identical source archives.
The final verified package retains the byte-identical tested production EXE;
validation tools are `8859ef67289ce90712a44b9c17174de4519a59b3`.
Recovery is `restore/recomp-m8`. M7's fixtures and immutable restore remain
unchanged; all M1–M7 regressions pass. [M7 record](milestones/M7_RESULT.md).

`main` is the current finished-game branch. The accepted M0–M8 snapshots are
listed in [RESTORE_POINTS.md](RESTORE_POINTS.md); see the
[branch cleanup record](handoff/BRANCH_CLEANUP_2026-10-25.md) for retired refs.
Routine CI checks tooling and persistence. Full native builds and campaign
validation run manually, so documentation and branch maintenance do not rebuild
the entire game.

Original breeding produces Liset (Octokid +1), Derzo (RayGigas +1), and Garon
(RayGigas +3). Squiz is reserved until his Sea story role finishes. Garon wins
the fourth Darck attempt with 91 HP; Slash and Derzo faint. Original story
healing restores the final party to full HP at levels 40/37/40.

CI tests real WinMM streaming through a signed virtual endpoint. Physical
speaker audibility and every optional postgame branch are not exhaustively
verified. New builds remain UNTESTED_CANDIDATE until their required checks pass.
See the [postgame checks and screenshots](handoff/POSTGAME_PROGRESS_2026-10-25.md)
for the additional key-world/egg/persistence replays and finite generator audit.
The existing partial development suite alone does not certify a new full game.

Actions cleanup reclaimed 3,946,430,584 bytes from 159 unused artifacts while
preserving referenced evidence; see [the storage audit](handoff/ACTIONS_STORAGE_2026-10-24.md).
Project text is English; historical evidence and original game text are retained.

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
