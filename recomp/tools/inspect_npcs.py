"""Read the original bank-105 NPC tables using an observed flag dump."""
import argparse
from pathlib import Path
from scan_game_modes import parse

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("dump", type=Path)
parser.add_argument("--world", type=int, required=True)
parser.add_argument("--width", type=int, required=True)
parser.add_argument("--height", type=int, required=True)
args = parser.parse_args()
bank = parse(Path(__file__).resolve().parents[2] / "src/banks/bank_105.asm")
ram = args.dump.read_bytes()
def byte(pc): return bank[pc - 0x4000]
def word(pc): return byte(pc) | (byte(pc + 1) << 8)
def flag(value): return bool(ram[0xCBD7 + value // 8] & (1 << (value % 8)))
def records(pc):
    for _ in range(100):
        low, high = byte(pc), byte(pc + 1)
        pc += 2
        if high != 0xFF:
            if flag(low | high << 8): pc += 2; continue
        elif low == 0xFF: return []
        elif low == 0xFE: pass
        elif low == 0xFD:
            first, second = word(pc), word(pc + 2)
            pc += 4
            if flag(first) or flag(second): pc += 2; continue
        elif low in (0xFC, 0xFB):
            condition = flag(word(pc)); pc += 2
            jump = byte(pc); pc += 2
            if condition == (low == 0xFB): pc += jump
            continue
        else: raise ValueError(f"Unsupported marker {high:02x}{low:02x}")
        target = word(pc)
        count = byte(target)
        if count > 5: raise ValueError(f"Bad NPC count {count} at {target:04x}")
        return [bank[target - 0x4000 + 1 + i * 11:target - 0x4000 + 12 + i * 11]
                for i in range(count)]
    raise ValueError("NPC condition cycle")

grid = word(0x4174 + args.world * 2)
for y in range(args.height):
    for x in range(args.width):
        pointer = word(grid + 2 * (y * args.width + x))
        if not pointer: continue
        for npc in records(pointer):
            print(f"world={args.world} region={x},{y} selector={npc[10]:02x} "
                  f"sprite={npc[2]:02x}/{npc[3]:02x} pos={npc[5]:02x},{npc[6]:02x} "
                  f"raw={npc.hex(' ')}")
