#pragma once
#include <filesystem>
namespace dwm2t {
int run_m7_discovery(const std::filesystem::path& output_dir);
int run_m7_route_search(const std::filesystem::path& output_dir);
int run_m7_fast_route_probe(const std::filesystem::path& output_dir, bool interactive = false);
int run_m7_p1_session(const std::filesystem::path& output_dir);
class Runtime;
int run_m7_p1_session(Runtime& runtime, const std::filesystem::path& output_dir);
int replay_m7_p1(Runtime& runtime, const std::filesystem::path& route);
int run_m7_p1_replay(const std::filesystem::path& route,
                     const std::filesystem::path& output_dir);
int run_m7_audio_probe();
int run_m7_real_battle_test(const std::filesystem::path& output_dir);
int run_m7_save_continue_test(
    const std::filesystem::path& save_path,
    const std::filesystem::path& output_dir);
} // namespace dwm2t
