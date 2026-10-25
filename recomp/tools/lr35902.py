#!/usr/bin/env python3
"""Complete LR35902 instruction decoder used by the DWM2t static recompiler.

This module turns bytes into stable instruction metadata for every legal base
opcode and all 256 CB-prefixed opcodes. Illegal Game Boy CPU opcodes are
represented explicitly instead of being silently treated as data.
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
from typing import Sequence

ILLEGAL_BASE_OPCODES = frozenset({
    0xD3, 0xDB, 0xDD,
    0xE3, 0xE4, 0xEB, 0xEC, 0xED,
    0xF4, 0xFC, 0xFD,
})

REG8 = ("B", "C", "D", "E", "H", "L", "(HL)", "A")
RP = ("BC", "DE", "HL", "SP")
RP2 = ("BC", "DE", "HL", "AF")
CC = ("NZ", "Z", "NC", "C")
ALU = ("ADD A,", "ADC A,", "SUB ", "SBC A,", "AND ", "XOR ", "OR ", "CP ")
ROT = ("RLC", "RRC", "RL", "RR", "SLA", "SRA", "SWAP", "SRL")

class Kind(Enum):
    BASE = auto()
    CB = auto()
    ILLEGAL = auto()

@dataclass(frozen=True)
class Decoded:
    pc: int
    kind: Kind
    opcode: int
    size: int
    mnemonic: str
    imm8: int = 0
    imm16: int = 0
    cb_opcode: int | None = None

    @property
    def next_pc(self) -> int:
        return (self.pc + self.size) & 0xFFFF

def _u8(data: Sequence[int], index: int) -> int:
    if index < 0 or index >= len(data):
        return 0
    return int(data[index]) & 0xFF

def _u16(data: Sequence[int], index: int) -> int:
    return _u8(data, index) | (_u8(data, index + 1) << 8)

def base_opcode_size(op: int) -> int:
    op &= 0xFF
    if op == 0xCB:
        return 2
    if op in ILLEGAL_BASE_OPCODES:
        return 1
    if op in {
        0x01, 0x08, 0x11, 0x21, 0x31,
        0xC2, 0xC3, 0xC4, 0xCA, 0xCC, 0xCD,
        0xD2, 0xD4, 0xDA, 0xDC, 0xEA, 0xFA,
    }:
        return 3
    if op in {
        0x06, 0x0E, 0x10, 0x16, 0x18, 0x1E,
        0x20, 0x26, 0x28, 0x2E, 0x30, 0x36, 0x38, 0x3E,
        0xC6, 0xCE, 0xD6, 0xDE, 0xE0, 0xE6, 0xE8, 0xEE,
        0xF0, 0xF6, 0xF8, 0xFE,
    }:
        return 2
    return 1

def _base_mnemonic(op: int, imm8: int, imm16: int) -> str:
    if op in ILLEGAL_BASE_OPCODES:
        return f"ILLEGAL ${op:02X}"
    if op == 0xCB:
        return "PREFIX CB"

    x = op >> 6
    y = (op >> 3) & 7
    z = op & 7
    p = y >> 1
    q = y & 1

    if x == 0:
        if z == 0:
            return (
                "NOP", f"LD (${imm16:04X}),SP", "STOP", f"JR {imm8:02X}",
                f"JR NZ,{imm8:02X}", f"JR Z,{imm8:02X}",
                f"JR NC,{imm8:02X}", f"JR C,{imm8:02X}",
            )[y]
        if z == 1:
            return f"LD {RP[p]},${imm16:04X}" if q == 0 else f"ADD HL,{RP[p]}"
        if z == 2:
            if q == 0:
                return ("LD (BC),A", "LD (DE),A", "LD (HL+),A", "LD (HL-),A")[p]
            return ("LD A,(BC)", "LD A,(DE)", "LD A,(HL+)", "LD A,(HL-)")[p]
        if z == 3:
            return f"{'INC' if q == 0 else 'DEC'} {RP[p]}"
        if z == 4:
            return f"INC {REG8[y]}"
        if z == 5:
            return f"DEC {REG8[y]}"
        if z == 6:
            return f"LD {REG8[y]},${imm8:02X}"
        return ("RLCA", "RRCA", "RLA", "RRA", "DAA", "CPL", "SCF", "CCF")[y]

    if x == 1:
        if y == 6 and z == 6:
            return "HALT"
        return f"LD {REG8[y]},{REG8[z]}"

    if x == 2:
        return f"{ALU[y]}{REG8[z]}"

    if z == 0:
        if y < 4:
            return f"RET {CC[y]}"
        return (
            f"LDH (${imm8:02X}),A", f"ADD SP,{imm8:02X}",
            f"LDH A,(${imm8:02X})", f"LD HL,SP+{imm8:02X}",
        )[y - 4]
    if z == 1:
        if q == 0:
            return f"POP {RP2[p]}"
        return ("RET", "RETI", "JP HL", "LD SP,HL")[p]
    if z == 2:
        if y < 4:
            return f"JP {CC[y]},${imm16:04X}"
        return (
            "LD (C),A", f"LD (${imm16:04X}),A",
            "LD A,(C)", f"LD A,(${imm16:04X})",
        )[y - 4]
    if z == 3:
        if y == 0:
            return f"JP ${imm16:04X}"
        if y == 1:
            return "PREFIX CB"
        if y == 6:
            return "DI"
        if y == 7:
            return "EI"
        return f"ILLEGAL ${op:02X}"
    if z == 4:
        if y < 4:
            return f"CALL {CC[y]},${imm16:04X}"
        return f"ILLEGAL ${op:02X}"
    if z == 5:
        if q == 0:
            return f"PUSH {RP2[p]}"
        if p == 0:
            return f"CALL ${imm16:04X}"
        return f"ILLEGAL ${op:02X}"
    if z == 6:
        return f"{ALU[y]}${imm8:02X}"
    return f"RST ${y * 8:02X}"

def _cb_mnemonic(cb: int) -> str:
    x = cb >> 6
    y = (cb >> 3) & 7
    z = cb & 7
    if x == 0:
        return f"{ROT[y]} {REG8[z]}"
    if x == 1:
        return f"BIT {y},{REG8[z]}"
    if x == 2:
        return f"RES {y},{REG8[z]}"
    return f"SET {y},{REG8[z]}"

def decode_one(data: Sequence[int], pc: int) -> Decoded:
    op = _u8(data, pc)
    if op in ILLEGAL_BASE_OPCODES:
        return Decoded(pc, Kind.ILLEGAL, op, 1, f"ILLEGAL ${op:02X}")
    if op == 0xCB:
        cb = _u8(data, pc + 1)
        return Decoded(pc, Kind.CB, op, 2, _cb_mnemonic(cb), cb_opcode=cb)
    size = base_opcode_size(op)
    imm8 = _u8(data, pc + 1) if size >= 2 else 0
    imm16 = _u16(data, pc + 1) if size >= 3 else 0
    return Decoded(pc, Kind.BASE, op, size, _base_mnemonic(op, imm8, imm16), imm8, imm16)

def decode_all_offsets(data: Sequence[int]) -> list[Decoded]:
    return [decode_one(data, pc) for pc in range(len(data))]

def validate_complete_decoder() -> None:
    legal = 0
    illegal = 0
    for op in range(256):
        sample = bytes((op, 0x5A, 0xA5, 0x00))
        ins = decode_one(sample, 0)
        if op in ILLEGAL_BASE_OPCODES:
            assert ins.kind is Kind.ILLEGAL and ins.size == 1
            illegal += 1
        elif op == 0xCB:
            assert ins.kind is Kind.CB and ins.cb_opcode == 0x5A and ins.size == 2
            legal += 1
        else:
            assert ins.kind is Kind.BASE and ins.size == base_opcode_size(op)
            legal += 1
    assert legal == 245
    assert illegal == 11
    for cb in range(256):
        ins = decode_one(bytes((0xCB, cb)), 0)
        assert ins.kind is Kind.CB and ins.cb_opcode == cb and ins.size == 2 and ins.mnemonic


def base_opcode_mcycles(op: int, taken: bool = False) -> int:
    """Return LR35902 machine cycles for a base opcode.

    For conditional JR/JP/CALL/RET, pass taken=True for the taken timing.
    CB-prefixed timing is handled by cb_opcode_mcycles().
    """
    op &= 0xFF
    if op in ILLEGAL_BASE_OPCODES:
        return 1
    if op == 0xCB:
        raise ValueError("use cb_opcode_mcycles for CB-prefixed instructions")

    x = op >> 6
    y = (op >> 3) & 7
    z = op & 7
    p = y >> 1
    q = y & 1

    if x == 0:
        if z == 0:
            if y == 0: return 1              # NOP
            if y == 1: return 5              # LD (a16),SP
            if y == 2: return 1              # STOP
            if y == 3: return 3              # JR r8
            return 3 if taken else 2         # JR cc,r8
        if z == 1:
            return 3 if q == 0 else 2
        if z == 2:
            return 2
        if z == 3:
            return 2
        if z in (4, 5):
            return 3 if y == 6 else 1
        if z == 6:
            return 3 if y == 6 else 2
        return 1

    if x == 1:
        if y == 6 and z == 6:
            return 1                         # HALT
        return 2 if (y == 6 or z == 6) else 1

    if x == 2:
        return 2 if z == 6 else 1

    # x == 3
    if z == 0:
        if y < 4:
            return 5 if taken else 2          # RET cc
        return (3, 4, 3, 3)[y - 4]           # LDH/ADD SP/LDH/LD HL,SP+r8
    if z == 1:
        if q == 0:
            return 3                         # POP
        return (4, 4, 1, 2)[p]               # RET/RETI/JP HL/LD SP,HL
    if z == 2:
        if y < 4:
            return 4 if taken else 3          # JP cc,a16
        return (2, 4, 2, 4)[y - 4]
    if z == 3:
        if y == 0: return 4                   # JP a16
        if y == 1: return 1                   # prefix placeholder
        return 1                              # illegal / DI / EI
    if z == 4:
        if y < 4:
            return 6 if taken else 3          # CALL cc,a16
        return 1
    if z == 5:
        if q == 0:
            return 4                         # PUSH
        return 6 if p == 0 else 1            # CALL / illegal
    if z == 6:
        return 2                             # ALU d8
    return 4                                 # RST


def cb_opcode_mcycles(cb: int) -> int:
    cb &= 0xFF
    x = cb >> 6
    z = cb & 7
    if z != 6:
        return 2
    return 3 if x == 1 else 4


def conditional_code(op: int) -> int | None:
    """Return condition index NZ/Z/NC/C for conditional control flow."""
    op &= 0xFF
    if op in (0x20, 0x28, 0x30, 0x38):
        return (op >> 3) & 3
    if op in (0xC0, 0xC8, 0xD0, 0xD8):
        return (op >> 3) & 3
    if op in (0xC2, 0xCA, 0xD2, 0xDA):
        return (op >> 3) & 3
    if op in (0xC4, 0xCC, 0xD4, 0xDC):
        return (op >> 3) & 3
    return None
