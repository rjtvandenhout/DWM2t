# Original two-player VS repeat, R4 production candidate

This curated subset records a GUI run on Wine of the production candidate from Actions run `40806942912`. The candidate identified source `1351bcd058e491455a477045a2ff86bbc3bd7b1c`; its executable SHA-256 was `63bf283dfeb7543c82d2787221788ab71e8651130b0a829b8987b368864a6f95`. Each player started with an independent copy of the genuine ending Journal, SHA-256 `0649c4ef78867d2e55f352ddb0fea811fea6e3cf7407f8451220cc2bf01df95d`. No Journal files are included here.

The unmodified receipt `original-vs-repeat.json` records the original D3 handshake, party exchange, a no-wager Free Battle, a consistent three-turn loss for player 1 and win for player 2, both postmatch menus, normal linked shutdown, and fresh Continue of each actual postmatch Journal. Both entire saves were byte-identical to the original after fresh Continue. The test used original game input and made no game-memory edits. It covers this particular linked battle and persistence path; it does not establish every link feature or full-game correctness.

The eight unmodified BMP captures have hashes matching the receipt. The receipt retains original paths and lists additional screenshots that are not included in this curated subset. Full scratch evidence is in `/workspace/scratch/full-rom-2026-10-26/original-vs-link-r4-1351-01`. Receipt SHA-256: `3050c31fcbac9a60f0cff658168f060b036cf438dc063bc7c60d258454f0367e`.

- [Link rules](original-D3-rules-menu-player1.bmp)
- [Team selection and no wager](correct-three-members-prize-default-No-player1.bmp)
- [Battle start](actual-linked-battle-start-player1.bmp)
- [Player 1 result](turn3-consistent-loss-player1.bmp) and [player 2 result](turn3-consistent-win-player2.bmp)
- [Postmatch menu](original-postmatch-menu-player1.bmp)
- Fresh Continue: [player 1](actual-full-party-and-11G-player1.bmp) and [player 2](actual-full-party-and-11G-player2.bmp)
