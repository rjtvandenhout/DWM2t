# Full-ROM implementation inventory — 2026-10-26

**Implementation is complete; acceptance of the new binary is pending.** The
first complete native Windows validation built all 256 original ROM banks and
passed 15 of the retained 18 tests. The three failure causes are identified;
their test-reference corrections require a fresh acceptance run. Five
hardware/runtime contract tests
pass on Windows and Linux, and 199 host contract cases pass. Existing accepted
M8/postgame evidence still identifies the earlier exact binaries; the new
implementation has not replaced the accepted player.

The target is the original **Cobi ROM on the native CGB hardware model**:
4 MiB, 256 banks, SHA256
`8e38a7420ef5239c7196aa4fd4b1499e65db2823e875bbf8241bb2199e766d4e`.
The original header identifies `DWM2-C` / `BQLE`, CGB compatibility `$80`,
SGB support `$03`, and cartridge type `$1B` (MBC5 with RAM and battery).
That cartridge type does not require RTC or rumble hardware.

This is a source and evidence inventory. It distinguishes original game content
already present in the full AOT translation from host hardware that must be
implemented. Unplayed reward paths are not missing host game logic.
The machine-readable record is
[content-inventory.json](evidence/2026-10-26-full-rom/content-inventory.json).

## Original game code and data already present

The full configuration translates fixed bank 0 and switchable banks 1–255.
The ROMX generator emits all 16,384 byte entry addresses per bank, including
computed-jump destinations; it does not limit translation to previously played
branches. The embedded ROM generator requires the original Cobi SHA256 above.
This preserves original story, NPC, battle, breeding, item, map and generator
logic instead of replacing those systems with native approximations.

The normal CMake product build now defaults to `DWM2T_ALL_ROMX=ON`; limited
discovery requires an explicit `OFF`. The new complete diagnostic at
`81cfb26e2e30815640a5c80463c662eaf2f11ead` successfully compiled fixed bank 0 and
all 255 ROMX banks. Compiled address coverage does not mean that every original
instruction, content path or random output has been exercised.

The execution column below records historical accepted/observed content. The
current native run's narrower observations are recorded separately under
“Validation in progress.”

| Content | Implementation/source status | Existing execution evidence |
| --- | --- | --- |
| Main campaign and ending | Original game code/data present; accepted full AOT. | M8 completes the main campaign, Darck, MagicPlug, full credits, THE END and original Journal/Continue. |
| Random Magic Key worlds | Original generation, names, layouts, encounters, bosses, rewards, caching and deletion are present. | One genuine QuietSea world was cleared and revisited; in-world Journal and fresh Continue pass. Other seeds/classes and capacity/deletion boundaries remain unplayed. |
| Remaining Arena classes | Original admission, fees, battles and prizes are present at `19:$6D68`, `19:$7708`, `12:$697E`. | B-class fee refusal was observed; B/A/S/pro victories remain pending. |
| Character gifts and granddaughter duel | Original post-ending branches are present. | Newlywed and evaluator eggs were claimed; the granddaughter duel was reached and lost. No victory is claimed. |
| NPC breeding offers and Terry | Original parent selection, breeding, consumption and spawn progression are present. | FunkyBird and Skeletor breeding were completed. Copycat/StoneMan collection gates were observed; remaining offers and Terry victory are pending. |
| Collection rewards and King bounties | Original catalogue predicates, battles and rewards are present. | Refusal gates were observed. The 50/100/120/140/150/160/250/290-species reward playthroughs remain pending. |
| Medal Man | Original seven-prize service and post-ending Darck gate are present at `13:$710E`, with menu gate `C837`. | Minimum-fee refusal was observed; the full prize ladder has not been claimed. |
| Local fixed postgame keys/worlds | Original Elf, Traveler, Brawn and subsequent world scripts/maps are present. | Legitimate key acquisition and their full world playthroughs remain pending. |
| Counterpart key worlds and Soul progression | Original Lonely/Baffle maps and Soul prerequisite/reward code are present. Cobi's local rewards do not grant every counterpart key. | A legitimate original exchange and counterpart peer are needed for the complete route; no substitute keys or flags have been injected. |
| DreamEgg | Original solo acquisition, item feeding, state and exchange code are present; see the exact source chain below. | The actual empty-egg refusal was observed. Acquisition, feeding, hatching and exchange remain unplayed. |
| Rare arrival content | Lamia, Dimensaur and Kagebou definitions and arrival text are present. | The legitimate arrival/distribution path is unresolved. Text or monster definitions alone do not prove a reachable solo reward or completed distribution support. |

