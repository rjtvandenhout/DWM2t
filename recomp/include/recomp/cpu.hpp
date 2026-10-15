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

    [[nodiscard]] bool zero() const {
        return (f & FlagZ) != 0;
    }

    void or_a(std::uint8_t value) {
        a = static_cast<std::uint8_t>(a | value);
        f = (a == 0) ? FlagZ : 0;
    }
};

} // namespace dwm2t
