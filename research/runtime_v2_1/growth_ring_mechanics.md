# Exact growth-ring bonus

The level-up code at Bank `1A:64A2` recognizes equipped accessory indices `0x1D` through `0x22`.

| Internal accessory | Ring | Stat |
|---:|---|---|
| 0x1D | War Ring | Max HP |
| 0x1E | Mage Ring | Max MP |
| 0x1F | Fight Ring | ATK |
| 0x20 | Sailor Ring | DEF |
| 0x21 | Thief Ring | AGL |
| 0x22 | Cleric Ring | INT |

Let `p = plus % 2`.

The game compares that parity with nine quantities:

1. current level
2. max HP
3. max MP
4. ATK
5. DEF
6. AGL
7. INT
8. WLD
9. visible name length

The name length is obtained from the ten-byte name field. `F0` terminates the scan; `8D` and `8E` are skipped and do not increase the count.

```text
matches = number of those 9 values whose parity equals p
ring_bonus = floor(matches / 2)
```

The selected stat's final level gain is:

```text
normal_table_gain + ring_bonus
```

before the normal 999 cap is applied.

Since there are nine parity checks, the ring bonus can range from 0 to 4 points on a level-up.
