# DWM2t

Matching decompilation and reverse-engineering workspace for the USA release of **Dragon Warrior Monsters 2: Cobi's Journey**.

## Target

This repository targets the user-provided clean dump with:

- Size: `4,194,304` bytes (`0x400000`)
- SHA-256: `8e38a7420ef5239c7196aa4fd4b1499e65db2823e875bbf8241bb2199e766d4e`
- SHA-1: `76901b7e5cadf9611dd4fac52e8501155c1e33a2`
- MD5: `f71ac6ac4bb335f59bfd2b594d47ab49`
- CRC32: `AB7BFDD5`

The original ROM is **not needed to build the checked-in source**.

## What is complete

The current source is a **100% byte-covering matching assembly baseline**:

- all 256 ROM banks are represented under `src/banks/`;
- all 4,194,304 target bytes are represented;
- the dependency-free Python rebuild matches every known target hash;
- RGBDS `rgbasm` + `rgblink` independently produce the same byte-identical ROM;
- GitHub Actions runs both verification paths on every source change.

That means the repository can already be edited, rebuilt and regression-tested without keeping a baserom in the repository.

## Native Windows player

The native Windows x64 recompilation has completed M8: all 256 ROM banks are
statically translated, and the original main story, complete credits, THE END,
ending Save and Continue pass native validation. The final package passes all
18 original native tests with zero skips and 21 actual launcher checks.

See the [native overview](recomp/README.md), [M8 completion record](recomp/milestones/M8_RESULT.md)
and [playthrough report with screenshots](recomp/handoff/M8_PROGRESS_2026-10-25.md).
`main` holds the current finished game; accepted M0–M8 snapshots remain in the
[immutable milestone branches](recomp/RESTORE_POINTS.md).

## What “decompilation” means here

Byte coverage and semantic understanding are different milestones.

Unknown regions remain honest raw `db` data. Verified systems are progressively lifted into named routines, structures, constants and tables while CI guarantees that no byte changes accidentally.

The current reverse-engineering dataset already covers monster records, growth/EXP tables, breeding, level-up behavior, resistance inheritance, personality logic, encounters, skills/items, sprites and overworld animation timing. See:

- `docs/SEMANTIC_DECOMP_ROADMAP.md`
- `symbols/known_regions.csv`
- `research/README.md`

## Build

Dependency-free verification:

```bash
make verify
```

Equivalent commands:

```bash
python tools/rebuild.py --out build/dwm2_cobi.gbc
python tools/verify.py build/dwm2_cobi.gbc
```

With RGBDS installed:

```bash
make rgbds
```

Do not run `rgbfix` when testing for an exact match. Header/checksum bytes are already represented in source.

To show project coverage:

```bash
make coverage
```

## Regenerating the raw baseline

Given your own matching cartridge dump:

```bash
python tools/decompile.py path/to/baserom.gbc
```

The generator refuses a non-matching ROM unless `--force` is explicitly supplied.

## Layout

- `src/main.asm` — RGBDS root.
- `src/banks/` — 256 byte-matching ROM-bank sources.
- `src/include/` — verified symbols/constants that emit no bytes.
- `symbols/` — machine-readable verified region map.
- `research/` — static extraction and runtime reverse-engineering evidence.
- `docs/` — project status, mechanics, sprite notes and semantic roadmap.
- `tools/decompile.py` — verified ROM → raw matching source.
- `tools/rebuild.py` — dependency-free source → ROM reconstruction.
- `tools/verify.py` — target hash validation.
- `tools/coverage.py` — coverage/status report.

## Contribution rule

A semantic rewrite is only accepted if the resulting ROM remains byte-identical. Guesses belong in notes, not in source labels.

## Copyright

This is a reverse-engineering research project. No license is asserted over the original game's program code, graphics, text, audio, characters or other copyrighted content. Users should obtain the original game data lawfully.
