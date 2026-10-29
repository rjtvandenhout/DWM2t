# Fresh R4 diagnostic evidence

The Windows diagnostic job of [Actions run 40806942912](https://github.com/rjtvandenhout/DWM2t/actions/runs/40806942912) passed on source `1351bcd058e491455a477045a2ff86bbc3bd7b1c`. The diagnostic executable SHA-256 is `61a0e6d3ff84b5322b101247fc93ff6889f123a1bcd94df663135757fb3b9855`. It is a separate build from the production candidate. The completed run later failed in the production local-link GUI gate, so this diagnostic evidence does **not** establish final player/package acceptance.

The independent [audit receipt](audit.json) records verification of the original GitHub ZIP digests, all 18 native tests with no failures or skips, the exact source archive and 255 switchable ROM banks, 38 original story checkpoints, and seven retained postgame checkpoints. Every actual 32 KiB checkpoint and parent-to-seed link was rehashed against the recorded route and manifest, with trace and fresh Continue markers checked. The original source and ROM identities and seed-bundle hashes are also recorded. This is coverage of those specific paths, not a claim that every possible seed or optional game path has been played.

The unmodified captures below were copied from the diagnostic story and postgame artifacts; screenshots show the last frame of the named checkpoint or its fresh Continue, not an entire playthrough:

- [Ending checkpoint at home](ending-checkpoint.bmp), SHA-256 `61e976b7febb7a7d2a9cf01b4e6d43d2049d0aff8b963458c53e9f9007df81aa`, and [fresh Continue](ending-fresh-continue.bmp), SHA-256 `89e152b42c5215e2214b56dcbf105be04f768d395f53717878d430e897afc385`
- [Key appraisal checkpoint](key-appraisal-checkpoint.bmp), SHA-256 `f28e8bbd019ace662dc1606c4e223e71967deeccd082e882c9f39fa7876e4500`
- [QuietSea clear checkpoint](quietsea-clear-checkpoint.bmp), SHA-256 `42552c2143528134b92d01c32ec6d4d524486102d6cf4301689836cea053f393`
- [QuietSea in-dungeon reload checkpoint](quietsea-dungeon-checkpoint.bmp), SHA-256 `9a093eff63c0663090ea414dbb27a09108546fe4a75e151c8037892782bb410f`

Audit receipt SHA-256: `1a9300f68219aaa3b672773a62cc7698cf29f156f5dd3d5015e247a96b2ee9e4`. No Journal save files or executables are included in this folder.
