#!/usr/bin/env python3
"""Generate the byte-exact RGBDS bank source from the verified Cobi ROM."""
from __future__ import annotations
import argparse, hashlib
from pathlib import Path

EXPECTED_SHA256 = "8e38a7420ef5239c7196aa4fd4b1499e65db2823e875bbf8241bb2199e766d4e"
ROM_SIZE = 0x400000
BANK_SIZE = 0x4000
BANK_COUNT = ROM_SIZE // BANK_SIZE

def write_bank(path: Path, bank: int, data: bytes) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        if bank == 0:
            f.write('SECTION "ROM Bank 000", ROM0[$0000]\n')
        else:
            f.write(f'SECTION "ROM Bank {bank:03d}", ROMX[$4000], BANK[$' + f'{bank:02X}' + ']\n')
        start = bank * BANK_SIZE
        f.write(f'; File offsets $' + f'{start:06X}' + '-$' + f'{start + BANK_SIZE - 1:06X}' + '\n')
        for i in range(0, len(data), 16):
            row = data[i:i+16]
            f.write("    db " + ", ".join(f"$" + f"{b:02X}" for b in row) + "\n")

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("rom", type=Path)
    ap.add_argument("--out-dir", type=Path, default=Path("src/banks"))
    ap.add_argument("--force", action="store_true", help="allow a non-matching input ROM")
    args = ap.parse_args()

    data = args.rom.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if len(data) != ROM_SIZE:
        raise SystemExit(f"wrong ROM size: {len(data)} bytes; expected {ROM_SIZE}")
    if digest != EXPECTED_SHA256 and not args.force:
        raise SystemExit(f"wrong ROM SHA-256: {digest}\nexpected: {EXPECTED_SHA256}")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    for bank in range(BANK_COUNT):
        write_bank(args.out_dir / f"bank_{bank:03d}.asm", bank,
                   data[bank*BANK_SIZE:(bank+1)*BANK_SIZE])

    main_asm = args.out_dir.parent / "main.asm"
    main_asm.write_text(
        "; Bit-perfect DWM2 Cobi decompilation root\n" +
        "".join(f'INCLUDE "src/banks/bank_{b:03d}.asm"\n' for b in range(BANK_COUNT)),
        encoding="utf-8",
    )
    print(f"generated {BANK_COUNT} banks from {digest}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
