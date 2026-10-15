#!/usr/bin/env python3
"""Generate complete ahead-of-time C++ translation for fixed ROM Bank 0."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from lr35902 import (
    Kind,
    base_opcode_mcycles,
    base_opcode_size,
    cb_opcode_mcycles,
    conditional_code,
    decode_one,
)

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


def shifted_byte_expr(bank: bytes, normal_address: int) -> str:
    normal = byte_expr(bank, normal_address)
    bugged = byte_expr(bank, normal_address - 1)
    return f"(halt_bug ? {bugged} : {normal})"


def word_expr(bank: bytes, address: int) -> str:
    normal_lo = byte_expr(bank, address)
    normal_hi = byte_expr(bank, address + 1)
    bug_lo = byte_expr(bank, address - 1)
    bug_hi = byte_expr(bank, address)
    return (
        "static_cast<std::uint16_t>("
        f"static_cast<std::uint16_t>(halt_bug ? {bug_lo} : {normal_lo}) | "
        f"(static_cast<std::uint16_t>(halt_bug ? {bug_hi} : {normal_hi}) << 8))"
    )


def cycle_line_for_base(op: int) -> str:
    cc = conditional_code(op)
    if cc is None:
        return f"            cpu.last_mcycles = {base_opcode_mcycles(op)}u;"
    not_taken = base_opcode_mcycles(op, False)
    taken = base_opcode_mcycles(op, True)
    return (
        f"            cpu.last_mcycles = lr35902::condition<{cc}>(cpu) "
        f"? {taken}u : {not_taken}u;"
    )


def emit_case(bank: bytes, pc: int) -> str:
    ins = decode_one(bank, pc)
    lines = [f"        case {cpp_u16(pc)}: {{"]
    lines.append("            const bool halt_bug = cpu.halt_bug;")
    lines.append("            cpu.halt_bug = false;")

    if ins.kind is Kind.CB:
        assert ins.cb_opcode is not None
        normal_cb = byte_expr(bank, pc + 1)
        bug_cb = byte_expr(bank, pc)
        lines.append(
            f"            const std::uint8_t cb = halt_bug ? {bug_cb} : {normal_cb};"
        )
        lines.append(
            f"            cpu.last_mcycles = halt_bug "
            f"? lr35902::cb_mcycles_dynamic(cb) "
            f": {cb_opcode_mcycles(ins.cb_opcode)}u;"
        )
        lines.append(
            f"            cpu.pc = static_cast<std::uint16_t>({cpp_u16(pc)} + "
            "(halt_bug ? 1u : 2u));"
        )
        lines.append("            if (halt_bug) {")
        lines.append("                lr35902::exec_cb_dynamic(cpu, memory, cb);")
        lines.append("            } else {")
        lines.append(
            f"                lr35902::exec_cb<{cpp_u8(ins.cb_opcode)}>(cpu, memory);"
        )
        lines.append("            }")
    else:
        op = ins.opcode
        size = base_opcode_size(op)
        imm8 = shifted_byte_expr(bank, pc + 1) if size >= 2 else "0u"
        imm16 = word_expr(bank, pc + 1) if size >= 3 else "0u"
        lines.append(cycle_line_for_base(op))
        lines.append(
            f"            cpu.pc = static_cast<std::uint16_t>({cpp_u16(pc)} + "
            f"{size}u - (halt_bug ? 1u : 0u));"
        )
        lines.append(
            f"            lr35902::exec_base<{cpp_u8(op)}>("
            f"cpu, memory, {imm8}, {imm16}, {cpp_u16(pc)});"
        )

    lines.append("            cpu.finish_instruction();")
    lines.append("            memory.tick_mcycles(cpu.last_mcycles);")
    lines.append("            return classify_bank0_step(cpu);")
    lines.append("        }")
    return "\n".join(lines)


def emit_chunk(bank: bytes, chunk: int) -> str:
    begin = chunk * CHUNK_SIZE
    end = begin + CHUNK_SIZE
    body = "\n".join(emit_case(bank, pc) for pc in range(begin, end))
    return f"""// AUTO-GENERATED. DO NOT EDIT.
// Fixed Bank 0 native translation chunk {chunk}: 0x{begin:04X}-0x{end - 1:04X}

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
    dispatch = "\n".join(
        f"    if (cpu.pc < {cpp_u16((i + 1) * CHUNK_SIZE)}) "
        f"return execute_bank0_chunk_{i}(cpu, memory);"
        for i in range(CHUNK_COUNT)
    )

    return f"""// AUTO-GENERATED. DO NOT EDIT.

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
        memory.set_rom_byte(i, kBank0Image[i]);
    }}
}}

StepResult execute_bank0_instruction(Cpu& cpu, Memory& memory) {{
    if (cpu.pc >= 0x4000) return StepResult::LeftBank0;
{dispatch}
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
        emit_master(bank), encoding="utf-8", newline="\n"
    )
    for chunk in range(CHUNK_COUNT):
        (args.out_dir / f"bank0_chunk_{chunk}.cpp").write_text(
            emit_chunk(bank, chunk), encoding="utf-8", newline="\n"
        )

    print(f"generated {CHUNK_COUNT + 1} C++ translation units in {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
