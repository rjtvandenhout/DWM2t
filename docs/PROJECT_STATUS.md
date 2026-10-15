# Project status

## Matching coverage

- ROM bytes represented in source: **4,194,304 / 4,194,304 (100%)**
- ROM banks represented: **256 / 256**
- Baseline bank size: **16 KiB**
- Target hash verification: **enabled**
- Original ROM required to rebuild current source: **no**

## Semantic decompilation

The repository starts from a byte-perfect matching baseline. Raw `db` regions are intentionally converted to semantic assembly/data structures incrementally. A region is only accepted when the resulting build remains byte-identical.

Already reverse-engineered areas from the current research set include core monster records, growth tables, breeding, runtime stat arithmetic, resistance inheritance, personality inheritance, enemy/encounter data, skill/item records, battle sprites, overworld sprites, and VBlank-driven animation timing.

The next phase is replacing matching raw bytes for known regions with labels, structs, constants and routines directly in `src/`.
