#include "recomp/window.hpp"
#include "recomp/audio_device.hpp"
#include "recomp/audio_presentation.hpp"

#include "recomp/memory.hpp"
#include "recomp/runtime.hpp"

#ifdef _WIN32

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <mmsystem.h>

#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <iostream>
#include <thread>
#include <vector>

namespace dwm2t {
namespace {


class WaveOutSink {
public:
    explicit WaveOutSink(int preferred = -1, int volume = 5, bool smooth = true,
                         unsigned prefill_frames = Apu::SampleRate / 20)
        : presentation_(volume, smooth), prefill_frames_(prefill_frames) {
        WAVEFORMATEX format{};
        format.wFormatTag = WAVE_FORMAT_PCM;
        format.nChannels = 2;
        format.nSamplesPerSec = Apu::SampleRate;
        format.wBitsPerSample = 16;
        format.nBlockAlign = 4;
        format.nAvgBytesPerSec = format.nSamplesPerSec * format.nBlockAlign;
        const auto selected = select_audio_device(waveOutGetNumDevs(), preferred, [&](int device) {
            HWAVEOUT candidate = nullptr;
            const auto result = waveOutOpen(&candidate, device < 0 ? WAVE_MAPPER : UINT(device),
                                           &format, 0, 0, CALLBACK_NULL);
            if (result == MMSYSERR_NOERROR) handle_ = candidate;
            return unsigned(result);
        });
        ready_ = selected.ready;
        if (ready_ && prefill_frames_) {
            buffering_ = waveOutPause(handle_) == MMSYSERR_NOERROR;
            if (!buffering_) ready_ = false;
        }
        if (ready_) {
            std::cout << "AUDIO_OUTPUT_READY device=" << selected.device
                      << " rate=" << Apu::SampleRate
                      << " mapper_error=" << selected.mapper_error << '\n';
            std::cout << "AUDIO_PRESENTATION volume=" << volume
                      << " smoothing=" << (smooth ? "on" : "off")
                      << " prefill_frames=" << prefill_frames_ << '\n';
            if (selected.mapper_error)
                std::cerr << "Audio: Windows default mapper failed (error " << selected.mapper_error
                          << "); using explicit playback device " << selected.device
                          << ". Use --audio-devices and --audio-device N to choose another output.\n";
        } else {
            char message[MAXERRORLENGTH]{};
            waveOutGetErrorTextA(selected.error, message, MAXERRORLENGTH);
            std::cerr << "Audio output unavailable: WinMM error=" << selected.error
                      << " (" << message << "), enumerated_devices=" << waveOutGetNumDevs()
                      << ". Check the output device; original APU timing remains active.\n";
        }
    }

    ~WaveOutSink() {
        if (handle_ == nullptr) return;
        waveOutReset(handle_);
        for (auto& slot : slots_) {
            if (slot.prepared) {
                waveOutUnprepareHeader(handle_, &slot.header, sizeof(slot.header));
                slot.prepared = false;
            }
        }
        waveOutClose(handle_);
    }

    [[nodiscard]] bool ready() const { return ready_; }
    [[nodiscard]] unsigned empty_events() const { return empty_events_; }
    [[nodiscard]] std::size_t submitted_frames() const { return total_frames_; }

