#!/usr/bin/env python3
"""Generate the complete native C++ translation for fixed ROM Bank 0.

Every byte address in $0000-$3FFF receives an entry translation. This is
intentional: LR35902 control flow can legally land on any byte, including an
operand byte. No opcode decoding is performed at runtime for normal Bank 0
execution.

The only dynamic decode choice is the CB second byte if execution starts on a
CB prefix at $3FFF, because that second byte is fetched from the currently
mapped ROMX byte at $4000. MBC5 mapping itself belongs to milestone M3.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from lr35902 import Kind, base_opcode_size, decode_one  # noqa: E402

DB_LINE = re.compile(r"^\s*db\b", re.IGNORECASE)
BYTE = re.compile(r"\$([0-9A-Fa-f]{2})\b")

BANK_SIZE = 0x4000
CHUNK_SIZE = 0x1000
CHUNK_COUNT = BANK_SIZE // CHUNK_SIZE


def load_bank(path: Path) -> bytes:
    out = bytearray()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not DB_LINE.match(line):
            continue
        out.extend(int(m.group(1), 16) for m in BYTE.finditer(line))
    if len(out) != BANK_SIZE:
        raise SystemExit(f"{path}: parsed {len(out)} bytes; expected {BANK_SIZE}")
    return bytes(out)


def cpp_u8(value: int) -> str:
    return f"0x{value & 0xFF:02X}u"


def cpp_u16(value: int) -> str:
    return f"0x{value & 0xFFFF:04X}u"


def byte_expr(bank: bytes, address: int) -> str:
    if 0 <= address < BANK_SIZE:
        return cpp_u8(bank[address])
    return f"memory.read8({cpp_u16(address)})"


def word_expr(bank: bytes, address: int) -> str:
    lo = byte_expr(bank, address)
    hi = byte_expr(bank, address + 1)
    if 0 <= address < BANK_SIZE - 1:
        return cpp_u16(bank[address] | (bank[address + 1] << 8))
    return (
        "static_cast<std::uint16_t>("
        f"static_cast<std::uint16_t>({lo}) | "
        f"(static_cast<std::uint16_t>({hi}) << 8))"
    )


def emit_case(bank: bytes, pc: int) -> str:
    ins = decode_one(bank, pc)
    lines = [f"        case {cpp_u16(pc)}: {{"]

    if ins.kind is Kind.CB:
        cb_expr = byte_expr(bank, pc + 1)
        next_pc = (pc + 2) & 0xFFFF
        lines.append(f"            cpu.pc = {cpp_u16(next_pc)};")
        if pc + 1 < BANK_SIZE:
            assert ins.cb_opcode is not None
            lines.append(
                f"            lr35902::exec_cb<{cpp_u8(ins.cb_opcode)}>(cpu, memory);"
            )
        else:
            lines.append(
                f"            lr35902::exec_cb_dynamic(cpu, memory, {cb_expr});"
            )
    else:
        op = ins.opcode
        size = base_opcode_size(op)
        next_pc = (pc + size) & 0xFFFF
        imm8 = byte_expr(bank, pc + 1) if size >= 2 else "0u"
        imm16 = word_expr(bank, pc + 1) if size >= 3 else "0u"
        lines.append(f"            cpu.pc = {cpp_u16(next_pc)};")
        lines.append(
            f"            lr35902::exec_base<{cpp_u8(op)}>("
            f"cpu, memory, {imm8}, {imm16}, {cpp_u16(pc)});"
        )

    lines.append("            cpu.finish_instruction();")
    lines.append("            return classify_bank0_step(cpu);")
    lines.append("        }")
    return "\n".join(lines)


def emit_chunk(bank: bytes, chunk: int) -> str:
    begin = chunk * CHUNK_SIZE
    end = begin + CHUNK_SIZE
    body = "\n".join(emit_case(bank, pc) for pc in range(begin, end))

    return f"""// AUTO-GENERATED. DO NOT EDIT.
// Bank 0 native translation chunk {chunk}: ${begin:04X}-${end - 1:04X}

#include "recomp/bank0.hpp"
#include "recomp/lr35902_exec.hpp"

