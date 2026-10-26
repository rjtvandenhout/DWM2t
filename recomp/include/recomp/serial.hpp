#pragma once

#include <cstdint>

namespace dwm2t {

// The cartridge still runs its own protocol. This is only the two-way serial
// shift register/clock wire; an unplugged input is high, never a game response.
class SerialPort {
public:
    SerialPort() = default;
    ~SerialPort() { disconnect(); }
    SerialPort(const SerialPort& other) { copy_registers(other); }
    SerialPort& operator=(const SerialPort& other) {
        if (this != &other) { disconnect(); copy_registers(other); }
        return *this;
    }

    void reset() {
        disconnect();
        data_ = 0;
        control_ = 0;
        bits_ = 0;
        cycles_ = 0;
        interrupt_ = false;
    }

    void connect(SerialPort& other) {
        if (&other == this || peer_ == &other) return;
        disconnect();
        other.disconnect();
        peer_ = &other;
        other.peer_ = this;
        // Existing transfers continue from their current hardware registers.
        if (active() && internal_clock()) set_owner(this);
        else if (other.active() && other.internal_clock()) set_owner(&other);
    }

    void disconnect() {
        if (peer_) {
            peer_->peer_ = nullptr;
            peer_->owner_ = nullptr;
        }
        peer_ = nullptr;
        owner_ = nullptr;
    }

    [[nodiscard]] std::uint8_t data() const { return data_; }
    [[nodiscard]] std::uint8_t control() const {
        return static_cast<std::uint8_t>(0x7Cu | control_);
    }
    [[nodiscard]] bool interrupt_pending() const { return interrupt_; }
    void clear_interrupt() { interrupt_ = false; }
    void write_data(std::uint8_t value) { data_ = value; }

    void write_control(std::uint8_t value) {
        control_ = static_cast<std::uint8_t>(value & 0x83u);
        bits_ = 0;
        cycles_ = 0;
        if (!active() || !internal_clock()) {
            if (owner_ == this) set_owner(nullptr);
        } else if (!owner_ || !owner_->active() || !owner_->internal_clock()) {
            set_owner(this);
        }
    }

    void tick_tcycle() {
        if (!active() || !internal_clock()) return;
        // A connected transfer has one clock driver. If both software endpoints
        // request internal clock, the first active driver completes that byte;
        // the other endpoint still exchanges real bits on that shared clock.
        if (peer_ && owner_ && owner_ != this && owner_->active() && owner_->internal_clock()) return;
        if (peer_ && owner_ != this) set_owner(this);
        const unsigned period = (control_ & 2u) ? 16u : 512u;
        if (++cycles_ < period) return;
        cycles_ = 0;
        const bool outgoing = (data_ & 0x80u) != 0;
        const bool incoming = !peer_ || !peer_->active() || (peer_->data_ & 0x80u) != 0;
        SerialPort* receiving_peer = peer_ && peer_->active() ? peer_ : nullptr;
        shift(incoming);
        if (receiving_peer) receiving_peer->shift(outgoing);
    }

private:
    [[nodiscard]] bool active() const { return (control_ & 0x80u) != 0; }
    [[nodiscard]] bool internal_clock() const { return (control_ & 1u) != 0; }
    void set_owner(SerialPort* owner) {
        owner_ = owner;
        if (peer_) peer_->owner_ = owner;
    }
    void shift(bool input) {
        data_ = static_cast<std::uint8_t>((data_ << 1) | (input ? 1u : 0u));
        if (++bits_ != 8) return;
        control_ = static_cast<std::uint8_t>(control_ & 3u);
        interrupt_ = true;
        cycles_ = 0;
        if (owner_ == this) set_owner(nullptr);
    }
    void copy_registers(const SerialPort& other) {
        data_ = other.data_;
        control_ = other.control_;
        bits_ = other.bits_;
        cycles_ = other.cycles_;
        interrupt_ = other.interrupt_;
        peer_ = nullptr;
        owner_ = nullptr;
    }

    std::uint8_t data_ = 0;
    std::uint8_t control_ = 0;
    unsigned bits_ = 0;
    unsigned cycles_ = 0;
    bool interrupt_ = false;
    SerialPort* peer_ = nullptr;
    SerialPort* owner_ = nullptr;
};

} // namespace dwm2t
