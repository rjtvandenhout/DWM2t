# Adjacent verified findings

## Child gender flag roll

Routine: `0E:61C1`, physical `0x3A1C1`.

The child species data supplies byte `D009`. There is an important first branch: if the **entire byte is zero**, the routine writes child byte `CADE = 0` immediately and consumes no RNG. If `D009 != 0`, its low two bits select thresholds `[0, 10, 50, 90]`. The game then calls the same nonuniform small RNG used by resistance inheritance and sets `CADE` to 1 when `threshold >= random_return`.

For nonzero `D009`, the actual flag-1 probabilities are:

- low2 = 0, threshold 0: 4/128 = 3.125%
- low2 = 1, threshold 10: 16/128 = 12.5%
- low2 = 2, threshold 50: 70/128 = 54.6875%
- low2 = 3, threshold 90: 123/128 = 96.09375%

For `D009 == 0` exactly, flag-1 probability is 0%.

This report deliberately calls it `gender flag 1`; the static routine proves the probability and written flag but does not by itself prove which human label (male/female) corresponds to 1.

## Battle resistance equipment/cape routine

At physical `0x64605`, internal effect codes 13..19 select seven 16-byte rows beginning at `0x64641`. Each row contains signed negative offsets terminated by `0x80`. Every listed resistance is incremented by one, capped at resistance 3.

The battle-copy pointer is positioned immediately after the 27 resistance bytes, so the signed offsets can be translated directly into resistance indices. The exact mapping is in `cape_resistance_runtime_rows.csv`.

The ROM-local item string table contains MagicCape, DracoCape, SilvrCape, GoldCape, PltnmCape, OrcaCape and BraveCape, but this audit does not claim a name-to-internal-code pairing until the item-to-equipment-code conversion itself is traced end-to-end.

## Item data parser correction

While following personality items, a previous static item export was found to have the wrong record width. The item table at physical `0x58CC2` has a leading empty record and then 13-byte records, not 15-byte records.

Thus item-name index N maps to item-data record N+1 in this table. The six personality book records are exported in `personality_book_item_records_corrected.csv`. Their effect subcodes are consecutive `0x1B..0x20`.

This is an adjacent data-layout correction; exact semantic assignment of those six subcodes to Axis A/B/C increase/decrease still requires following the item-dispatch path farther than the breeding/tactic mechanics needed here. The ROM-local text strongly gives the six intended pairs, but this package separates text inference from proven write targets.
