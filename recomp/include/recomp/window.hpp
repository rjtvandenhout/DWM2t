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
    int scale = 4,
    int audio_device = -1,
    int audio_volume = 25,
    bool audio_smooth = true);

int list_audio_devices();
int run_audio_playback_test(int device = -1);

int run_live_window_smoke(
    Runtime& runtime,
    Renderer& renderer,
    const std::filesystem::path& sav_path,
    int scale = 2);

} // namespace dwm2t
