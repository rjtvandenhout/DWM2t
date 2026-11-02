# Original local trade of different random keys — 2026-11-02

Under Wine, the actual verified production executable (game source `1351bcd058e491455a477045a2ff86bbc3bd7b1c`, executable SHA-256 `63bf283dfeb7543c82d2787221788ab71e8651130b0a829b8987b368864a6f95`) ran with two independently copied genuine Journals. Player 1 had cleared QuietSea (seed `0x16c0`, seed Journal SHA-256 `91b3690b8e7acee6a55118152497f0d57245236bce7c62d1b537ec0486180054`). Player 2 had earned and originally appraised FirstField (seed `0x1927`, Journal SHA-256 `67f0ccce0a65951e8dbab96d24e9f753a5c9cf916ca89340afec84da7fe4c7cf`). The latter was earned by original C-class input, appraised and saved using original game interactions. Only original P1 input was supplied; no game memory or original saves were modified.

The two players selected [QuietSea](quietsea-selected.bmp) and [FirstField](firstfield-selected.bmp). Each original trade screen displayed [the other player's key](player1-sees-firstfield.bmp) ([player 2](player2-sees-quietsea.bmp)); both confirmed the original record prompt and transaction. Both returned to their original title menus and the linked process exited 0.

Both actual resulting Journals were separately loaded with original Continue in fresh processes and reached their [expected original locations](fresh-player1.bmp) ([player 2](fresh-player2.bmp)); both fresh processes exited 0. Player 1's Journal retained the received FirstField record `00041408` and seed bytes `2719`, while player 2 retained QuietSea `80071308` and seed bytes `c016`. All 17 and 11 respectively owned 165-byte monster records and each player's 107 quest bytes matched their own original Journal. The key record difference includes the original cartridge's cache handling; these checks do not independently prove every generated world.

The [receipt](receipt.json) includes exact Journal hashes, record/seed observations and SHA-256 values of the captured screenshots, raw reports and input event logs. The scripts refer to their original scratch paths; no saves or binaries are included. This is one different-key exchange between two Cobi instances, not a Tara counterpart or physical link-cable claim.

The unmodified `fresh-report.json` was emitted by a helper originally written
for VS battles. Its generic `fresh_process_reload` and
`serial_protocol_success_verified` fields remain `false`; they are not set by
this key-trade helper and must not be read as successful VS or generic serial
certification. The separate `fresh_continue` events, actual independently loaded
Journals, received key records, original locations and exit codes substantiate
the two fresh Continues described above. The raw report is preserved unchanged.
