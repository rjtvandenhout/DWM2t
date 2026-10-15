# Native recomp restore points

These branches are intentionally immutable recovery points for major milestones.

| Restore branch | Commit | Meaning |
|---|---|---|
| `restore/recomp-m0` | `ac588dc73f59020efc69a53d17c46db6c7286acd` | first native EXE/static-recomp smoke pipeline |
| `restore/recomp-m1` | `68bf911c5845021db140575bdae721edda572965` | complete LR35902 frontend, Windows CI passing |
| `restore/recomp-m2` | created only after M2 Windows CI passes | complete fixed Bank 0 native translation |

## Recovery procedure

To inspect a restore point:

```bash
git fetch origin
git switch restore/recomp-m1
```

To restart development from one without rewriting the restore branch:

```bash
git switch -c recovery/my-work restore/recomp-m1
```

Do not force-push a restore branch. Create a new restore branch for later
milestones instead.
