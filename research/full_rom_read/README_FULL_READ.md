# Dragon Warrior Monsters 2: Cobi's Journey — Full Mechanics/Data ROM Read

This package was extracted directly from the supplied USA ROM. The original ROM is intentionally **not** included in this package.

## ROM identity

- Size: 4,194,304 bytes (4 MiB)
- MD5: `f71ac6ac4bb335f59bfd2b594d47ab49`
- SHA-1: `76901b7e5cadf9611dd4fac52e8501155c1e33a2`
- SHA-256: `8e38a7420ef5239c7196aa4fd4b1499e65db2823e875bbf8241bb2199e766d4e`
- CRC32: `AB7BFDD5`
- Header checksum: stored `E7`, calculated `E7` -> True
- Global checksum: stored `859E`, calculated `859E` -> True
- Header ROM-size code: 0x07 = 4,194,304 bytes
- Header RAM-size code: 0x03 = 32,768 bytes

## Major direct findings

1. **Stat growth really is 32 fixed lookup curves x 99 levels.** The table at `0x6A616` is dumped both per-level and summarized. Growth index 0 is not a zero-growth curve. It contributes 49 table points across levels 1–99. Growth index 17 gives +8 at level 45, matching old reverse-engineering notes.
2. **EXP is 32 x 99 24-bit little-endian table values** at `0x64E60`. All 32 extracted curves are monotonic. `exp_growth_by_level.csv` includes both stored values and simple differences between adjacent rows.
3. **Core species data is fully decoded for all 384 core-ID slots.** 323 slots point to defined structures and 61 point to the shared empty structure. The 47-byte record includes family, gender ratio, flags, recruitment rate, base max level, EXP growth, 3 skills, 6 stat-growth indexes, 27 resistances and base EXP yield.
4. **Critical attributes were located in this ROM at `0x28CB58`.** This was found by searching for the independently documented critical-value signature of the first Slime-family species. The signature occurs exactly once. `critical_attributes.csv` exposes the table by core ID. This table is separate from the 47-byte core structure, explaining the long-standing unknown noted by modders.
5. **Prebuilt enemies are fully decoded as 768 records.** IDs 0–624 are in the first block at `0xD0075`; IDs 625–767 continue at `0x288056`. Their 768-name pointer table begins at `0x22001C`, with strings at `0x22061C`.
6. **Breeding tables are preserved byte-perfectly and decoded where the encoding is established.** Species+species, family+species and family+family are exported as decoded tables. Species+family uses a compact one-byte family/control encoding, so that region is exported losslessly plus a per-species raw-pointer view rather than assigning speculative meanings to its control bytes. In this exact ROM the family+family pointer table begins at `0x3BE83`, and its 11x11 result matrix begins at `0x3BE99`.
7. **Items are decoded as 111 15-byte records** beginning at `0x58CC2`, including purchase price, target/icon fields, effect-related bytes and the two numeric effect variables used by healing/meat-style items.
8. **Skills and skill requirements are dumped for the full 223-ID pointer range.** Skill data is treated as 17-byte records at `0x680D4`; requirement records are 18 bytes at `0x6900A`. Empty/duplicate internal skill IDs are preserved rather than silently discarded.
9. **Random encounters for the documented main-world areas are decoded** into screen-level pointers, selection thresholds and prebuilt enemy IDs/names.
10. **Magic-key prefix and suffix thresholds and exact accepted-roll bins are extracted from the original selector.** Prefix rows use 16 bytes; suffix rows use 60 bytes (56 names plus four padding bytes). The selector accepts the first threshold greater than or equal to a roll in 0–99; prefix zero entries are skipped. `accepted_roll_count` records the exact selector bins, while `threshold_delta_from_previous` is only a threshold difference. These bins do not establish the distribution or correlations of all original PRNG seeds. The 2026-10-25 audit corrected 487 suffix thresholds that had been read using an incorrect 56-byte row stride and recovered the previously omitted suffix labels from the ROM.
11. **Personality command-effect tables are extracted** from the four 32-byte blocks and represented as signed 8x4 rows. Their exact semantic mapping to hidden traits still needs execution tracing.

## Files

- `core_monsters.csv` / `defined_monsters.csv` — species mechanics
- `monster_names.csv`, `families.csv` — universal species/family names
- `stat_growth_by_level.csv`, `stat_growth_summary.csv` — all 32 stat curves
- `exp_growth_by_level.csv`, `exp_growth_summary.csv` — all 32 EXP curves
- `skills_data.csv`, `skill_requirements.csv`, `skill_names.csv` — skills
- `items_data.csv`, `item_string_pointer_table.csv` — items
- `critical_attributes.csv` — hidden species critical attribute
- `prebuilt_enemies.csv`, `prebuilt_enemy_names.csv` — fixed enemies/gifts/boss building blocks
- `breeding_*.csv` / `breeding_*_raw.bin` — breeding recipes and lossless raw breeding regions
- `library_metadata.csv` — library size/rarity and displayed breeding references
- `random_encounters.csv` — fixed encounter tables
- `magic_key_*_thresholds.csv` — original key-generation thresholds, names and accepted-roll bins; reproduce with `python3 recomp/tools/inspect_magic_keys.py --output /tmp/new-magic-key-tables` or verify with `python3 recomp/tools/inspect_magic_keys.py --check` from the repository root.
- `items_data.csv` — lossless original 13-byte records for runtime IDs 0–98, including empty record 0; original name pointers and independent shop resale lookups are retained. The old 15-byte export overran the table and used name indices as runtime IDs. Unknown bytes now have neutral names; the raw word at bytes 1–2 is not presented as a universal shop purchase price. Reproduce with `python3 recomp/tools/inspect_items.py --output /tmp/new-item-records` or verify with `python3 recomp/tools/inspect_items.py --check`.
- `personality_command_effect_tables.csv` — hidden personality command effects
- `rom_map_mechanics.csv` — mechanics-oriented offset map
- raw `.bin` blocks — known but not yet semantically decoded structures preserved byte-perfectly for the next pass

## What is *not* honestly solved by a static table dump

A 4 MiB Game Boy ROM cannot be truthfully called “fully understood” just because every known table was copied. The remaining high-value unknowns are **runtime code paths**: the exact newborn-stat arithmetic, exact `+` effect on level-up gains, max-level calculation edge cases, resistance-inheritance RNG/math, some skill flags, item effect flags, arena-team substructure and the exact personality-trait update semantics. These require control-flow disassembly and/or emulator breakpoints rather than more table extraction.

The package therefore labels decoded, raw-preserved and unresolved material separately instead of inventing meanings for unknown bytes.

## Important correction from this pass

The public wiki notes that family IDs in Species + Family are not inherently two bytes. This exact ROM confirms that its mate lists are compact byte streams. I therefore removed the earlier empty/incorrect two-byte decode and replaced it with `breeding_species_plus_family_raw.csv` plus the exact raw binary block. No family-control byte is given a guessed meaning.
