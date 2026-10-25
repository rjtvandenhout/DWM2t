// Host filesystem fault injection only. Synthetic SRAM is never gameplay input.
// The original Memory implementation is compiled once in this test translation
// unit so its inline persistence helper sees the same injected host calls.
// Production sources and their build definitions are unchanged.
#include <array>
#include <atomic>
#include <cerrno>
#include <chrono>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>
#ifdef _WIN32
#define NOMINMAX
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#else
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>
#endif
#include "recomp/memory.hpp"

namespace faults {
enum class Mode { none, partial_write, flush, replace, collision, interrupt };
Mode mode = Mode::none;
std::filesystem::path collision_path;
#ifdef _WIN32
HANDLE WINAPI create(const wchar_t* path, DWORD access, DWORD sharing, LPSECURITY_ATTRIBUTES security,
                     DWORD disposition, DWORD attributes, HANDLE template_file) {
    if (mode == Mode::collision) {
        mode = Mode::none;
        collision_path = path;
        const HANDLE previous = CreateFileW(path, GENERIC_WRITE, 0, nullptr, CREATE_NEW,
                                            FILE_ATTRIBUTE_NORMAL, nullptr);
        if (previous == INVALID_HANDLE_VALUE) throw std::runtime_error("cannot create collision fixture");
        DWORD written = 0;
        const char marker[] = "preserve pre-existing temporary";
        if (!WriteFile(previous, marker, sizeof(marker), &written, nullptr) ||
                written != sizeof(marker) || !FlushFileBuffers(previous))
            throw std::runtime_error("cannot persist collision fixture");
        CloseHandle(previous);
    }
    return CreateFileW(path, access, sharing, security, disposition, attributes, template_file);
}
BOOL WINAPI write(HANDLE file, LPCVOID data, DWORD size, LPDWORD written, LPOVERLAPPED overlapped) {
    if (mode == Mode::partial_write || mode == Mode::interrupt) {
        const BOOL ok = WriteFile(file, data, size < 1024 ? size : 1024, written, overlapped);
        if (!ok) return FALSE;
        if (mode == Mode::interrupt) { FlushFileBuffers(file); std::_Exit(42); }
        SetLastError(ERROR_DISK_FULL);
        return FALSE;
    }
    return WriteFile(file, data, size, written, overlapped);
}
BOOL WINAPI flush(HANDLE file) {
    if (mode == Mode::flush) { SetLastError(ERROR_WRITE_FAULT); return FALSE; }
    return FlushFileBuffers(file);
}
BOOL WINAPI replace(const wchar_t* old_path, const wchar_t* new_path, DWORD flags) {
    if (mode == Mode::replace) { SetLastError(ERROR_ACCESS_DENIED); return FALSE; }
    return MoveFileExW(old_path, new_path, flags);
}
#else
int create(const char* path, int flags, mode_t permissions) {
    if (mode == Mode::collision) {
        mode = Mode::none;
        collision_path = path;
        const int previous = ::open(path, O_WRONLY | O_CREAT | O_EXCL, 0600);
        const char marker[] = "preserve pre-existing temporary";
        if (previous < 0 || ::write(previous, marker, sizeof(marker)) != sizeof(marker) ||
                ::fsync(previous) != 0 || ::close(previous) != 0)
            throw std::runtime_error("cannot persist collision fixture");
    }
    return ::open(path, flags, permissions);
}
// The helper also opens the parent directory after replacement.
int create(const char* path, int flags) { return ::open(path, flags); }
ssize_t write(int fd, const void* data, std::size_t size) {
    if (mode == Mode::partial_write || mode == Mode::interrupt) {
        const auto written = ::write(fd, data, size < 1024 ? size : 1024);
        if (written < 0) return written;
        if (mode == Mode::interrupt) { ::fsync(fd); std::_Exit(42); }
        errno = ENOSPC;
        return -1;
    }
    return ::write(fd, data, size);
}
int flush(int fd) {
    if (mode == Mode::flush) { errno = EIO; return -1; }
    return ::fsync(fd);
}
#endif
} // namespace faults

#ifdef _WIN32
#define CreateFileW faults::create
#define WriteFile faults::write
#define FlushFileBuffers faults::flush
#define MoveFileExW faults::replace
#else
// Qualified calls ::open/::write/::fsync become ::faults::create/write/flush.
#define open faults::create
#define write faults::write
#define fsync faults::flush
#endif
#include "recomp/atomic_sram.hpp"
#ifdef _WIN32
#undef CreateFileW
#undef WriteFile
#undef FlushFileBuffers
#undef MoveFileExW
#else
#undef open
#undef write
#undef fsync
#endif
#include "../src/memory.cpp"

