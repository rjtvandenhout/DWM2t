// Runs actual production-generated master/case code over synthetic CPU unit
// ROMs. No original game/save is loaded; sparse cases do not claim full AOT.
#include "recomp/runtime.hpp"

#include <filesystem>
#include <fstream>
#include <iostream>
#include <memory>
#include <stdexcept>

namespace {
using dwm2t::Cpu;
using dwm2t::Runtime;
using dwm2t::StepResult;
unsigned checks = 0;
void require(bool condition, const char* name) {
    if (!condition) throw std::runtime_error(name);
    ++checks;
}
std::unique_ptr<Runtime> fixture(unsigned bank, std::uint16_t pc) {
    auto result = std::make_unique<Runtime>();
    result->memory().write8(0xFF40, 0);
    result->memory().write8(0xFFFF, 0);
    result->memory().write8(0xFF0F, 0);
    result->memory().write8(0x2000, static_cast<std::uint8_t>(bank));
    result->cpu().pc = pc;
    result->cpu().sp = 0xD000;
    result->cpu().set_hl(0xC234);
    return result;
}
void alias_control_flow() {
    auto runtime = fixture(0, 0x4100);
    require(runtime->step() == StepResult::Continue && runtime->cpu().pc == 0x4104
            && runtime->cpu().last_mcycles == 3, "generated bank-zero alias JR uses its actual CPU window");
    require(runtime->step() == StepResult::Continue && runtime->cpu().pc == 0x4140
            && runtime->cpu().sp == 0xCFFE, "generated alias CALL reaches its actual absolute target");
    require(runtime->memory().read8(0xCFFE) == 7 && runtime->memory().read8(0xCFFF) == 0x41,
            "generated alias CALL pushes4107 rather than relocated0107");
    require(runtime->step() == StepResult::Continue && runtime->cpu().pc == 0x4107
            && runtime->cpu().sp == 0xD000, "generated alias RET restores the real return address");
    require(runtime->step() == StepResult::Continue && runtime->cpu().a == 0x5A
            && runtime->cpu().pc == 0x4109, "generated alias executes its original immediate value");
    for (unsigned chunk = 1; chunk <= 3; ++chunk) {
        runtime->cpu().pc = static_cast<std::uint16_t>(0x4000u+0x1000u*chunk);
        require(runtime->step() == StepResult::Continue
                && runtime->cpu().a == 0x66u+0x11u*chunk
                && runtime->cpu().pc == 0x4002u+0x1000u*chunk,
                "unmodified production master dispatches each bank-zero alias chunk");
    }
}
void generated_halt_bug_operands() {
    auto runtime = fixture(0, 0x4107);
    runtime->cpu().halt_bug = true;
    require(runtime->step() == StepResult::Continue && runtime->cpu().a == 0x3E
            && runtime->cpu().pc == 0x4108 && !runtime->cpu().halt_bug,
            "actual generated alias LD shifts its immediate under HALT bug");
    runtime->cpu().pc = 0x4110;
    runtime->cpu().halt_bug = true;
    require(runtime->step() == StepResult::Continue && runtime->cpu().bc() == 0x3401
            && runtime->cpu().pc == 0x4112,
            "actual generated three-byte operand shifts both bytes under HALT bug");
}
void fixed_boundary_cb() {
    auto bit = fixture(1, 0x3FFF);
    bit->memory().write8(0xC234, 0);
    bit->cpu().f = Cpu::FlagC;
    require(bit->step() == StepResult::Continue && bit->cpu().pc == 0x4001
            && bit->cpu().last_mcycles == 3 && bit->cpu().zero()
            && bit->cpu().flag(Cpu::FlagH) && bit->cpu().flag(Cpu::FlagC),
            "CB at3FFF executes mapped bank-one BIT memory with three-cycle timing");
    auto reset = fixture(0, 0x3FFF);
    reset->memory().write8(0xC234, 0xFF);
    reset->cpu().f = Cpu::FlagC;
    require(reset->step() == StepResult::Continue && reset->cpu().last_mcycles == 4
            && reset->memory().read8(0xC234) == 0xFE && reset->cpu().f == Cpu::FlagC,
            "the same CB at3FFF fetches RES memory when bank-zero alias supplies the next byte");
    auto rotate = fixture(2, 0x3FFF);
    rotate->cpu().b = 0x80; // Unpopulated synthetic bank2 byte0 is00: RLC B.
    require(rotate->step() == StepResult::Continue && rotate->cpu().b == 1
            && rotate->cpu().last_mcycles == 2 && rotate->cpu().flag(Cpu::FlagC),
            "mapped boundary opcode changes both operation and cycles, not only metadata");
}
void romx_and_alias_boundary_cb() {
    for (unsigned bank : {0u, 1u}) {
        auto runtime = fixture(bank, 0x7FFF);
        runtime->memory().write8(0x8000, 0x06); // RLC(HL): four M-cycles.
        runtime->memory().write8(0xC234, 0x80);
        require(runtime->step() == StepResult::Continue && runtime->cpu().pc == 0x8001
                && runtime->cpu().last_mcycles == 4 && runtime->memory().read8(0xC234) == 1
                && runtime->cpu().flag(Cpu::FlagC),
                "CB at7FFF executes actual mapped VRAM opcode in both ROMX and alias windows");
    }
    for (const auto address : {0x3FFFu, 0x7FFFu}) {
        auto runtime = fixture(address == 0x3FFF ? 1 : 0, static_cast<std::uint16_t>(address));
        runtime->cpu().halt_bug = true;
        runtime->cpu().e = 0;
        require(runtime->step() == StepResult::Continue && runtime->cpu().e == 2
                && runtime->cpu().pc == address+1 && runtime->cpu().last_mcycles == 2,
                "bugged CB boundary fetch repeatsCB itself and executes SET1 E");
    }
}
void boundary_word_fetch() {
    auto fixed = fixture(1, 0x3FFE);
    require(fixed->step() == StepResult::Continue && fixed->cpu().bc() == 0x46CB
            && fixed->cpu().pc == 0x4001,
            "fixed-bank three-byte instruction fetches high operand from the actual next bank");
    auto alias = fixture(0, 0x7FFE);
    alias->memory().write8(0x8000, 0x06);
    require(alias->step() == StepResult::Continue && alias->cpu().bc() == 0x06CB
            && alias->cpu().pc == 0x8001,
            "alias three-byte instruction fetches high operand from mapped VRAM");
}
}

