#pragma once

#include "recomp/cpu.hpp"
#include "recomp/memory.hpp"

#include <cstdint>
#include <type_traits>

namespace dwm2t::lr35902 {

inline std::uint16_t add_signed(std::uint16_t base, std::uint8_t imm8) {
    const auto signed_value = static_cast<std::int8_t>(imm8);
    return static_cast<std::uint16_t>(
        static_cast<std::int32_t>(base) + static_cast<std::int32_t>(signed_value));
}

inline void push16(Cpu& cpu, Memory& memory, std::uint16_t value) {
    cpu.sp = static_cast<std::uint16_t>(cpu.sp - 1);
    memory.write8(cpu.sp, static_cast<std::uint8_t>(value >> 8));
    cpu.sp = static_cast<std::uint16_t>(cpu.sp - 1);
    memory.write8(cpu.sp, static_cast<std::uint8_t>(value));
}

inline std::uint16_t pop16(Cpu& cpu, Memory& memory) {
    const std::uint8_t lo = memory.read8(cpu.sp);
    cpu.sp = static_cast<std::uint16_t>(cpu.sp + 1);
    const std::uint8_t hi = memory.read8(cpu.sp);
    cpu.sp = static_cast<std::uint16_t>(cpu.sp + 1);
    return static_cast<std::uint16_t>(
        static_cast<std::uint16_t>(lo) |
        (static_cast<std::uint16_t>(hi) << 8));
}

template <int I>
inline std::uint8_t read_r8(Cpu& cpu, Memory& memory) {
    static_assert(I >= 0 && I < 8);
    if constexpr (I == 0) return cpu.b;
    if constexpr (I == 1) return cpu.c;
    if constexpr (I == 2) return cpu.d;
    if constexpr (I == 3) return cpu.e;
    if constexpr (I == 4) return cpu.h;
    if constexpr (I == 5) return cpu.l;
    if constexpr (I == 6) return memory.read8(cpu.hl());
    return cpu.a;
}

template <int I>
inline void write_r8(Cpu& cpu, Memory& memory, std::uint8_t value) {
    static_assert(I >= 0 && I < 8);
    if constexpr (I == 0) cpu.b = value;
    else if constexpr (I == 1) cpu.c = value;
    else if constexpr (I == 2) cpu.d = value;
    else if constexpr (I == 3) cpu.e = value;
    else if constexpr (I == 4) cpu.h = value;
    else if constexpr (I == 5) cpu.l = value;
    else if constexpr (I == 6) memory.write8(cpu.hl(), value);
    else cpu.a = value;
}

template <int P>
inline std::uint16_t read_rp(const Cpu& cpu) {
    static_assert(P >= 0 && P < 4);
    if constexpr (P == 0) return cpu.bc();
    if constexpr (P == 1) return cpu.de();
    if constexpr (P == 2) return cpu.hl();
    return cpu.sp;
}

template <int P>
inline void write_rp(Cpu& cpu, std::uint16_t value) {
    static_assert(P >= 0 && P < 4);
    if constexpr (P == 0) cpu.set_bc(value);
    else if constexpr (P == 1) cpu.set_de(value);
    else if constexpr (P == 2) cpu.set_hl(value);
    else cpu.sp = value;
}

template <int P>
inline std::uint16_t read_rp2(const Cpu& cpu) {
    static_assert(P >= 0 && P < 4);
    if constexpr (P == 0) return cpu.bc();
    if constexpr (P == 1) return cpu.de();
    if constexpr (P == 2) return cpu.hl();
    return cpu.af();
}

template <int P>
inline void write_rp2(Cpu& cpu, std::uint16_t value) {
    static_assert(P >= 0 && P < 4);
    if constexpr (P == 0) cpu.set_bc(value);
    else if constexpr (P == 1) cpu.set_de(value);
    else if constexpr (P == 2) cpu.set_hl(value);
    else cpu.set_af(value);
}

template <int C>
inline bool condition(const Cpu& cpu) {
    static_assert(C >= 0 && C < 4);
    if constexpr (C == 0) return !cpu.flag(Cpu::FlagZ);
    if constexpr (C == 1) return cpu.flag(Cpu::FlagZ);
    if constexpr (C == 2) return !cpu.flag(Cpu::FlagC);
    return cpu.flag(Cpu::FlagC);
}

inline std::uint8_t inc8(Cpu& cpu, std::uint8_t value) {
    const std::uint8_t result = static_cast<std::uint8_t>(value + 1);
    const bool carry = cpu.flag(Cpu::FlagC);
    cpu.set_flags(result == 0, false, (value & 0x0F) == 0x0F, carry);
    return result;
}

inline std::uint8_t dec8(Cpu& cpu, std::uint8_t value) {
    const std::uint8_t result = static_cast<std::uint8_t>(value - 1);
    const bool carry = cpu.flag(Cpu::FlagC);
    cpu.set_flags(result == 0, true, (value & 0x0F) == 0x00, carry);
    return result;
}

inline void add_a(Cpu& cpu, std::uint8_t value, bool use_carry) {
    const unsigned carry = use_carry && cpu.flag(Cpu::FlagC) ? 1u : 0u;
    const unsigned result = static_cast<unsigned>(cpu.a) + value + carry;
    const bool half = ((cpu.a & 0x0F) + (value & 0x0F) + carry) > 0x0F;
    cpu.a = static_cast<std::uint8_t>(result);
    cpu.set_flags(cpu.a == 0, false, half, result > 0xFF);
}

inline void sub_a(Cpu& cpu, std::uint8_t value, bool use_carry, bool store) {
    const unsigned carry = use_carry && cpu.flag(Cpu::FlagC) ? 1u : 0u;
    const unsigned lhs = cpu.a;
    const unsigned rhs = static_cast<unsigned>(value) + carry;
    const std::uint8_t result = static_cast<std::uint8_t>(lhs - rhs);
    const bool half = (lhs & 0x0F) < ((value & 0x0F) + carry);
    const bool full = lhs < rhs;
    cpu.set_flags(result == 0, true, half, full);
    if (store) cpu.a = result;
}

inline void and_a(Cpu& cpu, std::uint8_t value) {
    cpu.a = static_cast<std::uint8_t>(cpu.a & value);
    cpu.set_flags(cpu.a == 0, false, true, false);
}

inline void xor_a(Cpu& cpu, std::uint8_t value) {
    cpu.a = static_cast<std::uint8_t>(cpu.a ^ value);
    cpu.set_flags(cpu.a == 0, false, false, false);
}

inline void or_a(Cpu& cpu, std::uint8_t value) {
    cpu.a = static_cast<std::uint8_t>(cpu.a | value);
    cpu.set_flags(cpu.a == 0, false, false, false);
}

template <int Y>
inline void alu(Cpu& cpu, std::uint8_t value) {
    static_assert(Y >= 0 && Y < 8);
    if constexpr (Y == 0) add_a(cpu, value, false);
    else if constexpr (Y == 1) add_a(cpu, value, true);
    else if constexpr (Y == 2) sub_a(cpu, value, false, true);
    else if constexpr (Y == 3) sub_a(cpu, value, true, true);
    else if constexpr (Y == 4) and_a(cpu, value);
    else if constexpr (Y == 5) xor_a(cpu, value);
    else if constexpr (Y == 6) or_a(cpu, value);
    else sub_a(cpu, value, false, false);
}

inline void add_hl(Cpu& cpu, std::uint16_t value) {
    const std::uint16_t lhs = cpu.hl();
    const std::uint32_t result = static_cast<std::uint32_t>(lhs) + value;
    const bool z = cpu.flag(Cpu::FlagZ);
    const bool half = ((lhs & 0x0FFF) + (value & 0x0FFF)) > 0x0FFF;
    cpu.set_hl(static_cast<std::uint16_t>(result));
    cpu.set_flags(z, false, half, result > 0xFFFF);
}

inline std::uint16_t add_sp_value(Cpu& cpu, std::uint16_t base, std::uint8_t imm8) {
    const std::uint16_t result = add_signed(base, imm8);
    const unsigned low = base & 0xFF;
    const unsigned u = imm8;
    cpu.set_flags(false, false,
                  ((low & 0x0F) + (u & 0x0F)) > 0x0F,
                  low + u > 0xFF);
    return result;
}

inline void daa(Cpu& cpu) {
    std::uint8_t correction = 0;
    bool carry = cpu.flag(Cpu::FlagC);

    if (!cpu.flag(Cpu::FlagN)) {
        if (cpu.flag(Cpu::FlagH) || (cpu.a & 0x0F) > 9) correction |= 0x06;
        if (carry || cpu.a > 0x99) {
            correction |= 0x60;
            carry = true;
        }
        cpu.a = static_cast<std::uint8_t>(cpu.a + correction);
    } else {
        if (cpu.flag(Cpu::FlagH)) correction |= 0x06;
        if (carry) correction |= 0x60;
        cpu.a = static_cast<std::uint8_t>(cpu.a - correction);
    }

    const bool n = cpu.flag(Cpu::FlagN);
    cpu.set_flags(cpu.a == 0, n, false, carry);
}

inline std::uint8_t rlc(Cpu& cpu, std::uint8_t v, bool zflag) {
    const bool c = (v & 0x80) != 0;
    v = static_cast<std::uint8_t>((v << 1) | (c ? 1 : 0));
    cpu.set_flags(zflag && v == 0, false, false, c);
    return v;
}

inline std::uint8_t rrc(Cpu& cpu, std::uint8_t v, bool zflag) {
    const bool c = (v & 0x01) != 0;
    v = static_cast<std::uint8_t>((v >> 1) | (c ? 0x80 : 0));
    cpu.set_flags(zflag && v == 0, false, false, c);
    return v;
}

inline std::uint8_t rl(Cpu& cpu, std::uint8_t v, bool zflag) {
    const bool old_c = cpu.flag(Cpu::FlagC);
    const bool new_c = (v & 0x80) != 0;
    v = static_cast<std::uint8_t>((v << 1) | (old_c ? 1 : 0));
    cpu.set_flags(zflag && v == 0, false, false, new_c);
    return v;
}

inline std::uint8_t rr(Cpu& cpu, std::uint8_t v, bool zflag) {
    const bool old_c = cpu.flag(Cpu::FlagC);
    const bool new_c = (v & 0x01) != 0;
    v = static_cast<std::uint8_t>((v >> 1) | (old_c ? 0x80 : 0));
    cpu.set_flags(zflag && v == 0, false, false, new_c);
    return v;
}

inline std::uint8_t sla(Cpu& cpu, std::uint8_t v) {
    const bool c = (v & 0x80) != 0;
    v = static_cast<std::uint8_t>(v << 1);
    cpu.set_flags(v == 0, false, false, c);
    return v;
}

inline std::uint8_t sra(Cpu& cpu, std::uint8_t v) {
    const bool c = (v & 0x01) != 0;
    const std::uint8_t msb = static_cast<std::uint8_t>(v & 0x80);
    v = static_cast<std::uint8_t>((v >> 1) | msb);
    cpu.set_flags(v == 0, false, false, c);
    return v;
}

inline std::uint8_t swap(Cpu& cpu, std::uint8_t v) {
    v = static_cast<std::uint8_t>((v << 4) | (v >> 4));
    cpu.set_flags(v == 0, false, false, false);
    return v;
}

inline std::uint8_t srl(Cpu& cpu, std::uint8_t v) {
    const bool c = (v & 0x01) != 0;
    v = static_cast<std::uint8_t>(v >> 1);
    cpu.set_flags(v == 0, false, false, c);
    return v;
}

template <std::uint8_t CB>
inline void exec_cb(Cpu& cpu, Memory& memory) {
    constexpr int x = CB >> 6;
    constexpr int y = (CB >> 3) & 7;
    constexpr int z = CB & 7;

    if constexpr (x == 0) {
        std::uint8_t v = read_r8<z>(cpu, memory);
        if constexpr (y == 0) v = rlc(cpu, v, true);
        else if constexpr (y == 1) v = rrc(cpu, v, true);
        else if constexpr (y == 2) v = rl(cpu, v, true);
        else if constexpr (y == 3) v = rr(cpu, v, true);
        else if constexpr (y == 4) v = sla(cpu, v);
        else if constexpr (y == 5) v = sra(cpu, v);
        else if constexpr (y == 6) v = swap(cpu, v);
        else v = srl(cpu, v);
        write_r8<z>(cpu, memory, v);
    } else if constexpr (x == 1) {
        const std::uint8_t v = read_r8<z>(cpu, memory);
        const bool bit_set = (v & (1u << y)) != 0;
        const bool carry = cpu.flag(Cpu::FlagC);
        cpu.set_flags(!bit_set, false, true, carry);
    } else if constexpr (x == 2) {
        std::uint8_t v = read_r8<z>(cpu, memory);
        v = static_cast<std::uint8_t>(v & ~(1u << y));
        write_r8<z>(cpu, memory, v);
    } else {
        std::uint8_t v = read_r8<z>(cpu, memory);
        v = static_cast<std::uint8_t>(v | (1u << y));
        write_r8<z>(cpu, memory, v);
    }
}

inline std::uint8_t cb_mcycles_dynamic(std::uint8_t cb) {
    const std::uint8_t x = static_cast<std::uint8_t>(cb >> 6);
    const std::uint8_t z = static_cast<std::uint8_t>(cb & 7u);
    if (z != 6u) return 2u;
    return x == 1u ? 3u : 4u;
}

inline void exec_cb_dynamic(Cpu& cpu, Memory& memory, std::uint8_t cb) {
#define DWM2T_CB_CASE(N) case N: exec_cb<N>(cpu, memory); return
    switch (cb) {
#define DWM2T_CB_ROW(H)         DWM2T_CB_CASE(H##0); DWM2T_CB_CASE(H##1); DWM2T_CB_CASE(H##2); DWM2T_CB_CASE(H##3);         DWM2T_CB_CASE(H##4); DWM2T_CB_CASE(H##5); DWM2T_CB_CASE(H##6); DWM2T_CB_CASE(H##7);         DWM2T_CB_CASE(H##8); DWM2T_CB_CASE(H##9); DWM2T_CB_CASE(H##A); DWM2T_CB_CASE(H##B);         DWM2T_CB_CASE(H##C); DWM2T_CB_CASE(H##D); DWM2T_CB_CASE(H##E); DWM2T_CB_CASE(H##F)
        DWM2T_CB_ROW(0x0);
        DWM2T_CB_ROW(0x1);
        DWM2T_CB_ROW(0x2);
        DWM2T_CB_ROW(0x3);
        DWM2T_CB_ROW(0x4);
        DWM2T_CB_ROW(0x5);
        DWM2T_CB_ROW(0x6);
        DWM2T_CB_ROW(0x7);
        DWM2T_CB_ROW(0x8);
        DWM2T_CB_ROW(0x9);
        DWM2T_CB_ROW(0xA);
        DWM2T_CB_ROW(0xB);
        DWM2T_CB_ROW(0xC);
        DWM2T_CB_ROW(0xD);
        DWM2T_CB_ROW(0xE);
        DWM2T_CB_ROW(0xF);
#undef DWM2T_CB_ROW
    }
#undef DWM2T_CB_CASE
}

template <std::uint8_t OP>
inline void exec_base(Cpu& cpu, Memory& memory,
                      std::uint8_t imm8, std::uint16_t imm16,
                      std::uint16_t opcode_pc) {
    constexpr int x = OP >> 6;
    constexpr int y = (OP >> 3) & 7;
    constexpr int z = OP & 7;
    constexpr int p = y >> 1;
    constexpr int q = y & 1;

    if constexpr (
        OP == 0xD3 || OP == 0xDB || OP == 0xDD ||
        OP == 0xE3 || OP == 0xE4 || OP == 0xEB ||
        OP == 0xEC || OP == 0xED || OP == 0xF4 ||
        OP == 0xFC || OP == 0xFD) {
        cpu.trap(opcode_pc, OP);
        return;
    }

    if constexpr (x == 0) {
        if constexpr (z == 0) {
            if constexpr (y == 0) {
                return;
            } else if constexpr (y == 1) {
                memory.write8(imm16, static_cast<std::uint8_t>(cpu.sp));
                memory.write8(static_cast<std::uint16_t>(imm16 + 1),
                              static_cast<std::uint8_t>(cpu.sp >> 8));
            } else if constexpr (y == 2) {
                cpu.stopped = true;
            } else if constexpr (y == 3) {
                cpu.pc = add_signed(cpu.pc, imm8);
            } else {
                if (condition<y - 4>(cpu)) cpu.pc = add_signed(cpu.pc, imm8);
            }
        } else if constexpr (z == 1) {
            if constexpr (q == 0) write_rp<p>(cpu, imm16);
            else add_hl(cpu, read_rp<p>(cpu));
        } else if constexpr (z == 2) {
            if constexpr (q == 0) {
                if constexpr (p == 0) memory.write8(cpu.bc(), cpu.a);
                else if constexpr (p == 1) memory.write8(cpu.de(), cpu.a);
                else if constexpr (p == 2) {
                    memory.write8(cpu.hl(), cpu.a);
                    cpu.set_hl(static_cast<std::uint16_t>(cpu.hl() + 1));
                } else {
                    memory.write8(cpu.hl(), cpu.a);
                    cpu.set_hl(static_cast<std::uint16_t>(cpu.hl() - 1));
                }
            } else {
                if constexpr (p == 0) cpu.a = memory.read8(cpu.bc());
                else if constexpr (p == 1) cpu.a = memory.read8(cpu.de());
                else if constexpr (p == 2) {
                    cpu.a = memory.read8(cpu.hl());
                    cpu.set_hl(static_cast<std::uint16_t>(cpu.hl() + 1));
                } else {
                    cpu.a = memory.read8(cpu.hl());
                    cpu.set_hl(static_cast<std::uint16_t>(cpu.hl() - 1));
                }
            }
        } else if constexpr (z == 3) {
            if constexpr (q == 0) write_rp<p>(cpu, static_cast<std::uint16_t>(read_rp<p>(cpu) + 1));
            else write_rp<p>(cpu, static_cast<std::uint16_t>(read_rp<p>(cpu) - 1));
        } else if constexpr (z == 4) {
            write_r8<y>(cpu, memory, inc8(cpu, read_r8<y>(cpu, memory)));
        } else if constexpr (z == 5) {
            write_r8<y>(cpu, memory, dec8(cpu, read_r8<y>(cpu, memory)));
        } else if constexpr (z == 6) {
            write_r8<y>(cpu, memory, imm8);
        } else {
            if constexpr (y == 0) cpu.a = rlc(cpu, cpu.a, false);
            else if constexpr (y == 1) cpu.a = rrc(cpu, cpu.a, false);
            else if constexpr (y == 2) cpu.a = rl(cpu, cpu.a, false);
            else if constexpr (y == 3) cpu.a = rr(cpu, cpu.a, false);
            else if constexpr (y == 4) daa(cpu);
            else if constexpr (y == 5) {
                cpu.a = static_cast<std::uint8_t>(~cpu.a);
                cpu.set_flag(Cpu::FlagN, true);
                cpu.set_flag(Cpu::FlagH, true);
            } else if constexpr (y == 6) {
                const bool zf = cpu.flag(Cpu::FlagZ);
                cpu.set_flags(zf, false, false, true);
            } else {
                const bool zf = cpu.flag(Cpu::FlagZ);
                const bool cf = !cpu.flag(Cpu::FlagC);
                cpu.set_flags(zf, false, false, cf);
            }
        }
    } else if constexpr (x == 1) {
        if constexpr (y == 6 && z == 6) {
            if (!cpu.ime && memory.pending_interrupts() != 0) {
                cpu.halt_bug = true;
                cpu.halted = false;
            } else {
                cpu.halted = true;
            }
        } else {
            write_r8<y>(cpu, memory, read_r8<z>(cpu, memory));
        }
    } else if constexpr (x == 2) {
        alu<y>(cpu, read_r8<z>(cpu, memory));
    } else {
        if constexpr (z == 0) {
            if constexpr (y < 4) {
                if (condition<y>(cpu)) cpu.pc = pop16(cpu, memory);
            } else if constexpr (y == 4) {
                memory.write8(static_cast<std::uint16_t>(0xFF00u + imm8), cpu.a);
            } else if constexpr (y == 5) {
                cpu.sp = add_sp_value(cpu, cpu.sp, imm8);
            } else if constexpr (y == 6) {
                cpu.a = memory.read8(static_cast<std::uint16_t>(0xFF00u + imm8));
            } else {
                cpu.set_hl(add_sp_value(cpu, cpu.sp, imm8));
            }
        } else if constexpr (z == 1) {
            if constexpr (q == 0) {
                write_rp2<p>(cpu, pop16(cpu, memory));
            } else {
                if constexpr (p == 0) {
                    cpu.pc = pop16(cpu, memory);
                } else if constexpr (p == 1) {
                    cpu.pc = pop16(cpu, memory);
                    cpu.ime = true;
                    cpu.ime_delay = 0;
                } else if constexpr (p == 2) {
                    cpu.pc = cpu.hl();
                } else {
                    cpu.sp = cpu.hl();
                }
            }
        } else if constexpr (z == 2) {
            if constexpr (y < 4) {
                if (condition<y>(cpu)) cpu.pc = imm16;
            } else if constexpr (y == 4) {
                memory.write8(static_cast<std::uint16_t>(0xFF00u + cpu.c), cpu.a);
            } else if constexpr (y == 5) {
                memory.write8(imm16, cpu.a);
            } else if constexpr (y == 6) {
                cpu.a = memory.read8(static_cast<std::uint16_t>(0xFF00u + cpu.c));
            } else {
                cpu.a = memory.read8(imm16);
            }
        } else if constexpr (z == 3) {
            if constexpr (y == 0) {
                cpu.pc = imm16;
            } else if constexpr (y == 1) {
                cpu.trap(opcode_pc, OP);
            } else if constexpr (y == 6) {
                cpu.ime = false;
                cpu.ime_delay = 0;
            } else if constexpr (y == 7) {
                cpu.schedule_ime_enable();
            } else {
                cpu.trap(opcode_pc, OP);
            }
        } else if constexpr (z == 4) {
            if constexpr (y < 4) {
                if (condition<y>(cpu)) {
                    push16(cpu, memory, cpu.pc);
                    cpu.pc = imm16;
                }
            } else {
                cpu.trap(opcode_pc, OP);
            }
        } else if constexpr (z == 5) {
            if constexpr (q == 0) {
                push16(cpu, memory, read_rp2<p>(cpu));
            } else {
                if constexpr (p == 0) {
                    push16(cpu, memory, cpu.pc);
                    cpu.pc = imm16;
                } else {
                    cpu.trap(opcode_pc, OP);
                }
            }
        } else if constexpr (z == 6) {
            alu<y>(cpu, imm8);
        } else {
            push16(cpu, memory, cpu.pc);
            cpu.pc = static_cast<std::uint16_t>(y * 8);
        }
    }
}

} // namespace dwm2t::lr35902
