#include "recomp/m6.hpp"
#include "recomp/memory.hpp"
#include "recomp/renderer.hpp"
#include "recomp/runtime.hpp"
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <iomanip>
#include <iostream>

namespace dwm2t {
namespace {
constexpr std::uint64_t kM5TitleHash = 0x49c67a53ef4f8a80ull;

struct FrameResult {
    StepResult result = StepResult::Continue;
    std::uint64_t frame = 0;
    std::uint64_t hash = 0;
};

FrameResult advance_frame(Runtime& runtime, Renderer& renderer, std::uint8_t buttons) {
    auto& memory = runtime.memory();
    memory.set_joypad_state(buttons);
    const std::uint64_t start_frame = memory.frame_counter();
    constexpr std::size_t max_steps_per_frame = 2'000'000;
    for (std::size_t step = 0; step < max_steps_per_frame; ++step) {
        const StepResult result = runtime.step();
        if (result != StepResult::Continue) {
            return {result, memory.frame_counter(), 0};
        }
        if (memory.frame_counter() != start_frame) {
            renderer.render(memory, true);
            return {StepResult::Continue, memory.frame_counter(), renderer.hash()};
        }
    }
    return {StepResult::StepLimit, memory.frame_counter(), 0};
}

int report_failure(Runtime& runtime, StepResult result, std::uint64_t relative_frame) {
    const auto& cpu = runtime.cpu();
    const auto& memory = runtime.memory();
    if (result == StepResult::MissingBank) {
        std::cout << "M6_PROBE_MISSING_BANK bank=" << cpu.missing_bank
                  << " pc=0x" << std::hex << cpu.pc << std::dec
                  << " frame=" << memory.frame_counter()
                  << " relative=" << relative_frame
                  << " C5DB=" << static_cast<unsigned>(memory.read8(0xC5DB))
                  << " C5DC=" << static_cast<unsigned>(memory.read8(0xC5DC))
                  << "\n";
        return 50;
    }
    if (result == StepResult::Trapped) {
        std::cout << "M6_PROBE_TRAP pc=0x" << std::hex << cpu.trap_pc
                  << " opcode=0x" << static_cast<unsigned>(cpu.trap_opcode)
                  << std::dec << " bank=" << memory.current_rom_bank()
                  << " frame=" << memory.frame_counter()
                  << " relative=" << relative_frame << "\n";
        return 51;
    }
    if (result == StepResult::Stopped) {
        std::cout << "M6_PROBE_STOP pc=0x" << std::hex << cpu.pc << std::dec
                  << " frame=" << memory.frame_counter()
                  << " relative=" << relative_frame << "\n";
        return 52;
    }
    std::cout << "M6_PROBE_STEP_LIMIT frame=" << memory.frame_counter()
              << " relative=" << relative_frame << "\n";
    return 53;
}

std::uint8_t scripted_buttons(std::uint64_t relative_frame) {
    if (relative_frame < 3) return JoyStart;
    if (relative_frame >= 24 && ((relative_frame - 24) % 30) < 2) return JoyA;
    if (relative_frame >= 180 && ((relative_frame - 180) % 240) < 2) return JoyStart;
    return 0;
}
} // namespace

int run_m6_probe(const std::filesystem::path& output_dir) {
    std::filesystem::create_directories(output_dir);
    Runtime runtime{};
    Renderer renderer{};
    auto& memory = runtime.memory();

    std::cout << "M6 exploration: booting real game path and driving P1 input\n";

    std::uint64_t observed_frame = memory.frame_counter();
    unsigned stable_title = 0;
    constexpr std::size_t boot_step_limit = 80'000'000;
    for (std::size_t step = 0; step < boot_step_limit; ++step) {
        const StepResult result = runtime.step();
        if (result != StepResult::Continue) return report_failure(runtime, result, 0);
        if (memory.frame_counter() == observed_frame) continue;
        observed_frame = memory.frame_counter();
        renderer.render(memory, true);
        if (renderer.hash() == kM5TitleHash &&
            memory.read8(0xC5DB) == 5 &&
            memory.read8(0xC5DC) == 0) ++stable_title;
        else stable_title = 0;
        if (stable_title >= 30) break;
    }

    if (stable_title < 30) {
        std::cout << "M6_PROBE_FAIL did_not_reach_retained_m5_title\n";
        return 54;
    }

    renderer.write_bmp(output_dir / "00_title.bmp");
    std::cout << "M6_TITLE_READY frame=" << memory.frame_counter()
              << " hash=0x" << std::hex << renderer.hash() << std::dec << "\n";

    std::uint8_t last_state = memory.read8(0xC5DB);
    std::uint8_t last_substate = memory.read8(0xC5DC);
    std::uint64_t last_hash = renderer.hash();

    constexpr std::uint64_t probe_frames = 1800;
    for (std::uint64_t relative = 0; relative < probe_frames; ++relative) {
        const std::uint8_t buttons = scripted_buttons(relative);
        const FrameResult frame = advance_frame(runtime, renderer, buttons);
        if (frame.result != StepResult::Continue) {
            renderer.write_bmp(output_dir / "last_frame_before_failure.bmp");
            return report_failure(runtime, frame.result, relative);
        }

        const std::uint8_t state = memory.read8(0xC5DB);
        const std::uint8_t substate = memory.read8(0xC5DC);
        const bool state_changed = state != last_state || substate != last_substate;
        const bool hash_changed = frame.hash != last_hash;

        if (relative < 12 || state_changed || (hash_changed && relative % 15 == 0) ||
            relative % 60 == 0) {
            std::cout << "M6_FRAME relative=" << relative
                      << " absolute=" << frame.frame
                      << " buttons=0x" << std::hex << static_cast<unsigned>(buttons)
                      << " hash=0x" << frame.hash << std::dec
                      << " C5DB=" << static_cast<unsigned>(state)
                      << " C5DC=" << static_cast<unsigned>(substate)
                      << " bank=" << memory.current_rom_bank()
                      << " pc=0x" << std::hex << runtime.cpu().pc << std::dec
                      << "\n";
        }

        if (state_changed) {
            renderer.write_bmp(output_dir /
                ("state_" + std::to_string(state) + "_" +
                 std::to_string(substate) + "_frame_" +
                 std::to_string(relative) + ".bmp"));
        }
        last_state = state;
        last_substate = substate;
        last_hash = frame.hash;
    }

    memory.set_joypad_state(0);
    renderer.write_bmp(output_dir / "probe_final.bmp");
    std::cout << "M6_PROBE_COMPLETE frame=" << memory.frame_counter()
              << " C5DB=" << static_cast<unsigned>(memory.read8(0xC5DB))
              << " C5DC=" << static_cast<unsigned>(memory.read8(0xC5DC))
              << " hash=0x" << std::hex << renderer.hash() << std::dec << "\n";
    return 0;
}
} // namespace dwm2t
