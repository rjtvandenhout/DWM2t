# M8 release-candidate implementation

**Status: implementation prepared; build and testing deferred.**

The user requested completion of implementation with testing left for later
on 2026-10-22. This pass adds a production player and build/package path; it
is not an M8 gameplay acceptance record. No new world, ending, Windows build,
regression pass or physical audio result is claimed by this document.

## Production entry point

`player/CMakeLists.txt` builds `DWM2tPlayer` as `DWM2tRecomp.exe`. It reuses
fixed bank 0, all 255 ROMX AOT libraries, the original embedded image and the
existing hardware/renderer/audio/window implementations. The historical
`src/main.cpp` and M6/M7/M8 acceptance/discovery harnesses are not linked into
the production target. They remain available in the parent developer build.

No arguments start normal play with the default persistent profile. `wmain`
preserves Unicode Windows paths. `--help`, `--version`, `--profile`,
`--play [save]`, `--scale`, audio volume/device/raw options and device listing
are implemented. Metadata always describes an untested candidate, not a final
release. Native code still traps on unknown executable RAM rather than using
an interpreter or fabricating game state.

The normal original game already supplies its remaining worlds and systems
through the translated cartridge code. No guessed story flags, boss outcomes,
key records or fabricated ending routes have been added. Whether all those
paths work in the host runtime is a deferred execution/validation question.

## Save handling

`atomic_sram.hpp` writes the exact 32768 SRAM bytes to an exclusively created
same-directory temporary file. It flushes/closes before replacement; Windows
uses wide-character file APIs and write-through replacement. POSIX builds use
write/fsync/rename and directory sync. Failed operations do not clear the
in-memory dirty flag. Existing non-regular or wrong-size files are refused;
load errors are detected before modifying the runtime's SRAM.

This changes host file persistence only, not cartridge rules or save format.
It does not equate arbitrary SRAM changes with an original Journal Save.
Power-loss guarantees depend on the filesystem/storage device and remain a
validation topic, not a proven result.

The production player holds a per-save native lock for its entire session,
backs up an existing valid file before play and captures read-only failure
metadata/framebuffer on an abnormal runtime exit. The packaged launcher adds
integrity checks, logs, explicit import-to-new-profile and separate backups.
Default saves stay under `%LOCALAPPDATA%\DWM2t\saves`, outside the package.
Earlier accepted saves and output packages are never migrated or overwritten
automatically. Explicit custom save paths remain supported.

## One-command build and package (no tests)

From the repository root on Windows, with Git, CMake, Python 3.10+ and x64
C++ build tools installed:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File recomp/Build-Candidate.ps1
```

The builder discovers an installed supported Visual Studio generator. Ninja
is also supported from an x64 developer prompt:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File recomp/Build-Candidate.ps1 -Generator Ninja -Jobs 2
```

Both workspace and output must be new. Defaults are unique directories below
`recomp/build/candidates/` and `recomp/build/packages/`, which are ignored by
Git. No old build cache, user save or package is deleted. The script archives
the pinned commit's sources, checks their exact owned-ROM identity, forces
complete AOT coverage and a static MSVC runtime, and builds the full dependency
graph. It never starts the player or any test command. Generated-registry and
PE-header checks are build/package identity checks, not gameplay validation.

The package contains the player, launcher, English instructions, license
notice and source/file manifests. It deliberately contains no personal or
acceptance saves. The output also retains compiler logs and `build-report.json`.
Its ZIP and metadata are explicitly marked `UNTESTED`; successful compilation
alone cannot promote this to an accepted release.

`.github/workflows/recomp-candidate.yml` exposes the same path as an explicit
manual build-only workflow. It has no push trigger, test steps, deployment or
public release step. The existing development-test workflow is preserved.
This implementation commit uses `[skip ci]` so it does not start that suite.
No workflow is dispatched as part of this implementation pass.

## Deferred acceptance

See `handoff/M8_TEST_LATER.md`. The immutable M7 restore stays at
`3bb1e18170fc928f372f9cc72cc433d85c0666ca`. The latest recorded story proof is
Kids Class/PirateKey, not the ending. Historical 18-check local results belong
to their recorded earlier binaries; they do not certify these new sources.
No `M8_RESULT.md`, accepted `restore/recomp-m8`, or final public release is
created while these checks remain deferred.
