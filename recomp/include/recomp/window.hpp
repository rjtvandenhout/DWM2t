#pragma once

#include "recomp/renderer.hpp"

#include <filesystem>

namespace dwm2t {

class Runtime;

int run_native_window(const Renderer::Framebuffer& framebuffer, int scale = 4);

int run_live_window(
    Runtime& runtime,
    Renderer& renderer,
    const std::filesystem::path& sav_path,
    int scale = 4);

int run_live_window_smoke(
    Runtime& runtime,
    Renderer& renderer,
    const std::filesystem::path& sav_path,
    int scale = 2);

} // namespace dwm2t
