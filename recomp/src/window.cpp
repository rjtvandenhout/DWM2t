#include "recomp/window.hpp"

#ifdef _WIN32

#define WIN32_LEAN_AND_MEAN
#include <windows.h>

#include <cstdint>

namespace dwm2t {

namespace {

const Renderer::Framebuffer* g_framebuffer = nullptr;

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
                    dc,
                    0,
                    0,
                    rect.right - rect.left,
                    rect.bottom - rect.top,
                    0,
                    0,
                    Renderer::Width,
                    Renderer::Height,
                    g_framebuffer->data(),
                    &info,
                    DIB_RGB_COLORS,
                    SRCCOPY);
            }

            EndPaint(hwnd, &ps);
            return 0;
        }

        case WM_ERASEBKGND:
            return 1;

        case WM_DESTROY:
            PostQuitMessage(0);
            return 0;

        default:
            return DefWindowProcW(hwnd, message, wparam, lparam);
    }
}

} // namespace

int run_native_window(const Renderer::Framebuffer& framebuffer, int scale) {
    g_framebuffer = &framebuffer;

    HINSTANCE instance = GetModuleHandleW(nullptr);
    const wchar_t* class_name = L"DWM2tRecompWindow";

    WNDCLASSW wc{};
    wc.lpfnWndProc = wnd_proc;
    wc.hInstance = instance;
    wc.hCursor = LoadCursor(nullptr, IDC_ARROW);
    wc.lpszClassName = class_name;

    RegisterClassW(&wc);

    RECT desired{
        0,
        0,
        Renderer::Width * scale,
        Renderer::Height * scale,
    };
    AdjustWindowRect(&desired, WS_OVERLAPPEDWINDOW, FALSE);

    HWND hwnd = CreateWindowExW(
        0,
        class_name,
        L"DWM2t Native Recomp",
        WS_OVERLAPPEDWINDOW | WS_VISIBLE,
        CW_USEDEFAULT,
        CW_USEDEFAULT,
        desired.right - desired.left,
        desired.bottom - desired.top,
        nullptr,
        nullptr,
        instance,
        nullptr);

    if (hwnd == nullptr) return 1;

    MSG msg{};
    while (GetMessageW(&msg, nullptr, 0, 0) > 0) {
        TranslateMessage(&msg);
        DispatchMessageW(&msg);
    }

    g_framebuffer = nullptr;
    return static_cast<int>(msg.wParam);
}

} // namespace dwm2t

#else

namespace dwm2t {

int run_native_window(const Renderer::Framebuffer&, int) {
    return 1;
}

} // namespace dwm2t

#endif
