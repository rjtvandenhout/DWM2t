#!/usr/bin/env python3
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
manifest = json.loads((ROOT / "decomp_manifest.json").read_text())
banks = sorted((ROOT / "src" / "banks").glob("bank_*.asm"))
known = ROOT / "symbols" / "known_regions.csv"

print(f"Target: {manifest['title']}")
print(f"ROM size: {manifest['size']:,} bytes")
print(f"Bank files: {len(banks)}/{manifest['banks']}")
print(f"Byte-covering baseline: {'YES' if len(banks) == manifest['banks'] else 'NO'}")
if known.exists():
    rows = [x for x in known.read_text().splitlines()[1:] if x.strip()]
    print(f"Verified named regions: {len(rows)}")
print("Semantic coverage is tracked by verified named regions, not by pretending raw db blocks are understood.")
