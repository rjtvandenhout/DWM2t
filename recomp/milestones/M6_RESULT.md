# M6 completion record

M6 proves that the native static recomp can leave the original DWM2 Cobi title,
follow the original new-game flow into a real in-game map, accept host input
through Game Boy P1 semantics, move the player through original game code, and
persist cartridge SRAM.

## Passing implementation

```text
1cca3634ef0093f51c3bbf2d7c3e578eed5ab268
```

Restore branch:

```text
restore/recomp-m6
```

Final Windows CI:

```text
38842905661
```

## Retained M5 boot regression

M5 remains a permanent boot-path regression and still reaches the original
Cobi title at the exact accepted state:

```text
M5_TITLE_REACHED
frame=1921
hash=0x49c67a53ef4f8a80
stable_frames=30
C5DB=5
C5DC=0
```

No external ROM file is loaded and no host-side title or map state is injected.

## Original title/menu/new-game flow

The deterministic M6 harness presses Start/A only through
`Memory::set_joypad_state()`, which feeds the Game Boy P1 path. It follows the
original game from the title into the opening ship map without directly editing
WRAM state.

The M6 AOT ROMX set reached by this accepted path is:

```text
1, 2, 4, 7, 15, 16, 18, 19, 20, 22, 23, 31, 40, 52, 53,
95, 96, 105, 127, 132, 133, 135
```

Banks were added only when real execution reported `MissingBank`. No generic
runtime LR35902 interpreter fallback was introduced.

## Overworld/map movement proof

The scripted new-game flow reaches the real opening ship map. CI captures the
map immediately before and after a legal Right input sent through P1.

Accepted result:

```text
M6_MOVE_RESULT
before_hash=0xd926fc62969f3bb4
after_hash=0xea72400372e2d1c5
SCX=0->0
SCY=0->0
wram_changes=69
frame=3757
```

The before/after framebuffers were also inspected visually: the player character
moves approximately one tile to the right on the ship. The unchanged SCX/SCY
values rule out a host-side camera shortcut; original game-owned state changes
and the rendered player position changes.

Artifact images:

- `m6_probe/overworld_before_move.bmp`
- `m6_probe/overworld_after_move.bmp`

## SRAM persistence

MBC5 cartridge SRAM is exposed as the exact 32 KiB save image. The interactive
runtime loads a `.sav` file on startup, tracks dirty writes, autosaves dirty
SRAM, and flushes it on exit.

CI writes and verifies all four 8 KiB RAM banks, reloads into a fresh
`Memory`, modifies bank 2, saves again, and verifies the modified byte after a
second reload.

Accepted result:

```text
M6_SRAM_PASS
bytes=32768
bank2_A321=0xe7
```

## Live native Windows loop

`DWM2tRecomp.exe --play [save-path]` runs the recompiled game in a live Win32
window at Game Boy frame cadence.

Keyboard mapping:

```text
Arrow keys  D-pad
Z           A
X           B
Enter       Start
Backspace   Select
```

Input is injected only through the existing joypad/P1 abstraction.

A dedicated Windows smoke test creates the real Win32 window, delivers
`WM_KEYDOWN`/`WM_KEYUP`, verifies that the state reaches P1, advances native
frames, renders them, and closes the window.

Accepted result:

```text
M6_WINDOW_SMOKE_PASS
frames=4
keydown=1
keyup=1
p1_down=1
p1_up=1
framebuffer_hash=0xb423319be6530b83
```

During this verification a real live-loop bug was found and fixed: LR35902 HALT
must be treated as a normal wait-for-interrupt state, not as a fatal runtime
result.

## Artifact

Final verified artifact:

```text
DWM2tRecomp-M6-Probe-Windows-x64
artifact id: 12022280550
artifact ZIP SHA-256:
5992166ec20d68e112b95e4d9b46159cfe8be6080b6609956570a15763bbc490
```

Verified executable:

```text
DWM2tRecomp.exe
PE32+ x86-64 Windows executable
SHA-256:
2c67c4a8951f2b2a74239ef9402aaf4bf1429cb22e684c4bc43dab3d3dcae31f
```

The deterministic SRAM fixture is exactly 32768 bytes.

M7 must continue from `recomp/handoff/M6_NEXT.md`.
