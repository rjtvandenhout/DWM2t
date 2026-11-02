# Second twenty supervised original-input training victories

From the genuine checkpoint 07 in the [first continuation](../2026-11-02-arena-training-continuation/README.md), the original party won 20 further QuietCrag encounters. Batches were limited to at most four victories, followed by the original shrine return, Warubou restoration, Journal and fresh Continue. Checkpoint 14 and its independent Continue are both exactly 32768 bytes, SHA-256 `0a3f752db96121462cc5edae965a4b2c2f6d9d64e331d236896c53d288fb08ea`. The preserved genuine Journal remains at `/workspace/scratch/arena-b-2026-11-02/session33/training_supervised_14.sav`, with 5688G and the team fully restored. Original saves, ROM and binaries are not included here. Squiz was not bred or used; original game state, RNG and saves were not patched.

All seven checkpoints below were checked byte-for-byte against separate fresh Continue SRAM. An independent audit confirmed 5688G, the same 107 quest bytes and normal party [12,0,10], with full HP and MP, in each. Garon, Slash and Derzo each gained 6615 EXP in these 20 wins. Their final levels were 41, 38 and 41. Original executed P1 commands, trace and supervised controller logs are retained here. The controller is not proven safe for arbitrary unattended menus and unknown input halted it for inspection.

| Checkpoint | Wins in batch | SHA-256 | Garon / Slash / Derzo EXP |
| --- | ---: | --- | --- |
| `training_supervised_07` | starting point | `2485a1196ab97e3a6be0159f8d7586ed6b297f351ebe21f2ece4684ac3fc1f3a` | 340734 / 351185 / 333864 |
| `training_supervised_08` | 4 | `ea98a81be72e8e03021ddb682fc64d4f094466d7498f0e4efa3ba8497dedfbb3` | 342403 / 352854 / 335533 |
| `training_supervised_09` | 1 | `372fadf979a48c4d816776f718ad95f309597aa9c5efa2bbed1390aab983980c` | 342818 / 353269 / 335948 |
| `training_supervised_10` | 4 | `805d3364faaa9aad77d5bfbc9c164dd0edc8bd333e8a883eea0fad049b75ed02` | 343827 / 354278 / 336957 |
| `training_supervised_11` | 1 | `2571569a2277a04fe53b4f37064b83207e5bba210ad1cf5a49dab5e146aa52a4` | 343963 / 354414 / 337093 |
| `training_supervised_12` | 4 | `491a1bfc702d4ee68ce5d5e46a69965d98cf3e499da317a4667b8614d89afb49` | 345382 / 355833 / 338512 |
| `training_supervised_13` | 4 | `238af60a18df73512fa702a1b26dca021e7b5ec6f2aae7306b5463af191cd9ee` | 347073 / 357524 / 340203 |
| `training_supervised_14` | 2 | `0a3f752db96121462cc5edae965a4b2c2f6d9d64e331d236896c53d288fb08ea` | 347349 / 357800 / 340479 |

At checkpoint 09 a [surprise attack](screenshots/surprise-stop.bmp) stopped the driver; after inspection, an original [FLEE choice](screenshots/original-flee.bmp) returned to the field. That escape was not counted as a victory. At checkpoint 11 [CoilBird](screenshots/coilbird-stop.bmp) was handled under supervision and [departed](screenshots/coilbird-departure.bmp); one actual preceding win was counted. The [final independent fresh Continue](screenshots/final-fresh-continue.bmp) shows the preserved progression.

A separate [S-class trial from checkpoint 14](../2026-11-02-arena-s-final40/README.md) won the first two rounds and lost the third. No S championship or prize is claimed.
