#include "recomp/m8.hpp"
#include "recomp/runtime.hpp"
#include "recomp/renderer.hpp"
#include <array>
#include <chrono>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <thread>

namespace dwm2t {
namespace {
std::uint64_t sram_hash(const Memory& memory) {
    std::uint64_t hash = 14695981039346656037ull;
    for (auto byte : memory.sram()) { hash ^= byte; hash *= 1099511628211ull; }
    return hash;
}

const char* button_name(std::uint8_t button) {
    switch (button) {
    case JoyRight: return "R"; case JoyLeft: return "L";
    case JoyUp: return "U"; case JoyDown: return "D";
    case JoyA: return "A"; case JoyB: return "B";
    case JoyStart: return "Start"; case JoySelect: return "Select";
    default: return "-";
    }
}

class Session {
public:
    Session(const std::filesystem::path& save, const std::filesystem::path& output)
        : output_(output) {
        std::filesystem::create_directories(output_);
        if (std::filesystem::exists(output_ / "trace_p1.txt"))
            throw std::runtime_error("output already contains a trace; refusing overwrite");
        trace_.open(output_ / "trace_p1.txt");
        if (!trace_) throw std::runtime_error("cannot open P1 trace");
        if (save != "-") {
            if (!std::filesystem::is_regular_file(save) ||
                std::filesystem::file_size(save) != Memory::SramSize ||
                !load_sram_file(runtime_.memory(), save))
                throw std::runtime_error("expected an existing exact 32 KiB original save");
        }
        trace_ << "# Fresh Runtime; seed SRAM FNV=" << std::hex
               << sram_hash(runtime_.memory()) << std::dec << '\n';
        std::cout << "M8_SEED sram=0x" << std::hex << sram_hash(runtime_.memory())
                  << std::dec << " source=" << save.string() << std::endl;
    }

    void flush() {
        if (!run_length_) return;
        trace_ << button_name(run_button_) << ' ' << run_length_ << " 0\n";
        trace_.flush(); run_length_ = 0;
    }

    void frame(std::uint8_t button) {
        // The only host input mutation is the controller port. CPU, memory,
        // rendering, RNG, party, quests and combat remain cartridge-owned.
        runtime_.memory().set_joypad_state(button);
        const auto initial = runtime_.memory().frame_counter();
        for (unsigned step = 0; step < 2'000'000; ++step) {
            const auto result = runtime_.step();
            if (result == StepResult::MissingBank || result == StepResult::Trapped ||
                result == StepResult::Stopped) {
                flush();
                trace_ << "runtime_failure " << int(result) << ' '
                       << runtime_.cpu().missing_bank << ' '
                       << runtime_.cpu().pc << '\n';
                trace_.flush();
                std::cout << "M8_RUNTIME_FAIL result=" << int(result)
                          << " bank=" << runtime_.memory().current_rom_bank()
                          << " missing=" << runtime_.cpu().missing_bank
                          << " pc=0x" << std::hex << runtime_.cpu().pc
                          << " opcode=0x" << unsigned(runtime_.cpu().trap_opcode)
                          << std::dec << std::endl;
                throw std::runtime_error("original execution failed closed");
            }
            if (runtime_.memory().frame_counter() != initial) {
                (void)runtime_.memory().apu().take_samples();
                if (run_length_ && (run_button_ != button || run_length_ == 30000)) flush();
                run_button_ = button; ++run_length_;
                return;
            }
        }
        flush(); trace_ << "runtime_failure frame_step_budget\n"; trace_.flush();
        throw std::runtime_error("frame step budget exceeded");
    }

    void pulse(std::uint8_t button, unsigned hold, unsigned idle) {
        if (hold > 30000 || idle > 30000) throw std::runtime_error("input frame budget exceeded");
        for (unsigned i = 0; i < hold + idle; ++i) frame(i < hold ? button : 0);
    }

