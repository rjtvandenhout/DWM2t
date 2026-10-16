#pragma once
#include <filesystem>
namespace dwm2t {
int run_m6_probe(const std::filesystem::path& output_dir);
int run_m6_sram_test(const std::filesystem::path& save_path);
} // namespace dwm2t
