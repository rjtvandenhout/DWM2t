# M8 checkpoint handoff and safe resume

This tooling change is based on `work/recomp-m8` at
`80d37f2f51038d295ef9c5cf03545dbb0565b26e`. It does not prove a new world,
a new Windows build, or M8 completion. No ROM bytes, game rules, native
acceptance constants, controller fixtures, restore branches or existing
saves are changed.

## Accepted checkpoint and scope

`M8_WORKING.md` records the original Kids Class victory and PirateKey prize.
The terminal Journal must match SHA256:

```text
A48FB7B52D6B5063F03725D205F96964174B44AFBB3600782892BA44CAEAA91A
```

The accepted M7 restore remains `3bb1e18170fc928f372f9cc72cc433d85c0666ca`.
The documented complete build has 255 ROMX banks plus Bank 0. Static coverage
is not proof of later-world or ending playability. Do not create an M8 result
or restore point until the original full playthrough and final gates pass.

## Behavior

`tools/test_m8_oasis.py` preserves the existing thirteen native commands and
their order. Feeding remains a side branch from story-05; audio remains a side
branch from story-08. Neither side branch replaces the main story seed.

Each new evidence directory receives `handoff.json`, recording the executable,
fixtures and save paths, sizes and SHA256 values. A failed process, missing or
truncated save, or changed input prevents a complete handoff. Older evidence
is not deleted. The report covers the checkpoint chain only, not the entire
CTest suite or physical audio output. It is an integrity record, not a signed
attestation; simulated test files are never accepted as gameplay evidence.

`tools/m8_handoff.py` requires a completed chain ending at the exact Kids Class
fixture and Journal. A limited-build or earlier-world report is rejected.
The executable must match the binary recorded by that successful chain;
a relocated byte-identical executable can be supplied with `--exe`.
Every session receives its own `play.sav` in a new directory. The original
checkpoint is never passed to the game as a writable play save.

## Validation and hosted workflow

On 2026-10-22, all 39 offline Python contracts passed locally without skips.
A differential check against fetched baseline blob
`29d82439ea3f3f4ee63f65a7d9ee557f8dc18653` preserved all thirteen native
commands and their seed relationships. These checks use simulated subprocesses
and explicitly synthetic files: they do not validate native gameplay.

The cleaned Actions workflow removes automatic obsolete M7 scans and the
unsafe cached-library shortcut. It checks tooling before building all ROMX
banks and running the retained native development suite. CMake still verifies
the complete dependency graph. Diagnostics and skipped-test results are kept;
a hosted audio skip is not physical output acceptance.

The optional cleanup runs only when requested by the workflow input or a
`[clean-actions]` commit marker. It considers completed failed/cancelled runs
older than one day, deleting at most 100 runs with no job steps or artifacts.
Successful runs, restore branches, each branch's newest run, and runs with
unknown evidence are retained. The cleanup audit is uploaded separately.
No cleanup is claimed unless the job actually executes successfully.

Run tooling contracts directly:

```powershell
python recomp/tools/test_m8_handoff.py
```

To generate a real handoff, run the complete-AOT development suite:

```powershell
ctest --test-dir recomp/build-all --parallel 4 --output-on-failure
```

Use `DWM2T_ALL_ROMX=ON` and verify that the extended Kids Class route is selected.
Never substitute a current user save for the acceptance output. Take the exact
manifest path printed by `M8_CHECKPOINT_HANDOFF`, not a guessed newest folder:

```powershell
python recomp/tools/m8_handoff.py --manifest "PATH_FROM_SUCCESSFUL_RUN/handoff.json" --verify-only
python recomp/tools/m8_handoff.py --manifest "PATH_FROM_SUCCESSFUL_RUN/handoff.json" --mode play
```

`--mode probe` starts the existing P1-only discovery interface from the copied
Journal. `--session-root` selects a directory for fresh sessions. Keep referenced
fixtures and evidence intact. The next gameplay work is the original Magic
Door/PirateKey route; this patch invents no controller route or game state.
