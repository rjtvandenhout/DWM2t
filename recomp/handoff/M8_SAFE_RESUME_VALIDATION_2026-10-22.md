# M8 safe-resume publication and validation - 2026-10-22

## Published changes

Active branch: `work/recomp-m8`.

- Workflow cleanup: `895df6e1587e5058e94d69cae7a2afa9d6c20d04`.
- Safe-resume implementation and contracts: `be60b9b812a53ad68511006ac4ced16dba4b365e`.
- Starting baseline: `80d37f2f51038d295ef9c5cf03545dbb0565b26e`.

The two implementation commits change only the active Actions workflow,
three Python tooling files and English handoff documentation. Original game
code, ROM banks, controller fixtures, acceptance constants and saves are
unchanged. The accepted `restore/recomp-m7` was checked remotely and remains
`3bb1e18170fc928f372f9cc72cc433d85c0666ca`.

The workflow no longer runs obsolete M7 ROM scans on each active-branch push.
It no longer bypasses native dependency checks with BuildProjectReferences=false.
It requests all 255 ROMX banks, retains the Kids Class development route, and
runs tooling checks before the native Windows suite. New comments, documentation,
commit messages and workflow labels are English.

## Local checks actually executed

- All 39 Python handoff contract tests pass without skips, including a second
  run after publication against files matching the committed Git blobs.
- Differential comparison against the fetched baseline driver preserves all
  thirteen ordered native commands and their main/side-branch seed relationships.
- YAML/static workflow checks pass.
- The exact cleanup JavaScript passes a simulated thirteen-run policy check:
  only three empty obsolete runs are selected. Successful, current, newest,
  recent, active, restore, artifact-bearing and started/unknown-step runs are
  preserved. This simulation makes no remote deletions.
- All five locally checked source/document files match their published Git
  blob hashes exactly.

These contracts use synthetic files and simulated subprocesses. They are not
native game execution, a Windows build, or new gameplay acceptance.

## Hosted validation actually requested

GitHub Actions run: `39822793568`, attempt 1, for implementation `be60b9b`.
Requested at 2026-10-22 17:27:07 UTC; ended in failure at 17:27:12 UTC.

Raw job results:

- `119978165489`, Clean Actions and validate M8 tooling: failure,
  `runner_id=0`, empty runner name, `steps=[]`.
- `119978203700`, Complete AOT build and retained M1-M8 development tests:
  skipped, no runner, `steps=[]`.

No runner executed the cleanup or tooling steps, and the dependent Windows
build/test did not run. Therefore obsolete run-history deletion is NOT complete,
no native test pass is claimed, and no new executable is published.
The earlier project record documents quota exhaustion, but this run's available
job data does not independently establish its underlying pre-run failure cause.
No billing or account settings were changed. No repeated automatic reruns or
background monitoring were scheduled.

## Remaining gate

Restore hosted runner availability, then rerun the failed workflow at `be60b9b`
or explicitly dispatch the current workflow with `clean_empty_runs=true`.
Verify the cleanup audit and actual native test results, including any audio
skips, before reporting hosted success. The existing local Windows validation
path remains available in the project. M8 full-game acceptance remains open.
