# M8 deferred validation handoff (historical)

M8 is now accepted; all deferred work below has been completed within the later
whole-game authorization. See [M8_RESULT.md](../milestones/M8_RESULT.md) and
[M8_NEXT.md](M8_NEXT.md). The earlier deferral is preserved as history.

> Historical deferral: the user's later whole-game continuation and finish
> requests authorize the validation work below. Current progress and remaining
> acceptance work are in [M8_PROGRESS_2026-10-25.md](M8_PROGRESS_2026-10-25.md).

The user explicitly deferred testing on 2026-10-22. Do not automatically run
these steps merely to build the release candidate. No build or test result
is recorded for the new player/save-hardening implementation.

## Preserved baseline

- M7 restore: `3bb1e18170fc928f372f9cc72cc433d85c0666ca` (do not move).
- Before this pass: `602681ffb3ecba799939265f008a90d7207bb4fd`.
- Latest recorded original progression: Oasis and Kids Class completed;
  PirateKey earned. Later worlds and ending/credits are unproven.
- Earlier M8 fixtures, constants and test-command sequence are unchanged.
- Safe-resume tooling remains separate; its prior 39 simulated-process
  checks were not gameplay validation. No new test pass is implied.

## First validation session, only when authorized

1. Build the new player via `recomp/Build-Candidate.ps1`; preserve its exact
   commit, EXE/ZIP hashes, build report and isolated source snapshot.
2. Build the diagnostic executable from the SAME commit in a NEW directory
   with full AOT and testing enabled, then run the retained suite. Do not reuse
   or overwrite a prior validation directory or any user's current save.

   ```powershell
   cmake -S recomp -B recomp/build/validation-NEW -A x64 -DDWM2T_ALL_ROMX=ON -DBUILD_TESTING=ON -DDWM2T_OUTPUT_NAME=DWM2tRecompValidation
   cmake --build recomp/build/validation-NEW --config Release --target DWM2tRecomp --parallel 2
   python recomp/tools/test_m8_handoff.py
   ctest --test-dir recomp/build/validation-NEW -C Release --parallel 4 --output-on-failure --output-junit native-results.xml
   ```

   Replace `validation-NEW` with an unused directory. Ninja requires the x64
   developer environment and `-G Ninja -DCMAKE_BUILD_TYPE=Release`, not `-A`.
   Developer gates exercise shared code; they do not alone validate the new
   production entry point. Preserve failures/skips instead of calling them green.
3. Independently exercise the copied production package: direct no-argument
   start, help/version, Unicode/space-containing paths, separate profiles,
   import into a new profile, refusal to overwrite an existing profile,
   checksum mismatch, native duplicate-instance lock, window/input/audio,
   exit logging, original Journal and fresh Continue.
4. Validate persistence failures: short/oversized save, symlink/directory,
   read-only destination, denied replacement, interrupted temporary write,
   pre-existing temporary file and failed flush. Verify previous-save
   preservation, unchanged SRAM format, pending dirty flag and recoverable
   pre-launch backups. Include the POSIX helper on a suitable host separately.
5. Resume original gameplay from a COPY of the recorded Kids Class Journal;
   preserve its source/hash. Record later worlds, major bosses and ending/
   credits using original controller input, not patched flags or RAM states.
   Pin later original Journal/fresh-Continue and relevant battle/audio evidence.
   Observe the user's milestone-pause rule during future gameplay unless they
   explicitly change it. This code-only pass did not advance story progression.
6. Re-run all retained/new gates against the final exact source and packaged
   binary. Only then document M8 acceptance and create its immutable restore
   and final package. Never promote an `UNTESTED_CANDIDATE` by renaming alone.

## Infrastructure distinction

The build-only candidate workflow is manual and independent of the existing
Actions cleanup/test job. No hosted runner result is claimed here. Historical
empty-run deletion was previously blocked; this pass does not claim those
runs have now been deleted. Keep successful runs and milestone artifacts.
