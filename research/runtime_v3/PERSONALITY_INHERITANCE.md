# Personality / temperament inheritance: exact runtime behavior

## Four hidden temperament bytes

The breeding records contain four adjacent hidden temperament bytes:

- Parent 1: `C9F5..C9F8`, monster-record offsets `+0x6F..+0x72`.
- Parent 2: `CA9A..CA9D`.
- Child: `CB3F..CB42`.

The breeding routine is at physical `0x39910`.

## Important correction: the average is 8-bit and can wrap

For each of the four bytes the actual LR35902 operations are:

`A = parent2_byte`
`A = A + parent1_byte`  (8-bit ADD; overflow carry is discarded)
`A = A >> 1`            (`SRL`, not rotate-through-carry)

Therefore the exact formula is:

`child_trait = (((parent1_trait + parent2_trait) & 0xFF) >> 1)`

It is NOT a normal wide-integer `floor((p1+p2)/2)` when the sum exceeds 255.

Example: 200 + 200 = 400 mathematically, but the byte addition wraps to 144, and the child receives 72.

This also means a newly bred child's four trait bytes are always in 0..127 before any later runtime changes.

See `personality_inheritance_wrap_examples.csv`.

## Displayed personality uses only three of the four bytes

The personality encoder at physical `0x39FF9` reads the monster-record offsets in this order:

1. `+0x6F` with weight 9
2. `+0x72` with weight 3
3. `+0x70` with weight 1

Offset `+0x71` is not used to select the displayed personality name.

Each used byte is converted to a base-3 digit:

- 192..255 -> digit 0
- 64..191 -> digit 1
- 0..63 -> digit 2

Then:

`personality_id = digit(+6F)*9 + digit(+72)*3 + digit(+70)`

This produces IDs 0..26. `personality_axis_grid.csv` maps all 27 IDs to the ROM-local personality names.

Because a freshly bred child starts with each inherited byte <=127, its initial post-breeding digits can only be 1 or 2. Runtime actions/items can subsequently move the bytes across the 192 threshold.

## Runtime battle copies

Battle setup maps the four record bytes to working RAM in this order:

- record `+0x6F` -> `D968` (Axis A)
- record `+0x70` -> `D978` (Axis C)
- record `+0x71` -> `D980` (Axis D, hidden from the displayed personality ID)
- record `+0x72` -> `D970` (Axis B)

The runtime personality encoder independently reproduces the same A/B/C base-3 calculation.

## Tactic-driven changes

The routine at physical `0xC12B5` applies signed, saturating 0..255 changes to all four working temperament axes.

The low two bits of `DA43[monster]` select one of four 8x4 delta tables. The row is selected by two conditions:

- `D8B7[monster]` gives row band 0,1,2,3 using thresholds 10,20,30.
- if hidden Axis D (`D980[monster]`) is at least 151, add 4 to the row number.

The exact raw signed tables are in `personality_tactic_deltas.csv`.

There is an additional bit-6 transformation on the full tactic byte:

1. If bit 6 is set, all four table deltas are negated while copied to the temporary delta buffer.
2. Then the one delta selected by `DAE8` is negated a second time, restoring that selected delta to its table sign while the other three remain reversed.
3. The four deltas are applied with saturation at 0 and 255.

This is exact code behavior. The semantic meaning of `DAE8` and the human-facing label for the bit-6 state are not proven solely by this local static trace, so this package does not invent names for them.

## Personality-pair breeding matrix

The previously verified 27x27 pair matrix remains included. Matrix value zero is the condition used by the hidden newborn-stat routine to add +5 percentage points to the baby's starting-stat bonus. There are 52 ordered zero cells, corresponding to 26 unique symmetric pairs.
