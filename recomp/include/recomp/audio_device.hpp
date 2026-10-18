#pragma once

namespace dwm2t {

struct AudioDeviceSelection {
    bool ready = false;
    int device = -1;
    unsigned error = 0;
    unsigned mapper_error = 0;
};

// Host output selection only. A failed Windows default mapper does not imply
// that every explicitly enumerated device is unavailable.
template<class Open>
constexpr AudioDeviceSelection select_audio_device(unsigned count, int preferred, Open open) {
    const unsigned first = open(preferred);
    if (first == 0) return {true, preferred, 0, 0};
    if (preferred >= 0) return {false, preferred, first, 0};
    unsigned last = first;
    for (unsigned device = 0; device < count; ++device) {
        last = open(int(device));
        if (last == 0) return {true, int(device), 0, first};
    }
    return {false, -1, last, first};
}

constexpr bool audio_device_contracts() {
    if (select_audio_device(2, -1, [](int) { return 0u; }).device != -1) return false;
    const auto fallback = select_audio_device(2, -1, [](int d) { return d < 0 ? 2u : 0u; });
    if (!fallback.ready || fallback.device != 0 || fallback.mapper_error != 2) return false;
    const auto second = select_audio_device(2, -1, [](int d) { return d == 1 ? 0u : 2u; });
    if (!second.ready || second.device != 1) return false;
    if (select_audio_device(0, -1, [](int) { return 6u; }).ready) return false;
    if (select_audio_device(2, -1, [](int) { return 4u; }).ready) return false;
    unsigned calls = 0;
    const auto explicit_failure = select_audio_device(2, 7, [&](int) { ++calls; return 2u; });
    return !explicit_failure.ready && explicit_failure.error == 2 && calls == 1;
}
static_assert(audio_device_contracts());

} // namespace dwm2t
