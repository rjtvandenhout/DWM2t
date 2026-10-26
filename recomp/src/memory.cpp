#include "recomp/memory.hpp"
#include "recomp/atomic_sram.hpp"

#include <algorithm>
#include <array>
#include <fstream>
#include <stdexcept>

namespace dwm2t {

namespace {

constexpr std::uint16_t kAddrP1   = 0xFF00;
constexpr std::uint16_t kAddrSB   = 0xFF01;
constexpr std::uint16_t kAddrSC   = 0xFF02;
constexpr std::uint16_t kAddrDIV  = 0xFF04;
constexpr std::uint16_t kAddrTIMA = 0xFF05;
constexpr std::uint16_t kAddrTMA  = 0xFF06;
constexpr std::uint16_t kAddrTAC  = 0xFF07;
constexpr std::uint16_t kAddrIF   = 0xFF0F;
constexpr std::uint16_t kAddrLCDC = 0xFF40;
constexpr std::uint16_t kAddrSTAT = 0xFF41;
constexpr std::uint16_t kAddrLY   = 0xFF44;
constexpr std::uint16_t kAddrLYC  = 0xFF45;
constexpr std::uint16_t kAddrDMA  = 0xFF46;
constexpr std::uint16_t kAddrKEY1 = 0xFF4D;
constexpr std::uint16_t kAddrVBK  = 0xFF4F;
constexpr std::uint16_t kAddrHDMA5 = 0xFF55;
constexpr std::uint16_t kAddrRP   = 0xFF56;
constexpr std::uint16_t kAddrBGPI = 0xFF68;
constexpr std::uint16_t kAddrBGPD = 0xFF69;
constexpr std::uint16_t kAddrOBPI = 0xFF6A;
constexpr std::uint16_t kAddrOBPD = 0xFF6B;
constexpr std::uint16_t kAddrSVBK = 0xFF70;

constexpr std::uint8_t io_index(std::uint16_t address) {
    return static_cast<std::uint8_t>(address - 0xFF00u);
}

} // namespace

Memory::Memory()
    : rom_(RomSize, 0) {
    clear();
}

void Memory::clear() {
    std::fill(rom_.begin(), rom_.end(), 0);
    for (auto& bank : vram_) bank.fill(0);
    sram_.fill(0);
    wram0_.fill(0);
    for (auto& bank : wramx_) bank.fill(0);
    oam_.fill(0);
    io_.fill(0);
    hram_.fill(0);
    bg_palette_.fill(0xFF);
    obj_palette_.fill(0xFF);

    ie_ = 0;
    rom_bank_ = 1;
    ram_bank_ = 0;
    ram_enabled_ = false;
    sram_dirty_ = false;

    joypad_pressed_ = 0;
    joypad_select_ = 0x30;
    stop_wake_ = false;

    div_counter_ = 0;
    tima_reload_delay_ = -1;
    total_tcycles_ = 0;
    total_base_tcycles_ = 0;
    double_speed_ = false;
    base_clock_phase_ = false;
    serial_.reset();
    vram_dma_source_ = 0;
    vram_dma_destination_ = 0x8000;
    vram_dma_blocks_ = 0;
    vram_dma_active_ = false;
    cpu_stall_mcycles_ = 0;

    ppu_dot_ = 0;
    frame_counter_ = 0;
    stat_irq_line_ = false;
    invalidate_scanline_scroll();
    apu_.reset();

    io_[io_index(kAddrP1)] = 0xCF;
    io_[io_index(kAddrIF)] = 0x00;
    io_[io_index(kAddrLCDC)] = 0x00;
    io_[io_index(kAddrSTAT)] = 0x80;
    io_[io_index(kAddrLY)] = 0;
    io_[io_index(kAddrLYC)] = 0;
    io_[io_index(kAddrVBK)] = 0;
    io_[io_index(kAddrBGPI)] = 0;
    io_[io_index(kAddrOBPI)] = 0;
    io_[io_index(kAddrSVBK)] = 1;
    io_[io_index(kAddrHDMA5)] = 0xFF;
}

void Memory::load_rom(const std::uint8_t* data, std::size_t size) {
    if (size != RomSize) {
        throw std::runtime_error("DWM2t runtime expected exactly 4 MiB of ROM data");
    }
    std::copy_n(data, size, rom_.begin());
}

void Memory::set_rom_byte(std::size_t offset, std::uint8_t value) {
    if (offset >= rom_.size()) {
        throw std::out_of_range("ROM byte offset");
    }
    rom_[offset] = value;
}

void Memory::load_sram(const std::uint8_t* data, std::size_t size) {
    if (size != SramSize) {
        throw std::runtime_error("DWM2t runtime expected exactly 32 KiB of SRAM data");
    }
    std::copy_n(data, size, sram_.begin());
    sram_dirty_ = false;
}

std::uint8_t Memory::selected_wram_bank() const {
    std::uint8_t bank = static_cast<std::uint8_t>(io_[io_index(kAddrSVBK)] & 0x07u);
    return bank == 0 ? 1 : bank;
}

std::uint8_t Memory::read_joypad() const {
    std::uint8_t result = static_cast<std::uint8_t>(0xC0u | joypad_select_ | 0x0Fu);

    if ((joypad_select_ & 0x10u) == 0) {
        if (joypad_pressed_ & JoyRight) result &= static_cast<std::uint8_t>(~0x01u);
        if (joypad_pressed_ & JoyLeft)  result &= static_cast<std::uint8_t>(~0x02u);
        if (joypad_pressed_ & JoyUp)    result &= static_cast<std::uint8_t>(~0x04u);
        if (joypad_pressed_ & JoyDown)  result &= static_cast<std::uint8_t>(~0x08u);
    }

    if ((joypad_select_ & 0x20u) == 0) {
        if (joypad_pressed_ & JoyA)      result &= static_cast<std::uint8_t>(~0x01u);
        if (joypad_pressed_ & JoyB)      result &= static_cast<std::uint8_t>(~0x02u);
        if (joypad_pressed_ & JoySelect) result &= static_cast<std::uint8_t>(~0x04u);
        if (joypad_pressed_ & JoyStart)  result &= static_cast<std::uint8_t>(~0x08u);
    }

    return result;
}

std::uint8_t Memory::read_stat() const {
    const bool lcd_on = (io_[io_index(kAddrLCDC)] & 0x80u) != 0;
    std::uint8_t mode = 0;

    if (lcd_on) {
        const std::uint8_t line = io_[io_index(kAddrLY)];
        if (line >= 144) mode = 1;
        else if (ppu_dot_ < 80) mode = 2;
        else if (ppu_dot_ < 252) mode = 3;
        else mode = 0;
    }

    std::uint8_t value = static_cast<std::uint8_t>(
        0x80u | (io_[io_index(kAddrSTAT)] & 0x78u) | mode);
    if (io_[io_index(kAddrLY)] == io_[io_index(kAddrLYC)]) value |= 0x04u;
    return value;
}

std::uint8_t Memory::read8(std::uint16_t address) const {
    if (address < 0x4000) {
        return rom_[address];
    }
    if (address < 0x8000) {
        const std::size_t bank = current_rom_bank();
        const std::size_t offset = bank * RomBankSize + (address - 0x4000u);
        return offset < rom_.size() ? rom_[offset] : 0xFF;
    }
    if (address < 0xA000) {
        const std::uint8_t bank = static_cast<std::uint8_t>(io_[io_index(kAddrVBK)] & 1u);
        return vram_[bank][address - 0x8000u];
    }
    if (address < 0xC000) {
        if (!ram_enabled_) return 0xFF;
        const std::size_t bank = static_cast<std::size_t>(ram_bank_ & 0x03u);
        return sram_[bank * 0x2000u + (address - 0xA000u)];
    }
    if (address < 0xD000) {
        return wram0_[address - 0xC000u];
    }
    if (address < 0xE000) {
        return wramx_[selected_wram_bank()][address - 0xD000u];
    }
    if (address < 0xFE00) {
        return read8(static_cast<std::uint16_t>(address - 0x2000u));
    }
    if (address < 0xFEA0) {
        return oam_[address - 0xFE00u];
    }
    if (address < 0xFF00) {
        return 0xFF;
    }
    if (address < 0xFF80) {
        if (address >= 0xFF10 && address <= 0xFF3F) return apu_.read(address);
        switch (address) {
            case kAddrP1:   return read_joypad();
            case kAddrSB:   return serial_.data();
            case kAddrSC:   return serial_.control();
            case kAddrDIV:  return static_cast<std::uint8_t>(div_counter_ >> 8);
            case kAddrIF:   return static_cast<std::uint8_t>(
                0xE0u | (io_[0x0F] & 0x1Fu) | (serial_.interrupt_pending() ? 8u : 0u));
            case kAddrSTAT: return read_stat();
            case kAddrLY:   return io_[0x44];
            case kAddrKEY1: return static_cast<std::uint8_t>(
                0x7Eu | (double_speed_ ? 0x80u : 0u) | (io_[0x4D] & 1u));
            case kAddrVBK:  return static_cast<std::uint8_t>(0xFEu | (io_[0x4F] & 1u));
            case kAddrBGPD: return bg_palette_[io_[0x68] & 0x3Fu];
            case kAddrOBPD: return obj_palette_[io_[0x6A] & 0x3Fu];
            // The original cartridge disables IR at boot. With no optical
            // receiver attached the input is high; unused bits read as ones.
            case kAddrRP:   return static_cast<std::uint8_t>(0x3Eu | (io_[0x56] & 0xC1u));
            case kAddrSVBK: return static_cast<std::uint8_t>(0xF8u | (io_[0x70] & 0x07u));
            default:        return io_[address - 0xFF00u];
        }
    }
    if (address < 0xFFFF) {
        return hram_[address - 0xFF80u];
    }
    return ie_;
}

void Memory::do_oam_dma(std::uint8_t page) {
    const std::uint16_t source = static_cast<std::uint16_t>(page) << 8;
    for (std::uint16_t i = 0; i < 0xA0; ++i) {
        oam_[i] = read8(static_cast<std::uint16_t>(source + i));
    }
}

void Memory::transfer_vram_dma_block() {
    if (vram_dma_blocks_ == 0) return;
    const auto bank = static_cast<std::uint8_t>(io_[0x4F] & 1u);
    for (unsigned i = 0; i < 16; ++i) {
        vram_[bank][(vram_dma_destination_ - 0x8000u + i) & 0x1FFFu] =
            read8(static_cast<std::uint16_t>(vram_dma_source_ + i));
    }
    vram_dma_source_ = static_cast<std::uint16_t>(vram_dma_source_ + 16u);
    vram_dma_destination_ = static_cast<std::uint16_t>(
        0x8000u | ((vram_dma_destination_ + 16u) & 0x1FF0u));
    io_[0x51] = static_cast<std::uint8_t>(vram_dma_source_ >> 8);
    io_[0x52] = static_cast<std::uint8_t>(vram_dma_source_ & 0xF0u);
    io_[0x53] = static_cast<std::uint8_t>((vram_dma_destination_ >> 8) & 0x1Fu);
    io_[0x54] = static_cast<std::uint8_t>(vram_dma_destination_ & 0xF0u);
    cpu_stall_mcycles_ += double_speed_ ? 16u : 8u;
    if (--vram_dma_blocks_ == 0) {
        vram_dma_active_ = false;
        io_[0x55] = 0xFF;
    } else {
        io_[0x55] = static_cast<std::uint8_t>(vram_dma_blocks_ - 1u);
    }
}

void Memory::start_vram_dma(std::uint8_t value) {
    if (vram_dma_active_) {
        if ((value & 0x80u) == 0) {
            vram_dma_active_ = false;
            io_[0x55] = static_cast<std::uint8_t>(0x80u | (vram_dma_blocks_ - 1u));
        }
        return;
    }
    vram_dma_source_ = static_cast<std::uint16_t>((io_[0x51] << 8) | (io_[0x52] & 0xF0u));
    vram_dma_destination_ = static_cast<std::uint16_t>(
        0x8000u | ((io_[0x53] & 0x1Fu) << 8) | (io_[0x54] & 0xF0u));
    vram_dma_blocks_ = (value & 0x7Fu) + 1u;
    vram_dma_active_ = (value & 0x80u) != 0;
    io_[0x55] = static_cast<std::uint8_t>(vram_dma_blocks_ - 1u);
    if (!vram_dma_active_ || (io_[0x40] & 0x80u) == 0) {
        while (vram_dma_blocks_ != 0) transfer_vram_dma_block();
    } else if (io_[0x44] < 144 && ppu_dot_ >= 252) {
        transfer_vram_dma_block();
    }
}

std::uint32_t Memory::take_cpu_stall_mcycles() {
    const std::uint32_t chunk = std::min(cpu_stall_mcycles_, double_speed_ ? 16u : 8u);
    cpu_stall_mcycles_ -= chunk;
    return chunk;
}

void Memory::invalidate_scanline_scroll() {
    pending_scx_.fill(0);
    pending_scy_.fill(0);
    completed_scx_.fill(0);
    completed_scy_.fill(0);
    scroll_lines_captured_ = 0;
    scanline_scroll_ready_ = false;
}

void Memory::write8(std::uint16_t address, std::uint8_t value) {
    if (address < 0x2000) {
        ram_enabled_ = (value & 0x0Fu) == 0x0Au;
        return;
    }
    if (address < 0x3000) {
        rom_bank_ = static_cast<std::uint16_t>((rom_bank_ & 0x0100u) | value);
        return;
    }
    if (address < 0x4000) {
        rom_bank_ = static_cast<std::uint16_t>(
            (rom_bank_ & 0x00FFu) | ((value & 1u) << 8));
        return;
    }
    if (address < 0x6000) {
        ram_bank_ = static_cast<std::uint8_t>(value & 0x0Fu);
        return;
    }
    if (address < 0x8000) {
        return;
    }
    if (address < 0xA000) {
        const std::uint8_t bank = static_cast<std::uint8_t>(io_[io_index(kAddrVBK)] & 1u);
        vram_[bank][address - 0x8000u] = value;
        return;
    }
    if (address < 0xC000) {
        if (ram_enabled_) {
            const std::size_t bank = static_cast<std::size_t>(ram_bank_ & 0x03u);
            const std::size_t offset = bank * 0x2000u + (address - 0xA000u);
            if (sram_[offset] != value) {
                sram_[offset] = value;
                sram_dirty_ = true;
            }
        }
        return;
    }
    if (address < 0xD000) {
        wram0_[address - 0xC000u] = value;
        return;
    }
    if (address < 0xE000) {
        wramx_[selected_wram_bank()][address - 0xD000u] = value;
        return;
    }
    if (address < 0xFE00) {
        write8(static_cast<std::uint16_t>(address - 0x2000u), value);
        return;
    }
    if (address < 0xFEA0) {
        oam_[address - 0xFE00u] = value;
        return;
    }
    if (address < 0xFF00) {
        return;
    }
    if (address < 0xFF80) {
        if (address >= 0xFF10 && address <= 0xFF3F) {
            apu_.write(address, value);
            return;
        }
        const std::uint8_t idx = static_cast<std::uint8_t>(address - 0xFF00u);
        switch (address) {
            case kAddrP1: {
                const std::uint8_t before = static_cast<std::uint8_t>(read_joypad() & 0x0Fu);
                joypad_select_ = static_cast<std::uint8_t>(value & 0x30u);
                const std::uint8_t after = static_cast<std::uint8_t>(read_joypad() & 0x0Fu);
                if ((before & static_cast<std::uint8_t>(~after)) != 0) {
                    request_interrupt(4);
                    stop_wake_ = true;
                }
                io_[idx] = static_cast<std::uint8_t>(0xC0u | joypad_select_ | 0x0Fu);
                return;
            }
            case kAddrSB:
                serial_.write_data(value);
                return;
            case kAddrSC:
                serial_.write_control(value);
                return;
            case kAddrDIV:
                write_div();
                return;
            case kAddrTIMA:
                io_[idx] = value;
                if (tima_reload_delay_ >= 0) tima_reload_delay_ = -1;
                return;
            case kAddrTMA:
                io_[idx] = value;
                return;
            case kAddrTAC:
                write_tac(value);
                return;
            case kAddrIF:
                io_[idx] = static_cast<std::uint8_t>(value & 0x1Fu);
                if ((value & 8u) == 0) serial_.clear_interrupt();
                return;
            case kAddrLCDC: {
                const bool was_on = (io_[idx] & 0x80u) != 0;
                const bool now_on = (value & 0x80u) != 0;
                io_[idx] = value;
                if (was_on && !now_on) {
                    ppu_dot_ = 0;
                    io_[0x44] = 0;
                    stat_irq_line_ = false;
                    invalidate_scanline_scroll();
                    if (vram_dma_active_) {
                        while (vram_dma_blocks_ != 0) transfer_vram_dma_block();
                    }
                }
                update_stat_interrupt_line();
                return;
            }
            case kAddrSTAT:
                io_[idx] = static_cast<std::uint8_t>((io_[idx] & 0x07u) | (value & 0x78u));
                update_stat_interrupt_line();
                return;
            case kAddrLY:
                io_[idx] = 0;
                ppu_dot_ = 0;
                invalidate_scanline_scroll();
                update_stat_interrupt_line();
                return;
            case kAddrLYC:
                io_[idx] = value;
                update_stat_interrupt_line();
                return;
            case kAddrDMA:
                io_[idx] = value;
                do_oam_dma(value);
                return;
            case kAddrKEY1:
                io_[idx] = static_cast<std::uint8_t>(value & 1u);
                return;
            case 0xFF51:
            case 0xFF52:
            case 0xFF53:
            case 0xFF54:
                if (vram_dma_active_) return;
                io_[idx] = static_cast<std::uint8_t>(value &
                    ((address == 0xFF52 || address == 0xFF54) ? 0xF0u :
                     address == 0xFF53 ? 0x1Fu : 0xFFu));
                return;
            case kAddrHDMA5:
                start_vram_dma(value);
                return;
            case kAddrRP:
                io_[idx] = static_cast<std::uint8_t>(value & 0xC1u);
                return;
            case kAddrVBK:
                io_[idx] = static_cast<std::uint8_t>(value & 1u);
                return;
            case kAddrBGPI:
                io_[idx] = static_cast<std::uint8_t>(value & 0xBFu);
                return;
            case kAddrBGPD: {
                const std::uint8_t pidx = static_cast<std::uint8_t>(io_[0x68] & 0x3Fu);
                bg_palette_[pidx] = value;
                if (io_[0x68] & 0x80u) {
                    io_[0x68] = static_cast<std::uint8_t>(
                        0x80u | ((pidx + 1u) & 0x3Fu));
                }
                return;
            }
            case kAddrOBPI:
                io_[idx] = static_cast<std::uint8_t>(value & 0xBFu);
                return;
            case kAddrOBPD: {
                const std::uint8_t pidx = static_cast<std::uint8_t>(io_[0x6A] & 0x3Fu);
                obj_palette_[pidx] = value;
                if (io_[0x6A] & 0x80u) {
                    io_[0x6A] = static_cast<std::uint8_t>(
                        0x80u | ((pidx + 1u) & 0x3Fu));
                }
                return;
            }
            case kAddrSVBK:
                io_[idx] = static_cast<std::uint8_t>(value & 0x07u);
                return;
            default:
                io_[idx] = value;
                return;
        }
    }
    if (address < 0xFFFF) {
        hram_[address - 0xFF80u] = value;
        return;
    }
    ie_ = value;
}

void Memory::set_joypad_state(std::uint8_t pressed_mask) {
    const std::uint8_t before = static_cast<std::uint8_t>(read_joypad() & 0x0Fu);
    joypad_pressed_ = pressed_mask;
    const std::uint8_t after = static_cast<std::uint8_t>(read_joypad() & 0x0Fu);
    if ((before & static_cast<std::uint8_t>(~after)) != 0) {
        request_interrupt(4);
        stop_wake_ = true;
    }
}

bool Memory::perform_speed_switch() {
    if ((io_[0x4D] & 1u) == 0) return false;
    double_speed_ = !double_speed_;
    io_[0x4D] = 0;
    base_clock_phase_ = false;
    write_div();
    return true;
}

void Memory::begin_stop() {
    stop_wake_ = false;
    write_div();
}

bool Memory::consume_stop_wake() {
    const bool wake = stop_wake_;
    stop_wake_ = false;
    return wake;
}

std::uint8_t Memory::pending_interrupts() const {
    return static_cast<std::uint8_t>(ie_ & read8(kAddrIF) & 0x1Fu);
}

void Memory::request_interrupt(std::uint8_t bit) {
    if (bit < 5) io_[0x0F] = static_cast<std::uint8_t>(io_[0x0F] | (1u << bit));
}

void Memory::clear_interrupt(std::uint8_t bit) {
    if (bit < 5) io_[0x0F] = static_cast<std::uint8_t>(io_[0x0F] & ~(1u << bit));
    if (bit == 3) serial_.clear_interrupt();
}

bool Memory::timer_input() const {
    const std::uint8_t tac = io_[0x07];
    if ((tac & 0x04u) == 0) return false;

    unsigned bit = 9;
    switch (tac & 0x03u) {
        case 0: bit = 9; break;
        case 1: bit = 3; break;
        case 2: bit = 5; break;
        case 3: bit = 7; break;
    }
    return ((div_counter_ >> bit) & 1u) != 0;
}

void Memory::timer_falling_edge() {
    if (tima_reload_delay_ >= 0) return;

    if (io_[0x05] == 0xFF) {
        io_[0x05] = 0x00;
        tima_reload_delay_ = 4;
    } else {
        ++io_[0x05];
    }
}

void Memory::write_div() {
    const bool old_input = timer_input();
    div_counter_ = 0;
    const bool new_input = timer_input();
    if (old_input && !new_input) timer_falling_edge();
}

void Memory::write_tac(std::uint8_t value) {
    const bool old_input = timer_input();
    io_[0x07] = static_cast<std::uint8_t>(0xF8u | (value & 0x07u));
    const bool new_input = timer_input();
    if (old_input && !new_input) timer_falling_edge();
}

void Memory::update_stat_interrupt_line() {
    if ((io_[0x40] & 0x80u) == 0) {
        stat_irq_line_ = false;
        return;
    }

    const std::uint8_t stat = read_stat();
    const std::uint8_t mode = static_cast<std::uint8_t>(stat & 0x03u);
    const bool coincidence = (stat & 0x04u) != 0;

    const bool line =
        (coincidence && (stat & 0x40u)) ||
        (mode == 2 && (stat & 0x20u)) ||
        (mode == 1 && (stat & 0x10u)) ||
        (mode == 0 && (stat & 0x08u));

    if (line && !stat_irq_line_) request_interrupt(1);
    stat_irq_line_ = line;
}

void Memory::tick_ppu_one_tcycle() {
    if ((io_[0x40] & 0x80u) == 0) {
        ppu_dot_ = 0;
        io_[0x44] = 0;
        return;
    }

    ++ppu_dot_;
    if (ppu_dot_ == 80 && io_[0x44] < 144) {
        const unsigned line = io_[0x44];
        pending_scx_[line] = io_[0x43];
        pending_scy_[line] = io_[0x42];
        if (line == scroll_lines_captured_) ++scroll_lines_captured_;
    }
    if (ppu_dot_ == 252 && io_[0x44] < 144 && vram_dma_active_) {
        transfer_vram_dma_block();
    }
    if (ppu_dot_ >= 456) {
        ppu_dot_ = 0;
        std::uint8_t next = static_cast<std::uint8_t>(io_[0x44] + 1);
        if (next == 144) {
            if (scroll_lines_captured_ == 144) {
                completed_scx_ = pending_scx_;
                completed_scy_ = pending_scy_;
                scanline_scroll_ready_ = true;
            }
            request_interrupt(0);
            ++frame_counter_;
        } else if (next > 153) {
            next = 0;
            scroll_lines_captured_ = 0;
        }
        io_[0x44] = next;
    }

    update_stat_interrupt_line();
}

void Memory::tick_one_tcycle() {
    const bool reload_was_pending = tima_reload_delay_ >= 0;
    const bool old_timer = timer_input();
    ++div_counter_;
    const bool new_timer = timer_input();
    if (old_timer && !new_timer) timer_falling_edge();

    if (reload_was_pending) {
        --tima_reload_delay_;
        if (tima_reload_delay_ == 0) {
            io_[0x05] = io_[0x06];
            request_interrupt(2);
            tima_reload_delay_ = -1;
        }
    }

    serial_.tick_tcycle();
    base_clock_phase_ = !base_clock_phase_;
    if (!double_speed_ || !base_clock_phase_) {
        tick_ppu_one_tcycle();
        apu_.tick_tcycle();
        ++total_base_tcycles_;
    }
    ++total_tcycles_;
}

void Memory::tick_tcycles(std::uint32_t tcycles) {
    for (std::uint32_t i = 0; i < tcycles; ++i) tick_one_tcycle();
}

void Memory::tick_mcycles(std::uint32_t mcycles) {
    tick_tcycles(mcycles * 4u);
}

std::uint8_t Memory::io(std::uint8_t offset) const {
    return read8(static_cast<std::uint16_t>(0xFF00u + offset));
}

void Memory::set_io_direct(std::uint8_t offset, std::uint8_t value) {
    if (offset == 0x01) { serial_.write_data(value); return; }
    if (offset == 0x02) { serial_.write_control(value); return; }
    if (offset == 0x0F && (value & 8u) == 0) serial_.clear_interrupt();
    io_[offset & 0x7Fu] = value;
}

bool load_sram_file(Memory& memory, const std::filesystem::path& path) {
    std::error_code ec;
    if (!std::filesystem::exists(path, ec)) return !ec;

    std::ifstream input(path, std::ios::binary);
    if (!input) return false;

    std::array<std::uint8_t, Memory::SramSize> data{};
    input.read(reinterpret_cast<char*>(data.data()),
               static_cast<std::streamsize>(data.size()));
    if (input.gcount() != static_cast<std::streamsize>(data.size())) return false;

    char extra = 0;
    if (input.read(&extra, 1)) return false;
    if (input.bad() || !input.eof()) return false;

    memory.load_sram(data.data(), data.size());
    return true;
}

bool save_sram_file(Memory& memory, const std::filesystem::path& path) {
    const auto& data = memory.sram();
    if (!save_io::write_sram_atomic(path, data.data(), data.size())) return false;

    // Keep pending cartridge writes dirty until durable replacement succeeds.
    memory.clear_sram_dirty();
    return true;
}

} // namespace dwm2t
