// Hardware/unit fixtures only: no original ROM, game save or P1 route is loaded.
// ROM dispatch is linked to explicit trapping stubs, never an interpreter.
#include "recomp/bank0.hpp"
#include "recomp/hram_exec.hpp"
#include "recomp/lr35902_exec.hpp"
#include "recomp/memory.hpp"
#include "recomp/romx.hpp"
#include "recomp/runtime.hpp"

#include <array>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

namespace dwm2t::test_stubs {
extern unsigned dispatch_calls;
extern unsigned image_load_calls;
}

namespace {
using dwm2t::Cpu;
using dwm2t::Memory;
using dwm2t::Runtime;
using dwm2t::StepResult;
unsigned checks = 0;

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
    ++checks;
}

bool serial_irq(const Memory& memory) { return (memory.read8(0xFF0F) & 8u) != 0; }
bool serial_busy(const Memory& memory) { return (memory.read8(0xFF02) & 0x80u) != 0; }

void start_serial(Memory& memory, std::uint8_t data, std::uint8_t control) {
    memory.write8(0xFF0F, 0);
    memory.write8(0xFF01, data);
    memory.write8(0xFF02, control);
}

void install_hram_helper(Memory& memory) {
    constexpr std::array<std::uint8_t, 10> code{0x3E, 0xC0, 0xE0, 0x46,
                                               0x3E, 0x28, 0x3D, 0x20, 0xFD, 0xC9};
    for (unsigned i = 0; i < code.size(); ++i)
        memory.write8(static_cast<std::uint16_t>(0xFF80u+i), code[i]);
}

void dma_registers(Memory& memory, std::uint16_t source, std::uint16_t destination) {
    memory.write8(0xFF51, static_cast<std::uint8_t>(source >> 8));
    memory.write8(0xFF52, static_cast<std::uint8_t>(source));
    memory.write8(0xFF53, static_cast<std::uint8_t>(destination >> 8));
    memory.write8(0xFF54, static_cast<std::uint8_t>(destination));
}

void mapper_physical_rom_and_wram() {
    auto memory = std::make_unique<Memory>();
    memory->set_rom_byte(0x0123, 0x10);
    memory->set_rom_byte(0x4000+0x0123, 0x11);
    memory->set_rom_byte(255u*0x4000u+0x0123, 0xEF);
    require(memory->read8(0x0123) == 0x10 && memory->read8(0x4123) == 0x11,
            "fixed and initial switchable ROM windows");
    memory->write8(0x2000, 0xFF);
    memory->write8(0x3000, 1);
    require(memory->current_rom_bank() == 255 && memory->read8(0x4123) == 0xEF,
            "ninth mapper bit mirrors the physical four-MiB cartridge");
    memory->write8(0x2000, 0);
    require(memory->current_rom_bank() == 0 && memory->read8(0x4123) == 0x10,
            "physical ROM bank zero is valid in the switchable window");
    memory->write8(0x3000, 0);
    memory->write8(0x2000, 1);
    require(memory->read8(0x4123) == 0x11 && memory->read8(0x0123) == 0x10,
            "mapper changes leave the fixed window unchanged");
    memory->write8(0xC123, 0x5A);
    require(memory->read8(0xE123) == 0x5A, "fixed WRAM echo");
    memory->write8(0xFF70, 0);
    memory->write8(0xD123, 0x31);
    memory->write8(0xFF70, 2);
    memory->write8(0xD123, 0x72);
    require(memory->read8(0xF123) == 0x72, "selected WRAM bank echo");
    memory->write8(0xFF70, 1);
    require(memory->read8(0xD123) == 0x31, "SVBK zero aliases bank one, not bank two");
}

void speed_switch_and_clock_domains() {
    auto memory = std::make_unique<Memory>();
    require(!memory->double_speed() && !memory->perform_speed_switch(),
            "speed switch needs a prepared KEY1 bit");
    memory->tick_tcycles(256);
    require(memory->read8(0xFF04) == 1 && memory->total_base_tcycles() == 256,
            "normal CPU and base clocks advance with LCD off");
    memory->write8(0xFF4D, 1);
    require((memory->read8(0xFF4D) & 0x81u) == 1 && memory->perform_speed_switch(),
            "KEY1 preparation performs a speed switch");
    require(memory->double_speed() && (memory->read8(0xFF4D) & 0x81u) == 0x80
            && memory->read8(0xFF04) == 0, "switch toggles speed, clears preparation and resets DIV");
    const auto cpu_before = memory->total_tcycles();
    const auto base_before = memory->total_base_tcycles();
    const auto audio_before = memory->apu().sample_frames();
    memory->tick_tcycles(8192);
    require(memory->total_tcycles()-cpu_before == 8192
            && memory->total_base_tcycles()-base_before == 4096,
            "double speed runs two CPU ticks per base tick even with LCD off");
    require(memory->apu().sample_frames()-audio_before == 32,
            "APU sample clock stays at base speed during double-speed CPU operation");
    memory->write8(0xFF4D, 1);
    require(memory->perform_speed_switch() && !memory->double_speed(),
            "a second prepared STOP switches back to normal speed");
    const auto second_base = memory->total_base_tcycles();
    memory->tick_mcycles(4);
    require(memory->total_base_tcycles()-second_base == 16,
            "normal M-cycles contain four base clocks after switching back");
}

