"""Read original map graphics from the repository; never modifies game state.

Bank 0 $19B7-$1A1E selects a flag-dependent map table from bank 17.
Bank 0 $0CF5/$0DA8 decompresses literal bytes or marker/back-reference runs.
This tool mirrors that data format for inspection only, not CPU execution.
"""
import argparse
from pathlib import Path
from scan_game_modes import parse

ROOT = Path(__file__).resolve().parents[2]
BANKS = {}

def bank(number):
    if number not in BANKS:
        BANKS[number] = parse(ROOT / f"src/banks/bank_{number:03}.asm")
    return BANKS[number]

def byte(number, address):
    return bank(number)[address - (0x4000 if number else 0)]

def word(number, address):
    return byte(number, address) | byte(number, address + 1) << 8

def decompress(number, address):
    length = word(number, address)
    marker = byte(number, address + 2)
    address += 3
    result = bytearray()
    while len(result) < length:
        value = byte(number, address)
        address += 1
        if value != marker:
            result.append(value)
            continue
        low, high = byte(number, address), byte(number, address + 1)
        address += 2
        offset = low | (high >> 4) << 8
        count = (high & 15) + 4
        if count == 19:
            # Original ADD A,$13 and DEC use an eight-bit counter. Zero
            # executes 256 copies; values above 255 wrap before the loop.
            count = (count + byte(number, address)) & 255
            if count == 0:
                count = 256
            address += 1
        for index in range(offset, offset + count):
            if len(result) == length:
                break
            # 0:$0D50-$0D77 adjusts the dictionary address on every byte,
            # including references that cross $FFF -> $000 within a run.
            index &= 0xFFF
            result.append(result[index] if index < len(result) else 0)
    return bytes(result)

def map_grid(world, flags):
    header = word(17, 0x44B8 + world * 2)
    width, height = byte(17, header + 6), byte(17, header + 7)
    mask_address = word(17, header + 16)
    mask = flags[mask_address] if flags is not None else 0
    choice = next((bit + 1 for bit in range(7, -1, -1) if mask & (1 << bit)), 0)
    descriptor = header + 18 + 6 * choice
    table, number = word(17, descriptor), byte(17, descriptor + 2)
    maps = []
    for y in range(height):
        row = []
        for x in range(width):
            entry = table + 3 * (y * width + x)
            data = decompress(byte(number, entry + 2), word(number, entry))
            if len(data) != 360:
                raise ValueError(f"Unexpected screen tile count: {len(data)}")
            row.append(data)
        maps.append(row)
    return width, height, maps

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("world", type=int)
    parser.add_argument("--dump", type=Path)
    args = parser.parse_args()
    ram = args.dump.read_bytes() if args.dump else None
    width, height, maps = map_grid(args.world, ram)
    print(f"Original world {args.world}: {width} x {height} screens")
    # One hex pair per 16x16 metatile (top-left tile of the 2x2 graphic).
    # This is a visual index only: collision/warp semantics require evidence.
    for ry in range(height):
        for y in range(9):
            print(" | ".join(" ".join(f"{maps[ry][rx][y*40+x*2]:02x}" for x in range(10))
                             for rx in range(width)))
        print()

if __name__ == "__main__":
    main()
