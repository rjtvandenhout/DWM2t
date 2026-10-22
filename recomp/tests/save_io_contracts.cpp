// Real filesystem contracts for host SRAM persistence, not gameplay evidence.
#include "recomp/atomic_sram.hpp"
#include "recomp/memory.hpp"
#include <array>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs = std::filesystem;
using Bytes = std::vector<std::uint8_t>;
unsigned checks = 0;
void check(bool ok, const char* name) {
    if (!ok) throw std::runtime_error(name);
    ++checks;
    std::cout << "SAVE_IO_PASS " << name << '\n';
}
Bytes read_file(const fs::path& path) {
    std::ifstream stream(path, std::ios::binary);
    if (!stream) throw std::runtime_error("cannot read synthetic fixture");
    return Bytes(std::istreambuf_iterator<char>(stream), {});
}
void write_fixture(const fs::path& path, const Bytes& data) {
    std::ofstream stream(path, std::ios::binary | std::ios::trunc);
    stream.write(reinterpret_cast<const char*>(data.data()), data.size());
    stream.close();
    if (!stream) throw std::runtime_error("cannot write synthetic fixture");
}
int main(int argc, char** argv) {
    try {
        if (argc != 2) throw std::runtime_error("expected evidence output directory");
        fs::create_directories(argv[1]);
        const auto tick = std::chrono::steady_clock::now().time_since_epoch().count();
        const auto root = fs::path(argv[1]) / ("save-io-" + std::to_string(tick));
        if (!fs::create_directory(root)) throw std::runtime_error("evidence already exists");
        std::cout << "SAVE_IO_EVIDENCE " << root.string() << '\n';
        Bytes first(dwm2t::Memory::SramSize), second(first.size());
        for (std::size_t i = 0; i < first.size(); ++i) {
            first[i] = static_cast<std::uint8_t>(i * 37u);
            second[i] = static_cast<std::uint8_t>(i * 17u + 9u);
        }
        const auto save = root / "original.sav";
        auto write = [&](const fs::path& path, const Bytes& data) {
            return dwm2t::save_io::write_sram_atomic(path, data.data(), data.size());
        };
        check(!dwm2t::save_io::write_sram_atomic({}, first.data(), first.size()), "reject_empty_path");
        check(!dwm2t::save_io::write_sram_atomic(save, nullptr, first.size()) && !fs::exists(save), "reject_null_input");
        check(!dwm2t::save_io::write_sram_atomic(save, first.data(), first.size()-1) && !fs::exists(save), "reject_wrong_size");
        check(write(save, first) && read_file(save) == first, "create_exact_sram");
        check(write(save, second) && read_file(save) == second, "replace_exact_sram");
        const auto nested = root / "new-parent" / "nested.sav";
        check(write(nested, first) && read_file(nested) == first, "create_parent_directory");
        const auto unicode = root / fs::path(u8"profile-\u00e9-\u2603.sav");
        check(write(unicode, first) && write(unicode, second) && read_file(unicode) == second, "unicode_save_path");
        const auto short_save = root / "short.sav";
        Bytes short_data(17, 0x5A); write_fixture(short_save, short_data);
        check(!write(short_save, second) && read_file(short_save) == short_data, "preserve_short_existing_file");
        const auto long_save = root / "long.sav";
        Bytes long_data(first.size()+1, 0x6B); write_fixture(long_save, long_data);
        check(!write(long_save, second) && read_file(long_save) == long_data, "preserve_oversized_existing_file");
        const auto directory = root / "directory.sav"; fs::create_directory(directory);
        check(!write(directory, first) && fs::is_directory(directory), "reject_directory_destination");
        const auto parent_file = root / "parent-file"; write_fixture(parent_file, short_data);
        check(!write(parent_file / "child.sav", first) && read_file(parent_file) == short_data, "preserve_blocked_parent");
        const auto orphan = root / "original.sav.tmp-stranded"; write_fixture(orphan, short_data);
        check(write(save, first) && read_file(save) == first && read_file(orphan) == short_data, "preserve_unrelated_temporary_file");
        auto memory = std::make_unique<dwm2t::Memory>();
        memory->write8(0, 0x0A); memory->write8(0xA123, 0x7B);
        check(memory->sram_dirty(), "cartridge_write_sets_dirty");
        check(!dwm2t::save_sram_file(*memory, directory) && memory->sram_dirty(), "failed_persistence_keeps_dirty");
        const auto memory_save = root / "memory.sav";
        check(dwm2t::save_sram_file(*memory, memory_save) && !memory->sram_dirty(), "successful_persistence_clears_dirty");
        auto fresh = std::make_unique<dwm2t::Memory>();
        check(dwm2t::load_sram_file(*fresh, memory_save) && fresh->sram() == memory->sram(), "fresh_memory_round_trip");
        const auto before = fresh->sram();
        check(!dwm2t::load_sram_file(*fresh, short_save) && fresh->sram() == before, "truncated_load_preserves_memory");
        check(!dwm2t::load_sram_file(*fresh, long_save) && fresh->sram() == before, "oversized_load_preserves_memory");
        const auto absent = root / "not-created.sav";
        check(dwm2t::load_sram_file(*fresh, absent) && !fs::exists(absent) && fresh->sram() == before, "missing_optional_save_is_not_created");
        std::error_code ec;
        const auto symlink = root / "linked.sav";
        fs::create_symlink(save, symlink, ec);
        if (!ec) {
            check(!write(symlink, second) && read_file(save) == first && fs::is_symlink(symlink), "reject_link_without_replacing_target");
        } else {
            std::cout << "SAVE_IO_CASE_UNAVAILABLE symlink " << ec.message() << '\n';
        }
#ifdef _WIN32
        HANDLE held = CreateFileW(save.c_str(), GENERIC_READ, FILE_SHARE_READ,
                                  nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
        if (held == INVALID_HANDLE_VALUE) throw std::runtime_error("cannot establish replacement-denial fixture");
        const bool denied = !write(save, second);
        CloseHandle(held);
        check(denied && read_file(save) == first, "denied_windows_replacement_preserves_previous_save");
#endif
        bool unexpected_temporary = false;
        for (const auto& entry : fs::recursive_directory_iterator(root)) {
            const auto name = entry.path().filename().string();
            if (name.find(".tmp-") != std::string::npos && entry.path() != orphan)
                unexpected_temporary = true;
        }
        check(!unexpected_temporary, "no_new_temporary_files_left");
        std::cout << "SAVE_IO_CONTRACTS_PASS checks=" << checks << " gameplay_test=false\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "SAVE_IO_CONTRACTS_FAIL after=" << checks << " reason=" << error.what() << '\n';
        return 1;
    }
}