void timer_overflow_reload_and_write_edges() {
    auto memory = std::make_unique<Memory>();
    memory->write8(0xFF05, 0xFF);
    memory->write8(0xFF06, 0x42);
    memory->write8(0xFF07, 5); // Enabled divider bit3: falling edges every16 CPU T-cycles.
    memory->tick_tcycles(15);
    require(memory->read8(0xFF05) == 0xFF && !(memory->read8(0xFF0F) & 4u),
            "TIMA does not overflow before the selected divider falling edge");
    memory->tick_tcycles(1);
    require(memory->read8(0xFF05) == 0 && !(memory->read8(0xFF0F) & 4u),
            "TIMA overflow exposes zero before its delayed reload and IRQ");
    memory->tick_tcycles(3);
    require(memory->read8(0xFF05) == 0 && !(memory->read8(0xFF0F) & 4u),
            "reload waits through the first three subsequent T-cycles");
    memory->write8(0xFF06, 0x73);
    memory->tick_tcycles(1);
    require(memory->read8(0xFF05) == 0x73 && (memory->read8(0xFF0F) & 4u),
            "the fourth subsequent T-cycle reloads current TMA and requests timer IRQ");

    auto canceled = std::make_unique<Memory>();
    canceled->write8(0xFF05, 0xFF);
    canceled->write8(0xFF06, 0x42);
    canceled->write8(0xFF07, 5);
    canceled->tick_tcycles(16);
    canceled->write8(0xFF05, 0x55);
    canceled->tick_tcycles(4);
    require(canceled->read8(0xFF05) == 0x55 && !(canceled->read8(0xFF0F) & 4u),
            "a TIMA write during the pending reload cancels both reload and IRQ");

    auto edge = std::make_unique<Memory>();
    edge->write8(0xFF05, 0x10);
    edge->write8(0xFF07, 5);
    edge->tick_tcycles(8);
    const auto before = edge->total_tcycles();
    edge->write8(0xFF04, 0);
    require(edge->read8(0xFF05) == 0x11 && edge->total_tcycles() == before,
            "DIV reset creates a timer falling edge without inventing elapsed CPU clocks");
    edge->tick_tcycles(8);
    edge->write8(0xFF07, 0);
    require(edge->read8(0xFF05) == 0x12,
            "disabling TAC while its selected divider bit is high produces the falling-edge increment");
}

void general_vram_dma() {
    auto memory = std::make_unique<Memory>();
    for (unsigned i = 0; i < 32; ++i)
        memory->write8(static_cast<std::uint16_t>(0xC110u+i), static_cast<std::uint8_t>(0x60u+i));
    memory->write8(0xFF4F, 1);
    dma_registers(*memory, 0xC113, 0x8007); // Hardware ignores the low four bits.
    memory->write8(0xFF55, 1);
    for (unsigned i = 0; i < 32; ++i) {
        require(memory->vram_bank_data(1)[i] == 0x60u+i, "GDMA copies all requested aligned bytes");
        require(memory->vram_bank_data(0)[i] == 0, "GDMA respects the selected VRAM bank");
    }
    require(memory->read8(0xFF55) == 0xFF, "completed GDMA reports no remaining blocks");
    require(memory->take_cpu_stall_mcycles() == 16 && memory->take_cpu_stall_mcycles() == 0,
            "two GDMA blocks queue sixteen normal M-cycles exactly once");
    memory->write8(0xFF4D, 1);
    require(memory->perform_speed_switch(), "prepare double-speed GDMA fixture");
    dma_registers(*memory, 0xC110, 0x8040);
    memory->write8(0xFF55, 0);
    require(memory->take_cpu_stall_mcycles() == 16,
            "one double-speed GDMA block queues sixteen CPU M-cycles");
    for (unsigned i = 0; i < 16; ++i)
        require(memory->vram_bank_data(1)[0x40+i] == 0x60u+i,
                "double-speed GDMA preserves copied data");
}

void hblank_dma_and_abort() {
    auto memory = std::make_unique<Memory>();
    for (unsigned i = 0; i < 32; ++i)
        memory->write8(static_cast<std::uint16_t>(0xC200u+i), static_cast<std::uint8_t>(i+1));
    memory->write8(0xFF40, 0x91);
    dma_registers(*memory, 0xC200, 0x8000);
    memory->write8(0xFF55, 0x81);
    memory->tick_tcycles(251);
    require(memory->vram_bank_data(0)[0] == 0 && memory->take_cpu_stall_mcycles() == 0,
            "HBlank DMA waits while the first visible scanline is transferring");
    memory->tick_tcycles(1);
    require(memory->vram_bank_data(0)[0] == 1 && memory->vram_bank_data(0)[15] == 16
            && memory->vram_bank_data(0)[16] == 0,
            "one HBlank copies one sixteen-byte block");
    require(memory->take_cpu_stall_mcycles() == 8 && memory->read8(0xFF55) == 0,
            "HBlank DMA retains one pending block and queues eight normal M-cycles");
    memory->write8(0xFF55, 0);
    require(memory->read8(0xFF55) == 0x80, "clearing HDMA5 bit seven cancels pending HBlank blocks");
    memory->tick_tcycles(456);
    require(memory->vram_bank_data(0)[16] == 0 && memory->take_cpu_stall_mcycles() == 0,
            "canceled HBlank DMA leaves subsequent scanlines and destination bytes unchanged");

    auto complete = std::make_unique<Memory>();
    for (unsigned i = 0; i < 32; ++i)
        complete->write8(static_cast<std::uint16_t>(0xC200u+i), static_cast<std::uint8_t>(i+1));
    complete->write8(0xFF40, 0x91);
    dma_registers(*complete, 0xC200, 0x8000);
    complete->write8(0xFF55, 0x81);
    complete->tick_tcycles(252);
    require(complete->take_cpu_stall_mcycles() == 8, "first full HDMA block timing");
    complete->tick_tcycles(456);
    require(complete->read8(0xFF55) == 0xFF && complete->take_cpu_stall_mcycles() == 8,
            "second HBlank completes the two-block transfer");
    for (unsigned i = 0; i < 32; ++i)
        require(complete->vram_bank_data(0)[i] == i+1, "completed HDMA preserves every source byte");
}

