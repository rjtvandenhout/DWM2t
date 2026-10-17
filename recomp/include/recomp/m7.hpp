#pragma once
#include <filesystem>
namespace dwm2t {
int run_m7_discovery(const std::filesystem::path& output_dir);
int run_m7_route_search(const std::filesystem::path& output_dir);
int run_m7_fast_route_probe(const std::filesystem::path& output_dir);
int run_m7_audio_probe();
} // namespace dwm2t
