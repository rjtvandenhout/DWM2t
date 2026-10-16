#include "recomp/m7.hpp"
#include "recomp/memory.hpp"
#include "recomp/renderer.hpp"
#include "recomp/runtime.hpp"

#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <memory>
#include <string>
#include <unordered_set>
#include <vector>

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
        if (result == StepResult::MissingBank ||
            result == StepResult::Trapped ||
            result == StepResult::Stopped) {
            return {result, memory.frame_counter(), 0};
        }
        if (memory.frame_counter() != start_frame) {
            renderer.render(memory, true);
            return {StepResult::Continue, memory.frame_counter(), renderer.hash()};
        }
    }
    return {StepResult::StepLimit, memory.frame_counter(), 0};
}

int report_failure(Runtime& runtime, Renderer& renderer,
                   const std::filesystem::path& output_dir,
                   StepResult result, std::uint64_t relative_frame) {
    renderer.render(runtime.memory(), true);
    renderer.write_bmp(output_dir / "failure_frame.bmp");
    const auto& cpu = runtime.cpu();
    const auto& memory = runtime.memory();
    if (result == StepResult::MissingBank) {
        std::cout << "M7_DISCOVERY_MISSING_BANK bank=" << cpu.missing_bank
                  << " pc=0x" << std::hex << cpu.pc << std::dec
                  << " frame=" << memory.frame_counter()
                  << " relative=" << relative_frame
                  << " C5DB=" << static_cast<unsigned>(memory.read8(0xC5DB))
                  << " C5DC=" << static_cast<unsigned>(memory.read8(0xC5DC))
                  << " hash=0x" << std::hex << renderer.hash() << std::dec
                  << "\n";
        return 90;
    }
    if (result == StepResult::Trapped) {
        std::cout << "M7_DISCOVERY_TRAP pc=0x" << std::hex << cpu.trap_pc
                  << " opcode=0x" << static_cast<unsigned>(cpu.trap_opcode)
                  << std::dec << " bank=" << memory.current_rom_bank()
                  << " frame=" << memory.frame_counter()
                  << " relative=" << relative_frame << "\n";
        return 91;
    }
    if (result == StepResult::Stopped) {
        std::cout << "M7_DISCOVERY_STOP pc=0x" << std::hex << cpu.pc << std::dec
                  << " frame=" << memory.frame_counter()
                  << " relative=" << relative_frame << "\n";
        return 92;
    }
    std::cout << "M7_DISCOVERY_STEP_LIMIT frame=" << memory.frame_counter()
              << " relative=" << relative_frame << "\n";
    return 93;
}

std::uint8_t m6_story_buttons(std::uint64_t relative_frame) {
    if (relative_frame < 3) return JoyStart;
    if (relative_frame >= 24 && ((relative_frame - 24) % 30) < 2) return JoyA;
    if (relative_frame >= 180 && ((relative_frame - 180) % 240) < 2) return JoyStart;
    return 0;
}

std::uint32_t mix_segment(std::uint64_t segment) {
    std::uint32_t x = static_cast<std::uint32_t>(segment) ^ 0x6D2B79F5u;
    x ^= x >> 16;
    x *= 0x7FEB352Du;
    x ^= x >> 15;
    x *= 0x846CA68Bu;
    x ^= x >> 16;
    return x;
}

std::uint8_t exploration_buttons(std::uint64_t frame) {
    // Deterministic P1-only random walk at roughly one-tile cadence. Every
    // movement attempt is followed by a short A pulse so reachable NPCs,
    // doors, stairs and map objects are exercised without host state edits.
    constexpr std::uint64_t segment_frames = 24;
    const std::uint64_t segment = frame / segment_frames;
    const std::uint64_t phase = frame % segment_frames;
    const std::uint32_t mixed = mix_segment(segment);

    constexpr std::array<std::uint8_t, 4> directions = {
        JoyRight, JoyLeft, JoyUp, JoyDown
    };
    const std::uint8_t direction = directions[mixed & 3u];

    if (phase < 15) return direction;
    if (phase >= 17 && phase < 19) return JoyA;
    if ((segment % 31u) == 0u && phase >= 20 && phase < 22) return JoyB;
    return 0;
}

std::uint64_t wram_hash(const Memory& memory) {
    std::uint64_t hash = 1469598103934665603ull;
    for (std::uint32_t address = 0xC000; address < 0xE000; ++address) {
        hash ^= memory.read8(static_cast<std::uint16_t>(address));
        hash *= 1099511628211ull;
    }
    return hash;
}

} // namespace

int run_m7_discovery(const std::filesystem::path& output_dir) {
    std::filesystem::create_directories(output_dir);
    Runtime runtime{};
    Renderer renderer{};
    auto& memory = runtime.memory();

    std::uint64_t observed_frame = memory.frame_counter();
    unsigned stable_title = 0;
    constexpr std::size_t boot_step_limit = 80'000'000;

    for (std::size_t step = 0; step < boot_step_limit; ++step) {
        const StepResult result = runtime.step();
        if (result == StepResult::MissingBank ||
            result == StepResult::Trapped ||
            result == StepResult::Stopped) {
            return report_failure(runtime, renderer, output_dir, result, 0);
        }
        if (memory.frame_counter() == observed_frame) continue;
        observed_frame = memory.frame_counter();
        renderer.render(memory, true);
        if (renderer.hash() == kM5TitleHash &&
            memory.read8(0xC5DB) == 5 &&
            memory.read8(0xC5DC) == 0) {
            ++stable_title;
        } else {
            stable_title = 0;
        }
        if (stable_title >= 30) break;
    }

    if (stable_title < 30) {
        std::cout << "M7_DISCOVERY_FAIL retained_title\n";
        return 94;
    }

    renderer.write_bmp(output_dir / "00_title.bmp");

    // Reuse the proven M6 P1 path exactly to reach the opening ship map.
    for (std::uint64_t relative = 0; relative < 1800; ++relative) {
        const FrameResult frame =
            advance_frame(runtime, renderer, m6_story_buttons(relative));
        if (frame.result != StepResult::Continue) {
            return report_failure(runtime, renderer, output_dir, frame.result, relative);
        }
    }

    for (std::uint64_t i = 0; i < 36; ++i) {
        const FrameResult frame = advance_frame(runtime, renderer, i < 24 ? JoyRight : 0);
        if (frame.result != StepResult::Continue) {
            return report_failure(runtime, renderer, output_dir, frame.result, 1800 + i);
        }
    }

    renderer.write_bmp(output_dir / "01_m6_ship_start.bmp");
    std::cout << "M7_DISCOVERY_SHIP frame=" << memory.frame_counter()
              << " hash=0x" << std::hex << renderer.hash()
              << " wram=0x" << wram_hash(memory) << std::dec
              << " C5DB=" << static_cast<unsigned>(memory.read8(0xC5DB))
              << " C5DC=" << static_cast<unsigned>(memory.read8(0xC5DC))
              << "\n";

    std::uint64_t last_hash = renderer.hash();
    std::uint8_t last_state = memory.read8(0xC5DB);
    std::uint8_t last_substate = memory.read8(0xC5DC);
    constexpr std::uint64_t explore_frames = 30000;

    for (std::uint64_t relative = 0; relative < explore_frames; ++relative) {
        const std::uint8_t buttons = exploration_buttons(relative);
        const FrameResult frame = advance_frame(runtime, renderer, buttons);
        if (frame.result != StepResult::Continue) {
            return report_failure(runtime, renderer, output_dir, frame.result,
                                  1836 + relative);
        }

        const std::uint8_t state = memory.read8(0xC5DB);
        const std::uint8_t substate = memory.read8(0xC5DC);
        const bool state_changed = state != last_state || substate != last_substate;
        const bool screen_changed = frame.hash != last_hash;

        if (relative % 480 == 0 || state_changed) {
            const std::string name =
                "checkpoint_" + std::to_string(relative) +
                "_s" + std::to_string(state) + "_" + std::to_string(substate) +
                ".bmp";
            renderer.write_bmp(output_dir / name);
            std::cout << "M7_DISCOVERY_FRAME relative=" << relative
                      << " absolute=" << frame.frame
                      << " buttons=0x" << std::hex << static_cast<unsigned>(buttons)
                      << " hash=0x" << frame.hash
                      << " wram=0x" << wram_hash(memory) << std::dec
                      << " C5DB=" << static_cast<unsigned>(state)
                      << " C5DC=" << static_cast<unsigned>(substate)
                      << " bank=" << memory.current_rom_bank()
                      << " pc=0x" << std::hex << runtime.cpu().pc << std::dec
                      << " sram_dirty=" << (memory.sram_dirty() ? 1 : 0)
                      << " changed=" << (screen_changed ? 1 : 0)
                      << "\n";
        }

        last_hash = frame.hash;
        last_state = state;
        last_substate = substate;
    }

    memory.set_joypad_state(0);
    renderer.write_bmp(output_dir / "99_final.bmp");
    std::cout << "M7_DISCOVERY_COMPLETE frame=" << memory.frame_counter()
              << " hash=0x" << std::hex << renderer.hash()
              << " wram=0x" << wram_hash(memory) << std::dec
              << " C5DB=" << static_cast<unsigned>(memory.read8(0xC5DB))
              << " C5DC=" << static_cast<unsigned>(memory.read8(0xC5DC))
              << " sram_dirty=" << (memory.sram_dirty() ? 1 : 0)
              << "\n";
    return 0;
}


namespace {

StepResult advance_search_frame(Runtime& runtime, std::uint8_t buttons) {
    auto& memory = runtime.memory();
    memory.set_joypad_state(buttons);
    const std::uint64_t start_frame = memory.frame_counter();
    constexpr std::size_t max_steps_per_frame = 2'000'000;
    for (std::size_t step = 0; step < max_steps_per_frame; ++step) {
        const StepResult result = runtime.step();
        if (result == StepResult::MissingBank ||
            result == StepResult::Trapped ||
            result == StepResult::Stopped) {
            return result;
        }
        if (memory.frame_counter() != start_frame) return StepResult::Continue;
    }
    return StepResult::StepLimit;
}

std::uint64_t tilemap_hash(const Memory& memory) {
    std::uint64_t hash = 1469598103934665603ull;
    for (unsigned bank = 0; bank < 2; ++bank) {
        const auto* vram = memory.vram_bank_data(static_cast<std::uint8_t>(bank));
        for (std::size_t i = 0x1800; i < 0x2000; ++i) {
            hash ^= vram[i];
            hash *= 1099511628211ull;
        }
    }
    hash ^= memory.read8(0xFF42);
    hash *= 1099511628211ull;
    hash ^= memory.read8(0xFF43);
    hash *= 1099511628211ull;
    return hash;
}

std::uint64_t background_hash(const Memory& memory) {
    std::uint64_t hash = 1469598103934665603ull;
    for (unsigned bank = 0; bank < 2; ++bank) {
        const auto* vram =
            memory.vram_bank_data(static_cast<std::uint8_t>(bank));
        for (std::size_t i = 0x1800; i < 0x2000; ++i) {
            hash ^= vram[i];
            hash *= 1099511628211ull;
        }
    }
    return hash;
}

std::uint64_t sram_hash(const Memory& memory) {
    std::uint64_t hash = 1469598103934665603ull;
    for (const std::uint8_t value : memory.sram()) {
        hash ^= value;
        hash *= 1099511628211ull;
    }
    return hash;
}

const char* search_action_name(std::uint8_t action) {
    switch (action) {
        case 0: return "R";
        case 1: return "L";
        case 2: return "U";
        case 3: return "D";
        case 4: return "A";
        case 5: return "B";
        default: return "?";
    }
}

StepResult apply_search_action(Runtime& runtime, std::uint8_t action) {
    constexpr std::uint64_t macro_frames = 24;
    for (std::uint64_t phase = 0; phase < macro_frames; ++phase) {
        std::uint8_t buttons = 0;
        if (action < 4) {
            constexpr std::array<std::uint8_t, 4> directions = {
                JoyRight, JoyLeft, JoyUp, JoyDown
            };
            if (phase < 15) buttons = directions[action];
            if (phase >= 17 && phase < 19) buttons = JoyA;
        } else if (action == 4) {
            if (phase < 2 || (phase >= 8 && phase < 10) ||
                (phase >= 16 && phase < 18)) {
                buttons = JoyA;
            }
        } else if (action == 5 && phase < 2) {
            buttons = JoyB;
        }

        const StepResult result = advance_search_frame(runtime, buttons);
        if (result != StepResult::Continue) return result;
    }
    runtime.memory().set_joypad_state(0);
    (void)runtime.memory().apu().take_samples();
    return StepResult::Continue;
}

struct SearchNode {
    Runtime runtime{};
    std::vector<std::uint8_t> path{};
    std::uint64_t score = 0;
    std::uint64_t screen_hash = 0;
    std::uint64_t map_hash = 0;
    std::uint64_t save_hash = 0;
};

void print_search_path(const std::vector<std::uint8_t>& path) {
    std::cout << " path=";
    for (std::size_t i = 0; i < path.size(); ++i) {
        if (i != 0) std::cout << ",";
        std::cout << search_action_name(path[i]);
    }
}

} // namespace