    void snapshot() {
        flush();
        auto& memory = runtime_.memory();
        Renderer renderer{}; renderer.render(memory, true);
        const auto stem = "m8_" + std::to_string(capture_++);
        renderer.write_bmp(output_ / (stem + ".bmp"));
        std::ofstream dump(output_ / (stem + ".ram"), std::ios::binary);
        for (unsigned address = 0; address < 65536; ++address) {
            const char value = char(memory.read8(std::uint16_t(address)));
            dump.write(&value, 1);
        }
        std::ofstream raw_sram(output_ / (stem + ".sram"), std::ios::binary);
        raw_sram.write(reinterpret_cast<const char*>(memory.sram().data()), Memory::SramSize);
        std::cout << "M8_STATE frame=" << memory.frame_counter()
                  << " mode=" << unsigned(memory.read8(0xC5DB)) << ':'
                  << unsigned(memory.read8(0xC5DC))
                  << " world=" << unsigned(memory.read8(0xFF90))
                  << " region=" << unsigned(memory.read8(0xFF8F)) << ','
                  << unsigned(memory.read8(0xFF92))
                  << " pos=" << unsigned(memory.read8(0xFF8E)) << ','
                  << unsigned(memory.read8(0xFF91))
                  << " party=" << unsigned(memory.read8(0xC6FD))
                  << " selector=0x" << std::hex << unsigned(memory.read8(0xC916))
                  << " sram=0x" << sram_hash(memory)
                  << " screen=0x" << renderer.hash() << std::dec
                  << " image=" << stem << ".bmp" << std::endl;
        // Read-only assertions make the generated trace independently replayable.
        for (auto address : {0xC5DB,0xC5DC,0xC6FD,0xFF90,0xFF8F,0xFF92,0xFF8E,0xFF91})
            trace_ << "expect " << std::hex << address << ' '
                   << unsigned(memory.read8(std::uint16_t(address))) << std::dec << '\n';
        for (unsigned address = 0xCBD7; address < 0xCC0F; ++address)
            trace_ << "expect " << std::hex << address << ' '
                   << unsigned(memory.read8(std::uint16_t(address))) << std::dec << '\n';
        trace_ << "expect_sram " << std::hex << sram_hash(memory) << '\n'
               << "expect_screen " << renderer.hash() << std::dec << '\n';
        trace_.flush();
    }

    void boot_continue(bool load_slot) {
        Renderer renderer{};
        unsigned stable = 0;
        for (unsigned i = 0; i < 3000 && stable < 30; ++i) {
            frame(0); renderer.render(runtime_.memory(), true);
            stable = renderer.hash() == 0x49c67a53ef4f8a80ull ? stable + 1 : 0;
        }
        if (stable != 30) throw std::runtime_error("original title was not reached");
        if (load_slot) {
            pulse(JoyStart, 6, 96); pulse(JoyA, 6, 180); pulse(JoyA, 6, 180);
            if (runtime_.memory().read8(0xC5DB) != 1)
                throw std::runtime_error("original Continue did not restore a field state");
        }
        snapshot();
    }

