# Semantic decompilation roadmap

The repository already has a **100% byte-matching assembly baseline**. Semantic decompilation means replacing raw `db` regions with named routines, tables, constants and structures while preserving the exact ROM hash.

## Acceptance rule

Every semantic change must pass both CI rebuilds:

1. `python tools/rebuild.py`
2. RGBDS `rgbasm` + `rgblink`

Both outputs must match:

`8e38a7420ef5239c7196aa4fd4b1499e65db2823e875bbf8241bb2199e766d4e`

## Verified regions ready for lifting

| System | File offset | Bank:address | Research |
|---|---:|---:|---|
| Breeding tables | `0x03A208` | `0E:6208` | `research/full_rom_read/` |
| Battle sprite far pointers | `0x010EAA` | `04:4EAA` | `research/sprites/` |
| EXP growth | `0x064E60` | `19:4E60` | `research/full_rom_read/` |
| Skill data | `0x0680D4` | `1A:40D4` | `research/full_rom_read/` |
| Skill requirements | `0x06900A` | `1A:500A` | `research/full_rom_read/` |
| Stat growth | `0x06A616` | `1A:6616` | `research/full_rom_read/` |
| Prebuilt enemies 1 | `0x0D0075` | `34:4075` | `research/full_rom_read/` |
| Core monster records | `0x0D4000` | `35:4000` | `research/full_rom_read/` |
| Overworld sprite pointers | `0x0E0001` | `38:4001` | `research/sprites/` |
| Prebuilt enemies 2 | `0x288056` | `A2:4056` | `research/full_rom_read/` |
| Critical attribute table | `0x28CB58` | `A3:4B58` | `research/full_rom_read/` |

## Runtime systems already reverse-engineered

The research tree contains verified work for:

- child starting-stat arithmetic and hidden breeding bonuses;
- child `+` and max-level calculation;
- normal level-up stat growth;
- Growth Ring behavior;
- resistance inheritance, equipment filtering and RNG;
- personality inheritance and hidden axes;
- personality pair bonus matrix;
- gender flag RNG;
- battle and overworld sprite decompression/layout;
- VBlank-driven overworld animation timing.

## Next code-lifting order

1. Bank 0 interrupt/VBlank and common utility routines.
2. Growth/EXP tables and their callers.
3. Core monster structure accessors.
4. Breeding result calculation and resistance inheritance.
5. Sprite decompressor and pointer tables.
6. Encounter/prebuilt-monster routines.
7. Skills/items/battle mechanics.
8. Remaining banks, text, maps, sound and UI.

The baseline deliberately keeps unknown bytes raw. We prefer an honest `db` block over a guessed function name.
