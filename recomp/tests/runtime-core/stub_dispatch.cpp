// These traps are test linkage only. No original ROM or generated AOT entries
// are embedded, interpreted or emulated by this independent host contract TU.
#include "recomp/bank0.hpp"
#include "recomp/memory.hpp"
#include "recomp/romx.hpp"

namespace dwm2t::test_stubs {
unsigned dispatch_calls = 0;
unsigned image_load_calls = 0;
}

namespace dwm2t {
namespace {
StepResult trap_dispatch(Cpu& cpu, Memory& memory) {
    ++test_stubs::dispatch_calls;
    cpu.trap(cpu.pc, memory.read8(cpu.pc));
    return StepResult::Trapped;
}
}

void load_full_rom_image(Memory&) { ++test_stubs::image_load_calls; }
void load_bank0_image(Memory&) { ++test_stubs::image_load_calls; }
StepResult execute_bank0_instruction(Cpu& cpu, Memory& memory) {
    return trap_dispatch(cpu, memory);
}
StepResult execute_bank0_romx_instruction(Cpu& cpu, Memory& memory) {
    return trap_dispatch(cpu, memory);
}
StepResult execute_translated_romx(Cpu& cpu, Memory& memory) {
    return trap_dispatch(cpu, memory);
}
StepResult run_bank0(Cpu& cpu, Memory& memory, std::size_t) {
    return trap_dispatch(cpu, memory);
}
std::size_t bank0_translated_entry_count() { return 0; }
std::size_t translated_romx_bank_count() { return 0; }
bool romx_bank_is_translated(std::uint16_t) { return false; }
}
