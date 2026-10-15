#include "recomp/bank0.hpp"
#include "recomp/lr35902_exec.hpp"

#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <string_view>

namespace {

constexpr std::string_view kTargetSha256 =
    "8e38a7420ef5239c7196aa4fd4b1499e65db2823e875bbf8241bb2199e766d4e";

constexpr std::uint16_t kNativeReturnSentinel = 0x4000;
constexpr std::uint16_t kTestStackTop = 0xDFF0;

void prepare_call(dwm2t::Cpu& cpu,
                  dwm2t::Memory& memory,
                  std::uint16_t entry) {
    cpu.pc = entry;
    cpu.sp = kTestStackTop;
    cpu.halted = false;
    cpu.stopped = false;
    cpu.trapped = false;
    cpu.ime = false;
    cpu.ime_delay = 0;
    dwm2t::lr35902::push16(cpu, memory, kNativeReturnSentinel);
}

bool test_translation_coverage() {
    return dwm2t::bank0_translated_entry_count() == 0x4000;
}

bool test_memset() {
    dwm2t::Cpu cpu{};
    dwm2t::Memory memory{};
    dwm2t::load_bank0_image(memory);

    constexpr std::uint16_t begin = 0xC100;
    constexpr std::uint16_t count = 32;
    constexpr std::uint8_t value = 0x5A;

    cpu.a = value;
    cpu.set_hl(begin);
    cpu.set_bc(count);
    prepare_call(cpu, memory, 0x0949);

    const auto result = dwm2t::run_bank0(cpu, memory, 10000);

    for (std::uint16_t i = 0; i < count; ++i) {
        if (memory.read8(static_cast<std::uint16_t>(begin + i)) != value) {
            return false;
        }
    }

    return result == dwm2t::StepResult::LeftBank0 &&
           cpu.bc() == 0 &&
           cpu.hl() == static_cast<std::uint16_t>(begin + count) &&
           cpu.a == 0 &&
           cpu.sp == kTestStackTop;
}

bool test_memcpy() {
    dwm2t::Cpu cpu{};
    dwm2t::Memory memory{};
    dwm2t::load_bank0_image(memory);

    constexpr std::uint16_t source = 0xC200;
    constexpr std::uint16_t target = 0xC300;
    constexpr std::uint16_t count = 64;

    for (std::uint16_t i = 0; i < count; ++i) {
        memory.write8(
            static_cast<std::uint16_t>(source + i),
            static_cast<std::uint8_t>((i * 37u + 11u) & 0xFFu));
    }

    cpu.set_de(source);
    cpu.set_hl(target);
    cpu.set_bc(count);
    prepare_call(cpu, memory, 0x1679);

    const auto result = dwm2t::run_bank0(cpu, memory, 20000);

    for (std::uint16_t i = 0; i < count; ++i) {
        if (memory.read8(static_cast<std::uint16_t>(source + i)) !=
            memory.read8(static_cast<std::uint16_t>(target + i))) {
            return false;
        }
    }

    return result == dwm2t::StepResult::LeftBank0 &&
           cpu.bc() == 0 &&
           cpu.de() == static_cast<std::uint16_t>(source + count) &&
           cpu.hl() == static_cast<std::uint16_t>(target + count) &&
           cpu.a == 0 &&
           cpu.sp == kTestStackTop;
}

bool test_rng_095b() {
    dwm2t::Cpu cpu{};
    dwm2t::Memory memory{};
    dwm2t::load_bank0_image(memory);

    constexpr std::uint16_t rng_index = 0xC5E8;
    constexpr std::uint16_t rng_value = 0xC5E7;
    constexpr std::uint16_t table = 0x0973;

    memory.write8(rng_index, 0);
    const std::uint8_t expected = memory.read8(table + 1);

    cpu.set_hl(0xBEEF);
    prepare_call(cpu, memory, 0x095B);

    const auto result = dwm2t::run_bank0(cpu, memory, 1000);

    return result == dwm2t::StepResult::LeftBank0 &&
           memory.read8(rng_index) == 1 &&
           memory.read8(rng_value) == expected &&
           cpu.hl() == 0xBEEF &&
           cpu.sp == kTestStackTop;
}

bool test_flag_edges() {
    dwm2t::Cpu cpu{};
    dwm2t::Memory memory{};

    cpu.a = 0x0F;
    cpu.f = 0;
    dwm2t::lr35902::exec_base<0xC6>(cpu, memory, 0x01, 0, 0x0000);
    const bool add_ok =
        cpu.a == 0x10 &&
        !cpu.flag(dwm2t::Cpu::FlagZ) &&
        !cpu.flag(dwm2t::Cpu::FlagN) &&
        cpu.flag(dwm2t::Cpu::FlagH) &&
        !cpu.flag(dwm2t::Cpu::FlagC);

    cpu.a = 0x00;
    cpu.f = dwm2t::Cpu::FlagC;
    dwm2t::lr35902::exec_base<0xDE>(cpu, memory, 0x00, 0, 0x0000);
    const bool sbc_ok =
        cpu.a == 0xFF &&
        !cpu.flag(dwm2t::Cpu::FlagZ) &&
        cpu.flag(dwm2t::Cpu::FlagN) &&
        cpu.flag(dwm2t::Cpu::FlagH) &&
        cpu.flag(dwm2t::Cpu::FlagC);

    cpu.a = 0x09;
    cpu.f = 0;
    dwm2t::lr35902::exec_base<0xC6>(cpu, memory, 0x01, 0, 0x0000);
    dwm2t::lr35902::exec_base<0x27>(cpu, memory, 0, 0, 0x0000);
    const bool daa_ok = cpu.a == 0x10 && !cpu.flag(dwm2t::Cpu::FlagC);

    return add_ok && sbc_ok && daa_ok;
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

    std::cout << "DWM2t native static recomp - milestone M2\n";
    std::cout << "Target ROM SHA-256: " << kTargetSha256 << "\n\n";

    const bool coverage_ok = test_translation_coverage();
    const bool memset_ok = test_memset();
    const bool memcpy_ok = test_memcpy();
    const bool rng_ok = test_rng_095b();
    const bool flags_ok = test_flag_edges();

    print_result("Bank 0 translated entry coverage 16384/16384", coverage_ok);
    print_result("Bank 0 $0949 memset", memset_ok);
    print_result("Bank 0 $1679 memcpy", memcpy_ok);
    print_result("Bank 0 $095B RNG/table routine", rng_ok);
    print_result("LR35902 arithmetic/DAA flag edges", flags_ok);

    if (!coverage_ok || !memset_ok || !memcpy_ok || !rng_ok || !flags_ok) {
        std::cerr << "\nM2 static recomp self-test failed.\n";
        return EXIT_FAILURE;
    }

    std::cout
        << "\nM2 PASS: every fixed Bank 0 byte address has a build-time "
           "native translation and verified routines execute through the "
           "generic LR35902 semantic backend.\n";
    std::cout
        << "Next milestone: M3 hardware runtime (MBC5, mapped memory, "
           "interrupts, timers and joypad).\n";
    return EXIT_SUCCESS;
}
