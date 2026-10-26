#include "recomp/memory.hpp"
#include "recomp/renderer.hpp"

#include <array>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {

using dwm2t::Memory;
using dwm2t::Renderer;

constexpr std::uint32_t White = 0xFFFFFFFFu;
constexpr std::uint32_t Red = 0xFFFF0000u;
constexpr std::uint32_t Green = 0xFF00FF00u;
constexpr std::uint32_t Blue = 0xFF0000FFu;

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

void palette(Memory& memory, bool obj, unsigned number,
             const std::array<std::uint16_t, 4>& colors) {
    const std::uint16_t index = obj ? 0xFF6A : 0xFF68;
    const std::uint16_t data = obj ? 0xFF6B : 0xFF69;
    memory.write8(index, static_cast<std::uint8_t>(0x80u | (number * 8u)));
    for (const auto color : colors) {
        memory.write8(data, static_cast<std::uint8_t>(color));
        memory.write8(data, static_cast<std::uint8_t>(color >> 8));
    }
}

void solid_tile(Memory& memory, unsigned number, std::uint8_t color) {
    for (unsigned row = 0; row < 8; ++row) {
        const auto address = static_cast<std::uint16_t>(0x8000u + number * 16u + row * 2u);
        memory.write8(address, (color & 1u) ? 0xFF : 0x00);
        memory.write8(static_cast<std::uint16_t>(address + 1),
                      (color & 2u) ? 0xFF : 0x00);
    }
}

void obj(Memory& memory, unsigned number, unsigned x, unsigned y,
         std::uint8_t tile, std::uint8_t attributes) {
    const auto address = static_cast<std::uint16_t>(0xFE00u + number * 4u);
    memory.write8(address, static_cast<std::uint8_t>(y + 16u));
    memory.write8(static_cast<std::uint16_t>(address + 1), static_cast<std::uint8_t>(x + 8u));
    memory.write8(static_cast<std::uint16_t>(address + 2), tile);
    memory.write8(static_cast<std::uint16_t>(address + 3), attributes);
}

void obj_fixture(Memory& memory) {
    palette(memory, false, 0, {0x7FFF, 0x001F, 0x03E0, 0x7C00});
    palette(memory, true, 0, {0x7FFF, 0x03E0, 0x001F, 0x7C00});
    palette(memory, true, 1, {0x7FFF, 0x7C00, 0x001F, 0x03E0});
    solid_tile(memory, 0, 1); // Red background.
    solid_tile(memory, 1, 1); // Green/blue object, depending on palette.
    solid_tile(memory, 2, 0); // Transparent object.
    obj(memory, 0, 0, 0, 1, 0);
    obj(memory, 1, 0, 0, 1, 1);
    memory.write8(0xFF40, 0x93);
}

void priority_contracts() {
    Memory memory;
    Renderer renderer;
    obj_fixture(memory);

    require(renderer.render(memory, true)[0] == Green,
            "CGB lower OAM index must win an opaque object overlap");

    obj(memory, 0, 0, 0, 1, 0x80);
    require(renderer.render(memory, true)[0] == Red,
            "BG-hidden highest-priority opaque OBJ must block the lower OBJ");

    memory.write8(0xFF4F, 1);
    memory.write8(0x9800, 0x80);
    memory.write8(0xFF4F, 0);
    memory.write8(0xFF40, 0x92);
    require(renderer.render(memory, true)[0] == Green,
            "CGB LCDC bit0 clear must override both tile and OBJ BG priority");

    memory.write8(0xFF40, 0x93);
    memory.write8(0xFF4F, 1);
    memory.write8(0x9800, 0);
    memory.write8(0xFF4F, 0);
    obj(memory, 0, 0, 0, 2, 0x80);
    require(renderer.render(memory, true)[0] == Blue,
            "Transparent highest-priority OBJ must allow the lower OBJ pixel");
}

void dmg_priority_contracts() {
    Memory memory;
    Renderer renderer;
    solid_tile(memory, 0, 0);
    solid_tile(memory, 1, 1);
    memory.write8(0xFF47, 0xE4);
    memory.write8(0xFF48, 0xE4); // Color1 is light gray.
    memory.write8(0xFF49, 0x0C); // Color1 is black.
    obj(memory, 0, 5, 0, 1, 0x00);
    obj(memory, 1, 0, 0, 1, 0x10);
    memory.write8(0xFF40, 0x93);

    require(renderer.render(memory, false)[5] == 0xFF000000u,
            "DMG leftmost selected OBJ must beat a lower OAM index");
    obj(memory, 0, 0, 0, 1, 0x00);
    require(renderer.render(memory, false)[0] == 0xFFAAAAAAu,
            "DMG equal-X objects must retain OAM index priority");
}

