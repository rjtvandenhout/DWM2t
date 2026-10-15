# DWM2 Cobi Runtime Mechanics v2.1 - independent local verification

This audit was performed **without internet sources**. It checks the v2 runtime package directly against the supplied Cobi's Journey ROM.

## Source identity

Expected/embedded ROM SHA-256:

`8e38a7420ef5239c7196aa4fd4b1499e65db2823e875bbf8241bb2199e766d4e`

Actual supplied ROM SHA-256:

`8e38a7420ef5239c7196aa4fd4b1499e65db2823e875bbf8241bb2199e766d4e`

Result: **PASS**. Size: 4,194,304 bytes.

Additional locally calculated hashes:

- MD5: `f71ac6ac4bb335f59bfd2b594d47ab49`
- SHA-1: `76901b7e5cadf9611dd4fac52e8501155c1e33a2`
- CRC32: `AB7BFDD5`

These hashes are reported only as local identity checks in this audit. No online comparison was performed.

## Package integrity

The original v2 ZIP passes its own `MANIFEST_SHA256.txt` for every listed payload file. ZIP CRC testing reports no corrupt member.

Original v2 ZIP SHA-256:

`8c2d560321c857197064a493871d1a8797c7ada887f4a184c18fb838545958cd`

## Byte-for-byte runtime evidence

Every line in the three disassembly evidence files that includes a physical ROM address and raw opcode/data bytes was compared to the supplied ROM:

- `annotated_breeding_disassembly.txt`: 519 / 519 lines match
- `annotated_levelup_disassembly.txt`: 283 / 283 lines match
- `breeding_mode_disassembly.txt`: 131 / 131 lines match
- Total: **933 / 933 exact matches**

No opcode-byte mismatch was found.

## Extracted-table verification

- Stat growth: **3,168 / 3,168** CSV values match bytes in the ROM.
- EXP growth: **3,168 / 3,168** 24-bit CSV values match bytes in the ROM.
- Personality/trait pair matrix: **729 / 729** decoded entries reproduce the packed ROM matrix exactly.
- Matrix value `0`: 52 ordered entries. The matrix is symmetric and has no zero diagonal, so this is **26 distinct unordered parent pairings**.

## Runtime formula conclusions

### Natural level-up stats: CONFIRMED

The runtime calculates each base gain as:

`GrowthTable[growth_index][current_level]`

The first stored byte of each 99-byte curve corresponds to table index 0. The ordinary level-up path reads index `current_level`; for a normal level 1 -> 2 level-up it therefore reads the second stored byte. The first byte is zero for all 32 curves.

No general `+` multiplier or `+` bonus exists in this calculation. I additionally checked the two identified runtime callers of Bank 1A:`6418`: both subsequently apply the six values in `D095..D09A` directly to the monster's stats. Their add helpers contain no read of the monster's `+` value. This strengthens the conclusion that `+` does not secretly get added after the growth routine returns.

### Growth-ring bonus: CONFIRMED

Accessory indices `1D..22` select HP, MP, ATK, DEF, AGL and INT respectively. If one is equipped, the code compares the parity of the monster's `+` value with nine quantities:

current level, max HP, max MP, ATK, DEF, AGL, INT, WLD, and counted name length.

`bonus = floor(parity_matches / 2)`, therefore 0..4.

Precision note: byte `F0` **terminates** the ten-byte name scan. Bytes `8D` and `8E` are skipped and do not increase the count.

The ring **names** in the package are labels carried into the report; the runtime section itself proves the accessory indices and stat mapping, not the English item-name strings.

### Newborn base stats: CONFIRMED

For each inherited stat value:

`N = floor((P1_corrected + P2_corrected) / 4)`

HP and MP are each calculated once per parent source field and written to both current and maximum newborn values.

Flat stat accessories recognized by the correction routine are subtracted before inheritance when the displayed stat is below 999. If a displayed parent stat is already 999 or higher, the routine intentionally skips subtraction.

### Hidden newborn percentage: CONFIRMED, wording tightened

