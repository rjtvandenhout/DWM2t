#include "recomp/apu.hpp"

#include <algorithm>
#include <array>
#include <cstdint>
#include <utility>

namespace dwm2t {
namespace {

constexpr std::array<std::array<int, 8>, 4> kDuty = {{
    {{0,0,0,0,0,0,0,1}},
    {{1,0,0,0,0,0,0,1}},
    {{1,0,0,0,0,1,1,1}},
    {{0,1,1,1,1,1,1,0}},
}};

constexpr std::array<std::uint32_t, 8> kNoiseDivisor = {
    8, 16, 32, 48, 64, 80, 96, 112
};

std::uint16_t square_period(std::uint16_t frequency) {
    return static_cast<std::uint16_t>(
        std::max<unsigned>(4u, (2048u - (frequency & 0x07FFu)) * 4u));
}

std::uint16_t wave_period(std::uint16_t frequency) {
    return static_cast<std::uint16_t>(
        std::max<unsigned>(2u, (2048u - (frequency & 0x07FFu)) * 2u));
}

std::int16_t clamp16(int value) {
    return static_cast<std::int16_t>(std::clamp(value, -32768, 32767));
}

} // namespace

void Apu::reset() {
    regs_.fill(0);
    wave_ram_.fill(0);
    square1_ = {};
    square2_ = {};
    wave_ = {};
    noise_ = {};
    powered_ = false;
    frame_seq_counter_ = 0;
    frame_seq_step_ = 0;
    sample_counter_ = 0;
    samples_.clear();
    sample_frames_ = 0;
}

void Apu::power_off() {
    regs_.fill(0);
    square1_ = {};
    square2_ = {};
    wave_ = {};
    noise_ = {};
    powered_ = false;
    frame_seq_counter_ = 0;
    frame_seq_step_ = 0;
}

std::uint8_t Apu::read(std::uint16_t address) const {
    if (address >= 0xFF30 && address <= 0xFF3F) {
        return wave_ram_[address - 0xFF30u];
    }
    if (address == 0xFF26) {
        std::uint8_t value = powered_ ? 0xF0u : 0x70u;
        if (square1_.enabled) value |= 0x01u;
        if (square2_.enabled) value |= 0x02u;
        if (wave_.enabled) value |= 0x04u;
        if (noise_.enabled) value |= 0x08u;
        return value;
    }
    if (address >= 0xFF10 && address <= 0xFF2F) {
        return regs_[address - 0xFF10u];
    }
    return 0xFF;
}

void Apu::trigger_square(Square& ch, bool sweep) {
    if (ch.length == 0) ch.length = 64;
    ch.enabled = ch.dac;
    ch.timer = square_period(ch.frequency);
    ch.duty_pos = 0;
    ch.envelope_timer = ch.envelope_period == 0 ? 8 : ch.envelope_period;
    if (!sweep) return;

    ch.shadow_frequency = ch.frequency;
    ch.sweep_timer = ch.sweep_period == 0 ? 8 : ch.sweep_period;
    ch.sweep_enabled = ch.sweep_period != 0 || ch.sweep_shift != 0;
    if (ch.sweep_shift != 0) {
        bool overflow = false;
        (void)calculate_sweep(overflow);
        if (overflow) ch.enabled = false;
    }
}

void Apu::trigger_wave() {
    if (wave_.length == 0) wave_.length = 256;
    wave_.enabled = wave_.dac;
    wave_.timer = wave_period(wave_.frequency);
    wave_.position = 0;
}

void Apu::trigger_noise() {
    if (noise_.length == 0) noise_.length = 64;
    noise_.enabled = noise_.dac;
    noise_.lfsr = 0x7FFF;
    const std::uint32_t base = kNoiseDivisor[noise_.divisor_code & 7u];
    noise_.timer = std::max<std::uint32_t>(8u, base << noise_.clock_shift);
    noise_.envelope_timer =
        noise_.envelope_period == 0 ? 8 : noise_.envelope_period;
}

std::uint16_t Apu::calculate_sweep(bool& overflow) const {
    const std::uint16_t delta =
        static_cast<std::uint16_t>(square1_.shadow_frequency >> square1_.sweep_shift);
    const int next = square1_.sweep_negate
        ? static_cast<int>(square1_.shadow_frequency) - static_cast<int>(delta)
        : static_cast<int>(square1_.shadow_frequency) + static_cast<int>(delta);
    overflow = next < 0 || next > 2047;
    return static_cast<std::uint16_t>(next & 0x07FF);
}

void Apu::write(std::uint16_t address, std::uint8_t value) {
    if (address >= 0xFF30 && address <= 0xFF3F) {
        wave_ram_[address - 0xFF30u] = value;
        return;
    }
    if (address == 0xFF26) {
        if ((value & 0x80u) == 0) {
            power_off();
        } else if (!powered_) {
            powered_ = true;
            frame_seq_counter_ = 0;
            frame_seq_step_ = 0;
            regs_[0x16] = 0x80;
        }
        return;
    }
    if (address < 0xFF10 || address > 0xFF2F || !powered_) return;

    regs_[address - 0xFF10u] = value;
    switch (address) {
        case 0xFF10:
            square1_.sweep_period = static_cast<std::uint8_t>((value >> 4) & 7u);
            square1_.sweep_negate = (value & 0x08u) != 0;
            square1_.sweep_shift = static_cast<std::uint8_t>(value & 7u);
            break;
        case 0xFF11:
            square1_.duty = static_cast<std::uint8_t>(value >> 6);
            square1_.length = static_cast<std::uint8_t>(64u - (value & 0x3Fu));
            break;
        case 0xFF12:
            square1_.dac = (value & 0xF8u) != 0;
            square1_.volume = static_cast<std::uint8_t>(value >> 4);
            square1_.envelope_add = (value & 0x08u) != 0;
            square1_.envelope_period = static_cast<std::uint8_t>(value & 7u);
            if (!square1_.dac) square1_.enabled = false;
            break;
        case 0xFF13:
            square1_.frequency =
                static_cast<std::uint16_t>((square1_.frequency & 0x0700u) | value);
            break;
        case 0xFF14:
            square1_.frequency = static_cast<std::uint16_t>(
                (square1_.frequency & 0x00FFu) | ((value & 7u) << 8));
            square1_.length_enable = (value & 0x40u) != 0;
            if (value & 0x80u) trigger_square(square1_, true);
            break;
        case 0xFF16:
            square2_.duty = static_cast<std::uint8_t>(value >> 6);
            square2_.length = static_cast<std::uint8_t>(64u - (value & 0x3Fu));
            break;
        case 0xFF17:
            square2_.dac = (value & 0xF8u) != 0;
            square2_.volume = static_cast<std::uint8_t>(value >> 4);
            square2_.envelope_add = (value & 0x08u) != 0;
            square2_.envelope_period = static_cast<std::uint8_t>(value & 7u);
            if (!square2_.dac) square2_.enabled = false;
            break;
        case 0xFF18:
            square2_.frequency =
                static_cast<std::uint16_t>((square2_.frequency & 0x0700u) | value);
            break;
        case 0xFF19:
            square2_.frequency = static_cast<std::uint16_t>(
                (square2_.frequency & 0x00FFu) | ((value & 7u) << 8));
            square2_.length_enable = (value & 0x40u) != 0;
            if (value & 0x80u) trigger_square(square2_, false);
            break;
        case 0xFF1A:
            wave_.dac = (value & 0x80u) != 0;
            if (!wave_.dac) wave_.enabled = false;
            break;
        case 0xFF1B:
            wave_.length = static_cast<std::uint16_t>(256u - value);
            break;
        case 0xFF1C:
            wave_.volume_code = static_cast<std::uint8_t>((value >> 5) & 3u);
            break;
        case 0xFF1D:
            wave_.frequency =
                static_cast<std::uint16_t>((wave_.frequency & 0x0700u) | value);
            break;
        case 0xFF1E:
            wave_.frequency = static_cast<std::uint16_t>(
                (wave_.frequency & 0x00FFu) | ((value & 7u) << 8));
            wave_.length_enable = (value & 0x40u) != 0;
            if (value & 0x80u) trigger_wave();
            break;
        case 0xFF20:
            noise_.length = static_cast<std::uint8_t>(64u - (value & 0x3Fu));
            break;
        case 0xFF21:
            noise_.dac = (value & 0xF8u) != 0;
            noise_.volume = static_cast<std::uint8_t>(value >> 4);
            noise_.envelope_add = (value & 0x08u) != 0;
            noise_.envelope_period = static_cast<std::uint8_t>(value & 7u);
            if (!noise_.dac) noise_.enabled = false;
            break;
        case 0xFF22:
            noise_.clock_shift = static_cast<std::uint8_t>(value >> 4);
            noise_.width7 = (value & 0x08u) != 0;
            noise_.divisor_code = static_cast<std::uint8_t>(value & 7u);
            break;
        case 0xFF23:
            noise_.length_enable = (value & 0x40u) != 0;
            if (value & 0x80u) trigger_noise();
            break;
        default:
            break;
    }
}

void Apu::clock_length() {
    auto clock_square = [](Square& ch) {
        if (ch.length_enable && ch.length > 0 && --ch.length == 0) {
            ch.enabled = false;
        }
    };
    clock_square(square1_);
    clock_square(square2_);
    if (wave_.length_enable && wave_.length > 0 && --wave_.length == 0) {
        wave_.enabled = false;
    }
    if (noise_.length_enable && noise_.length > 0 && --noise_.length == 0) {
        noise_.enabled = false;
    }
}

void Apu::clock_envelopes() {
    auto clock = [](auto& ch) {
        if (ch.envelope_period == 0) return;
        if (ch.envelope_timer > 0) --ch.envelope_timer;
        if (ch.envelope_timer != 0) return;
        ch.envelope_timer = ch.envelope_period;
        if (ch.envelope_add) {
            if (ch.volume < 15) ++ch.volume;
        } else if (ch.volume > 0) {
            --ch.volume;
        }
    };
    clock(square1_);
    clock(square2_);
    clock(noise_);
}

void Apu::clock_sweep() {
    if (!square1_.sweep_enabled) return;
    if (square1_.sweep_timer > 0) --square1_.sweep_timer;
    if (square1_.sweep_timer != 0) return;
    square1_.sweep_timer = square1_.sweep_period == 0 ? 8 : square1_.sweep_period;
    if (square1_.sweep_period == 0) return;

    bool overflow = false;
    const std::uint16_t next = calculate_sweep(overflow);
    if (overflow) {
        square1_.enabled = false;
        return;
    }
    if (square1_.sweep_shift != 0) {
        square1_.shadow_frequency = next;
        square1_.frequency = next;
        square1_.timer = square_period(next);
        (void)calculate_sweep(overflow);
        if (overflow) square1_.enabled = false;
    }
}

void Apu::clock_frame_sequencer() {
    if ((frame_seq_step_ & 1u) == 0) clock_length();
    if (frame_seq_step_ == 2 || frame_seq_step_ == 6) clock_sweep();
    if (frame_seq_step_ == 7) clock_envelopes();
    frame_seq_step_ = static_cast<std::uint8_t>((frame_seq_step_ + 1u) & 7u);
}

int Apu::square_output(const Square& ch) const {
    if (!powered_ || !ch.enabled || !ch.dac) return 0;
    const int sign = kDuty[ch.duty & 3u][ch.duty_pos & 7u] ? 1 : -1;
    return sign * static_cast<int>(ch.volume);
}

int Apu::wave_output() const {
    if (!powered_ || !wave_.enabled || !wave_.dac || wave_.volume_code == 0) {
        return 0;
    }
    const std::uint8_t byte = wave_ram_[(wave_.position >> 1) & 0x0Fu];
    std::uint8_t sample =
        (wave_.position & 1u) == 0 ? static_cast<std::uint8_t>(byte >> 4)
                                   : static_cast<std::uint8_t>(byte & 0x0Fu);
    const unsigned shift = wave_.volume_code == 1 ? 0u :
                           wave_.volume_code == 2 ? 1u : 2u;
    sample = static_cast<std::uint8_t>(sample >> shift);
    return static_cast<int>(sample) - 8;
}

int Apu::noise_output() const {
    if (!powered_ || !noise_.enabled || !noise_.dac) return 0;
    const int sign = (noise_.lfsr & 1u) == 0 ? 1 : -1;
    return sign * static_cast<int>(noise_.volume);
}

void Apu::emit_sample() {
    const int channels[4] = {
        square_output(square1_),
        square_output(square2_),
        wave_output(),
        noise_output()
    };
    const std::uint8_t nr50 = regs_[0x14];
    const std::uint8_t nr51 = regs_[0x15];
    const int left_volume = static_cast<int>(((nr50 >> 4) & 7u) + 1u);
    const int right_volume = static_cast<int>((nr50 & 7u) + 1u);

    int left = 0;
    int right = 0;
    for (unsigned i = 0; i < 4; ++i) {
        if (nr51 & (1u << (i + 4))) left += channels[i];
        if (nr51 & (1u << i)) right += channels[i];
    }

    // Store the exact pre-gain mix (at most 4 * 15 * 8 in magnitude).
    // Legacy captures still scale/clamp identically in take_samples(); live
    // playback can attenuate before conversion rather than after clipping.
    samples_.push_back(static_cast<std::int16_t>(left * left_volume));
    samples_.push_back(static_cast<std::int16_t>(right * right_volume));
    ++sample_frames_;
}

void Apu::tick_tcycle() {
    if (powered_) {
        if (square1_.timer > 0) --square1_.timer;
        if (square1_.timer == 0) {
            square1_.timer = square_period(square1_.frequency);
            square1_.duty_pos =
                static_cast<std::uint8_t>((square1_.duty_pos + 1u) & 7u);
        }

        if (square2_.timer > 0) --square2_.timer;
        if (square2_.timer == 0) {
            square2_.timer = square_period(square2_.frequency);
            square2_.duty_pos =
                static_cast<std::uint8_t>((square2_.duty_pos + 1u) & 7u);
        }

        if (wave_.timer > 0) --wave_.timer;
        if (wave_.timer == 0) {
            wave_.timer = wave_period(wave_.frequency);
            wave_.position = static_cast<std::uint8_t>((wave_.position + 1u) & 31u);
        }

        if (noise_.timer > 0) --noise_.timer;
        if (noise_.timer == 0) {
            const std::uint32_t base = kNoiseDivisor[noise_.divisor_code & 7u];
            noise_.timer = std::max<std::uint32_t>(8u, base << noise_.clock_shift);
            const std::uint16_t xor_bit =
                static_cast<std::uint16_t>(
                    (noise_.lfsr ^ (noise_.lfsr >> 1)) & 1u);
            noise_.lfsr =
                static_cast<std::uint16_t>((noise_.lfsr >> 1) | (xor_bit << 14));
            if (noise_.width7) {
                noise_.lfsr = static_cast<std::uint16_t>(
                    (noise_.lfsr & ~(1u << 6)) | (xor_bit << 6));
            }
        }

        if (++frame_seq_counter_ >= 8192u) {
            frame_seq_counter_ = 0;
            clock_frame_sequencer();
        }
    }

    if (++sample_counter_ >= 128u) {
        sample_counter_ = 0;
        emit_sample();
    }
}

std::vector<std::int16_t> Apu::take_samples() {
    std::vector<std::int16_t> out;
    out.swap(samples_);
    for (auto& sample : out) sample = clamp16(int(sample) * 96);
    return out;
}

std::vector<std::int32_t> Apu::take_playback_samples() {
    std::vector<std::int32_t> out;
    out.reserve(samples_.size());
    for (const auto sample : samples_) out.push_back(int(sample) * 96);
    samples_.clear();
    return out;
}

} // namespace dwm2t
