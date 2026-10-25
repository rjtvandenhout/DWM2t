# Accepted M8 evidence

The accepted native/packaging run is
[40183484388](https://github.com/rjtvandenhout/DWM2t/actions/runs/40183484388),
using validation tools `8859ef67289ce90712a44b9c17174de4519a59b3`.
The unchanged diagnostic/production game binaries were independently built
from `3d573873ae8122cbb10fcd5d0f7ae7a33a7609ba` in run 40175408153.

Start with `final-acceptance-audit.json`, `verified-package.json`,
`verified-artifact-audit.json`, `native-tests-windows.xml`,
`final-package-windows.json` and `final-ending-journal-windows.json`.
`artifacts.json` distinguishes original Actions ZIPs from the inner player ZIP
and records each preserved evidence file's SHA256.

Accepted coverage is all 38 original Windows story checkpoints, all 18 executed
native tests with zero failures/skips, 21 actual Play.cmd checks, original ending
Journal/fresh reload, and Windows/POSIX persistence contracts. Story audit also
checks all 38 freshly replayed parent links and all 115 archived 32-KiB Journals.

The `original-*-unaccepted` records contain two genuine unavailable-device
skips. The `legacy-audio-*-failed` records contain the later actual stream-gate
failure. They remain unaccepted; their bytes were not rewritten. Controlled
current-driver probe records document five clean original stream runs before
the complete accepted native suite. CI uses a genuine signed virtual render
endpoint; physical speaker audibility is not measured.

JSON/XML/log files copied from Windows retain their original bytes and line
endings. Independent audit JSONs are separately identified by filename.
The complete input Journals and large binaries remain in the referenced
Actions artifacts and local delivery, outside Git. The player ZIP bundles no
user/test Saves. Optional postgame paths are not exhaustively tested.
