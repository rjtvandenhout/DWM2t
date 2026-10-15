# Runtime mechanics confirmed from the target ROM

## Normal level-up growth

Normal level-up gains index the species growth table directly. The monster `+` value is not a generic stat-growth multiplier.

## Child starting stats

```text
N = floor((Parent1CorrectedStat + Parent2CorrectedStat) / 4)
Final = min(999, N + ceil(N * q / 100))
```

The hidden `q` bonus can include personality-pair, both-parents-at-max-level, parent-plus parity/threshold, and finalized-breeding-mode bonuses.

## Max level

```text
MaxLevel = min(99, SpeciesBaseMaxLevel + 3 * Plus)
```

## Resistance inheritance

Resistance inheritance uses the child's natural resistance, the sum of effective parent resistances, child `+`, and non-uniform RNG tables. Equipment-granted resistance is explicitly filtered in relevant cases.

## Personality inheritance

Hidden temperament axes are averaged with 8-bit wraparound before shift/division. The visible personality is derived from three ternary-classified axes; a fourth hidden axis participates in other runtime behavior.
