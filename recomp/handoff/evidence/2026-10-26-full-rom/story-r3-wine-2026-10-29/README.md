# Original story checkpoint replay on Wine

On 2026-10-29, the retained set of 38 original-input story checkpoints passed under Wine using the full-bank Windows diagnostic built from source `1351bcd058e491455a477045a2ff86bbc3bd7b1c` in the cancelled Actions run `40799717118`. The diagnostic executable SHA-256 was `4d96e9c8d0318c0018057469365588e6becbdf2505def77d55cd967c1f4df11e`. Each stage used the pinned genuine original Journal and original P1 route, created a Journal and passed fresh Continue; all 38 newly replayed parent/output Journal links were audited. No save or game-memory injection was used.

The ending route passed the recorded screen-hash assertions for Darck defeated, credits start, credits final and THE END at frames 139859, 183818, 200072 and 204957 respectively, then matched the original ending Journal and passed fresh Continue. The generic executable log prints `ending_credits=NOT_YET_PROVEN` as a fixed checkpoint message; the wrapper separately verifies the four timed route assertions and their ordering, as recorded in the passed report.

The retained [Darck](../screenshots/ending-darck-defeated.bmp), [credits start](../screenshots/ending-credits-start.bmp), [credits final](../screenshots/ending-credits-final.bmp) and [THE END](../screenshots/ending-the-end.bmp) images are **historical captures from source `81cfb26`**, not newly saved R3 images. The R3 replay checked the same expected screen hashes at those moments. Their original provenance and hashes are in [ending-observation-witnesses.json](../ending-observation-witnesses.json).

The unmodified BMPs below are captures from this R3 replay at the completed checkpoints, after the interactions:

- [Ending Journal checkpoint](ending-complete-checkpoint.bmp) and [fresh Continue](ending-fresh-continue.bmp)
- [Sky completion checkpoint](sky-complete-checkpoint.bmp)
- [Ice world entry checkpoint](ice-world-entry-checkpoint.bmp)
- [C-class victory checkpoint](c-class-victory-checkpoint.bmp)

The unmodified [story report](story-checkpoints-validation.json), [ending log](ending-native.log) and [P1 trace](ending-trace-p1.txt) identify files in the original scratch run at `/workspace/scratch/full-rom-2026-10-26/independent-story-r3-01/`; not all referenced files are included here. SHA-256 values are `276c3a1fea918b938254d591297369e5d606d31056380eb261931b3306a033dc` for the report, `78ecd0a09717d518e81b0bd0c73e0079428562ba4ce32700bd6c906fd65c475b` for the log and `7c34ed68a05cb1e3453adf48c81bcd5916060e4c20018e9ad860fe6ca7d9ac3d` for the trace.

This is supplementary Wine evidence for the earlier diagnostic build. It does not replace native Windows acceptance of the fresh build or prove every optional path or random seed. No saves or executables are included here.
