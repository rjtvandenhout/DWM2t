#!/usr/bin/env python3
"""Milestone M1 validation for the complete LR35902 static-recomp frontend."""

from __future__ import annotations
import argparse
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from lr35902 import Kind, decode_all_offsets, decode_one, validate_complete_decoder

DB_LINE = re.compile(r"^\s*db\b", re.IGNORECASE)
BYTE = re.compile(r"\$([0-9A-Fa-f]{2})\b")

def load_bank(path: Path) -> bytes:
    out = bytearray()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not DB_LINE.match(line):
            continue
        out.extend(int(m.group(1), 16) for m in BYTE.finditer(line))
    if len(out) != 0x4000:
        raise SystemExit(f"{path}: parsed {len(out)} bytes, expected 16384")
    return bytes(out)

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bank0", type=Path, default=Path("src/banks/bank_000.asm"))
    args = ap.parse_args()

    validate_complete_decoder()
    bank = load_bank(args.bank0)
    decoded = decode_all_offsets(bank)
    assert len(decoded) == 0x4000

    assert decode_one(bank, 0x0040).mnemonic == "DI"
    assert decode_one(bank, 0x0041).mnemonic == "JP $03A4"
    assert decode_one(bank, 0x0949).mnemonic == "LD D,A"
    assert decode_one(bank, 0x095B).mnemonic == "PUSH HL"
    assert decode_one(bank, 0x1679).mnemonic == "LD A,(DE)"

    illegal_offsets = sum(1 for x in decoded if x.kind is Kind.ILLEGAL)
    cb_offsets = sum(1 for x in decoded if x.kind is Kind.CB)

    print("M1 LR35902 decoder: PASS")
    print("  base legal opcodes: 245 / 245")
    print("  base illegal opcodes represented: 11 / 11")
    print("  CB-prefixed opcodes: 256 / 256")
    print(f"  Bank 0 independent entry decodes: {len(decoded)} / 16384")
    print(f"  Bank 0 offsets decoding as CB prefix: {cb_offsets}")
    print(f"  Bank 0 offsets decoding as illegal opcode: {illegal_offsets}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