void interrupt_priority_and_stack() {
    constexpr std::array<std::uint16_t, 5> vectors{0x40, 0x48, 0x50, 0x58, 0x60};
    for (unsigned bit = 0; bit < vectors.size(); ++bit) {
        auto runtime = std::make_unique<Runtime>();
        auto& cpu = runtime->cpu();
        auto& memory = runtime->memory();
        memory.write8(0xFF40, 0);
        memory.write8(0xFFFF, 0x1F);
        memory.write8(0xFF0F, static_cast<std::uint8_t>(0x1Fu & ~((1u << bit)-1u)));
        cpu.pc = 0x2345;
        cpu.sp = 0xD000;
        cpu.ime = true;
        cpu.ime_delay = 1;
        const auto before = memory.total_tcycles();
        const auto calls = dwm2t::test_stubs::dispatch_calls;
        require(runtime->step() == StepResult::Continue && cpu.pc == vectors[bit],
                "interrupt arbitration chooses the lowest pending enabled source");
        require(cpu.sp == 0xCFFE && memory.read8(0xCFFE) == 0x45 && memory.read8(0xCFFF) == 0x23,
                "interrupt entry pushes the actual return PC little endian");
        require(!cpu.ime && cpu.ime_delay == 0 && !cpu.halt_bug
                && (memory.read8(0xFF0F) & (1u << bit)) == 0,
                "interrupt entry clears IME delay, HALT bug and only its acknowledged IF bit");
        const auto remaining = static_cast<std::uint8_t>(0x1Fu & ~((1u << (bit+1u))-1u));
        require((memory.read8(0xFF0F) & 0x1Fu) == remaining,
                "higher-priority-number pending interrupts remain requested");
        require(cpu.last_mcycles == 5 && memory.total_tcycles()-before == 20
                && dwm2t::test_stubs::dispatch_calls == calls,
                "interrupt entry costs five M-cycles without executing a ROM opcode");
    }
}

void ei_di_reti_and_halt() {
    auto memory = std::make_unique<Memory>();
    Cpu cpu;
    dwm2t::lr35902::exec_base<0xFB>(cpu, *memory, 0, 0, 0x0100);
    cpu.finish_instruction();
    require(!cpu.ime && cpu.ime_delay == 1, "EI waits until the following instruction finishes");
    dwm2t::lr35902::exec_base<0xFB>(cpu, *memory, 0, 0, 0x0101);
    cpu.finish_instruction();
    require(cpu.ime && cpu.ime_delay == 0, "a second EI does not postpone the first EI");
    cpu = Cpu{};
    dwm2t::lr35902::exec_base<0xFB>(cpu, *memory, 0, 0, 0x0100);
    cpu.finish_instruction();
    dwm2t::lr35902::exec_base<0xF3>(cpu, *memory, 0, 0, 0x0101);
    cpu.finish_instruction();
    require(!cpu.ime && cpu.ime_delay == 0, "DI cancels a pending EI");
    cpu.sp = 0xC100;
    memory->write8(0xC100, 0x34);
    memory->write8(0xC101, 0x12);
    dwm2t::lr35902::exec_base<0xD9>(cpu, *memory, 0, 0, 0x0102);
    require(cpu.ime && cpu.ime_delay == 0 && cpu.pc == 0x1234 && cpu.sp == 0xC102,
            "RETI pops the return address and enables IME immediately");
    cpu = Cpu{};
    memory->write8(0xFFFF, 1);
    memory->write8(0xFF0F, 1);
    dwm2t::lr35902::exec_base<0x76>(cpu, *memory, 0, 0, 0x0100);
    require(cpu.halt_bug && !cpu.halted, "HALT with IME clear and enabled pending IRQ triggers the fetch bug");
    cpu = Cpu{};
    memory->write8(0xFFFF, 0);
    dwm2t::lr35902::exec_base<0x76>(cpu, *memory, 0, 0, 0x0100);
    require(cpu.halted && !cpu.halt_bug, "masked interrupt requests do not trigger the HALT bug");
}

