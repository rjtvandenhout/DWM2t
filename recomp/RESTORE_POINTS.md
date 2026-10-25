# Native recomp restore points

These branches are immutable recovery points for accepted native-recomp milestones.

`main` contains the current finished game and subsequent maintenance. The
`restore/recomp-m0` through `restore/recomp-m8` branches retain the accepted
milestones at the exact commits below. Development and probe branches are
temporary; retire them after their work is integrated or audited as superseded.

| Restore branch | Commit | Meaning |
|---|---|---|
| `restore/recomp-m0` | `ac588dc73f59020efc69a53d17c46db6c7286acd` | first native EXE/static-recomp smoke pipeline |
| `restore/recomp-m1` | `68bf911c5845021db140575bdae721edda572965` | complete LR35902 frontend |
| `restore/recomp-m2` | `e68bd3e1136f93982a33d755d20bd3b093a6f7b5` | complete fixed Bank 0 native translation |
| `restore/recomp-m3` | `8ec0c1e80b5cea3df8f9581d1424fae319ec67d6` | headless mapped hardware runtime |
| `restore/recomp-m4` | `29c4c8249f5a77a17ea8194d624d20af52da3e6b` | deterministic CGB renderer + Win32 presentation |
| `restore/recomp-m5` | `9d0b9830ea6542def717a8cde726691cd0421cc2` | original DWM2 title screen through native recompiled game code |
| `restore/recomp-m6` | `70628e9a6f210f494ace326c51d1ac295a36c023` | live P1 input, real ship-map movement, Win32 loop and 32 KiB SRAM persistence |
| `restore/recomp-m7` | `3bb1e18170fc928f372f9cc72cc433d85c0666ca` | real P1 battle/player attack, original timed audio, Journal Save and fresh-runtime Continue; all twelve gates pass locally |
| `restore/recomp-m8` | `e44b41394c23f63f55b6d5255bc065696ba554c2` | complete 256-bank native Windows player; original main story/credits/ending Save, all 18 native tests with zero skips, 38 story checkpoints and verified package |

See [M8 completion](milestones/M8_RESULT.md), [current status](STATUS.md),
[playing and recovery](handoff/M8_NEXT.md), and the
[branch cleanup record](handoff/BRANCH_CLEANUP_2026-10-25.md).

## Recovery procedure

Inspect the latest accepted milestone without modifying it:

```bash
git fetch origin
git switch --detach origin/restore/recomp-m8
```

Start new recovery work from it:

```bash
git switch -c recovery/my-work origin/restore/recomp-m8
```

Never force-push a restore branch. Later milestones receive a new
`restore/recomp-mN` branch instead.
