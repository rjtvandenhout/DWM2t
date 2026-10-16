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
    Runtime base{};
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
    if (stable_title < 30) return 121;

    for (std::uint64_t relative = 0; relative < 1800; ++relative) {
        const StepResult result =
            advance_search_frame(base, m6_story_buttons(relative));
        if (result != StepResult::Continue) return 122;
    }
    for (std::uint64_t i = 0; i < 36; ++i) {
        const StepResult result =
            advance_search_frame(base, i < 24 ? JoyRight : 0);
        if (result != StepResult::Continue) return 123;
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
        if (result != StepResult::Continue) return 125;
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
    constexpr std::uint32_t trial_count = 8;

    for (std::uint32_t seed = 0; seed < trial_count; ++seed) {
        Runtime trial = base;
        Renderer trial_renderer{};
        std::uint64_t last_save = sram_hash(trial.memory());

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

            const Runtime focus_base = trial;
            for (std::size_t strategy = 0; strategy < strategies.size(); ++strategy) {
                Runtime focused = focus_base;
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