void ei_halt_interrupt_return() {
    auto runtime = std::make_unique<Runtime>();
    auto& cpu = runtime->cpu();
    auto& memory = runtime->memory();
    memory.write8(0xFFFF, 1);
    memory.write8(0xFF0F, 1);
    cpu.pc = 0x1235; // EI at1234 has already advanced its fetch PC.
    cpu.sp = 0xD000;
    dwm2t::lr35902::exec_base<0xFB>(cpu, memory, 0, 0, 0x1234);
    cpu.finish_instruction();
    cpu.pc = 0x1236; // HALT at1235, before its fetch bug is consumed.
    dwm2t::lr35902::exec_base<0x76>(cpu, memory, 0, 0, 0x1235);
    cpu.finish_instruction();
    require(cpu.ime && cpu.halt_bug && !cpu.halted, "EI then HALT exposes the pending fetch suppression");
    require(runtime->step() == StepResult::Continue && cpu.pc == 0x40 && !cpu.halt_bug,
            "pending IRQ is accepted before a bugged next opcode fetch");
    require(memory.read8(0xCFFE) == 0x35 && memory.read8(0xCFFF) == 0x12,
            "EI HALT interrupt returns to HALT itself, not the following byte");
}

void halt_idle_and_wake() {
    auto runtime = std::make_unique<Runtime>();
    auto& cpu = runtime->cpu();
    auto& memory = runtime->memory();
    install_hram_helper(memory);
    memory.write8(0xFFFF, 0);
    memory.write8(0xFF0F, 1);
    cpu.pc = 0xFF86;
    cpu.a = 2;
    cpu.halted = true;
    const auto before = memory.total_tcycles();
    require(runtime->step() == StepResult::Continue && cpu.halted && cpu.pc == 0xFF86,
            "HALT remains asleep while its IRQ is masked");
    require(cpu.last_mcycles == 1 && memory.total_tcycles()-before == 4,
            "HALT idle keeps hardware clocks running");
    memory.write8(0xFFFF, 1);
    require(runtime->step() == StepResult::Continue && !cpu.halted
            && cpu.pc == 0xFF87 && cpu.a == 1 && (memory.read8(0xFF0F) & 1),
            "enabled IRQ wakes HALT with IME clear without acknowledging the interrupt");
}

void stop_wake_and_speed_opcode() {
    auto runtime = std::make_unique<Runtime>();
    auto& cpu = runtime->cpu();
    auto& memory = runtime->memory();
    install_hram_helper(memory);
    memory.write8(0xFFFF, 0);
    memory.write8(0xFF00, 0x20); // Direction keys selected; A is not selected.
    memory.set_joypad_state(dwm2t::JoyRight);
    memory.tick_tcycles(512);
    cpu.pc = 0xFF86;
    cpu.a = 2;
    dwm2t::lr35902::exec_base<0x10>(cpu, memory, 0, 0, 0x0100);
    require(cpu.stopped && memory.read8(0xFF04) == 0, "ordinary STOP gates CPU execution and resets DIV");
    const auto before = memory.total_tcycles();
    const auto base_before = memory.total_base_tcycles();
    memory.write8(0xFF0F, 8);
    memory.write8(0xFFFF, 8);
    require(runtime->step() == StepResult::Stopped && cpu.last_mcycles == 0
            && memory.total_tcycles() == before && memory.total_base_tcycles() == base_before,
            "STOP consumes neither CPU nor base clocks and ignores unrelated pending IRQ");
    memory.set_joypad_state(dwm2t::JoyRight);
    require(runtime->step() == StepResult::Stopped, "a held pre-STOP key is not a fresh wake edge");
    memory.set_joypad_state(0);
    memory.set_joypad_state(dwm2t::JoyA);
    require(runtime->step() == StepResult::Stopped, "an unselected P1 key does not wake STOP");
    memory.write8(0xFFFF, 0);
    memory.set_joypad_state(static_cast<std::uint8_t>(dwm2t::JoyA | dwm2t::JoyRight));
    require(runtime->step() == StepResult::Continue && !cpu.stopped
            && cpu.pc == 0xFF87 && cpu.a == 1,
            "a fresh selected P1 edge wakes STOP independently of IE and IME");

    Cpu speed_cpu;
    memory.write8(0xFF4D, 1);
    dwm2t::lr35902::exec_base<0x10>(speed_cpu, memory, 0, 0, 0x0100);
    require(memory.double_speed() && !speed_cpu.stopped,
            "prepared KEY1 STOP switches speed and continues instead of entering STOP");
}

