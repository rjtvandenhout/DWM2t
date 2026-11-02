# Five bounded S Class timing variants

Each trial started in a fresh diagnostic process from the genuine level-41 Garon / 5688G Journal SHA-256 `a261d433e47f1ad62fbcdf43e6095d49afd170ad0ebe2aedf22f4964b572f797`. The original full-ROM executable SHA-256 was `61a0e6d3ff84b5322b101247fc93ff6889f123a1bcd94df663135757fb3b9855`, running under Wine on Linux. The original controller selected Defense for Garon and Charge for Slash and Derzo. The only deliberately varied input was a finite wait at the original Arena dialogue; no memory, RNG, money, item or save bytes were injected. Each entry below is a separate original-input attempt and retained its actual loss screen.

| Trial | No-button wait | Observed result | Evidence |
| --- | ---: | --- | --- |
| 1 | 73 frames | Won battle one; lost battle two | [Loss](trial-1-loss.bmp), [trace](trial-1-trace.txt) |
| 2 | 147 frames | Won battles one and two; lost battle three | [Battle-two win](best-trial-round2-win.bmp), [battle-three start](best-trial-round3-start.bmp), [loss](trial-2-loss.bmp), [trace](trial-2-trace.txt) |
| 3 | 221 frames | Lost battle one | [Loss](trial-3-loss.bmp), [trace](trial-3-trace.txt) |
| 4 | 295 frames | Won battle one; lost battle two | [Loss](trial-4-loss.bmp), [trace](trial-4-trace.txt) |
| 5 | 369 frames | Won battle one; lost battle two | [Loss](trial-5-loss.bmp), [trace](trial-5-trace.txt) |

The best attempt's third battle began with Slash at 75 HP, Derzo at 207 HP and Garon unconscious. A separate original-input replay by another agent reproduced that exact state and tried Slash Charge / Derzo Defense; it also lost the final battle. That independent trial and four other original variants are documented in the [separate five-trial report](../2026-11-02-arena-s-variants/README.md). Across these ten bounded trials no S champion announcement, reward or post-victory Journal was observed. These ten outcomes do not prove S Class is impossible.

The original diagnostic commands, P1/observation traces, driver logs, screenshots and [structured observations](own-trials-observation.json) are retained for all five trials. The [driver](original-input-driver.py) uses local scratch paths and helper modules and is not a self-contained reproduction by itself; exact original commands and traces are retained separately. A [checksum manifest](sha256sums.txt) covers the evidence files. Actual game saves, RAM snapshots, ROMs and executables are not included. Squiz was not used or bred.
