#pragma once

#include "recomp/cpu.hpp"
#include "recomp/memory.hpp"

#include <cstddef>
#include <cstdint>

namespace dwm2t {

enum class StepResult {
    Continue,
    LeftBank0,
    Halted,
    Stopped,
    Trapped,
    MissingBank,
    StepLimit,
};

inline StepResult classify_bank0_step(const Cpu& cpu) {
    if (cpu.trapped) return StepResult::Trapped;
    if (cpu.stopped) return StepResult::Stopped;
    if (cpu.halted) return StepResult::Halted;
    if (cpu.pc >= 0x4000) return StepResult::LeftBank0;
    return StepResult::Continue;
}

void load_bank0_image(Memory& memory);
StepResult execute_bank0_instruction(Cpu& cpu, Memory& memory);
StepResult run_bank0(Cpu& cpu, Memory& memory, std::size_t max_steps);
std::size_t bank0_translated_entry_count();

} // namespace dwm2t