void runtime_dma_stall_and_interrupt() {
    auto runtime = std::make_unique<Runtime>();
    auto& cpu = runtime->cpu();
    auto& memory = runtime->memory();
    memory.write8(0xFF40, 0);
    for (unsigned i = 0; i < 2048; ++i)
        memory.write8(static_cast<std::uint16_t>(0xC100u+i), static_cast<std::uint8_t>(i));
    dma_registers(memory, 0xC100, 0x8000);
    memory.write8(0xFF55, 0x7F); // The maximum128-block GDMA queues1024 M-cycles.
    memory.write8(0xFFFF, 8);
    memory.write8(0xFF0F, 8);
    cpu.pc = 0x2345;
    cpu.sp = 0xD000;
    cpu.ime = true;
    cpu.ime_delay = 1;
    const auto before = memory.total_tcycles();
    require(runtime->step() == StepResult::Continue && cpu.last_mcycles == 1024,
            "maximum GDMA stall does not truncate to an eight-bit cycle count");
    require(cpu.pc == 0x2345 && cpu.sp == 0xD000 && cpu.ime && cpu.ime_delay == 1
            && memory.total_tcycles()-before == 4096 && serial_irq(memory),
            "GDMA stalls before interrupt arbitration without finishing an instruction");
    require(runtime->step() == StepResult::Continue && cpu.pc == 0x58 && !cpu.ime,
            "queued serial IRQ is accepted after the DMA stall ends");
    require(memory.read8(0xCFFE) == 0x45 && memory.read8(0xCFFF) == 0x23,
            "post-DMA interrupt preserves the unexecuted PC");

    auto stopped = std::make_unique<Runtime>();
    auto& stop_memory = stopped->memory();
    auto& stop_cpu = stopped->cpu();
    stop_memory.write8(0xFF00, 0x20);
    stop_memory.write8(0xFFFF, 0);
    stop_memory.begin_stop();
    stop_cpu.stopped = true;
    stop_cpu.pc = 0x2345;
    dma_registers(stop_memory, 0xC100, 0x8000);
    stop_memory.write8(0xFF55, 0);
    const auto stop_before = stop_memory.total_tcycles();
    require(stopped->step() == StepResult::Stopped && stop_memory.total_tcycles() == stop_before,
            "STOP does not consume or tick a queued GDMA stall");
    stop_memory.set_joypad_state(dwm2t::JoyRight);
    require(stopped->step() == StepResult::Continue && stop_cpu.pc == 0x2345
            && stop_cpu.last_mcycles == 8 && stop_memory.total_tcycles()-stop_before == 32,
            "after STOP wake the original pending GDMA stall is consumed before dispatch");
}

void hram_entries_and_halt_bug() {
    auto memory = std::make_unique<Memory>();
    install_hram_helper(*memory);
    Cpu cpu;
    cpu.pc = 0xFF80;
    require(dwm2t::execute_known_hram_dma(cpu, *memory) == StepResult::Continue
            && cpu.a == 0xC0 && cpu.pc == 0xFF82 && cpu.last_mcycles == 2,
            "known HRAM LD A immediate uses original bytes and cycles");
    cpu = Cpu{};
    cpu.pc = 0xFF80;
    cpu.halt_bug = true;
    require(dwm2t::execute_known_hram_dma(cpu, *memory) == StepResult::Continue
            && cpu.a == 0x3E && cpu.pc == 0xFF81 && !cpu.halt_bug,
            "HALT bug suppresses the HRAM opcode fetch increment for immediate LD");
    cpu = Cpu{};
    cpu.pc = 0xFF82;
    cpu.a = 0x5A;
    cpu.halt_bug = true;
    require(dwm2t::execute_known_hram_dma(cpu, *memory) == StepResult::Continue
            && memory->read8(0xFFE0) == 0x5A && cpu.pc == 0xFF83 && cpu.last_mcycles == 3,
            "bugged LDH uses E0 as its immediate instead of writing DMA register46");
    cpu = Cpu{};
    cpu.pc = 0xFF83;
    cpu.set_hl(0xC234);
    memory->write8(0xC234, 0xA6);
    require(dwm2t::execute_known_hram_dma(cpu, *memory) == StepResult::Continue
            && cpu.b == 0xA6 && cpu.pc == 0xFF84,
            "byte entry83 executes its own original LD B memory opcode");
    cpu = Cpu{};
    cpu.pc = 0xFF85;
    cpu.f = Cpu::FlagZ;
    require(dwm2t::execute_known_hram_dma(cpu, *memory) == StepResult::Continue
            && cpu.pc == 0xFFC4 && cpu.last_mcycles == 3,
            "byte entry85 executes original taken JR Z with signed immediate3D");
    cpu = Cpu{};
    cpu.pc = 0xFF88;
    require(dwm2t::execute_known_hram_dma(cpu, *memory) == StepResult::Trapped
            && cpu.trap_pc == 0xFF88 && cpu.trap_opcode == 0xFD,
            "illegal byte entry88 traps instead of being treated as padding");
    memory->write8(0xFF84, 0);
    cpu = Cpu{};
    cpu.pc = 0xFF80;
    const auto before = memory->total_tcycles();
    require(dwm2t::execute_known_hram_dma(cpu, *memory) == StepResult::Trapped
            && memory->total_tcycles() == before,
            "a changed HRAM signature is rejected without interpreting replacement RAM code");
}

void sticky_trap_and_zero_aot_identity() {
    require(dwm2t::bank0_translated_entry_count() == 0
            && dwm2t::translated_romx_bank_count() == 0 && !dwm2t::romx_bank_is_translated(1),
            "standalone target reports zero original-ROM AOT entries honestly");
    for (unsigned window = 0; window < 3; ++window) {
        auto runtime = std::make_unique<Runtime>();
        if (window == 1) runtime->cpu().pc = 0x4000;
        if (window == 2) {
            runtime->memory().write8(0x2000, 0);
            runtime->cpu().pc = 0x4000;
        }
        runtime->memory().write8(0xFF0F, 0);
        const auto calls = dwm2t::test_stubs::dispatch_calls;
        require(runtime->step() == StepResult::Trapped
                && dwm2t::test_stubs::dispatch_calls == calls+1,
                "fixed ROM, ROMX and bank-zero-alias dispatch all hit explicit traps");
    }
    auto runtime = std::make_unique<Runtime>();
    auto& cpu = runtime->cpu();
    auto& memory = runtime->memory();
    cpu.trap(0x1234, 0xD3);
    cpu.pc = 0x4567;
    cpu.sp = 0xC100;
    cpu.ime = true;
    cpu.last_mcycles = 77;
    memory.write8(0xFFFF, 0x1F);
    memory.write8(0xFF0F, 0x1F);
    const auto before = memory.total_tcycles();
    const auto calls = dwm2t::test_stubs::dispatch_calls;
    require(runtime->step() == StepResult::Trapped && cpu.pc == 0x4567 && cpu.sp == 0xC100
            && cpu.ime && cpu.last_mcycles == 77 && memory.total_tcycles() == before
            && dwm2t::test_stubs::dispatch_calls == calls,
            "a trapped Runtime cannot advance clocks, execute ROM or service pending IRQs");
}