int run_m7_route_search(const std::filesystem::path& output_dir) {
    std::filesystem::create_directories(output_dir);
    auto base_owner = std::make_unique<Runtime>();
    Runtime& base = *base_owner;
    Renderer renderer{};

    std::uint64_t observed_frame = base.memory().frame_counter();
    unsigned stable_title = 0;
    constexpr std::size_t boot_step_limit = 80'000'000;
    for (std::size_t step = 0; step < boot_step_limit; ++step) {
        const StepResult result = base.step();
        if (result == StepResult::MissingBank ||
            result == StepResult::Trapped ||
            result == StepResult::Stopped) {
            std::cout << "M7_SEARCH_FAIL boot result="
                      << static_cast<unsigned>(result) << "\n";
            return 120;
        }
        if (base.memory().frame_counter() == observed_frame) continue;
        observed_frame = base.memory().frame_counter();
        renderer.render(base.memory(), true);
        if (renderer.hash() == kM5TitleHash &&
            base.memory().read8(0xC5DB) == 5 &&
            base.memory().read8(0xC5DC) == 0) {
            ++stable_title;
        } else {
            stable_title = 0;
        }
        if (stable_title >= 30) break;
    }
    if (stable_title < 30) {
        std::cout << "M7_SEARCH_FAIL title_not_reached frame="
                  << base.memory().frame_counter()
                  << " pc=0x" << std::hex << base.cpu().pc << std::dec << std::endl;
        return 121;
    }

    for (std::uint64_t relative = 0; relative < 1800; ++relative) {
        const StepResult result =
            advance_search_frame(base, m6_story_buttons(relative));
        if (result != StepResult::Continue) {
            std::cout << "M7_SEARCH_FAIL story result="
                      << static_cast<unsigned>(result)
                      << " relative=" << relative
                      << " frame=" << base.memory().frame_counter()
                      << " bank=" << base.memory().current_rom_bank()
                      << " pc=0x" << std::hex << base.cpu().pc << std::dec << std::endl;
            return 122;
        }
    }
    for (std::uint64_t i = 0; i < 36; ++i) {
        const StepResult result =
            advance_search_frame(base, i < 24 ? JoyRight : 0);
        if (result != StepResult::Continue) {
            std::cout << "M7_SEARCH_FAIL ship_move result="
                      << static_cast<unsigned>(result)
                      << " relative=" << i
                      << " frame=" << base.memory().frame_counter()
                      << " bank=" << base.memory().current_rom_bank()
                      << " pc=0x" << std::hex << base.cpu().pc << std::dec << std::endl;
            return 123;
        }
    }

    constexpr std::uint64_t town_prefix_frames = 12600;
    for (std::uint64_t relative = 0; relative < town_prefix_frames; ++relative) {
        const StepResult result =
            advance_search_frame(base, exploration_buttons(relative));
        if (result == StepResult::MissingBank) {
            std::cout << "M7_SEARCH_MISSING_BANK_PREFIX bank="
                      << base.cpu().missing_bank << " pc=0x" << std::hex
                      << base.cpu().pc << std::dec << "\n";
            return 124;
        }
        if (result != StepResult::Continue) {
            std::cout << "M7_SEARCH_FAIL prefix result="
                      << static_cast<unsigned>(result)
                      << " relative=" << relative
                      << " frame=" << base.memory().frame_counter()
                      << " bank=" << base.memory().current_rom_bank()
                      << " pc=0x" << std::hex << base.cpu().pc << std::dec
                      << " C5DB=" << static_cast<unsigned>(base.memory().read8(0xC5DB))
                      << " C5DC=" << static_cast<unsigned>(base.memory().read8(0xC5DC))
                      << std::endl;
            return 125;
        }
    }

    (void)base.memory().apu().take_samples();
    renderer.render(base.memory(), true);
    renderer.write_bmp(output_dir / "search_base.bmp");

    std::cout << "M7_SEARCH_BASE frame=" << base.memory().frame_counter()
              << " screen=0x" << std::hex << renderer.hash()
              << " map=0x" << tilemap_hash(base.memory())
              << " sram=0x" << sram_hash(base.memory()) << std::dec
              << " C5DB=" << static_cast<unsigned>(base.memory().read8(0xC5DB))
              << " C5DC=" << static_cast<unsigned>(base.memory().read8(0xC5DC))
              << "\n";

    if (base.memory().read8(0xC5DB) != 1) {
        std::cout << "M7_SEARCH_FAIL base_not_overworld\n";
        return 126;
    }

    constexpr std::uint64_t frames_per_trial = 6000;
    constexpr std::uint32_t trial_count = 2;

    for (std::uint32_t seed = 0; seed < trial_count; ++seed) {
        auto trial_owner = std::make_unique<Runtime>(base);
        Runtime& trial = *trial_owner;
        Renderer trial_renderer{};
        std::uint64_t last_save = sram_hash(trial.memory());
        std::uint8_t previous_submode = trial.memory().read8(0xC5DC);
        unsigned dialog_capture = 0;

        for (std::uint64_t relative = 0; relative < frames_per_trial; ++relative) {
            constexpr std::uint64_t segment_frames = 20;
            const std::uint64_t segment = relative / segment_frames;
            const std::uint64_t phase = relative % segment_frames;
            const std::uint32_t salt =
                seed * 0xA511E9B3u + static_cast<std::uint32_t>(segment);
            const std::uint32_t mixed = mix_segment(salt);
            constexpr std::array<std::uint8_t, 4> directions = {
                JoyRight, JoyLeft, JoyUp, JoyDown
            };

            std::uint8_t buttons = 0;
            if (phase < 13) buttons = directions[mixed & 3u];
            if (phase >= 14 && phase < 16) buttons = JoyA;
            if ((segment + seed * 7u) % 43u == 0u &&
                phase >= 17 && phase < 19) {
                buttons = JoyB;
            }

            const StepResult result = advance_search_frame(trial, buttons);
            if (result == StepResult::MissingBank) {
                trial_renderer.render(trial.memory(), true);
                trial_renderer.write_bmp(
                    output_dir / ("search_missing_seed_" + std::to_string(seed) + ".bmp"));
                std::cout << "M7_SEARCH_MISSING_BANK seed=" << seed
                          << " relative=" << relative
                          << " bank=" << trial.cpu().missing_bank
                          << " pc=0x" << std::hex << trial.cpu().pc
                          << " screen=0x" << trial_renderer.hash()
                          << std::dec << std::endl;
                return 127;
            }
            if (result == StepResult::Trapped ||
                result == StepResult::Stopped ||
                result == StepResult::StepLimit) {
                std::cout << "M7_SEARCH_TRIAL_ABORT seed=" << seed
                          << " relative=" << relative
                          << " result=" << static_cast<unsigned>(result)
                          << std::endl;
                break;
            }

            const std::uint8_t mode = trial.memory().read8(0xC5DB);
            const std::uint8_t submode = trial.memory().read8(0xC5DC);

            if (previous_submode == 0 && submode != 0 && dialog_capture < 24) {
                trial_renderer.render(trial.memory(), true);
                const std::string dialog_name =
                    "search_dialog_seed_" + std::to_string(seed) + "_" +
                    std::to_string(dialog_capture) + ".bmp";
                trial_renderer.write_bmp(output_dir / dialog_name);
                std::cout << "M7_SEARCH_DIALOG seed=" << seed
                          << " capture=" << dialog_capture
                          << " relative=" << relative
                          << " C5DB=" << static_cast<unsigned>(mode)
                          << " C5DC=" << static_cast<unsigned>(submode)
                          << " screen=0x" << std::hex << trial_renderer.hash()
                          << " map=0x" << tilemap_hash(trial.memory())
                          << " sram=0x" << sram_hash(trial.memory())
                          << std::dec << std::endl;
                ++dialog_capture;
            }
            previous_submode = submode;

            if (mode != 1) {
                trial_renderer.render(trial.memory(), true);
                trial_renderer.write_bmp(
                    output_dir / ("search_mode_seed_" + std::to_string(seed) + ".bmp"));
                std::cout << "M7_SEARCH_MODE_CHANGE seed=" << seed
                          << " relative=" << relative
                          << " C5DB=" << static_cast<unsigned>(mode)
                          << " C5DC=" << static_cast<unsigned>(submode)
                          << " screen=0x" << std::hex << trial_renderer.hash()
                          << " map=0x" << tilemap_hash(trial.memory())
                          << " sram=0x" << sram_hash(trial.memory())
                          << std::dec << std::endl;
                return 0;
            }

            if ((relative % 24u) == 0u) {
                const std::uint64_t save = sram_hash(trial.memory());
                if (save != last_save) {
                    trial_renderer.render(trial.memory(), true);
                    std::cout << "M7_SEARCH_SRAM_CHANGE seed=" << seed
                              << " relative=" << relative
                              << " before=0x" << std::hex << last_save
                              << " after=0x" << save
                              << " screen=0x" << trial_renderer.hash()
                              << std::dec << std::endl;
                    last_save = save;
                }
            }

            if ((relative % 240u) == 0u) {
                (void)trial.memory().apu().take_samples();
            }
        }

        (void)trial.memory().apu().take_samples();
        trial_renderer.render(trial.memory(), true);
        trial_renderer.write_bmp(
            output_dir / ("search_seed_" + std::to_string(seed) + "_final.bmp"));

        if (seed <= 1) {
            struct FocusLeg {
                std::uint8_t buttons;
                std::uint64_t frames;
            };
            constexpr std::array<std::array<FocusLeg, 5>, 6> strategies = {{
                {{{JoyLeft, 100}, {0, 8}, {JoyUp, 80}, {0, 8}, {JoyA, 24}}},
                {{{JoyUp, 80}, {0, 8}, {JoyLeft, 110}, {JoyUp, 40}, {JoyA, 24}}},
                {{{JoyLeft, 150}, {JoyA, 24}, {JoyUp, 100}, {JoyA, 24}, {0, 8}}},
                {{{JoyUp, 150}, {JoyLeft, 150}, {JoyA, 24}, {JoyUp, 32}, {0, 8}}},
                {{{JoyLeft, 80}, {JoyUp, 160}, {JoyRight, 40}, {JoyA, 24}, {0, 8}}},
                {{{JoyUp, 100}, {JoyA, 24}, {JoyLeft, 100}, {JoyA, 24}, {JoyUp, 40}}},
            }};

            auto focus_base_owner = std::make_unique<Runtime>(trial);
            const Runtime& focus_base = *focus_base_owner;
            for (std::size_t strategy = 0; strategy < strategies.size(); ++strategy) {
                auto focused_owner = std::make_unique<Runtime>(focus_base);
                Runtime& focused = *focused_owner;
                bool abort = false;
                for (const FocusLeg& leg : strategies[strategy]) {
                    for (std::uint64_t f = 0; f < leg.frames; ++f) {
                        std::uint8_t buttons = leg.buttons;
                        if (leg.buttons == JoyA) {
                            buttons = (f % 12u) < 2u ? JoyA : 0;
                        }
                        const StepResult result =
                            advance_search_frame(focused, buttons);
                        if (result == StepResult::MissingBank) {
                            Renderer rr{};
                            rr.render(focused.memory(), true);
                            rr.write_bmp(output_dir /
                                ("search_focus_missing_" +
                                 std::to_string(seed) + "_" +
                                 std::to_string(strategy) + ".bmp"));
                            std::cout << "M7_SEARCH_FOCUS_MISSING_BANK seed=" << seed
                                      << " strategy=" << strategy
                                      << " bank=" << focused.cpu().missing_bank
                                      << " pc=0x" << std::hex << focused.cpu().pc
                                      << " screen=0x" << rr.hash()
                                      << std::dec << std::endl;
                            return 127;
                        }
                        if (result == StepResult::Trapped ||
                            result == StepResult::Stopped ||
                            result == StepResult::StepLimit) {
                            abort = true;
                            break;
                        }
                        if (focused.memory().read8(0xC5DB) != 1) {
                            Renderer rr{};
                            rr.render(focused.memory(), true);
                            rr.write_bmp(output_dir /
                                ("search_focus_mode_" +
                                 std::to_string(seed) + "_" +
                                 std::to_string(strategy) + ".bmp"));
                            std::cout << "M7_SEARCH_FOCUS_MODE_CHANGE seed=" << seed
                                      << " strategy=" << strategy
                                      << " C5DB="
                                      << static_cast<unsigned>(
                                             focused.memory().read8(0xC5DB))
                                      << " C5DC="
                                      << static_cast<unsigned>(
                                             focused.memory().read8(0xC5DC))
                                      << " screen=0x" << std::hex << rr.hash()
                                      << " map=0x" << tilemap_hash(focused.memory())
                                      << std::dec << std::endl;
                            return 0;
                        }
                    }
                    if (abort) break;
                }

                if (seed == 1 && strategy == 4) {
                    struct StoryApproach {
                        std::uint8_t first_button;
                        std::uint64_t first_frames;
                        std::uint8_t second_button;
                        std::uint64_t second_frames;
                    };
                    constexpr std::array<StoryApproach, 8> approaches = {{
                        {JoyLeft, 42, JoyUp, 14},
                        {JoyLeft, 48, JoyUp, 16},
                        {JoyLeft, 54, JoyUp, 18},
                        {JoyLeft, 42, JoyUp, 22},
                        {JoyLeft, 48, JoyUp, 24},
                        {JoyLeft, 54, JoyUp, 26},
                        {JoyUp, 16, JoyLeft, 48},
                        {JoyUp, 22, JoyLeft, 48},
                    }};

                    auto story_base_owner = std::make_unique<Runtime>(focused);
                    const Runtime& story_base = *story_base_owner;
                    const std::uint64_t base_save_hash =
                        sram_hash(story_base.memory());

                    for (std::size_t story = 0; story < approaches.size(); ++story) {
                        auto story_owner = std::make_unique<Runtime>(story_base);
                        Runtime& story_runtime = *story_owner;
                        const StoryApproach approach = approaches[story];

                        auto run_leg = [&](std::uint8_t buttons,
                                           std::uint64_t frames) -> StepResult {
                            for (std::uint64_t f = 0; f < frames; ++f) {
                                const StepResult result =
                                    advance_search_frame(story_runtime, buttons);
                                if (result != StepResult::Continue) return result;
                            }
                            return StepResult::Continue;
                        };

                        StepResult story_result =
                            run_leg(approach.first_button, approach.first_frames);
                        if (story_result == StepResult::Continue) {
                            story_result =
                                run_leg(approach.second_button, approach.second_frames);
                        }

                        bool saw_dialog = false;
                        bool dialog_closed = false;
                        std::uint64_t dialog_frames = 0;

                        if (story_result == StepResult::Continue) {
                            // Speak exactly once. Once C5DC indicates that the
                            // text system is active, pulse A only while it stays
                            // active and stop immediately after it closes. This
                            // avoids reopening the NPC forever.
                            constexpr std::uint64_t max_dialog_frames = 1200;
                            for (; dialog_frames < max_dialog_frames; ++dialog_frames) {
                                const std::uint8_t before_submode =
                                    story_runtime.memory().read8(0xC5DC);
                                if (saw_dialog && before_submode == 0) {
                                    dialog_closed = true;
                                    break;
                                }

                                std::uint8_t buttons = 0;
                                if (!saw_dialog) {
                                    if (dialog_frames < 2) buttons = JoyA;
                                } else if ((dialog_frames % 60u) < 2u) {
                                    buttons = JoyA;
                                }

                                story_result =
                                    advance_search_frame(story_runtime, buttons);
                                if (story_result != StepResult::Continue) break;

                                const std::uint8_t after_submode =
                                    story_runtime.memory().read8(0xC5DC);
                                if (after_submode != 0) saw_dialog = true;

                                if (story == 0 && saw_dialog &&
                                    (dialog_frames == 55 || dialog_frames == 115 ||
                                     dialog_frames == 175 || dialog_frames == 235 ||
                                     dialog_frames == 295 || dialog_frames == 355 ||
                                     dialog_frames == 415 || dialog_frames == 475 ||
                                     dialog_frames == 535)) {
                                    Renderer clue_renderer{};
                                    clue_renderer.render(story_runtime.memory(), true);
                                    clue_renderer.write_bmp(
                                        output_dir /
                                        ("search_story_dialog_" +
                                         std::to_string(dialog_frames) + ".bmp"));
                                    std::cout << "M7_SEARCH_STORY_DIALOG_CAPTURE frame="
                                              << dialog_frames
                                              << " C5DC="
                                              << static_cast<unsigned>(after_submode)
                                              << " screen=0x" << std::hex
                                              << clue_renderer.hash() << std::dec
                                              << std::endl;
                                }

                                if (saw_dialog && after_submode == 0) {
                                    dialog_closed = true;
                                    break;
                                }
                            }
                        }

                        if (story_result == StepResult::MissingBank) {
                            Renderer sr{};
                            sr.render(story_runtime.memory(), true);
                            sr.write_bmp(output_dir /
                                ("search_story_missing_" +
                                 std::to_string(story) + ".bmp"));
                            std::cout << "M7_SEARCH_STORY_MISSING_BANK route="
                                      << story
                                      << " bank=" << story_runtime.cpu().missing_bank
                                      << " pc=0x" << std::hex
                                      << story_runtime.cpu().pc
                                      << " screen=0x" << sr.hash()
                                      << std::dec << std::endl;
                            return 127;
                        }
                        if (story_result == StepResult::Trapped ||
                            story_result == StepResult::Stopped ||
                            story_result == StepResult::StepLimit) {
                            std::cout << "M7_SEARCH_STORY_ABORT route=" << story
                                      << " result="
                                      << static_cast<unsigned>(story_result)
                                      << std::endl;
                            continue;
                        }
                        if (story_runtime.memory().read8(0xC5DB) != 1) {
                            Renderer sr{};
                            sr.render(story_runtime.memory(), true);
                            sr.write_bmp(output_dir /
                                ("search_story_mode_" +
                                 std::to_string(story) + ".bmp"));
                            std::cout << "M7_SEARCH_STORY_MODE_CHANGE route="
                                      << story
                                      << " C5DB="
                                      << static_cast<unsigned>(
                                             story_runtime.memory().read8(0xC5DB))
                                      << " C5DC="
                                      << static_cast<unsigned>(
                                             story_runtime.memory().read8(0xC5DC))
                                      << " screen=0x" << std::hex << sr.hash()
                                      << " map=0x"
                                      << tilemap_hash(story_runtime.memory())
                                      << std::dec << std::endl;
                            return 0;
                        }

                        if (story == 0 && dialog_closed) {
                            // Pinned pure-D-pad path discovered by the physical
                            // navigation search. It exits the bedroom/house and
                            // reaches the outdoor area without any A presses.
                            constexpr std::array<std::uint8_t, 18>
                                outdoor_actions = {
                                    3,3,3,3,3,3,3,3,
                                    0,0,3,3,0,0,3,0,0,3
                                };
                            constexpr std::uint64_t kOutdoorScreenHash =
                                0x7e0ce91b1463de95ull;

                            auto outdoor =
                                std::make_unique<Runtime>(story_runtime);

                            auto apply_navigation =
                                [&](Runtime& runtime,
                                    std::uint8_t direction)
                                    -> StepResult {
                                constexpr std::uint64_t macro_frames =
                                    24;
                                constexpr std::array<std::uint8_t, 4>
                                    directions = {
                                        JoyRight, JoyLeft,
                                        JoyUp, JoyDown
                                    };
                                bool saw_lcd_off = false;
                                for (std::uint64_t phase = 0;
                                     phase < macro_frames; ++phase) {
                                    const std::uint8_t buttons =
                                        phase < 15
                                            ? directions[
                                                  direction & 3u]
                                            : 0;
                                    const StepResult result =
                                        advance_search_frame(
                                            runtime, buttons);
                                    if (result !=
                                        StepResult::Continue) {
                                        return result;
                                    }
                                    if ((runtime.memory().read8(
                                             0xFF40) & 0x80u) == 0) {
                                        saw_lcd_off = true;
                                    }
                                }

                                // A room/region transition can keep LCDC off
                                // longer than the movement macro. Do not hash
                                // partially rebuilt VRAM as a new region.
                                // Wait for the cartridge to turn the LCD back
                                // on, then give it a few idle frames to present
                                // the destination.
                                if (saw_lcd_off ||
                                    (runtime.memory().read8(
                                         0xFF40) & 0x80u) == 0) {
                                    bool lcd_back_on = false;
                                    for (std::uint64_t settle = 0;
                                         settle < 240; ++settle) {
                                        const StepResult result =
                                            advance_search_frame(
                                                runtime, 0);
                                        if (result !=
                                            StepResult::Continue) {
                                            return result;
                                        }
                                        if ((runtime.memory().read8(
                                                 0xFF40) & 0x80u) != 0) {
                                            lcd_back_on = true;
                                            for (unsigned idle = 0;
                                                 idle < 12; ++idle) {
                                                const StepResult idle_result =
                                                    advance_search_frame(
                                                        runtime, 0);
                                                if (idle_result !=
                                                    StepResult::Continue) {
                                                    return idle_result;
                                                }
                                            }
                                            break;
                                        }
                                    }
                                    if (!lcd_back_on) {
                                        return StepResult::StepLimit;
                                    }
                                }

                                runtime.memory().set_joypad_state(0);
                                (void)runtime.memory().apu()
                                    .take_samples();
                                return StepResult::Continue;
                            };

                            for (std::size_t i = 0;
                                 i < outdoor_actions.size(); ++i) {
                                const StepResult result =
                                    apply_navigation(
                                        *outdoor,
                                        outdoor_actions[i]);
                                if (result ==
                                    StepResult::MissingBank) {
                                    std::cout
                                        << "M7_SEARCH_OUTDOOR_MISSING_BANK index="
                                        << i
                                        << " bank="
                                        << outdoor->cpu().missing_bank
                                        << " pc=0x" << std::hex
                                        << outdoor->cpu().pc
                                        << std::dec << std::endl;
                                    return 127;
                                }
                                if (result !=
                                    StepResult::Continue) {
                                    std::cout
                                        << "M7_SEARCH_OUTDOOR_ABORT index="
                                        << i
                                        << " result="
                                        << static_cast<unsigned>(
                                               result)
                                        << std::endl;
                                    return 133;
                                }
                            }

                            Renderer region_renderer{};
                            region_renderer.render(
                                outdoor->memory(), true);
                            region_renderer.write_bmp(
                                output_dir /
                                "search_outdoor_start.bmp");
                            const std::uint64_t outdoor_region =
                                background_hash(outdoor->memory());

                            std::cout
                                << "M7_SEARCH_OUTDOOR screen=0x"
                                << std::hex
                                << region_renderer.hash()
                                << " expected=0x"
                                << kOutdoorScreenHash
                                << " region=0x"
                                << outdoor_region
                                << " scrollmap=0x"
                                << tilemap_hash(
                                       outdoor->memory())
                                << std::dec << std::endl;

                            if (region_renderer.hash() !=
                                kOutdoorScreenHash) {
                                std::cout
                                    << "M7_SEARCH_OUTDOOR_FAIL deterministic_hash"
                                    << std::endl;
                                return 134;
                            }

                            // The earlier physical-navigation artifact shows a
                            // second building west of the farm with Tara/Cobi
                            // aligned directly below its doorway. Probe that
                            // exact path first instead of spending minutes on
                            // a wide map search.
                            constexpr std::array<std::uint8_t, 11>
                                vault_building_path = {
                                    2,1,1,1,1,1,3,1,3,3,2
                                };
                            auto vault_door =
                                std::make_unique<Runtime>(*outdoor);
                            for (std::size_t i = 0;
                                 i < vault_building_path.size(); ++i) {
                                const StepResult result =
                                    apply_navigation(
                                        *vault_door,
                                        vault_building_path[i]);
                                if (result == StepResult::MissingBank) {
                                    std::cout
                                        << "M7_SEARCH_VAULT_DOOR_MISSING_BANK prefix="
                                        << i
                                        << " bank="
                                        << vault_door->cpu().missing_bank
                                        << " pc=0x" << std::hex
                                        << vault_door->cpu().pc
                                        << std::dec << std::endl;
                                    return 127;
                                }
                                if (result != StepResult::Continue) {
                                    std::cout
                                        << "M7_SEARCH_VAULT_DOOR_ABORT prefix="
                                        << i
                                        << " result="
                                        << static_cast<unsigned>(result)
                                        << std::endl;
                                    return 138;
                                }
                            }

                            Renderer vault_door_renderer{};
                            for (unsigned up_step = 0;
                                 up_step < 10; ++up_step) {
                                vault_door_renderer.render(
                                    vault_door->memory(), true);
                                vault_door_renderer.write_bmp(
                                    output_dir /
                                    ("search_vault_door_" +
                                     std::to_string(up_step) + ".bmp"));
                                std::cout
                                    << "M7_SEARCH_VAULT_DOOR step="
                                    << up_step
                                    << " screen=0x" << std::hex
                                    << vault_door_renderer.hash()
                                    << " bg=0x"
                                    << background_hash(
                                           vault_door->memory())
                                    << " scrollmap=0x"
                                    << tilemap_hash(
                                           vault_door->memory())
                                    << std::dec
                                    << " C5DB="
                                    << static_cast<unsigned>(
                                           vault_door->memory().read8(
                                               0xC5DB))
                                    << " C5DC="
                                    << static_cast<unsigned>(
                                           vault_door->memory().read8(
                                               0xC5DC))
                                    << " LCDC=0x" << std::hex
                                    << static_cast<unsigned>(
                                           vault_door->memory().read8(
                                               0xFF40))
                                    << std::dec << std::endl;

                                if (vault_door->memory().read8(
                                        0xC5DB) != 1) {
                                    std::cout
                                        << "M7_SEARCH_VAULT_DOOR_MODE_CHANGE step="
                                        << up_step << std::endl;
                                    return 0;
                                }

                                const StepResult result =
                                    apply_navigation(
                                        *vault_door, 2);
                                if (result == StepResult::MissingBank) {
                                    vault_door_renderer.render(
                                        vault_door->memory(), true);
                                    vault_door_renderer.write_bmp(
                                        output_dir /
                                        "search_vault_door_missing.bmp");
                                    std::cout
                                        << "M7_SEARCH_VAULT_DOOR_MISSING_BANK step="
                                        << up_step
                                        << " bank="
                                        << vault_door->cpu().missing_bank
                                        << " pc=0x" << std::hex
                                        << vault_door->cpu().pc
                                        << " screen=0x"
                                        << vault_door_renderer.hash()
                                        << std::dec << std::endl;
                                    return 127;
                                }
                                if (result != StepResult::Continue) {
                                    std::cout
                                        << "M7_SEARCH_VAULT_DOOR_ABORT step="
                                        << up_step
                                        << " result="
                                        << static_cast<unsigned>(result)
                                        << std::endl;
                                    return 138;
                                }
                            }

                            vault_door_renderer.render(
                                vault_door->memory(), true);
                            vault_door_renderer.write_bmp(
                                output_dir /
                                "search_vault_door_final.bmp");
                            std::cout
                                << "M7_SEARCH_VAULT_DOOR_PROBE_COMPLETE screen=0x"
                                << std::hex
                                << vault_door_renderer.hash()
                                << " bg=0x"
                                << background_hash(
                                       vault_door->memory())
                                << std::dec
                                << " C5DB="
                                << static_cast<unsigned>(
                                       vault_door->memory().read8(
                                           0xC5DB))
                                << " C5DC="
                                << static_cast<unsigned>(
                                       vault_door->memory().read8(
                                           0xC5DC))
                                << std::endl;

                            const std::uint64_t npc_sram_before =
                                sram_hash(vault_door->memory());
                            bool npc_dialog_seen = false;
                            bool npc_dialog_closed = false;
                            constexpr std::array<std::uint64_t, 7>
                                npc_capture_frames = {
                                    30, 90, 150, 240, 360, 480, 600
                                };

                            for (std::uint64_t frame = 0;
                                 frame < 1400; ++frame) {
                                const std::uint8_t before_submode =
                                    vault_door->memory().read8(0xC5DC);
                                if (npc_dialog_seen &&
                                    before_submode == 0) {
                                    npc_dialog_closed = true;
                                    break;
                                }

                                std::uint8_t buttons = 0;
                                if (!npc_dialog_seen) {
                                    if (frame < 2 ||
                                        (frame >= 120 &&
                                         (frame % 120u) < 2u)) {
                                        buttons = JoyA;
                                    }
                                } else if ((frame % 60u) < 2u) {
                                    buttons = JoyA;
                                }

                                const StepResult result =
                                    advance_search_frame(
                                        *vault_door, buttons);
                                if (result ==
                                    StepResult::MissingBank) {
                                    vault_door_renderer.render(
                                        vault_door->memory(), true);
                                    vault_door_renderer.write_bmp(
                                        output_dir /
                                        "search_vault_npc_missing.bmp");
                                    std::cout
                                        << "M7_SEARCH_VAULT_NPC_MISSING_BANK frame="
                                        << frame
                                        << " bank="
                                        << vault_door->cpu().missing_bank
                                        << " pc=0x" << std::hex
                                        << vault_door->cpu().pc
                                        << " screen=0x"
                                        << vault_door_renderer.hash()
                                        << std::dec << std::endl;
                                    return 127;
                                }
                                if (result == StepResult::Trapped ||
                                    result == StepResult::Stopped ||
                                    result == StepResult::StepLimit) {
                                    std::cout
                                        << "M7_SEARCH_VAULT_NPC_ABORT frame="
                                        << frame
                                        << " result="
                                        << static_cast<unsigned>(result)
                                        << std::endl;
                                    return 139;
                                }

                                const std::uint8_t mode =
                                    vault_door->memory().read8(0xC5DB);
                                const std::uint8_t submode =
                                    vault_door->memory().read8(0xC5DC);
                                if (submode != 0) {
                                    npc_dialog_seen = true;
                                }

                                if (npc_dialog_seen &&
                                    std::find(
                                        npc_capture_frames.begin(),
                                        npc_capture_frames.end(),
                                        frame) !=
                                        npc_capture_frames.end()) {
                                    vault_door_renderer.render(
                                        vault_door->memory(), true);
                                    vault_door_renderer.write_bmp(
                                        output_dir /
                                        ("search_vault_npc_text_" +
                                         std::to_string(frame) +
                                         ".bmp"));
                                    std::cout
                                        << "M7_SEARCH_VAULT_NPC_TEXT frame="
                                        << frame
                                        << " C5DB="
                                        << static_cast<unsigned>(mode)
                                        << " C5DC="
                                        << static_cast<unsigned>(submode)
                                        << " screen=0x" << std::hex
                                        << vault_door_renderer.hash()
                                        << std::dec << std::endl;
                                }

                                if (mode != 1) {
                                    vault_door_renderer.render(
                                        vault_door->memory(), true);
                                    vault_door_renderer.write_bmp(
                                        output_dir /
                                        "search_vault_npc_mode.bmp");
                                    std::cout
                                        << "M7_SEARCH_VAULT_NPC_MODE_CHANGE frame="
                                        << frame
                                        << " C5DB="
                                        << static_cast<unsigned>(mode)
                                        << " C5DC="
                                        << static_cast<unsigned>(submode)
                                        << " screen=0x" << std::hex
                                        << vault_door_renderer.hash()
                                        << " sram=0x"
                                        << sram_hash(
                                               vault_door->memory())
                                        << std::dec << std::endl;
                                    return 0;
                                }

                                if (npc_dialog_seen &&
                                    submode == 0) {
                                    npc_dialog_closed = true;
                                    break;
                                }
                            }

                            vault_door->memory().set_joypad_state(0);
                            vault_door_renderer.render(
                                vault_door->memory(), true);
                            vault_door_renderer.write_bmp(
                                output_dir /
                                "search_vault_npc_after.bmp");
                            const std::uint64_t npc_sram_after =
                                sram_hash(vault_door->memory());
                            std::cout
                                << "M7_SEARCH_VAULT_NPC_COMPLETE seen="
                                << (npc_dialog_seen ? 1 : 0)
                                << " closed="
                                << (npc_dialog_closed ? 1 : 0)
                                << " screen=0x" << std::hex
                                << vault_door_renderer.hash()
                                << " sram_before=0x"
                                << npc_sram_before
                                << " sram_after=0x"
                                << npc_sram_after
                                << std::dec
                                << " sram_changed="
                                << (npc_sram_before !=
                                    npc_sram_after ? 1 : 0)
                                << " C5DB="
                                << static_cast<unsigned>(
                                       vault_door->memory().read8(
                                           0xC5DB))
                                << " C5DC="
                                << static_cast<unsigned>(
                                       vault_door->memory().read8(
                                           0xC5DC))
                                << std::endl;

                            if (!npc_dialog_seen ||
                                !npc_dialog_closed) {
                                return 139;
                            }

                            // The in-ROM guide has now explicitly said:
                            // "Go to the Vault" / "The Vault is west".
                            // Leave this building through the south exit, then
                            // probe the west route with pure D-pad input.
                            constexpr unsigned guide_exit_steps = 12;
                            for (unsigned step = 0;
                                 step < guide_exit_steps; ++step) {
                                const StepResult result =
                                    apply_navigation(*vault_door, 3);
                                if (result ==
                                    StepResult::MissingBank) {
                                    std::cout
                                        << "M7_SEARCH_GUIDE_EXIT_MISSING_BANK step="
                                        << step
                                        << " bank="
                                        << vault_door->cpu().missing_bank
                                        << " pc=0x" << std::hex
                                        << vault_door->cpu().pc
                                        << std::dec << std::endl;
                                    return 127;
                                }
                                if (result !=
                                    StepResult::Continue) {
                                    std::cout
                                        << "M7_SEARCH_GUIDE_EXIT_ABORT step="
                                        << step
                                        << " result="
                                        << static_cast<unsigned>(result)
                                        << std::endl;
                                    return 140;
                                }
                                vault_door_renderer.render(
                                    vault_door->memory(), true);
                                if (step < 4 ||
                                    step + 1 ==
                                        guide_exit_steps ||
                                    (step % 2u) == 1u) {
                                    vault_door_renderer.write_bmp(
                                        output_dir /
                                        ("search_guide_exit_" +
                                         std::to_string(step) +
                                         ".bmp"));
                                }
                                std::cout
                                    << "M7_SEARCH_GUIDE_EXIT step="
                                    << step
                                    << " screen=0x" << std::hex
                                    << vault_door_renderer.hash()
                                    << " bg=0x"
                                    << background_hash(
                                           vault_door->memory())
                                    << " map=0x"
                                    << tilemap_hash(
                                           vault_door->memory())
                                    << std::dec
                                    << " C5DB="
                                    << static_cast<unsigned>(
                                           vault_door->memory().read8(
                                               0xC5DB))
                                    << " C5DC="
                                    << static_cast<unsigned>(
                                           vault_door->memory().read8(
                                               0xC5DC))
                                    << std::endl;
                                if (vault_door->memory().read8(
                                        0xC5DB) != 1) {
                                    std::cout
                                        << "M7_SEARCH_GUIDE_EXIT_MODE_CHANGE"
                                        << std::endl;
                                    return 0;
                                }
                            }

                            // The south exit reaches a compact island with
                            // a circular hatch/stone feature in the middle.
                            // Direct west movement is blocked by the surrounding
                            // trees, so try a small deterministic set of
                            // P1-only approaches around the ring and interact
                            // only after reaching the feature.
                            struct VaultApproach {
                                std::array<std::uint8_t, 10> moves;
                                std::size_t count;
                            };
                            constexpr std::array<VaultApproach, 8>
                                vault_approaches = {{
                                    {{{3,3,1,1,3,3,0,0,2,0}}, 9},
                                    {{{3,3,0,0,3,3,1,1,2,0}}, 9},
                                    {{{1,1,3,3,3,0,0,2,0,0}}, 8},
                                    {{{0,0,3,3,3,1,1,2,0,0}}, 8},
                                    {{{3,1,1,3,3,0,0,3,2,0}}, 9},
                                    {{{3,0,0,3,3,1,1,3,2,0}}, 9},
                                    {{{1,3,3,0,0,3,1,2,0,0}}, 8},
                                    {{{0,3,3,1,1,3,0,2,0,0}}, 8}
                                }};

                            const Runtime island_seed = *vault_door;
                            const std::uint64_t island_bg =
                                background_hash(
                                    island_seed.memory());
                            std::cout
                                << "M7_SEARCH_VAULT_ISLAND seed_bg=0x"
                                << std::hex << island_bg
                                << " screen=0x"
                                << vault_door_renderer.hash()
                                << std::dec << std::endl;

                            // The exhaustive probe found the shortest real
                            // island interaction at D,L,D. Preserve the
                            // resulting post-dialogue game state instead of
                            // discarding it: this NPC may gate the central
                            // Vault object through WRAM story state.
                            auto island_story =
                                std::make_unique<Runtime>(
                                    island_seed);
                            constexpr std::array<
                                std::uint8_t, 3>
                                island_story_path = {
                                    3, 1, 3
                                };
                            for (std::size_t i = 0;
                                 i < island_story_path.size();
                                 ++i) {
                                const StepResult result =
                                    apply_navigation(
                                        *island_story,
                                        island_story_path[i]);
                                if (result ==
                                    StepResult::MissingBank) {
                                    std::cout
                                        << "M7_SEARCH_ISLAND_NPC_MISSING_BANK move="
                                        << i
                                        << " bank="
                                        << island_story->cpu()
                                               .missing_bank
                                        << " pc=0x"
                                        << std::hex
                                        << island_story->cpu().pc
                                        << std::dec
                                        << std::endl;
                                    return 127;
                                }
                                if (result !=
                                    StepResult::Continue) {
                                    return 143;
                                }
                            }

                            const std::uint64_t
                                island_story_wram_before =
                                    wram_hash(
                                        island_story->memory());
                            const std::uint64_t
                                island_story_sram_before =
                                    sram_hash(
                                        island_story->memory());

                            std::array<std::uint8_t, 0x2000>
                                island_visible_wram_before{};
                            for (std::size_t i = 0;
                                 i < island_visible_wram_before.size();
                                 ++i) {
                                island_visible_wram_before[i] =
                                    island_story->memory().read8(
                                        static_cast<std::uint16_t>(
                                            0xC000u + i));
                            }
                            std::array<std::uint8_t, 0x7F>
                                island_hram_before{};
                            for (std::size_t i = 0;
                                 i < island_hram_before.size();
                                 ++i) {
                                island_hram_before[i] =
                                    island_story->memory().read8(
                                        static_cast<std::uint16_t>(
                                            0xFF80u + i));
                            }

                            const Runtime island_story_control_seed =
                                *island_story;
                            std::uint64_t island_dialog_elapsed_frames = 0;

                            constexpr std::array<std::uint16_t, 14>
                                island_watch_addresses = {
                                    0xC529, 0xC531, 0xC533, 0xC534,
                                    0xC537, 0xC538, 0xC54F, 0xC554,
                                    0xC555, 0xC556, 0xC5D7, 0xC5E7,
                                    0xC5E8, 0xC5F0
                                };
                            std::array<std::uint8_t,
                                       island_watch_addresses.size()>
                                island_watch_values{};
                            for (std::size_t i = 0;
                                 i < island_watch_addresses.size();
                                 ++i) {
                                island_watch_values[i] =
                                    island_story->memory().read8(
                                        island_watch_addresses[i]);
                            }

                            bool island_dialog_seen = false;
                            bool island_dialog_closed = false;
                            unsigned island_dialog_page = 0;
                            std::uint64_t next_page_press = 96;

                            for (std::uint64_t frame = 0;
                                 frame < 1200; ++frame) {
                                island_dialog_elapsed_frames = frame + 1;
                                const std::uint8_t
                                    before_submode =
                                        island_story->memory()
                                            .read8(0xC5DC);
                                if (island_dialog_seen &&
                                    before_submode == 0) {
                                    island_dialog_closed =
                                        true;
                                    break;
                                }

                                std::uint8_t buttons = 0;
                                if (!island_dialog_seen) {
                                    if (frame < 2) {
                                        buttons = JoyA;
                                    }
                                } else if (frame ==
                                           next_page_press) {
                                    buttons = JoyA;
                                }

                                StepResult result =
                                    StepResult::Continue;

                                if (!island_dialog_seen &&
                                    frame == 0 &&
                                    buttons == JoyA) {
                                    // Trace the first real interaction edge at
                                    // instruction granularity before the script
                                    // settles into HALT. Keep only ROMX PCs and
                                    // deduplicate them so CI output remains
                                    // compact.
                                    auto& trace_memory =
                                        island_story->memory();
                                    trace_memory.set_joypad_state(
                                        buttons);
                                    const std::uint64_t
                                        trace_start_frame =
                                            trace_memory.frame_counter();
                                    std::unordered_set<std::uint64_t>
                                        trace_seen;
                                    unsigned trace_lines = 0;
                                    constexpr std::size_t
                                        trace_step_limit = 2'000'000;

                                    for (std::size_t trace_step = 0;
                                         trace_step <
                                             trace_step_limit;
                                         ++trace_step) {
                                        const std::uint16_t
                                            before_pc =
                                                island_story->cpu().pc;
                                        const std::uint16_t
                                            before_bank =
                                                trace_memory
                                                    .current_rom_bank();
                                        const bool before_halted =
                                            island_story->cpu().halted;

                                        result =
                                            island_story->step();

                                        if (!before_halted &&
                                            before_pc >= 0x4000 &&
                                            before_pc < 0x8000) {
                                            const std::uint64_t key =
                                                (static_cast<
                                                     std::uint64_t>(
                                                     before_bank)
                                                 << 16) |
                                                before_pc;
                                            if (trace_seen.insert(
                                                    key).second &&
                                                trace_lines < 256) {
                                                std::cout
                                                    << "M7_SEARCH_ISLAND_ROMX_TRACE step="
                                                    << trace_step
                                                    << " bank="
                                                    << before_bank
                                                    << " pc=0x"
                                                    << std::hex
                                                    << before_pc
                                                    << std::dec
                                                    << " sp=0x"
                                                    << std::hex
                                                    << island_story
                                                           ->cpu().sp
                                                    << std::dec
                                                    << std::endl;
                                                ++trace_lines;
                                            }
                                        }

                                        if (result ==
                                                StepResult::MissingBank ||
                                            result ==
                                                StepResult::Trapped ||
                                            result ==
                                                StepResult::Stopped) {
                                            break;
                                        }
                                        if (trace_memory.frame_counter() !=
                                            trace_start_frame) {
                                            result =
                                                StepResult::Continue;
                                            break;
                                        }
                                    }

                                    std::cout
                                        << "M7_SEARCH_ISLAND_ROMX_TRACE_COMPLETE unique="
                                        << trace_seen.size()
                                        << " printed="
                                        << trace_lines
                                        << " end_bank="
                                        << trace_memory
                                               .current_rom_bank()
                                        << " end_pc=0x"
                                        << std::hex
                                        << island_story->cpu().pc
                                        << std::dec
                                        << " halted="
                                        << (island_story->cpu().halted
                                                ? 1
                                                : 0)
                                        << std::endl;
                                } else {
                                    result =
                                        advance_search_frame(
                                            *island_story,
                                            buttons);
                                }
                                if (result ==
                                    StepResult::MissingBank) {
                                    std::cout
                                        << "M7_SEARCH_ISLAND_NPC_MISSING_BANK frame="
                                        << frame
                                        << " bank="
                                        << island_story->cpu()
                                               .missing_bank
                                        << " pc=0x"
                                        << std::hex
                                        << island_story->cpu().pc
                                        << std::dec
                                        << std::endl;
                                    return 127;
                                }
                                if (result ==
                                        StepResult::Trapped ||
                                    result ==
                                        StepResult::Stopped ||
                                    result ==
                                        StepResult::StepLimit) {
                                    break;
                                }

                                for (std::size_t watch = 0;
                                     watch < island_watch_addresses.size();
                                     ++watch) {
                                    const std::uint8_t value =
                                        island_story->memory().read8(
                                            island_watch_addresses[watch]);
                                    if (value !=
                                        island_watch_values[watch]) {
                                        std::cout
                                            << "M7_SEARCH_ISLAND_WATCH frame="
                                            << frame
                                            << " addr=0x" << std::hex
                                            << island_watch_addresses[watch]
                                            << " before=0x"
                                            << static_cast<unsigned>(
                                                   island_watch_values[watch])
                                            << " after=0x"
                                            << static_cast<unsigned>(value)
                                            << " pc=0x"
                                            << island_story->cpu().pc
                                            << std::dec
                                            << " bank="
                                            << island_story->memory()
                                                   .current_rom_bank()
                                            << " C5DC="
                                            << static_cast<unsigned>(
                                                   island_story->memory()
                                                       .read8(0xC5DC))
                                            << std::endl;
                                        island_watch_values[watch] =
                                            value;
                                    }
                                }

                                const std::uint8_t submode =
                                    island_story->memory()
                                        .read8(0xC5DC);
                                if (submode != 0 &&
                                    !island_dialog_seen) {
                                    island_dialog_seen = true;
                                    next_page_press =
                                        frame + 96;
                                }

                                if (island_dialog_seen &&
                                    submode != 0 &&
                                    frame + 1 ==
                                        next_page_press) {
                                    vault_door_renderer.render(
                                        island_story->memory(),
                                        true);
                                    vault_door_renderer.write_bmp(
                                        output_dir /
                                        ("search_island_npc_page_" +
                                         std::to_string(
                                             island_dialog_page) +
                                         ".bmp"));
                                    std::cout
                                        << "M7_SEARCH_ISLAND_NPC_PAGE page="
                                        << island_dialog_page
                                        << " frame=" << frame
                                        << " screen=0x"
                                        << std::hex
                                        << vault_door_renderer.hash()
                                        << std::dec
                                        << " C5DC="
                                        << static_cast<unsigned>(
                                               submode)
                                        << std::endl;
                                    ++island_dialog_page;
                                }

                                if (buttons == JoyA &&
                                    island_dialog_seen) {
                                    next_page_press =
                                        frame + 96;
                                }
                            }

                            island_story->memory()
                                .set_joypad_state(0);
                            vault_door_renderer.render(
                                island_story->memory(), true);
                            vault_door_renderer.write_bmp(
                                output_dir /
                                "search_island_npc_after.bmp");

                            const std::uint64_t
                                island_story_wram_after =
                                    wram_hash(
                                        island_story->memory());
                            const std::uint64_t
                                island_story_sram_after =
                                    sram_hash(
                                        island_story->memory());

                            std::cout
                                << "M7_SEARCH_ISLAND_NPC_COMPLETE seen="
                                << (island_dialog_seen ? 1 : 0)
                                << " closed="
                                << (island_dialog_closed ? 1 : 0)
                                << " wram_before=0x"
                                << std::hex
                                << island_story_wram_before
                                << " wram_after=0x"
                                << island_story_wram_after
                                << " sram_before=0x"
                                << island_story_sram_before
                                << " sram_after=0x"
                                << island_story_sram_after
                                << " screen=0x"
                                << vault_door_renderer.hash()
                                << std::dec
                                << std::endl;

                            auto island_control =
                                std::make_unique<Runtime>(
                                    island_story_control_seed);
                            for (std::uint64_t frame = 0;
                                 frame < island_dialog_elapsed_frames;
                                 ++frame) {
                                const StepResult control_result =
                                    advance_search_frame(
                                        *island_control, 0);
                                if (control_result !=
                                    StepResult::Continue) {
                                    std::cout
                                        << "M7_SEARCH_ISLAND_CONTROL_ABORT frame="
                                        << frame
                                        << " result="
                                        << static_cast<unsigned>(
                                               control_result)
                                        << std::endl;
                                    break;
                                }
                            }
                            island_control->memory()
                                .set_joypad_state(0);

                            unsigned island_wram_change_count = 0;
                            for (std::size_t i = 0;
                                 i < island_visible_wram_before.size();
                                 ++i) {
                                const std::uint16_t address =
                                    static_cast<std::uint16_t>(
                                        0xC000u + i);
                                const std::uint8_t after =
                                    island_story->memory().read8(
                                        address);
                                const std::uint8_t control_after =
                                    island_control->memory().read8(
                                        address);
                                if (after == control_after) {
                                    continue;
                                }
                                if (island_wram_change_count < 96) {
                                    std::cout
                                        << "M7_SEARCH_ISLAND_WRAM_CHANGE addr=0x"
                                        << std::hex
                                        << (0xC000u + i)
                                        << " control=0x"
                                        << static_cast<unsigned>(
                                               control_after)
                                        << " interaction=0x"
                                        << static_cast<unsigned>(after)
                                        << std::dec << std::endl;
                                }
                                ++island_wram_change_count;
                            }

                            unsigned island_high_wram_change_count = 0;
                            for (std::size_t i = 0x400;
                                 i < island_visible_wram_before.size();
                                 ++i) {
                                const std::uint16_t address =
                                    static_cast<std::uint16_t>(
                                        0xC000u + i);
                                const std::uint8_t interaction =
                                    island_story->memory().read8(
                                        address);
                                const std::uint8_t control =
                                    island_control->memory().read8(
                                        address);
                                if (interaction == control) {
                                    continue;
                                }
                                if (island_high_wram_change_count < 96) {
                                    std::cout
                                        << "M7_SEARCH_ISLAND_HIGH_WRAM_CHANGE addr=0x"
                                        << std::hex << address
                                        << " control=0x"
                                        << static_cast<unsigned>(
                                               control)
                                        << " interaction=0x"
                                        << static_cast<unsigned>(
                                               interaction)
                                        << std::dec << std::endl;
                                }
                                ++island_high_wram_change_count;
                            }

                            unsigned island_hram_change_count = 0;
                            for (std::size_t i = 0;
                                 i < island_hram_before.size();
                                 ++i) {
                                const std::uint16_t address =
                                    static_cast<std::uint16_t>(
                                        0xFF80u + i);
                                const std::uint8_t after =
                                    island_story->memory().read8(
                                        address);
                                const std::uint8_t control_after =
                                    island_control->memory().read8(
                                        address);
                                if (after == control_after) {
                                    continue;
                                }
                                if (island_hram_change_count < 32) {
                                    std::cout
                                        << "M7_SEARCH_ISLAND_HRAM_CHANGE addr=0x"
                                        << std::hex
                                        << (0xFF80u + i)
                                        << " control=0x"
                                        << static_cast<unsigned>(
                                               control_after)
                                        << " interaction=0x"
                                        << static_cast<unsigned>(after)
                                        << std::dec << std::endl;
                                }
                                ++island_hram_change_count;
                            }

                            const std::uint64_t
                                island_control_sram =
                                    sram_hash(
                                        island_control->memory());
                            std::cout
                                << "M7_SEARCH_ISLAND_STATE_DIFF frames="
                                << island_dialog_elapsed_frames
                                << " wram_changes="
                                << island_wram_change_count
                                << " high_wram_changes="
                                << island_high_wram_change_count
                                << " hram_changes="
                                << island_hram_change_count
                                << " interaction_sram=0x"
                                << std::hex
                                << island_story_sram_after
                                << " control_sram=0x"
                                << island_control_sram
                                << std::dec
                                << " sram_diff="
                                << (island_story_sram_after !=
                                            island_control_sram
                                        ? 1
                                        : 0)
                                << std::endl;

                            if (!island_dialog_seen ||
                                !island_dialog_closed) {
                                return 144;
                            }

                            const Runtime island_progress_seed =
                                *island_story;

                            struct KeyActivator {
                                std::uint8_t buttons;
                                const char* name;
                            };
                            constexpr std::array<KeyActivator, 7>
                                key_activators = {{
                                    {JoyStart, "start"},
                                    {JoySelect, "select"},
                                    {JoyA, "a"},
                                    {JoyB, "b"},
                                    {static_cast<std::uint8_t>(
                                         JoyStart | JoySelect),
                                     "start_select"},
                                    {static_cast<std::uint8_t>(
                                         JoyA | JoyB),
                                     "a_b"},
                                    {static_cast<std::uint8_t>(
                                         JoyStart | JoyA),
                                     "start_a"}
                                }};

                            for (const KeyActivator& activator :
                                 key_activators) {
                                auto candidate =
                                    std::make_unique<Runtime>(
                                        island_progress_seed);
                                const std::uint64_t before_wram =
                                    wram_hash(
                                        candidate->memory());
                                for (unsigned frame = 0;
                                     frame < 72; ++frame) {
                                    const std::uint8_t buttons =
                                        frame < 2
                                            ? activator.buttons
                                            : 0;
                                    const StepResult result =
                                        advance_search_frame(
                                            *candidate,
                                            buttons);
                                    if (result ==
                                        StepResult::MissingBank) {
                                        std::cout
                                            << "M7_SEARCH_KEY_ACTIVATOR_MISSING_BANK name="
                                            << activator.name
                                            << " bank="
                                            << candidate->cpu()
                                                   .missing_bank
                                            << " pc=0x"
                                            << std::hex
                                            << candidate->cpu().pc
                                            << std::dec
                                            << std::endl;
                                        return 127;
                                    }
                                    if (result !=
                                        StepResult::Continue) {
                                        break;
                                    }
                                }

                                vault_door_renderer.render(
                                    candidate->memory(), true);
                                vault_door_renderer.write_bmp(
                                    output_dir /
                                    (std::string(
                                         "search_key_activator_") +
                                     activator.name + ".bmp"));
                                std::cout
                                    << "M7_SEARCH_KEY_ACTIVATOR name="
                                    << activator.name
                                    << " buttons=0x"
                                    << std::hex
                                    << static_cast<unsigned>(
                                           activator.buttons)
                                    << " screen=0x"
                                    << vault_door_renderer.hash()
                                    << " bg=0x"
                                    << background_hash(
                                           candidate->memory())
                                    << " map=0x"
                                    << tilemap_hash(
                                           candidate->memory())
                                    << " wram_before=0x"
                                    << before_wram
                                    << " wram_after=0x"
                                    << wram_hash(
                                           candidate->memory())
                                    << std::dec
                                    << " C5DB="
                                    << static_cast<unsigned>(
                                           candidate->memory()
                                               .read8(0xC5DB))
                                    << " C5DC="
                                    << static_cast<unsigned>(
                                           candidate->memory()
                                               .read8(0xC5DC))
                                    << std::endl;
                            }

                            for (std::size_t candidate = 0;
                                 candidate <
                                     vault_approaches.size();
                                 ++candidate) {
                                auto approach =
                                    std::make_unique<Runtime>(
                                        island_progress_seed);
                                bool abort_candidate = false;

                                for (std::size_t move = 0;
                                     move <
                                         vault_approaches[
                                             candidate].count;
                                     ++move) {
                                    const StepResult result =
                                        apply_navigation(
                                            *approach,
                                            vault_approaches[
                                                candidate]
                                                .moves[move]);
                                    if (result ==
                                        StepResult::MissingBank) {
                                        std::cout
                                            << "M7_SEARCH_VAULT_HATCH_MISSING_BANK candidate="
                                            << candidate
                                            << " move=" << move
                                            << " bank="
                                            << approach->cpu()
                                                   .missing_bank
                                            << " pc=0x"
                                            << std::hex
                                            << approach->cpu().pc
                                            << std::dec
                                            << std::endl;
                                        return 127;
                                    }
                                    if (result !=
                                        StepResult::Continue) {
                                        std::cout
                                            << "M7_SEARCH_VAULT_HATCH_ABORT candidate="
                                            << candidate
                                            << " move=" << move
                                            << " result="
                                            << static_cast<unsigned>(
                                                   result)
                                            << std::endl;
                                        abort_candidate =
                                            true;
                                        break;
                                    }
                                    if (approach->memory()
                                            .read8(0xC5DB) !=
                                        1) {
                                        vault_door_renderer
                                            .render(
                                                approach
                                                    ->memory(),
                                                true);
                                        vault_door_renderer
                                            .write_bmp(
                                                output_dir /
                                                ("search_vault_hatch_mode_" +
                                                 std::to_string(
                                                     candidate) +
                                                 ".bmp"));
                                        std::cout
                                            << "M7_SEARCH_VAULT_HATCH_MODE_CHANGE candidate="
                                            << candidate
                                            << " move=" << move
                                            << " C5DB="
                                            << static_cast<
                                                   unsigned>(
                                                   approach
                                                       ->memory()
                                                       .read8(
                                                           0xC5DB))
                                            << " C5DC="
                                            << static_cast<
                                                   unsigned>(
                                                   approach
                                                       ->memory()
                                                       .read8(
                                                           0xC5DC))
                                            << std::endl;
                                        return 0;
                                    }
                                }
                                if (abort_candidate) {
                                    continue;
                                }

                                vault_door_renderer.render(
                                    approach->memory(), true);
                                vault_door_renderer
                                    .write_bmp(
                                        output_dir /
                                        ("search_vault_hatch_pos_" +
                                         std::to_string(
                                             candidate) +
                                         ".bmp"));
                                const std::uint64_t before =
                                    sram_hash(
                                        approach->memory());

                                if (candidate == 4) {
                                    struct PortalActivator {
                                        std::uint8_t buttons;
                                        const char* name;
                                    };
                                    constexpr std::array<
                                        PortalActivator, 6>
                                        portal_activators = {{
                                            {JoyStart, "start"},
                                            {JoySelect, "select"},
                                            {JoyA, "a"},
                                            {JoyB, "b"},
                                            {static_cast<std::uint8_t>(
                                                 JoyStart | JoySelect),
                                             "start_select"},
                                            {static_cast<std::uint8_t>(
                                                 JoyA | JoyB),
                                             "a_b"}
                                        }};

                                    for (const PortalActivator& pa :
                                         portal_activators) {
                                        auto portal_test =
                                            std::make_unique<Runtime>(
                                                *approach);
                                        const std::uint64_t
                                            portal_wram_before =
                                                wram_hash(
                                                    portal_test
                                                        ->memory());
                                        const std::uint64_t
                                            portal_sram_before =
                                                sram_hash(
                                                    portal_test
                                                        ->memory());

                                        for (unsigned f = 0;
                                             f < 96; ++f) {
                                            const std::uint8_t
                                                buttons =
                                                    f < 2
                                                        ? pa.buttons
                                                        : 0;
                                            const StepResult result =
                                                advance_search_frame(
                                                    *portal_test,
                                                    buttons);
                                            if (result ==
                                                StepResult::MissingBank) {
                                                std::cout
                                                    << "M7_SEARCH_PORTAL_ACTIVATOR_MISSING_BANK name="
                                                    << pa.name
                                                    << " bank="
                                                    << portal_test
                                                           ->cpu()
                                                           .missing_bank
                                                    << " pc=0x"
                                                    << std::hex
                                                    << portal_test
                                                           ->cpu().pc
                                                    << std::dec
                                                    << std::endl;
                                                return 127;
                                            }
                                            if (result !=
                                                StepResult::Continue) {
                                                break;
                                            }
                                        }

                                        vault_door_renderer.render(
                                            portal_test->memory(),
                                            true);
                                        vault_door_renderer.write_bmp(
                                            output_dir /
                                            (std::string(
                                                 "search_portal_activator_") +
                                             pa.name + ".bmp"));

                                        std::cout
                                            << "M7_SEARCH_PORTAL_ACTIVATOR name="
                                            << pa.name
                                            << " screen=0x"
                                            << std::hex
                                            << vault_door_renderer
                                                   .hash()
                                            << " bg=0x"
                                            << background_hash(
                                                   portal_test
                                                       ->memory())
                                            << " map=0x"
                                            << tilemap_hash(
                                                   portal_test
                                                       ->memory())
                                            << " wram_before=0x"
                                            << portal_wram_before
                                            << " wram_after=0x"
                                            << wram_hash(
                                                   portal_test
                                                       ->memory())
                                            << " sram_before=0x"
                                            << portal_sram_before
                                            << " sram_after=0x"
                                            << sram_hash(
                                                   portal_test
                                                       ->memory())
                                            << std::dec
                                            << " C5DB="
                                            << static_cast<unsigned>(
                                                   portal_test
                                                       ->memory()
                                                       .read8(
                                                           0xC5DB))
                                            << " C5DC="
                                            << static_cast<unsigned>(
                                                   portal_test
                                                       ->memory()
                                                       .read8(
                                                           0xC5DC))
                                            << std::endl;
                                    }
                                }

                                bool interaction_seen =
                                    false;
                                bool interaction_closed =
                                    false;
                                for (std::uint64_t frame = 0;
                                     frame < 900; ++frame) {
                                    const std::uint8_t
                                        before_submode =
                                            approach->memory()
                                                .read8(
                                                    0xC5DC);
                                    if (interaction_seen &&
                                        before_submode == 0) {
                                        interaction_closed =
                                            true;
                                        break;
                                    }

                                    std::uint8_t buttons =
                                        0;
                                    if (!interaction_seen) {
                                        if (frame < 2 ||
                                            (frame >= 120 &&
                                             (frame %
                                                  120u) <
                                                 2u)) {
                                            buttons = JoyA;
                                        }
                                    } else if (
                                        (frame % 60u) <
                                        2u) {
                                        buttons = JoyA;
                                    }

                                    const StepResult result =
                                        advance_search_frame(
                                            *approach,
                                            buttons);
                                    if (result ==
                                        StepResult::MissingBank) {
                                        vault_door_renderer
                                            .render(
                                                approach
                                                    ->memory(),
                                                true);
                                        vault_door_renderer
                                            .write_bmp(
                                                output_dir /
                                                "search_vault_hatch_missing.bmp");
                                        std::cout
                                            << "M7_SEARCH_VAULT_HATCH_MISSING_BANK candidate="
                                            << candidate
                                            << " frame="
                                            << frame
                                            << " bank="
                                            << approach->cpu()
                                                   .missing_bank
                                            << " pc=0x"
                                            << std::hex
                                            << approach->cpu().pc
                                            << " screen=0x"
                                            << vault_door_renderer
                                                   .hash()
                                            << std::dec
                                            << std::endl;
                                        return 127;
                                    }
                                    if (result ==
                                            StepResult::Trapped ||
                                        result ==
                                            StepResult::Stopped ||
                                        result ==
                                            StepResult::StepLimit) {
                                        break;
                                    }

                                    const std::uint8_t mode =
                                        approach->memory()
                                            .read8(0xC5DB);
                                    const std::uint8_t
                                        submode =
                                            approach->memory()
                                                .read8(
                                                    0xC5DC);
                                    if (submode != 0) {
                                        interaction_seen =
                                            true;
                                    }

                                    if (interaction_seen &&
                                        (frame == 30 ||
                                         frame == 90 ||
                                         frame == 150 ||
                                         frame == 240)) {
                                        vault_door_renderer
                                            .render(
                                                approach
                                                    ->memory(),
                                                true);
                                        vault_door_renderer
                                            .write_bmp(
                                                output_dir /
                                                ("search_vault_hatch_text_" +
                                                 std::to_string(
                                                     candidate) +
                                                 "_" +
                                                 std::to_string(
                                                     frame) +
                                                 ".bmp"));
                                    }

                                    if (mode != 1) {
                                        vault_door_renderer
                                            .render(
                                                approach
                                                    ->memory(),
                                                true);
                                        vault_door_renderer
                                            .write_bmp(
                                                output_dir /
                                                ("search_vault_hatch_mode_" +
                                                 std::to_string(
                                                     candidate) +
                                                 ".bmp"));
                                        std::cout
                                            << "M7_SEARCH_VAULT_HATCH_MODE_CHANGE candidate="
                                            << candidate
                                            << " frame="
                                            << frame
                                            << " C5DB="
                                            << static_cast<
                                                   unsigned>(
                                                   mode)
                                            << " C5DC="
                                            << static_cast<
                                                   unsigned>(
                                                   submode)
                                            << " screen=0x"
                                            << std::hex
                                            << vault_door_renderer
                                                   .hash()
                                            << " sram=0x"
                                            << sram_hash(
                                                   approach
                                                       ->memory())
                                            << std::dec
                                            << std::endl;
                                        return 0;
                                    }

                                    if (interaction_seen &&
                                        submode == 0) {
                                        interaction_closed =
                                            true;
                                        break;
                                    }
                                }

                                approach->memory()
                                    .set_joypad_state(0);
                                vault_door_renderer.render(
                                    approach->memory(), true);
                                vault_door_renderer
                                    .write_bmp(
                                        output_dir /
                                        ("search_vault_hatch_after_" +
                                         std::to_string(
                                             candidate) +
                                         ".bmp"));
                                const std::uint64_t after =
                                    sram_hash(
                                        approach->memory());
                                std::cout
                                    << "M7_SEARCH_VAULT_HATCH candidate="
                                    << candidate
                                    << " seen="
                                    << (interaction_seen
                                            ? 1
                                            : 0)
                                    << " closed="
                                    << (interaction_closed
                                            ? 1
                                            : 0)
                                    << " screen=0x"
                                    << std::hex
                                    << vault_door_renderer
                                           .hash()
                                    << " bg=0x"
                                    << background_hash(
                                           approach
                                               ->memory())
                                    << " sram_before=0x"
                                    << before
                                    << " sram_after=0x"
                                    << after
                                    << std::dec
                                    << " changed="
                                    << (before != after
                                            ? 1
                                            : 0)
                                    << " C5DB="
                                    << static_cast<
                                           unsigned>(
                                           approach
                                               ->memory()
                                               .read8(0xC5DB))
                                    << " C5DC="
                                    << static_cast<
                                           unsigned>(
                                           approach
                                               ->memory()
                                               .read8(0xC5DC))
                                    << std::endl;
                            }

                            std::cout
                                << "M7_SEARCH_VAULT_HATCH_NO_TRIGGER candidates="
                                << vault_approaches.size()
                                << std::endl;

                            struct IslandNode {
                                std::unique_ptr<Runtime> runtime;
                                std::vector<std::uint8_t> path;
                                std::uint64_t screen = 0;
                                std::uint64_t position = 0;
                                std::uint64_t oam = 0;
                            };

                            auto island_oam_hash =
                                [](const Memory& memory) {
                                    std::uint64_t hash =
                                        1469598103934665603ull;
                                    for (std::uint32_t address =
                                             0xFE00;
                                         address < 0xFEA0;
                                         ++address) {
                                        hash ^= memory.read8(
                                            static_cast<std::uint16_t>(
                                                address));
                                        hash *=
                                            1099511628211ull;
                                    }
                                    return hash;
                                };

                            std::vector<IslandNode>
                                island_frontier;
                            {
                                auto root =
                                    std::make_unique<Runtime>(
                                        island_progress_seed);
                                vault_door_renderer.render(
                                    root->memory(), true);
                                island_frontier.push_back({
                                    std::move(root),
                                    {},
                                    vault_door_renderer.hash(),
                                    tilemap_hash(
                                        island_progress_seed.memory()),
                                    island_oam_hash(
                                        island_progress_seed.memory())
                                });
                            }

                            std::unordered_set<std::uint64_t>
                                island_seen;
                            {
                                std::uint64_t sig =
                                    island_frontier.front()
                                        .screen;
                                sig ^= island_frontier.front()
                                           .position +
                                    0x9E3779B97F4A7C15ull +
                                    (sig << 6) +
                                    (sig >> 2);
                                sig ^= island_frontier.front()
                                           .oam +
                                    0x9E3779B97F4A7C15ull +
                                    (sig << 6) +
                                    (sig >> 2);
                                island_seen.insert(sig);
                            }

                            constexpr std::size_t
                                island_depth = 28;
                            constexpr std::size_t
                                island_state_limit = 256;
                            constexpr std::array<
                                std::uint8_t, 4>
                                island_actions = {
                                    0, 1, 2, 3
                                };
                            constexpr std::uint64_t
                                kGuideExteriorBg =
                                    0x2c4791b344ab1745ull;

                            std::size_t island_states = 1;
                            unsigned interaction_capture = 0;

                            for (std::size_t depth = 0;
                                 depth < island_depth &&
                                 !island_frontier.empty();
                                 ++depth) {
                                std::vector<IslandNode> next;

                                for (const IslandNode& node :
                                     island_frontier) {
                                    // Probe A from every unique physical
                                    // state. This is kept in a clone so a
                                    // failed interaction cannot perturb
                                    // navigation discovery.
                                    auto probe =
                                        std::make_unique<Runtime>(
                                            *node.runtime);
                                    const std::uint64_t
                                        probe_sram_before =
                                            sram_hash(
                                                probe->memory());
                                    const std::uint64_t
                                        probe_wram_before =
                                            wram_hash(
                                                probe->memory());
                                    const std::uint64_t
                                        probe_bg_before =
                                            background_hash(
                                                probe->memory());

                                    bool interaction_seen =
                                        false;
                                    bool interaction_closed =
                                        false;
                                    bool probe_abort = false;
                                    bool interaction_page_captured =
                                        false;
                                    std::uint64_t interaction_page_hash =
                                        0;

                                    for (std::uint64_t frame = 0;
                                         frame <
                                             (interaction_seen
                                                  ? 720u
                                                  : 48u);
                                         ++frame) {
                                        const std::uint8_t
                                            submode_before =
                                                probe->memory()
                                                    .read8(
                                                        0xC5DC);
                                        if (interaction_seen &&
                                            submode_before == 0) {
                                            interaction_closed =
                                                true;
                                            break;
                                        }

                                        std::uint8_t buttons = 0;
                                        if (!interaction_seen) {
                                            if (frame < 2) {
                                                buttons = JoyA;
                                            }
                                        } else if (
                                            (frame % 60u) <
                                            2u) {
                                            buttons = JoyA;
                                        }

                                        const StepResult result =
                                            advance_search_frame(
                                                *probe,
                                                buttons);
                                        if (result ==
                                            StepResult::MissingBank) {
                                            vault_door_renderer
                                                .render(
                                                    probe->memory(),
                                                    true);
                                            vault_door_renderer
                                                .write_bmp(
                                                    output_dir /
                                                    "search_vault_interact_missing.bmp");
                                            std::cout
                                                << "M7_SEARCH_VAULT_INTERACT_MISSING_BANK depth="
                                                << depth
                                                << " bank="
                                                << probe->cpu()
                                                       .missing_bank
                                                << " pc=0x"
                                                << std::hex
                                                << probe->cpu().pc
                                                << std::dec;
                                            print_search_path(
                                                node.path);
                                            std::cout
                                                << std::endl;
                                            return 127;
                                        }
                                        if (result ==
                                                StepResult::Trapped ||
                                            result ==
                                                StepResult::Stopped ||
                                            result ==
                                                StepResult::StepLimit) {
                                            probe_abort = true;
                                            break;
                                        }

                                        const std::uint8_t
                                            mode =
                                                probe->memory()
                                                    .read8(
                                                        0xC5DB);
                                        const std::uint8_t
                                            submode =
                                                probe->memory()
                                                    .read8(
                                                        0xC5DC);
                                        if (submode != 0) {
                                            interaction_seen =
                                                true;
                                            if (!interaction_page_captured) {
                                                // Capture the first active
                                                // text/object page before the
                                                // automatic A pulses close it.
                                                for (unsigned settle = 0;
                                                     settle < 24;
                                                     ++settle) {
                                                    const StepResult settle_result =
                                                        advance_search_frame(
                                                            *probe, 0);
                                                    if (settle_result !=
                                                        StepResult::Continue) {
                                                        break;
                                                    }
                                                }
                                                vault_door_renderer.render(
                                                    probe->memory(), true);
                                                interaction_page_hash =
                                                    vault_door_renderer.hash();
                                                if (interaction_capture < 32) {
                                                    vault_door_renderer
                                                        .write_bmp(
                                                            output_dir /
                                                            ("search_vault_interact_page_" +
                                                             std::to_string(
                                                                 interaction_capture) +
                                                             ".bmp"));
                                                }
                                                std::cout
                                                    << "M7_SEARCH_VAULT_INTERACT_PAGE depth="
                                                    << depth
                                                    << " capture="
                                                    << interaction_capture
                                                    << " screen=0x"
                                                    << std::hex
                                                    << interaction_page_hash
                                                    << " bg=0x"
                                                    << background_hash(
                                                           probe->memory())
                                                    << std::dec;
                                                print_search_path(
                                                    node.path);
                                                std::cout
                                                    << std::endl;
                                                interaction_page_captured =
                                                    true;
                                            }
                                        }

                                        if (mode != 1) {
                                            vault_door_renderer
                                                .render(
                                                    probe->memory(),
                                                    true);
                                            vault_door_renderer
                                                .write_bmp(
                                                    output_dir /
                                                    "search_vault_interact_mode.bmp");
                                            std::cout
                                                << "M7_SEARCH_VAULT_INTERACT_MODE_CHANGE depth="
                                                << depth
                                                << " C5DB="
                                                << static_cast<
                                                       unsigned>(
                                                       mode)
                                                << " C5DC="
                                                << static_cast<
                                                       unsigned>(
                                                       submode)
                                                << " screen=0x"
                                                << std::hex
                                                << vault_door_renderer
                                                       .hash()
                                                << " bg=0x"
                                                << background_hash(
                                                       probe
                                                           ->memory())
                                                << " sram=0x"
                                                << sram_hash(
                                                       probe
                                                           ->memory())
                                                << std::dec;
                                            print_search_path(
                                                node.path);
                                            std::cout
                                                << std::endl;
                                            return 0;
                                        }
                                    }

                                    probe->memory()
                                        .set_joypad_state(0);

                                    if (!probe_abort) {
                                        const std::uint64_t
                                            probe_sram_after =
                                                sram_hash(
                                                    probe->memory());
                                        const std::uint64_t
                                            probe_wram_after =
                                                wram_hash(
                                                    probe->memory());
                                        const std::uint64_t
                                            probe_bg_after =
                                                background_hash(
                                                    probe->memory());

                                        if (probe_bg_after !=
                                                probe_bg_before &&
                                            probe_bg_after !=
                                                kGuideExteriorBg) {
                                            vault_door_renderer
                                                .render(
                                                    probe->memory(),
                                                    true);
                                            vault_door_renderer
                                                .write_bmp(
                                                    output_dir /
                                                    "search_vault_interact_exit.bmp");
                                            std::cout
                                                << "M7_SEARCH_VAULT_INTERACT_EXIT depth="
                                                << depth
                                                << " screen=0x"
                                                << std::hex
                                                << vault_door_renderer
                                                       .hash()
                                                << " bg_before=0x"
                                                << probe_bg_before
                                                << " bg_after=0x"
                                                << probe_bg_after
                                                << " sram=0x"
                                                << probe_sram_after
                                                << std::dec;
                                            print_search_path(
                                                node.path);
                                            std::cout
                                                << std::endl;
                                            return 0;
                                        }

                                        if (interaction_seen ||
                                            probe_sram_after !=
                                                probe_sram_before) {
                                            vault_door_renderer
                                                .render(
                                                    probe->memory(),
                                                    true);
                                            if (interaction_capture <
                                                24) {
                                                vault_door_renderer
                                                    .write_bmp(
                                                        output_dir /
                                                        ("search_vault_interact_" +
                                                         std::to_string(
                                                             interaction_capture) +
                                                         ".bmp"));
                                            }
                                            std::cout
                                                << "M7_SEARCH_VAULT_INTERACT depth="
                                                << depth
                                                << " capture="
                                                << interaction_capture
                                                << " seen="
                                                << (interaction_seen
                                                        ? 1
                                                        : 0)
                                                << " closed="
                                                << (interaction_closed
                                                        ? 1
                                                        : 0)
                                                << " screen=0x"
                                                << std::hex
                                                << vault_door_renderer
                                                       .hash()
                                                << " bg=0x"
                                                << probe_bg_after
                                                << " sram_before=0x"
                                                << probe_sram_before
                                                << " sram_after=0x"
                                                << probe_sram_after
                                                << " wram_before=0x"
                                                << probe_wram_before
                                                << " wram_after=0x"
                                                << probe_wram_after
                                                << " page=0x"
                                                << interaction_page_hash
                                                << std::dec;
                                            print_search_path(
                                                node.path);
                                            std::cout
                                                << std::endl;
                                            ++interaction_capture;

                                            if (probe_sram_after !=
                                                probe_sram_before) {
                                                return 0;
                                            }
                                        }
                                    }

                                    for (const std::uint8_t action :
                                         island_actions) {
                                        if (island_states >=
                                            island_state_limit) {
                                            break;
                                        }

                                        auto child =
                                            std::make_unique<
                                                Runtime>(
                                                *node.runtime);
                                        const StepResult result =
                                            apply_navigation(
                                                *child,
                                                action);
                                        if (result ==
                                            StepResult::MissingBank) {
                                            std::cout
                                                << "M7_SEARCH_VAULT_ISLAND_MISSING_BANK depth="
                                                << depth
                                                << " bank="
                                                << child->cpu()
                                                       .missing_bank
                                                << " pc=0x"
                                                << std::hex
                                                << child->cpu().pc
                                                << std::dec;
                                            std::vector<
                                                std::uint8_t>
                                                path =
                                                    node.path;
                                            path.push_back(
                                                action);
                                            print_search_path(
                                                path);
                                            std::cout
                                                << std::endl;
                                            return 127;
                                        }
                                        if (result !=
                                            StepResult::Continue) {
                                            continue;
                                        }

                                        vault_door_renderer
                                            .render(
                                                child->memory(),
                                                true);
                                        const std::uint64_t
                                            screen =
                                                vault_door_renderer
                                                    .hash();
                                        const std::uint64_t bg =
                                            background_hash(
                                                child->memory());
                                        const std::uint64_t
                                            position =
                                                tilemap_hash(
                                                    child->memory());
                                        const std::uint64_t oam =
                                            island_oam_hash(
                                                child->memory());

                                        std::vector<
                                            std::uint8_t>
                                            path = node.path;
                                        path.push_back(action);

                                        if (child->memory()
                                                .read8(0xC5DB) !=
                                            1) {
                                            vault_door_renderer
                                                .write_bmp(
                                                    output_dir /
                                                    "search_vault_island_mode.bmp");
                                            std::cout
                                                << "M7_SEARCH_VAULT_ISLAND_MODE_CHANGE depth="
                                                << depth
                                                << " C5DB="
                                                << static_cast<
                                                       unsigned>(
                                                       child
                                                           ->memory()
                                                           .read8(
                                                               0xC5DB))
                                                << " C5DC="
                                                << static_cast<
                                                       unsigned>(
                                                       child
                                                           ->memory()
                                                           .read8(
                                                               0xC5DC))
                                                << " screen=0x"
                                                << std::hex
                                                << screen
                                                << " bg=0x"
                                                << bg
                                                << std::dec;
                                            print_search_path(
                                                path);
                                            std::cout
                                                << std::endl;
                                            return 0;
                                        }

                                        if (bg ==
                                            kGuideExteriorBg) {
                                            continue;
                                        }
                                        if (bg != island_bg &&
                                            screen !=
                                                0xb423319be6530b83ull) {
                                            vault_door_renderer
                                                .write_bmp(
                                                    output_dir /
                                                    "search_vault_island_exit.bmp");
                                            std::cout
                                                << "M7_SEARCH_VAULT_ISLAND_EXIT depth="
                                                << depth
                                                << " screen=0x"
                                                << std::hex
                                                << screen
                                                << " bg=0x"
                                                << bg
                                                << " map=0x"
                                                << position
                                                << std::dec;
                                            print_search_path(
                                                path);
                                            std::cout
                                                << std::endl;
                                            return 142;
                                        }

                                        std::uint64_t sig =
                                            screen;
                                        sig ^= position +
                                            0x9E3779B97F4A7C15ull +
                                            (sig << 6) +
                                            (sig >> 2);
                                        sig ^= oam +
                                            0x9E3779B97F4A7C15ull +
                                            (sig << 6) +
                                            (sig >> 2);
                                        if (!island_seen
                                                 .insert(sig)
                                                 .second) {
                                            continue;
                                        }

                                        ++island_states;
                                        next.push_back({
                                            std::move(child),
                                            std::move(path),
                                            screen,
                                            position,
                                            oam
                                        });
                                    }
                                }

                                if (!next.empty() &&
                                    (depth % 4u) == 0u) {
                                    std::cout
                                        << "M7_SEARCH_VAULT_GRID depth="
                                        << depth
                                        << " frontier="
                                        << next.size()
                                        << " states="
                                        << island_states
                                        << " interactions="
                                        << interaction_capture
                                        << std::endl;
                                }
                                island_frontier =
                                    std::move(next);

                                if (island_states >=
                                    island_state_limit) {
                                    break;
                                }
                            }

                            std::cout
                                << "M7_SEARCH_VAULT_GRID_COMPLETE states="
                                << island_states
                                << " interactions="
                                << interaction_capture
                                << std::endl;
                            return 141;

                            auto oam_hash = [](const Memory& memory) {
                                std::uint64_t hash =
                                    1469598103934665603ull;
                                for (std::uint32_t address = 0xFE00;
                                     address < 0xFEA0; ++address) {
                                    hash ^= memory.read8(
                                        static_cast<std::uint16_t>(
                                            address));
                                    hash *= 1099511628211ull;
                                }
                                return hash;
                            };

                            struct RegionNode {
                                std::unique_ptr<Runtime> runtime;
                                std::vector<std::uint8_t> path;
                                std::uint64_t score = 0;
                                std::uint64_t region = 0;
                                std::uint64_t position = 0;
                                std::uint64_t oam = 0;
                            };

                            std::vector<RegionNode> frontier;
                            frontier.push_back({
                                std::move(outdoor),
                                {},
                                0,
                                outdoor_region,
                                0,
                                0
                            });
                            frontier.front().position =
                                tilemap_hash(
                                    frontier.front()
                                        .runtime->memory());
                            frontier.front().oam =
                                oam_hash(
                                    frontier.front()
                                        .runtime->memory());

                            std::unordered_set<std::uint64_t>
                                seen_states;
                            std::unordered_set<std::uint64_t>
                                seen_regions;
                            seen_regions.insert(outdoor_region);
                            unsigned region_capture = 0;

                            constexpr std::array<std::uint8_t, 4>
                                region_actions = {1, 3, 2, 0};
                            constexpr std::size_t region_width = 48;
                            constexpr std::size_t region_depth = 72;

                            for (std::size_t depth = 0;
                                 depth < region_depth &&
                                 !frontier.empty(); ++depth) {
                                std::vector<RegionNode> next;
                                next.reserve(
                                    frontier.size() *
                                    region_actions.size());

                                for (const RegionNode& node :
                                     frontier) {
                                    for (const std::uint8_t action :
                                         region_actions) {
                                        auto child =
                                            std::make_unique<Runtime>(
                                                *node.runtime);
                                        const StepResult result =
                                            apply_navigation(
                                                *child, action);

                                        if (result ==
                                            StepResult::MissingBank) {
                                            region_renderer.render(
                                                child->memory(), true);
                                            region_renderer.write_bmp(
                                                output_dir /
                                                "search_region_missing.bmp");
                                            std::cout
                                                << "M7_SEARCH_REGION_MISSING_BANK depth="
                                                << depth
                                                << " action="
                                                << search_action_name(
                                                       action)
                                                << " bank="
                                                << child->cpu()
                                                       .missing_bank
                                                << " pc=0x"
                                                << std::hex
                                                << child->cpu().pc
                                                << " screen=0x"
                                                << region_renderer.hash()
                                                << std::dec;
                                            print_search_path(
                                                node.path);
                                            std::cout
                                                << std::endl;
                                            return 127;
                                        }
                                        if (result ==
                                                StepResult::Trapped ||
                                            result ==
                                                StepResult::Stopped ||
                                            result ==
                                                StepResult::StepLimit) {
                                            continue;
                                        }

                                        const std::uint8_t mode =
                                            child->memory().read8(
                                                0xC5DB);
                                        const std::uint8_t submode =
                                            child->memory().read8(
                                                0xC5DC);
                                        const std::uint64_t region =
                                            background_hash(
                                                child->memory());
                                        const std::uint64_t position =
                                            tilemap_hash(
                                                child->memory());
                                        const std::uint64_t oam =
                                            oam_hash(
                                                child->memory());

                                        std::vector<std::uint8_t>
                                            path = node.path;
                                        path.push_back(action);

                                        if (mode != 1) {
                                            region_renderer.render(
                                                child->memory(), true);
                                            region_renderer.write_bmp(
                                                output_dir /
                                                "search_region_mode.bmp");
                                            std::cout
                                                << "M7_SEARCH_REGION_MODE_CHANGE depth="
                                                << depth
                                                << " C5DB="
                                                << static_cast<unsigned>(
                                                       mode)
                                                << " C5DC="
                                                << static_cast<unsigned>(
                                                       submode)
                                                << " screen=0x"
                                                << std::hex
                                                << region_renderer.hash()
                                                << " region=0x"
                                                << region
                                                << std::dec;
                                            print_search_path(
                                                path);
                                            std::cout
                                                << std::endl;
                                            return 0;
                                        }

                                        std::uint64_t signature =
                                            region;
                                        signature ^= position +
                                            0x9E3779B97F4A7C15ull +
                                            (signature << 6) +
                                            (signature >> 2);
                                        signature ^= oam +
                                            0x9E3779B97F4A7C15ull +
                                            (signature << 6) +
                                            (signature >> 2);
                                        if (!seen_states.insert(
                                                 signature).second) {
                                            continue;
                                        }

                                        const bool new_region =
                                            seen_regions.insert(
                                                region).second;
                                        std::uint64_t score = 0;
                                        if (new_region) {
                                            score +=
                                                1'000'000'000'000ull;
                                            if (region_capture < 32) {
                                                region_renderer.render(
                                                    child->memory(),
                                                    true);
                                                region_renderer.write_bmp(
                                                    output_dir /
                                                    ("search_region_" +
                                                     std::to_string(
                                                         region_capture) +
                                                     ".bmp"));
                                                std::cout
                                                    << "M7_SEARCH_REGION_NEW capture="
                                                    << region_capture
                                                    << " depth="
                                                    << depth
                                                    << " screen=0x"
                                                    << std::hex
                                                    << region_renderer.hash()
                                                    << " region=0x"
                                                    << region
                                                    << " scrollmap=0x"
                                                    << position
                                                    << std::dec;
                                                print_search_path(
                                                    path);
                                                std::cout
                                                    << std::endl;
                                                ++region_capture;
                                            }
                                        }

                                        // Follow the ROM hint "The Vault is
                                        // west", but keep enough alternatives
                                        // to route around collisions.
                                        if (action == 1) {
                                            score +=
                                                30'000'000ull;
                                        } else if (
                                            action == 3) {
                                            score +=
                                                8'000'000ull;
                                        } else if (
                                            action == 2) {
                                            score +=
                                                4'000'000ull;
                                        }

                                        next.push_back({
                                            std::move(child),
                                            std::move(path),
                                            score,
                                            region,
                                            position,
                                            oam
                                        });
                                    }
                                }

                                std::stable_sort(
                                    next.begin(), next.end(),
                                    [](const RegionNode& a,
                                       const RegionNode& b) {
                                        if (a.score != b.score) {
                                            return a.score >
                                                   b.score;
                                        }
                                        if (a.region != b.region) {
                                            return a.region <
                                                   b.region;
                                        }
                                        return a.position <
                                               b.position;
                                    });
                                if (next.size() > region_width) {
                                    next.resize(region_width);
                                }

                                if (!next.empty() &&
                                    (depth % 8u) == 0u) {
                                    std::cout
                                        << "M7_SEARCH_REGION depth="
                                        << depth
                                        << " frontier="
                                        << next.size()
                                        << " regions="
                                        << seen_regions.size()
                                        << " best_region=0x"
                                        << std::hex
                                        << next.front().region
                                        << std::dec;
                                    print_search_path(
                                        next.front().path);
                                    std::cout << std::endl;
                                }
                                frontier =
                                    std::move(next);
                            }

                            for (std::size_t i = 0;
                                 i < frontier.size() &&
                                 i < 8; ++i) {
                                region_renderer.render(
                                    frontier[i].runtime->memory(),
                                    true);
                                region_renderer.write_bmp(
                                    output_dir /
                                    ("search_region_final_" +
                                     std::to_string(i) +
                                     ".bmp"));
                                std::cout
                                    << "M7_SEARCH_REGION_FINAL index="
                                    << i
                                    << " screen=0x"
                                    << std::hex
                                    << region_renderer.hash()
                                    << " region=0x"
                                    << frontier[i].region
                                    << " scrollmap=0x"
                                    << frontier[i].position
                                    << std::dec;
                                print_search_path(
                                    frontier[i].path);
                                std::cout << std::endl;
                            }
                        }

                        Renderer sr{};
                        sr.render(story_runtime.memory(), true);
                        sr.write_bmp(output_dir /
                            ("search_story_" + std::to_string(story) + ".bmp"));
                        const std::uint64_t save_hash =
                            sram_hash(story_runtime.memory());
                        std::cout << "M7_SEARCH_STORY_COMPLETE route=" << story
                                  << " saw_dialog=" << (saw_dialog ? 1 : 0)
                                  << " dialog_closed=" << (dialog_closed ? 1 : 0)
                                  << " dialog_frames=" << dialog_frames
                                  << " screen=0x" << std::hex << sr.hash()
                                  << " map=0x" << tilemap_hash(story_runtime.memory())
                                  << " sram=0x" << save_hash
                                  << " sram_changed="
                                  << (save_hash != base_save_hash ? 1 : 0)
                                  << std::dec
                                  << " C5DB="
                                  << static_cast<unsigned>(
                                         story_runtime.memory().read8(0xC5DB))
                                  << " C5DC="
                                  << static_cast<unsigned>(
                                         story_runtime.memory().read8(0xC5DC))
                                  << std::endl;
                    }
                }

                Renderer rr{};
                rr.render(focused.memory(), true);
                rr.write_bmp(output_dir /
                    ("search_focus_" + std::to_string(seed) + "_" +
                     std::to_string(strategy) + ".bmp"));
                std::cout << "M7_SEARCH_FOCUS_COMPLETE seed=" << seed
                          << " strategy=" << strategy
                          << " screen=0x" << std::hex << rr.hash()
                          << " map=0x" << tilemap_hash(focused.memory())
                          << " sram=0x" << sram_hash(focused.memory())
                          << std::dec
                          << " C5DB="
                          << static_cast<unsigned>(focused.memory().read8(0xC5DB))
                          << " C5DC="
                          << static_cast<unsigned>(focused.memory().read8(0xC5DC))
                          << std::endl;
            }
        }
        std::cout << "M7_SEARCH_TRIAL_COMPLETE seed=" << seed
                  << " screen=0x" << std::hex << trial_renderer.hash()
                  << " map=0x" << tilemap_hash(trial.memory())
                  << " sram=0x" << sram_hash(trial.memory())
                  << std::dec
                  << " C5DB="
                  << static_cast<unsigned>(trial.memory().read8(0xC5DB))
                  << " C5DC="
                  << static_cast<unsigned>(trial.memory().read8(0xC5DC))
                  << std::endl;
    }

    std::cout << "M7_SEARCH_NO_MODE_CHANGE trials=" << trial_count
              << " frames_per_trial=" << frames_per_trial << std::endl;
    return 129;
}