namespace fs = std::filesystem;
using Bytes = std::vector<std::uint8_t>;
unsigned checks = 0;
void check(bool condition, const char* label) {
    if (!condition) throw std::runtime_error(label);
    ++checks;
    std::cout << "SAVE_IO_FAULT_PASS " << label << '\n';
}
Bytes read_file(const fs::path& path) {
    std::ifstream stream(path, std::ios::binary);
    if (!stream) throw std::runtime_error("cannot read synthetic fixture");
    return Bytes(std::istreambuf_iterator<char>(stream), {});
}
std::vector<fs::path> temporaries(const fs::path& root) {
    std::vector<fs::path> result;
    for (const auto& entry : fs::directory_iterator(root))
        if (entry.path().filename().string().find(".tmp-") != std::string::npos)
            result.push_back(entry.path());
    return result;
}
int interrupted_child(const fs::path& exe, const fs::path& save) {
#ifdef _WIN32
    auto command = L"\"" + exe.wstring() + L"\" --interrupt \"" + save.wstring() + L"\"";
    STARTUPINFOW startup{}; startup.cb = sizeof(startup);
    PROCESS_INFORMATION process{};
    if (!CreateProcessW(nullptr, command.data(), nullptr, nullptr, FALSE, 0, nullptr, nullptr,
                        &startup, &process)) throw std::runtime_error("cannot launch interrupted writer");
    const auto waited = WaitForSingleObject(process.hProcess, 10000);
    DWORD code = 0;
    const bool got = GetExitCodeProcess(process.hProcess, &code) != 0;
    if (waited != WAIT_OBJECT_0) TerminateProcess(process.hProcess, 99);
    CloseHandle(process.hThread); CloseHandle(process.hProcess);
    if (waited != WAIT_OBJECT_0 || !got) throw std::runtime_error("interrupted writer timed out");
    return static_cast<int>(code);
#else
    const pid_t pid = fork();
    if (pid < 0) throw std::runtime_error("cannot fork interrupted writer");
    if (pid == 0) { execl(exe.c_str(), exe.c_str(), "--interrupt", save.c_str(), nullptr); std::_Exit(99); }
    int status = 0;
    if (waitpid(pid, &status, 0) != pid || !WIFEXITED(status))
        throw std::runtime_error("interrupted writer did not exit normally");
    return WEXITSTATUS(status);
#endif
}

int main(int argc, char** argv) {
    try {
        if (argc == 3 && std::string(argv[1]) == "--interrupt") {
            faults::mode = faults::Mode::interrupt;
            Bytes data(32768, 0xB7);
            dwm2t::save_io::write_sram_atomic(argv[2], data.data(), data.size());
            return 98;
        }
        if (argc != 2) throw std::runtime_error("expected a new evidence parent");
        const auto root = fs::path(argv[1]) / ("save-io-faults-" + std::to_string(
            std::chrono::steady_clock::now().time_since_epoch().count()));
        fs::create_directories(root.parent_path());
        if (!fs::create_directory(root)) throw std::runtime_error("evidence already exists");
        std::cout << "SAVE_IO_FAULT_EVIDENCE " << root.string() << '\n';
        const auto save = root/"synthetic.sav";
        Bytes original(32768, 0xA3);
        check(dwm2t::save_io::write_sram_atomic(save, original.data(), original.size()), "create_synthetic_original");
        auto memory = std::make_unique<dwm2t::Memory>();
        memory->write8(0, 0x0A); memory->write8(0xA123, 0x7B);
        check(memory->sram_dirty(), "synthetic_cartridge_write_sets_dirty");
        for (const auto mode : {faults::Mode::partial_write, faults::Mode::flush}) {
            faults::mode = mode;
            check(!dwm2t::save_sram_file(*memory, save),
                  mode == faults::Mode::flush ? "failed_flush_is_reported" : "partial_write_is_reported");
            check(memory->sram_dirty() && read_file(save) == original, "failure_preserves_previous_save_and_dirty_flag");
            check(temporaries(root).empty(), "failed_call_removes_its_own_temporary");
        }
#ifdef _WIN32
        faults::mode = faults::Mode::replace;
        check(!dwm2t::save_sram_file(*memory, save) && memory->sram_dirty() && read_file(save) == original,
              "failed_replace_preserves_previous_save_and_dirty_flag");
        faults::mode = faults::Mode::none;
        check(SetFileAttributesW(save.c_str(), FILE_ATTRIBUTE_READONLY) != 0, "set_readonly_fixture");
        const bool refused_readonly = !dwm2t::save_sram_file(*memory, save);
        check(SetFileAttributesW(save.c_str(), FILE_ATTRIBUTE_NORMAL) != 0, "clear_readonly_fixture");
        check(refused_readonly && memory->sram_dirty() && read_file(save) == original,
              "readonly_destination_preserves_previous_save_and_dirty_flag");
#endif
        faults::mode = faults::Mode::none;
        check(interrupted_child(fs::absolute(argv[0]), fs::absolute(save)) == 42,
              "child_stops_during_actual_partial_temporary_write");
        auto abandoned = temporaries(root);
        check(abandoned.size() == 1 && fs::file_size(abandoned[0]) == 1024 && read_file(save) == original,
              "interrupted_write_keeps_original_and_partial_temporary_separate");
        auto fresh = std::make_unique<dwm2t::Memory>();
        check(dwm2t::load_sram_file(*fresh, save) && Bytes(fresh->sram().begin(), fresh->sram().end()) == original,
              "fresh_load_reads_original_instead_of_abandoned_temporary");
        const auto partial = read_file(abandoned[0]);
        faults::mode = faults::Mode::collision;
        check(dwm2t::save_sram_file(*memory, save) && !memory->sram_dirty(), "retry_after_exact_temporary_name_collision");
        check(fs::is_regular_file(faults::collision_path) &&
                  read_file(faults::collision_path) != Bytes(memory->sram().begin(), memory->sram().end()),
              "preexisting_exact_temporary_is_not_replaced");
        check(read_file(abandoned[0]) == partial && fs::file_size(save) == 32768 &&
                  read_file(save) == Bytes(memory->sram().begin(), memory->sram().end()),
              "recovery_persists_exact_sram_without_consuming_abandoned_temporary");
        check(temporaries(root).size() == 2, "only_the_two_expected_abandoned_temporaries_remain");
        std::cout << "SAVE_IO_FAULT_CONTRACTS_PASS checks=" << checks << " gameplay_test=false\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "SAVE_IO_FAULT_CONTRACTS_FAIL after=" << checks << " reason=" << error.what() << '\n';
        return 1;
    }
}
