# Reverse-engineering research index

Everything here was generated or verified against the target Cobi ROM named in the repository root.

- **`full_rom_read/`**: static tables, monster records, skills, items, encounters, breeding tables and ROM-map exports.
- **`runtime_v2_1/`**: verified level-up, breeding-stat, `+`, max-level and Growth Ring mechanics.
- **`runtime_v3/`**: resistance inheritance, personality inheritance, RNG distributions and adjacent breeding behavior.
- **`sprites/`**: battle/overworld sprite pointer maps, decompression tooling, frame metadata and atlas previews.

Research is evidence for semantic source lifting. When a researched region is converted into named assembly, the resulting ROM must remain byte-identical in CI.