void serial_unconnected_and_fast() {
    auto memory = std::make_unique<Memory>();
    start_serial(*memory, 0, 0x81);
    require((memory->read8(0xFF02) & 0x7Cu) == 0x7C, "serial unused control bits read high");
    memory->tick_tcycles(511);
    require(memory->read8(0xFF01) == 0 && serial_busy(*memory) && !serial_irq(*memory),
            "normal serial shifts no bit before512 CPU T-cycles");
    memory->tick_tcycles(1);
    require(memory->read8(0xFF01) == 1 && serial_busy(*memory),
            "an unplugged wire supplies a high bit at the actual serial edge");
    memory->tick_tcycles(3583);
    require(serial_busy(*memory) && !serial_irq(*memory), "normal serial remains busy through cycle4095");
    memory->tick_tcycles(1);
    require(memory->read8(0xFF01) == 0xFF && !serial_busy(*memory) && serial_irq(*memory),
            "unconnected normal transfer completes at4096 cycles with FF and IRQ3");
    memory->write8(0xFF0F, 0);
    memory->tick_tcycles(4096);
    require(!serial_irq(*memory), "acknowledged serial completion does not retrigger while idle");
    start_serial(*memory, 0, 0x83);
    memory->tick_tcycles(127);
    require(serial_busy(*memory) && !serial_irq(*memory), "fast serial remains busy through cycle127");
    memory->tick_tcycles(1);
    require(!serial_busy(*memory) && serial_irq(*memory) && memory->read8(0xFF01) == 0xFF,
            "CGB fast serial completes eight sixteen-cycle bits at128 CPU T-cycles");
    memory->clear_interrupt(3);
    require(!serial_irq(*memory), "clear_interrupt acknowledges the serial source as well as IF storage");
    memory->write8(0xFF4D, 1);
    require(memory->perform_speed_switch(), "prepare double-speed serial fixture");
    start_serial(*memory, 0, 0x81);
    const auto cpu_before = memory->total_tcycles();
    const auto base_before = memory->total_base_tcycles();
    memory->tick_tcycles(4096);
    require(serial_irq(*memory) && !serial_busy(*memory)
            && memory->total_tcycles()-cpu_before == 4096
            && memory->total_base_tcycles()-base_before == 2048,
            "serial divider follows CPU clocks while double-speed PPU and APU stay on base clocks");
}

void serial_external_timeout_and_abort() {
    auto memory = std::make_unique<Memory>();
    start_serial(*memory, 0xA5, 0x80);
    memory->tick_tcycles(3*4096);
    require(serial_busy(*memory) && !serial_irq(*memory) && memory->read8(0xFF01) == 0xA5,
            "external-clock transfer has no invented timeout or response without clock edges");
    memory->write8(0xFF02, 0);
    memory->tick_tcycles(4096);
    require(!serial_busy(*memory) && !serial_irq(*memory) && memory->read8(0xFF01) == 0xA5,
            "clearing serial start aborts an external wait without raising an IRQ");
    start_serial(*memory, 0, 0x81);
    memory->tick_tcycles(1024);
    require(memory->read8(0xFF01) == 3, "unconnected serial shifts partial data before abort");
    memory->write8(0xFF02, 1);
    memory->tick_tcycles(4096);
    require(memory->read8(0xFF01) == 3 && !serial_busy(*memory) && !serial_irq(*memory),
            "mid-byte abort stops remaining internal clock edges");
    start_serial(*memory, 0x55, 0x81);
    memory->tick_tcycles(4096);
    require(memory->read8(0xFF01) == 0xFF && serial_irq(*memory), "a new transfer starts cleanly after abort");
}

void serial_real_peer_bits_and_ack() {
    auto master = std::make_unique<Memory>();
    auto slave = std::make_unique<Memory>();
    master->connect_link_peer(*slave);
    start_serial(*slave, 0x3C, 0x80);
    slave->tick_tcycles(4096);
    require(slave->read8(0xFF01) == 0x3C && serial_busy(*slave), "armed peer cannot supply its own external clock");
    start_serial(*master, 0xA5, 0x81);
    master->tick_tcycles(512);
    require(master->read8(0xFF01) == 0x4A && slave->read8(0xFF01) == 0x79,
            "peer clock exchanges actual outgoing MSB bits simultaneously");
    require(!serial_irq(*master) && !serial_irq(*slave), "partial peer byte does not raise either completion IRQ");
    master->tick_tcycles(3584);
    require(master->read8(0xFF01) == 0x3C && slave->read8(0xFF01) == 0xA5
            && !serial_busy(*master) && !serial_busy(*slave), "eight peer edges exchange both actual bytes");
    require(serial_irq(*master) && serial_irq(*slave), "both endpoints see their actual completion IRQ immediately");
    master->write8(0xFF0F, 0);
    require(!serial_irq(*master) && serial_irq(*slave), "one endpoint cannot acknowledge its peer interrupt");
    slave->clear_interrupt(3);
    require(!serial_irq(*slave), "the peer interrupt can be independently acknowledged");
    master->disconnect_link_peer();
}

