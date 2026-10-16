#pragma once
#include <filesystem>
namespace dwm2t {
int run_m7_discovery(const std::filesystem::path& output_dir);
int run_m7_audio_probe();
} // namespace dwm2t
