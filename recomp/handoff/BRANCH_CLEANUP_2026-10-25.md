# Recomp branch cleanup — 2026-10-25

Status: audit complete; canonical-main integration and exact-ref retirement are
pending. The final application receipt will record actual branch/cache changes.

The maintained layout is `main` plus immutable `restore/recomp-m0` through
`restore/recomp-m8`. Main receives the accepted M8 history and maintenance;
all nine milestone commits remain unchanged. [Milestone index](../RESTORE_POINTS.md).
The verified Windows player, original ending Save, game source, ROM banks,
controller fixtures and golden values remain unchanged while the user tests.

## Audit and recovery

The initial remote contains 36 branches. Of 26 noncanonical refs, 14 are already
reachable, one has equivalent retained M5 documentation and 11 are superseded
experiments. No useful unique product work needs integration. All bootstrap
and research branches are actual ancestors of accepted M8. The old gate-scan
scripts' five source-bank matches are covered by the retained parameterized
scanner; obsolete probe implementations are not merged into the game.

37 experimental commits sit outside retained history. Before any retirement,
a complete 43-ref, prerequisite-free Git bundle was created and verified:
`/workspace/branch-cleanup-2026-10-25/pre-cleanup.bundle` (6,990,792 bytes).
SHA256: `346e531eea00de6ecd5890d3afda4abadd93933a8dd4cc86b0e845f7aa74d7ba`.
The bundle stays outside Git and preserves all original remote/local heads.

[Detailed content/history audit](evidence/2026-10-25-branch-cleanup/branch-audit.json),
[original remote refs](evidence/2026-10-25-branch-cleanup/remote-heads-before.txt),
[bundle refs](evidence/2026-10-25-branch-cleanup/bundle-heads.txt), and
[guarded application plan](evidence/2026-10-25-branch-cleanup/cleanup-plan.json).

To recover an archived experiment into a new branch:

```sh
git fetch /path/to/pre-cleanup.bundle refs/remotes/origin/work/recomp-m7-battle-gate-scan:refs/heads/recovery/old-probe
```

## Reviewed refs for retirement

These are the audited pre-cleanup tips. The live deletion operation must lease
its exact current tips; the M8 PR head may advance only by the reviewed cleanup
commit that is first preserved on main. Deletion is atomic and excludes every
restore ref and main.

| Branch | Audited original commit | Classification |
| --- | --- | --- |
| `archive/recomp-m5-attempt1` | `2fe6a0a3b3bf8d1a0c18130f20f43c33351b9331` | Superseded experiment; archived |
| `bootstrap-full-decomp` | `513d05cd7bfdfa5d99a33d0939cebff435529c51` | Already in retained history |
| `bootstrap-upload` | `9785ce52d6d46b27370ae9adf7d91bc23787bed0` | Already in retained history |
| `bootstrap/full-decomp` | `48474472c6f2ed37a2e77315b1dd46ec68d8f8ce` | Already in retained history |
| `recomp/native-pc` | `4996ea8753077786abe77c5d0673bbc325d6c40d` | Already in retained history |
| `research-upload` | `cc0cfd82946b6b11ac0b456494468d14ce1cc839` | Already in retained history |
| `work/recomp-m2` | `e68bd3e1136f93982a33d755d20bd3b093a6f7b5` | Already in retained history |
| `work/recomp-m3` | `1036a43d24f46d01e3feebbe7ab15ecc4c2e4396` | Already in retained history |
| `work/recomp-m4` | `66d6743a04411b5a142e2c3538b1261b2da31bb9` | Already in retained history |
| `work/recomp-m5` | `33b76c5f65b44ca05cd12c2c9a0e2bc55a50d010` | Equivalent retained documentation |
| `work/recomp-m6` | `70628e9a6f210f494ace326c51d1ac295a36c023` | Already in retained history |
| `work/recomp-m7` | `bc79ec91342031451103145e4fd830d9b7fe00dd` | Already in retained history |
| `work/recomp-m7-battle-flag2-route` | `ab5835169f6419ee902cf1983df21b7eb40b788a` | Superseded experiment; archived |
| `work/recomp-m7-battle-flag4-seed` | `88f30f349867e56ee1b3144d6df1a17f44aa2e44` | Superseded experiment; archived |
| `work/recomp-m7-battle-gate-scan` | `84205b5061300898e66fd43e8843954685b7716d` | Superseded experiment; archived |
| `work/recomp-m7-battle-post-slash` | `1688e900a055961db9a4f88a4429ee0b26bcdf9e` | Superseded experiment; archived |
| `work/recomp-m7-battle-pump-seed` | `fba06a038451477a92e86b92a23bf17a501ee937` | Superseded experiment; archived |
| `work/recomp-m7-battle-selector09` | `20ff816fa5164d4eeb611bd688bd71d3a2ecc850` | Superseded experiment; archived |
| `work/recomp-m7-probe` | `0372efdd818b2378ba87b03db8592c0eadfed318` | Superseded experiment; archived |
| `work/recomp-m7-save-probe` | `0cff0bd40d925097fd5dc5c35a24686b863312ee` | Superseded experiment; archived |
| `work/recomp-m8` | `0e59dbd19415cce58393c21c2ede2acd6f60c4d3` | Already in retained history |
| `work/recomp-m8-audio-host-probe-20261025` | `17daad09c676abfce0f8d38a97754f7c5804cb9a` | Superseded experiment; archived |
| `work/recomp-m8-dancer-20261023` | `e44b41394c23f63f55b6d5255bc065696ba554c2` | Already in retained history |
| `work/recomp-m8-pirate-validation-20261022` | `8fc6e64cca83fd63a99f8b3544e3992c304d25cd` | Already in retained history |
| `work/recomp-m8-recheck-20261022` | `bfc591146659964740f6958add5f8e8b8ed14d5f` | Already in retained history |
| `work/recomp-m8-world-validation` | `4d5f07f61ff5606d26a645d25f6f030d0c5ee34d` | Superseded experiment; archived |

## Recomp and CI maintenance

- Update stale current status and the restore index through M8. Historical
  milestone evidence and accepted hashes remain intact.
- Replace the former cached full-build workflow with quick Linux/Windows
  tooling and filesystem contracts on main/PRs. Heavy full-campaign validation
  and build-only candidates remain manual.
- Retire duplicate pinned historical workflows from main; their source remains
  in the immutable M8 snapshot and full-history backup. Keep every fresh native,
  campaign, persistence, production and final-package acceptance gate.
- Use explicit source/run inputs for completing an archived fresh build, and
  support both direct and namespaced producer-job names.
- Retire audited local aliases/worktrees after integration. The old 437,842,443-byte
  cache tied to `work/recomp-m8` is rebuildable and unused by the maintained
  workflows; its actual deletion, if applied, belongs in the receipt.

No full game replay is implied by housekeeping checks. The existing M8 accepted
run remains [40183484388](https://github.com/rjtvandenhout/DWM2t/actions/runs/40183484388);
[its completion record](../milestones/M8_RESULT.md) identifies the unchanged
player and actual original-game proof.
