#include "recomp/generated.hpp"

#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <string_view>

namespace {

constexpr std::string_view kTargetSha256 =
    "8e38a7420ef5239c7196aa4fd4b1499e65db2823e875bbf8241bb2199e766d4e";

bool test_memset() {
    dwm2t::Cpu cpu{};
    dwm2t::Memory memory{};

    constexpr std::uint16_t begin = 0xC100;
    constexpr std::uint16_t count = 32;
    constexpr std::uint8_t value = 0x5A;

    cpu.a = value;
    cpu.set_hl(begin);
    cpu.set_bc(count);

    dwm2t::recomp_memset_0949(cpu, memory);

    for (std::uint16_t i = 0; i < count; ++i) {
        if (memory.read8(static_cast<std::uint16_t>(begin + i)) != value) {
            return false;
        }
    }

    return cpu.bc() == 0 &&
           cpu.hl() == static_cast<std::uint16_t>(begin + count) &&
           cpu.a == 0;
}

bool test_memcpy() {
    dwm2t::Cpu cpu{};
    dwm2t::Memory memory{};

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

    dwm2t::recomp_memcpy_1679(cpu, memory);

    for (std::uint16_t i = 0; i < count; ++i) {
        if (memory.read8(static_cast<std::uint16_t>(source + i)) !=
            memory.read8(static_cast<std::uint16_t>(target + i))) {
            return false;
        }
    }

    return cpu.bc() == 0 &&
           cpu.de() == static_cast<std::uint16_t>(source + count) &&
           cpu.hl() == static_cast<std::uint16_t>(target + count) &&
           cpu.a == 0;
}

} // namespace

int main(int argc, char** argv) {
    if (argc > 1 && std::string_view(argv[1]) != "--self-test") {
        std::cerr << "Usage: DWM2tRecomp.exe [--self-test]\n";
        return EXIT_FAILURE;
    }

    std::cout << "DWM2t native static recomp - milestone M0\n";
    std::cout << "Target ROM SHA-256: " << kTargetSha256 << "\n\n";

    const bool memset_ok = test_memset();
    const bool memcpy_ok = test_memcpy();

    std::cout << "Bank 0 $0949 memset static recomp: "
              << (memset_ok ? "PASS" : "FAIL") << "\n";
    std::cout << "Bank 0 $1679 memcpy static recomp: "
              << (memcpy_ok ? "PASS" : "FAIL") << "\n";

    if (!memset_ok || !memcpy_ok) {
        std::cerr << "\nStatic recomp smoke test failed.\n";
        return EXIT_FAILURE;
    }

    std::cout << "\nM0 PASS: LR35902 source bytes were translated at build time "
                 "and executed as native host code.\n";
    return EXIT_SUCCESS;
}