    std::size_t submit(std::vector<std::int32_t> samples) {
        if (!ready_ || samples.empty()) return 0;
        if (!buffering_ && total_frames_) {
            bool pending = false;
            for (const auto& slot : slots_)
                pending |= slot.prepared && !(slot.header.dwFlags & WHDR_DONE);
            if (!pending) {
                ++empty_events_;
                if (prefill_frames_) {
                    buffering_ = waveOutPause(handle_) == MMSYSERR_NOERROR;
                    paused_frames_ = 0;
                    if (!buffering_) { ready_ = false; return 0; }
                }
            }
        }

        std::size_t offset = 0;
        while (offset < samples.size()) {
            Slot* slot = find_free_slot();
            if (slot == nullptr) {
                // Host buffering must never stall emulated CPU/APU timing.
                // If Windows falls behind, discard only host presentation
                // samples; the emulated APU state continues uninterrupted.
                return offset;
            }

            const std::size_t count =
                std::min<std::size_t>(slot->data.size(), samples.size() - offset);
            for (std::size_t i = 0; i < count; ++i)
                slot->data[i] = presentation_.sample(samples[offset + i], unsigned((offset + i) % 2));

            slot->header = {};
            slot->header.lpData = reinterpret_cast<LPSTR>(slot->data.data());
            slot->header.dwBufferLength =
                static_cast<DWORD>(count * sizeof(std::int16_t));

            if (waveOutPrepareHeader(handle_, &slot->header, sizeof(slot->header)) !=
                MMSYSERR_NOERROR) {
                ready_ = false;
                std::cerr << "Audio output failed while preparing a playback buffer.\n";
                return offset;
            }
            slot->prepared = true;

            if (waveOutWrite(handle_, &slot->header, sizeof(slot->header)) !=
                MMSYSERR_NOERROR) {
                waveOutUnprepareHeader(handle_, &slot->header, sizeof(slot->header));
                slot->prepared = false;
                ready_ = false;
                std::cerr << "Audio output failed while submitting a playback buffer.\n";
                return offset;
            }
            offset += count;
            total_frames_ += count / 2;
            paused_frames_ += unsigned(count / 2);
            if (buffering_ && paused_frames_ >= prefill_frames_) {
                if (waveOutRestart(handle_) != MMSYSERR_NOERROR) {
                    ready_ = false;
                    std::cerr << "Audio output failed while starting the buffered stream.\n";
                    return offset;
                }
                buffering_ = false;
            }
        }
        return offset;
    }

    [[nodiscard]] unsigned played_frames() const {
        if (!handle_) return 0;
        MMTIME position{}; position.wType = TIME_SAMPLES;
        if (waveOutGetPosition(handle_, &position, sizeof(position)) != MMSYSERR_NOERROR ||
            position.wType != TIME_SAMPLES) return 0;
        return position.u.sample;
    }

private:
    static constexpr std::size_t SlotCount = 8;
    static constexpr std::size_t ValuesPerSlot = 4096;

    struct Slot {
        WAVEHDR header{};
        std::array<std::int16_t, ValuesPerSlot> data{};
        bool prepared = false;
    };

    Slot* find_free_slot() {
        for (std::size_t attempt = 0; attempt < SlotCount; ++attempt) {
            Slot& slot = slots_[next_slot_];
            next_slot_ = (next_slot_ + 1u) % SlotCount;

            if (slot.prepared) {
                if ((slot.header.dwFlags & WHDR_DONE) == 0) continue;
                waveOutUnprepareHeader(handle_, &slot.header, sizeof(slot.header));
                slot.prepared = false;
            }
            return &slot;
        }
        return nullptr;
    }

    HWAVEOUT handle_ = nullptr;
    std::array<Slot, SlotCount> slots_{};
    std::size_t next_slot_ = 0;
    bool ready_ = false;
    AudioPresentation presentation_;
    unsigned prefill_frames_, paused_frames_ = 0, empty_events_ = 0;
    std::size_t total_frames_ = 0;
    bool buffering_ = false;
};

struct WindowContext {
    const Renderer::Framebuffer* framebuffer = nullptr;
    std::uint8_t host_buttons = 0;
};

bool is_fatal_step(StepResult result) {
    return result == StepResult::MissingBank ||
           result == StepResult::Trapped ||
           result == StepResult::Stopped;
}

void set_button(WindowContext& context, std::uint8_t button, bool down) {
    if (down) context.host_buttons = static_cast<std::uint8_t>(context.host_buttons | button);
    else context.host_buttons = static_cast<std::uint8_t>(context.host_buttons & ~button);
}

void handle_key(WindowContext& context, WPARAM key, bool down) {
    switch (key) {
        case VK_RIGHT: set_button(context, JoyRight, down); break;
        case VK_LEFT: set_button(context, JoyLeft, down); break;
        case VK_UP: set_button(context, JoyUp, down); break;
        case VK_DOWN: set_button(context, JoyDown, down); break;
        case 'Z': set_button(context, JoyA, down); break;
        case 'X': set_button(context, JoyB, down); break;
        case VK_RETURN: set_button(context, JoyStart, down); break;
        case VK_BACK: set_button(context, JoySelect, down); break;
        default: break;
    }
}

LRESULT CALLBACK wnd_proc(HWND hwnd, UINT message, WPARAM wparam, LPARAM lparam) {
    auto* context = reinterpret_cast<WindowContext*>(GetWindowLongPtrW(hwnd, GWLP_USERDATA));
    if (message == WM_NCCREATE) {
        context = static_cast<WindowContext*>(reinterpret_cast<CREATESTRUCTW*>(lparam)->lpCreateParams);
        SetWindowLongPtrW(hwnd, GWLP_USERDATA, reinterpret_cast<LONG_PTR>(context));
    }
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

            if (context != nullptr && context->framebuffer != nullptr) {
                StretchDIBits(
                    dc, 0, 0, rect.right - rect.left, rect.bottom - rect.top,
                    0, 0, Renderer::Width, Renderer::Height,
                    context->framebuffer->data(), &info, DIB_RGB_COLORS, SRCCOPY);
            }
            EndPaint(hwnd, &ps);
            return 0;
        }
        case WM_KEYDOWN:
        case WM_SYSKEYDOWN:
            if (context != nullptr) handle_key(*context, wparam, true);
            return 0;
        case WM_KEYUP:
        case WM_SYSKEYUP:
            if (context != nullptr) handle_key(*context, wparam, false);
            return 0;
        case WM_KILLFOCUS:
            if (context != nullptr) context->host_buttons = 0;
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

HWND create_window(int scale, WindowContext& context,
                   const wchar_t* title = L"DWM2t Native Recomp") {
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
        0, class_name, title,
        WS_OVERLAPPEDWINDOW | WS_VISIBLE,
        CW_USEDEFAULT, CW_USEDEFAULT,
        desired.right - desired.left, desired.bottom - desired.top,
        nullptr, nullptr, instance, &context);
}

} // namespace

