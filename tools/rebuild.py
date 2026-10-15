#!/usr/bin/env python3
"""Rebuild the exact ROM from the raw RGBDS db bank source."""
from __future__ import annotations
import argparse, re
from pathlib import Path

BANK_COUNT = 256
BANK_SIZE = 0x4000
DB_RE = re.compile(r"^\s*db\s+(.+?)\s*(?:;.*)?$", re.IGNORECASE)
HEX_RE = re.compile(r"\$([0-9a-fA-F]{2})\b")

def parse_bank(path: Path) -> bytes:
    out = bytearray()
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        m = DB_RE.match(line)
        if not m:
            continue
        vals = HEX_RE.findall(m.group(1))
        if not vals:
            raise ValueError(f"{path}:{lineno}: db without byte literals")
        out.extend(int(v, 16) for v in vals)
    if len(out) != BANK_SIZE:
        raise ValueError(f"{path}: {len(out)} bytes; expected {BANK_SIZE}")
    return bytes(out)

def rebuild(src: Path) -> bytes:
    chunks = []
    for bank in range(BANK_COUNT):
        path = src / f"bank_{bank:03d}.asm"
        if not path.exists():
            raise FileNotFoundError(path)
        chunks.append(parse_bank(path))
    return b"".join(chunks)

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=Path("src/banks"))
    ap.add_argument("--out", type=Path, default=Path("build/dwm2_cobi.gbc"))
    args = ap.parse_args()
    data = rebuild(args.src)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(data)
    print(f"wrote {len(data)} bytes to {args.out}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
