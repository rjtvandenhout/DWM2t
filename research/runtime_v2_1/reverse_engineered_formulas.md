# DWM2 Cobi USA: formulas recovered from runtime machine code

ROM SHA-256: `8e38a7420ef5239c7196aa4fd4b1499e65db2823e875bbf8241bb2199e766d4e`

This report is based on static disassembly of the user's clean USA Rev.00 Cobi ROM. It documents what the LR35902 code actually does, rather than relying on old FAQ folklore.

## 1. Natural level-up stat growth

For each of HP, MP, ATK, DEF, AGL and INT:

```text
base_gain = GrowthTable[species_growth_index][current_level]
```

The table has 32 growth curves, each with 99 one-byte entries. A level-up from level `L` to `L+1` reads entry `L`, which corresponds to `gain_on_level_entry = L+1` in `stat_growth_by_level.csv`.

There is no general read of the monster's `+` value in the natural-growth lookup. Therefore a high `+` does **not** directly increase ordinary level-up gains in this ROM.

The resulting stat is clamped to 999.

### Growth-ring exception

Accessory indices `0x1D..0x22` are the six growth rings, mapping in order to:

```text
0x1D War Ring    -> Max HP
0x1E Mage Ring   -> Max MP
0x1F Fight Ring  -> ATK
0x20 Sailor Ring -> DEF
0x21 Thief Ring  -> AGL
0x22 Cleric Ring -> INT
```

The ring computes an extra bonus from parity, not from the magnitude of `+`:

```text
p = monster_plus % 2
matches = count(x % 2 == p for x in [
    current_level, max_hp, max_mp, atk, def, agl, int, wld, name_length
])
ring_bonus = floor(matches / 2)
```

Only the stat selected by the equipped growth ring gets `ring_bonus` added to its normal table gain.

This means `+` can influence a growth-ring bonus through **even/odd parity**, but `+20` is not intrinsically stronger than `+2`, and `+21` is not intrinsically stronger than `+1` for this calculation.

## 2. Base newborn stats

For eight stored values (current HP, max HP, current MP, max MP, ATK, DEF, AGL, INT), the game first computes:

```text
N = floor((P1_corrected + P2_corrected) / 4)
```

For HP and MP the same inherited value is written to both current and maximum values.

### Equipped flat-stat accessories are normally removed first

Before inheritance, flat accessory bonuses are stripped from each parent if that accessory affects the stat being inherited. The code recognizes these bonus groups:

```text
HP  +30 / +80
MP  +30 / +80
ATK +10 / +50
DEF +10 / +50 / +5
AGL +10 / +50
INT +50 / +100
```

There is an important cap edge case: if the displayed parent stat is already `>=999`, the routine does **not** subtract the accessory bonus. This avoids subtracting from a capped value whose uncapped underlying value is unknown, but it also means a capped displayed 999 is inherited as 999.

## 3. Hidden newborn percentage bonus

After the `/4` calculation, the game builds a percentage `q`.

For finalized standard breeding, the components are:

```text
q = 3                                      # finalized breeding path
q += 5 if trait_pair_matrix_value == 0
q += 5 if BOTH parents are at max level
q += 2 if BOTH parent plus values >= 5 AND (p1_plus + p2_plus) is even
```

Then every one of the eight newborn stat values gets:

```text
final = min(999, N + ceil(N * q / 100))
```

So the old `(P1 + P2) / 4` rule is only the first stage.

For standard finalized breeding, `q` ranges from 3% to 15% depending on the parents. This explains level-1 offspring exceeding the old theoretical 499 ceiling from two displayed 999-stat parents.

Example with two 999-stat parents:

```text
N = floor((999 + 999) / 4) = 499
q = 7%  -> 499 + ceil(34.93) = 534
q = 12% -> 499 + ceil(59.88) = 559
q = 15% -> 499 + ceil(74.85) = 574
```

The internal 27x27 trait-pair matrix is exported in `personality_pair_matrix.csv`. Only matrix value `0` matters to this stat-bonus routine and contributes +5 percentage points. The other matrix values are preserved in the export but should not be given names without further evidence.

## 4. Child `+` value

On the finalized local breeding path, the base is the pedigree/base parent's `+` value. The mate's `+` is not directly added.

Then the game adds a level-sum bonus:

```text
sum(parent levels) < 40   -> +1
40..59                    -> +2
60..75                    -> +3
76..99                    -> +4
100+                       -> +5
```

Finally:

```text
child_plus = min(99, pedigree_plus + level_sum_bonus)
```

A separate non-final/preview path uses `max(parent1_plus, parent2_plus)` as its temporary base. Link mode also follows the pedigree/base-parent rule.

## 5. Maximum level

The actual ROM formula is:

```text
child_max_level = min(99, species_base_max_level + 3 * child_plus)
```

This is `+3 levels per plus`, not +2. The code loads literal `3` immediately before the multiplication helper.

## 6. Breeding modes

The breeding routine uses an internal mode byte. Caller and recipe-parser analysis identifies:

```text
0 = preview/query-style path
1 = finalized local breeding path
2 = link-cable breeding path
```

Mode 2 is especially strong evidence because only mode `2` is permitted to pass the `FB FB` link-only breeding delimiter documented in the breeding tables.

The finalized/nonzero path also supplies the +3 percentage-point newborn stat component described above.

## 7. Growth index 0

Growth index 0 is a real 99-entry curve, not a sentinel and not 'zero growth'. It is accessed by the exact same lookup as indices 1..31. There is no special-case branch for growth index 0 in the level-up routine.

See `stat_growth_by_level.csv` for every exact gain.

## 8. Correct active-record stat order

Runtime code confirms the active monster record uses:

```text
+63 ATK
+65 DEF
+67 AGL
+69 INT
```

Some old community documentation swaps the labels for +67 and +69. The level-up routine and core growth order make the ROM ordering unambiguous.

---

## Verification addendum (v2.1)

A second, internet-free byte-for-byte audit against the supplied ROM found no falsified core formula. Precision refinements:

- The +3 newborn percentage component is exactly conditional on `D7F1 != 0`; therefore both nonzero modes receive it.
- The trait-pair matrix's 52 zero-valued **ordered** CSV entries form 26 unique pairings because the matrix is symmetric.
- In the growth-ring name scan, `F0` terminates the scan; `8D` and `8E` are skipped.
- The runtime arithmetic proves that nonzero mode uses parent record 1's `+`; the phrase "pedigree/base parent" is a semantic caller-level label.
- Both identified callers of the natural level-up routine were checked. Their stat-application helpers apply `D095..D09A` directly and contain no later read of `+`, strengthening the conclusion that there is no hidden post-processing `+` growth bonus.

See `VERIFICATION_AUDIT.md` and `verify_against_rom.py`.
