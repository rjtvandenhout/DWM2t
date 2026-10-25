# M1 handoff: complete LR35902 frontend

## Restore point

After M1 is accepted, `restore/recomp-m1` must point at the exact passing M1 head.

M0 is permanently recoverable at:

```text
restore/recomp-m0
ac588dc73f59020efc69a53d17c46db6c7286acd
```

## What M1 establishes

- all 245 legal LR35902 base opcodes decode;
- all 11 illegal Game Boy CPU opcodes are explicit;
- all 256 CB-prefixed opcodes decode;
- instruction sizes and immediate operands are stable metadata;
- every byte offset in Bank 0 can be independently decoded as a possible entry point;
- CI validates decoder completeness before building the native executable.

## Instructions to continue to M2

1. Do not turn the frontend into a runtime opcode interpreter.
2. Add a C++ semantic backend with the opcode as a compile-time template argument.
3. Generate native C++ entry translations for all 16,384 Bank 0 addresses.
4. Embed the exact Bank 0 image for reads of constants/data.
5. Expand CPU state with PC, SP, AF, IME and trap/stop state.
6. Implement exact flags for arithmetic, DAA, rotations, shifts, stack and branches.
7. Regression-test Bank 0 routines at `$0949`, `$095B` and `$1679`.
8. Compile the generated Bank 0 translation into the Windows executable in CI.
9. Declare M2 complete only after the Windows self-test passes.
10. Create `restore/recomp-m2` and write `M2_NEXT.md`.

## Deferred to M3

MBC5 banking, mapped VRAM/OAM, hardware interrupt scheduling, timers, joypad side effects, HALT-bug fidelity and the native renderer belong to the hardware/runtime milestone.