The prior finite random-world audit covers all ten terrain classes, 48 recipes,
264 structure records, 64 surface templates, 180 selectable dungeon layouts,
833 distinct compressed assets and all difficulty lookup boundaries. Those are
static source/asset checks, not native playthroughs of every output or a proof
that the outer generator terminates for every possible seed. See the
[postgame report](POSTGAME_PROGRESS_2026-10-25.md) and its retained raw evidence.

## Concrete host implementation work

At baseline `b349cc9bdd8d3f61821fd4ca52d52261789eaf93`, serial registers `$FF01`
and `$FF02` fell through to generic IO storage. There was no serial shift clock,
connected peer, transfer completion or serial IRQ producer. The serial interrupt
vector existed, but that did not implement a cable.

The original game demonstrates the required contract directly:

- [Bank 0 `$0058`](../../src/banks/bank_000.asm:8) jumps to `$255B`, which saves
  registers and far-calls bank 27 `$4001`, the original serial protocol handler.
- [Bank 0 `$08AD`](../../src/banks/bank_000.asm:141) writes a byte and starts an
  internal-clock transfer with SC `$81`; `$08BA` starts external-clock SC `$80`.
  The common `$08C7` routine resets SC and writes SB.
- [Bank 0 `$07D1`](../../src/banks/bank_000.asm:128) waits for SC bit 7 to clear.
  Consequently even a detached internal-clock transfer needs real completion
  behavior, receiving high input bits, before original error/cancellation flow
  can continue. Keeping the bit set indefinitely is a native hardware defect.
- [Bank 27 `$4001`](../../src/banks/bank_027.asm:3) handles received command bytes
  and protocol state. The guest ROM, rather than the host, must decide trades,
  battles, breeding, egg exchange and the resulting saves.

The completed implementation pass adds serial hardware and local dual-runtime
peer execution, alongside CPU/AOT edge handling and renderer/window corrections.
Each player must retain a separate genuine Journal, runtime and P1 state.
The host transport must carry serial bits/clock behavior; it must not manufacture
monsters, keys, rewards or completion flags. The new hardware contracts have
passed; final campaign, postgame, GUI and package acceptance remains pending.

## DreamEgg is an original solo feature

DreamEgg does not need an invented native acquisition service or a serial peer
for its initial acquisition:

1. [Bank 96 `$50E5`](../../src/banks/bank_096.asm:273) processes type 4/5 dungeon
   rewards. An eligible ordinary reward draw below 5 sets the structure's
   descriptor state to 3 and its reward byte to `$81`.
2. [Bank 18 `$6295`](../../src/banks/bank_018.asm:556) recognizes reward `$81`
   and reaches `$62FC`. If `CECE == 1`, the game uses the original Magic Key
   fallback; otherwise it starts the egg event.
3. [Bank 18 `$621F`](../../src/banks/bank_018.asm:548) calls bank 240 `$7D0A`.
   [That factory](../../src/banks/bank_240.asm:979) clears `CE9B..CF72`, sets
   `CECE = 1`, and creates the original egg data.
4. [Bank 19 `$7D45`](../../src/banks/bank_019.asm:983) checks for the real egg.
   [Bank 133 `$4717`](../../src/banks/bank_133.asm:116) opens original item-feeding
   menu `2:0C`; [bank 241 `$4187`](../../src/banks/bank_241.asm:27) calls the
   original item-effect code at bank 240 `$7284` and consumes the selected item.
