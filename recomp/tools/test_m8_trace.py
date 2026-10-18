"""Fail-closed trace-tool contracts, not full-game M8 acceptance."""
import argparse
import hashlib
from pathlib import Path
import subprocess
import tempfile

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    exe = args.exe.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="trace-contract-", dir=args.output) as folder:
        root = Path(folder)
        cases = {
            "controller_only": ("- 1 0\nexpect C6FD 00\n", 0, "M8_TRACE_REPLAY_PASS"),
            "reject_checkpoint": ("mark unsafe\n", 230, "M8_REPLAY_FAIL"),
            "reject_restore": ("back unsafe\n", 230, "M8_REPLAY_FAIL"),
            "reject_host_write": ("write C5DB 4\n", 230, "M8_REPLAY_FAIL"),
            "reject_wrong_seed": ("# Fresh Runtime; seed SRAM FNV=0\n", 230, "seed SRAM does not match"),
            "reject_state_mismatch": ("expect C6FD FF\n", 230, "replay assertion failed"),
            "reject_sram_mismatch": ("expect_sram 0\n", 230, "hash assertion failed"),
            "reject_screen_mismatch": ("expect_screen 0\n", 230, "hash assertion failed"),
            "reject_frame_budget": ("A 30001 0\n", 230, "input frame budget exceeded"),
            "reject_partial_failure": ("runtime_failure 3 99 16385\n", 230, "M8_REPLAY_FAIL"),
        }
        for name, (contents, expected, message) in cases.items():
            trace = root / f"{name}.txt"
            trace.write_text(contents, encoding="utf-8")
            result = subprocess.run([str(exe), "--m8-replay", "-", str(trace), str(root / name)],
                                    capture_output=True, text=True, timeout=30)
            combined = result.stdout + result.stderr
            if result.returncode != expected or message not in combined:
                raise AssertionError(f"{name}: exit={result.returncode}\n{combined}")
            print(f"M8_TRACE_CONTRACT_PASS {name}")
        trace = root / "controller_only.txt"
        protected = root / "controller_only" / "trace_p1.txt"
        before = hashlib.sha256(protected.read_bytes()).digest()
        result = subprocess.run([str(exe), "--m8-replay", "-", str(trace), str(protected.parent)],
                                capture_output=True, text=True, timeout=30)
        if result.returncode != 230 or "refusing overwrite" not in result.stderr:
            raise AssertionError("existing trace was not protected")
        if hashlib.sha256(protected.read_bytes()).digest() != before:
            raise AssertionError("existing evidence was changed")
        print("M8_TRACE_CONTRACT_PASS existing_evidence_protected")
        short_save = root / "invalid.sav"
        short_save.write_bytes(b"\x00")
        result = subprocess.run([str(exe), "--m8-replay", str(short_save), str(trace),
                                 str(root / "short_save")], capture_output=True, text=True, timeout=30)
        if result.returncode != 230 or "exact 32 KiB" not in result.stderr:
            raise AssertionError("non-32-KiB save was not rejected")
        print("M8_TRACE_CONTRACT_PASS exact_save_size_required")
        result = subprocess.run([str(exe), "--m8-checkpoint-test", "-", str(trace),
                                 str(root / "unsaved_checkpoint")],
                                capture_output=True, text=True, timeout=30)
        if result.returncode != 230 or "return to idle field" not in result.stderr:
            raise AssertionError("unsaved non-field checkpoint was not rejected")
        print("M8_TRACE_CONTRACT_PASS reject_unsaved_checkpoint")
    print("M8_TRACE_CONTRACT_PASS total=13 full_game_acceptance=NOT_CLAIMED")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
