#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, zlib
from pathlib import Path

EXPECTED_SIZE = 4_194_304
EXPECTED_SHA256 = "8e38a7420ef5239c7196aa4fd4b1499e65db2823e875bbf8241bb2199e766d4e"
EXPECTED_SHA1 = "76901b7e5cadf9611dd4fac52e8501155c1e33a2"
EXPECTED_MD5 = "f71ac6ac4bb335f59bfd2b594d47ab49"
EXPECTED_CRC32 = "AB7BFDD5"

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("rom", type=Path)
    args = ap.parse_args()
    data = args.rom.read_bytes()
    values = {
        "Size": str(len(data)),
        "SHA-256": hashlib.sha256(data).hexdigest(),
        "SHA-1": hashlib.sha1(data).hexdigest(),
        "MD5": hashlib.md5(data).hexdigest(),
        "CRC32": f"{zlib.crc32(data) & 0xffffffff:08X}",
    }
    for k, v in values.items():
        print(f"{k}: {v}")
    ok = (
        len(data) == EXPECTED_SIZE and
        values["SHA-256"] == EXPECTED_SHA256 and
        values["SHA-1"] == EXPECTED_SHA1 and
        values["MD5"] == EXPECTED_MD5 and
        values["CRC32"] == EXPECTED_CRC32
    )
    print("MATCH" if ok else "MISMATCH")
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())
