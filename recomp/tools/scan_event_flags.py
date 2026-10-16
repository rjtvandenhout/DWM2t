#!/usr/bin/env python3
import argparse
import pathlib
import re

DB_RE = re.compile(r"^\s*db\s+(.*)$", re.IGNORECASE)
HEX_RE = re.compile(r"\$([0-9A-Fa-f]{2})")

def parse_bank(path: pathlib.Path) -> bytes:
    out = bytearray()
    for line in path.read_text(encoding="utf-8").splitlines():
        m = DB_RE.match(line)
        if m:
            out.extend(int(x, 16) for x in HEX_RE.findall(m.group(1)))
    return bytes(out)

def find_all(data: bytes, needle: bytes):
    start = 0
    while True:
        pos = data.find(needle, start)
        if pos < 0:
            return
        yield pos
        start = pos + 1

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--banks-dir", type=pathlib.Path, required=True)
    ap.add_argument("--flags", nargs="+", required=True)
    args = ap.parse_args()
    flags = [int(v, 0) for v in args.flags]
    refs = 0
    for path in sorted(args.banks_dir.glob("bank_*.asm")):
        bank = int(path.stem.split("_")[-1])
        data = parse_bank(path)
        base = 0 if bank == 0 else 0x4000
        for flag in flags:
            lo, hi = flag & 0xFF, (flag >> 8) & 0xFF
            patterns = {
                "check": bytes([0x11, lo, hi, 0xCD, 0x1B, 0x18]),
                "set": bytes([0x11, lo, hi, 0xCD, 0x45, 0x18]),
            }
            for op, needle in patterns.items():
                for off in find_all(data, needle):
                    refs += 1
                    print(f"M7_FLAG_REF flag=0x{flag:04x} op={op} bank={bank} pc=0x{base + off:04x} file={path.name}")
    print(f"M7_FLAG_SCAN_COMPLETE refs={refs}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
