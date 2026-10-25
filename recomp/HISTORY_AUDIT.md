# Native recomp repository audit

Audit date: 2026-10-16.

This file records repository-history details that matter when continuing the
static native recomp roadmap. It does not redefine any accepted milestone.

## Source of truth

The current roadmap and accepted restore-point table on
`recomp/native-pc` are the source of truth:

- `recomp/STATUS.md`
- `recomp/RESTORE_POINTS.md`
- `recomp/milestones/M*_RESULT.md`
- `recomp/handoff/M*_NEXT.md`

Restore branches are immutable historical recovery snapshots. Their bundled
status documentation may reflect the repository state at the instant the
snapshot was created and can therefore be stale relative to later milestones.
Do not rewrite or force-push a restore branch merely to refresh documentation.

## M5 history note

The M5 documentation work head
`33b76c5f65b44ca05cd12c2c9a0e2bc55a50d010` is not itself an ancestor of the
current promoted branch.

This is a history-shape issue, not a missing implementation issue. M5 was
promoted through commit `93c50f9ca1537c37578c7e7ea3e6afdb2627d9f0`, and the
promoted branch contains the same accepted M5 result and handoff content. No
functional M5 game code is missing from `recomp/native-pc`.

## M6 restore note

`restore/recomp-m6` points to
`70628e9a6f210f494ace326c51d1ac295a36c023`. It contains the passing M6
implementation plus its completion/handoff commit and has a successful Windows
CI record. Historical status/restore-list files inside that snapshot are not
used as the current roadmap.

## Native CI cold-build correction

The M6 promotion initially exposed a CI robustness bug on a cold cache. The
workflow first built only the discovery bank and then invoked the final target
with `/p:BuildProjectReferences=false`. That optimization assumes every
required static library already exists in the restored cache, so a clean runner
could fail at link time with:

`LNK1181: cannot open input file 'Release\\dwm2t_bank0.lib'`

The workflow now builds the ordinary `DWM2tRecomp` CMake target with project
references enabled. CMake/MSBuild therefore materialize Bank 0, the embedded ROM
image, every configured AOT ROMX dependency, the generated dispatch source, and
the executable on a cold runner. The build cache remains an optimization only,
never a correctness requirement.

## Continuation rule

Do not start M7 from an older work snapshot after this audit. The M7 work branch
must be based on the audited, green `recomp/native-pc` head before new battle,
audio, or save/continue changes are committed.