5. Egg exchange is a distinct serial-dependent path. For example,
   [bank 240 `$527B`](../../src/banks/bank_240.asm:298) prepares the serial data
   pointers/count, and `$52C0` supplies the complete original egg-state block.

This chain establishes original acquisition/feeding implementation and a
specific future gameplay lead. It does not claim played acquisition, every food
effect, hatching correctness, or a completed exchange. The special DreamEgg
state is distinct from ordinary farm eggs awarded by NPCs.

## Version and hardware scope

The repository's matching source is Cobi. Original hardcoded Cobi branches
grant Brawn locally at `19:$7BA1`; alternate reward text or maps in the same ROM
do not establish a complete Tara build. Tara ROM identity/comparison and an
actual counterpart peer remain separate from Cobi feature coverage. A complete
Tara campaign is not claimed without the corresponding original source/input.

SGB is also a separate hardware mode. The header advertises it; original
[bank 0 `$05E2`](../../src/banks/bank_000.asm:97) performs SGB detection and
[bank 31 `$5040`](../../src/banks/bank_031.asm:263) emits SGB packets through P1.
The current native target boots CGB and renders a 160×144 game surface; an SGB
packet receiver/SNES border is not part of that active native mode. Compiling
the legacy SGB guest code does not prove an SGB host implementation. This must
remain explicit when describing “full ROM.” An infrared-register implementation
likewise does not prove an original IR gameplay feature: the confirmed `$FF56`
write at `0:$01C9` is boot initialization, and no IR content exchange is claimed.

## Retained source inventory and static checks

The source-only command
`python recomp/tools/audit_magic_worlds.py --output <new-report.json>` has run.
Its retained [receipt](/workspace/scratch/full-rom-2026-10-26/host-contracts-01/worlds.json)
reports `passed_static_checks`, no findings, and the unchanged original ROM
SHA256. It parses all 256 raw banks as 16,384 bytes each and checks the
reconstructed 4,194,304-byte image. The finite checks cover ten terrain classes,
48 recipes, 264 structure records, 64 surface templates, 180 selectable dungeon
layouts and 833 compressed assets. The receipt identifies its AOT checks as
source/emission checks, not an acceptance of a diagnostic executable.

The actual [build identity](/workspace/scratch/full-rom-2026-10-26/native-failure-01/extracted/diagnostic-output/build-identity.json)
separately records fixed bank 0, ROMX banks 1–255 and the same ROM SHA256 for the
compiled Windows diagnostic. The retained failure audit verifies all 844
archived source-manifest file hashes and the Git archive's `81cfb26` commit.
Source-manifest hashes identify the raw assembly files; they should not be
mistaken for per-bank hashes of their reconstructed binary bytes.

The new static command
`python recomp/tools/inventory_full_rom.py --output <new-report.json>` also
provides a [draft per-bank receipt](/workspace/scratch/full-rom-2026-10-26/original-bank-inventory-draft.json).
It records:

- Exactly `src/banks/bank_000.asm` through `bank_255.asm`, each parsed as 16,384
  original bytes; per-bank byte count, SHA256, source path and CPU window.
- Fixed-bank and switchable-window mapping, total 4,194,304 bytes, and the
  reconstructed original Cobi SHA256 stated above.
- Explicit selection of all 255 ROMX banks in the normal full build and the
  AOT generator's 16,384 emitted entry addresses per bank; bank-0 alias handling
  is a runtime mapping contract rather than an additional cartridge bank.
- Separation of code/data inventory from executed test coverage. A bank or
  opcode emitted by the compiler is not marked as dynamically exercised.
- The source commit and output hashes needed to rerun and compare the inventory
  after the implementation is committed.

The draft reconstructs the same 256-bank, 4,194,304-byte ROM and records every
bank's original-byte SHA256, assembly-source SHA256, cartridge offset and CPU
window. It explicitly sets runtime execution, dynamic coverage and native
build verification to false. Its `source_inputs_match_commit=false` reflects
the new inventory tool being uncommitted when the draft was made; a clean
committed receipt is still pending. The JSON inventory retains this provenance
instead of treating the draft as exact-commit acceptance. A subsequent
[clean committed receipt](evidence/2026-10-26-full-rom/original-bank-inventory.json)
at `b4e9587ba574cdd3b55f9fd8a366404fd4a0cd2c` verifies all 256 banks with
`source_inputs_match_commit=true`. It remains source-preservation evidence,
separate from native execution coverage.

