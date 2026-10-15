#!/usr/bin/env python3
"""Generate an embedded 4 MiB ROM image from the checked-in matching source.

The generated C++ contains Base64 text so the native executable needs no
external .gbc file. The bytes are still sourced exclusively from src/banks/.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
from pathlib import Path
import re
import textwrap

DB_LINE = re.compile(r"^\s*db\b", re.IGNORECASE)
BYTE = re.compile(r"\$([0-9A-Fa-f]{2})\b")

BANK_SIZE = 0x4000
BANK_COUNT = 256
EXPECTED_SHA256 = "8e38a7420ef5239c7196aa4fd4b1499e65db2823e875bbf8241bb2199e766d4e"


def parse_bank(path: Path) -> bytes:
    out = bytearray()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not DB_LINE.match(line):
            continue
        out.extend(int(m.group(1), 16) for m in BYTE.finditer(line))
    if len(out) != BANK_SIZE:
        raise SystemExit(f"{path}: parsed {len(out)} bytes, expected {BANK_SIZE}")
    return bytes(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--banks-dir", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    rom = b"".join(
        parse_bank(args.banks_dir / f"bank_{bank:03d}.asm")
        for bank in range(BANK_COUNT)
    )

    digest = hashlib.sha256(rom).hexdigest()
    if digest != EXPECTED_SHA256:
        raise SystemExit(
            f"matching-source ROM hash mismatch: {digest} != {EXPECTED_SHA256}"
        )

    encoded = base64.b64encode(rom).decode("ascii")
    literal = "\n".join(
        f'    "{chunk}"'
        for chunk in textwrap.wrap(encoded, 120)
    )

    cpp = f'''// AUTO-GENERATED. DO NOT EDIT.
// Source ROM SHA-256: {digest}

#include "recomp/memory.hpp"

#include <cstddef>
#include <cstdint>
#include <stdexcept>
#include <vector>

namespace dwm2t {{

namespace {{

constexpr char kRomBase64[] =
{literal}
;

int b64_value(char c) {{
    if (c >= 'A' && c <= 'Z') return c - 'A';
    if (c >= 'a' && c <= 'z') return c - 'a' + 26;
    if (c >= '0' && c <= '9') return c - '0' + 52;
    if (c == '+') return 62;
    if (c == '/') return 63;
    if (c == '=') return -2;
    return -1;
}}

std::vector<std::uint8_t> decode_rom() {{
    std::vector<std::uint8_t> out;
    out.reserve(Memory::RomSize);

    std::uint32_t val = 0;
    int bits = -8;
    for (const char c : kRomBase64) {{
        if (c == '\\0') break;
        const int d = b64_value(c);
        if (d == -2) break;
        if (d < 0) continue;
        val = (val << 6) | static_cast<std::uint32_t>(d);
        bits += 6;
        if (bits >= 0) {{
            out.push_back(static_cast<std::uint8_t>((val >> bits) & 0xFF));
            bits -= 8;
        }}
    }}

    if (out.size() != Memory::RomSize) {{
        throw std::runtime_error("embedded DWM2 ROM image decoded to wrong size");
    }}
    return out;
}}

}} // namespace

void load_full_rom_image(Memory& memory) {{
    const auto rom = decode_rom();
    memory.load_rom(rom.data(), rom.size());
}}

}} // namespace dwm2t
'''

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(cpp, encoding="utf-8", newline="\n")
    print(f"generated embedded ROM source: {args.out}")
    print(f"ROM SHA-256: {digest}")
    print(f"Base64 characters: {len(encoded)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
