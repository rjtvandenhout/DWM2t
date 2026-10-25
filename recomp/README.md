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
Windows gates passed twice; subsequent hosted checks also passed. Actions
artifact cleanup reclaimed 3,946,430,584 bytes while preserving referenced
builds and evidence; see [the storage audit](handoff/ACTIONS_STORAGE_2026-10-24.md).

Run the offline build/validation cycle from the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File recomp/tools/check_m7_local.ps1
```

See `milestones/M7_RESULT.md`, `handoff/M7_LOCAL_WINDOWS.md`, and
`handoff/M7_NEXT.md`. Recovery: `restore/recomp-m7`. Full-game playability is
still the final M8 milestone. Ordinary menu mode C5DB=2 is not battle proof;
the accepted real battle mode is C5DB=4.

The M8 development build statically compiles bank 0 and all 255 switchable ROM
banks, with no runtime opcode interpreter. Original controller-only routes
have completed Oasis, Kids Class and Sea World. After Squiz finished his story
role, original breeding produced Liset (Octokid +1), now a trained healer.
The team also won C Class, completed the linked trades for IceKey and reached
Norden in Ice World, earned the Crest, defeated BombCrag and AgDevil, and
restored Norden, Yuna and Queen Helen. Native Windows run
[40136433795](https://github.com/rjtvandenhout/DWM2t/actions/runs/40136433795)
passes all twenty later story checkpoints with exact original Journal saves
and fresh Continue; every archived save independently matches Wine.
Later Wine replays breed Totum and Nyar to hatch
Derzo (RayGigas +1). The production candidate's normal GUI also passes a later
Continue, original Journal and fresh-process reload check under Wine and
native Windows (run 40144322233). Native
Windows run 40152139075 has audited twenty archived checkpoints and
replayed ten later routes through Heaven Sword; all ten new Journal hashes
match Wine with the full 107-byte quest block verified. A third original
breeding produces Garon (RayGigas +3). Wine validation now covers 38 checkpoints
through all Heaven relics, Niterich, Mudou and Sky completion. The party has
earned Limbo Key and entered the final world. The first guardian attempt and
original training to level39/37/37 also replay independently. The three-monster
Limbo guardian is now defeated with all three allies alive; its later Journal
also passes independent replay. The later supply Journals and complete ending
also pass independent replay. Garon defeats Darck in the fourth attempt; Slash
and Derzo faint. The original MagicPlug aftermath, full credits, THE END,
ending Save and postgame Continue are recorded. The ending Journal preserves
all 17 monsters and all 107 quest bytes. The historical production player also
passes original ending Journal and fresh-process reload under Wine.

**Final M8 acceptance is pending.** Fresh exact-source diagnostic/production
builds, combined native Windows regressions and final verified-package checks
remain outstanding.
The [current progress report](handoff/M8_PROGRESS_2026-10-25.md) includes original
screenshots and exact evidence. Working notes are in `handoff/M8_WORKING.md`;
the active draft PR is [#4](https://github.com/rjtvandenhout/DWM2t/pull/4) on
`work/recomp-m8-dancer-20261023`. The M7 restore remains immutable. Project text
is English; historical evidence and original game text are retained unchanged.

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

For later-game development, an optional complete AOT build translates all
255 switchable banks, rather than only the banks already reached in tests.
Use a separate build directory; this needs substantially more time, RAM and
disk space. From an x64 Visual Studio developer prompt, with Ninja installed:

```powershell
cmake -S recomp -B recomp/build-all -G Ninja -DCMAKE_BUILD_TYPE=Release -DDWM2T_ALL_ROMX=ON -DDWM2T_OUTPUT_NAME=DWM2tRecompFull
cmake --build recomp/build-all --parallel 4
ctest --test-dir recomp/build-all --parallel 4 --output-on-failure
```

This remains ahead-of-time native code with no runtime instruction-interpreter
fallback. Compiling every bank is not proof of full-game playability or M8
completion; the original gameplay, ending and Save/Continue gates still apply.
The extended Kids Class regression is enabled only with `DWM2T_ALL_ROMX=ON`.
The smaller default build retains the proven earlier Oasis/home tests; it is
not the build for later-game testing. CMake prints the selected coverage mode.

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
9. **M8** fully playable native PC release and optional enhanced patches.

## Project rules

- The matching RGBDS build is the behavioral/source reference.
- Accepted milestones get immutable `restore/recomp-mN` branches.
- Every milestone leaves continuation instructions under `recomp/handoff/`.
- Missing native code is surfaced explicitly rather than hidden behind an
  instruction interpreter.
- Hardware compatibility behavior belongs in the runtime; original game
  instructions remain ahead-of-time translated.