void serial_disconnect_and_peer_abort() {
    for (const bool abort_peer : {false, true}) {
        auto master = std::make_unique<Memory>();
        auto slave = std::make_unique<Memory>();
        master->connect_link_peer(*slave);
        start_serial(*slave, 0x3C, 0x80);
        start_serial(*master, 0xA5, 0x81);
        master->tick_tcycles(512);
        if (abort_peer) slave->write8(0xFF02, 0);
        else master->disconnect_link_peer();
        master->tick_tcycles(3584);
        require(master->read8(0xFF01) == 0x7F && serial_irq(*master),
                "disconnect or peer abort supplies only high bits for the remainder");
        slave->tick_tcycles(8192);
        require(slave->read8(0xFF01) == 0x79 && !serial_irq(*slave),
                "disconnected or aborted peer retains its own partial shifted register");
        require(serial_busy(*slave) == !abort_peer,
                "a disconnected external wait remains busy while an explicitly aborted wait stops");
        master->disconnect_link_peer();
    }
}

void serial_copy_isolation() {
    auto master = std::make_unique<Memory>();
    auto slave = std::make_unique<Memory>();
    master->connect_link_peer(*slave);
    start_serial(*slave, 0x3C, 0x80);
    start_serial(*master, 0xA5, 0x81);
    master->tick_tcycles(512);
    auto copy = std::make_unique<Memory>(*master);
    auto assigned = std::make_unique<Memory>();
    *assigned = *master;
    copy->tick_tcycles(3584);
    assigned->tick_tcycles(3584);
    require(copy->read8(0xFF01) == 0x7F && assigned->read8(0xFF01) == 0x7F
            && serial_irq(*copy) && serial_irq(*assigned),
            "copy and assignment retain partial registers but never inherit a live peer connection");
    require(master->read8(0xFF01) == 0x4A && slave->read8(0xFF01) == 0x79
            && !serial_irq(*master) && !serial_irq(*slave),
            "ticking a Memory snapshot cannot mutate either live endpoint");
    copy.reset();
    assigned.reset();
    master->tick_tcycles(3584);
    require(master->read8(0xFF01) == 0x3C && slave->read8(0xFF01) == 0xA5,
            "destroying snapshots does not disconnect the original real-bit link");
    master->disconnect_link_peer();
}

void serial_clock_handover_and_no_double_tick() {
    auto first = std::make_unique<Memory>();
    auto second = std::make_unique<Memory>();
    first->connect_link_peer(*second);
    start_serial(*first, 0x12, 0x81);
    first->write8(0xFF02, 0x80); // It relinquishes its clock but stays armed.
    start_serial(*second, 0x34, 0x81);
    second->tick_tcycles(4096);
    require(first->read8(0xFF01) == 0x34 && second->read8(0xFF01) == 0x12
            && serial_irq(*first) && serial_irq(*second),
            "rewriting an active clock driver as external permits real peer clock handover");

    start_serial(*first, 0x96, 0x81);
    start_serial(*second, 0x69, 0x81);
    for (unsigned i = 0; i < 4095; ++i) {
        first->tick_tcycles(1);
        second->tick_tcycles(1);
    }
    require(serial_busy(*first) && serial_busy(*second),
            "ticking two internally armed endpoints does not double the shared clock");
    first->tick_tcycles(1);
    second->tick_tcycles(1);
    require(first->read8(0xFF01) == 0x69 && second->read8(0xFF01) == 0x96
            && serial_irq(*first) && serial_irq(*second),
            "one actual internal clock driver completes the bidirectional byte");
    first->disconnect_link_peer();
}

void serial_connected_runtime_interrupt() {
    auto master = std::make_unique<Runtime>();
    auto peer = std::make_unique<Runtime>();
    master->memory().connect_link_peer(peer->memory());
    start_serial(peer->memory(), 0x42, 0x80);
    start_serial(master->memory(), 0x24, 0x81);
    peer->memory().write8(0xFFFF, 8);
    peer->cpu().pc = 0x3456;
    peer->cpu().sp = 0xD000;
    peer->cpu().ime = true;
    master->memory().tick_tcycles(4096);
    const auto calls = dwm2t::test_stubs::dispatch_calls;
    require(peer->step() == StepResult::Continue && peer->cpu().pc == 0x58
            && peer->cpu().last_mcycles == 5 && !serial_irq(peer->memory()),
            "a real connected serial completion reaches Runtime vector58 and is acknowledged");
    require(peer->memory().read8(0xCFFE) == 0x56 && peer->memory().read8(0xCFFF) == 0x34
            && peer->memory().read8(0xFF01) == 0x24
            && dwm2t::test_stubs::dispatch_calls == calls,
            "connected IRQ preserves the actual peer byte and return PC without running fake game code");
    master->memory().disconnect_link_peer();
}

