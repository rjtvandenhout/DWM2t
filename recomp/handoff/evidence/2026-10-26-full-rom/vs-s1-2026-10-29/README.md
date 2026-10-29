# Original two-player VS repeat, 2026-10-29

This is a curated subset of an actual GUI run of the production candidate on Wine. The candidate identified source `1351bcd058e491455a477045a2ff86bbc3bd7b1c` and its executable SHA-256 was `11a23469d25fb17f2edabd5298c57356a0d33b3f5a0281c35d91e352eda13225`. Both players began with independent copies of the genuine ending Journal, SHA-256 `0649c4ef78867d2e55f352ddb0fea811fea6e3cf7407f8451220cc2bf01df95d`; no Journal files are included here.

The unmodified receipt `original-vs-repeat.json` records a successful original D3 handshake, the party exchange, a no-wager Free Battle, a consistent three-turn loss for player 1 and win for player 2, both postmatch menus, normal linked shutdown, and a fresh Continue of each actual postmatch Journal. Both saves were byte-identical to the original after the fresh Continue. The test used original game input and made no game-memory edits. It covers this particular linked battle and persistence path, not every feature of the game.

The eight unmodified BMP captures show the rules handshake, player 1's selected team and No wager, battle start, each side's result, the returned menu, and both fresh Continues with the original party and 11G. Their SHA-256 values match the receipt. The receipt is preserved verbatim; its Windows paths identify where this run took place and do not imply the executable, saves, or all 81 listed screenshots are present in this curated directory. The complete original scratch run and earlier failed automation attempts were retained at `/workspace/scratch/full-rom-2026-10-26/original-vs-link-resume-1351-01` through `-06`. Earlier attempts exposed helper timing, input and palette assumptions; the successful run used corrected helper `/workspace/scratch/full-rom-2026-10-26/original-vs-link-repeat-stable-06/repeat_vs_probe.py`.

Receipt SHA-256: `dd2a8a596d24fad07a5469854578f6adaaad9ba0d75713953d520206f120bbf4`.

## Captures

- [Link rules](original-D3-rules-menu-player1.bmp)
- [Team selection and no wager](correct-three-members-prize-default-No-player1.bmp)
- [Battle start](actual-linked-battle-start-player1.bmp)
- [Player 1 result](turn3-consistent-loss-player1.bmp) and [player 2 result](turn3-consistent-win-player2.bmp)
- [Postmatch menu](original-postmatch-menu-player1.bmp)
- Fresh Continue: [player 1](actual-full-party-and-11G-player1.bmp) and [player 2](actual-full-party-and-11G-player2.bmp)
