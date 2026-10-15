#include "recomp/runtime.hpp"

#include "recomp/lr35902_exec.hpp"
#include "recomp/romx.hpp"

#include <cstdint>

namespace dwm2t {

namespace {

constexpr std::uint16_t kInterruptVectors[5] = {
    0x0040, // VBlank
    0x0048, // LCD STAT
    0x0050, // Timer
    0x0058, // Serial
    0x0060, // Joypad
};

unsigned first_pending_interrupt(std::uint8_t pending) {
    for (unsigned bit = 0; bit < 5; ++bit) {
        if (pending & (1u << bit)) return bit;
    }
    return 5;
}

} // namespace

Runtime::Runtime() {
    reset_cgb_post_boot();
}

void Runtime::reset_cgb_post_boot() {
    cpu_ = Cpu{};
    memory_.clear();
    load_full_rom_image(memory_);

    // Standard CGB post-boot register state. The cartridge entry point at
    // $0100 immediately jumps into DWM2's own initialization at $0150.
    cpu_.a = 0x11;
    cpu_.f = 0x80;
    cpu_.b = 0x00;
    cpu_.c = 0x00;
    cpu_.d = 0xFF;
    cpu_.e = 0x56;
    cpu_.h = 0x00;
    cpu_.l = 0x0D;
    cpu_.sp = 0xFFFE;
    cpu_.pc = 0x0100;
    cpu_.ime = false;

    // CGB hardware values that are observable before DWM2 overwrites them.
    memory_.set_io_direct(0x00, 0xCF); // P1
    memory_.set_io_direct(0x05, 0x00); // TIMA
    memory_.set_io_direct(0x06, 0x00); // TMA
    memory_.set_io_direct(0x07, 0xF8); // TAC
    memory_.set_io_direct(0x0F, 0x01); // IF
    memory_.set_io_direct(0x40, 0x91); // LCDC
    memory_.set_io_direct(0x41, 0x80); // STAT writable bits clear
    memory_.set_io_direct(0x42, 0x00); // SCY
    memory_.set_io_direct(0x43, 0x00); // SCX
    memory_.set_io_direct(0x44, 0x00); // LY
    memory_.set_io_direct(0x45, 0x00); // LYC
    memory_.set_io_direct(0x47, 0xFC); // BGP
    memory_.set_io_direct(0x48, 0xFF); // OBP0
    memory_.set_io_direct(0x49, 0xFF); // OBP1
    memory_.set_io_direct(0x4F, 0x00); // VBK
    memory_.set_io_direct(0x70, 0x01); // SVBK
}

bool Runtime::service_interrupt_if_needed() {
    const std::uint8_t pending = memory_.pending_interrupts();

    if (cpu_.halted && pending != 0) {
        cpu_.halted = false;
    }
    if (cpu_.stopped && (pending & (1u << 4)) != 0) {
        cpu_.stopped = false;
    }

    if (!cpu_.ime || pending == 0) return false;

    const unsigned bit = first_pending_interrupt(pending);
    if (bit >= 5) return false;

    cpu_.ime = false;
    cpu_.ime_delay = 0;
    cpu_.halted = false;
    memory_.clear_interrupt(static_cast<std::uint8_t>(bit));
    lr35902::push16(cpu_, memory_, cpu_.pc);
    cpu_.pc = kInterruptVectors[bit];
    cpu_.last_mcycles = 5;
    memory_.tick_mcycles(5);
    return true;
}

StepResult Runtime::execute_current_instruction() {
    if (cpu_.pc < 0x4000) {
        const StepResult result = execute_bank0_instruction(cpu_, memory_);
        return result == StepResult::LeftBank0 ? StepResult::Continue : result;
    }

    if (cpu_.pc < 0x8000) {
        const std::uint16_t bank = memory_.current_rom_bank();
        switch (bank) {
            case 2:
                return execute_romx_bank_2(cpu_, memory_);
            default:
                cpu_.missing_bank = bank;
                return StepResult::MissingBank;
        }
    }

    cpu_.trap(cpu_.pc, memory_.read8(cpu_.pc));
    return StepResult::Trapped;
}

StepResult Runtime::step() {
    if (service_interrupt_if_needed()) {
        return StepResult::Continue;
    }

    if (cpu_.halted) {
        cpu_.last_mcycles = 1;
        memory_.tick_mcycles(1);
        return StepResult::Continue;
    }

    if (cpu_.stopped) {
        cpu_.last_mcycles = 1;
        memory_.tick_mcycles(1);
        return StepResult::Stopped;
    }

    return execute_current_instruction();
}

StepResult Runtime::run(std::size_t max_steps) {
    for (std::size_t i = 0; i < max_steps; ++i) {
        const StepResult result = step();
        if (result != StepResult::Continue) return result;
    }
    return StepResult::StepLimit;
}

} // namespace dwm2t
