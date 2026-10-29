# Original postgame checkpoint replay on Wine

On 2026-10-29, all seven retained original-P1 postgame checkpoints passed on Wine using the full-bank Windows diagnostic built from source `1351bcd058e491455a477045a2ff86bbc3bd7b1c` in the cancelled Actions run `40799717118`. The diagnostic executable SHA-256 was `4d96e9c8d0318c0018057469365588e6becbdf2505def77d55cd967c1f4df11e`. The replay began with a genuine ending Journal, SHA-256 `0649c4ef78867d2e55f352ddb0fea811fea6e3cf7407f8451220cc2bf01df95d`, and used the pinned genuine postgame Journal bundle. The original game made all game-state changes; no save or game-memory injection was used.

Each checkpoint ran its original recorded input, created a Journal and reopened it through a fresh Continue. The replay additionally audited all seven newly replayed parent/output Journal links. This is supplemental Wine evidence from the earlier diagnostic build: it does not replace native Windows acceptance of a later build, prove every postgame path or random seed, or establish final package acceptance. No saves or executables are included here.

The two JSON reports are preserved without modification. Their paths refer to the original scratch run at `/workspace/scratch/full-rom-2026-10-26/independent-postgame-r3-01/`; not all files referenced there are included in this curated directory.

- `postgame-supplemental-validation.json` SHA-256: `2cfcd01fb4abfb3a4d6cfeaf26fad8de5f7c92aff8cdbfbf3a2aee3c94f0d009`.
- `story-checkpoints-validation.json` SHA-256: `b27be0ad08b24d34f53e4fb1c88941c79ac95df77dec4a26af9456d9e720ce64`.

The unmodified BMPs are the captured checkpoint screens; they show the resulting positions, not necessarily the interaction itself:

- [Key appraisal](key-appraisal.bmp)
- [QuietSea clear](quietsea-clear.bmp) and its [fresh Continue](quietsea-clear-fresh-continue.bmp)
- [Newlywed gift](newlywed-gift.bmp)
- [Certified egg](certified-egg.bmp)
- [Quest gates](quest-gates.bmp)
- [QuietSea dungeon reload checkpoint](quietsea-reload-dungeon.bmp)
- [NPC offers](npc-offers.bmp)