    void replay_trace(const std::filesystem::path& path) {
        std::ifstream trace(path);
        if (!trace) throw std::runtime_error("cannot open recorded P1 trace");
        std::string line;
        while (std::getline(trace, line)) {
            constexpr std::string_view seed_prefix = "# Fresh Runtime; seed SRAM FNV=";
            if (line.starts_with(seed_prefix)) {
                std::istringstream seed(line.substr(seed_prefix.size()));
                std::uint64_t expected = 0;
                if (!(seed >> std::hex >> expected) ||
                    runtime_.memory().frame_counter() != 0 ||
                    sram_hash(runtime_.memory()) != expected)
                    throw std::runtime_error("recorded trace seed SRAM does not match");
            }
            std::istringstream input(line); std::string command; input >> command;
            if (command.empty() || command[0] == '#') continue;
            if (command == "expect_sram" || command == "expect_screen") {
                std::uint64_t expected = 0, actual = 0;
                if (!(input >> std::hex >> expected)) throw std::runtime_error("invalid hash assertion");
                if (command == "expect_sram") actual = sram_hash(runtime_.memory());
                else { Renderer renderer{}; renderer.render(runtime_.memory(), true); actual = renderer.hash(); }
                if (actual != expected) throw std::runtime_error("recorded hash assertion failed");
                flush(); trace_ << line << '\n'; continue;
            }
            if (command == "expect") {
                unsigned address = 0, expected = 0;
                if (!(input >> std::hex >> address >> expected) || address > 65535 || expected > 255)
                    throw std::runtime_error("invalid recorded assertion");
                if (runtime_.memory().read8(std::uint16_t(address)) != expected)
                    throw std::runtime_error("recorded P1 replay assertion failed");
                flush(); trace_ << line << '\n';
                continue;
            }
            unsigned hold = 0, idle = 0;
            if (!(input >> hold >> idle)) throw std::runtime_error("invalid recorded P1 command");
            std::uint8_t button = 0; bool known = command == "-";
            for (auto candidate : {JoyRight,JoyLeft,JoyUp,JoyDown,JoyA,JoyB,JoyStart,JoySelect})
                if (command == button_name(candidate)) { button = candidate; known = true; }
            if (!known) throw std::runtime_error("recorded trace must contain only P1 input/assertions");
            pulse(button, hold, idle);
        }
        snapshot();
        std::cout << "M8_TRACE_REPLAY_PASS source=" << path.string() << std::endl;
    }

    void battle(unsigned budget, bool flee) {
        auto& memory = runtime_.memory();
        if (memory.read8(0xC5DB) != 4) return;
        bool flee_selected = false;
        for (unsigned i = 0; i < budget; ++i) {
            // 49:$46CA -> 22:$6A4E -> 20:$5CA8 is the original recruitment
            // name editor. It requires a deliberate name/END choice, not A spam.
            if (memory.read8(0xCFC8) == 2 && memory.read8(0xCFC9) == 5 &&
                memory.read8(0xCFCA) == 3 && memory.read8(0xCFCC) == 2) {
                std::cout << "M8_BATTLE_NEEDS_NAME original_recruitment_menu" << std::endl;
                return;
            }
            if (memory.read8(0xC5DB) != 4) {
                pulse(0, 0, 60);
                std::cout << "M8_BATTLE_FINISHED frames=" << i << std::endl;
                return;
            }
            // Original main battle menu: normalize the visible 2x2 selection
            // by P1, not by patching its cursor. Movement callers release D-pad
            // as soon as a real encounter starts.
            if (flee && !flee_selected && i >= 96) {
                pulse(JoyB, 2, 24);
                pulse(JoyRight, 2, 12); pulse(JoyDown, 2, 12);
                pulse(JoyA, 2, 24); flee_selected = true;
            }
            frame((!flee || flee_selected) && i % 32 < 2 ? JoyA : 0);
            if (i && i % 600 == 0) snapshot();
        }
        throw std::runtime_error("battle P1 frame budget exhausted");
    }

    void talk(unsigned budget, unsigned period) {
        if (period < 4 || period > 300) throw std::runtime_error("invalid dialogue pulse period");
        auto& memory = runtime_.memory();
        bool seen = memory.read8(0xC5DC) != 0;
        for (unsigned i = 0; i < budget; ++i) {
            if (memory.read8(0xC5DB) == 4) { battle(12000, false); return; }
            if (seen && memory.read8(0xC5DB) == 1 && memory.read8(0xC5DC) == 0) return;
            frame(i % period < 2 ? JoyA : 0);
            if (memory.read8(0xC5DC) != 0) seen = true;
            if (!seen && i >= 48) return;
        }
        throw std::runtime_error("dialogue P1 frame budget exhausted");
    }

