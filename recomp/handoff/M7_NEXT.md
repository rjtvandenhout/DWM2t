# M7 handoff: start M8, the final fully playable native release

## Accepted baseline

Recover from immutable `restore/recomp-m7`. Passing implementation is
`424ebdb5d40338867651123dccf5dddbf66806ba`; the milestone record is
`recomp/milestones/M7_RESULT.md`. Never move or force-push an accepted restore.

M7 is complete, not merely discovery-ready: original P1 quest/Slash/Oasis
encounter, genuine C5DB=4 battle, player attack with enemy HP 9->6 versus an
unchanged no-input control, deterministic original-game audio, original
Journal Save, exact 32 KiB SRAM, and fresh-runtime Continue all pass. The full
twelve-gate suite passed twice on local Windows. Hosted Actions was unavailable
because of its monthly quota; local acceptance was explicitly user-authorized.

## Start locally

From the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File recomp/tools/check_m7_local.ps1
.\recomp\build\DWM2tRecomp.exe --play recomp/build/local-validation/m7_original.sav
```

The NMake executable is directly in `recomp/build/`; a Visual Studio generator
puts it under `recomp/build/Release/`. See `M7_LOCAL_WINDOWS.md` for setup.
The test-created save is original progress at Home with Slash and the Oasis
Key. Enter opens the title menu; Z/Z selects Continue and its existing slot.
Arrow keys = D-pad, Z = A, X = B, Enter = Start, Backspace = Select.
The in-game field menu opens with A facing empty space, not Start.

Keep normal play saves separate from acceptance output, which the tests may
overwrite. Copy the accepted save before interactive exploration.

## M8 implementation order

1. Retain all twelve M1-M7 gates and their exact accepted values unchanged.
   Do not use C5DB=2 as battle evidence: it also represents ordinary menus.
2. Continue original gameplay beyond the M7 encounter using P1 only. Capture
   each newly reached MissingBank with bank/PC, scene and reproducible inputs.
   Add required original ROMX code to AOT and record why it is needed.
3. Use only repository sources and the user's own ROM/original runtime output.
   No external technical game information, host-fabricated quest/party/battle
   state, injected graphics, or generic runtime interpreter fallback.
4. If original executable code is copied to HRAM/WRAM, require a verified
   signature and explicit native translation, preserving fail-closed behavior.
5. Extend deterministic original-input routes through remaining worlds,
   progression, battles, key systems and the original ending/credits. Save at
   meaningful later checkpoints and verify fresh-runtime Continue there.
6. Validate the complete playthrough, keyboard responsiveness, rendering,
   audio timing and original SRAM behavior together on Windows. Resolve actual
   runtime failures; do not substitute a battle-looking image for gameplay.
7. Package the standalone Windows x64 executable, clear controls/save
   instructions and a repeatable offline build/test workflow. Preserve user
   saves across updates. Re-run identical GitHub CTest validation when Actions
   quota permits, without claiming unavailable CI has passed.
8. Only after original full-game playability and all retained gates pass,
   create the final `restore/recomp-m8`, `M8_RESULT.md`, and release handoff.
   Optional enhancements come after a verified original baseline.

## Discovery tools and pitfalls

- `--m7-p1-probe <route> <output>` replays a strict P1 fixture, then accepts
  appended commands from `<output>/commands.txt`. `--m7-continue-probe <sav>
  <output>` boots a fresh runtime from an original Save and performs Continue.
- `--m7-replay-p1 <route> <output>` accepts finite P1-only fixtures and read-only
  state assertions; it rejects diagnostic checkpoint/state commands.
- Diagnostic `mark/back/seek` shortcuts must never enter acceptance fixtures.
- `recomp/tests/m7_party_p1.txt` is the original fresh-boot quest route;
  `m7_oasis_p1.txt` continues from that state. Continue changes timing/RNG, so
  discovery after loading a save can encounter a battle at a different step.
- Current combat HP is D8BF's word table, slots 0..2 and 4..6. D0D5 combatant
  record copies can remain stale during a battle. See 49:$7806/$7832 and the
  equal-time control in `src/m7_acceptance.cpp`.
- Event flags start at CBD7; original facing is 0=Down, 1=Right, 2=Up, 3=Left.
- Old large search harnesses remain for historical diagnostics, not acceptance.

M7 does not certify all worlds, every monster/command, later-game systems or
the ending. Those are the remaining M8 work, not hidden M7 completion claims.
