// Production Windows entry point. No synthetic fixtures or discovery commands.
#include "recomp/renderer.hpp"
#include "recomp/romx.hpp"
#include "recomp/runtime.hpp"
#include "recomp/window.hpp"

#ifndef NOMINMAX
#define NOMINMAX
#endif
#define WIN32_LEAN_AND_MEAN
#include <windows.h>

#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <string_view>

#ifndef DWM2T_SOURCE_REVISION
#define DWM2T_SOURCE_REVISION "unknown"
#endif

namespace {
namespace fs = std::filesystem;

struct SaveLock {
    HANDLE handle = INVALID_HANDLE_VALUE;
    explicit SaveLock(const fs::path& save) {
        auto path = save;
        path += L".lock";
        handle = CreateFileW(path.c_str(), GENERIC_READ | GENERIC_WRITE, 0, nullptr,
                             OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
        if (handle == INVALID_HANDLE_VALUE)
            throw std::runtime_error("Save is locked by another game, or its directory is not writable");
    }
    ~SaveLock() { if (handle != INVALID_HANDLE_VALUE) CloseHandle(handle); }
    SaveLock(const SaveLock&) = delete;
    SaveLock& operator=(const SaveLock&) = delete;
};

bool valid_profile(std::wstring_view value) {
    if (value.empty() || value.size() > 48) return false;
    std::wstring upper;
    for (wchar_t c : value) {
        if (!((c >= L'a' && c <= L'z') || (c >= L'A' && c <= L'Z') ||
              (c >= L'0' && c <= L'9') || c == L'_' || c == L'-')) return false;
        upper += (c >= L'a' && c <= L'z') ? wchar_t(c - L'a' + L'A') : c;
    }
    if (upper == L"CON" || upper == L"PRN" || upper == L"AUX" || upper == L"NUL") return false;
    if (upper.size() == 4 && (upper.substr(0, 3) == L"COM" || upper.substr(0, 3) == L"LPT") &&
        upper[3] >= L'1' && upper[3] <= L'9') return false;
    return true;
}

int integer(std::wstring_view value, int minimum, int maximum) {
    std::size_t used = 0;
    const int number = std::stoi(std::wstring(value), &used);
    if (used != value.size() || number < minimum || number > maximum)
        throw std::runtime_error("Option value is outside its supported range");
    return number;
}

fs::path default_save(std::wstring_view profile) {
    const DWORD length = GetEnvironmentVariableW(L"LOCALAPPDATA", nullptr, 0);
    if (length == 0) throw std::runtime_error("LOCALAPPDATA unavailable; supply --play <save-path>");
    std::wstring value(length, L'\0');
    const DWORD copied = GetEnvironmentVariableW(L"LOCALAPPDATA", value.data(), length);
    if (copied == 0 || copied >= length) throw std::runtime_error("Cannot read LOCALAPPDATA");
    value.resize(copied);
    return fs::path(value) / L"DWM2t" / L"saves" / (std::wstring(profile) + L".sav");
}

std::wstring run_id() {
    FILETIME time{};
    GetSystemTimeAsFileTime(&time);
    const auto ticks = (std::uint64_t(time.dwHighDateTime) << 32) | time.dwLowDateTime;
    return std::to_wstring(ticks) + L"-" + std::to_wstring(GetCurrentProcessId());
}

void help() {
    std::cout <<
        "DWM2t native player - M8 candidate (testing pending)\n"
        "No arguments: play with %LOCALAPPDATA%/DWM2t/saves/default.sav\n"
        "  --play [save-path]   Play with an explicit save, or the default profile\n"
        "  --profile NAME       Separate profile (letters/digits/underscore/hyphen)\n"
        "  --audio-volume 0..100  Game volume; default 5\n"
        "  --audio-device N     Windows device ID; -1 selects automatic fallback\n"
        "  --audio-raw          Disable host smoothing\n"
        "  --audio-devices      List playback devices without starting the game\n"
        "  --scale 1..8         Initial integer window scale; default 4\n"
        "  --version | --help\n"
        "Arrow keys: move. Z: A. X: B. Enter: Start. Backspace: Select.\n"
        "Save using the original PLAN > Journal. Closing alone is not Journal Save.\n";
}
} // namespace

int wmain(int argc, wchar_t** argv) {
    try {
        if (argc == 2 && std::wstring_view(argv[1]) == L"--help") { help(); return 0; }
        if (argc == 2 && std::wstring_view(argv[1]) == L"--version") {
            std::cout << "DWM2t M8 UNTESTED_CANDIDATE\nsource=" << DWM2T_SOURCE_REVISION
                      << "\nfixed_banks=1 romx_banks=" << dwm2t::translated_romx_bank_count()
                      << "\nfull_game_verified=false\n";
            return 0;
        }
        if (argc == 2 && std::wstring_view(argv[1]) == L"--audio-devices")
            return dwm2t::list_audio_devices();

        fs::path save;
        std::wstring profile = L"default";
        int volume = 5, device = -1, scale = 4;
        bool smooth = true, explicit_profile = false, play_seen = false;
        for (int i = 1; i < argc; ++i) {
            const std::wstring_view option(argv[i]);
            const auto value = [&]() -> std::wstring_view {
                if (++i >= argc) throw std::runtime_error("An option value is missing");
                return argv[i];
            };
            if (option == L"--play" && !play_seen) {
                play_seen = true;
                if (i + 1 < argc && !std::wstring_view(argv[i + 1]).starts_with(L"--"))
                    save = argv[++i];
            } else if (option == L"--profile" && !explicit_profile) {
                profile = value(); explicit_profile = true;
                if (!valid_profile(profile)) throw std::runtime_error("Invalid or reserved profile name");
            } else if (option == L"--audio-volume") volume = integer(value(), 0, 100);
            else if (option == L"--audio-device") device = integer(value(), -1, 1024);
            else if (option == L"--audio-raw") smooth = false;
            else if (option == L"--scale") scale = integer(value(), 1, 8);
            else throw std::runtime_error("Unknown or repeated option; use --help");
        }
        if (!save.empty() && explicit_profile)
            throw std::runtime_error("Use either --profile or an explicit save path, not both");
        if (save.empty()) save = default_save(profile);
        save = fs::absolute(save).lexically_normal();
        if (save.filename().empty()) throw std::runtime_error("A save filename is required");
        fs::create_directories(save.parent_path());
        // Normalize parent aliases so normal alternate paths share one lock.
        save = fs::weakly_canonical(save.parent_path()) / save.filename();
        SaveLock lock(save);
        std::error_code ec;
        const auto status = fs::symlink_status(save, ec);
        if (ec && ec != std::errc::no_such_file_or_directory)
            throw std::runtime_error("Cannot inspect save file");
        const auto id = run_id();
        fs::path backup;
        if (fs::exists(status)) {
            if (!fs::is_regular_file(status) || fs::file_size(save) != 32768u)
                throw std::runtime_error("Refusing malformed, linked or non-32-KiB save");
            const auto folder = save.parent_path() / L"backups" / save.stem();
            fs::create_directories(folder);
            backup = folder / (id + L".sav");
            if (!fs::copy_file(save, backup, fs::copy_options::none))
                throw std::runtime_error("Cannot create the pre-launch save backup");
        }
        if (dwm2t::translated_romx_bank_count() != 255)
            throw std::runtime_error("The production player requires all 255 ROMX banks");
        std::cout << "DWM2T_PLAYER source=" << DWM2T_SOURCE_REVISION
                  << " status=UNTESTED_CANDIDATE romx_banks=255\n";
        std::wcout << L"Save: " << save.native() << L'\n';
        if (!backup.empty()) std::wcout << L"Backup: " << backup.native() << L'\n';
        // Heap allocation leaves the Windows stack for ordinary rendering.
        auto runtime = std::make_unique<dwm2t::Runtime>();
        auto renderer = std::make_unique<dwm2t::Renderer>();
        const int result = dwm2t::run_live_window(*runtime, *renderer, save, scale, device, volume, smooth);
        if (result != 0) {
            const auto folder = save.parent_path() / L"diagnostics" / id;
            fs::create_directories(folder);
            renderer->render(runtime->memory(), true);
            renderer->write_bmp(folder / L"last-frame.bmp");
            std::ofstream report(folder / L"failure.txt");
            const auto& cpu = runtime->cpu();
            report << "source=" << DWM2T_SOURCE_REVISION << "\nexit_code=" << result
                   << "\nbank=" << runtime->memory().current_rom_bank()
                   << "\npc=" << cpu.pc << "\ntrap_pc=" << cpu.trap_pc
                   << "\nmissing_bank=" << cpu.missing_bank
                   << "\nframe=" << runtime->memory().frame_counter()
                   << "\nNo synthetic recovery state was created.\n";
            const auto message = L"The native runtime stopped. Diagnostic files:\n" + folder.native() +
                L"\nYour pre-launch backup remains separate. This candidate is not fully validated.";
            MessageBoxW(nullptr, message.c_str(), L"DWM2t runtime stopped", MB_OK | MB_ICONERROR);
        }
        return result;
    } catch (const std::exception& error) {
        std::cerr << "DWM2t player error: " << error.what() << '\n';
        MessageBoxW(nullptr, L"DWM2t could not start safely. See the console or launcher log.\n"
                    L"Check the save/profile, permissions and command-line options.",
                    L"DWM2t player", MB_OK | MB_ICONERROR);
        return 1;
    }
}
