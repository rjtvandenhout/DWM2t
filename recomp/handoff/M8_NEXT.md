# M8 accepted player and recovery handoff

The original main campaign is complete and M8 is accepted on 2026-10-25.
[Completion record, source identities and screenshots](../milestones/M8_RESULT.md).
[Successful validation/download](https://github.com/rjtvandenhout/DWM2t/actions/runs/40183484388).

## Play

Extract the entire `DWM2t-M8-VERIFIED-3d573873ae81.zip` into a new directory.
Run `DWM2t-M8/Play.cmd`. Its SHA256 is
`2e002da616fa5692ba56ba5b91a1d6ace0049fb596fe6b25d56c65fae200e02e`.
Local delivery is under `outputs/`, with a matching `.sha256` sidecar.
Actions artifacts have 30-day retention; keep a downloaded package.

Arrow keys are the D-pad; Z is A, X is B, Enter is Start and Backspace is
Select. Open the field menu with A facing empty space, then use PLAN > Journal
and finish the original confirmation. Closing the window flushes SRAM; use
the original Journal to record progress.

Saves and pre-launch backups are outside the package under
`%LOCALAPPDATA%\DWM2t\saves\`. Logs are under `%LOCALAPPDATA%\DWM2t\logs\`.
The launcher checks file integrity, uses separate profiles and retains backups.
Default volume is 5%; `Play.cmd -Volume 1` selects 1%.

## Original ending Save

The separate delivered Journal is
`outputs/M8-ending-3d573873ae81/ending_complete.sav`: exactly 32,768 bytes,
SHA256 `0649c4ef78867d2e55f352ddb0fea811fea6e3cf7407f8451220cc2bf01df95d`.
It preserves all 17 monsters and all 107 quest bytes, ending flag 0x25,
Garon/Slash/Derzo 40/37/40, full HP 220/180/207, and 11G.

From the extracted package, import the downloaded file into a **new** profile:

```bat
Play.cmd -Profile m8_ending -ImportSave "C:\path\to\ending_complete.sav"
```

The source is copied and an existing profile is refused. The player package
contains no user/test Saves and never searches for old files automatically.

## Reproduce or continue development

Accepted game/build source is `3d573873ae8122cbb10fcd5d0f7ae7a33a7609ba`;
accepted validation tools are `8859ef67289ce90712a44b9c17174de4519a59b3`.
The immutable recovery branch is `restore/recomp-m8`. M7 remains unchanged at
`3bb1e18170fc928f372f9cc72cc433d85c0666ca`.

Full validation is manual:

```sh
gh workflow run recomp-player-validation.yml --ref restore/recomp-m8 -f validation_mode=fresh-campaign
```

It builds new independent diagnostic/production binaries, retains the original
suite, plays the original campaign and gates the final package. Optional
`story_journals_base64` supplies the pinned genuine Journal bundle for four
workers; an empty input retains serial replay. The build-run diagnostic
artifact contains that bundle and its reported SHA256. Every child input
must still match its actual newly replayed parent output.

`finish-fresh-build` can finish the same exact archived build on a suitable
Windows audio host without recompiling its game. It reruns all 18 original
tests from the archived source, preserves initial XML as unaccepted, checks
both source archives and exact EXEs, and records the actual separate runs.
Its final Play.cmd and ending GUI gates remain mandatory. The CI-only signed
audio-driver helper refuses to run outside GitHub Windows CI.

Newly built packages remain `UNTESTED_CANDIDATE` until their required evidence
passes. Preserve failures, original Journals and the M7/M8 recovery branches.
Main-story acceptance does not exhaustively cover optional postgame paths.
CI tests real WinMM streaming through a virtual endpoint; physical audibility
is not measured. Optional enhancements can proceed as separate work.
