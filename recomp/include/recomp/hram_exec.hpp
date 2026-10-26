#pragma once

#include "recomp/bank0.hpp"

namespace dwm2t {

// DWM2 copies one fixed 10-byte OAM DMA helper from ROM0 into HRAM $FF80.
// Its machine code is known at build time, so it remains ahead-of-time
// translated instead of falling back to an LR35902 runtime interpreter.
// Every byte entry in that exact signature has native opcode semantics,
// including the shifted fetch/PC behavior after the HALT bug.
bool is_known_hram_dma_pc(std::uint16_t pc);
StepResult execute_known_hram_dma(Cpu& cpu, Memory& memory);

} // namespace dwm2t
