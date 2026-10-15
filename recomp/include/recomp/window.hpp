#pragma once

#include "recomp/renderer.hpp"

namespace dwm2t {

// Displays a framebuffer in a simple native window until the user closes it.
// Returns 0 on a normal close. On non-Windows hosts the function returns 1.
int run_native_window(const Renderer::Framebuffer& framebuffer, int scale = 4);

} // namespace dwm2t
