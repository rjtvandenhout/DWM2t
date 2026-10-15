# Verified ROM map highlights

All offsets below are file offsets in the 4 MiB target ROM unless noted otherwise.

| Area | Offset / region | Notes |
|---|---:|---|
| EXP growth tables | `0x064E60` | 32 growth curves × 99 levels, 24-bit values |
| Skill data | `0x0680D4` area | skill/effect data |
| Skill requirements | `0x06900A` | level/stat/prerequisite requirements |
| Stat growth tables | `0x06A616` | 32 growth curves × 99 levels |
| Core monster data | `0x0D4000–0x0D7FFF` | species records, growth indices, resistances, etc. |
| Prebuilt enemy block 1 | `0x0D0075` area | fixed enemy/NPC monster records |
| Prebuilt enemy block 2 | `0x288056` area | additional prebuilt records |
| Hidden crit attribute table | `0x28CB58` | species values 0..3 |
| Breeding tables | `0x03A208+` | species/family breeding recipes |
| Battle sprite far pointers | `0x010EAA` | 3-byte far pointers per core monster |
| Overworld sprite far pointers | `0x0E0001` | 3-byte far pointers to compressed overworld sprite sets |

See `research/` for the full CSV exports and verification notes.
