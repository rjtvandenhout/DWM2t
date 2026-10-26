# Full-ROM implementation inventory — 2026-10-26

**Implementation is in progress. No new builds, tests or gameplay validation
have been run for this implementation phase.** Existing M8 and supplemental
postgame results remain historical evidence for their exact accepted binaries.
They do not validate the new hardware/runtime changes.

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

The accepted Windows package was built with `DWM2T_ALL_ROMX=ON`. At the start of
this phase the plain CMake option still defaulted to `OFF`, retaining the older
limited discovery configuration. Making complete AOT the default product build
is an implementation item; limited discovery should require an explicit choice.

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
monsters, keys, rewards or completion flags. Final validation is pending at this
document's creation.

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

## Reproducible ROM-bank inventory contract

The root implementation will provide a source-only inventory command and a
retained receipt. Its evidence must include:

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

This specification is recorded in the JSON inventory. It is not a claim that
the new inventory command, new native build or validation has already run.

## Validation phase remains deferred

After implementation is complete, validation must cover the new hardware and
CPU/renderer contracts, original no-peer cancellation, two-runtime serial
communication through original menus, and the retained main-story/postgame
Journal regressions. Collection rewards, DreamEgg feeding/hatching, rare arrival
reachability, additional generated worlds, cache capacity/deletion and the
counterpart campaign remain distinct gameplay coverage items. A hardware-unit
pass must not be presented as completion of those original content routes.
