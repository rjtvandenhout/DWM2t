#!/usr/bin/env python3
"""
DWM2 Cobi's Journey (USA) sprite extractor.

This script contains no ROM data. Point it at your own ROM dump.

Verified target SHA-256:
8e38a7420ef5239c7196aa4fd4b1499e65db2823e875bbf8241bb2199e766d4e

Requires:
    pip install pillow
"""

from pathlib import Path
from PIL import Image
import argparse, hashlib, json, math, csv, shutil

EXPECTED_SHA256 = "8e38a7420ef5239c7196aa4fd4b1499e65db2823e875bbf8241bb2199e766d4e"

BATTLE_PTR_TABLE = 0x0E0001
BATTLE_PAL_TABLE = 0x09F328
BATTLE_COUNT = 383

OW_GFX_PTR_TABLE = 0x0103AC
OW_PAL_MAP = 0x010A46
OW_PAL_TABLE = 0x1F8B15
OAM_PTR_TABLE = 0x1FC008
OW_COUNT = 98

OW_FIXED_W = 64
OW_FIXED_H = 48
OW_ANCHOR_X = 32
OW_ANCHOR_Y = 40

def cpu_to_abs(bank, ptr):
    return ptr if bank == 0 else bank * 0x4000 + (ptr - 0x4000)

def bgr555_to_rgb(v):
    return tuple(round(c * 255 / 31) for c in (v & 31, (v >> 5) & 31, (v >> 10) & 31))

def read_palette(rom, off):
    out = []
    for i in range(4):
        v = rom[off + i*2] | (rom[off + i*2 + 1] << 8)
        out.append(bgr555_to_rgb(v))
    return out

def decompress(rom, off, dest=0x8000):
    """Reimplementation of the game's graphics decompressor at CPU $0CF5."""
    outlen = rom[off] | (rom[off+1] << 8)
    marker = rom[off+2]
    src = off + 3
    out = bytearray(outlen)
    pos = 0
    start = dest
    end = dest + outlen

    while pos < outlen:
        a = rom[src]
        src += 1
        if a != marker:
            out[pos] = a
            pos += 1
            continue

        low = rom[src]
        ctl = rom[src+1]
        src += 2
        count = (ctl & 0x0F) + 4
        if count == 19:
            count = rom[src] + 19
            src += 1

        addr = start + ((ctl >> 4) << 8) + low
        if addr > end:
            addr -= 0x1000

        for _ in range(count):
            if pos >= outlen:
                break
            if addr < start or addr >= end:
                value = 0
            else:
                value = out[addr - start]
            out[pos] = value
            pos += 1
            addr += 1

    return bytes(out), src - off

def decode_tile(tile, palette, transparent_index=0):
    img = Image.new("RGBA", (8, 8), (0,0,0,0))
    px = img.load()
    colors = [(*c, 0 if i == transparent_index else 255) for i,c in enumerate(palette)]
    for y in range(8):
        lo = tile[y*2]
        hi = tile[y*2+1]
        for x in range(8):
            bit = 7-x
            idx = (((hi >> bit) & 1) << 1) | ((lo >> bit) & 1)
            px[x,y] = colors[idx]
    return img

def signed8(v):
    return v - 256 if v >= 128 else v

