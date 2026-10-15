# Breeding RNG helper

Core RNG routine: physical `0x095B`.

It increments `C5E8`, masks it to 7 bits, and indexes the 128-byte table at `0x0973`. The table contains 128 unique byte values, so across a full state cycle every table byte occurs exactly once.

Resistance/gender transform: `0E:611B`, physical `0x3A11B`.

For selected RNG byte `x` and caller mask `B`:

`low = x`
`high = ((2*x) & 0xFF) & B`
`n = (high << 8) | low`
`return floor(n / 41)`

The carry entering `RL A` is zero on this call path: the core RNG's `AND $7F` clears carry and the subsequent address addition cannot carry for a 0..127 table index.

Masks used here:

- `B=0x0F`: small helper, result 0..93, 55 distinct values.
- `B=0x1F`: wide helper, result 0..193, 86 distinct values.

The exact frequency distributions and cumulative threshold probabilities are exported as CSV.