    void journal(const std::string& name) {
        if (name.empty() || name.find_first_not_of("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-") != std::string::npos)
            throw std::runtime_error("invalid checkpoint name");
        auto& memory = runtime_.memory();
        if (memory.read8(0xC5DB) != 1 || memory.read8(0xC5DC) != 0)
            throw std::runtime_error("Journal requires an idle field and empty facing tile");
        const auto baseline = memory.sram();
        pulse(JoyA, 6, 96);
        if (memory.read8(0xC5DB) != 1 || memory.read8(0xC5DC) != 2)
            throw std::runtime_error("field menu did not open (possibly facing an NPC)");
        pulse(JoyRight, 6, 24); pulse(JoyDown, 6, 24); pulse(JoyA, 6, 96);
        if (memory.read8(0xC5DB) != 2 || memory.read8(0xC5DC) != 3)
            throw std::runtime_error("original PLAN menu was not reached");
        for (unsigned i = 0; i < 5; ++i) pulse(JoyDown, 6, 24);
        pulse(JoyA, 6, 96); pulse(JoyA, 6, 96); pulse(JoyA, 6, 96);
        pulse(0, 0, 180); snapshot();
        pulse(JoyA, 6, 96); pulse(JoyB, 6, 96); pulse(JoyB, 6, 96);
        for (unsigned retry = 0; retry < 12 &&
             (memory.read8(0xC5DB) != 1 || memory.read8(0xC5DC) != 0); ++retry)
            pulse(JoyB, 2, 60);
        unsigned changed = 0;
        for (unsigned i = 0; i < Memory::SramSize; ++i)
            if (baseline[i] != memory.sram()[i]) ++changed;
        if (!changed || memory.read8(0xC5DB) != 1 || memory.read8(0xC5DC) != 0)
            throw std::runtime_error("original Journal did not save and return to field");
        const auto path = output_ / (name + ".sav");
        if (std::filesystem::exists(path)) throw std::runtime_error("checkpoint already exists; refusing overwrite");
        if (!save_sram_file(memory, path)) throw std::runtime_error("cannot persist original SRAM");
        std::cout << "M8_ORIGINAL_SAVE path=" << path.string() << " bytes="
                  << std::filesystem::file_size(path) << " changed=" << changed
                  << " sram=0x" << std::hex << sram_hash(memory) << std::dec << std::endl;
        verify_continue(path, output_ / (name + "_continue"));
    }

    void verify_continue(const std::filesystem::path& save,
                         const std::filesystem::path& output) {
        // A new constructor owns every CPU/hardware/work-RAM byte. Only the
        // exact original SRAM file crosses into the Continue verification.
        Session fresh(save, output);
        if (fresh.runtime_.cpu().pc != 0x0100 ||
            fresh.runtime_.memory().frame_counter() != 0 ||
            fresh.runtime_.memory().sram() != runtime_.memory().sram())
            throw std::runtime_error("fresh-runtime SRAM isolation failed");
        fresh.boot_continue(true);
        unsigned mismatches = 0;
        std::ofstream evidence(output / "continue_evidence.txt");
        evidence << "Original Journal Save; new Runtime; exact 32768-byte SRAM file only\n";
        for (unsigned address = 0xC6FD; address < 0xC82D; ++address) {
            const auto expected = runtime_.memory().read8(std::uint16_t(address));
            const auto actual = fresh.runtime_.memory().read8(std::uint16_t(address));
            if (expected != actual) {
                evidence << "party mismatch " << std::hex << address << ' '
                         << unsigned(expected) << " -> " << unsigned(actual) << '\n';
                ++mismatches;
            }
        }
        for (auto address : {0xCBD7,0xCBD8,0xCBD9,0xCBDA,0xCBDB,
                             0xFF90,0xFF8F,0xFF92,0xFF8E,0xFF91}) {
            const auto expected = runtime_.memory().read8(std::uint16_t(address));
            const auto actual = fresh.runtime_.memory().read8(std::uint16_t(address));
            evidence << std::hex << address << ' ' << unsigned(expected)
                     << " -> " << unsigned(actual) << '\n';
            if (expected != actual) ++mismatches;
        }
        evidence << std::dec << "party_bytes=304 fields=10 mismatches=" << mismatches << '\n';
        if (mismatches) throw std::runtime_error("fresh Continue differs from saved party/quest/location");
        fresh.flush();
        std::cout << "M8_FRESH_CONTINUE_PASS party_bytes=304 fields=10 source="
                  << save.string() << std::endl;
    }

