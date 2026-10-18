# M7 local Windows workflow

This document records the repeatable local cycle for the native recompilation
track. GitHub remains the commit surface; local Windows execution is the
primary development and acceptance loop. The user confirmed that the monthly
Actions quota is exhausted and explicitly requested local validation instead.
Hosted CI should run the same gates again when available; quota exhaustion
itself is neither a test failure nor a passing result.

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

The offline runner finds the installed CMake and Visual Studio C++ toolchain,
configures a fresh NMake Release build when needed, builds incrementally, and
runs all twelve CTest gates. No GitHub runner, ROM download, or network is used:

```powershell
powershell -ExecutionPolicy Bypass -File recomp/tools/check_m7_local.ps1
```

Logs are under `recomp/build/Testing/Temporary/LastTest.log`; screenshots and
save evidence are under `recomp/build/local-validation/`. A nonzero exit means
M7 is not accepted. For individual diagnostics:

```powershell
python recomp/tools/test_lr35902.py --bank0 src/banks/bank_000.asm
python recomp/tools/recompile_bank0.py --bank src/banks/bank_000.asm --audit-only
recomp/build/DWM2tRecomp.exe --self-test --bmp recomp/build/m4_renderer_test.bmp
recomp/build/DWM2tRecomp.exe --title-test recomp/build/m5_title_screen.bmp
recomp/build/DWM2tRecomp.exe --m6-probe recomp/build/m6_probe
recomp/build/DWM2tRecomp.exe --m6-sram-test recomp/build/m6_test.sav
recomp/build/DWM2tRecomp.exe --m6-window-smoke recomp/build/m6_test.sav
recomp/build/DWM2tRecomp.exe --m7-audio-probe
recomp/build/DWM2tRecomp.exe --m7-battle-test recomp/build/m7_battle
recomp/build/DWM2tRecomp.exe --m7-save-continue-test recomp/build/m7_real.sav recomp/build/m7_save_continue
```

The battle gate must produce a genuine P1-entered battle and prove an original
battle action/turn effect. **C5DB=2 is not battle evidence**: actual P1 play
showed that both PLAN and Magic Door key selection use that mode. The user
explicitly approved replacing that mistaken condition with proven real battle
entry, the measured battle mode, and command/turn evidence. The save
probe must prove an original in-game save, a 32 KiB SRAM image, and Continue
from a fresh runtime. No host-side RAM or battle state may be injected.

## Current local result

- Python/LR35902, M4, M5, M6 movement/SRAM/window, and original-game audio pass.
- Strict, finite P1 fixtures now replay the introductory quest and original
  Slash party introduction from a fresh runtime, without host RAM writes,
  checkpoint restores, or fabricated party/quest state.
- The real PLAN > Journal and Magic Door > Oasis Key paths have been reached.
- Original Journal Save and fresh-runtime Continue pass automatically: 317
  SRAM bytes changed, exact 32768-byte file, all 304 party/inventory bytes and
  eleven quest/location fields restored. SRAM FNV: `0x81daa8e19c019ce4`.
- A genuine original Oasis encounter sets C5DB=4 and reaches 49:$4001. The
  P1 Fight command resolves an actual Slash attack: enemy HP 9->6, Slash HP
  25->20, while the equal-time no-input control stays unchanged. Exact
  framebuffer and 282-frame action regression values are pinned.
- All twelve gates passed twice locally: 156.85 seconds initially and
  131.65 seconds for the final pinned acceptance run.
- Legacy route-search probes are discovery tools, not acceptance evidence;
  the old `C5DB=2` heuristic must not certify M7.
- M7 is accepted; see `../milestones/M7_RESULT.md` and `M7_NEXT.md` for M8.

## Acceptance and handoff rule

Only after every M7 acceptance probe is green, together with the M4-M6 and
audio regressions, create `restore/recomp-m7` and update the milestone result
and next-step documents. Until then, keep generated build output and save files
under `recomp/build/` and do not treat diagnostic route progress as acceptance.
