#include "recomp/m7.hpp"
#include "recomp/runtime.hpp"
#include "recomp/renderer.hpp"

#include <fstream>
#include <iostream>
#include <map>
#include <memory>
#include <sstream>
#include <string>
#include <thread>
#include <chrono>
#include <array>
#include <deque>
#include <unordered_set>

namespace dwm2t {
namespace {
StepResult p1_frame(Runtime& runtime, std::uint8_t buttons) {
    runtime.memory().set_joypad_state(buttons);
    const auto frame = runtime.memory().frame_counter();
    for (unsigned step = 0; step < 2'000'000; ++step) {
        const auto result = runtime.step();
        if (result == StepResult::MissingBank || result == StepResult::Trapped ||
            result == StepResult::Stopped) return result;
        if (runtime.memory().frame_counter() != frame) {
            (void)runtime.memory().apu().take_samples();
            return StepResult::Continue;
        }
    }
    return StepResult::StepLimit;
}

// Discovery only: fork cartridge-owned checkpoints and explore P1 paths.
// A found path is exported so acceptance can replay it from a fresh Runtime.
bool seek_quest(Runtime& runtime, unsigned budget,
                const std::filesystem::path& output_dir) {
    struct Node { std::unique_ptr<Runtime> state; std::string path; };
    std::deque<Node> queue;
    std::unordered_set<std::uint64_t> visited;
    const auto key = [](const Runtime& state) {
        std::uint64_t value = 0;
        constexpr std::array<std::uint16_t, 5> locations = {0xFF90, 0xFF8F, 0xFF92, 0xFF8E, 0xFF91};
        for (auto address : locations)
            value = (value << 8) | state.memory().read8(address);
        return value;
    };
    const auto flags = [](const Runtime& state) {
        return unsigned(state.memory().read8(0xCBD7)) |
            (unsigned(state.memory().read8(0xCBD8)) << 8) |
            (unsigned(state.memory().read8(0xCBD9)) << 16);
    };
    const unsigned initial = flags(runtime);
    const auto advance = [](Runtime& state, unsigned hold, unsigned idle,
                            std::uint8_t buttons) {
        for (unsigned i = 0; i < hold + idle; ++i) {
            auto result = p1_frame(state, i < hold ? buttons : 0);
            if (result != StepResult::Continue) return result;
        }
        return StepResult::Continue;
    };
    queue.push_back({std::make_unique<Runtime>(runtime), {}});
    visited.insert(key(runtime));
    unsigned expanded = 0;
    while (!queue.empty() && expanded < budget) {
        auto node = std::move(queue.front()); queue.pop_front(); ++expanded;
        for (unsigned direction = 0; direction < 4; ++direction) {
            constexpr std::array<std::uint8_t, 4> buttons = {JoyRight, JoyLeft, JoyUp, JoyDown};
            constexpr std::array<const char*, 4> names = {"R", "L", "U", "D"};
            auto child = std::make_unique<Runtime>(*node.state);
            auto path = node.path + names[direction] + " 16 60\n";
            auto result = advance(*child, 16, 60, buttons[direction]);
            if (result != StepResult::Continue) {
                std::cout << "P1_SEEK_RUNTIME result=" << int(result)
                          << " missing=" << child->cpu().missing_bank << std::endl;
                std::ofstream(output_dir / "seek_failure_path.txt") << path;
                return false;
            }
            const auto child_key = key(*child);
            const auto& mem = child->memory();
            int x = mem.read8(0xFF8E), y = mem.read8(0xFF91);
            switch (mem.read8(0xFF98) & 3) {
            // Original 135:$42C4: 0=Down, 1=Right, 2=Up, 3=Left.
            case 0: y += 17; break; case 1: x += 17; break;
            case 2: --y; break; case 3: --x; break;
            }
            bool npc_ahead = false;
            for (unsigned actor = 0; actor < mem.read8(0xCB7D) && actor < 5; ++actor) {
                const auto base = std::uint16_t(0xCB7F + actor * 16);
                if ((mem.read8(base + 11) >> 4) == (x >> 4) &&
                    (mem.read8(base + 12) >> 4) == (y >> 4)) npc_ahead = true;
            }
            if (visited.contains(child_key) && !npc_ahead) continue;
            // Face every reachable tile and let the original NPC/interaction
            // dispatcher decide whether there is something to talk to.
            if (npc_ahead) {
            result = advance(*child, 2, 96, JoyA);
            path += "A 2 96\ntalk\n";
            bool seen = child->memory().read8(0xC5DC) != 0;
            for (unsigned frame = 0; result == StepResult::Continue && frame < 3600; ++frame) {
                if (seen && child->memory().read8(0xC5DC) == 0) break;
                result = p1_frame(*child, frame % 96 < 2 ? JoyA : 0);
                if (child->memory().read8(0xC5DC) != 0) seen = true;
                if (!seen && frame >= 48) break;
            }
            }
            if (result != StepResult::Continue) {
                std::cout << "P1_SEEK_RUNTIME result=" << int(result)
                          << " missing=" << child->cpu().missing_bank << std::endl;
                std::ofstream(output_dir / "seek_failure_path.txt") << path;
                return false;
            }
            const unsigned added = flags(*child) & ~initial;
            if (added || child->memory().read8(0xC5DB) == 2) {
                std::ofstream(output_dir / "seek_path.txt") << path;
                std::cout << "P1_SEEK_FOUND nodes=" << expanded << " added="
                          << std::hex << added << std::dec << std::endl;
                runtime = *child;
                return true;
            }
            if (child->memory().read8(0xC5DB) != 1 ||
                child->memory().read8(0xC5DC) != 0) continue;
            if (!visited.contains(key(*child)) && queue.size() < 192) {
                visited.insert(key(*child));
                queue.push_back({std::move(child), std::move(path)});
            }
        }
        if (expanded % 100 == 0)
            std::cout << "P1_SEEK_PROGRESS nodes=" << expanded << " queued="
                      << queue.size() << " visited=" << visited.size()
                      << " location=" << std::hex << key(*node.state)
                      << std::dec << std::endl;
    }
    std::cout << "P1_SEEK_EXHAUSTED nodes=" << expanded << std::endl;
    return false;
}
}

int run_m7_p1_session(Runtime& runtime, const std::filesystem::path& output_dir) {
    std::filesystem::create_directories(output_dir);
    std::ofstream transcript(output_dir / "p1.txt");
    std::map<std::string, std::unique_ptr<Runtime>> checkpoints;
    auto sram_baseline = runtime.memory().sram();
    Renderer renderer{};
    unsigned capture = 0;
    const auto snapshot = [&] {
        auto& memory = runtime.memory();
        renderer.render(memory, true);
        const auto path = output_dir / ("p1_" + std::to_string(capture++) + ".bmp");
        renderer.write_bmp(path);
        std::ofstream dump(output_dir / ("p1_" + std::to_string(capture - 1) + ".ram"), std::ios::binary);
        for (unsigned address = 0; address < 0x10000; ++address) {
            const char value = static_cast<char>(memory.read8(static_cast<std::uint16_t>(address)));
            dump.write(&value, 1);
        }
        std::cout << "P1_FRAME frame=" << memory.frame_counter()
                  << " C5DB=" << unsigned(memory.read8(0xC5DB))
                  << " C5DC=" << unsigned(memory.read8(0xC5DC))
                  << " bank=" << memory.current_rom_bank()
                  << " pc=" << std::hex << runtime.cpu().pc
                  << " selector=" << unsigned(memory.read8(0xC916))
                  << " flags0=" << unsigned(memory.read8(0xCBD7))
                  << " flags1=" << unsigned(memory.read8(0xCBD8))
                  << " C193=" << unsigned(memory.read8(0xC193))
                  << " C562=" << unsigned(memory.read8(0xC562))
                  << " world=" << unsigned(memory.read8(0xFF90))
                  << " region=" << unsigned(memory.read8(0xFF8F))
                  << "," << unsigned(memory.read8(0xFF92))
                  << " pos=" << unsigned(memory.read8(0xFF8E))
                  << "," << unsigned(memory.read8(0xFF91))
                  << " hash=" << renderer.hash() << std::dec
                  << " dirty=" << memory.sram_dirty()
                  << " image=" << path.string() << std::endl;
    };
    snapshot();
    std::cout << "P1_READY commands: R/L/U/D/A/B/Start/Select/- hold release; boot; story; mark name; back name; quit" << std::endl;
    std::string line;
    std::size_t consumed = 0;
    while (true) {
        std::ifstream commands(output_dir / "commands.txt");
        bool found = false;
        for (std::size_t index = 0; std::getline(commands, line); ++index) {
            if (index == consumed) { found = true; break; }
        }
        if (!found) {
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
            continue;
        }
        ++consumed;
        std::istringstream input(line);
        std::string command;
        input >> command;
        if (command.empty() || command[0] == '#') continue;
        if (command == "quit") break;
        transcript << line << std::endl;
        if (command == "srammark") {
            sram_baseline = runtime.memory().sram();
            snapshot();
            continue;
        }
        if (command == "persist") {
            unsigned changes = 0;
            const auto& sram = runtime.memory().sram();
            for (std::size_t i = 0; i < sram.size(); ++i)
                if (sram[i] != sram_baseline[i]) ++changes;
            const auto path = output_dir / "p1.sav";
            if (!save_sram_file(runtime.memory(), path)) return 215;
            std::cout << "P1_SRAM_FILE bytes=" << std::filesystem::file_size(path)
                      << " changed_since_mark=" << changes << std::endl;
            snapshot();
            continue;
        }
        if (command == "fresh") {
            Runtime fresh{};
            if (!load_sram_file(fresh.memory(), output_dir / "p1.sav")) return 214;
            runtime = std::move(fresh);
            snapshot();
            continue;
        }
        if (command == "seek") {
            unsigned budget = 5000; input >> budget;
            seek_quest(runtime, budget, output_dir);
            snapshot();
            continue;
        }
        if (command == "mark" || command == "back") {
            std::string name;
            input >> name;
            if (command == "mark") checkpoints[name] = std::make_unique<Runtime>(runtime);
            else if (checkpoints.contains(name)) runtime = *checkpoints.at(name);
            snapshot();
            continue;
        }
        if (command == "boot") {
            unsigned stable = 0;
            for (unsigned frame = 0; frame < 3000 && stable < 30; ++frame) {
                const auto result = p1_frame(runtime, 0);
                if (result != StepResult::Continue) return int(result) + 220;
                renderer.render(runtime.memory(), true);
                stable = renderer.hash() == 0x49c67a53ef4f8a80ull ? stable + 1 : 0;
            }
            snapshot();
            continue;
        }
        if (command == "story") {
            for (unsigned frame = 0; frame < 1836; ++frame) {
                std::uint8_t buttons = 0;
                if (frame < 3) buttons = JoyStart;
                else if (frame < 1800) {
                    if (frame >= 24 && (frame - 24) % 30 < 2) buttons = JoyA;
                    else if (frame >= 180 && (frame - 180) % 240 < 2) buttons = JoyStart;
                } else if (frame < 1824) buttons = JoyRight;
                const auto result = p1_frame(runtime, buttons);
                if (result != StepResult::Continue) return int(result) + 220;
            }
            snapshot();
            continue;
        }
        if (command == "talk") {
            bool seen = runtime.memory().read8(0xC5DC) != 0;
            for (unsigned frame = 0; frame < 3600; ++frame) {
                if (seen && runtime.memory().read8(0xC5DC) == 0) break;
                const auto result = p1_frame(runtime, frame % 96 < 2 ? JoyA : 0);
                if (result != StepResult::Continue) return int(result) + 220;
                if (runtime.memory().read8(0xC5DC) != 0) seen = true;
                if (frame % 96 == 95) snapshot();
                if (!seen && frame >= 48) break;
            }
            snapshot();
            continue;
        }
        unsigned hold = 2, release = 24;
        input >> hold >> release;
        if (hold > 30000 || release > 30000) return 219;
        std::uint8_t buttons = 0;
        if (command == "R") buttons = JoyRight;
        else if (command == "L") buttons = JoyLeft;
        else if (command == "U") buttons = JoyUp;
        else if (command == "D") buttons = JoyDown;
        else if (command == "A") buttons = JoyA;
        else if (command == "B") buttons = JoyB;
        else if (command == "Start") buttons = JoyStart;
        else if (command == "Select") buttons = JoySelect;
        else if (command != "-") { std::cout << "P1_UNKNOWN" << std::endl; continue; }
        for (unsigned frame = 0; frame < hold + release; ++frame) {
            const auto result = p1_frame(runtime, frame < hold ? buttons : 0);
            if (result != StepResult::Continue) {
                snapshot();
                std::cout << "P1_FAIL result=" << int(result)
                          << " missing=" << runtime.cpu().missing_bank << std::endl;
                return int(result) + 220;
            }
        }
        snapshot();
    }
    return 0;
}

int run_m7_p1_session(const std::filesystem::path& output_dir) {
    Runtime runtime{};
    return run_m7_p1_session(runtime, output_dir);
}

int replay_m7_p1(Runtime& runtime, const std::filesystem::path& route) {
    std::ifstream script(route);
    if (!script) return 216;
    Renderer renderer{};
    std::string line;
    unsigned line_number = 0;
    while (std::getline(script, line)) {
        ++line_number;
        std::istringstream input(line);
        std::string command;
        input >> command;
        if (command.empty() || command[0] == '#') continue;
        if (command == "quit") break;
        if (command == "expect") {
            std::string address_text, value_text;
            if (!(input >> address_text >> value_text)) return 219;
            const auto address = std::stoul(address_text, nullptr, 16);
            const auto expected = std::stoul(value_text, nullptr, 16);
            if (address > 0xFFFF || expected > 0xFF ||
                runtime.memory().read8(std::uint16_t(address)) != expected) {
                std::cout << "P1_REPLAY_EXPECT_FAIL line=" << line_number
                          << " address=" << address_text << " expected="
                          << value_text << std::endl;
                return 217;
            }
            continue;
        }
        unsigned hold = 2, idle = 24, frames = 0;
        std::uint8_t buttons = 0;
        if (command == "boot") frames = 3000;
        else if (command == "story") frames = 1836;
        else if (command == "talk") frames = 3600;
        else {
            if (!(input >> hold >> idle) || hold > 30000 || idle > 30000) return 219;
            if (command == "R") buttons = JoyRight;
            else if (command == "L") buttons = JoyLeft;
            else if (command == "U") buttons = JoyUp;
            else if (command == "D") buttons = JoyDown;
            else if (command == "A") buttons = JoyA;
            else if (command == "B") buttons = JoyB;
            else if (command == "Start") buttons = JoyStart;
            else if (command == "Select") buttons = JoySelect;
            else if (command != "-") return 219; // No mark/back/seek in replay.
            frames = hold + idle;
        }
        unsigned stable = 0;
        bool seen = runtime.memory().read8(0xC5DC) != 0;
        for (unsigned frame = 0; frame < frames; ++frame) {
            if (command == "talk" && seen && runtime.memory().read8(0xC5DC) == 0) break;
            std::uint8_t state = frame < hold ? buttons : 0;
            if (command == "boot") state = 0;
            else if (command == "talk") state = frame % 96 < 2 ? JoyA : 0;
            else if (command == "story") {
                state = 0;
                if (frame < 3) state = JoyStart;
                else if (frame < 1800) {
                    if (frame >= 24 && (frame - 24) % 30 < 2) state = JoyA;
                    else if (frame >= 180 && (frame - 180) % 240 < 2) state = JoyStart;
                } else if (frame < 1824) state = JoyRight;
            }
            const auto result = p1_frame(runtime, state);
            if (result != StepResult::Continue) {
                std::cout << "P1_REPLAY_RUNTIME_FAIL line=" << line_number
                          << " result=" << int(result)
                          << " missing=" << runtime.cpu().missing_bank
                          << " pc=" << std::hex << runtime.cpu().pc
                          << std::dec << std::endl;
                return 220 + int(result);
            }
            if (command == "boot") {
                renderer.render(runtime.memory(), true);
                stable = renderer.hash() == 0x49c67a53ef4f8a80ull ? stable + 1 : 0;
                if (stable == 30) break;
            } else if (command == "talk") {
                if (runtime.memory().read8(0xC5DC) != 0) seen = true;
                if (!seen && frame >= 48) break;
            }
        }
        if (command == "boot" && stable != 30) return 218;
    }
    return 0;
}

int run_m7_p1_replay(const std::filesystem::path& route,
                     const std::filesystem::path& output_dir) {
    Runtime runtime{};
    const int result = replay_m7_p1(runtime, route);
    std::filesystem::create_directories(output_dir);
    Renderer renderer{};
    renderer.render(runtime.memory(), true);
    renderer.write_bmp(output_dir / "replay_final.bmp");
    std::cout << "P1_REPLAY_COMPLETE result=" << result
              << " frame=" << runtime.memory().frame_counter()
              << " C5DB=" << unsigned(runtime.memory().read8(0xC5DB))
              << " C5DC=" << unsigned(runtime.memory().read8(0xC5DC))
              << " flags=" << std::hex << unsigned(runtime.memory().read8(0xCBD7))
              << "/" << unsigned(runtime.memory().read8(0xCBD8))
              << "/" << unsigned(runtime.memory().read8(0xCBD9))
              << " hash=" << renderer.hash() << std::dec << std::endl;
    return result;
}
}
