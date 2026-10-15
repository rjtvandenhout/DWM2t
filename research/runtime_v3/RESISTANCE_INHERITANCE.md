# Resistance inheritance: exact runtime behavior

All statements in this file come from the supplied Cobi's Journey ROM and the local runtime disassembly. No internet source was used for this verification.

## Data locations

- Parent 1 resistance array: `C9F9`, 27 bytes.
- Parent 2 resistance array: `CA9E`, 27 bytes.
- Child resistance array: `CB43`, 27 bytes.
- Child `+`: `CB3D`.
- Natural child species resistances are loaded into `D01A..D034`.
- Main inheritance routine: bank `0E`, CPU `5CB2`, physical `0x39CB2`.

For every one of the 27 resistance slots the routine starts from the child's natural resistance `R0` in the range 0..3.

## Parent resistance filter

Before adding the two parent resistances, the game calls `0E:5DCD` for each parent.

If a parent's current value is not 2, that value is returned normally.

If the value is exactly 2, the game checks the parent's byte at resistance-array base + `0x31`, corresponding to monster-record offset `+0xA4`. Values 1..27 are translated through the 27-byte table at physical `0x39E02`. If that accessory/effect code maps to the resistance slot currently being inherited, the helper returns `0xFF` and the entire inheritance attempt for that slot is aborted.

This is a very specific anti-accessory inheritance rule: a matching equipment-derived `2` is not accepted as hereditary resistance.

## Parent sum gate

After filtering, let `S = parent1 + parent2`.

- Natural `R0 = 3`: never upgraded; remains 3.
- Natural `R0 = 2`: needs `S >= 5` to enter an upgrade path.
- Natural `R0 = 0 or 1`: needs `S >= 3`.
- Child `+ = 0`: no inheritance upgrade even when the parent sum qualifies.

## Upgrade paths for natural 0 or 1

The exact paths are:

- `S = 3`: one attempt with factor 1.
- `S = 4`: one attempt with factor 3.
- `S = 5`: one attempt with factor 10. Only if it succeeds, a second attempt with factor 3 occurs. This can yield +0, +1, or +2 resistance.
- `S = 6`: +1 is unconditional, then one attempt with factor 5. This yields at least +1 and can yield +2.

A general attempt computes `T = child_plus * factor`.

- If `T >= 100`, it succeeds immediately without consuming RNG.
- Otherwise the small resistance RNG is called and the attempt succeeds when `T >= random_return`.

Final resistance is still masked to the low two bits when stored.

## Upgrade paths for natural 2

- `S < 5`: no change.
- `S = 5`: special wide-RNG check. It succeeds when `child_plus >= wide_random_return`.
- `S = 6`: normal factor-2 check.

There is a `cp $01` instruction at `0E:5D90` on the S=5 path while A still contains the parent sum. In the normal path A is 5 there, so this branch cannot fire. It behaves like dead/leftover code and does not alter normal S=5 behavior.

## The RNG is not uniform 0-99 / 0-199

This is the biggest correction to simplified descriptions of the mechanic.

The core RNG (`00:095B`) advances a 7-bit state and selects one of 128 unique bytes from a fixed ROM table. `0E:611B` transforms that byte and integer-divides a constructed 16-bit value by 41.

With mask `0x0F`, the helper returns only 55 distinct values in the range 0..93. With mask `0x1F`, it returns 86 distinct values in the range 0..193. The values are not equally frequent.

Therefore all exact inheritance probabilities are quantized in steps of 1/128, and two-stage S=5 probabilities must preserve sequential RNG state rather than multiply two independent percentages.

See `resistance_inheritance_probabilities.csv`, `resistance_rng_small_distribution.csv`, `resistance_rng_wide_distribution.csv`, and `rng_threshold_cdf.csv` for the exhaustive numbers.

## Guaranteed thresholds using the actual small RNG

Because the small helper's maximum return is 93, practical 100% thresholds can occur before the code's explicit `T >= 100` shortcut:

- factor 1: `+93`
- factor 2: `+47`
- factor 3: `+31`
- factor 5: `+19`
- factor 10: `+10` (the explicit >=100 shortcut fires here)

For the special wide S=5 path on a natural resistance 2, even `+99` is not guaranteed because the wide helper reaches 193.
