# DWM2t native static recomp

This branch is the native-PC recompilation track for DWM2t.

The matching RGBDS decompilation remains the source of truth. The native build reads the checked-in Game Boy machine-code bytes at **build time**, translates selected LR35902 routines to C++, and lets the host compiler produce native x86-64 code.

## Current milestone: M0

M0 proves the pipeline end-to-end:

```text
src/banks/bank_000.asm
        |
        v
recompile_smoke.py
  LR35902 -> C++
        |
        v
MSVC / clang / GCC
        |
        v
DWM2tRecomp.exe
```

Two real routines are translated mechanically from the matching ROM source:

- `$0949` — the Bank 0 memset helper
- `$1679` — the Bank 0 memcpy helper

The executable runs both translated routines against the native compatibility memory model and fails if their observable results are wrong.

This is deliberately a small proof-of-recomp milestone. It is a real native executable, but it is **not yet the playable game**.

## Windows build

Requirements:

- CMake 3.24+
- Python 3
- Visual Studio 2022 Build Tools with the C++ workload

From the repository root:

```powershell
cmake -S recomp -B recomp/build -A x64
cmake --build recomp/build --config Release
.\recomp\build\Release\DWM2tRecomp.exe --self-test
```

GitHub Actions also builds `DWM2tRecomp.exe` on Windows and uploads it as an artifact.

## Roadmap

1. **M0**: build-time LR35902 -> C++ translation + native EXE smoke test.
2. **M1**: broaden the decoder to all LR35902 opcodes and statically translate Bank 0 control flow.
3. **M2**: native Game Boy memory map, MBC5 banking, interrupts, timers and joypad.
4. **M3**: PPU/OAM/tile compatibility renderer and a native window.
5. **M4**: reach the original title screen using recompiled code.
6. **M5**: overworld input, map movement and save RAM.
7. **M6**: battle/audio completion and full-game regression testing.
8. **M7**: playable native PC release with optional enhanced patches.

The rule is the same as the matching decomp: do not guess semantics in the source of truth. The recomp layer may add host-side compatibility code, but original game behavior should remain testable against the matching ROM build.
