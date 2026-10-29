#include "recomp/hram_exec.hpp"

#include "recomp/lr35902_exec.hpp"

#include <array>
#include <cstdint>

namespace dwm2t {

namespace {

constexpr std::array<std::uint8_t, 10> kExpectedDmaCode = {
    0x3E, 0xC0,       // LD A,$C0
    0xE0, 0x46,       // LDH [$46],A
    0x3E, 0x28,       // LD A,40
    0x3D,             // DEC A
    0x20, 0xFD,       // JR NZ,$FF86
    0xC9,             // RET
};

bool signature_matches(const Memory& memory) {
    for (std::size_t i = 0; i < kExpectedDmaCode.size(); ++i) {
        if (memory.read8(static_cast<std::uint16_t>(0xFF80u + i)) !=
            kExpectedDmaCode[i]) {
            return false;
        }
    }
    return true;
}

StepResult finish(Cpu& cpu, Memory& memory) {
    cpu.finish_instruction();
    memory.tick_mcycles(cpu.last_mcycles);
    if (cpu.trapped) return StepResult::Trapped;
    if (cpu.stopped) return StepResult::Stopped;
    if (cpu.halted) return StepResult::Halted;
    return StepResult::Continue;
}

} // namespace

bool is_known_hram_dma_pc(std::uint16_t pc) {
    return pc >= 0xFF80 && pc <= 0xFF89;
}

StepResult execute_known_hram_dma(Cpu& cpu, Memory& memory) {
    if (!signature_matches(memory)) {
        cpu.trap(cpu.pc, memory.read8(cpu.pc));
        return StepResult::Trapped;
    }

    const bool halt_bug = cpu.halt_bug;
    cpu.halt_bug = false;

    switch (cpu.pc) {
        case 0xFF80:
            cpu.last_mcycles = 2;
            cpu.pc = static_cast<std::uint16_t>(0xFF82u - (halt_bug ? 1u : 0u));
            lr35902::exec_base<0x3E>(cpu, memory, halt_bug ? 0x3E : 0xC0, 0, 0xFF80);
            return finish(cpu, memory);

        case 0xFF81: {
            const bool taken = !cpu.zero();
            cpu.last_mcycles = static_cast<std::uint8_t>(taken ? 5 : 2);
            cpu.pc = static_cast<std::uint16_t>(0xFF82u - (halt_bug ? 1u : 0u));
            lr35902::exec_base<0xC0>(cpu, memory, 0, 0, 0xFF81);
            return finish(cpu, memory);
        }

        case 0xFF82:
            cpu.last_mcycles = 3;
            cpu.pc = static_cast<std::uint16_t>(0xFF84u - (halt_bug ? 1u : 0u));
            lr35902::exec_base<0xE0>(cpu, memory, halt_bug ? 0xE0 : 0x46, 0, 0xFF82);
            return finish(cpu, memory);

        case 0xFF83:
            cpu.last_mcycles = 2;
            cpu.pc = static_cast<std::uint16_t>(0xFF84u - (halt_bug ? 1u : 0u));
            lr35902::exec_base<0x46>(cpu, memory, 0, 0, 0xFF83);
            return finish(cpu, memory);

        case 0xFF84:
            cpu.last_mcycles = 2;
            cpu.pc = static_cast<std::uint16_t>(0xFF86u - (halt_bug ? 1u : 0u));
            lr35902::exec_base<0x3E>(cpu, memory, halt_bug ? 0x3E : 0x28, 0, 0xFF84);
            return finish(cpu, memory);

        case 0xFF85: {
            const bool taken = cpu.zero();
            cpu.last_mcycles = static_cast<std::uint8_t>(taken ? 3 : 2);
            cpu.pc = static_cast<std::uint16_t>(0xFF87u - (halt_bug ? 1u : 0u));
            lr35902::exec_base<0x28>(cpu, memory, halt_bug ? 0x28 : 0x3D, 0, 0xFF85);
            return finish(cpu, memory);
        }

        case 0xFF86:
            cpu.last_mcycles = 1;
            cpu.pc = static_cast<std::uint16_t>(0xFF87u - (halt_bug ? 1u : 0u));
            lr35902::exec_base<0x3D>(cpu, memory, 0, 0, 0xFF86);
            return finish(cpu, memory);

        case 0xFF87: {
            const bool taken = !cpu.zero();
            cpu.last_mcycles = static_cast<std::uint8_t>(taken ? 3 : 2);
            cpu.pc = static_cast<std::uint16_t>(0xFF89u - (halt_bug ? 1u : 0u));
            lr35902::exec_base<0x20>(cpu, memory, halt_bug ? 0x20 : 0xFD, 0, 0xFF87);
            return finish(cpu, memory);
        }

        case 0xFF88:
            cpu.last_mcycles = 1;
            cpu.pc = static_cast<std::uint16_t>(0xFF89u - (halt_bug ? 1u : 0u));
            lr35902::exec_base<0xFD>(cpu, memory, 0, 0, 0xFF88);
            return finish(cpu, memory);

        case 0xFF89:
            cpu.last_mcycles = 4;
            cpu.pc = static_cast<std::uint16_t>(0xFF8Au - (halt_bug ? 1u : 0u));
            lr35902::exec_base<0xC9>(cpu, memory, 0, 0, 0xFF89);
            return finish(cpu, memory);

        default:
            cpu.trap(cpu.pc, memory.read8(cpu.pc));
            return StepResult::Trapped;
    }
}

} // namespace dwm2t