## Validation in progress

Implementation was committed as `195ca680b2805339bff86c690c25c99aea6688a2`.
The first final-validation source is
`81cfb26e2e30815640a5c80463c662eaf2f11ead`, which additionally checks total DMA
stall time across linked scheduler slices. Its
[Windows run 40355244285](https://github.com/rjtvandenhout/DWM2t/actions/runs/40355244285)
produced the complete diagnostic SHA256
`b1c141d5b3cbb9640ae0af8831e7d369560a3785097cc6834f1734417b2538b3`.
The original ROM SHA256 remains unchanged.

The retained [native failure audit](/workspace/scratch/full-rom-2026-10-26/native-failure-01/native-failure-audit.json)
preserves the original artifact, job log, source archive, build identity, XML
and observed save/screen comparisons. Native job `121685836009` ran all 18
tests: 15 passed, three failed, none skipped:

- `M4_renderer`: the renderer component passes and its BMP matches the old
  build. The mapped-hardware harness still expected effective bank `$100`
  instead of the correct mirrored physical bank 0 for this 4 MiB ROM. The
  working-tree harness correction is not yet a passing rerun.
- `M7_audio`: the unchanged APU now includes the original boot's correct
  32-T-cycle GDMA stall. A subsequent controlled four-variant
  [causal comparison](evidence/2026-10-26-full-rom/PCM_CAUSALITY.md) reproduces
  the historical PCM byte-for-byte only when that stall is omitted. Restoring
  the former timer behavior alone has no effect. The exact M7 pin has been
  corrected in the working tree; a fresh native acceptance run is still needed.
- `M8_oasis_checkpoint`: the first exact audio pin fails in the enemy-feeding
  side route after the preceding game-state assertions pass. That route's item
  throw and subsequent checkpoint were not reached by that failed native run.
  A separate original-P1 observation subsequently completed all 19,508 frames
  and matched all 76 non-audio assertions. Its three measured audio references
  still require strict replay on the final source.

Reference migration preserves the original controller bytes, frame positions,
state/Save assertions and manifest expectations. The reference ledger freezes
all 58 audio-bearing routes and 375 exact PCM boundaries. Complete measurements
now cover 5,338,451 original P1 frames on separately identified Windows and
Linux discovery executables. The sealed migration and strict final-source
replay remain separate acceptance steps. A
subsequent Kids Class observation found one intermediate screenshot difference
at frame 14,370: `9a38ae3eef2d8568` versus `be55670a278cea50`. The original binary
reproduces the old image; only the first 16 pixel rows differ, and the original
SRAM and exposed game-memory bytes match. The subsequent
[same-live-Memory comparison](evidence/2026-10-26-full-rom/RENDERER_CAUSALITY.md)
isolates the feature: both the old renderer and the current renderer with only
scroll history disabled reproduce the old image exactly. Actual completed SCY
history is 2 on rows 0–16, then 0; the current bitmap is byte-identical on Linux
and Windows. Memory remains unchanged across all three renders. This exact
one-line screen-reference update is approved and retained in the guard; every
other non-audio route byte remains frozen. No screen check is removed.

The [strict reference guard](evidence/2026-10-26-full-rom/reference-integrity-guard.json)
and a separate [root diff audit](evidence/2026-10-26-full-rom/reference-migration-independent-diff.json)
pass. The exact 428 changed lines comprise 375 audio references, this one
approved screen reference, 45 manifest route hashes and seven active wrapper
route hashes. All other bytes in the 64 target files are unchanged. A further
local run passes all ten existing host suites (199 cases) and the new reference
guard. These are validation-tool checks, not final Windows game acceptance.

The seven completed Oasis/Inn/story Journal outputs before that failure are
byte-identical to the accepted baseline, as is the earlier original M7 Journal.
Seven corresponding 64 KiB observation snapshots differ only at six hardware
register reads: `FF02`, `FF4D`, `FF52`, `FF54`, `FF55`, `FF56`; all other 65,530
bytes match. These are partial regression observations, not the separate
seven-stage postgame acceptance replay. The full 38-stage campaign and fresh
seven-stage postgame jobs were skipped after the native-suite failure.

Additional results already available:

- Exact-source Windows and Linux standalone core reports each pass all five
  named memory, runtime, serial, renderer and generated-AOT tests. The reports
  bind 35 source inputs and three test binaries. See the
  [Windows report](/workspace/scratch/full-rom-2026-10-26/fresh-production-01/runtime-core-windows/runtime-core-validation.json)
  and [Linux report](/workspace/scratch/full-rom-2026-10-26/runtime-core-linux-02/runtime-core-validation.json).
- The [host-contract results](/workspace/scratch/full-rom-2026-10-26/host-contracts-01/results.json)
  record 199 passing unit cases across ten suites, plus successful decoder,
  bank-0, key, item and finite-world static checks. Synthetic evidence fixtures
  in these suites are not gameplay proof.
- The separate [independent core audit](/workspace/scratch/full-rom-2026-10-26/independent-core-audit/independent-core-audit.json)
  preserves the provenance of Windows PR run `40355216796` at merge source
  `e793442b8431b5f207dea098003e3f36df318a49`, and Linux evidence from the full
  run. Its comparison establishes matching branch/merge source inputs while
  retaining their distinct commit identities and LF/CRLF archive hashes.
- A separate original-P1 two-peer VS probe completed the `$B7/$D3` handshake,
  actual party exchange and a four-turn original Free Battle without a wager.
  Player 1 won and Player 2 lost consistently. Both returned to the original
  menu and closed normally. Fresh, separate production processes then continued
  each actual post-match Journal; both complete 32-KiB files returned exactly
  to the genuine ending seed, including all 17 full monster records and all
  107 quest bytes. The [retained receipt](evidence/2026-10-26-full-rom/original-vs-link-observation.json)
  identifies the actual `81cfb26` production EXE and Wine platform. It does not
  certify all other link services or a later binary. Important captured screens:
  [rules](evidence/2026-10-26-full-rom/screenshots/p1-first-vs-confirm.bmp),
  [battle](evidence/2026-10-26-full-rom/screenshots/p1-battle-exchange-wait5.bmp),
  [winner](evidence/2026-10-26-full-rom/screenshots/p1-turn4-result.bmp),
  [loser](evidence/2026-10-26-full-rom/screenshots/p2-turn4-result.bmp).
- A fully detached, single-window original VS probe also passed: the ROM
  displayed its two normal not-ready message pages, B returned to the menu,
  and original Continue restored the complete ending save byte-for-byte.
  The [detached receipt](evidence/2026-10-26-full-rom/detached-vs-observation.json)
  records the actual 53-second Wine run, normal exit and unchanged source seed.
  No connected peer or fabricated serial response was supplied.

The earlier authorized Actions cleanup also removed 144 superseded build/probe
artifacts, reclaiming 482,264,078 bytes. All 23 deliberately preserved artifacts
were verified afterward, including the accepted M8 package. The immutable
M0–M8 branches and `main` were unchanged. The
[cleanup receipt](evidence/2026-10-26-full-rom/actions-artifact-cleanup.json)
retains the exact deleted/preserved identities and remote branch commits.

Acceptance still requires a fresh pass of all 18 retained native tests and completing
the retained main-story/postgame chains, production GUI/persistence checks and
strict package gates on the final exact source. Original no-peer cancellation
and successful original-menu linked transactions remain separate execution
claims. Collection rewards, DreamEgg feeding/hatching, rare arrivals,
additional worlds, cache capacity/deletion, Tara and SGB scope retain the
limitations above. No whole-ROM exhaustive gameplay validation is claimed.