void scroll_fixture(Memory& memory) {
    palette(memory, false, 0, {0x7FFF, 0x001F, 0x03E0, 0x7C00});
    // Four colors independently identify the low bits of X and Y:
    // white/red on even rows, green/blue on odd rows.
    for (unsigned row = 0; row < 8; ++row) {
        const auto address = static_cast<std::uint16_t>(0x8000u + row * 2u);
        memory.write8(address, 0x55);
        memory.write8(static_cast<std::uint16_t>(address + 1),
                      (row & 1u) ? 0xFF : 0x00);
    }
    memory.write8(0xFF40, 0x91);
}

void scanline_scroll_contracts() {
    Memory memory;
    Renderer renderer;
    scroll_fixture(memory);
    require(!memory.has_scanline_scroll(),
            "Fresh LCD state must use direct-register rendering before a full frame");
    memory.write8(0xFF43, 1);
    memory.write8(0xFF42, 1);
    require(renderer.render(memory, true)[0] == Blue,
            "Pre-frame renderer must use both live SCX and live SCY");

    std::array<std::uint8_t, Renderer::Height> scroll_x{};
    std::array<std::uint8_t, Renderer::Height> scroll_y{};
    for (unsigned line = 0; line < Renderer::Height; ++line) {
        scroll_x[line] = static_cast<std::uint8_t>(line & 1u);
        scroll_y[line] = static_cast<std::uint8_t>((line >> 1) & 1u);
        memory.write8(0xFF43, scroll_x[line]);
        memory.write8(0xFF42, scroll_y[line]);
        memory.tick_tcycles(80);
        // Mutating registers after the latch must not change this line.
        memory.write8(0xFF43, static_cast<std::uint8_t>(scroll_x[line] ^ 1u));
        memory.write8(0xFF42, static_cast<std::uint8_t>(scroll_y[line] ^ 1u));
        memory.tick_tcycles(376);
        if (line + 1 < Renderer::Height) {
            require(!memory.has_scanline_scroll(),
                    "A partial visible frame must not publish scroll latches");
        }
    }
    require(memory.has_scanline_scroll(),
            "The first complete visible frame must publish at VBlank");
    const auto& frame = renderer.render(memory, true);
    constexpr std::array<std::uint32_t, 4> colors = {White, Red, Green, Blue};
    for (unsigned line = 0; line < Renderer::Height; ++line) {
        require(memory.scanline_scx(line) == scroll_x[line],
                "Completed SCX latch changed after its capture point");
        require(memory.scanline_scy(line) == scroll_y[line],
                "Completed SCY latch changed after its capture point");
        const unsigned color = scroll_x[line] + 2u * ((line + scroll_y[line]) & 1u);
        require(frame[line * Renderer::Width] == colors[color],
                "Rendered row did not use its own SCX and SCY latches");
    }

    memory.tick_tcycles(10u * 456u); // Leave VBlank, entering the next line0.
    memory.write8(0xFF43, 1);
    memory.write8(0xFF42, 1);
    memory.tick_tcycles(80);
    require(memory.scanline_scx(0) == scroll_x[0] &&
            memory.scanline_scy(0) == scroll_y[0],
            "Building the next frame must not mutate the completed frame");
    require(renderer.render(memory, true)[0] == White,
            "Renderer must keep the published frame while the next is partial");

    memory.write8(0xFF40, 0);
    require(!memory.has_scanline_scroll(),
            "LCD disable must invalidate completed scroll latches");
    memory.write8(0xFF40, 0x91);
    memory.write8(0xFF43, 1);
    memory.write8(0xFF42, 0);
    require(renderer.render(memory, true)[0] == Red,
            "LCD restart must use fresh live registers until another full frame");
}

} // namespace

int main(int argc, char** argv) {
    try {
        priority_contracts();
        dmg_priority_contracts();
        scanline_scroll_contracts();
        if (argc > 1) {
            const std::filesystem::path directory(argv[1]);
            std::filesystem::create_directories(directory);
            std::ofstream evidence(directory / "renderer-contracts.json");
            evidence << "{\n  \"status\": \"passed\",\n"
                        "  \"contracts\": [\"cgb-object-priority\", \"dmg-object-priority\", "
                        "\"per-line-scroll-publication\"]\n}\n";
            if (!evidence) throw std::runtime_error("Could not write renderer contract evidence");
        }
        std::cout << "PASS: CGB/DMG object priorities and full-frame SCX/SCY publication\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL: renderer contracts: " << error.what() << '\n';
        return 1;
    }
}
