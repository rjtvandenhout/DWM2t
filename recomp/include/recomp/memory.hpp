#pragma once

#include "recomp/apu.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <vector>

namespace dwm2t {

enum JoypadButton : std::uint8_t {
    JoyRight  = 1u << 0,
    JoyLeft   = 1u << 1,
    JoyUp     = 1u << 2,
    JoyDown   = 1u << 3,
    JoyA      = 1u << 4,
    JoyB      = 1u << 5,
    JoySelect = 1u << 6,
    JoyStart  = 1u << 7,
};

class Memory {
public:
    static constexpr std::size_t RomSize = 0x400000;
    static constexpr std::size_t RomBankSize = 0x4000;
    static constexpr std::size_t VramBankSize = 0x2000;
    static constexpr std::size_t SramSize = 0x8000;

    Memory();

    void clear();

    void load_rom(const std::uint8_t* data, std::size_t size);
    void set_rom_byte(std::size_t offset, std::uint8_t value);
    [[nodiscard]] const std::vector<std::uint8_t>& rom() const { return rom_; }

    void load_sram(const std::uint8_t* data, std::size_t size);
    [[nodiscard]] const std::array<std::uint8_t, SramSize>& sram() const { return sram_; }
    [[nodiscard]] bool sram_dirty() const { return sram_dirty_; }
    void clear_sram_dirty() { sram_dirty_ = false; }

    [[nodiscard]] std::uint8_t read8(std::uint16_t address) const;
    void write8(std::uint16_t address, std::uint8_t value);

    [[nodiscard]] std::uint16_t current_rom_bank() const { return rom_bank_ & 0x01FFu; }
    [[nodiscard]] std::uint8_t current_ram_bank() const { return static_cast<std::uint8_t>(ram_bank_ & 0x0Fu); }
    [[nodiscard]] bool ram_enabled() const { return ram_enabled_; }

    void set_joypad_state(std::uint8_t pressed_mask);
    [[nodiscard]] std::uint8_t joypad_state() const { return joypad_pressed_; }

    [[nodiscard]] std::uint8_t pending_interrupts() const;
    void request_interrupt(std::uint8_t bit);
    void clear_interrupt(std::uint8_t bit);

    void tick_mcycles(std::uint32_t mcycles);
    void tick_tcycles(std::uint32_t tcycles);
    [[nodiscard]] std::uint64_t total_tcycles() const { return total_tcycles_; }

    [[nodiscard]] std::uint8_t* vram_bank_data(std::uint8_t bank) {
        return vram_[bank & 1u].data();
    }
    [[nodiscard]] const std::uint8_t* vram_bank_data(std::uint8_t bank) const {
        return vram_[bank & 1u].data();
    }

    [[nodiscard]] std::uint8_t* oam_data() { return oam_.data(); }
    [[nodiscard]] const std::uint8_t* oam_data() const { return oam_.data(); }

    [[nodiscard]] std::uint8_t io(std::uint8_t offset) const;
    void set_io_direct(std::uint8_t offset, std::uint8_t value);

    [[nodiscard]] std::uint16_t ppu_dot() const { return ppu_dot_; }
    [[nodiscard]] std::uint8_t ly() const { return io_[0x44]; }
    [[nodiscard]] std::uint64_t frame_counter() const { return frame_counter_; }
    [[nodiscard]] Apu& apu() { return apu_; }
    [[nodiscard]] const Apu& apu() const { return apu_; }

    [[nodiscard]] const std::array<std::uint8_t, 0x40>& bg_palette_ram() const {
        return bg_palette_;
    }
    [[nodiscard]] const std::array<std::uint8_t, 0x40>& obj_palette_ram() const {
        return obj_palette_;
    }

private:
    [[nodiscard]] std::uint8_t read_joypad() const;
    [[nodiscard]] std::uint8_t read_stat() const;
    [[nodiscard]] std::uint8_t selected_wram_bank() const;

    void write_div();
    void write_tac(std::uint8_t value);
    [[nodiscard]] bool timer_input() const;
    void timer_falling_edge();
    void tick_one_tcycle();
    void tick_ppu_one_tcycle();
    void update_stat_interrupt_line();
    void do_oam_dma(std::uint8_t page);

    std::vector<std::uint8_t> rom_;
    std::array<std::array<std::uint8_t, VramBankSize>, 2> vram_{};
    std::array<std::uint8_t, SramSize> sram_{};
    std::array<std::uint8_t, 0x1000> wram0_{};
    std::array<std::array<std::uint8_t, 0x1000>, 8> wramx_{};
    std::array<std::uint8_t, 0xA0> oam_{};
    std::array<std::uint8_t, 0x80> io_{};
    std::array<std::uint8_t, 0x7F> hram_{};
    std::array<std::uint8_t, 0x40> bg_palette_{};
    std::array<std::uint8_t, 0x40> obj_palette_{};

    std::uint8_t ie_ = 0;
    std::uint16_t rom_bank_ = 1;
    std::uint8_t ram_bank_ = 0;
    bool ram_enabled_ = false;
    bool sram_dirty_ = false;

    std::uint8_t joypad_pressed_ = 0;
    std::uint8_t joypad_select_ = 0x30;

    std::uint16_t div_counter_ = 0;
    int tima_reload_delay_ = -1;
    std::uint64_t total_tcycles_ = 0;

    std::uint16_t ppu_dot_ = 0;
    std::uint64_t frame_counter_ = 0;
    bool stat_irq_line_ = false;
    Apu apu_{};
};

void load_full_rom_image(Memory& memory);
bool load_sram_file(Memory& memory, const std::filesystem::path& path);
bool save_sram_file(Memory& memory, const std::filesystem::path& path);

} // namespace dwm2t
