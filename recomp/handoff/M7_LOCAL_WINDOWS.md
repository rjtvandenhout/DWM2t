# M7 local Windows workflow

This document records the repeatable local cycle for the native recompilation
track. GitHub remains the commit and final-validation surface; local Windows
execution is the primary development loop.

## Local tools

- Python 3.14: `C:\Python314\python.exe`
- Visual Studio Community 2026 C++ toolchain
- User-local CMake 4.4.4:
  `C:\Users\rick9\AppData\Roaming\Python\Python314\Scripts\cmake.exe`

The Visual Studio generator is not available in this installation, so use the
NMake generator from a Visual Studio developer prompt.

## Configure and build

From the repository root in PowerShell:

```powershell
$vsDev = 'C:\Program Files\Microsoft Visual Studio\18\Community\Common7\Tools\VsDevCmd.bat'
$cmake = 'C:\Users\rick9\AppData\Roaming\Python\Python314\Scripts\cmake.exe'
$line = 'call "' + $vsDev + '" -arch=x64 && "' + $cmake + '" -G "NMake Makefiles" -DCMAKE_BUILD_TYPE=Release -S recomp -B recomp/build && "' + $cmake + '" --build recomp/build'
cmd.exe /d /c $line
```

Incremental rebuilds use the same developer prompt:

```powershell
cmake --build recomp/build
```

The executable is `recomp/build/DWM2tRecomp.exe`.

## Local validation order

Run the cheap source/runtime checks first, then the M7 probes:

```powershell
python recomp/tools/test_lr35902.py --bank0 src/banks/bank_000.asm
python recomp/tools/recompile_bank0.py --bank src/banks/bank_000.asm --audit-only
recomp/build/DWM2tRecomp.exe --self-test --bmp recomp/build/m4_renderer_test.bmp
recomp/build/DWM2tRecomp.exe --title-test recomp/build/m5_title_screen.bmp
recomp/build/DWM2tRecomp.exe --m6-probe recomp/build/m6_probe
recomp/build/DWM2tRecomp.exe --m6-sram-test recomp/build/m6_test.sav
recomp/build/DWM2tRecomp.exe --m6-window-smoke recomp/build/m6_test.sav
recomp/build/DWM2tRecomp.exe --m7-audio-probe
recomp/build/DWM2tRecomp.exe --m7-fast-route recomp/build/m7_search
recomp/build/DWM2tRecomp.exe --m7-save-continue-test recomp/build/m7_real.sav recomp/build/m7_save_continue
```

`--m7-fast-route` must produce a real P1 battle with `C5DB=2` and prove a
command effect by comparing original-game control and command runs. The save
probe must prove an original in-game save, a 32 KiB SRAM image, and Continue
from a fresh runtime. No host-side RAM or battle state may be injected.

## Current local result

- Python/LR35902, M4, M5, M6 movement/SRAM/window, and original-game audio pass.
- The pinned P1 route reaches the original selector/dialogue checkpoints.
- The current battle search still exhausts without `C5DB=2`; `C193` and
  `C562` remain zero at the selector-1A checkpoint and the tested adjacent
  movement/interactions do not load a target.
- The save/Continue probe still finds no real in-game save candidate.
- Therefore `restore/recomp-m7` must not be created yet.

## Acceptance and handoff rule

Only after every M7 acceptance probe is green, together with the M4-M6 and
audio regressions, create `restore/recomp-m7` and update the milestone result
and next-step documents. Until then, keep generated build output and save files
under `recomp/build/` and do not treat diagnostic route progress as acceptance.
