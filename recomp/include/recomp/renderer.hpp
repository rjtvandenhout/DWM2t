#pragma once

#include "recomp/memory.hpp"

#include <array>
#include <cstdint>
#include <filesystem>

namespace dwm2t {

class Renderer {
public:
    static constexpr int Width = 160;
    static constexpr int Height = 144;
    using Framebuffer = std::array<std::uint32_t, Width * Height>;

    const Framebuffer& render(const Memory& memory, bool cgb_mode = true);

    [[nodiscard]] const Framebuffer& framebuffer() const { return framebuffer_; }
    [[nodiscard]] std::uint64_t hash() const;

    bool write_bmp(const std::filesystem::path& path) const;

private:
    static std::uint32_t cgb_color(
        const std::array<std::uint8_t, 0x40>& palette_ram,
        unsigned palette,
        unsigned color);

    Framebuffer framebuffer_{};
    std::array<std::uint8_t, Width * Height> bg_color_index_{};
    std::array<std::uint8_t, Width * Height> bg_priority_{};
};

} // namespace dwm2t