using CaseFunction = void (*)();
struct Case { const char* name; CaseFunction run; };
struct Outcome { std::string name; std::string error; unsigned passed_checks; };

std::string json_string(const std::string& text) {
    std::string result = "\"";
    for (const char c : text) {
        if (c == '\\' || c == '"') result += '\\';
        if (c == '\n') result += "\\n";
        else if (c == '\r') result += "\\r";
        else result += c;
    }
    return result+'"';
}

} // namespace

int main(int argc, char** argv) {
    std::filesystem::path evidence;
    std::string group;
    std::vector<Outcome> outcomes;
    bool reserved = false;
    bool passed = false;
    std::string fatal;
    try {
        if (argc != 3) throw std::runtime_error("expected group and new evidence directory");
        group = argv[1];
        evidence = argv[2];
        if (std::filesystem::exists(evidence) || !std::filesystem::create_directories(evidence))
            throw std::runtime_error("contract evidence directory must be new");
        reserved = true;
        std::vector<Case> cases;
        if (group == "memory") cases = {
            {"mapper_physical_rom_and_wram", mapper_physical_rom_and_wram},
            {"speed_switch_and_clock_domains", speed_switch_and_clock_domains},
            {"timer_overflow_reload_and_write_edges", timer_overflow_reload_and_write_edges},
            {"general_vram_dma", general_vram_dma},
            {"hblank_dma_and_abort", hblank_dma_and_abort}};
        else if (group == "runtime") cases = {
            {"interrupt_priority_and_stack", interrupt_priority_and_stack},
            {"ei_di_reti_and_halt", ei_di_reti_and_halt},
            {"ei_halt_interrupt_return", ei_halt_interrupt_return},
            {"halt_idle_and_wake", halt_idle_and_wake},
            {"stop_wake_and_speed_opcode", stop_wake_and_speed_opcode},
            {"runtime_dma_stall_and_interrupt", runtime_dma_stall_and_interrupt},
            {"hram_entries_and_halt_bug", hram_entries_and_halt_bug},
            {"sticky_trap_and_zero_aot_identity", sticky_trap_and_zero_aot_identity}};
        else if (group == "serial") cases = {
            {"serial_unconnected_and_fast", serial_unconnected_and_fast},
            {"serial_external_timeout_and_abort", serial_external_timeout_and_abort},
            {"serial_real_peer_bits_and_ack", serial_real_peer_bits_and_ack},
            {"serial_disconnect_and_peer_abort", serial_disconnect_and_peer_abort},
            {"serial_copy_isolation", serial_copy_isolation},
            {"serial_clock_handover_and_no_double_tick", serial_clock_handover_and_no_double_tick},
            {"serial_connected_runtime_interrupt", serial_connected_runtime_interrupt}};
        else throw std::runtime_error("unknown hardware contract group");
        for (const auto& test : cases) {
            const unsigned before = checks;
            std::string error;
            try { test.run(); }
            catch (const std::exception& failure) { error = failure.what(); }
            outcomes.push_back({test.name, error, checks-before});
            std::cout << "HARDWARE_CASE " << group << ' ' << test.name << ' '
                      << (error.empty() ? "PASS" : "FAIL") << " checks=" << checks-before;
            if (!error.empty()) std::cout << " reason=" << error;
            std::cout << '\n';
        }
        passed = !outcomes.empty();
        for (const auto& outcome : outcomes) if (!outcome.error.empty()) passed = false;
    } catch (const std::exception& failure) { fatal = failure.what(); }
    if (reserved) {
        std::ofstream report(evidence/"hardware-contracts.json", std::ios::out);
        report << "{\n  \"schema\": 1,\n  \"status\": " << json_string(passed ? "passed" : "failed")
               << ",\n  \"group\": " << json_string(group)
               << ",\n  \"checks\": " << checks << ",\n  \"original_game_executed\": false,"
               << "\n  \"original_save_loaded_or_written\": false,\n  \"original_rom_aot_entries\": 0,"
               << "\n  \"rom_dispatch_stub_calls\": " << dwm2t::test_stubs::dispatch_calls
               << ",\n  \"scope\": \"Actual host hardware core with synthetic unit registers and trapping ROM stubs; no gameplay or AOT coverage claim\","
               << "\n  \"cases\": [";
        for (std::size_t i = 0; i < outcomes.size(); ++i) {
            if (i) report << ',';
            report << "\n    {\"name\": " << json_string(outcomes[i].name)
                   << ", \"status\": " << json_string(outcomes[i].error.empty() ? "passed" : "failed")
                   << ", \"checks\": " << outcomes[i].passed_checks
                   << ", \"error\": " << json_string(outcomes[i].error) << '}';
        }
        report << "\n  ],\n  \"fatal_error\": " << json_string(fatal) << "\n}\n";
        report.close();
        if (!report) { passed = false; fatal = "cannot persist hardware contract receipt"; }
    }
    if (!fatal.empty()) std::cerr << "HARDWARE_CONTRACTS_FAIL " << fatal << '\n';
    std::cout << (passed ? "HARDWARE_CONTRACTS_PASS " : "HARDWARE_CONTRACTS_FAIL ")
              << group << " checks=" << checks << " original_game_executed=false\n";
    return passed ? 0 : 1;
}
