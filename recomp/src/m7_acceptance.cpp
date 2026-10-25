#include "recomp/m7.hpp"
#include "recomp/runtime.hpp"
#include "recomp/renderer.hpp"

#include <array>
#include <fstream>
#include <iostream>

namespace dwm2t {
namespace {
std::uint64_t hash_bytes(const auto& bytes) {
    std::uint64_t hash = 14695981039346656037ull;
    for (auto byte : bytes) { hash ^= byte; hash *= 1099511628211ull; }
    return hash;
}

std::uint64_t capture(Runtime& runtime, const std::filesystem::path& path) {
    Renderer renderer{};
    renderer.render(runtime.memory(), true);
    renderer.write_bmp(path);
    return renderer.hash();
}

StepResult frame(Runtime& runtime, std::uint8_t buttons) {
    runtime.memory().set_joypad_state(buttons);
    const auto initial = runtime.memory().frame_counter();
    for (unsigned step = 0; step < 2'000'000; ++step) {
        const auto result = runtime.step();
        if (result == StepResult::MissingBank || result == StepResult::Trapped ||
            result == StepResult::Stopped) {
            std::cout << "M7_BATTLE_RUNTIME_FAIL result=" << int(result)
                      << " missing=" << runtime.cpu().missing_bank
                      << " pc=0x" << std::hex << runtime.cpu().pc << std::dec << std::endl;
            return result;
        }
        if (runtime.memory().frame_counter() != initial) {
            (void)runtime.memory().apu().take_samples();
            return StepResult::Continue;
        }
    }
    return StepResult::StepLimit;
}

// Original 49:$7806 / $7832 draws current combat HP from the D8BF word table.
// Slots 0..2 are the party and 4..6 the enemies (slot 3 is unused). This is
// not the D0D5 record copy, which stays stale until combat state is committed.
// Actual P1 combat independently showed HUD 25->15 matching D8BF, and enemy
// D8C7 9->4 when Slash attacked. Never write any of these fields from the host.
auto combat_hp(const Runtime& runtime) {
    std::array<unsigned, 6> hp{};
    for (unsigned slot = 0; slot < hp.size(); ++slot) {
        const unsigned combat_slot = slot < 3 ? slot : slot + 1;
        const auto address = std::uint16_t(0xD8BF + combat_slot * 2);
        hp[slot] = runtime.memory().read8(address) |
            (unsigned(runtime.memory().read8(address + 1)) << 8);
    }
    return hp;
}
}

int run_m7_real_battle_test(const std::filesystem::path& output_dir) {
    std::filesystem::create_directories(output_dir);
    Runtime battle{};
    int result = replay_m7_p1(battle, "recomp/tests/m7_party_p1.txt");
    if (result) return result;
    result = replay_m7_p1(battle, "recomp/tests/m7_oasis_p1.txt");
    if (result) return result;
    for (unsigned i = 0; i < 240; ++i)
        if (frame(battle, 0) != StepResult::Continue) return 207;
    const auto& memory = battle.memory();
    const auto initial_hp = combat_hp(battle);
    if (memory.read8(0xC5DB) != 4 || memory.read8(0xC6FD) != 1 ||
        memory.read8(0xD88F) != 1 || memory.read8(0xD890) == 0 ||
        memory.read8(0xD890) > 3 || initial_hp[0] != 25 || initial_hp[3] == 0)
        return 208;
    const auto before_screen = capture(battle, output_dir / "battle_before.bmp");
    // Equal-time control starts from exactly the same cartridge-owned state.
    Runtime control = battle;
    Runtime command = battle;
    unsigned action_frame = 0;
    for (; action_frame < 1800; ++action_frame) {
        if (frame(control, 0) != StepResult::Continue ||
            frame(command, action_frame % 96 < 2 ? JoyA : 0) != StepResult::Continue)
            return 209;
        if (combat_hp(control) != initial_hp) return 210;
        const auto hp = combat_hp(command);
        bool damage = false;
        // Require damage to an enemy, i.e. an actual party attack resolving,
        // not merely the enemy taking its own first action or a menu change.
        for (unsigned i = 3; i < hp.size(); ++i)
            if (initial_hp[i] && hp[i] < initial_hp[i]) damage = true;
        if (damage) break;
    }
    if (action_frame == 1800) return 211;
    const auto after_hp = combat_hp(command);
    const auto after_screen = capture(command, output_dir / "battle_action.bmp");
    const auto control_screen = capture(control, output_dir / "battle_control.bmp");
    if (after_screen == control_screen) return 212;
    std::ofstream evidence(output_dir / "battle_evidence.txt");
    evidence << "Fresh original boot/quest/party; P1 Oasis Key; real C5DB=4 battle\n"
             << "P1 Fight/default confirmations; equal-time no-input control\n"
             << "action_frames=" << action_frame + 1 << '\n';
    for (unsigned i = 0; i < after_hp.size(); ++i)
        evidence << "HP[" << i << "] " << initial_hp[i] << " -> " << after_hp[i]
                 << "; control=" << initial_hp[i] << '\n';
    evidence << std::hex << "framebuffer " << before_screen << " -> " << after_screen
             << "; control=" << control_screen << '\n';
    std::cout << "M7_BATTLE_RESULT original_P1_encounter mode=4 original_player_attack"
              << " frames=" << action_frame + 1
              << " party_hp=" << initial_hp[0] << "->" << after_hp[0]
              << " enemy_hp=" << initial_hp[3] << "->" << after_hp[3]
              << " control_hp_unchanged=1 before=0x" << std::hex << before_screen
              << " after=0x" << after_screen << " control=0x" << control_screen
              << std::dec << std::endl;
    if (action_frame + 1 != 282 || initial_hp[3] != 9 ||
        after_hp[0] != 20 || after_hp[3] != 6 ||
        before_screen != 0x08e2dcfe5df6d1e0ull ||
        control_screen != before_screen ||
        after_screen != 0xa220d333e6f055b0ull) {
        std::cout << "M7_BATTLE_FAIL deterministic_regression_changed" << std::endl;
        return 213;
    }
    std::cout << "M7_BATTLE_PASS original_player_attack_and_equal_time_control" << std::endl;
    return 0;
}

int run_m7_save_continue_test(const std::filesystem::path& save_path,
                             const std::filesystem::path& output_dir) {
    std::filesystem::create_directories(output_dir);
    // No debug checkpoint or host-written game state: fresh cartridge boot,
    // original quest progression, original Slash introduction, then Journal.
    Runtime source{};
    int result = replay_m7_p1(source, "recomp/tests/m7_party_p1.txt");
    if (result) return result;
    const auto sram_before = source.memory().sram();
    result = replay_m7_p1(source, "recomp/tests/m7_save_p1.txt");
    if (result) return result;
    const auto saved_sram = source.memory().sram();
    unsigned changed = 0;
    for (std::size_t i = 0; i < saved_sram.size(); ++i)
        if (saved_sram[i] != sram_before[i]) ++changed;
    if (!changed || !source.memory().sram_dirty()) return 201;
    if (changed != 317 || hash_bytes(saved_sram) != 0x81daa8e19c019ce4ull) return 214;

    // Game-owned party/inventory and persistent quest/location witnesses.
    // Exclude transient field/NPC animation workspaces beginning at C82D.
    std::array<std::uint8_t, 0x130> saved_party{};
    for (unsigned i = 0; i < saved_party.size(); ++i)
        saved_party[i] = source.memory().read8(std::uint16_t(0xC6FD + i));
    if (hash_bytes(saved_party) != 0xe39e0b6ad4462761ull) return 215;
    constexpr std::array<std::uint16_t, 11> fields = {
        0xC6FD, 0xCBD7, 0xCBD8, 0xCBD9, 0xCBDA, 0xCBDB,
        0xFF90, 0xFF8F, 0xFF92, 0xFF8E, 0xFF91
    };
    std::array<std::uint8_t, fields.size()> expected{};
    for (unsigned i = 0; i < fields.size(); ++i)
        expected[i] = source.memory().read8(fields[i]);
    const auto source_screen = capture(source, output_dir / "original_save_field.bmp");
    if (!save_sram_file(source.memory(), save_path) ||
        std::filesystem::file_size(save_path) != Memory::SramSize) return 202;

    // A genuinely new CPU, WRAM, VRAM, PPU and APU. Only .sav crosses over.
    Runtime fresh{};
    if (fresh.cpu().pc != 0x0100 || fresh.memory().frame_counter() != 0 ||
        fresh.memory().read8(0xC6FD) != 0) return 203;
    if (!load_sram_file(fresh.memory(), save_path) ||
        fresh.memory().sram() != saved_sram) return 204;
    result = replay_m7_p1(fresh, "recomp/tests/m7_continue_p1.txt");
    if (result) return result;
    const auto continued_screen = capture(fresh, output_dir / "fresh_continue_field.bmp");
    if (source_screen != 0xe2c568bb82de9659ull ||
        continued_screen != 0xbc6b373672fa22d8ull) return 216;
    std::ofstream evidence(output_dir / "save_continue_evidence.txt");
    evidence << "original Journal Save; fresh constructor; SRAM file only\n"
             << "bytes=" << Memory::SramSize << " changed=" << changed
             << " sram_fnv=0x" << std::hex << hash_bytes(saved_sram)
             << " party_fnv=0x" << hash_bytes(saved_party) << '\n';
    for (unsigned i = 0; i < fields.size(); ++i) {
        const auto actual = fresh.memory().read8(fields[i]);
        evidence << std::hex << fields[i] << ": " << unsigned(expected[i])
                 << " -> " << unsigned(actual) << '\n';
        if (actual != expected[i]) return 205;
    }
    for (unsigned i = 0; i < saved_party.size(); ++i)
        if (fresh.memory().read8(std::uint16_t(0xC6FD + i)) != saved_party[i]) return 206;
    std::cout << "M7_SAVE_CONTINUE_PASS original_Journal_save fresh_Runtime_SRAM_only"
              << " bytes=" << Memory::SramSize << " changed=" << changed
              << " party_bytes=" << saved_party.size()
              << " matched_fields=" << fields.size()
              << " sram=0x" << std::hex << hash_bytes(saved_sram)
              << " source_screen=0x" << source_screen
              << " continued_screen=0x" << continued_screen << std::dec << std::endl;
    return 0;
}
}