int run_m7_audio_probe() {
    Runtime runtime{};
    Renderer renderer{};
    auto& memory = runtime.memory();

    std::uint64_t observed_frame = memory.frame_counter();
    unsigned stable_title = 0;
    constexpr std::size_t max_steps = 80'000'000;

    for (std::size_t step = 0; step < max_steps; ++step) {
        const StepResult result = runtime.step();
        if (result == StepResult::MissingBank ||
            result == StepResult::Trapped ||
            result == StepResult::Stopped) {
            std::cout << "M7_AUDIO_FAIL runtime_result="
                      << static_cast<unsigned>(result)
                      << " bank=" << runtime.cpu().missing_bank
                      << " pc=0x" << std::hex << runtime.cpu().pc << std::dec << "\n";
            return 100;
        }
        if (memory.frame_counter() == observed_frame) continue;
        observed_frame = memory.frame_counter();
        renderer.render(memory, true);
        if (renderer.hash() == kM5TitleHash &&
            memory.read8(0xC5DB) == 5 &&
            memory.read8(0xC5DC) == 0) {
            ++stable_title;
        } else {
            stable_title = 0;
        }
        if (stable_title >= 30) break;
    }

    if (stable_title < 30) {
        std::cout << "M7_AUDIO_FAIL retained_title\n";
        return 101;
    }

    const auto samples = memory.apu().take_samples();
    std::uint64_t hash = 1469598103934665603ull;
    std::uint64_t nonzero = 0;
    int peak = 0;
    for (const std::int16_t sample : samples) {
        const std::uint16_t bits = static_cast<std::uint16_t>(sample);
        hash ^= static_cast<std::uint8_t>(bits & 0xFFu);
        hash *= 1099511628211ull;
        hash ^= static_cast<std::uint8_t>(bits >> 8);
        hash *= 1099511628211ull;
        if (sample != 0) ++nonzero;
        const int magnitude =
            sample < 0 ? -static_cast<int>(sample) : static_cast<int>(sample);
        if (magnitude > peak) peak = magnitude;
    }

    std::cout << "M7_AUDIO_RESULT sample_values=" << samples.size()
              << " stereo_frames=" << (samples.size() / 2)
              << " nonzero=" << nonzero
              << " peak=" << peak
              << " hash=0x" << std::hex << hash
              << " NR50=0x" << static_cast<unsigned>(memory.read8(0xFF24))
              << " NR51=0x" << static_cast<unsigned>(memory.read8(0xFF25))
              << " NR52=0x" << static_cast<unsigned>(memory.read8(0xFF26))
              << std::dec << "\n";

    constexpr std::uint64_t kExpectedAudioHash = 0x03b50ed7ed79bda0ull;
    if (samples.size() != 2138926u ||
        nonzero != 1074861u ||
        peak != 19200 ||
        hash != kExpectedAudioHash) {
        std::cout << "M7_AUDIO_FAIL deterministic_pcm_mismatch"
                  << " expected_hash=0x" << std::hex << kExpectedAudioHash
                  << std::dec << "\n";
        return 102;
    }

    std::cout << "M7_AUDIO_PASS original_game_apu_writes_produced_deterministic_pcm\n";
    return 0;
}

} // namespace dwm2t
