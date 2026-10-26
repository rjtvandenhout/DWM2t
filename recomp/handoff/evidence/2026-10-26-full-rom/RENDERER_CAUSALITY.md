# Same-live-Memory rendering comparison at Kids victory

The sole cause of the frame-14370 screen difference is completed per-scanline scroll preservation. On the **same const live Memory object**, the current renderer produces `be55670a278cea50`; both the exact old renderer and the current renderer with only scanline-scroll selection disabled produce the original expected `9a38ae3eef2d8568`.

| Renderer | Framebuffer hash |
| --- | --- |
| Frozen81cfb current | be55670a278cea50 |
| Exact old3d renderer, class renamed only | 9a38ae3eef2d8568 |
| Frozen81cfb current, sole feature ablation: `scanline_scroll = false` | 9a38ae3eef2d8568 |

The actual completed scanline values are SCX=0 for all144 rows, SCY=2 for rows0 through16 inclusive, and SCY=0 for rows17 through143. Live IO SCX/SCY are both0. LCDC=0x83, C5E1=0 and every OAM byte is0. Current versus either flat renderer differs by exactly688 pixels, bounded by x1..158 and y0..15; row16 has no pixel difference despite its recorded SCY2. Old3d versus current flat-scroll ablation has zero pixel differences.

The read-only observation records all144 scanline values plus VRAM banks0/1, CGB BG/OBJ palettes and OAM. Relevant render-state fingerprints are identical before/after all three renders: `a67263790addbf05`. The current BMP is byte-for-byte identical to the native Windows production observation `m8_315.bmp` (SHA256 `96dbaad0e2ab58589ba0defa7d0f35326584d00e0db31d88cbd276db2f2de1fe`). Both flat renderer BMPs are byte-for-byte identical to each other (SHA256 `723b981d59c86d9a3b76a07144081e155e7f99b187890a9c7a9ca49ee883d5aa`).

This is a diagnostic result, **not replay acceptance**. The exact original expected screen guard remains unchanged and throws immediately after the read-only observations; native return230 ends with `M8_REPLAY_FAIL recorded hash assertion failed`. Original game inputs and all linked objects were rehashed unchanged. Audio guards remain observational as in the frozen parent Linux diagnostic producer; all non-audio assertions remain strict. No runtime state, ROM, save, flags, RNG, expected screen or tracked source was edited.

The current renderer selects completed scroll history at frozen `source/recomp/src/renderer.cpp:99,108–111`. Frozen Memory publishes completed lines at `source/recomp/src/memory.cpp:611`. Independent original-ROM analysis also identifies the bank0:$04ED shake-counter routine that can write SCY at$050F independently of C5E1. This probe did not trace the identity of each IO writer, so it does not attribute this particular pin to one exact original shake instruction.

## Reproduction and receipts

- Full observation: `run-03/renderer_causality/same-memory-renderer-causality.json`.
- Immutable input/object recheck and actual failing return: `run-receipt-03.json`.
- Same-current-native BMP bytes: `bmp-crosschecks.json`.
- Exact genuine seed/P1 hashes and invocation: `replay-invocation-03.json`.
- Full linked objects, private augmentation commands and hashes: `additional-aot-provenance-03.json`.
- Helper source provenance: `preparation.json`, `add-bank242-provenance.json`.
- Original strict screen guard preserved in `m8_renderer_observer.cpp`; all added helper renderers accept const Memory.
- Actual diagnostic replay log: `replay-03.log`.

The private diagnostic reuses the sealed original61-bank observer objects. Actual original P1 execution first encountered missing bank242 at$6692, then bank12 at$659F. Each failure is retained as runs01/02. Only those two additional original banks were generated from frozen81cfb source using its original AOT generator, along with a private expanded registry. There is no instruction fallback and no claim that this diagnostic includes all256 banks. Neither shared source nor shared objects was changed. Run03 reached the required original pin in24.25 seconds after linking.
