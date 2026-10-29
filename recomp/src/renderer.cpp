#include "recomp/renderer.hpp"

#include <algorithm>
#include <array>
#include <cstdint>
#include <fstream>
#include <vector>

namespace dwm2t {

namespace {

std::uint8_t expand5(std::uint8_t value) {
    return static_cast<std::uint8_t>((value * 255u + 15u) / 31u);
}

std::uint8_t dmg_shade(std::uint8_t palette, std::uint8_t color) {
    const unsigned shade = (palette >> (color * 2u)) & 3u;
    static constexpr std::uint8_t levels[4] = {255, 170, 85, 0};
    return levels[shade];
}

std::uint8_t tile_pixel(
    const std::uint8_t* bank,
    std::size_t tile_offset,
    unsigned x,
    unsigned y) {

    const std::size_t row = tile_offset + y * 2u;
    const std::uint8_t lo = bank[row];
    const std::uint8_t hi = bank[row + 1];
    const unsigned bit = 7u - x;
    return static_cast<std::uint8_t>(
        ((lo >> bit) & 1u) | (((hi >> bit) & 1u) << 1u));
}

#pragma pack(push, 1)
struct BitmapFileHeader {
    std::uint16_t type;
    std::uint32_t size;
    std::uint16_t reserved1;
    std::uint16_t reserved2;
    std::uint32_t off_bits;
};

struct BitmapInfoHeader {
    std::uint32_t size;
    std::int32_t width;
    std::int32_t height;
    std::uint16_t planes;
    std::uint16_t bit_count;
    std::uint32_t compression;
    std::uint32_t size_image;
    std::int32_t x_pels_per_meter;
    std::int32_t y_pels_per_meter;
    std::uint32_t clr_used;
    std::uint32_t clr_important;
};
#pragma pack(pop)

} // namespace

std::uint32_t Renderer::cgb_color(
    const std::array<std::uint8_t, 0x40>& ram,
    unsigned palette,
    unsigned color) {

    const unsigned index = ((palette & 7u) * 8u) + ((color & 3u) * 2u);
    const std::uint16_t bgr555 = static_cast<std::uint16_t>(
        ram[index] | (static_cast<std::uint16_t>(ram[index + 1]) << 8));

    const std::uint8_t r = expand5(static_cast<std::uint8_t>(bgr555 & 0x1Fu));
    const std::uint8_t g = expand5(static_cast<std::uint8_t>((bgr555 >> 5) & 0x1Fu));
    const std::uint8_t b = expand5(static_cast<std::uint8_t>((bgr555 >> 10) & 0x1Fu));

    return 0xFF000000u |
           (static_cast<std::uint32_t>(r) << 16) |
           (static_cast<std::uint32_t>(g) << 8) |
           b;
}

const Renderer::Framebuffer& Renderer::render(const Memory& memory, bool cgb_mode) {
    const std::uint8_t lcdc = memory.read8(0xFF40);

    if ((lcdc & 0x80u) == 0) {
        framebuffer_.fill(0xFFFFFFFFu);
        bg_color_index_.fill(0);
        bg_priority_.fill(0);
        return framebuffer_;
    }

    const auto* vram0 = memory.vram_bank_data(0);
    const auto* vram1 = memory.vram_bank_data(1);

    const std::uint8_t scy = memory.read8(0xFF42);
    const std::uint8_t scx = memory.read8(0xFF43);
    const std::uint8_t wy = memory.read8(0xFF4A);
    const std::uint8_t wx = memory.read8(0xFF4B);
    const bool scanline_scroll = memory.has_scanline_scroll();

    const bool window_enable = (lcdc & 0x20u) != 0;
    const std::size_t bg_map = (lcdc & 0x08u) ? 0x1C00u : 0x1800u;
    const std::size_t window_map = (lcdc & 0x40u) ? 0x1C00u : 0x1800u;
    const bool unsigned_tiles = (lcdc & 0x10u) != 0;
    const bool bg_priority_master = (lcdc & 0x01u) != 0;

    for (int sy = 0; sy < Height; ++sy) {
        const std::uint8_t line_scx = scanline_scroll
            ? memory.scanline_scx(static_cast<unsigned>(sy)) : scx;
        const std::uint8_t line_scy = scanline_scroll
            ? memory.scanline_scy(static_cast<unsigned>(sy)) : scy;
        for (int sx = 0; sx < Width; ++sx) {
            bool use_window = false;
            unsigned px = static_cast<unsigned>(sx + line_scx) & 0xFFu;
            unsigned py = static_cast<unsigned>(sy + line_scy) & 0xFFu;
            std::size_t map_base = bg_map;

            const int window_left = static_cast<int>(wx) - 7;
            if (window_enable &&
                sy >= static_cast<int>(wy) &&
                sx >= window_left &&
                window_left < Width) {
                use_window = true;
                px = static_cast<unsigned>(sx - window_left);
                py = static_cast<unsigned>(sy - wy);
                map_base = window_map;
            }

            (void)use_window;

            const unsigned tile_x = (px >> 3) & 31u;
            const unsigned tile_y = (py >> 3) & 31u;
            const std::size_t map_offset = map_base + tile_y * 32u + tile_x;

            const std::uint8_t tile_id = vram0[map_offset];
            const std::uint8_t attr = cgb_mode ? vram1[map_offset] : 0;

            unsigned tx = px & 7u;
            unsigned ty = py & 7u;
            if (attr & 0x20u) tx = 7u - tx;
            if (attr & 0x40u) ty = 7u - ty;

            std::size_t tile_offset = 0;
            if (unsigned_tiles) {
                tile_offset = static_cast<std::size_t>(tile_id) * 16u;
            } else {
                const auto signed_id = static_cast<std::int8_t>(tile_id);
                tile_offset = static_cast<std::size_t>(
                    0x1000 + static_cast<int>(signed_id) * 16);
            }

            const std::uint8_t* tile_bank =
                (cgb_mode && (attr & 0x08u)) ? vram1 : vram0;
            const std::uint8_t color = tile_pixel(tile_bank, tile_offset, tx, ty);
            const unsigned index = static_cast<unsigned>(sy * Width + sx);

            bg_color_index_[index] = color;
            bg_priority_[index] = static_cast<std::uint8_t>(
                cgb_mode && bg_priority_master && (attr & 0x80u) ? 1u : 0u);

            if (cgb_mode) {
                framebuffer_[index] = cgb_color(
                    memory.bg_palette_ram(), attr & 7u, color);
            } else {
                const std::uint8_t shade =
                    dmg_shade(memory.read8(0xFF47), color);
                framebuffer_[index] =
                    0xFF000000u |
                    (static_cast<std::uint32_t>(shade) << 16) |
                    (static_cast<std::uint32_t>(shade) << 8) |
                    shade;
            }
        }
    }

    if ((lcdc & 0x02u) == 0) return framebuffer_;

    const bool tall = (lcdc & 0x04u) != 0;
    const int sprite_height = tall ? 16 : 8;
    const auto* oam = memory.oam_data();

    for (int sy = 0; sy < Height; ++sy) {
        std::array<unsigned, 10> selected{};
        unsigned count = 0;

        for (unsigned sprite = 0; sprite < 40 && count < selected.size(); ++sprite) {
            const int y = static_cast<int>(oam[sprite * 4]) - 16;
            if (sy >= y && sy < y + sprite_height) {
                selected[count++] = sprite;
            }
        }

        // CGB uses OAM order. DMG gives the leftmost selected OBJ priority,
        // retaining OAM order for equal X positions.
        if (!cgb_mode) {
            std::stable_sort(selected.begin(), selected.begin() + count,
                [oam](unsigned first, unsigned second) {
                    return oam[first * 4 + 1] < oam[second * 4 + 1];
                });
        }

        std::array<bool, Width> obj_claimed{};
        for (unsigned selected_index = 0; selected_index < count; ++selected_index) {

            const unsigned sprite = selected[selected_index];
            const int y = static_cast<int>(oam[sprite * 4]) - 16;
            const int x = static_cast<int>(oam[sprite * 4 + 1]) - 8;
            std::uint8_t tile = oam[sprite * 4 + 2];
            const std::uint8_t attr = oam[sprite * 4 + 3];

            int row = sy - y;
            if (attr & 0x40u) row = sprite_height - 1 - row;

            if (tall) {
                tile &= 0xFEu;
                if (row >= 8) {
                    ++tile;
                    row -= 8;
                }
            }

            const std::uint8_t* tile_bank =
                (cgb_mode && (attr & 0x08u)) ? vram1 : vram0;
            const std::size_t tile_offset = static_cast<std::size_t>(tile) * 16u;

            for (int col = 0; col < 8; ++col) {
                const int sx = x + col;
                if (sx < 0 || sx >= Width) continue;

                unsigned tx = static_cast<unsigned>(col);
                if (attr & 0x20u) tx = 7u - tx;

                const std::uint8_t color = tile_pixel(
                    tile_bank, tile_offset, tx, static_cast<unsigned>(row));
                if (color == 0 || obj_claimed[static_cast<unsigned>(sx)]) continue;

                // OBJ-to-OBJ arbitration precedes BG priority. An opaque
                // winning OBJ still blocks lower-priority OBJs when the BG
                // subsequently hides its pixel.
                obj_claimed[static_cast<unsigned>(sx)] = true;

                const unsigned index = static_cast<unsigned>(sy * Width + sx);
                const bool bg_nonzero = bg_color_index_[index] != 0;
                const bool obj_behind_bg = (attr & 0x80u) != 0;

                if ((!cgb_mode || bg_priority_master) && bg_nonzero &&
                    (obj_behind_bg || bg_priority_[index] != 0)) {
                    continue;
                }

                if (cgb_mode) {
                    framebuffer_[index] = cgb_color(
                        memory.obj_palette_ram(), attr & 7u, color);
                } else {
                    const std::uint8_t palette =
                        memory.read8((attr & 0x10u) ? 0xFF49 : 0xFF48);
                    const std::uint8_t shade = dmg_shade(palette, color);
                    framebuffer_[index] =
                        0xFF000000u |
                        (static_cast<std::uint32_t>(shade) << 16) |
                        (static_cast<std::uint32_t>(shade) << 8) |
                        shade;
                }
            }
        }
    }

    return framebuffer_;
}

std::uint64_t Renderer::hash() const {
    std::uint64_t h = 1469598103934665603ull;
    for (const std::uint32_t pixel : framebuffer_) {
        for (unsigned shift = 0; shift < 32; shift += 8) {
            h ^= static_cast<std::uint8_t>(pixel >> shift);
            h *= 1099511628211ull;
        }
    }
    return h;
}

bool Renderer::write_bmp(const std::filesystem::path& path) const {
    std::ofstream file(path, std::ios::binary);
    if (!file) return false;

    constexpr std::uint32_t image_size =
        static_cast<std::uint32_t>(Width * Height * sizeof(std::uint32_t));
    constexpr std::uint32_t header_size =
        sizeof(BitmapFileHeader) + sizeof(BitmapInfoHeader);

    const BitmapFileHeader file_header{
        0x4D42,
        header_size + image_size,
        0,
        0,
        header_size,
    };

    const BitmapInfoHeader info_header{
        sizeof(BitmapInfoHeader),
        Width,
        -Height,
        1,
        32,
        0,
        image_size,
        2835,
        2835,
        0,
        0,
    };

    file.write(
        reinterpret_cast<const char*>(&file_header),
        sizeof(file_header));
    file.write(
        reinterpret_cast<const char*>(&info_header),
        sizeof(info_header));
    file.write(
        reinterpret_cast<const char*>(framebuffer_.data()),
        image_size);

    return static_cast<bool>(file);
}

} // namespace dwm2t
