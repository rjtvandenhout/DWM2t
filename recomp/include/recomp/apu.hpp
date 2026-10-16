#pragma once
#include <array>
#include <cstdint>
#include <vector>

namespace dwm2t {

class Apu {
public:
    static constexpr std::uint32_t SampleRate = 32768;

    void reset();
    [[nodiscard]] std::uint8_t read(std::uint16_t address) const;
    void write(std::uint16_t address, std::uint8_t value);
    void tick_tcycle();

    [[nodiscard]] std::vector<std::int16_t> take_samples();
    [[nodiscard]] std::uint64_t sample_frames() const { return sample_frames_; }

private:
    struct Square {
        bool enabled = false;
        bool dac = false;
        bool length_enable = false;
        std::uint8_t duty = 0;
        std::uint8_t duty_pos = 0;
        std::uint8_t length = 0;
        std::uint8_t volume = 0;
        std::uint8_t envelope_period = 0;
        std::uint8_t envelope_timer = 0;
        bool envelope_add = false;
        std::uint16_t frequency = 0;
        std::uint16_t timer = 0;
        std::uint16_t shadow_frequency = 0;
        std::uint8_t sweep_period = 0;
        std::uint8_t sweep_timer = 0;
        std::uint8_t sweep_shift = 0;
        bool sweep_negate = false;
        bool sweep_enabled = false;
    };

    struct Wave {
        bool enabled = false;
        bool dac = false;
        bool length_enable = false;
        std::uint16_t length = 0;
        std::uint16_t frequency = 0;
        std::uint16_t timer = 0;
        std::uint8_t position = 0;
        std::uint8_t volume_code = 0;
    };

    struct Noise {
        bool enabled = false;
        bool dac = false;
        bool length_enable = false;
        std::uint8_t length = 0;
        std::uint8_t volume = 0;
        std::uint8_t envelope_period = 0;
        std::uint8_t envelope_timer = 0;
        bool envelope_add = false;
        std::uint8_t clock_shift = 0;
        std::uint8_t divisor_code = 0;
        bool width7 = false;
        std::uint32_t timer = 0;
        std::uint16_t lfsr = 0x7FFF;
    };

    void power_off();
    void trigger_square(Square& ch, bool sweep);
    void trigger_wave();
    void trigger_noise();
    void clock_frame_sequencer();
    void clock_length();
    void clock_envelopes();
    void clock_sweep();
    [[nodiscard]] std::uint16_t calculate_sweep(bool& overflow) const;
    [[nodiscard]] int square_output(const Square& ch) const;
    [[nodiscard]] int wave_output() const;
    [[nodiscard]] int noise_output() const;
    void emit_sample();

    std::array<std::uint8_t, 0x20> regs_{};
    std::array<std::uint8_t, 16> wave_ram_{};
    Square square1_{};
    Square square2_{};
    Wave wave_{};
    Noise noise_{};
    bool powered_ = false;
    std::uint32_t frame_seq_counter_ = 0;
    std::uint8_t frame_seq_step_ = 0;
    std::uint32_t sample_counter_ = 0;
    std::vector<std::int16_t> samples_{};
    std::uint64_t sample_frames_ = 0;
};

} // namespace dwm2t
