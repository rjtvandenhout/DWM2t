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

    constexpr std::size_t beam_width = 10;
    constexpr std::size_t max_depth = 36;
    std::vector<SearchNode> beam;
    SearchNode initial{};
    initial.runtime = std::move(base);
    initial.screen_hash = renderer.hash();
    initial.map_hash = tilemap_hash(initial.runtime.memory());
    initial.save_hash = sram_hash(initial.runtime.memory());
    beam.push_back(std::move(initial));

    std::unordered_set<std::uint64_t> seen;
    seen.insert(beam.front().map_hash ^ (beam.front().save_hash << 1));

    for (std::size_t depth = 0; depth < max_depth; ++depth) {
        std::vector<SearchNode> candidates;
        candidates.reserve(beam_width * 6);

        for (const SearchNode& parent : beam) {
            for (std::uint8_t action = 0; action < 6; ++action) {
                SearchNode child{};
                child.runtime = parent.runtime;
                child.path = parent.path;
                child.path.push_back(action);

                const StepResult result = apply_search_action(child.runtime, action);
                Renderer child_renderer{};
                child_renderer.render(child.runtime.memory(), true);

                if (result == StepResult::MissingBank) {
                    child_renderer.write_bmp(output_dir / "search_missing_bank.bmp");
                    std::cout << "M7_SEARCH_MISSING_BANK bank="
                              << child.runtime.cpu().missing_bank
                              << " pc=0x" << std::hex << child.runtime.cpu().pc
                              << " screen=0x" << child_renderer.hash() << std::dec
                              << " depth=" << (depth + 1);
                    print_search_path(child.path);
                    std::cout << "\n";
                    return 127;
                }
                if (result == StepResult::Trapped ||
                    result == StepResult::Stopped ||
                    result == StepResult::StepLimit) {
                    continue;
                }

                const std::uint8_t mode = child.runtime.memory().read8(0xC5DB);
                const std::uint8_t submode = child.runtime.memory().read8(0xC5DC);
                child.screen_hash = child_renderer.hash();
                child.map_hash = tilemap_hash(child.runtime.memory());
                child.save_hash = sram_hash(child.runtime.memory());

                if (mode != 1) {
                    child_renderer.write_bmp(output_dir / "search_mode_change.bmp");
                    std::cout << "M7_SEARCH_MODE_CHANGE C5DB="
                              << static_cast<unsigned>(mode)
                              << " C5DC=" << static_cast<unsigned>(submode)
                              << " screen=0x" << std::hex << child.screen_hash
                              << " map=0x" << child.map_hash
                              << " sram=0x" << child.save_hash << std::dec
                              << " depth=" << (depth + 1);
                    print_search_path(child.path);
                    std::cout << "\n";
                    return 0;
                }

                const bool save_changed = child.save_hash != parent.save_hash;
                const bool map_changed = child.map_hash != parent.map_hash;
                const bool screen_changed = child.screen_hash != parent.screen_hash;
                const std::uint64_t signature =
                    child.map_hash ^ (child.save_hash << 1) ^
                    (static_cast<std::uint64_t>(submode) << 56);
                const bool novel = seen.insert(signature).second;

                child.score =
                    (save_changed ? 1000000ull : 0ull) +
                    (map_changed ? 10000ull : 0ull) +
                    (submode != 0 ? 1000ull : 0ull) +
                    (novel ? 100ull : 0ull) +
                    (screen_changed ? 10ull : 0ull) +
                    static_cast<std::uint64_t>(depth);

                if (novel || save_changed || map_changed || submode != 0) {
                    candidates.push_back(std::move(child));
                }
            }
        }

        if (candidates.empty()) {
            std::cout << "M7_SEARCH_FAIL exhausted depth=" << depth << "\n";
            return 128;
        }

        std::stable_sort(candidates.begin(), candidates.end(),
            [](const SearchNode& lhs, const SearchNode& rhs) {
                return lhs.score > rhs.score;
            });
        if (candidates.size() > beam_width) candidates.resize(beam_width);

        std::cout << "M7_SEARCH_DEPTH depth=" << (depth + 1)
                  << " candidates=" << candidates.size()
                  << " best_score=" << candidates.front().score
                  << " best_map=0x" << std::hex << candidates.front().map_hash
                  << " best_sram=0x" << candidates.front().save_hash << std::dec
                  << " C5DC="
                  << static_cast<unsigned>(
                         candidates.front().runtime.memory().read8(0xC5DC))
                  << "\n";

        beam = std::move(candidates);
    }

    Renderer best_renderer{};
    best_renderer.render(beam.front().runtime.memory(), true);
    best_renderer.write_bmp(output_dir / "search_best.bmp");
    std::cout << "M7_SEARCH_NO_MODE_CHANGE depth=" << max_depth;
    print_search_path(beam.front().path);
    std::cout << "\n";
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