int list_audio_devices() {
    const unsigned count = waveOutGetNumDevs();
    std::cout << "WinMM playback devices: " << count << " (automatic/default = -1)\n";
    for (unsigned device = 0; device < count; ++device) {
        WAVEOUTCAPSA caps{};
        if (waveOutGetDevCapsA(device, &caps, sizeof(caps)) == MMSYSERR_NOERROR)
            std::cout << device << ": " << caps.szPname << '\n';
    }
    return 0;
}

int run_audio_playback_test(int device) {
    WaveOutSink audio(device);
    if (!audio.ready()) return 77; // Environmental absence is not an APU failure.
    Runtime runtime{};
    auto& memory = runtime.memory();
    std::vector<std::int32_t> pcm;
    std::uint64_t observed = 0;
    for (unsigned step = 0; step < 80'000'000 && pcm.size() < 16384; ++step) {
        const auto result = runtime.step();
        if (is_fatal_step(result)) {
            std::cerr << "AUDIO_PLAYBACK_FAIL original_runtime\n"; return 140;
        }
        if (memory.frame_counter() == observed) continue;
        observed = memory.frame_counter();
        const auto samples = memory.apu().take_playback_samples();
        if (observed >= 1800) pcm.insert(pcm.end(), samples.begin(), samples.end());
    }
    const auto nonzero = std::count_if(pcm.begin(), pcm.end(), [](auto s) { return s != 0; });
    int peak = 0;
    std::size_t clipped = 0;
    for (const auto value : pcm) {
        peak = (std::max)(peak, value < 0 ? -int(value) : int(value));
        if (value < -32768 || value > 32767) ++clipped;
    }
    if (pcm.size() < 16384 || !nonzero) {
        std::cerr << "AUDIO_PLAYBACK_FAIL original_pcm\n"; return 141;
    }
    const auto submitted = audio.submit(pcm);
    const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(2);
    while (audio.played_frames() < submitted / 2 && std::chrono::steady_clock::now() < deadline)
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    const auto played = audio.played_frames();
    if (submitted != pcm.size() || played < submitted / 2) {
        std::cerr << "AUDIO_PLAYBACK_FAIL submitted=" << submitted << " played_frames=" << played << '\n';
        return 142;
    }
    std::cout << "AUDIO_PLAYBACK_PASS original_pcm_values=" << pcm.size()
              << " nonzero=" << nonzero << " submitted=" << submitted
              << " premix_peak=" << peak << " exceeds_legacy_pcm=" << clipped
              << " played_frames=" << played << " subjective_hearing=not_assessed\n";
    return 0;
}

