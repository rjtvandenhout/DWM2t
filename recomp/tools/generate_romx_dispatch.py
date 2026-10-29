#!/usr/bin/env python3
"""Generate the ahead-of-time ROMX bank registry."""

from __future__ import annotations
import argparse
from pathlib import Path

def write_text_if_changed(path: Path, text: str) -> bool:
    """Preserve mtime when generated content is already identical."""
    if path.exists():
        try:
            if path.read_text(encoding="utf-8") == text:
                return False
        except OSError:
            pass
    path.write_text(text, encoding="utf-8", newline="\n")
    return True



def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--banks", nargs="+", type=int, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    banks = sorted(set(args.banks))
    if not banks or any(b < 1 or b > 255 for b in banks):
        raise SystemExit("ROMX banks must be unique values in 1..255")

    decls = "\n".join(
        f"StepResult execute_romx_bank_{bank}(Cpu&, Memory&);"
        for bank in banks
    )
    cases = "\n".join(
        f"        case {bank}: return execute_romx_bank_{bank}(cpu, memory);"
        for bank in banks
    )
    membership = "\n".join(
        f"        case {bank}: return true;" for bank in banks
    )

    cpp = f'''// AUTO-GENERATED. DO NOT EDIT.
// AOT ROMX bank registry: {", ".join(map(str, banks))}

#include "recomp/romx.hpp"
#include "recomp/bank0.hpp"

namespace dwm2t {{

{decls}

StepResult execute_translated_romx(Cpu& cpu, Memory& memory) {{
    const std::uint16_t bank = memory.current_rom_bank();
    switch (bank) {{
        case 0: return execute_bank0_romx_instruction(cpu, memory);
{cases}
        default:
            cpu.missing_bank = bank;
            return StepResult::MissingBank;
    }}
}}

bool romx_bank_is_translated(std::uint16_t bank) {{
    switch (bank) {{
        case 0: return true; // Physical Bank 0 also maps in the ROMX window.
{membership}
        default: return false;
    }}
}}

std::size_t translated_romx_bank_count() {{
    return {len(banks)}u;
}}

}} // namespace dwm2t
'''

    args.out.parent.mkdir(parents=True, exist_ok=True)
    changed = write_text_if_changed(args.out, cpp)
    print("AOT ROMX banks:", " ".join(map(str, banks)))
    print("ROMX registry changed:", "yes" if changed else "no")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
