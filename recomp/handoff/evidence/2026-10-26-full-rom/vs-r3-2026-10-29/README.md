# Original two-player VS repeat, R3 production candidate

This curated subset records a GUI run on Wine on 2026-10-29 of the production candidate from Actions run `40799717118`, artifact `12867312469`. The candidate identified source `1351bcd058e491455a477045a2ff86bbc3bd7b1c`; its executable SHA-256 was `829e95842cea5a0cc9d13f601ae89b814c4fd2109ca08065bf50a9d944378ec1`. Each player started with an independent copy of the genuine ending Journal, SHA-256 `0649c4ef78867d2e55f352ddb0fea811fea6e3cf7407f8451220cc2bf01df95d`. No Journal files are included here.

The unmodified receipt `original-vs-repeat.json` records the original D3 handshake, party exchange, a no-wager Free Battle, a consistent three-turn loss for player 1 and win for player 2, both postmatch menus, normal linked shutdown, and a fresh Continue of each actual postmatch Journal. Both saves were byte-identical to the original after fresh Continue. The test used original game input, did not reset the saves, and made no game-memory edits. It covers this linked battle and persistence path, not every feature of the game.

Eight unmodified BMP captures show the rules handshake, player 1's selected team and No wager, battle start, both outcomes, the returned menu, and both fresh Continues with the original party and 11G. Their hashes match the receipt. The receipt is preserved verbatim: its Windows paths identify the original run and do not imply the executable, saves, or every listed screenshot are present in this curated directory. The complete scratch run is `/workspace/scratch/full-rom-2026-10-26/original-vs-link-r3-1351-02`; an earlier attempt at `-01` ended after a battle because the helper acknowledged the result before its text finished typing. The successful run used `/workspace/scratch/full-rom-2026-10-26/original-vs-link-repeat-stable-07/repeat_vs_probe.py` with a fully drawn-message check.

Receipt SHA-256: `de91bf26517e925203508635348bbb11e4bf976aafe11d3d03381ac9026da945`.

## Captures

- [Link rules](original-D3-rules-menu-player1.bmp)
- [Team selection and no wager](correct-three-members-prize-default-No-player1.bmp)
- [Battle start](actual-linked-battle-start-player1.bmp)
- [Player 1 result](turn3-consistent-loss-player1.bmp) and [player 2 result](turn3-consistent-win-player2.bmp)
- [Postmatch menu](original-postmatch-menu-player1.bmp)
- Fresh Continue: [player 1](actual-full-party-and-11G-player1.bmp) and [player 2](actual-full-party-and-11G-player2.bmp)