    void walk(std::uint8_t direction, unsigned hold, unsigned idle) {
        auto& memory = runtime_.memory();
        if (hold > 30000 || idle > 30000) throw std::runtime_error("walk budget exceeded");
        unsigned moved = 0;
        for (; moved < hold; ++moved) {
            if (memory.read8(0xC5DB) != 1 || memory.read8(0xC5DC) != 0) break;
            frame(direction);
        }
        pulse(0, 0, idle);
        std::cout << "M8_WALK input_frames=" << moved << " requested=" << hold << std::endl;
    }

    int poll() {
        std::ofstream commands_log(output_ / "commands_executed.txt");
        std::size_t consumed = 0;
        while (true) {
            std::ifstream commands(output_ / "commands.txt");
            std::string line; bool found = false;
            for (std::size_t i = 0; std::getline(commands, line); ++i)
                if (i == consumed) { found = true; break; }
            if (!found) { std::this_thread::sleep_for(std::chrono::milliseconds(100)); continue; }
            ++consumed;
            std::istringstream input(line); std::string command; input >> command;
            if (command.empty() || command[0] == '#') continue;
            commands_log << line << std::endl;
            if (command == "quit") { flush(); return 0; }
            if (command == "battle" || command == "flee") {
                unsigned budget = 12000; input >> budget;
                if (budget > 60000) throw std::runtime_error("battle budget too large");
                battle(budget, command == "flee");
            } else if (command == "talk") {
                unsigned budget = 12000, period = 16; input >> budget >> period;
                if (budget > 60000) throw std::runtime_error("dialogue budget too large");
                talk(budget, period);
            } else if (command == "journal") {
                std::string name; input >> name; journal(name);
            } else if (command == "snapshot") {
                // Observation only.
            } else if (command == "walk") {
                std::string direction; unsigned hold = 0, idle = 60;
                if (!(input >> direction >> hold)) throw std::runtime_error("expected walk direction/frames");
                input >> idle;
                std::uint8_t button = 0;
                for (auto candidate : {JoyRight,JoyLeft,JoyUp,JoyDown})
                    if (direction == button_name(candidate)) button = candidate;
                if (!button) throw std::runtime_error("expected a D-pad direction");
                walk(button, hold, idle);
            } else {
                unsigned hold = 0, idle = 0;
                if (!(input >> hold >> idle)) throw std::runtime_error("expected hold/release frame counts");
                std::uint8_t button = 0; bool known = command == "-";
                for (auto candidate : {JoyRight,JoyLeft,JoyUp,JoyDown,JoyA,JoyB,JoyStart,JoySelect})
                    if (command == button_name(candidate)) { button = candidate; known = true; }
                if (!known) throw std::runtime_error("unknown input command");
                pulse(button, hold, idle);
            }
            snapshot();
        }
    }

