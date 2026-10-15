#pragma once

#include "recomp/bank0.hpp"

namespace dwm2t {

// Milestone M3 starts native ROMX execution with Bank 2, which is used by the
// game's CGB initialization path. Later milestones add more generated banks.
StepResult execute_romx_bank_2(Cpu& cpu, Memory& memory);

} // namespace dwm2t
