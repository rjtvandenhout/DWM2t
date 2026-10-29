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
    int audio_volume = 5,
    bool audio_smooth = true);

// Two original cartridges on one local serial cable. Each window receives
// only its own focused keyboard input; each runtime retains its own SRAM.
int run_linked_windows(
    Runtime& first,
    Renderer& first_renderer,
    const std::filesystem::path& first_save,
    Runtime& second,
    Renderer& second_renderer,
    const std::filesystem::path& second_save,
    int scale = 4,
    int audio_device = -1,
    int audio_volume = 5,
    bool audio_smooth = true);

int list_audio_devices();
int run_audio_playback_test(int device = -1);
int run_audio_stream_test();

int run_live_window_smoke(
    Runtime& runtime,
    Renderer& renderer,
    const std::filesystem::path& sav_path,
    int scale = 2);

} // namespace dwm2t