    Runtime& runtime() { return runtime_; }

private:
    Runtime runtime_{};
    std::filesystem::path output_;
    std::ofstream trace_;
    std::uint8_t run_button_ = 0;
    unsigned run_length_ = 0, capture_ = 0;
};
}

int run_m8_session(const std::filesystem::path& save, const std::filesystem::path& output,
                   const std::filesystem::path& trace) {
    try {
        Session session(save, output);
        try {
            if (trace.empty()) session.boot_continue(save != "-");
            else session.replay_trace(trace);
            return session.poll();
        }
        catch (...) { session.snapshot(); throw; }
    } catch (const std::exception& error) {
        std::cerr << "M8_SESSION_FAIL " << error.what() << std::endl; return 230;
    }
}

int run_m8_replay(const std::filesystem::path& save, const std::filesystem::path& route,
                  const std::filesystem::path& output) {
    try {
        Session session(save, output);
        session.replay_trace(route);
        std::cout << "M8_REPLAY_RESULT result=0" << std::endl;
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "M8_REPLAY_FAIL " << error.what() << std::endl; return 230;
    }
}

int run_m8_oasis_test(const std::filesystem::path& seed, const std::filesystem::path& route,
                      const std::filesystem::path& output) {
    try {
        Session session(seed, output);
        if (sram_hash(session.runtime().memory()) != 0x81daa8e19c019ce4ull)
            throw std::runtime_error("Oasis regression requires the original accepted M7 Journal save");
        session.replay_trace(route);
        auto& memory = session.runtime().memory();
        // Pinned discovery trace: original Continue, travel, two encounters,
        // recruitment/name/Yes, town entry and original PLAN > Journal Save.
        if (sram_hash(memory) != 0x79f780ede66cc6d1ull ||
            memory.frame_counter() != 29449 || memory.read8(0xC6FD) != 2 ||
            memory.read8(0xC5DB) != 1 || memory.read8(0xC5DC) != 0 ||
            memory.read8(0xFF90) != 33 || memory.read8(0xFF8F) != 0 ||
            memory.read8(0xFF92) != 0 || memory.read8(0xFF8E) != 80 ||
            memory.read8(0xFF91) != 128)
            throw std::runtime_error("recorded Oasis Journal checkpoint differs from pinned evidence");
        const auto save = output / "oasis_original_journal.sav";
        if (std::filesystem::exists(save) || !save_sram_file(memory, save) ||
            std::filesystem::file_size(save) != Memory::SramSize)
            throw std::runtime_error("cannot persist original recorded Journal SRAM");
        session.verify_continue(save, output / "fresh_continue");
        std::cout << "M8_OASIS_CHECKPOINT_PASS party=2 original_Journal fresh_Runtime"
                     " ending_credits=NOT_YET_PROVEN" << std::endl;
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "M8_OASIS_CHECKPOINT_FAIL " << error.what() << std::endl;
        return 230;
    }
}

int run_m8_inn_test(const std::filesystem::path& seed, const std::filesystem::path& route,
                    const std::filesystem::path& output) {
    try {
        Session session(seed, output);
        auto& memory = session.runtime().memory();
        if (sram_hash(memory) != 0x79f780ede66cc6d1ull)
            throw std::runtime_error("inn regression requires the recorded original Oasis Journal save");
        const auto initial_hp = memory.sram()[0x5B];
        session.replay_trace(route);
        if (initial_hp != 18 || memory.sram()[0x5B] != 25 || memory.sram()[0x5D] != 25 ||
            sram_hash(memory) != 0x520c04981e15a459ull ||
            memory.frame_counter() != 4924 || memory.read8(0xC6FD) != 2 ||
            memory.read8(0xC5DB) != 1 || memory.read8(0xC5DC) != 0 ||
            memory.read8(0xFF90) != 34 || memory.read8(0xFF8F) != 0 ||
            memory.read8(0xFF92) != 0 || memory.read8(0xFF8E) != 80 ||
            memory.read8(0xFF91) != 80)
            throw std::runtime_error("original inn healing/Journal differs from pinned evidence");
        const auto save = output / "inn_original_journal.sav";
        if (std::filesystem::exists(save) || !save_sram_file(memory, save) ||
            std::filesystem::file_size(save) != Memory::SramSize)
            throw std::runtime_error("cannot persist original inn Journal SRAM");
        session.verify_continue(save, output / "fresh_continue");
        std::cout << "M8_INN_CHECKPOINT_PASS original_healing hp=18->25/25"
                     " original_Journal fresh_Runtime ending_credits=NOT_YET_PROVEN" << std::endl;
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "M8_INN_CHECKPOINT_FAIL " << error.what() << std::endl;
        return 230;
    }
}
}