namespace dwm2t {{

StepResult execute_bank0_chunk_{chunk}(Cpu& cpu, Memory& memory) {{
    switch (cpu.pc) {{
{body}
        default:
            cpu.trap(cpu.pc, memory.read8(cpu.pc));
            return StepResult::Trapped;
    }}
}}

}} // namespace dwm2t
"""


def emit_master(bank: bytes) -> str:
    rows = []
    for i in range(0, BANK_SIZE, 16):
        row = ", ".join(cpp_u8(b) for b in bank[i : i + 16])
        rows.append(f"    {row},")
    image = "\n".join(rows)

    decls = "\n".join(
        f"StepResult execute_bank0_chunk_{i}(Cpu&, Memory&);" for i in range(CHUNK_COUNT)
    )

    dispatch = []
    for i in range(CHUNK_COUNT):
        hi = (i + 1) * CHUNK_SIZE
        dispatch.append(
            f"    if (cpu.pc < {cpp_u16(hi)}) return execute_bank0_chunk_{i}(cpu, memory);"
        )
    dispatch_text = "\n".join(dispatch)

    return f"""// AUTO-GENERATED. DO NOT EDIT.
// Complete fixed Bank 0 image plus native dispatch glue.

#include "recomp/bank0.hpp"

#include <array>
#include <cstddef>
#include <cstdint>

namespace dwm2t {{

{decls}

namespace {{

constexpr std::array<std::uint8_t, 0x4000> kBank0Image = {{
{image}
}};

}} // namespace

void load_bank0_image(Memory& memory) {{
    for (std::size_t i = 0; i < kBank0Image.size(); ++i) {{
        memory.write8(static_cast<std::uint16_t>(i), kBank0Image[i]);
    }}
}}

StepResult execute_bank0_instruction(Cpu& cpu, Memory& memory) {{
    if (cpu.pc >= 0x4000) return StepResult::LeftBank0;
{dispatch_text}
    cpu.trap(cpu.pc, memory.read8(cpu.pc));
    return StepResult::Trapped;
}}

StepResult run_bank0(Cpu& cpu, Memory& memory, std::size_t max_steps) {{
    for (std::size_t step = 0; step < max_steps; ++step) {{
        const StepResult result = execute_bank0_instruction(cpu, memory);
        if (result != StepResult::Continue) return result;
    }}
    return StepResult::StepLimit;
}}

std::size_t bank0_translated_entry_count() {{
    return 0x4000;
}}

}} // namespace dwm2t
"""


def audit(bank: bytes) -> dict[str, int]:
    counts = {"base": 0, "cb": 0, "illegal": 0, "cross_boundary": 0}
    for pc in range(BANK_SIZE):
        ins = decode_one(bank, pc)
        if ins.kind is Kind.CB:
            counts["cb"] += 1
        elif ins.kind is Kind.ILLEGAL:
            counts["illegal"] += 1
        else:
            counts["base"] += 1
        if pc + ins.size > BANK_SIZE:
            counts["cross_boundary"] += 1
    return counts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bank", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path)
    ap.add_argument("--audit-only", action="store_true")
    args = ap.parse_args()

    bank = load_bank(args.bank)
    counts = audit(bank)

    print("Bank 0 static recomp audit")
    print(f"  entry addresses: {BANK_SIZE}")
    print(f"  base decodes: {counts['base']}")
    print(f"  CB decodes: {counts['cb']}")
    print(f"  illegal decodes: {counts['illegal']}")
    print(f"  bank-boundary operand fetches: {counts['cross_boundary']}")

    if args.audit_only:
        return 0

    if args.out_dir is None:
        raise SystemExit("--out-dir is required unless --audit-only is used")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "bank0_master.cpp").write_text(
        emit_master(bank).replace("$", "$"), encoding="utf-8", newline="\n"
    )
    for chunk in range(CHUNK_COUNT):
        (args.out_dir / f"bank0_chunk_{chunk}.cpp").write_text(
            emit_chunk(bank, chunk).replace("$", "$"),
            encoding="utf-8",
            newline="\n",
        )

    print(f"generated {CHUNK_COUNT + 1} C++ translation units in {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
