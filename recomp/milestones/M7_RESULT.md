# M7 completion record

M7 is accepted locally on Windows on 2026-10-18. It proves a genuine original
P1 battle and player attack, timed original-game audio, original Journal Save,
and Continue in a fresh runtime. It does not claim full-game playability; that
is the final M8 milestone.

Passing implementation: `424ebdb5d40338867651123dccf5dddbf66806ba`.
Immutable recovery branch: `restore/recomp-m7`.

## Validation authority

The user confirmed that GitHub Actions' monthly quota was exhausted and
explicitly authorized local Windows validation instead. Hosted CI did not run
and is not claimed as green. Both the local runner and the updated hosted
workflow use the same twelve CTest gates. No acceptance requirement was waived.

The complete local suite passed twice: first in 156.85 seconds, then in 131.65
seconds after pinning the exact battle/save regression values. Final output:

```text
100% tests passed out of 12
Alle lokale M7-gates zijn geslaagd.
```

Toolchain: Windows x64, Visual Studio Community 2026 / MSVC 14.51,
Python 3.14, CMake/CTest 4.4.4, NMake Release. Run from the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File recomp/tools/check_m7_local.ps1
```

Tests: M1_decoder, M2_bank0_audit, M4_renderer, M5_title, M6_movement,
M6_sram, M6_window, M7_audio, M7_intro_p1, M7_party_p1, M7_battle,
M7_save_continue. Logs: `recomp/build/Testing/Temporary/LastTest.log`.
Evidence: `recomp/build/local-validation/`.

## Genuine battle and command effect

All progression starts at the real cartridge boot. Strict P1-only fixtures
complete the original introductory quest, obtain Slash through the original
story, use the Oasis Key at the Magic Door, and enter an original encounter.
No host-written quest, party, battle, framebuffer, or save state is used.

The user explicitly approved correcting the earlier mistaken `C5DB=2` rule:
actual play proves that mode 2 also covers PLAN and key selection. A genuine
battle uses **C5DB=4** and reaches original native bank 49:$4001. Mode 2 alone
is never battle acceptance.

The test copies only the already game-created battle state for an equal-time
no-input control. P1 Fight/default confirmations must make an actual party
attack resolve. It reads current combat HP from the original HUD's word table
at D8BF (49:$7806/$7832), not stale combatant-record copies at D0D5.

Pinned result after 282 frames:

```text
Slash HP:       25 -> 20     control: 25
CactiBall HP:    9 ->  6     control:  9
before/control framebuffer: 0x08e2dcfe5df6d1e0
attack framebuffer:         0xa220d333e6f055b0
M7_BATTLE_PASS original_player_attack_and_equal_time_control
```

The inspected original framebuffer says "CactiBall took 3 damage!". A separate
P1 discovery playthrough also completed the encounter and returned to the map.
The gate requires damage to an enemy; cursor/input-register divergence alone
cannot pass. Captures: `battle/battle_before.bmp`, `battle/battle_action.bmp`,
`battle/battle_control.bmp`; numerical evidence: `battle/battle_evidence.txt`.

## Original Save and fresh-runtime Continue

The field menu opens with A facing empty space. The verified path is
PLAN > Journal > Yes. Original code displays "Your progress has been recorded".
The test compares SRAM immediately before this menu against the saved result;
New Game's prior SRAM initialization is not counted as the Save effect.

```text
original Journal SRAM bytes changed: 317
persisted file size:                 32768
SRAM FNV:                           0x81daa8e19c019ce4
party/inventory FNV:                 0xe39e0b6ad4462761
party/inventory bytes matched:       304 (C6FD..C82C)
quest/location fields matched:       11
```

A new Runtime constructor resets CPU, WRAM, VRAM, PPU and APU. Only the exact
SRAM file is loaded. Start/A/A chooses original Continue and the existing slot.
Slash, flags EE/FF/AF/0C, world 6, region 0/0 and position 70/40 are restored.
Field framebuffers differ only in their legitimate runtime animation phase:

```text
saved field:     0xe2c568bb82de9659
fresh Continue:  0xbc6b373672fa22d8
M7_SAVE_CONTINUE_PASS original_Journal_save fresh_Runtime_SRAM_only
```

This is not the synthetic M6 SRAM fixture. Evidence is in `save_continue/`
and the newly created `m7_original.sav` under `local-validation/`.

## Audio and retained regressions

Original APU writes produce 2,138,926 sample values / 1,069,463 stereo frames,
1,074,861 nonzero values, peak 19,200, hash `0x03b50ed7ed79bda0`.
NR50/NR51/NR52 finish at 77/33/F3. The live Win32 loop retains the WinMM
audio sink, independently clocked emulated APU timing, P1 input and SRAM flush.
No physical speaker-output claim is made by the headless PCM test.

M4 hash remains `0x284882dc2a98916f`; M5 remains frame 1921 / hash
`0x49c67a53ef4f8a80`; M6 movement remains
`0xd926fc62969f3bb4 -> 0xea72400372e2d1c5`, with 69 WRAM changes.
The original M6 SRAM and real Windows key-down/up/window tests remain green.

## Native code coverage and boundaries

Accepted ROMX AOT set (45 banks):

```text
1 2 3 4 7 8 9 10 15 16 17 18 19 20 21 22 23 25 26 29 31 37 38 40
47 48 49 50 51 52 53 54 55 57 58 95 96 105 115 127 132 133 135 161 163
```

New banks were reached by original P1 execution or identified as direct
required calls from that reached Journal/battle path; CMake records the entry
addresses/call chains. No generic runtime opcode interpreter or fabricated
RAM/framebuffer shortcut was added. Missing native code still fails explicitly.
Only repository matching sources and their original game output were used;
no external technical game information was consulted.

Legacy bounded search probes are diagnostic only. `--m7-battle-test` is the
acceptance gate; the old `--m7-fast-route` CLI name aliases this real test.
M8 continuation instructions: `recomp/handoff/M7_NEXT.md`.
