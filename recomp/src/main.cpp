#include "recomp/bank0.hpp"
#include "recomp/lr35902_exec.hpp"
#include "recomp/m6.hpp"
#include "recomp/m7.hpp"
#include "recomp/renderer.hpp"
#include "recomp/romx.hpp"
#include "recomp/runtime.hpp"
#include "recomp/window.hpp"

#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <string>
#include <string_view>

namespace {

constexpr std::string_view kTargetSha256 =
    "8e38a7420ef5239c7196aa4fd4b1499e65db2823e875bbf8241bb2199e766d4e";

bool test_embedded_rom_and_mbc5() {
    dwm2t::Memory memory{};
    dwm2t::load_full_rom_image(memory);

    const bool header_ok =
        memory.read8(0x0100) == 0x00 &&
        memory.read8(0x0101) == 0xC3 &&
        memory.read8(0x0147) == 0x1B &&
        memory.read8(0x0148) == 0x07 &&
        memory.read8(0x0149) == 0x03;

    const std::uint8_t bank1_first = memory.rom()[0x4000];
    const std::uint8_t bank2_first = memory.rom()[0x8000];

    const bool default_bank_ok =
        memory.current_rom_bank() == 1 &&
        memory.read8(0x4000) == bank1_first;

    memory.write8(0x2000, 0x02);
    const bool low_bank_ok =
        memory.current_rom_bank() == 2 &&
        memory.read8(0x4000) == bank2_first;

    memory.write8(0x2000, 0x00);
    memory.write8(0x3000, 0x01);
    const bool high_bit_ok = memory.current_rom_bank() == 0x100;

    memory.write8(0x3000, 0x00);
    memory.write8(0x0000, 0x0A);
    memory.write8(0x4000, 0x02);
    memory.write8(0xA123, 0x5A);
    const bool sram_ok =
        memory.ram_enabled() &&
        memory.current_ram_bank() == 2 &&
        memory.read8(0xA123) == 0x5A;

    return header_ok && default_bank_ok && low_bank_ok && high_bit_ok && sram_ok;
}

bool test_wram_vram_and_dma() {
    dwm2t::Memory memory{};
    dwm2t::load_full_rom_image(memory);

    memory.write8(0xFF70, 0x03);
    memory.write8(0xD000, 0xA3);
    memory.write8(0xFF70, 0x01);
    const bool wram_isolated = memory.read8(0xD000) != 0xA3;
    memory.write8(0xFF70, 0x03);
    const bool wram_restored = memory.read8(0xD000) == 0xA3;

    memory.write8(0xFF4F, 0x00);
    memory.write8(0x8000, 0x11);
    memory.write8(0xFF4F, 0x01);
    memory.write8(0x8000, 0x22);
    const bool vram1 = memory.read8(0x8000) == 0x22;
    memory.write8(0xFF4F, 0x00);
    const bool vram0 = memory.read8(0x8000) == 0x11;

    for (std::uint16_t i = 0; i < 0xA0; ++i) {
        memory.write8(static_cast<std::uint16_t>(0xC100 + i),
                      static_cast<std::uint8_t>(i ^ 0x5A));
    }
    memory.write8(0xFF46, 0xC1);

    bool dma_ok = true;
    for (std::uint16_t i = 0; i < 0xA0; ++i) {
        if (memory.read8(static_cast<std::uint16_t>(0xFE00 + i)) !=
            static_cast<std::uint8_t>(i ^ 0x5A)) {
            dma_ok = false;
            break;
        }
    }

    return wram_isolated && wram_restored && vram0 && vram1 && dma_ok;
}

bool test_timer_and_joypad() {
    dwm2t::Memory memory{};

    memory.write8(0xFF05, 0xFE);
    memory.write8(0xFF06, 0xA7);
    memory.write8(0xFF07, 0x05);
    memory.tick_tcycles(40);

    const bool timer_ok =
        memory.read8(0xFF05) == 0xA7 &&
        (memory.read8(0xFF0F) & 0x04) != 0;

    memory.write8(0xFF0F, 0);
    memory.write8(0xFF00, 0x10);
    memory.set_joypad_state(dwm2t::JoyA | dwm2t::JoyStart);
    const std::uint8_t p1 = memory.read8(0xFF00);

    const bool joypad_ok =
        (p1 & 0x01) == 0 &&
        (p1 & 0x08) == 0 &&
        (memory.read8(0xFF0F) & 0x10) != 0;

    return timer_ok && joypad_ok;
}

bool test_interrupt_entry() {
    dwm2t::Runtime runtime{};
    auto& cpu = runtime.cpu();
    auto& memory = runtime.memory();

    cpu.pc = 0x1234;
    cpu.sp = 0xDFF0;
    cpu.ime = true;
    memory.write8(0xFFFF, 0x01);
    memory.write8(0xFF0F, 0x01);

    const std::uint64_t before = memory.total_tcycles();
    const auto result = runtime.step();

    return result == dwm2t::StepResult::Continue &&
           cpu.pc == 0x0040 &&
           cpu.sp == 0xDFEE &&
           memory.read8(0xDFEE) == 0x34 &&
           memory.read8(0xDFEF) == 0x12 &&
           !cpu.ime &&
           (memory.read8(0xFF0F) & 1u) == 0 &&
           memory.total_tcycles() - before == 20;
}

bool test_halt_bug_trigger() {
    dwm2t::Cpu cpu{};
    dwm2t::Memory memory{};

    cpu.ime = false;
    memory.write8(0xFFFF, 0x01);
    memory.write8(0xFF0F, 0x01);
    dwm2t::lr35902::exec_base<0x76>(cpu, memory, 0, 0, 0x2000);
    return !cpu.halted && cpu.halt_bug;
}

bool test_native_romx_bank2_call() {
    dwm2t::Runtime runtime{};
    auto& cpu = runtime.cpu();
    auto& memory = runtime.memory();

    memory.write8(0x2000, 0x02);
    memory.write8(0xC525, 0x01);

    cpu = dwm2t::Cpu{};
    cpu.pc = 0x42FA;
    cpu.sp = 0xDFF0;
    dwm2t::lr35902::push16(cpu, memory, 0x8000);

    dwm2t::StepResult result = dwm2t::StepResult::Continue;
    for (std::size_t i = 0; i < 10000; ++i) {
        if (cpu.pc == 0x8000) break;
        result = runtime.step();
        if (result != dwm2t::StepResult::Continue) break;
    }

    constexpr std::uint8_t expected[8] = {
        0x00, 0x7C, 0xFF, 0x7F, 0xE0, 0x01, 0x00, 0x00
    };

    bool copy1 = true;
    bool copy2 = true;
    for (std::uint16_t i = 0; i < 8; ++i) {
        copy1 &= memory.read8(static_cast<std::uint16_t>(0xC49F + i)) == expected[i];
        copy2 &= memory.read8(static_cast<std::uint16_t>(0xC4DF + i)) == expected[i];
    }

    return result == dwm2t::StepResult::Continue &&
           cpu.pc == 0x8000 &&
           copy1 &&
           copy2 &&
           memory.read8(0xC526) == 0x7F &&
           memory.read8(0xC527) == 0x7F;
}

void set_cgb_color(
    dwm2t::Memory& memory,
    bool obj,
    unsigned palette,
    unsigned color,
    std::uint16_t bgr555) {

    const std::uint16_t index_reg = obj ? 0xFF6A : 0xFF68;
    const std::uint16_t data_reg = obj ? 0xFF6B : 0xFF69;
    const std::uint8_t index =
        static_cast<std::uint8_t>(palette * 8u + color * 2u);

    memory.write8(index_reg, index);
    memory.write8(data_reg, static_cast<std::uint8_t>(bgr555));
    memory.write8(index_reg, static_cast<std::uint8_t>(index + 1));
    memory.write8(data_reg, static_cast<std::uint8_t>(bgr555 >> 8));
}

void make_renderer_fixture(dwm2t::Memory& memory) {
    memory.clear();

    set_cgb_color(memory, false, 0, 0, 0x7FFF);
    set_cgb_color(memory, false, 0, 1, 0x001F);
    set_cgb_color(memory, false, 0, 2, 0x03E0);
    set_cgb_color(memory, false, 0, 3, 0x7C00);

    set_cgb_color(memory, false, 1, 0, 0x0000);
    set_cgb_color(memory, false, 1, 1, 0x03FF);
    set_cgb_color(memory, false, 1, 2, 0x7C1F);
    set_cgb_color(memory, false, 1, 3, 0x7FE0);

    set_cgb_color(memory, true, 1, 0, 0x0000);
    set_cgb_color(memory, true, 1, 1, 0x7C00);
    set_cgb_color(memory, true, 1, 2, 0x03E0);
    set_cgb_color(memory, true, 1, 3, 0x01FF);

    memory.write8(0xFF4F, 0);
    for (unsigned row = 0; row < 8; ++row) {
        memory.write8(static_cast<std::uint16_t>(0x8000 + row * 2), 0xAA);
        memory.write8(static_cast<std::uint16_t>(0x8001 + row * 2), 0x00);
    }

    // Sprite tile 2: transparent border, opaque color 3 center.
    for (unsigned row = 0; row < 8; ++row) {
        const std::uint8_t bits = (row == 0 || row == 7) ? 0x00 : 0x7E;
        memory.write8(static_cast<std::uint16_t>(0x8020 + row * 2), bits);
        memory.write8(static_cast<std::uint16_t>(0x8021 + row * 2), bits);
    }

    for (unsigned i = 0; i < 32u * 32u; ++i) {
        memory.write8(static_cast<std::uint16_t>(0x9800 + i), 0);
        memory.write8(static_cast<std::uint16_t>(0x9C00 + i), 1);
    }

    memory.write8(0xFF4F, 1);
    for (unsigned row = 0; row < 8; ++row) {
        memory.write8(static_cast<std::uint16_t>(0x8010 + row * 2), 0xCC);
        memory.write8(static_cast<std::uint16_t>(0x8011 + row * 2), 0x33);
    }

    for (unsigned i = 0; i < 32u * 32u; ++i) {
        memory.write8(static_cast<std::uint16_t>(0x9800 + i), 0x00);
        memory.write8(static_cast<std::uint16_t>(0x9C00 + i), 0x69);
    }

    memory.write8(0xFF4F, 0);

    memory.write8(0xFE00, 64 + 16);
    memory.write8(0xFE01, 72 + 8);
    memory.write8(0xFE02, 2);
    memory.write8(0xFE03, 1);

    memory.write8(0xFF42, 5);
    memory.write8(0xFF43, 3);
    memory.write8(0xFF4A, 40);
    memory.write8(0xFF4B, 47);

    // LCD on, window map $9C00, window on, $8000 tile addressing,
    // sprites on, BG/window master priority on.
    memory.write8(0xFF40, 0xF3);
}

bool test_renderer(
    dwm2t::Renderer& renderer,
    const std::filesystem::path* bmp_path,
    std::uint64_t& out_hash) {

    dwm2t::Memory memory{};
    make_renderer_fixture(memory);

    const auto& first = renderer.render(memory, true);
    out_hash = renderer.hash();

    const std::uint32_t sprite_center =
        first[67 * dwm2t::Renderer::Width + 75];

    const std::uint64_t first_hash = out_hash;
    renderer.render(memory, true);
    const bool deterministic = renderer.hash() == first_hash;

    bool diverse = false;
    const std::uint32_t first_pixel = first[0];
    for (const std::uint32_t pixel : first) {
        if (pixel != first_pixel) {
            diverse = true;
            break;
        }
    }

    bool bmp_ok = true;
    if (bmp_path != nullptr) {
        bmp_ok = renderer.write_bmp(*bmp_path);
    }

    // BGR555 $01FF -> R=255, G=123, B=0 in the deterministic converter.
    constexpr std::uint32_t expected_sprite_center = 0xFFFF7B00u;

    return deterministic &&
           diverse &&
           sprite_center == expected_sprite_center &&
           first_hash != 0 &&
           bmp_ok;
}


int run_title_probe(const std::filesystem::path& output_dir) {
    std::filesystem::create_directories(output_dir);

    dwm2t::Runtime runtime{};
    dwm2t::Renderer renderer{};

    auto& cpu = runtime.cpu();
    auto& memory = runtime.memory();

    std::uint64_t observed_frame = memory.frame_counter();
    std::uint8_t last_state = memory.read8(0xC5DB);
    std::uint8_t last_substate = memory.read8(0xC5DC);
    std::uint64_t last_hash = 0;
    unsigned stable_frames = 0;
    bool have_frame = false;

    constexpr std::size_t max_steps = 80'000'000;
    constexpr std::uint64_t max_frames = 2400;

    std::cout << "M5 title boot probe: starting real CGB cartridge path at $0100\\n";
    std::cout << "AOT ROMX bank count: " << dwm2t::translated_romx_bank_count() << "\\n";

    for (std::size_t step = 0; step < max_steps; ++step) {
        const dwm2t::StepResult result = runtime.step();

        if (result == dwm2t::StepResult::MissingBank) {
            if (have_frame) {
                renderer.write_bmp(output_dir / "last_frame_before_missing_bank.bmp");
            }
            std::cout
                << "M5_PROBE_MISSING_BANK bank=" << cpu.missing_bank
                << " pc=0x" << std::hex << cpu.pc << std::dec
                << " frame=" << memory.frame_counter()
                << " C5DB=" << static_cast<unsigned>(memory.read8(0xC5DB))
                << " C5DC=" << static_cast<unsigned>(memory.read8(0xC5DC))
                << " steps=" << step << "\\n";
            return 20;
        }

        if (result == dwm2t::StepResult::Trapped) {
            if (have_frame) {
                renderer.write_bmp(output_dir / "last_frame_before_trap.bmp");
            }
            std::cout
                << "M5_PROBE_TRAP pc=0x" << std::hex << cpu.trap_pc
                << " opcode=0x" << static_cast<unsigned>(cpu.trap_opcode)
                << std::dec
                << " bank=" << memory.current_rom_bank()
                << " frame=" << memory.frame_counter()
                << " C5DB=" << static_cast<unsigned>(memory.read8(0xC5DB))
                << " C5DC=" << static_cast<unsigned>(memory.read8(0xC5DC))
                << " steps=" << step << "\\n";
            return 21;
        }

        if (result == dwm2t::StepResult::Stopped) {
            std::cout
                << "M5_PROBE_STOP pc=0x" << std::hex << cpu.pc << std::dec
                << " frame=" << memory.frame_counter() << "\\n";
            return 22;
        }

        const std::uint64_t frame = memory.frame_counter();
        if (frame != observed_frame) {
            observed_frame = frame;
            renderer.render(memory, true);
            have_frame = true;
            const std::uint64_t hash = renderer.hash();

            if (hash == last_hash) ++stable_frames;
            else stable_frames = 0;
            last_hash = hash;

            const std::uint8_t state = memory.read8(0xC5DB);
            const std::uint8_t substate = memory.read8(0xC5DC);
            const bool state_changed = state != last_state || substate != last_substate;
            last_state = state;
            last_substate = substate;

            const bool checkpoint =
                frame <= 5 ||
                frame == 15 ||
                frame == 30 ||
                frame == 60 ||
                frame == 90 ||
                frame == 120 ||
                frame == 180 ||
                frame == 240 ||
                frame == 360 ||
                frame == 480 ||
                frame == 600 ||
                frame == 750 ||
                frame == 900 ||
                (frame > 900 && frame % 120 == 0) ||
                state_changed;

            if (checkpoint) {
                const std::string file =
                    "frame_" + std::to_string(frame) +
                    "_state_" + std::to_string(state) +
                    "_" + std::to_string(substate) +
                    ".bmp";
                renderer.write_bmp(output_dir / file);
            }

            if (frame <= 10 || frame % 30 == 0 || state_changed) {
                std::cout
                    << "M5_FRAME frame=" << frame
                    << " hash=0x" << std::hex << hash << std::dec
                    << " stable=" << stable_frames
                    << " C5DB=" << static_cast<unsigned>(state)
                    << " C5DC=" << static_cast<unsigned>(substate)
                    << " bank=" << memory.current_rom_bank()
                    << " pc=0x" << std::hex << cpu.pc << std::dec
                    << "\\n";
            }

            if (frame >= max_frames) {
                renderer.write_bmp(output_dir / "probe_final_frame.bmp");
                std::cout
                    << "M5_PROBE_FRAME_BUDGET frame=" << frame
                    << " hash=0x" << std::hex << hash << std::dec
                    << " stable=" << stable_frames
                    << " C5DB=" << static_cast<unsigned>(state)
                    << " C5DC=" << static_cast<unsigned>(substate)
                    << "\\n";
                return 0;
            }
        }
    }

    if (have_frame) renderer.write_bmp(output_dir / "probe_step_budget_frame.bmp");
    std::cout << "M5_PROBE_STEP_BUDGET steps=" << max_steps
              << " frame=" << memory.frame_counter() << "\\n";
    return 23;
}

constexpr std::uint64_t kM5TitleHash = 0x49c67a53ef4f8a80ull;
constexpr unsigned kM5TitleStableFrames = 30;

int run_title_regression(
    const std::filesystem::path* bmp_path,
    bool show_window) {

    dwm2t::Runtime runtime{};
    dwm2t::Renderer renderer{};

    auto& cpu = runtime.cpu();
    auto& memory = runtime.memory();

    std::uint64_t observed_frame = memory.frame_counter();
    unsigned title_stable_frames = 0;

    constexpr std::size_t max_steps = 80'000'000;
    constexpr std::uint64_t max_frames = 2400;

    std::cout
        << "M5 original-title regression: booting recompiled DWM2 from $0100\n";
    std::cout
        << "AOT ROMX bank count: "
        << dwm2t::translated_romx_bank_count() << "\n";

    for (std::size_t step = 0; step < max_steps; ++step) {
        const dwm2t::StepResult result = runtime.step();

        if (result == dwm2t::StepResult::MissingBank) {
            std::cerr
                << "M5 FAIL: missing AOT ROMX bank " << cpu.missing_bank
                << " at pc=0x" << std::hex << cpu.pc << std::dec
                << " frame=" << memory.frame_counter() << "\n";
            return 30;
        }

        if (result == dwm2t::StepResult::Trapped) {
            std::cerr
                << "M5 FAIL: trap at pc=0x" << std::hex << cpu.trap_pc
                << " opcode=0x" << static_cast<unsigned>(cpu.trap_opcode)
                << std::dec
                << " bank=" << memory.current_rom_bank()
                << " frame=" << memory.frame_counter() << "\n";
            return 31;
        }

        if (result == dwm2t::StepResult::Stopped) {
            std::cerr
                << "M5 FAIL: unexpected STOP at pc=0x"
                << std::hex << cpu.pc << std::dec
                << " frame=" << memory.frame_counter() << "\n";
            return 32;
        }

        const std::uint64_t frame = memory.frame_counter();
        if (frame == observed_frame) continue;
        observed_frame = frame;

        renderer.render(memory, true);
        const std::uint64_t hash = renderer.hash();
        const std::uint8_t state = memory.read8(0xC5DB);
        const std::uint8_t substate = memory.read8(0xC5DC);

        if (hash == kM5TitleHash && state == 5 && substate == 0) {
            ++title_stable_frames;
        } else {
            title_stable_frames = 0;
        }

        if (title_stable_frames >= kM5TitleStableFrames) {
            if (bmp_path != nullptr && !renderer.write_bmp(*bmp_path)) {
                std::cerr << "M5 FAIL: could not write title BMP\n";
                return 33;
            }

            std::cout
                << "M5_TITLE_REACHED frame=" << frame
                << " hash=0x" << std::hex << hash << std::dec
                << " stable_frames=" << title_stable_frames
                << " C5DB=" << static_cast<unsigned>(state)
                << " C5DC=" << static_cast<unsigned>(substate)
                << "\n";
            std::cout
                << "M5 PASS: original DWM2 Cobi title framebuffer was produced "
                   "by the recompiled cartridge boot path.\n";

            if (show_window) {
                return dwm2t::run_native_window(renderer.framebuffer(), 4);
            }
            return EXIT_SUCCESS;
        }

        if (frame >= max_frames) {
            std::cerr
                << "M5 FAIL: title hash 0x" << std::hex << kM5TitleHash
                << std::dec << " did not remain stable for "
                << kM5TitleStableFrames
                << " frames before frame budget " << max_frames << "\n";
            return 34;
        }
    }

    std::cerr << "M5 FAIL: step budget exceeded before title screen\n";
    return 35;
}

void print_result(std::string_view name, bool ok) {
    std::cout << name << ": " << (ok ? "PASS" : "FAIL") << "\n";
}

int run_self_tests(const std::filesystem::path* bmp_path) {
    std::cout << "DWM2t native static recomp - milestone M4\n";
    std::cout << "Target ROM SHA-256: " << kTargetSha256 << "\n\n";

    const bool mbc_ok = test_embedded_rom_and_mbc5();
    const bool memory_ok = test_wram_vram_and_dma();
    const bool timer_input_ok = test_timer_and_joypad();
    const bool interrupt_ok = test_interrupt_entry();
    const bool halt_ok = test_halt_bug_trigger();
    const bool bank2_ok = test_native_romx_bank2_call();

    dwm2t::Renderer renderer{};
    std::uint64_t render_hash = 0;
    const bool renderer_ok = test_renderer(renderer, bmp_path, render_hash);

    print_result("M3 mapped hardware regression suite", 
        mbc_ok && memory_ok && timer_input_ok && interrupt_ok && halt_ok && bank2_ok);
    print_result("CGB BG/window/OAM/palette software renderer", renderer_ok);

    std::cout << "Renderer FNV-1a: 0x"
              << std::hex << std::setw(16) << std::setfill('0')
              << render_hash << std::dec << "\n";

    if (!mbc_ok || !memory_ok || !timer_input_ok ||
        !interrupt_ok || !halt_ok || !bank2_ok || !renderer_ok) {
        std::cerr << "\nM4 native visual runtime self-test failed.\n";
        return EXIT_FAILURE;
    }

    std::cout
        << "\nM4 PASS: the native recomp now renders Game Boy Color tilemaps, "
           "window layers, OAM sprites and palettes into a deterministic "
           "160x144 host framebuffer and can present it in a Win32 window.\n";
    std::cout
        << "Next milestone: M5 original DWM2 title screen from recompiled game code.\n";
    return EXIT_SUCCESS;
}

} // namespace

