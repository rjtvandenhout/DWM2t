#pragma once

#include <array>
#include <cstdint>

namespace dwm2t {

// Host-only comfort controls, never applied to retained regression captures.
// State is continuous across Windows playback buffers.
class AudioPresentation {
public:
    explicit constexpr AudioPresentation(int volume = 25, bool smooth = true)
        : volume_(volume), smooth_(smooth) {}

    constexpr std::int16_t sample(std::int32_t input, unsigned channel) {
        const std::int64_t fixed = std::int64_t(input) * 65536;
        previous_[channel] = smooth_ ? (fixed + previous_[channel]) / 2 : fixed;
        const auto output = previous_[channel] * volume_ / (100 * 65536);
        return static_cast<std::int16_t>(output < -32768 ? -32768 : output > 32767 ? 32767 : output);
    }

private:
    int volume_;
    bool smooth_;
    std::array<std::int64_t, 2> previous_{};
};

constexpr bool audio_presentation_contracts() {
    AudioPresentation raw(100, false), quiet(25, false), mute(0), softened;
    for (int value : {-32768, -19200, 0, 19200, 32767}) {
        for (unsigned channel = 0; channel < 2; ++channel) {
            if (raw.sample(static_cast<std::int16_t>(value), channel) != value) return false;
            if (quiet.sample(static_cast<std::int16_t>(value), channel) != value / 4) return false;
            if (mute.sample(static_cast<std::int16_t>(value), channel) != 0) return false;
        }
    }
    // An impulse must decay, and left-channel history must not leak right.
    if (softened.sample(16000, 0) != 2000 || softened.sample(0, 1) != 0) return false;
    if (softened.sample(0, 0) != 1000 || softened.sample(0, 0) != 500) return false;
    // Pre-conversion gain must preserve a loud mix, not attenuate clipped PCM.
    if (quiet.sample(40000, 0) != 10000 || quiet.sample(-40000, 1) != -10000) return false;
    if (raw.sample(40000, 0) != 32767 || raw.sample(-40000, 1) != -32768) return false;
    // Sustained maximum input stays bounded, with 12 dB playback headroom.
    for (int i = 0; i < 64; ++i) {
        const int value = softened.sample(32767, 0);
        if (value < 0 || value > 8191) return false;
    }
    return true;
}
static_assert(audio_presentation_contracts());

} // namespace dwm2t
