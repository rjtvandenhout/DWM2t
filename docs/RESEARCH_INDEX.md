# Reverse-engineering research index

This directory indexes the ROM-derived research that accompanies the byte-matching source tree.

All results target the same verified USA Cobi's Journey ROM:

```text
SHA-256  8e38a7420ef5239c7196aa4fd4b1499e65db2823e875bbf8241bb2199e766d4e
Size     4,194,304 bytes
```

## `research/full_rom_read/`

Static extraction of major ROM data structures. This includes:

- core monster records and defined-monster tables;
- monster, skill and prebuilt-enemy names;
- complete stat-growth and EXP-growth tables;
- breeding tables in all discovered combinations;
- item records and string pointers;
- skill records and skill requirements;
- encounter/prebuilt-enemy records;
- library metadata, Magic Key thresholds and personality data;
- hidden critical-hit species attributes;
- ROM-map/mechanics offsets.

Start with `research/full_rom_read/README_FULL_READ.md`.

## `research/runtime_v2_1/`

Verified runtime-code analysis for level-up and breeding mechanics. It contains:

- newborn stat arithmetic;
- hidden breeding percentage bonuses;
- child-plus and max-level behavior;
- normal stat-growth runtime flow;
- Growth Ring mechanics;
- breeding-mode analysis;
- personality-pair matrix;
- source-offset map and a verification audit.

Start with `research/runtime_v2_1/VERIFICATION_AUDIT.md` and
`research/runtime_v2_1/reverse_engineered_formulas.md`.

## `research/runtime_v3/`

Verified resistance/personality runtime analysis:

- resistance inheritance probabilities;
- resistance RNG distributions and guarantee thresholds;
- equipment/accessory resistance filtering;
- personality-axis inheritance and 8-bit wraparound;
- tactic/personality deltas;
- child-gender flag probabilities;
- verified ROM slices used by the analysis.

Start with `research/runtime_v3/RESISTANCE_INHERITANCE.md` and
`research/runtime_v3/PERSONALITY_INHERITANCE.md`.

## `research/sprites/`

Battle and overworld sprite reverse engineering:

- battle-sprite pointer/decompression metadata;
- overworld sprite pointer/decompression/frame metadata;
- extracted frame manifests;
- labelled/clean overview PNGs;
- reusable extraction script under `research/sprites/tools/`;
- verification notes.

Start with `research/sprites/README.md`.

## Source-of-truth rule

Research notes explain meaning; `src/` is the byte-matching source of truth. When a
raw `db` region is converted to semantic labels/instructions/data definitions, the
change is only accepted if both the Python rebuild and RGBDS rebuild still reproduce
the exact target ROM hash.
