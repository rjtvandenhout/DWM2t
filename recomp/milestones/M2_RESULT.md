# M2 completion record

Milestone M2 was accepted after the Windows x64 GitHub Actions run completed successfully.

## Passing source

```text
e68bd3e1136f93982a33d755d20bd3b093a6f7b5
```

Restore branch:

```text
restore/recomp-m2
```

## CI evidence

Workflow run:

```text
38819460960
```

Bank 0 audit:

```text
entry addresses: 16384
base decodes: 15726
CB decodes: 382
illegal decodes: 276
bank-boundary operand fetches: 0
```

Native executable self-test:

```text
Bank 0 translated entry coverage 16384/16384: PASS
Bank 0 $0949 memset: PASS
Bank 0 $1679 memcpy: PASS
Bank 0 $095B RNG/table routine: PASS
LR35902 arithmetic/DAA flag edges: PASS
```

Generated Windows artifact:

```text
DWM2tRecomp-M2-Windows-x64
artifact id: 12012103231
artifact zip SHA-256: bd8534ea8f75c8cef31623a93e6ea724b5f138fbfd4f6c8606dce7da6119ac03
```

## Next action

Continue strictly with `recomp/handoff/M2_NEXT.md`. The next milestone is M3:
the headless Game Boy hardware/runtime layer. Do not start rendering or title-screen
work before the M3 acceptance tests are green.
