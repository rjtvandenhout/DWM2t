# M7 PCM change: isolated cause proven

Four bounded diagnostic binaries reproduce the exact original M7 stimulus: fresh CGB boot, no P1/save/state injection, stop after30 consecutive original title frames. Actual frozen81cfb26e2e30815640a5c80463c662eaf2f11ead source and production AOT generators are used. Only original boot/title ROMX banks1/2/7/127 plus bank0 are compiled. These are diagnostic variants, not full-game acceptance binaries.

| Diagnostic Memory variant | Sample values | Nonzero | Peak | PCM FNV | Total CPU/base T |
|---|---:|---:|---:|---|---:|
| Current81c behavior | 2138928 | 1075360 | 19200 | `7807be6a3e82c89a` | 136891392 |
| Omit only queued DMA stall clocks | 2138926 | 1074861 | 19200 | `03b50ed7ed79bda0` | 136891360 |
| Restore only former3T TIMA reload | 2138928 | 1075360 | 19200 | `7807be6a3e82c89a` | 136891392 |
| Omit DMA stall and restore former3T TIMA | 2138926 | 1074861 | 19200 | `03b50ed7ed79bda0` | 136891360 |

The current diagnostic exactly reproduces the failed native Windows M7 aggregate. Removing only the DMA stall exactly reproduces the retained original3d aggregate. The two timer variants are byte-identical to their respective same-DMA PCM captures, not merely hash matches. All four processes exit0 in approximately4.8s each; AOT objects were shared and compiled once.

All four title BMPs are byte-identical: SHA256 `b065cc3eda9ffa600bc125edaefc7dec77e399327c01b764ca79745c497a8e5b`. First matching title frame1892, final frame1921,30 stable frames, and NR50/51/52=`77/33/F3` are identical. The only CPU/base-clock difference is exactly32T and one scheduler step.

The original CGB reset path at ROM0:$08D6–08E3 zeroes FF51–55. Writing HDMA5=0 starts a real16-byte general VRAM DMA. Current source copies that block and queues8 normal-speed machine cycles; the old generic I/O store omitted the transfer and stall. The read-only event trace records `HDMA5 t=66352 value=0 lcd=17`, then an8M CPU stall atPC08E5 fromT66364 toT66396. LCDC17 has its LCD-enable bit clear. No TAC write occurs during any capture; post-boot TAC is disabled. Hence the timer correction is not exercised by this title stimulus.

APU code is unchanged. `Apu::tick_tcycle` samples every128 base clocks even while NR52 is off; `power_off`/power-on do not reset its sample counter. The additional32 clocks during LCD-off boot therefore persist as a sampling phase change despite unchanged game/title state. Current totalT is exactly divisible by128; the legacy-clock total has remainder96. This accounts for the extra stereo pair. The first differing sample value is index722635 (stereo frame361317);152915 values differ in the common prefix. Raw PCM and the exact first-difference neighborhood are retained in `pcm-byte-comparison.json`.

Current core contracts independently distinguish the correct hardware behavior: `general_vram_dma` checks the actual copied data and queued8M/normal or16M/double-speed block cost; `runtime_dma_stall_and_interrupt` checks clock consumption before interrupt dispatch without PC/IME-delay advancement. Omitting the queue would violate those contracts. `timer_overflow_reload_and_write_edges` separately requires TMA/IRQ only on the fourth subsequent T-cycle; reverting that correction does not fix this M7 capture and is not warranted.

Conclusions: this M7 baseline PCM difference is fully attributable to the corrected original boot DMA stall under the exact stimulus. EI/EI, EI;HALT, the new bank0 alias, boundary fetches, HRAM handling and the4T timer correction remain present when the original PCM is restored, so none is needed to explain this difference. Double-speed mode is inactive: total CPU and base clocks are equal in every capture. Host audio endpoints are not involved in this raw APU capture.

M8 enemy-feeding also compares an old cumulative raw PCM assertion after a fresh boot. The same32T sampling-phase mechanism applies, and preceding original Journal/BMP/state witnesses matched in the native failure artifact. This bounded experiment did not replay the feeding route, so it does not independently prove the complete M8 PCM difference is solely DMA. No tracked files, goldens, original fixtures, game bytes or accepted package were changed.

Reproducibility: `source-inputs.json` pins all frozen core/header/tool/original-bank inputs. `provenance.json` lists production generation commands and exact diagnostic Memory variants. `CMakeLists.txt`, `main.cpp`, the four Memory sources, generated sources, build/configuration logs, executable identities, per-run commands, raw PCM and event logs are retained locally. `run-results.json` contains the full measured matrix and binary hashes; `artifact-index.json` adds source/artifact hashes. The common Memory instrumentation only logs TAC/HDMA5 writes; it changes no game/runtime state.
