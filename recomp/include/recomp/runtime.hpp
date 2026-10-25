#pragma once

#include "recomp/bank0.hpp"
#include "recomp/cpu.hpp"
#include "recomp/memory.hpp"

#include <cstddef>
#include <cstdint>

namespace dwm2t {

class Runtime {
public:
    Runtime();

    void reset_cgb_post_boot();

    [[nodiscard]] Cpu& cpu() { return cpu_; }
    [[nodiscard]] const Cpu& cpu() const { return cpu_; }
    [[nodiscard]] Memory& memory() { return memory_; }
    [[nodiscard]] const Memory& memory() const { return memory_; }

    StepResult step();
    StepResult run(std::size_t max_steps);

private:
    bool service_interrupt_if_needed();
    StepResult execute_current_instruction();

    Cpu cpu_{};
    Memory memory_{};
};

} // namespace dwm2t
