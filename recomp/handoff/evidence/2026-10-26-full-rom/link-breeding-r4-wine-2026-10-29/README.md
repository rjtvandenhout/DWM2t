# Original local-link breeding, R4 production candidate

On 2026-10-29 the R4 production candidate from Actions run `40806942912` was exercised under Wine using two independent copies of the genuine ending Journal and original controller inputs. The executable identifies source `1351bcd058e491455a477045a2ff86bbc3bd7b1c` and SHA-256 `63bf283dfeb7543c82d2787221788ab71e8651130b0a829b8987b368864a6f95`. The original Journal SHA-256 is `0649c4ef78867d2e55f352ddb0fea811fea6e3cf7407f8451220cc2bf01df95d`. No Journal or executable is included here.

The original game linked the two players for Breeding. Player 1 selected farm SpotSlime **AAAy** and player 2 selected farm Spooky **A**; Squiz was not selected. The game reported the monsters liked each other, played the breeding animation, and displayed Babble's egg for player 1 and Spooky's egg for player 2.

Both actual post-breeding Journals were opened in fresh processes via Continue and reached the original home. Their 32 KiB records each held 17 owned monsters: only the selected parent was removed, the corresponding offspring was added with +2, and all 16 other complete 165-byte records and all 107 quest bytes matched the original. The linked process and both fresh processes exited with code 0. The unmodified [replay receipt](breeding-replay.json) contains the actual inputs, screenshots, hashes, results, and source identity; its SHA-256 is `64094f98cf69141b8b5f3f1ded5077c9f88982bca7ffe026b4aa1e06980c1904`.

This proves one linked breeding pairing under Wine, not a separate monster-trade feature, all link modes, or full-game correctness. `replay.py` is the exact scratch helper used for this run and references the existing observation helper and R3 visual references in the scratch workspace; it is retained for provenance, not as a standalone test. Earlier wrapper attempts and the complete run remain in `/workspace/scratch/full-rom-2026-10-26/link-breeding-r4/`.

- Both players [ready to breed](after3-player1.bmp) and [player 2](after3-player2.bmp)
- [Player 1 chooses SpotSlime](farm-choices-player1.bmp); [player 2 chooses Spooky](page2-player2.bmp)
- [Compatibility message](after-confirm-player1.bmp) and [original animation](animation-player1.bmp)
- [Babble egg](offspring-full-player1.bmp) and [Spooky egg](offspring-full-player2.bmp)
- Fresh Continue: [player 1 save card](save-card-player1.bmp) and [home](fresh-original-home-player1.bmp); [player 2 save card](save-card-player2.bmp) and [home](fresh-original-home-player2.bmp)
