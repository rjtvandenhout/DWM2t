#pragma once

#include "recomp/bank0.hpp"

#include <cstddef>
#include <cstdint>

namespace dwm2t {

// Generated registry dispatches only banks translated ahead-of-time into the
// executable. Unknown banks return MissingBank, making the real boot path
// discoverable without falling back to runtime opcode interpretation.
StepResult execute_translated_romx(Cpu& cpu, Memory& memory);
bool romx_bank_is_translated(std::uint16_t bank);
std::size_t translated_romx_bank_count();

} // namespace dwm2t
