# DWM2 Cobi Runtime Mechanics v2.1 (verified)

This package is the runtime-code follow-up to the earlier full static ROM read. It does **not** contain the ROM.

## Main discoveries

- Natural stat gains are deterministic table lookups. High `+` does not directly increase ordinary gains.
- Growth index 0 is an ordinary curve, with no special-case branch.
- Growth rings add 0..4 points using a hidden parity algorithm.
- Newborn stats start with `floor((parent1 + parent2) / 4)` after correcting most equipped flat-stat accessories.
- A previously undocumented hidden percentage stage then adds 3..15% on finalized standard breeding, rounded **up** per stat.
- The hidden percentage stage explains level-1 offspring above the supposed 499 inheritance ceiling.
- Child plus uses the pedigree/base parent's plus plus a +1..+5 parent-level-sum bonus, capped at +99.
- Maximum level is `base_max + 3 * plus`, capped at 99.
- Link-cable mode is identified directly from the `FB FB` link-only recipe delimiter behavior.
- Runtime code confirms active-record offsets +67 = AGL and +69 = INT.

## Files

- `reverse_engineered_formulas.md` — clean formulas and conclusions
- `annotated_breeding_disassembly.txt` — opcode-level evidence
- `annotated_levelup_disassembly.txt` — opcode-level evidence
- `breeding_mode_disassembly.txt` — link-mode parser evidence
- `breeding_modes.md` — mode interpretation
- `growth_ring_mechanics.md` — exact ring algorithm
- `personality_pair_matrix.csv` — all 729 ordered parent-pair entries
- `personality_pairs_getting_5pct.csv` — the 52 ordered pairs that trigger the hidden +5 percentage points
- `personality_pair_matrix_grid.csv` — human-readable 27x27 matrix
- `stat_growth_by_level.csv`, `exp_growth_by_level.csv` — copied from v1 for convenience
- `source_offsets.csv` — key ROM addresses
- `dwm2_formula_calculator.py` — standalone implementation of recovered formulas
- `MANIFEST_SHA256.txt` — package file hashes

ROM analyzed: Cobi's Journey USA Rev.00, SHA-256 `8e38a7420ef5239c7196aa4fd4b1499e65db2823e875bbf8241bb2199e766d4e`.


## v2.1 verification

A second local, internet-free audit compared the package back to the supplied ROM. See `VERIFICATION_AUDIT.md`. The core formulas survived; wording was tightened around nonzero breeding mode, matrix symmetry, and the name-length terminator. A standalone `verify_against_rom.py` is included.