int run_audio_stream_test() {
    // Original cartridge music only. Capture first, then isolate Windows
    // streaming from CPU speed while introducing bounded host scheduling jitter.
    Runtime runtime{};
    auto& memory = runtime.memory();
    std::vector<std::vector<std::int32_t>> chunks;
    std::uint64_t observed = 0;
    for (unsigned step = 0; step < 120'000'000 && chunks.size() < 180; ++step) {
        const auto result = runtime.step();
        if (is_fatal_step(result)) return 144;
        if (memory.frame_counter() == observed) continue;
        observed = memory.frame_counter();
        auto samples = memory.apu().take_playback_samples();
        if (observed >= 1800) chunks.push_back(std::move(samples));
    }
    if (chunks.size() != 180) return 145;
    unsigned baseline_empty = 0;
    for (const bool buffered : {false, true}) {
        WaveOutSink audio(-1, 5, true, buffered ? Apu::SampleRate / 20 : 0);
        if (!audio.ready()) return 77;
        using Clock = std::chrono::steady_clock;
        auto deadline = Clock::now();
        for (std::size_t i = 0; i < chunks.size(); ++i) {
            std::this_thread::sleep_until(deadline);
            if (i % 17 == 5) std::this_thread::sleep_for(std::chrono::milliseconds(20));
            if (audio.submit(chunks[i]) != chunks[i].size()) {
                std::cerr << "AUDIO_STREAM_FAIL dropped_or_failed_submission\n";
                return 146;
            }
            deadline += std::chrono::microseconds(16742);
        }
        const auto finish = Clock::now() + std::chrono::seconds(2);
        while (audio.played_frames() < audio.submitted_frames() && Clock::now() < finish)
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
        const auto empty = audio.empty_events();
        std::cout << "AUDIO_STREAM_RESULT buffered=" << buffered
                  << " queued_frames=" << audio.submitted_frames()
                  << " played_frames=" << audio.played_frames()
                  << " queue_empty_events=" << empty << " injected_jitter_ms=20\n";
        if (!buffered) baseline_empty = empty;
        if (audio.played_frames() < audio.submitted_frames() || (buffered && empty)) {
            std::cerr << "AUDIO_STREAM_FAIL incomplete_or_empty_buffered_queue\n";
            return 147;
        }
    }
    std::cout << "AUDIO_STREAM_PASS original_music baseline_queue_empty_events="
              << baseline_empty << " buffered_queue_empty_events=0 subjective_quality=not_assessed\n";
    return 0;
}

int run_native_window(const Renderer::Framebuffer& framebuffer, int scale) {
    WindowContext context{&framebuffer};

    HWND hwnd = create_window(scale, context);
    if (hwnd == nullptr) {
        return 1;
    }

    MSG msg{};
    while (GetMessageW(&msg, nullptr, 0, 0) > 0) {
        TranslateMessage(&msg);
        DispatchMessageW(&msg);
    }

    return static_cast<int>(msg.wParam);
}

