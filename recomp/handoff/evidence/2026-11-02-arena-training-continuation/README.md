# Twenty further supervised original-input training victories

Starting from the genuine 17-win Journal described in the [earlier training evidence](../2026-11-02-arena-training/README.md), the original party Garon, Slash and Derzo won 20 further QuietCrag encounters. Every batch contained at most four wins and ended with original shrine return, Warubou restoration, Journal and a separate fresh Continue check. No original user save was overwritten, Squiz was not bred or used, and no game memory, RNG or save bytes were injected.

The local original Journal and fresh Continue files are 32 KiB and byte-identical at every checkpoint. They remain in `/workspace/scratch/arena-b-2026-11-02/session33/`; saves, ROM and executables are not included here. Logs, full original executed input, game observation traces, and the research controller used under supervision are included. Unknown phase or recruitment text stopped the pilot and was inspected before further input. In particular [Almiraj](screenshots/almiraj-stop.bmp) and [SpikyBoy](screenshots/spikyboy-stop.bmp) departed after supervised original dialogue. The controller is not proven safe for arbitrary unattended dialogue.

| Checkpoint | Wins in batch | SHA-256 | Garon / Slash / Derzo EXP |
| --- | ---: | --- | --- |
| `training_cycle17` | starting point | `64a5f73e97f1936ff8b9d7c69bde83b4a4a6ff55431d1873ccd68893cd1942f8` | 334290 / 344741 / 327420 |
| `training_supervised_01` | 2 | `a097951ddd5e0fa34bf9c4e2f0e45ae04b2f5c28c7d29365f749313a396b2000` | 334984 / 345435 / 328114 |
| `training_supervised_02` | 1 | `81b7f7314b1bce8b48d489b046178e450adefef3df2b3e2d434e55482fa3c178` | 335366 / 345817 / 328496 |
| `training_supervised_03` | 4 | `b0913e685b6293f7216335b275dcefc54efd41ca340943b96fdc44a073331861` | 336764 / 347215 / 329894 |
| `training_supervised_04` | 4 | `418a4d3613e503c08389785c6c09e93d3539f8d6d113625da6fb2b493ab2e9e6` | 338333 / 348784 / 331463 |
| `training_supervised_05` | 3 | `a08638f7b589f6658c277349433c491ff144db62335e6d95e02dca270c7cce97` | 339131 / 349582 / 332261 |
| `training_supervised_06` | 2 | `4ec1ad339372bb3d8fc340c9389dc3e535423d663e953555cb99aeba0f12fc23` | 339651 / 350102 / 332781 |
| `training_supervised_07` | 4 | `2485a1196ab97e3a6be0159f8d7586ed6b297f351ebe21f2ece4684ac3fc1f3a` | 340734 / 351185 / 333864 |

[Derzo reached level 41](screenshots/derzo-level41.bmp) in the second batch. At the [final fresh Continue](screenshots/final-fresh-continue.bmp), the party was Garon level 41, Slash level 38 and Derzo level 41, all fully restored. On a separate copy of checkpoint 02, an [S-class attempt](../2026-11-02-arena-s-derzo41/README.md) won two rounds and lost the third; no S championship is claimed. A [final independent S trial from checkpoint 07](../2026-11-02-arena-s-final20/README.md) again won the first two rounds and lost the third.
