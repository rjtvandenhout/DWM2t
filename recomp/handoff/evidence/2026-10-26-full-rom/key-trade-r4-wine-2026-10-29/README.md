# Original local-link key trade observation

On 2026-10-29 the R4 production candidate from Actions run `40806942912` ran under Wine with two independent copies of the genuine QuietSea-clear Journal. The EXE identified game source `1351bcd058e491455a477045a2ff86bbc3bd7b1c`, SHA-256 `63bf283dfeb7543c82d2787221788ab71e8651130b0a829b8987b368864a6f95`. The untouched seed Journal SHA-256 was `91b3690b8e7acee6a55118152497f0d57245236bce7c62d1b537ec0486180054`. No saves or executables are included here.

Using original controller input, both players chose QuietSea from the original key-trade menu and confirmed the exchange and record prompt. The game displayed that the keys would be traded and returned both players to the title menu. Both actual resulting Journals opened in fresh processes at the original QuietSea cave; the linked and both fresh processes exited with code 0. Their complete 40 monster records, party bytes and 107 quest bytes matched the input Journal after Continue.

The recorded Journal changes included moving the key record and seed from slot 3 to slot 6 and clearing five world-cache bytes in each of the working and backup cache copies. The exact before/after byte offsets and hashes are in [key-trade-observation.json](key-trade-observation.json). The original-ROM static trace below accounts for these changes; they have **not been compared with an independent original-ROM emulator**. Both players began with copies of the same key and seed (`0x16c0`); no distinct generated world, counterpart version or Tara exchange is claimed. The fresh Windows acceptance is separate.

## Original-ROM trace of the changed key and cache

The following is a static analysis of original guest instructions, not an emulator run or a recorded dynamic instruction trace. Addresses are Game Boy bank and CPU address, with banks in hexadecimal.

- Original [bank $1B:$5E85–$5E95](../../../../../src/banks/bank_027.asm) obtains the selected key index and calls [bank $12:$69B0](../../../../../src/banks/bank_018.asm). That routine invalidates the selected cached world's marker and compacts the subsequent four-byte key records and two-byte seeds. Bank $1B:$5E96–$5F06 scans for the first empty key slot and copies the received record and seed into it. In the saved observation, indices 4–6 shifted to 3–5 and the incoming record and seed occupied index 6, exactly matching this ordering.
- For a received cached key, bank $1B:$5F1D–$5F5C calls $5FD4 on the received 405-byte cache before selecting a free cache slot with [bank $60:$6C61](../../../../../src/banks/bank_096.asm) and writing the cache to cartridge RAM. The helper at bank $1B:$5FD4 clears bit 7 at buffer offset $001 and zeroes offsets $178, $17C, $180 and $184. Independently comparing all 405 bytes of each player's working and backup saved cache with the input gives an exact match to those five transformations, corresponding to saved offsets $4001/$4178/$417C/$4180/$4184 and $6001/$6178/$617C/$6180/$6184.
- Bank $1B:$5F75–$5F7C preserves only the incoming key's bit 7 and ORs in the newly allocated cache index. With the observed input and allocation this accounts for the key's first byte changing from $C0 to $80: the world-completed bit is cleared while the cached-world flag remains set. The exchanged seed remains $16C0.

This trace supports the specific observed slot and cache transition from the original cartridge code. It does not establish that every key exchange, different seed, counterpart version or host hardware behavior is correct.

The event logs are preserved as captured. The exploratory helper reused its `manual-19` screenshot label for a later read-only capture; both earlier screenshots were retained under `action-19` in the original scratch output, and the curated returned-title screenshots are from the later capture. The scripts refer to local paths and include no save data.

- [Original key chooser](key-chooser-player1.bmp)
- Proposed QuietSea exchange: [player 1](proposed-quietsea-player1.bmp), [player 2](proposed-quietsea-player2.bmp)
- [Original record prompt](record-result-player1.bmp) and [trade message](keys-now-traded-player2.bmp)
- Returned title menus: [player 1](returned-title-player1.bmp), [player 2](returned-title-player2.bmp)
- Fresh Continue in QuietSea: [player 1](fresh-quietsea-player1.bmp), [player 2](fresh-quietsea-player2.bmp)

Receipt SHA-256: `ab177ccd6766fe7ca5f055c6d987e445d281f5eb5ad3f8bc44554eae6ddd0da1`.
