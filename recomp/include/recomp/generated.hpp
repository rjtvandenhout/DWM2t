#pragma once

#include "recomp/cpu.hpp"
#include "recomp/memory.hpp"

namespace dwm2t {

// Generated at build time from src/banks/bank_000.asm.
void recomp_memset_0949(Cpu& cpu, Memory& memory);
void recomp_memcpy_1679(Cpu& cpu, Memory& memory);

} // namespace dwm2t
