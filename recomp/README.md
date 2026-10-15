# DWM2t native static recomp

This branch is the native-PC recompilation track for DWM2t.

The matching RGBDS decompilation remains the source of truth. The native build
reads the checked-in Game Boy machine-code bytes at **build time**, translates
them to C++, and lets the host compiler produce native x86-64 code.

There is no LR35902 opcode decoder in the normal Bank 0 execution path at
runtime. Bank 0 instruction entry points are generated ahead of time.

## Current milestone: M2

M0 established the native EXE pipeline.

M1 added a complete LR35902 frontend:

- 245 legal base opcodes;
- all 11 illegal Game Boy CPU opcodes represented explicitly;
- all 256 CB-prefixed opcodes;
- stable instruction sizes and immediates;
- independent decode coverage for every Bank 0 byte address.

M2 takes the next step:

```text
src/banks/bank_000.asm
        |
        v
recompile_bank0.py
        |
        +--> bank0_master.cpp
        +--> bank0_chunk_0.cpp
        +--> bank0_chunk_1.cpp
        +--> bank0_chunk_2.cpp
        +--> bank0_chunk_3.cpp
        |
        v
compile-time LR35902 semantic templates
        |
        v
MSVC / clang / GCC
        |
        v
DWM2tRecomp.exe
```

All **16,384** fixed Bank 0 addresses receive a native translation entry.
The exact Bank 0 bytes are also embedded for ROM-data reads.

Current regression anchors include:

- `$0949` Bank 0 memset helper;
- `$095B` RNG/table helper;
- `$1679` Bank 0 memcpy helper;
- arithmetic/half-carry/DAA edge checks.

This executable is still a technical native recomp milestone, **not yet the
playable game**. The next milestone is the Game Boy hardware/runtime layer.

## Windows build

Requirements:

- CMake 3.24+
- Python 3
- Visual Studio 2022 Build Tools with the C++ workload

From the repository root:

```powershell
python recomp/tools/test_lr35902.py --bank0 src/banks/bank_000.asm
python recomp/tools/recompile_bank0.py --bank src/banks/bank_000.asm --audit-only

cmake -S recomp -B recomp/build -A x64
cmake --build recomp/build --config Release
.\recomp\build\Release\DWM2tRecomp.exe --self-test
```

GitHub Actions performs the same validation and uploads the Windows executable.

## Roadmap

1. **M0**: native EXE pipeline and initial statically translated routines.
2. **M1**: complete LR35902 decode/frontend.
3. **M2**: all fixed Bank 0 entry addresses statically translated to native C++.
4. **M3**: Game Boy memory map, MBC5 banking, interrupts, timers and joypad.
5. **M4**: PPU/OAM/tile compatibility renderer and native window.
6. **M5**: reach the original title screen through recompiled code.
7. **M6**: input, maps, overworld movement and save RAM.
8. **M7**: battles, audio and remaining save/runtime behavior.
9. **M8**: fully playable native PC release with optional enhanced patches.

## Project rules

- The matching RGBDS build remains untouched as the reference.
- Recomp work stays on `recomp/native-pc` until it is mature.
- Each completed milestone gets a `restore/recomp-mN` branch.
- Each milestone leaves a continuation note in `recomp/handoff/`.
- Do not hide emulation/interpreter fallbacks inside a milestone and call them
  static recompilation. Hardware compatibility code is fine; runtime opcode
  decoding is not the normal execution strategy.
