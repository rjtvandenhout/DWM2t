# Full-ROM Cobi player — result and playing guide

The native Windows x64 player has passed the recorded main-story, postgame and package checks. It statically translates all 256 banks of the supplied Cobi ROM and embeds the original game data; it does not require a separate ROM file or a runtime opcode interpreter. It uses a CGB hardware runtime, including local two-player hosting.

[Download the verified player and ending save](https://github.com/rjtvandenhout/DWM2t/actions/runs/40821196055/artifacts/12875666985) · [Final validation run](https://github.com/rjtvandenhout/DWM2t/actions/runs/40821196055)

GitHub may require you to sign in. The Actions artifact is scheduled to expire on **2026-11-28**; download and keep a local copy.

## Start the game

1. Extract the downloaded Actions artifact. It contains `DWM2t-M8-VERIFIED-1351bcd058e4.zip`, `ending_complete.sav` and `verified-package.json`.
2. Extract the inner player ZIP, open the resulting `DWM2t-M8` folder and run `Play.cmd`. Keep the supplied files together.
3. Alternatively, double-click `DWM2tRecomp.exe`. Both methods use the default save under `%LOCALAPPDATA%\DWM2t\saves\`; `Play.cmd` also supplies integrity checks, session logs, named profiles and save imports.

Arrow keys move; **Z** is A, **X** is B, **Enter** is Start and **Backspace** is Select. Use the original game's **PLAN > Journal** and complete its confirmation to save. Closing the window flushes cartridge SRAM, but does not replace the game's Journal action.

## Use the ending save

`ending_complete.sav` is the genuine 32,768-byte ending Journal from the validated story. Keep the downloaded file as a backup. From the extracted `DWM2t-M8` folder, import it into a new profile:

```bat
Play.cmd -Profile ending -ImportSave "C:\path\to\ending_complete.sav"
```

The launcher copies the file and refuses to overwrite an existing profile. Choose **Continue** in the game. The save's SHA-256 is `0649c4ef78867d2e55f352ddb0fea811fea6e3cf7407f8451220cc2bf01df95d`. It also matches the actual [story artifact](https://github.com/rjtvandenhout/DWM2t/actions/runs/40806942912/artifacts/12872502085), at `ending-complete/native/checkpoint.sav`.

## Local two-player link

Run `Play.cmd -Profile player1 -LinkProfile player2` to open two locally connected games with separate saves. Import any existing Journal into each new profile first, then close the single-player session before starting the pair. Focus a window to control its player; player 1 provides audio. At the original save menu, highlight the same link service in both windows before confirming. For VS, highlight **VS MODE** in each window.

The native Windows package checks cover the two-window host, input and save isolation. Separate original-input observations under Wine used the exact final production executable:

- A [no-wager linked battle](evidence/2026-10-26-full-rom/vs-r4-2026-10-29/README.md) completed with consistent results and fresh Continue for both players.
- [Linked breeding](evidence/2026-10-26-full-rom/link-breeding-r4-wine-2026-10-29/README.md) paired SpotSlime with Spooky, producing Babble +2 and Spooky +2. Squiz was untouched; both resulting Journals reopened successfully.
- A [same-key QuietSea trade](evidence/2026-10-26-full-rom/key-trade-r4-wine-2026-10-29/README.md) reopened both players' Journals; its record also includes an original-ROM source trace of the observed key and cache changes.

These specific observations do not establish every link transaction, different-key trade or counterpart feature. The local host does not connect to a physical GBC or a separately loaded Tara ROM.

## What was validated

- The retained Windows native suite passed **18 tests, with no failures or skips**. It was rerun against the archived diagnostic build; the initial archived suite also passed.
- The diagnostic completed **38 original story checkpoints**, including Darck, MagicPlug, the full credits, THE END and the ending Journal. All 38 parent-Journal links were audited.
- Seven retained postgame checkpoints and their parent links passed, including the recorded QuietSea key-world route and save comparisons. A [separate Wine QuietSea replay after the same-key trade](evidence/2026-10-26-full-rom/quietsea-repeat-r3-wine-2026-10-29/README.md) reached the SteelFang reward on an earlier diagnostic executable from the same game source; it does not establish a second copy of that item or an independently reloaded reward save.
- The Windows and Linux hardware-core and persistence checks passed. The final Windows package passed its launcher, profile, integrity, Journal/reload and local-host checks.

The archived builds and campaign came from [run 40806942912](https://github.com/rjtvandenhout/DWM2t/actions/runs/40806942912). That run's diagnostic, production and POSIX jobs passed, but its production-Journal job failed; a [native Windows modal diagnostic](evidence/2026-10-26-full-rom/modal-diagnostic-r4-windows-2026-10-29/README.md) identified a test automation assumption when dismissing the expected same-save rejection dialog. The [successful continuation](https://github.com/rjtvandenhout/DWM2t/actions/runs/40821196055) revalidated the original production binary with corrected validation tooling, reran the native suite and completed the package gates. The earlier failure remains part of the record. The [independent release audit](evidence/2026-10-26-full-rom/verified-r4-2026-10-29/README.md) checks the uploaded files and their provenance.

## Exact identities

| Item | SHA-256 |
| --- | --- |
| GitHub artifact download, 131,729,885 bytes | `3ee40e3d34462b37b2ad8d5aca002be035a36fce8ef347e83c5381d38f3f839f` |
| Inner player ZIP, 136,292,168 bytes | `e769ba4357a81147a79671d5da8f3cb97515eb483a621f16141b27485fcd88a6` |
| Production EXE, 729,611,264 bytes | `63bf283dfeb7543c82d2787221788ab71e8651130b0a829b8987b368864a6f95` |
| Diagnostic EXE | `61a0e6d3ff84b5322b101247fc93ff6889f123a1bcd94df663135757fb3b9855` |
| Original Cobi ROM image | `8e38a7420ef5239c7196aa4fd4b1499e65db2823e875bbf8241bb2199e766d4e` |

The original game/build source is `1351bcd058e491455a477045a2ff86bbc3bd7b1c`. The successful continuation's validation and packaging tooling is `2e4057a190e626c4f1fe8118668f45a0d89bafb3`. Later documentation commits are not the source of those binaries. The downloaded package contains its own manifest and validation records.

## Scope and history

All-bank translation and the recorded routes do not prove every instruction, optional quest, random seed or link transaction. Additional Arena and collection rewards, DreamEgg hatching, rare arrivals, counterpart content and many random worlds remain unplayed. Tara's version requires the genuine counterpart ROM and separate validation. Super Game Boy packet/border presentation is outside the active CGB target. CI's audio endpoint does not establish audibility on every physical sound device.

The [full implementation inventory](FULL_ROM_IMPLEMENTATION_2026-10-26.md), [historical M8 completion](../milestones/M8_RESULT.md), [postgame report](POSTGAME_PROGRESS_2026-10-25.md) and [M0–M8 restore points](../RESTORE_POINTS.md) retain their own source identities and evidence.
