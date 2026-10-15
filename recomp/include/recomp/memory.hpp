#pragma once

#include <array>
#include <cstdint>

namespace dwm2t {

class Memory {
public:
    [[nodiscard]] std::uint8_t read8(std::uint16_t address) const {
        return bytes_[address];
    }

    void write8(std::uint16_t address, std::uint8_t value) {
        bytes_[address] = value;
    }

    void clear() {
        bytes_.fill(0);
    }

private:
    std::array<std::uint8_t, 0x10000> bytes_{};
};

} // namespace dwm2t