int main(int argc, char** argv) {
    bool passed = false;
    bool reserved = false;
    std::filesystem::path output;
    try {
        if (argc != 2) throw std::runtime_error("expected new generated-AOT evidence directory");
        output = argv[1];
        if (std::filesystem::exists(output) || !std::filesystem::create_directories(output))
            throw std::runtime_error("generated-AOT evidence directory must be new");
        reserved = true;
        alias_control_flow();
        generated_halt_bug_operands();
        fixed_boundary_cb();
        romx_and_alias_boundary_cb();
        boundary_word_fetch();
        passed = true;
    } catch (const std::exception& error) {
        std::cerr << "GENERATED_AOT_CONTRACTS_FAIL " << error.what() << '\n';
    }
    if (reserved) {
        std::ofstream report(output/"generated-aot-contracts.json");
        report << "{\"schema\":1,\"status\":\"" << (passed ? "passed" : "failed")
               << "\",\"checks\":" << checks
               << ",\"original_game_executed\":false,\"synthetic_fixture\":true,"
               << "\"sparse_generated_cases\":true,\"full_bank_coverage_claimed\":false,"
               << "\"scope\":\"Actual production AOT master/case emitters over synthetic unit ROMs; no original-game acceptance\"}\n";
        report.close();
        if (!report) passed = false;
    }
    std::cout << (passed ? "GENERATED_AOT_CONTRACTS_PASS" : "GENERATED_AOT_CONTRACTS_FAIL")
              << " checks=" << checks << " original_game_executed=false\n";
    return passed ? 0 : 1;
}
