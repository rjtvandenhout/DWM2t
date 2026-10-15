#include "recomp/bank0.hpp"
#include "recomp/lr35902_exec.hpp"
#include "recomp/runtime.hpp"

#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <string_view>

namespace {

constexpr std::string_view kTargetSha256 =
    "8e38a7420ef5239c7196aa4fd4b1499e65db2823e875bbf8241bb2199e766d4e";

bool test_embedded_rom_and_mbc5() {
    dwm2t::Memory memory{};
    dwm2t::load_full_rom_image(memory);

    const bool header_ok =
        memory.read8(0x0100) == 0x00 &&
        memory.read8(0x0101) == 0xC3 &&
        memory.read8(0x0147) == 0x1B &&
        memory.read8(0x0148) == 0x07 &&
        memory.read8(0x0149) == 0x03;

    const std::uint8_t bank1_first = memory.rom()[0x4000];
    const std::uint8_t bank2_first = memory.rom()[0x8000];

    const bool default_bank_ok =
        memory.current_rom_bank() == 1 &&
        memory.read8(0x4000) == bank1_first;

    memory.write8(0x2000, 0x02);
    const bool low_bank_ok =
        memory.current_rom_bank() == 2 &&
        memory.read8(0x4000) == bank2_first;

    memory.write8(0x2000, 0x00);
    memory.write8(0x3000, 0x01);
    const bool high_bit_ok = memory.current_rom_bank() == 0x100;

    memory.write8(0x3000, 0x00);
    memory.write8(0x0000, 0x0A);
    memory.write8(0x4000, 0x02);
    memory.write8(0xA123, 0x5A);
    const bool sram_ok =
        memory.ram_enabled() &&
        memory.current_ram_bank() == 2 &&
        memory.read8(0xA123) == 0x5A;

    return header_ok && default_bank_ok && low_bank_ok && high_bit_ok && sram_ok;
}

bool test_wram_vram_and_dma() {
    dwm2t::Memory memory{};
    dwm2t::load_full_rom_image(memory);

    memory.write8(0xFF70, 0x03);
    memory.write8(0xD000, 0xA3);
    memory.write8(0xFF70, 0x01);
    const bool wram_isolated = memory.read8(0xD000) != 0xA3;
    memory.write8(0xFF70, 0x03);
    const bool wram_restored = memory.read8(0xD000) == 0xA3;

    memory.write8(0xFF4F, 0x00);
    memory.write8(0x8000, 0x11);
    memory.write8(0xFF4F, 0x01);
    memory.write8(0x8000, 0x22);
    const bool vram1 = memory.read8(0x8000) == 0x22;
    memory.write8(0xFF4F, 0x00);
    const bool vram0 = memory.read8(0x8000) == 0x11;

    for (std::uint16_t i = 0; i < 0xA0; ++i) {
        memory.write8(static_cast<std::uint16_t>(0xC100 + i),
                      static_cast<std::uint8_t>(i ^ 0x5A));
    }
    memory.write8(0xFF46, 0xC1);

    bool dma_ok = true;
    for (std::uint16_t i = 0; i < 0xA0; ++i) {
        if (memory.read8(static_cast<std::uint16_t>(0xFE00 + i)) !=
            static_cast<std::uint8_t>(i ^ 0x5A)) {
            dma_ok = false;
            break;
        }
    }

    return wram_isolated && wram_restored && vram0 && vram1 && dma_ok;
}

bool test_timer_and_joypad() {
    dwm2t::Memory memory{};

    memory.write8(0xFF05, 0xFE);
    memory.write8(0xFF06, 0xA7);
    memory.write8(0xFF07, 0x05); // enable, DIV bit 3 input
    memory.tick_tcycles(40);

    const bool timer_ok =
        memory.read8(0xFF05) == 0xA7 &&
        (memory.read8(0xFF0F) & 0x04) != 0;

    memory.write8(0xFF0F, 0);
    memory.write8(0xFF00, 0x10); // buttons selected
    memory.set_joypad_state(dwm2t::JoyA | dwm2t::JoyStart);
    const std::uint8_t p1 = memory.read8(0xFF00);

    const bool joypad_ok =
        (p1 & 0x01) == 0 &&
        (p1 & 0x08) == 0 &&
        (memory.read8(0xFF0F) & 0x10) != 0;

    return timer_ok && joypad_ok;
}

bool test_interrupt_entry() {
    dwm2t::Runtime runtime{};
    auto& cpu = runtime.cpu();
    auto& memory = runtime.memory();

    cpu.pc = 0x1234;
    cpu.sp = 0xDFF0;
    cpu.ime = true;
    memory.write8(0xFFFF, 0x01);
    memory.write8(0xFF0F, 0x01);

    const std::uint64_t before = memory.total_tcycles();
    const auto result = runtime.step();

    return result == dwm2t::StepResult::Continue &&
           cpu.pc == 0x0040 &&
           cpu.sp == 0xDFEE &&
           memory.read8(0xDFEE) == 0x34 &&
           memory.read8(0xDFEF) == 0x12 &&
           !cpu.ime &&
           (memory.read8(0xFF0F) & 1u) == 0 &&
           memory.total_tcycles() - before == 20;
}

bool test_halt_bug_trigger() {
    dwm2t::Cpu cpu{};
    dwm2t::Memory memory{};

    cpu.ime = false;
    memory.write8(0xFFFF, 0x01);
    memory.write8(0xFF0F, 0x01);

    dwm2t::lr35902::exec_base<0x76>(cpu, memory, 0, 0, 0x2000);

    return !cpu.halted && cpu.halt_bug;
}

bool test_native_romx_bank2_call() {
    dwm2t::Runtime runtime{};
    auto& cpu = runtime.cpu();
    auto& memory = runtime.memory();

    // FUN_ROM2_42FA is part of the real CGB initialization path. It copies the
    // eight bytes at Bank 2:$4322 to two WRAM locations using Bank 0 memcpy.
    memory.write8(0x2000, 0x02);
    memory.write8(0xC525, 0x01); // IsGBC

    cpu = dwm2t::Cpu{};
    cpu.pc = 0x42FA;
    cpu.sp = 0xDFF0;
    dwm2t::lr35902::push16(cpu, memory, 0x8000);

    dwm2t::StepResult result = dwm2t::StepResult::Continue;
    for (std::size_t i = 0; i < 10000; ++i) {
        if (cpu.pc == 0x8000) break;
        result = runtime.step();
        if (result != dwm2t::StepResult::Continue) break;
    }

    constexpr std::uint8_t expected[8] = {
        0x00, 0x7C, 0xFF, 0x7F, 0xE0, 0x01, 0x00, 0x00
    };

    bool copy1 = true;
    bool copy2 = true;
    for (std::uint16_t i = 0; i < 8; ++i) {
        copy1 &= memory.read8(static_cast<std::uint16_t>(0xC49F + i)) == expected[i];
        copy2 &= memory.read8(static_cast<std::uint16_t>(0xC4DF + i)) == expected[i];
    }

    return result == dwm2t::StepResult::Continue &&
           cpu.pc == 0x8000 &&
           copy1 &&
           copy2 &&
           memory.read8(0xC526) == 0x7F &&
           memory.read8(0xC527) == 0x7F;
}

void print_result(std::string_view name, bool ok) {
    std::cout << name << ": " << (ok ? "PASS" : "FAIL") << "\n";
}

} // namespace

