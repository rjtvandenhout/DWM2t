# DWM2 Cobi Runtime Mechanics v3: Resistance + Personality (local-only verified)

This package was produced from the user's supplied **Dragon Warrior Monsters 2: Cobi's Journey (USA)** ROM and the locally generated v2.1 runtime package. **No internet source was used for this pass.**

## ROM identity

- Size: 4,194,304 bytes
- SHA-256: `8e38a7420ef5239c7196aa4fd4b1499e65db2823e875bbf8241bb2199e766d4e`
- SHA-1: `76901b7e5cadf9611dd4fac52e8501155c1e33a2`
- MD5: `f71ac6ac4bb335f59bfd2b594d47ab49`
- CRC32: `AB7BFDD5`

## Biggest findings

1. Resistance inheritance is now reconstructed down to its branch structure, equipment filter, child-plus multipliers and exact RNG state behavior.
2. The resistance RNG is **not uniform**. The small helper has only 55 distinct outputs (0..93) and the wide helper 86 (0..193), over a 128-state deterministic table cycle.
3. Therefore exact probabilities are multiples of 1/128 and differ from simple percentage approximations.
4. Personality breeding inherits four hidden temperament bytes, but an important correction was found: the game performs the parent addition in **8-bit A**, discards overflow, then shifts right. Exact formula: `(((p1+p2)&0xFF)>>1)`.
5. Displayed personality is a 3-axis base-3 encoding using record offsets +6F, +72, +70. The fourth byte +71 is hidden from the personality name but directly affects tactic-driven temperament changes.
6. The full four-axis tactic mutation tables and their row-selection rules are extracted.
7. The child gender flag has a special full-byte-zero branch: `D009 == 0` gives flag 0 without RNG. Otherwise low2 thresholds 0/10/50/90 use the same nonuniform RNG, yielding 3.125%, 12.5%, 54.6875%, and 96.09375% flag-1 chances.
8. A prior item-table parse was corrected: the table uses 13-byte records with a leading empty record.

## Files

- `RESISTANCE_INHERITANCE.md` - exact resistance algorithm.
- `PERSONALITY_INHERITANCE.md` - breeding and runtime temperament mechanics.
- `BREEDING_RNG.md` - exact 128-state RNG transform.
- `ADJACENT_FINDINGS.md` - gender roll, cape runtime, item parser correction.
- `resistance_inheritance_probabilities.csv` - exhaustive natural resistance x parent sum x plus probabilities.
- `resistance_rng_*_distribution.csv` and `rng_threshold_cdf.csv` - exact RNG distributions.
- `resistance_accessory_map.csv` - 1..27 anti-inheritance equipment mapping.
- `cape_resistance_runtime_rows.csv` - internal cape/equipment resistance increments.
- `personality_axis_grid.csv` - all 27 personality IDs as base-3 states.
- `personality_tactic_deltas.csv` - all four 8x4 tactic tables.
- `personality_inheritance_wrap_examples.csv` - examples exposing the 8-bit wrap.
- `child_gender_flag1_probabilities.csv` - exact flag probabilities.
- `verified_rom_slices.csv` - SHA-256 for every ROM slice used by this pass.
- `verify_v3_against_rom.py` - local repeatable verifier.
- `disasm_*.txt` - relevant instruction-level evidence.
- `MANIFEST_SHA256.txt` - hashes of all package files.