int main(int argc, char** argv) {
    if (argc >= 2 && std::string_view(argv[1]) == "--m7-discovery") {
        if (argc != 3) {
            std::cerr << "Usage: DWM2tRecomp.exe --m7-discovery <output-dir>\\n";
            return EXIT_FAILURE;
        }
        return dwm2t::run_m7_discovery(argv[2]);
    }

    if (argc >= 2 && std::string_view(argv[1]) == "--m6-window-smoke") {
        if (argc != 3) {
            std::cerr << "Usage: DWM2tRecomp.exe --m6-window-smoke <save-path>\\n";
            return EXIT_FAILURE;
        }
        dwm2t::Runtime runtime{};
        dwm2t::Renderer renderer{};
        return dwm2t::run_live_window_smoke(runtime, renderer, argv[2], 2);
    }

    if (argc >= 2 && std::string_view(argv[1]) == "--play") {
        if (argc != 2 && argc != 3) {
            std::cerr << "Usage: DWM2tRecomp.exe --play [save-path]\\n";
            return EXIT_FAILURE;
        }
        const std::filesystem::path save_path =
            argc == 3 ? std::filesystem::path(argv[2]) : std::filesystem::path("DWM2t.sav");
        dwm2t::Runtime runtime{};
        dwm2t::Renderer renderer{};
        return dwm2t::run_live_window(runtime, renderer, save_path, 4);
    }

    if (argc >= 2 && std::string_view(argv[1]) == "--m6-sram-test") {
        if (argc != 3) {
            std::cerr << "Usage: DWM2tRecomp.exe --m6-sram-test <save-path>\\n";
            return EXIT_FAILURE;
        }
        return dwm2t::run_m6_sram_test(argv[2]);
    }

    if (argc >= 2 && std::string_view(argv[1]) == "--m6-probe") {
        if (argc != 3) {
            std::cerr << "Usage: DWM2tRecomp.exe --m6-probe <output-dir>\\n";
            return EXIT_FAILURE;
        }
        return dwm2t::run_m6_probe(argv[2]);
    }

    if (argc >= 2 && std::string_view(argv[1]) == "--title-test") {
        if (argc != 3) {
            std::cerr << "Usage: DWM2tRecomp.exe --title-test <bmp-path>\\n";
            return EXIT_FAILURE;
        }
        const std::filesystem::path title_bmp = argv[2];
        return run_title_regression(&title_bmp, false);
    }

    if (argc >= 2 && std::string_view(argv[1]) == "--title-window") {
        if (argc != 2) {
            std::cerr << "Usage: DWM2tRecomp.exe --title-window\\n";
            return EXIT_FAILURE;
        }
        return run_title_regression(nullptr, true);
    }

    if (argc >= 2 && std::string_view(argv[1]) == "--title-probe") {
        if (argc != 3) {
            std::cerr << "Usage: DWM2tRecomp.exe --title-probe <output-dir>\\n";
            return EXIT_FAILURE;
        }
        return run_title_probe(argv[2]);
    }

    if (argc >= 2 && std::string_view(argv[1]) == "--window-test") {
        dwm2t::Memory memory{};
        make_renderer_fixture(memory);
        dwm2t::Renderer renderer{};
        renderer.render(memory, true);
        return dwm2t::run_native_window(renderer.framebuffer(), 4);
    }

    std::filesystem::path bmp_path;
    const std::filesystem::path* bmp_ptr = nullptr;

    if (argc >= 2 && std::string_view(argv[1]) != "--self-test") {
        std::cerr
            << "Usage: DWM2tRecomp.exe [--self-test [--bmp path]] | --window-test\n";
        return EXIT_FAILURE;
    }

    if (argc == 4 && std::string_view(argv[2]) == "--bmp") {
        bmp_path = argv[3];
        bmp_ptr = &bmp_path;
    } else if (argc != 1 && argc != 2) {
        std::cerr
            << "Usage: DWM2tRecomp.exe [--self-test [--bmp path]] | --window-test\n";
        return EXIT_FAILURE;
    }

    return run_self_tests(bmp_ptr);
}