int main(int argc, char** argv) {
    if (argc > 1 && std::string_view(argv[1]) != "--self-test") {
        std::cerr << "Usage: DWM2tRecomp.exe [--self-test]\n";
        return EXIT_FAILURE;
    }

    std::cout << "DWM2t native static recomp - milestone M3\n";
    std::cout << "Target ROM SHA-256: " << kTargetSha256 << "\n\n";

    const bool mbc_ok = test_embedded_rom_and_mbc5();
    const bool memory_ok = test_wram_vram_and_dma();
    const bool timer_input_ok = test_timer_and_joypad();
    const bool interrupt_ok = test_interrupt_entry();
    const bool halt_ok = test_halt_bug_trigger();
    const bool bank2_ok = test_native_romx_bank2_call();

    print_result("Embedded 4 MiB ROM + MBC5 ROM/SRAM banking", mbc_ok);
    print_result("WRAM/VRAM banking + OAM DMA", memory_ok);
    print_result("Timer overflow + joypad matrix/IRQ", timer_input_ok);
    print_result("Interrupt priority/stack entry + 5 M-cycles", interrupt_ok);
    print_result("HALT bug trigger condition", halt_ok);
    print_result("Native Bank 2 -> Bank 0 -> Bank 2 call flow", bank2_ok);

    if (!mbc_ok || !memory_ok || !timer_input_ok ||
        !interrupt_ok || !halt_ok || !bank2_ok) {
        std::cerr << "\nM3 hardware runtime self-test failed.\n";
        return EXIT_FAILURE;
    }

    std::cout
        << "\nM3 PASS: the native recomp now has mapped Game Boy memory, "
           "MBC5 banking, SRAM, timers, interrupts, joypad, cycle advancement "
           "and ahead-of-time ROMX execution.\n";
    std::cout
        << "Next milestone: M4 PPU/OAM/tile renderer and native PC window.\n";
    return EXIT_SUCCESS;
}
