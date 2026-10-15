#!/usr/bin/env python3
"""Generate ahead-of-time C++ translation for one switchable ROMX bank."""

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
CPU_BASE = 0x4000
CHUNK_SIZE = 0x1000
CHUNK_COUNT = 4


def load_bank(path: Path) -> bytes:
    out = bytearray()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not DB_LINE.match(line):
            continue
        out.extend(int(m.group(1), 16) for m in BYTE.finditer(line))
    if len(out) != BANK_SIZE:
        raise SystemExit(f"{path}: parsed {len(out)} bytes; expected {BANK_SIZE}")
    return bytes(out)


def u8(v: int) -> str:
    return f"0x{v & 0xFF:02X}u"


def u16(v: int) -> str:
    return f"0x{v & 0xFFFF:04X}u"


def static_or_runtime_byte(bank: bytes, cpu_address: int) -> str:
    offset = cpu_address - CPU_BASE
    if 0 <= offset < BANK_SIZE:
        return u8(bank[offset])
    return f"memory.read8({u16(cpu_address)})"


def shifted_byte(bank: bytes, address: int) -> str:
    return (
        f"(halt_bug ? {static_or_runtime_byte(bank, address - 1)} "
        f": {static_or_runtime_byte(bank, address)})"
    )


def shifted_word(bank: bytes, address: int) -> str:
    nlo = static_or_runtime_byte(bank, address)
    nhi = static_or_runtime_byte(bank, address + 1)
    blo = static_or_runtime_byte(bank, address - 1)
    bhi = static_or_runtime_byte(bank, address)
    return (
        "static_cast<std::uint16_t>("
        f"static_cast<std::uint16_t>(halt_bug ? {blo} : {nlo}) | "
        f"(static_cast<std::uint16_t>(halt_bug ? {bhi} : {nhi}) << 8))"
    )


def cycle_line(op: int) -> str:
    cc = conditional_code(op)
    if cc is None:
        return f"            cpu.last_mcycles = {base_opcode_mcycles(op)}u;"
    nt = base_opcode_mcycles(op, False)
    tk = base_opcode_mcycles(op, True)
    return (
        f"            cpu.last_mcycles = lr35902::condition<{cc}>(cpu) "
        f"? {tk}u : {nt}u;"
    )


def emit_case(bank: bytes, offset: int) -> str:
    pc = CPU_BASE + offset
    ins = decode_one(bank, offset)
    lines = [f"        case {u16(pc)}: {{"]
    lines.append("            const bool halt_bug = cpu.halt_bug;")
    lines.append("            cpu.halt_bug = false;")

    if ins.kind is Kind.CB:
        assert ins.cb_opcode is not None
        normal_cb = static_or_runtime_byte(bank, pc + 1)
        bug_cb = static_or_runtime_byte(bank, pc)
        lines.append(
            f"            const std::uint8_t cb = halt_bug ? {bug_cb} : {normal_cb};"
        )
        lines.append(
            f"            cpu.last_mcycles = halt_bug "
            f"? lr35902::cb_mcycles_dynamic(cb) : {cb_opcode_mcycles(ins.cb_opcode)}u;"
        )
        lines.append(
            f"            cpu.pc = static_cast<std::uint16_t>({u16(pc)} + "
            "(halt_bug ? 1u : 2u));"
        )
        lines.append("            if (halt_bug) {")
        lines.append("                lr35902::exec_cb_dynamic(cpu, memory, cb);")
        lines.append("            } else {")
        lines.append(
            f"                lr35902::exec_cb<{u8(ins.cb_opcode)}>(cpu, memory);"
        )
        lines.append("            }")
    else:
        op = ins.opcode
        size = base_opcode_size(op)
        imm8 = shifted_byte(bank, pc + 1) if size >= 2 else "0u"
        imm16 = shifted_word(bank, pc + 1) if size >= 3 else "0u"
        lines.append(cycle_line(op))
        lines.append(
            f"            cpu.pc = static_cast<std::uint16_t>({u16(pc)} + "
            f"{size}u - (halt_bug ? 1u : 0u));"
        )
        lines.append(
            f"            lr35902::exec_base<{u8(op)}>("
            f"cpu, memory, {imm8}, {imm16}, {u16(pc)});"
        )

    lines.append("            cpu.finish_instruction();")
    lines.append("            memory.tick_mcycles(cpu.last_mcycles);")
    lines.append("            if (cpu.trapped) return StepResult::Trapped;")
    lines.append("            if (cpu.stopped) return StepResult::Stopped;")
    lines.append("            if (cpu.halted) return StepResult::Halted;")
    lines.append("            return StepResult::Continue;")
    lines.append("        }")
    return "\n".join(lines)


def emit_chunk(bank: bytes, bank_number: int, chunk: int) -> str:
    begin = chunk * CHUNK_SIZE
    end = begin + CHUNK_SIZE
    body = "\n".join(emit_case(bank, off) for off in range(begin, end))
    return f"""// AUTO-GENERATED. DO NOT EDIT.
// ROMX bank {bank_number} native translation, offsets 0x{begin:04X}-0x{end - 1:04X}

#include "recomp/romx.hpp"
#include "recomp/lr35902_exec.hpp"

namespace dwm2t {{

StepResult execute_romx_bank_{bank_number}_chunk_{chunk}(Cpu& cpu, Memory& memory) {{
    switch (cpu.pc) {{
{body}
        default:
            cpu.trap(cpu.pc, memory.read8(cpu.pc));
            return StepResult::Trapped;
    }}
}}

}} // namespace dwm2t
"""


def emit_master(bank_number: int) -> str:
    decls = "\n".join(
        f"StepResult execute_romx_bank_{bank_number}_chunk_{i}(Cpu&, Memory&);"
        for i in range(CHUNK_COUNT)
    )
    dispatch = "\n".join(
        f"    if (cpu.pc < {u16(CPU_BASE + (i + 1) * CHUNK_SIZE)}) "
        f"return execute_romx_bank_{bank_number}_chunk_{i}(cpu, memory);"
        for i in range(CHUNK_COUNT)
    )
    return f"""// AUTO-GENERATED. DO NOT EDIT.

#include "recomp/romx.hpp"

namespace dwm2t {{

{decls}

StepResult execute_romx_bank_{bank_number}(Cpu& cpu, Memory& memory) {{
    if (cpu.pc < 0x4000 || cpu.pc >= 0x8000) return StepResult::Continue;
    if (memory.current_rom_bank() != {bank_number}u) return StepResult::Continue;
{dispatch}
    cpu.trap(cpu.pc, memory.read8(cpu.pc));
    return StepResult::Trapped;
}}

}} // namespace dwm2t
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bank", type=Path, required=True)
    ap.add_argument("--bank-number", type=int, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    args = ap.parse_args()

    if not (1 <= args.bank_number <= 255):
        raise SystemExit("bank-number must be 1..255 for this 4 MiB target")

    bank = load_bank(args.bank)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    (args.out_dir / f"romx_bank_{args.bank_number}_master.cpp").write_text(
        emit_master(args.bank_number), encoding="utf-8", newline="\n"
    )
    for chunk in range(CHUNK_COUNT):
        (args.out_dir / f"romx_bank_{args.bank_number}_chunk_{chunk}.cpp").write_text(
            emit_chunk(bank, args.bank_number, chunk),
            encoding="utf-8",
            newline="\n",
        )

    print(
        f"generated ROMX bank {args.bank_number}: "
        f"{BANK_SIZE} translated entry addresses"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
