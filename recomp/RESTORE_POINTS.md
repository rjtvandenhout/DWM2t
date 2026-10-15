# Native recomp restore points

These branches are immutable recovery points for accepted native-recomp milestones.

| Restore branch | Commit | Meaning |
|---|---|---|
| `restore/recomp-m0` | `ac588dc73f59020efc69a53d17c46db6c7286acd` | first native EXE/static-recomp smoke pipeline |
| `restore/recomp-m1` | `68bf911c5845021db140575bdae721edda572965` | complete LR35902 frontend |
| `restore/recomp-m2` | `e68bd3e1136f93982a33d755d20bd3b093a6f7b5` | complete fixed Bank 0 native translation |
| `restore/recomp-m3` | `8ec0c1e80b5cea3df8f9581d1424fae319ec67d6` | headless mapped hardware runtime |
| `restore/recomp-m4` | `29c4c8249f5a77a17ea8194d624d20af52da3e6b` | deterministic CGB renderer + Win32 presentation |
| `restore/recomp-m5` | `9d0b9830ea6542def717a8cde726691cd0421cc2` | original DWM2 title screen reached through native recompiled game code |

## Recovery procedure

Inspect a restore point:

```bash
git fetch origin
git switch restore/recomp-m5
```

Start new recovery work without modifying the restore branch:

```bash
git switch -c recovery/my-work restore/recomp-m5
```

Never force-push a restore branch. Later milestones receive a new
`restore/recomp-mN` branch instead.