def battle_sprite(rom, cid):
    p = BATTLE_PTR_TABLE + cid*3
    ptr = rom[p] | (rom[p+1] << 8)
    bank = rom[p+2]
    source = cpu_to_abs(bank, ptr)
    raw, used = decompress(rom, source)
    if len(raw) != 0x240:
        raise ValueError(f"Core ID {cid}: expected 0x240 decompressed bytes, got {len(raw):#x}")

    poff = BATTLE_PAL_TABLE + cid*8
    palette = read_palette(rom, poff)
    img = Image.new("RGBA", (48,48), (0,0,0,0))
    for t in range(36):
        tile = decode_tile(raw[t*16:(t+1)*16], palette)
        img.alpha_composite(tile, ((t % 6)*8, (t // 6)*8))
    return img, {
        "core_id": cid, "graphics_bank": bank, "graphics_cpu_pointer": f"0x{ptr:04X}",
        "graphics_rom_offset": f"0x{source:06X}", "compressed_bytes_used": used,
        "palette_rom_offset": f"0x{poff:06X}",
        "palette": ["#%02X%02X%02X" % c for c in palette]
    }

def ow_definition_ptr(rom, sid):
    a = OAM_PTR_TABLE + sid*2
    return rom[a] | (rom[a+1] << 8)

def ow_frame_ptrs(rom, sid):
    dp = ow_definition_ptr(rom, sid)
    a = cpu_to_abs(127, dp)
    first = rom[a] | (rom[a+1] << 8)
    count = (first - dp)//2 if first >= dp and (first-dp)%2 == 0 else 6
    if not (1 <= count <= 12):
        count = 6
    return dp, [rom[a+i*2] | (rom[a+i*2+1] << 8) for i in range(count)]

def parse_oam_frame(rom, ptr):
    a = cpu_to_abs(127, ptr)
    out = []
    for _ in range(64):
        y = rom[a]
        if y == 0x80:
            break
        out.append((signed8(y), signed8(rom[a+1]), rom[a+2], rom[a+3]))
        a += 4
    return out

def ow_graphics(rom, sid):
    a = OW_GFX_PTR_TABLE + sid*2
    ptr = rom[a] | (rom[a+1] << 8)
    bank = 125 if sid < 0x50 else 126
    source = cpu_to_abs(bank, ptr)
    raw, used = decompress(rom, source)
    return raw, used, bank, ptr, source

def ow_palette(rom, sid):
    idx = rom[OW_PAL_MAP + sid]
    off = OW_PAL_TABLE + idx*8
    return idx, off, read_palette(rom, off)

def ow_frame(rom, sid, frame_index):
    gfx, used, bank, ptr, source = ow_graphics(rom, sid)
    pidx, poff, palette = ow_palette(rom, sid)
    dp, fps = ow_frame_ptrs(rom, sid)
    fptr = fps[frame_index]
    objects = parse_oam_frame(rom, fptr)

    img = Image.new("RGBA", (OW_FIXED_W, OW_FIXED_H), (0,0,0,0))
    for y,x,tile,attr in objects:
        if tile*16+16 > len(gfx):
            continue
        tileimg = decode_tile(gfx[tile*16:(tile+1)*16], palette)
        if attr & 0x20:
            tileimg = tileimg.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        if attr & 0x40:
            tileimg = tileimg.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        img.alpha_composite(tileimg, (OW_ANCHOR_X+x, OW_ANCHOR_Y+y))
    return img

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rom", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--allow-other-hash", action="store_true")
    args = ap.parse_args()

    rom = args.rom.read_bytes()
    sha = hashlib.sha256(rom).hexdigest()
    if sha != EXPECTED_SHA256 and not args.allow_other_hash:
        raise SystemExit(
            f"ROM SHA-256 mismatch.\nExpected: {EXPECTED_SHA256}\nGot:      {sha}\n"
            "Use --allow-other-hash only if you intentionally want to test another revision."
        )

    out = args.output
    (out/"battle").mkdir(parents=True, exist_ok=True)
    (out/"overworld").mkdir(parents=True, exist_ok=True)

    battle_meta = []
    for cid in range(BATTLE_COUNT):
        img, meta = battle_sprite(rom, cid)
        img.save(out/"battle"/f"{cid:03d}.png")
        battle_meta.append(meta)

    ow_meta = []
    for sid in range(OW_COUNT):
        d = out/"overworld"/f"sprite_{sid:03d}"
        d.mkdir(parents=True, exist_ok=True)
        dp, fps = ow_frame_ptrs(rom, sid)
        frames = []
        for fi in range(len(fps)):
            frame = ow_frame(rom, sid, fi)
            frame.save(d/f"frame_{fi}.png")
            frames.append(frame)
        strip = Image.new("RGBA", (len(frames)*OW_FIXED_W, OW_FIXED_H), (0,0,0,0))
        for fi,frame in enumerate(frames):
            strip.alpha_composite(frame, (fi*OW_FIXED_W,0))
        strip.save(d/"strip.png")
        gfx, used, bank, ptr, source = ow_graphics(rom, sid)
        pidx, poff, palette = ow_palette(rom, sid)
        ow_meta.append({
            "sprite_id": sid, "frame_count": len(fps), "graphics_bank": bank,
            "graphics_cpu_pointer": f"0x{ptr:04X}", "graphics_rom_offset": f"0x{source:06X}",
            "decompressed_bytes": len(gfx), "palette_index": pidx,
            "palette_rom_offset": f"0x{poff:06X}", "oam_definition_cpu_pointer": f"0x{dp:04X}"
        })

    (out/"manifest.json").write_text(json.dumps({
        "rom_sha256": sha, "battle": battle_meta, "overworld": ow_meta
    }, indent=2), encoding="utf-8")
    print(f"Done: {out}")

if __name__ == "__main__":
    main()
