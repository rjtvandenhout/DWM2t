#pragma once

// Host-side persistence only. No cartridge state, format or timing changes.
#include <atomic>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <string>
#include <system_error>

#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>
#else
#include <cerrno>
#include <fcntl.h>
#include <unistd.h>
#endif

namespace dwm2t::save_io {

inline bool write_sram_atomic(const std::filesystem::path& path,
                              const std::uint8_t* data, std::size_t size) {
    // A save is the exact original cartridge SRAM, never a CPU savestate.
    if (path.empty() || data == nullptr || size != 32768u) return false;
    std::error_code ec;
    const auto parent = path.has_parent_path() ? path.parent_path()
                                              : std::filesystem::path(".");
    std::filesystem::create_directories(parent, ec);
    if (ec) return false;

    const auto status = std::filesystem::symlink_status(path, ec);
    if (ec && ec != std::errc::no_such_file_or_directory) return false;
    ec.clear();
    if (std::filesystem::exists(status)) {
        // Never replace a link, directory or malformed/unrelated file.
        if (!std::filesystem::is_regular_file(status)) return false;
        const auto old_size = std::filesystem::file_size(path, ec);
        if (ec || old_size != size) return false;
    }

    static std::atomic<std::uint64_t> sequence{0};
    const auto clock = std::chrono::steady_clock::now().time_since_epoch().count();
#ifdef _WIN32
    const auto pid = GetCurrentProcessId();
#else
    const auto pid = getpid();
#endif
    for (unsigned attempt = 0; attempt < 32; ++attempt) {
        auto temporary = path;
        temporary += ".tmp-" + std::to_string(pid) + "-" + std::to_string(clock) +
                     "-" + std::to_string(sequence.fetch_add(1));
        bool ok = false;
#ifdef _WIN32
        HANDLE handle = CreateFileW(temporary.c_str(), GENERIC_WRITE, 0, nullptr,
                                   CREATE_NEW, FILE_ATTRIBUTE_NORMAL |
                                   FILE_FLAG_WRITE_THROUGH, nullptr);
        if (handle == INVALID_HANDLE_VALUE) {
            const DWORD error = GetLastError();
            if (error == ERROR_FILE_EXISTS || error == ERROR_ALREADY_EXISTS) continue;
            return false;
        }
        DWORD written = 0;
        ok = WriteFile(handle, data, static_cast<DWORD>(size), &written, nullptr) != 0;
        ok = ok && written == size;
        if (ok) ok = FlushFileBuffers(handle) != 0;
        if (!CloseHandle(handle)) ok = false;
        if (ok) {
            // Same-directory replacement: do not delete/truncate the old file
            // first. A failed write/flush/replacement keeps the old save intact.
            ok = MoveFileExW(temporary.c_str(), path.c_str(),
                             MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH) != 0;
        }
#else
        const int fd = ::open(temporary.c_str(), O_WRONLY | O_CREAT | O_EXCL, 0600);
        if (fd < 0) {
            if (errno == EEXIST) continue;
            return false;
        }
        std::size_t offset = 0;
        ok = true;
        while (offset < size) {
            const auto count = ::write(fd, data + offset, size - offset);
            if (count < 0 && errno == EINTR) continue;
            if (count <= 0) { ok = false; break; }
            offset += static_cast<std::size_t>(count);
        }
        if (ok) {
            int result;
            do { result = ::fsync(fd); } while (result < 0 && errno == EINTR);
            ok = result == 0;
        }
        if (::close(fd) != 0) ok = false;
        if (ok) {
            std::filesystem::rename(temporary, path, ec);
            ok = !ec;
            if (ok) {
                // Persist the rename as well as the file contents. If this
                // fails, report failure and keep the in-memory dirty flag.
                const int directory = ::open(parent.c_str(), O_RDONLY | O_DIRECTORY);
                if (directory < 0) ok = false;
                else {
                    int result;
                    do { result = ::fsync(directory); } while (result < 0 && errno == EINTR);
                    ok = result == 0;
                    if (::close(directory) != 0) ok = false;
                }
            }
        }
#endif
        if (!ok) {
            // Remove only the temporary file created by this invocation.
            // A temporary left by an interrupted process is never loaded.
            std::error_code ignored;
            std::filesystem::remove(temporary, ignored);
        }
        return ok;
    }
    return false;
}

} // namespace dwm2t::save_io
