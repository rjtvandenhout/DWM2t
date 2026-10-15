#include "recomp/memory.hpp"

// The first recomp milestone intentionally keeps the compatibility memory
// model simple. Game Boy address-space behavior (MBC5, VRAM/OAM, IO, HRAM,
// timers, etc.) is added in later milestones behind this same interface.
