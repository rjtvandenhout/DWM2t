#pragma once

#include <cstdint>

namespace dwm2t {

struct Cpu {
    static constexpr std::uint8_t FlagZ = 0x80;
    static constexpr std::uint8_t FlagN = 0x40;
    static constexpr std::uint8_t FlagH = 0x20;
    static constexpr std::uint8_t FlagC = 0x10;

    std::uint8_t a = 0;
    std::uint8_t b = 0;
    std::uint8_t c = 0;
    std::uint8_t d = 0;
    std::uint8_t e = 0;
    std::uint8_t h = 0;
    std::uint8_t l = 0;
    std::uint8_t f = 0;

    std::uint16_t sp = 0xFFFE;
    std::uint16_t pc = 0x0000;

    bool ime = false;
    std::uint8_t ime_delay = 0;
    bool halted = false;
    bool stopped = false;
    bool halt_bug = false;
    bool trapped = false;
    std::uint16_t trap_pc = 0;
    std::uint8_t trap_opcode = 0;

    std::uint8_t last_mcycles = 0;
    std::uint16_t missing_bank = 0xFFFF;

    [[nodiscard]] std::uint16_t af() const {
        return static_cast<std::uint16_t>(
            (static_cast<std::uint16_t>(a) << 8) | (f & 0xF0));
    }

    [[nodiscard]] std::uint16_t bc() const {
        return static_cast<std::uint16_t>(
            (static_cast<std::uint16_t>(b) << 8) | c);
    }

    [[nodiscard]] std::uint16_t de() const {
        return static_cast<std::uint16_t>(
            (static_cast<std::uint16_t>(d) << 8) | e);
    }

    [[nodiscard]] std::uint16_t hl() const {
        return static_cast<std::uint16_t>(
            (static_cast<std::uint16_t>(h) << 8) | l);
    }

    void set_af(std::uint16_t value) {
        a = static_cast<std::uint8_t>(value >> 8);
        f = static_cast<std::uint8_t>(value & 0xF0);
    }

    void set_bc(std::uint16_t value) {
        b = static_cast<std::uint8_t>(value >> 8);
        c = static_cast<std::uint8_t>(value);
    }

    void set_de(std::uint16_t value) {
        d = static_cast<std::uint8_t>(value >> 8);
        e = static_cast<std::uint8_t>(value);
    }

    void set_hl(std::uint16_t value) {
        h = static_cast<std::uint8_t>(value >> 8);
        l = static_cast<std::uint8_t>(value);
    }

    [[nodiscard]] bool flag(std::uint8_t mask) const {
        return (f & mask) != 0;
    }

    [[nodiscard]] bool zero() const {
        return flag(FlagZ);
    }

    [[nodiscard]] bool carry() const {
        return flag(FlagC);
    }

    void set_flag(std::uint8_t mask, bool enabled) {
        if (enabled) {
            f = static_cast<std::uint8_t>(f | mask);
        } else {
            f = static_cast<std::uint8_t>(f & ~mask);
        }
        f &= 0xF0;
    }

    void set_flags(bool z, bool n, bool hflag, bool cflag) {
        f = static_cast<std::uint8_t>(
            (z ? FlagZ : 0) |
            (n ? FlagN : 0) |
            (hflag ? FlagH : 0) |
            (cflag ? FlagC : 0));
    }

    void schedule_ime_enable() {
        ime_delay = 2;
    }

    void finish_instruction() {
        if (ime_delay != 0) {
            --ime_delay;
            if (ime_delay == 0) {
                ime = true;
            }
        }
        f &= 0xF0;
    }

    void trap(std::uint16_t at_pc, std::uint8_t opcode) {
        trapped = true;
        trap_pc = at_pc;
        trap_opcode = opcode;
    }
};

} // namespace dwm2t