The exact runtime accumulator is:

- +5 if packed parent trait-pair matrix value == 0
- +5 if parent 1 current level == max level **and** parent 2 current level == max level
- +2 if both parent `+` values are at least 5 and their sum is even
- +3 if internal breeding mode byte `D7F1 != 0`

The last condition is literally **nonzero mode**, not specifically a check for `mode == 1`. Thus modes 1 and 2 both receive the +3 component.

For every newborn stat:

`final = min(999, N + ceil(N * q / 100))`

The multiply/divide helper was re-read independently. The division routine returns quotient in HL and remainder in A; the caller increments HL when A is nonzero, which proves round-up/ceiling behavior.

For nonzero mode the possible percentage total is 3..15%.

### 999 + 999 example: CONFIRMED

`N = floor(1998 / 4) = 499`

- q=7 -> 534
- q=12 -> 559
- q=15 -> 574

The v2 test vectors are arithmetically correct.

### Child `+`: CONFIRMED, semantic label qualified

The machine code proves:

- if `D7F1 != 0`, base `+` comes from parent record 1 (`C9F3`)
- if `D7F1 == 0`, base `+` is `max(parent1_plus, parent2_plus)`
- add +1/+2/+3/+4/+5 for level-sum thresholds <40 / 40..59 / 60..75 / 76..99 / >=100
- cap at 99

Calling parent record 1 the "pedigree/base parent" is a semantic interpretation of the surrounding breeding flow, not something encoded as a textual label in this arithmetic routine.

### Maximum level: CONFIRMED

`max_level = min(99, species_base_max_level + 3 * child_plus)`

Literal multiplier `03` appears immediately before the multiply helper.

### Breeding modes: arithmetic behavior CONFIRMED; UI labels are interpretations

The code definitely distinguishes mode 0, mode 1 and mode 2. Mode 2 uniquely passes two special recipe delimiters in the parser. Mode 1 and mode 2 are both nonzero for the +3 newborn-stat component and both use parent-record-1 `+` as the child-plus base. Mode 0 uses max(parent pluses) and does not get the +3 component.

The labels "preview/query", "finalized local", and "link-cable" are based on surrounding caller behavior. They are useful labels, but are conceptually one step less direct than the arithmetic conclusions above.

### Active stat order: CONFIRMED

The runtime walks the active record as:

- +5D max HP
- +61 max MP
- +63 ATK
- +65 DEF
- +67 AGL
- +69 INT

Therefore +67 = AGL and +69 = INT is confirmed.

## Corrections/clarifications versus v2 wording

No core formula from v2 was falsified. Three wording refinements are warranted:

1. The +3 newborn bonus is exactly `D7F1 != 0`, so it also applies to mode 2, not merely a mode-1 "standard finalized" path.
2. The 52 matrix-zero entries are ordered CSV entries but represent 26 unique pairings because the matrix is symmetric.
3. In the name-length scan, `F0` terminates the scan; `8D` and `8E` are the bytes that are skipped from the count.

Everything else listed above survived the local ROM re-check.

## Useful runtime-range SHA-256 fingerprints

These allow later work to detect accidental ROM/version drift without relying on filenames:

- newborn core `0x398B1..0x399E0`: `e88083888946d7faf40751579b3a025c25625aac0c4e35d9a656836889960cbb`
- hidden newborn bonus `0x39EE8..0x3A03E`: `762abd573bbbe9be939b3cd8e45bb09a3356cbb60fa7c9cff92ac5a487d9df8c`
- trait matrix `0x3A03F..0x3A116`: `624ef39806f3090a26cceff39ed1c5960697bbb54206195258bc8fce7b30c3fb`
- level-up block `0x6A418..0x6A615`: `362fa9408464d5eb3037d501adb8b51262f45db4e5d6cb46d8712cf2b74bec99`
- stat growth tables `0x6A616..0x6B275`: `c9c52632077a5629b5e8cb2d393f6213d82a0a37cc434ff45c6179933c75f95c`
