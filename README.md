# DWM2t — Dragon Warrior Monsters 2: Cobi's Journey decompilation

This repository is the canonical reverse-engineering/decompilation workspace for the USA release of **Dragon Warrior Monsters 2: Cobi's Journey**.

## Target ROM

The source was generated from the user-provided clean ROM dump with:

- Size: `4,194,304` bytes (`0x400000`)
- SHA-256: `8e38a7420ef5239c7196aa4fd4b1499e65db2823e875bbf8241bb2199e766d4e`
- SHA-1: `76901b7e5cadf9611dd4fac52e8501155c1e33a2`
- MD5: `f71ac6ac4bb335f59bfd2b594d47ab49`
- CRC32: `AB7BFDD5`

The original ROM is **not required in the repository** after the source has been generated. Every byte of the 4 MiB ROM is represented in `src/banks/`.

## Current state

`src/` provides **100% byte coverage** of the target ROM in RGBDS-compatible assembly. The first goal of this project is reproducibility: the source can be rebuilt into a byte-identical ROM and verified against the SHA-256 above.

This is a complete *matching disassembly baseline*, not a claim that every routine has already been given a human-readable semantic name. Known systems are being progressively converted from raw `db` regions into labelled assembly/data structures without changing the resulting ROM hash. See `docs/PROJECT_STATUS.md` and `research/`.

## Build / verify

A dependency-free Python rebuilder is included:

```bash
python tools/rebuild.py --out build/dwm2_cobi.gbc
python tools/verify.py build/dwm2_cobi.gbc
```

Or simply:

```bash
make verify
```

Expected SHA-256:

```text
8e38a7420ef5239c7196aa4fd4b1499e65db2823e875bbf8241bb2199e766d4e
```

### RGBDS

The same source layout is intentionally valid RGBDS source. With RGBDS installed:

```bash
make rgbds
```

Do **not** run `rgbfix` on the output when checking for a byte-identical match; the ROM header/checksum bytes are already present in source.

## Regenerating the raw matching source

If you want to regenerate the bank files from your own clean dump:

```bash
python tools/decompile.py path/to/baserom.gbc
```

The script refuses a ROM with the wrong SHA-256 unless `--force` is explicitly supplied.

## Repository layout

- `src/main.asm` — RGBDS entry point.
- `src/banks/` — all 256 × 16 KiB ROM banks, byte-exact.
- `tools/decompile.py` — ROM → matching assembly bank source.
- `tools/rebuild.py` — matching assembly → ROM, no third-party dependencies.
- `tools/verify.py` — hash/size validation.
- `research/` — extracted tables and verified runtime-mechanics research.
- `docs/` — ROM map, sprite notes, runtime notes, workflow/status.

## Rule for future edits

A semantic cleanup is only considered accepted when `make verify` still reproduces the target SHA-256. That keeps reverse engineering honest: names can improve, bytes cannot drift accidentally.

## Legal note

This repository is a reverse-engineering research project. No license is asserted over the original game code, graphics, text, music, or other copyrighted game content. The original cartridge/ROM dump should be obtained lawfully by the user.


## Matching decompilation status

The repository now contains a complete byte-covering RGBDS assembly baseline for the verified USA Cobi's Journey ROM:

- 256 ROM banks represented under `src/banks/`.
- 4,194,304 bytes covered by source.
- Target SHA-256: `8e38a7420ef5239c7196aa4fd4b1499e65db2823e875bbf8241bb2199e766d4e`.
- `make verify` rebuilds the image using the repository's deterministic Python rebuilder and checks all known hashes.
- `make rgbds` assembles and links the same source with RGBDS.
- GitHub Actions verifies both rebuild paths are byte-identical to the target.

This is a **matching disassembly baseline**, not a claim that every routine and data block has already been semantically named or rewritten. Known mechanics, tables, sprites and offsets are documented under `docs/`; semantic decompilation can proceed incrementally while exact-output CI prevents regressions.