int run_live_window(
    Runtime& runtime,
    Renderer& renderer,
    const std::filesystem::path& sav_path,
    int scale,
    int audio_device,
    int audio_volume,
    bool audio_smooth) {

    if (!load_sram_file(runtime.memory(), sav_path)) {
        std::cerr << "M6 live FAIL: invalid SRAM file " << sav_path.string() << "\n";
        return 2;
    }

    renderer.render(runtime.memory(), true);
    WindowContext context{&renderer.framebuffer()};

    HWND hwnd = create_window(scale, context);
    if (hwnd == nullptr) {
        return 1;
    }

    WaveOutSink audio(audio_device, audio_volume, audio_smooth);

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
        memory.set_joypad_state(context.host_buttons);
        const std::uint64_t start_frame = memory.frame_counter();

        StepResult result = StepResult::Continue;
        std::size_t steps = 0;
        constexpr std::size_t max_steps_per_frame = 2'000'000;
        while (memory.frame_counter() == start_frame && steps < max_steps_per_frame) {
            result = runtime.step();
            ++steps;
            if (result == StepResult::Stopped) break;
            if (is_fatal_step(result)) break;
        }

        // A normal STOP freezes the cartridge clock until a new selected P1
        // edge. Keep pumping the native window so that input can wake it.
        if (is_fatal_step(result) && result != StepResult::Stopped) {
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

        audio.submit(memory.apu().take_playback_samples());

        renderer.render(memory, true);
        context.framebuffer = &renderer.framebuffer();
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
    return exit_code;
}

int run_linked_windows(
    Runtime& first,
    Renderer& first_renderer,
    const std::filesystem::path& first_save,
    Runtime& second,
    Renderer& second_renderer,
    const std::filesystem::path& second_save,
    int scale,
    int audio_device,
    int audio_volume,
    bool audio_smooth) {

    const std::array<Runtime*, 2> runtimes{&first, &second};
    const std::array<Renderer*, 2> renderers{&first_renderer, &second_renderer};
    const std::array<std::filesystem::path, 2> saves{first_save, second_save};
    for (unsigned player = 0; player < 2; ++player) {
        if (!load_sram_file(runtimes[player]->memory(), saves[player])) {
            std::cerr << "LOCAL_LINK_FAIL player=" << player + 1
                      << " invalid_sram=" << saves[player].string() << '\n';
            return 2;
        }
        renderers[player]->render(runtimes[player]->memory(), true);
    }

    // The cable is an IO device. Both CPUs still execute the original boot,
    // dialogue and link protocol; no game variables or SRAM fields are set.
    struct Cable {
        Memory& memory;
        Cable(Memory& left, Memory& right) : memory(left) { memory.connect_link_peer(right); }
        ~Cable() { memory.disconnect_link_peer(); }
    } cable(first.memory(), second.memory());

    std::array<WindowContext, 2> contexts{{
        {&first_renderer.framebuffer()}, {&second_renderer.framebuffer()}}};
    std::array<HWND, 2> windows{};
    windows[0] = create_window(scale, contexts[0], L"DWM2t Native Recomp - Player 1 (local link)");
    if (windows[0] == nullptr) return 1;
    windows[1] = create_window(scale, contexts[1], L"DWM2t Native Recomp - Player 2 (local link)");
    if (windows[1] == nullptr) {
        DestroyWindow(windows[0]);
        return 1;
    }

    WaveOutSink audio(audio_device, audio_volume, audio_smooth);
    std::cout << "LOCAL_LINK_READY players=2 transport=local_serial audio=player1\n"
                 "Focus either window for Arrow/Z/X/Enter/Backspace controls. "
                 "Use Journal in each game; closing either window closes both.\n";

    using Clock = std::chrono::steady_clock;
    constexpr auto frame_period = std::chrono::microseconds(16742);
    constexpr std::size_t max_steps_per_frame = 2'000'000;
    auto next_frame = Clock::now();
    std::array<Clock::time_point, 2> last_save{next_frame, next_frame};
    std::array<bool, 2> sleeping{};
    std::array<std::uint64_t, 2> clock_offsets{};
    const auto clock = [&](unsigned player) {
        return runtimes[player]->memory().total_base_tcycles() + clock_offsets[player];
    };
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

        for (unsigned player = 0; player < 2; ++player)
            runtimes[player]->memory().set_joypad_state(contexts[player].host_buttons);

        const std::array<std::uint64_t, 2> start_frames{
            first.memory().frame_counter(), second.memory().frame_counter()};
        std::array<std::size_t, 2> steps{};
        const auto advance = [&](unsigned player) {
            auto& runtime = *runtimes[player];
            auto& memory = runtime.memory();
            if (steps[player]++ >= max_steps_per_frame) {
                std::cerr << "LOCAL_LINK_FAIL player=" << player + 1
                          << " frame_step_budget_exceeded\n";
                exit_code = 6;
                return;
            }
            const auto before = memory.total_base_tcycles();
            const auto result = runtime.step();
            if (result == StepResult::Stopped) {
                sleeping[player] = true;
                return;
            }
            if (result == StepResult::MissingBank || result == StepResult::Trapped) {
                const auto& cpu = runtime.cpu();
                exit_code = result == StepResult::MissingBank ? 3 : 4;
                std::cerr << "LOCAL_LINK_FAIL player=" << player + 1
                          << " result=" << static_cast<unsigned>(result)
                          << " bank=" << memory.current_rom_bank()
                          << " pc=0x" << std::hex << cpu.pc
                          << " trap_pc=0x" << cpu.trap_pc << std::dec
                          << " missing_bank=" << cpu.missing_bank << '\n';
                return;
            }
            if (memory.total_base_tcycles() <= before) {
                std::cerr << "LOCAL_LINK_FAIL player=" << player + 1
                          << " nonadvancing_base_clock\n";
                exit_code = 6;
                return;
            }
        };
        for (unsigned player = 0; player < 2; ++player) {
            if (!sleeping[player]) continue;
            // STOP freezes this cartridge's oscillator. Retry only after the
            // actual host P1 update; Runtime alone decides whether it wakes.
            // The host offset prevents a resumed CPU from fast-forwarding
            // through the other player's elapsed time. It never ticks Memory.
            if (clock(player) < clock(1 - player))
                clock_offsets[player] += clock(1 - player) - clock(player);
            sleeping[player] = false;
            advance(player);
            if (exit_code != 0) break;
        }
        if (exit_code != 0) break;
        while ((!sleeping[0] && first.memory().frame_counter() == start_frames[0]) ||
               (!sleeping[1] && second.memory().frame_counter() == start_frames[1])) {
            // Schedule in the shared base-clock domain. A CGB double-speed
            // CPU must not run its peer's serial/APU/PPU clock twice as fast.
            const unsigned player = sleeping[0] ? 1 : sleeping[1] ? 0 :
                                    clock(0) <= clock(1) ? 0 : 1;
            advance(player);
            if (exit_code != 0) break;
        }
        if (exit_code != 0) break;

        audio.submit(first.memory().apu().take_playback_samples());
        // The peer's APU continues to run, but its presentation queue must
        // also be drained even though only Player 1 is audible.
        (void)second.memory().apu().take_playback_samples();
        const auto now = Clock::now();
        for (unsigned player = 0; player < 2; ++player) {
            auto& memory = runtimes[player]->memory();
            renderers[player]->render(memory, true);
            contexts[player].framebuffer = &renderers[player]->framebuffer();
            InvalidateRect(windows[player], nullptr, FALSE);
            UpdateWindow(windows[player]);
            if (memory.sram_dirty() && now - last_save[player] >= std::chrono::seconds(2)) {
                if (!save_sram_file(memory, saves[player])) {
                    std::cerr << "LOCAL_LINK_FAIL player=" << player + 1
                              << " could_not_persist_sram\n";
                    exit_code = 7;
                    break;
                }
                last_save[player] = now;
            }
        }
        if (exit_code != 0) break;

        next_frame += frame_period;
        const auto after_work = Clock::now();
        if (next_frame > after_work) std::this_thread::sleep_until(next_frame);
        else if (after_work - next_frame > std::chrono::milliseconds(250)) next_frame = after_work;
    }

    // Attempt each pending write independently, including when the other
    // player failed. A failed write remains dirty in its own Memory object.
    for (unsigned player = 0; player < 2; ++player) {
        auto& memory = runtimes[player]->memory();
        memory.set_joypad_state(0);
        if (memory.sram_dirty() && !save_sram_file(memory, saves[player])) {
            std::cerr << "LOCAL_LINK_FAIL player=" << player + 1 << " final_sram_write_failed\n";
            if (exit_code == 0) exit_code = 7;
        }
    }
    for (auto window : windows)
        if (IsWindow(window)) DestroyWindow(window);
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
    WindowContext context{&renderer.framebuffer()};

    HWND hwnd = create_window(scale, context);
    if (hwnd == nullptr) {
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
    const bool keydown_ok = (context.host_buttons & JoyRight) != 0;

    // Prove that the Win32 keyboard mapping reaches the same P1/joypad state
    // used by the deterministic M6 movement regression, then release it
    // before advancing the cartridge boot path.
    runtime.memory().set_joypad_state(context.host_buttons);
    const bool p1_down_ok =
        (runtime.memory().joypad_state() & JoyRight) != 0;

    PostMessageW(hwnd, WM_KEYUP, VK_RIGHT, 0);
    pump_messages();
    const bool keyup_ok = (context.host_buttons & JoyRight) == 0;
    runtime.memory().set_joypad_state(context.host_buttons);
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
            std::cerr << "M6_WINDOW_SMOKE_FAIL runtime frame="
                      << frame_index
                      << " result=" << static_cast<unsigned>(result)
                      << " pc=0x" << std::hex << cpu.pc
                      << " missing_bank=" << std::dec << cpu.missing_bank
                      << "\n";
            return 82;
        }

        renderer.render(memory, true);
        context.framebuffer = &renderer.framebuffer();
        InvalidateRect(hwnd, nullptr, FALSE);
        UpdateWindow(hwnd);
        pump_messages();
    }

    runtime.memory().set_joypad_state(0);
    if (IsWindow(hwnd)) DestroyWindow(hwnd);
    pump_messages();

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
int run_live_window(Runtime&, Renderer&, const std::filesystem::path&, int, int, int, bool) { return 1; }
int run_linked_windows(Runtime&, Renderer&, const std::filesystem::path&,
                       Runtime&, Renderer&, const std::filesystem::path&,
                       int, int, int, bool) { return 1; }
int list_audio_devices() { return 1; }
int run_audio_playback_test(int) { return 77; }
int run_audio_stream_test() { return 77; }
int run_live_window_smoke(Runtime&, Renderer&, const std::filesystem::path&, int) { return 1; }
} // namespace dwm2t
#endif
