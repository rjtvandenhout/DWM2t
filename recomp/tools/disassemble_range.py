"""Disassemble an explicit range of the repository's matching source bank."""
import argparse
from pathlib import Path
from lr35902 import decode_one
from scan_game_modes import parse

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("bank", type=int)
parser.add_argument("start", type=lambda x: int(x, 0))
parser.add_argument("length", type=lambda x: int(x, 0))
args = parser.parse_args()
root = Path(__file__).resolve().parents[2]
data = parse(root / "src" / "banks" / f"bank_{args.bank:03}.asm")
base = 0x4000 if args.bank else 0
pc = args.start
while pc < min(base + len(data), args.start + args.length):
    inst = decode_one(data, pc - base)
    raw = data[pc - base:pc - base + inst.size]
    print(f"{args.bank:03}:{pc:04X} {raw.hex(' '):<9} {inst.mnemonic}")
    pc += inst.size
