#include "recomp/window.hpp"

#include "recomp/memory.hpp"
#include "recomp/runtime.hpp"

#ifdef _WIN32

#define WIN32_LEAN_AND_MEAN
#include <windows.h>

#include <chrono>
#include <cstdint>
#include <iostream>
#include <thread>

namespace dwm2t {
namespace {

const Renderer::Framebuffer* g_framebuffer = nullptr;
std::uint8_t g_host_buttons = 0;

bool is_fatal_step(StepResult result) {
    return result == StepResult::MissingBank ||
           result == StepResult::Trapped ||
           result == StepResult::Stopped;
}

void set_button(std::uint8_t button, bool down) {
    if (down) g_host_buttons = static_cast<std::uint8_t>(g_host_buttons | button);
    else g_host_buttons = static_cast<std::uint8_t>(g_host_buttons & ~button);
}

void handle_key(WPARAM key, bool down) {
    switch (key) {
        case VK_RIGHT: set_button(JoyRight, down); break;
        case VK_LEFT: set_button(JoyLeft, down); break;
        case VK_UP: set_button(JoyUp, down); break;
        case VK_DOWN: set_button(JoyDown, down); break;
        case 'Z': set_button(JoyA, down); break;
        case 'X': set_button(JoyB, down); break;
        case VK_RETURN: set_button(JoyStart, down); break;
        case VK_BACK: set_button(JoySelect, down); break;
        default: break;
    }
}

LRESULT CALLBACK wnd_proc(HWND hwnd, UINT message, WPARAM wparam, LPARAM lparam) {
    switch (message) {
        case WM_PAINT: {
            PAINTSTRUCT ps{};
            HDC dc = BeginPaint(hwnd, &ps);
            RECT rect{};
            GetClientRect(hwnd, &rect);

            BITMAPINFO info{};
            info.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
            info.bmiHeader.biWidth = Renderer::Width;
            info.bmiHeader.biHeight = -Renderer::Height;
            info.bmiHeader.biPlanes = 1;
            info.bmiHeader.biBitCount = 32;
            info.bmiHeader.biCompression = BI_RGB;

            if (g_framebuffer != nullptr) {
                StretchDIBits(
                    dc, 0, 0, rect.right - rect.left, rect.bottom - rect.top,
                    0, 0, Renderer::Width, Renderer::Height,
                    g_framebuffer->data(), &info, DIB_RGB_COLORS, SRCCOPY);
            }
            EndPaint(hwnd, &ps);
            return 0;
        }
        case WM_KEYDOWN:
        case WM_SYSKEYDOWN:
            handle_key(wparam, true);
            return 0;
        case WM_KEYUP:
        case WM_SYSKEYUP:
            handle_key(wparam, false);
            return 0;
        case WM_KILLFOCUS:
            g_host_buttons = 0;
            return 0;
        case WM_ERASEBKGND:
            return 1;
        case WM_DESTROY:
            PostQuitMessage(0);
            return 0;
        default:
            return DefWindowProcW(hwnd, message, wparam, lparam);
    }
}

HWND create_window(int scale) {
    HINSTANCE instance = GetModuleHandleW(nullptr);
    const wchar_t* class_name = L"DWM2tRecompWindow";

    WNDCLASSW wc{};
    wc.lpfnWndProc = wnd_proc;
    wc.hInstance = instance;
    wc.hCursor = LoadCursor(nullptr, IDC_ARROW);
    wc.lpszClassName = class_name;
    RegisterClassW(&wc);

    RECT desired{0, 0, Renderer::Width * scale, Renderer::Height * scale};
    AdjustWindowRect(&desired, WS_OVERLAPPEDWINDOW, FALSE);

    return CreateWindowExW(
        0, class_name, L"DWM2t Native Recomp",
        WS_OVERLAPPEDWINDOW | WS_VISIBLE,
        CW_USEDEFAULT, CW_USEDEFAULT,
        desired.right - desired.left, desired.bottom - desired.top,
        nullptr, nullptr, instance, nullptr);
}

} // namespace

int run_native_window(const Renderer::Framebuffer& framebuffer, int scale) {
    g_framebuffer = &framebuffer;
    g_host_buttons = 0;

    HWND hwnd = create_window(scale);
    if (hwnd == nullptr) {
        g_framebuffer = nullptr;
        return 1;
    }

    MSG msg{};
    while (GetMessageW(&msg, nullptr, 0, 0) > 0) {
        TranslateMessage(&msg);
        DispatchMessageW(&msg);
    }

    g_framebuffer = nullptr;
    g_host_buttons = 0;
    return static_cast<int>(msg.wParam);
}

int run_live_window(
    Runtime& runtime,
    Renderer& renderer,
    const std::filesystem::path& sav_path,
    int scale) {

    if (!load_sram_file(runtime.memory(), sav_path)) {
        std::cerr << "M6 live FAIL: invalid SRAM file " << sav_path.string() << "\n";
        return 2;
    }

    renderer.render(runtime.memory(), true);
    g_framebuffer = &renderer.framebuffer();
    g_host_buttons = 0;

    HWND hwnd = create_window(scale);
    if (hwnd == nullptr) {
        g_framebuffer = nullptr;
        return 1;
    }

    using Clock = std::chrono::steady_clock;
    constexpr auto frame_period = std::chrono::microseconds(16742);
    auto next_frame = Clock::now();
    auto last_save = next_frame;
    int exit_code = 0;
    bool running = true;
    MSG msg{};

    while (running) {
        while (PeekMessageW(&msg, nullptr, 0, 0, PM_REMOVE)) {
            if (msg.message == WM_QUIT) {
                running = false;
                break;
            }
            TranslateMessage(&msg);
            DispatchMessageW(&msg);
        }
        if (!running) break;

        auto& memory = runtime.memory();
        memory.set_joypad_state(g_host_buttons);
        const std::uint64_t start_frame = memory.frame_counter();

        StepResult result = StepResult::Continue;
        std::size_t steps = 0;
        constexpr std::size_t max_steps_per_frame = 2'000'000;
        while (memory.frame_counter() == start_frame && steps < max_steps_per_frame) {
            result = runtime.step();
            ++steps;
            if (is_fatal_step(result)) break;
        }

        if (is_fatal_step(result)) {
            const auto& cpu = runtime.cpu();
            if (result == StepResult::MissingBank) {
                std::cerr << "M6 live FAIL: missing AOT ROMX bank "
                          << cpu.missing_bank << " pc=0x"
                          << std::hex << cpu.pc << std::dec << "\n";
                exit_code = 3;
            } else if (result == StepResult::Trapped) {
                std::cerr << "M6 live FAIL: CPU trap pc=0x"
                          << std::hex << cpu.trap_pc << std::dec << "\n";
                exit_code = 4;
            } else {
                std::cerr << "M6 live FAIL: unexpected STOP\n";
                exit_code = 5;
            }
            break;
        }
        if (steps >= max_steps_per_frame) {
            std::cerr << "M6 live FAIL: frame step budget exceeded\n";
            exit_code = 6;
            break;
        }

        renderer.render(memory, true);
        g_framebuffer = &renderer.framebuffer();
        InvalidateRect(hwnd, nullptr, FALSE);
        UpdateWindow(hwnd);

        const auto now = Clock::now();
        if (memory.sram_dirty() && now - last_save >= std::chrono::seconds(2)) {
            if (!save_sram_file(memory, sav_path)) {
                std::cerr << "M6 live FAIL: could not persist SRAM\n";
                exit_code = 7;
                break;
            }
            last_save = now;
        }

        next_frame += frame_period;
        const auto after_work = Clock::now();
        if (next_frame > after_work) {
            std::this_thread::sleep_until(next_frame);
        } else if (after_work - next_frame > std::chrono::milliseconds(250)) {
            next_frame = after_work;
        }
    }

    runtime.memory().set_joypad_state(0);
    if (runtime.memory().sram_dirty() &&
        !save_sram_file(runtime.memory(), sav_path) &&
        exit_code == 0) {
        exit_code = 7;
    }

    if (IsWindow(hwnd)) DestroyWindow(hwnd);
    g_framebuffer = nullptr;
    g_host_buttons = 0;
    return exit_code;
}

int run_live_window_smoke(
    Runtime& runtime,
    Renderer& renderer,
    const std::filesystem::path& sav_path,
    int scale) {

    if (!load_sram_file(runtime.memory(), sav_path)) {
        std::cerr << "M6_WINDOW_SMOKE_FAIL invalid_sram\n";
        return 80;
    }

    renderer.render(runtime.memory(), true);
    g_framebuffer = &renderer.framebuffer();
    g_host_buttons = 0;

    HWND hwnd = create_window(scale);
    if (hwnd == nullptr) {
        g_framebuffer = nullptr;
        std::cerr << "M6_WINDOW_SMOKE_FAIL create_window\n";
        return 81;
    }

    auto pump_messages = []() {
        MSG msg{};
        while (PeekMessageW(&msg, nullptr, 0, 0, PM_REMOVE)) {
            if (msg.message == WM_QUIT) continue;
            TranslateMessage(&msg);
            DispatchMessageW(&msg);
        }
    };

    PostMessageW(hwnd, WM_KEYDOWN, VK_RIGHT, 0);
    pump_messages();
    const bool keydown_ok = (g_host_buttons & JoyRight) != 0;

    // Prove that the Win32 keyboard mapping reaches the same P1/joypad state
    // used by the deterministic M6 movement regression, then release it
    // before advancing the cartridge boot path.
    runtime.memory().set_joypad_state(g_host_buttons);
    const bool p1_down_ok =
        (runtime.memory().joypad_state() & JoyRight) != 0;

    PostMessageW(hwnd, WM_KEYUP, VK_RIGHT, 0);
    pump_messages();
    const bool keyup_ok = (g_host_buttons & JoyRight) == 0;
    runtime.memory().set_joypad_state(g_host_buttons);
    const bool p1_up_ok =
        (runtime.memory().joypad_state() & JoyRight) == 0;

    constexpr unsigned smoke_frames = 4;
    for (unsigned frame_index = 0; frame_index < smoke_frames; ++frame_index) {
        auto& memory = runtime.memory();
        const std::uint64_t start_frame = memory.frame_counter();

        StepResult result = StepResult::Continue;
        std::size_t steps = 0;
        constexpr std::size_t max_steps_per_frame = 2'000'000;
        while (memory.frame_counter() == start_frame && steps < max_steps_per_frame) {
            result = runtime.step();
            ++steps;
            if (is_fatal_step(result)) break;
        }
        if (is_fatal_step(result) || steps >= max_steps_per_frame) {
            const auto& cpu = runtime.cpu();
            DestroyWindow(hwnd);
            g_framebuffer = nullptr;
            g_host_buttons = 0;
            std::cerr << "M6_WINDOW_SMOKE_FAIL runtime frame="
                      << frame_index
                      << " result=" << static_cast<unsigned>(result)
                      << " pc=0x" << std::hex << cpu.pc
                      << " missing_bank=" << std::dec << cpu.missing_bank
                      << "\n";
            return 82;
        }

        renderer.render(memory, true);
        g_framebuffer = &renderer.framebuffer();
        InvalidateRect(hwnd, nullptr, FALSE);
        UpdateWindow(hwnd);
        pump_messages();
    }

    runtime.memory().set_joypad_state(0);
    if (IsWindow(hwnd)) DestroyWindow(hwnd);
    pump_messages();
    g_framebuffer = nullptr;
    g_host_buttons = 0;

    if (!keydown_ok || !keyup_ok || !p1_down_ok || !p1_up_ok) {
        std::cerr << "M6_WINDOW_SMOKE_FAIL keyboard_mapping"
                  << " down=" << keydown_ok
                  << " up=" << keyup_ok
                  << " p1_down=" << p1_down_ok
                  << " p1_up=" << p1_up_ok << "\n";
        return 83;
    }

    std::cout << "M6_WINDOW_SMOKE_PASS frames=" << smoke_frames
              << " keydown=1 keyup=1 p1_down=1 p1_up=1 framebuffer_hash=0x"
              << std::hex << renderer.hash() << std::dec << "\n";
    return 0;
}

} // namespace dwm2t

#else

namespace dwm2t {
int run_native_window(const Renderer::Framebuffer&, int) { return 1; }
int run_live_window(Runtime&, Renderer&, const std::filesystem::path&, int) { return 1; }
int run_live_window_smoke(Runtime&, Renderer&, const std::filesystem::path&, int) { return 1; }
} // namespace dwm2t
#endif
