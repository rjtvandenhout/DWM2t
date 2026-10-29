# Original local-link breeding observation

On 2026-10-29 the R3 production candidate from Actions run `40799717118` was exercised under Wine, using two independent copies of the genuine ending Journal and original controller inputs. The EXE identifies source `1351bcd058e491455a477045a2ff86bbc3bd7b1c` and SHA-256 `829e95842cea5a0cc9d13f601ae89b814c4fd2109ca08065bf50a9d944378ec1`. The seed SHA-256 is `0649c4ef78867d2e55f352ddb0fea811fea6e3cf7407f8451220cc2bf01df95d` and its original file was unchanged. No saves or executable are included here.

The game linked the two players for Breeding. Player 1 selected the farm SpotSlime **AAAy** and player 2 selected the farm Spooky **A**; Squiz was not selected. The original game reported that the monsters liked each other, played the breeding animation, and displayed Babble's egg for player 1 and Spooky's egg for player 2.

Both actual post-breeding Journals were opened in fresh processes using original Continue inputs and reached the original home. Comparing the resulting 32 KiB files with the seed showed 17 owned records per player: only the selected parent was removed, the corresponding offspring was added with +2, and all 16 other complete 165-byte records and all 107 quest bytes matched. Both fresh processes returned exit code 0. The linked process received WM_CLOSE and exited without forced cleanup, but its numeric exit code was not recorded. Details and file hashes are in [breeding-observation.json](breeding-observation.json); the original controller and capture events are preserved as JSONL.

This is one original linked breeding pairing, not proof of a separate monster-trade feature, every link mode, or full-game correctness. The ongoing fresh Windows acceptance run is separate.

- [Both players ready](link-ready-p1.bmp) and [player 2](link-ready-p2.bmp)
- [Player 1 selects SpotSlime](spotslime-p1.bmp); [player 2 selects Spooky](spooky-p2.bmp)
- [The original compatibility result](compatible-p1.bmp) and [breeding animation](breeding-animation.bmp)
- [Babble egg for player 1](babble-egg-p1.bmp); [Spooky egg for player 2](spooky-egg-p2.bmp)
- Fresh Continue: [player 1 save card](continue-card-p1.bmp) and [home](continue-home-p1.bmp); [player 2 save card](continue-card-p2.bmp) and [home](continue-home-p2.bmp)
