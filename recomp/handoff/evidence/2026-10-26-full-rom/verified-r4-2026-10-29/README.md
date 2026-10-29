# Independent verification of the R4 player package

The [independent audit receipt](independent-final-release-audit.json) records an inspection of the actual uploaded Windows player, its validation evidence and the ending Journal. The receipt's scratch paths describe where this inspection ran; those local files may not persist.

The original game build and story source was `1351bcd058e491455a477045a2ff86bbc3bd7b1c`, produced by [run 40806942912](https://github.com/rjtvandenhout/DWM2t/actions/runs/40806942912). Its diagnostic and campaign jobs passed; its production GUI gate failed, and the full run concluded failure. The separately identified [continuation run 40821196055](https://github.com/rjtvandenhout/DWM2t/actions/runs/40821196055), at tooling commit `2e4057a190e626c4f1fe8118668f45a0d89bafb3`, passed the corrected Windows GUI gates, all 18 original native tests, final packaging, `Play.cmd` and ending-Continue checks. It did not rebuild the original player.

The [verified player artifact](https://github.com/rjtvandenhout/DWM2t/actions/runs/40821196055/artifacts/12875666985) has ID `12875666985` and includes an inner player ZIP, `verified-package.json` and the genuine `ending_complete.sav`. GitHub artifacts are retained for 30 days; this artifact is recorded to expire on **2026-11-28 at 05:26:50 UTC**. Download and keep a copy before then.

| Inspected item | Bytes | SHA-256 |
| --- | ---: | --- |
| Downloaded GitHub artifact ZIP | 131,729,885 | `3ee40e3d34462b37b2ad8d5aca002be035a36fce8ef347e83c5381d38f3f839f` |
| Inner verified player ZIP | 136,292,168 | `e769ba4357a81147a79671d5da8f3cb97515eb483a621f16141b27485fcd88a6` |
| Tested production executable | 729,611,264 | `63bf283dfeb7543c82d2787221788ab71e8651130b0a829b8987b368864a6f95` |
| Original ending Journal | 32,768 | `0649c4ef78867d2e55f352ddb0fea811fea6e3cf7407f8451220cc2bf01df95d` |

The audit independently checked both artifact ZIP digests, all 32 packaged evidence hashes, the 18 executed native test cases with zero failures or skips, the actual `Play.cmd` report and a fresh ending Continue. The delivered ending Journal was byte-identical to the actual original ending checkpoint. The 11 attested tooling/workflow files match the named tooling commit, allowing only checkout newline conversion.

Separate [native Windows campaign/postgame screenshots](../diagnostic-r4-windows-2026-10-29/README.md), [local VS evidence](../vs-r4-2026-10-29/README.md) and [linked breeding evidence](../link-breeding-r4-wine-2026-10-29/README.md) identify their own build and platform. The recorded checkpoints do not establish every optional route, random seed, Tara version or SGB mode.

Receipt SHA-256: `f38c6bba5dd2b5867299cd4a1916c61c3e243bafb1101094efdf611bee7b7bad`. No save files or executables are included in this folder.
