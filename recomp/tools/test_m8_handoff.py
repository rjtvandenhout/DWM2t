"""Offline handoff contracts with simulated subprocesses; NOT gameplay evidence."""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

import m8_handoff as handoff
import test_m8_oasis as chain

ROUTES = [
    "m8_asiya_arrival_p1.txt", "m8_asiya_king_p1.txt",
    "m8_kalka_canal_preparation_p1.txt", "m8_dam_boss_victory_p1.txt",
    "m8_asiya_thieves_report_p1.txt", "m8_watercall_exchange_p1.txt",
    "m8_oasis_curselamp_victory_p1.txt", "m8_post_oasis_home_p1.txt",
    "m8_kids_class_victory_p1.txt",
]
# Clearly synthetic file fixture; never supplied to an actual game runtime.
TEST_SAVE = b"K" * handoff.SRAM_BYTES
TEST_SPEC = handoff.CheckpointSpec(ROUTES[-1], hashlib.sha256(TEST_SAVE).hexdigest())


class FakeNative:
    """Only models subprocess/file contracts, not cartridge execution."""
    def __init__(self, args, *, fail=None, omit=None, truncate=None,
                 mutate_seed=None, mutate_route=None, mutate_exe=None):
        self.args, self.calls = args, []
        self.fail, self.omit, self.truncate = fail, omit, truncate
        self.mutate_seed, self.mutate_route, self.mutate_exe = mutate_seed, mutate_route, mutate_exe

    def __call__(self, command, **kwargs):
        self.calls.append(list(command))
        flag = command[1]
        destination = Path(command[-1])
        name = "oasis" if flag == "--m8-oasis-test" else destination.name
        if name == self.fail:
            return subprocess.CompletedProcess(command, 17)
        destination.mkdir(parents=True, exist_ok=True)
        if name == self.mutate_seed:
            source = Path(command[2]); source.write_bytes(b"!" + source.read_bytes()[1:])
        if name == self.mutate_route:
            source = Path(command[3]); source.write_text("# changed fixture\n", encoding="utf-8")
        if name == self.mutate_exe:
            self.args.exe.write_bytes(self.args.exe.read_bytes() + b"changed")
        save_name = {
            "--m8-oasis-test": "oasis_original_journal.sav",
            "--m8-inn-test": "inn_original_journal.sav",
            "--m8-checkpoint-test": "checkpoint.sav",
        }.get(flag)
        if save_name and name != self.omit:
            content = TEST_SAVE if Path(command[3]).name == ROUTES[-1] else (
                bytes([len(self.calls)]) * handoff.SRAM_BYTES
            )
            if name == self.truncate:
                content = content[:123]
            (destination / save_name).write_bytes(content)
        return subprocess.CompletedProcess(command, 0)


class Contracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.exe = self.root / "DWM2tRecompFull.exe"
        self.exe.write_bytes(b"SYNTHETIC EXECUTABLE CONTRACT FIXTURE; NEVER EXECUTED")
        self.seed = self.root / "m7_original.sav"
        self.seed.write_bytes(b"S" * handoff.SRAM_BYTES)
        route_root = self.root / "routes"; route_root.mkdir()
        for name in ROUTES + ["oasis.txt", "inn.txt", "feeding.txt", "audio.txt"]:
            (route_root / name).write_text("# contract fixture, no original game input\n", encoding="utf-8")
        self.args = argparse.Namespace(
            exe=self.exe, seed=self.seed, route=route_root / "oasis.txt",
            inn_route=route_root / "inn.txt", checkpoint_route=[route_root / p for p in ROUTES],
            feeding_route=route_root / "feeding.txt", audio_route=route_root / "audio.txt",
            output=self.root / "evidence",
        )

    def run_chain(self, **faults):
        runner = FakeNative(self.args, **faults)
        with contextlib.redirect_stdout(io.StringIO()):
            code, output = chain.run_chain(self.args, runner=runner)
        return code, output, runner, json.loads((output / "handoff.json").read_text())

    def good(self):
        code, output, runner, report = self.run_chain()
        self.assertEqual(code, 0)
        return output, runner, report

    def verify(self, output, **kwargs):
        return handoff.load_verified_handoff(output / "handoff.json", checkpoint=TEST_SPEC, **kwargs)

    def change_report(self, output, report):
        handoff.write_report(output / "handoff.json", report)

    def launch(self, output, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            return handoff.launch_session(output / "handoff.json", self.root / "sessions",
                                          checkpoint=TEST_SPEC, **kwargs)

    def test_full_chain_reports_exact_final_checkpoint(self):
        output, _, report = self.good()
        self.assertEqual(report["status"], "complete")
        self.assertEqual(report["scope"], handoff.SCOPE)
        self.assertEqual(report["final_checkpoint"]["path"], "story-09/checkpoint.sav")
        self.assertEqual(report["final_checkpoint"]["sha256"], TEST_SPEC.sha256)
        self.assertEqual(self.verify(output)[1].read_bytes(), TEST_SAVE)

    def test_existing_command_order_is_unchanged(self):
        _, runner, _ = self.good()
        observed = [(c[1], Path(c[3]).name) for c in runner.calls]
        expected = [("--m8-oasis-test", "oasis.txt"), ("--m8-inn-test", "inn.txt")]
        for index, name in enumerate(ROUTES, 1):
            expected.append(("--m8-checkpoint-test", name))
            if index == 5: expected.append(("--m8-checkpoint-test", "feeding.txt"))
            if index == 8: expected.append(("--m8-audio-output-test", "audio.txt"))
        self.assertEqual(observed, expected)

    def test_feeding_does_not_replace_main_seed(self):
        output, runner, _ = self.good()
        feeding = next(c for c in runner.calls if Path(c[3]).name == "feeding.txt")
        watercall = next(c for c in runner.calls if Path(c[3]).name == ROUTES[5])
        self.assertEqual(feeding[2], str(output / "story-05/checkpoint.sav"))
        self.assertEqual(watercall[2], feeding[2])

    def test_audio_does_not_replace_main_seed(self):
        output, runner, _ = self.good()
        audio = next(c for c in runner.calls if Path(c[3]).name == "audio.txt")
        kids = runner.calls[-1]
        self.assertEqual(kids[2], str(output / "story-08/checkpoint.sav"))
        self.assertEqual(kids[2], audio[2])

    def test_seed_source_and_routes_remain_unchanged(self):
        before = {p: p.read_bytes() for p in [self.exe, self.seed, *self.args.checkpoint_route]}
        self.good()
        self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_no_side_branches_still_runs_main_chain(self):
        self.args.feeding_route = self.args.audio_route = None
        _, runner, report = self.good()
        self.assertEqual(len(runner.calls), 11)
        self.assertTrue(all(s["role"] == "main" for s in report["stages"]))

    def test_native_failure_halts_later_stages(self):
        code, _, runner, report = self.run_chain(fail="story-03")
        self.assertEqual(code, 17)
        self.assertEqual(len(runner.calls), 5)
        self.assertEqual(report["status"], "failed")
        self.assertIsNone(report["final_checkpoint"])

    def test_feeding_failure_halts_main_story(self):
        code, _, runner, report = self.run_chain(fail="enemy-feeding")
        self.assertEqual(code, 17)
        self.assertEqual(Path(runner.calls[-1][-1]).name, "enemy-feeding")
        self.assertIsNone(report["final_checkpoint"])

    def test_audio_failure_halts_tournament(self):
        code, _, runner, _ = self.run_chain(fail="hub-audio")
        self.assertEqual(code, 17)
        self.assertNotIn(ROUTES[-1], [Path(c[3]).name for c in runner.calls])

    def test_exit_zero_without_final_save_is_failure(self):
        code, _, _, report = self.run_chain(omit="story-09")
        self.assertEqual(code, 2)
        self.assertEqual(report["status"], "failed")
        self.assertIsNone(report["final_checkpoint"])

    def test_truncated_output_is_failure(self):
        code, _, runner, _ = self.run_chain(truncate="inn")
        self.assertEqual(code, 2)
        self.assertEqual(len(runner.calls), 2)

    def test_truncated_initial_seed_is_rejected_before_native_run(self):
        self.seed.write_bytes(b"small")
        code, _, runner, _ = self.run_chain()
        self.assertEqual(code, 2)
        self.assertEqual(runner.calls, [])

    def test_missing_executable_is_rejected(self):
        self.exe.unlink()
        code, _, runner, report = self.run_chain()
        self.assertEqual(code, 2)
        self.assertEqual(runner.calls, [])
        self.assertEqual(report["status"], "failed")

    def test_mutated_native_seed_is_rejected(self):
        code, _, runner, _ = self.run_chain(mutate_seed="inn")
        self.assertEqual(code, 2)
        self.assertEqual(len(runner.calls), 2)

    def test_mutated_route_is_rejected(self):
        code, _, runner, _ = self.run_chain(mutate_route="story-01")
        self.assertEqual(code, 2)
        self.assertEqual(len(runner.calls), 3)

    def test_changed_executable_during_chain_is_rejected(self):
        code, _, _, report = self.run_chain(mutate_exe="story-09")
        self.assertEqual(code, 2)
        self.assertEqual(report["status"], "failed")

    def test_repeated_runs_use_new_output_directories(self):
        a, _, _ = self.good(); b, _, _ = self.good()
        self.assertNotEqual(a, b)
        self.assertTrue((a / "story-09/checkpoint.sav").is_file())

    def test_subprocess_launch_error_leaves_failed_report(self):
        with contextlib.redirect_stdout(io.StringIO()):
            code, output = chain.run_chain(self.args, runner=mock.Mock(side_effect=OSError("cannot launch")))
        report = json.loads((output / "handoff.json").read_text())
        self.assertEqual(code, 2)
        self.assertEqual(report["status"], "failed")

    def test_failed_and_running_reports_cannot_resume(self):
        output, _, report = self.good()
        for state in ["failed", "running", "discovery", "unknown"]:
            with self.subTest(state=state):
                report["status"] = state; self.change_report(output, report)
                with self.assertRaises(handoff.HandoffError): self.verify(output)

    def test_wrong_schema_cannot_resume(self):
        output, _, report = self.good()
        report["schema"] = "anything"; self.change_report(output, report)
        with self.assertRaises(handoff.HandoffError): self.verify(output)

    def test_invalid_json_cannot_resume(self):
        output, _, _ = self.good()
        (output / "handoff.json").write_text("{bad json")
        with self.assertRaises(handoff.HandoffError): self.verify(output)

    def test_tampered_checkpoint_same_length_is_rejected(self):
        output, _, _ = self.good()
        (output / "story-09/checkpoint.sav").write_bytes(b"T" * handoff.SRAM_BYTES)
        with self.assertRaises(handoff.HandoffError): self.verify(output)

    def test_tampered_route_after_chain_is_rejected(self):
        output, _, _ = self.good()
        self.args.checkpoint_route[2].write_text("# changed\n")
        with self.assertRaises(handoff.HandoffError): self.verify(output)

    def test_swapped_executable_is_rejected(self):
        output, _, _ = self.good()
        self.exe.write_bytes(b"different build")
        with self.assertRaises(handoff.HandoffError): self.verify(output)

    def test_relocated_identical_executable_is_allowed(self):
        output, _, _ = self.good()
        other = self.root / "same-build.exe"; other.write_bytes(self.exe.read_bytes())
        self.exe.unlink()
        verified = self.verify(output, exe=other)[0]
        # Windows TEMP can use an 8.3 alias (RUNNER~1) while the verifier
        # deliberately resolves the long path. Compare canonical identity.
        self.assertEqual(verified, other.resolve(strict=True))
        self.assertTrue(verified.samefile(other))

    def test_noncanonical_identical_executable_is_allowed(self):
        output, _, _ = self.good()
        folder = self.root / "alias-parent"; folder.mkdir()
        alias = folder / ".." / self.exe.name
        verified = self.verify(output, exe=alias)[0]
        self.assertEqual(verified, self.exe.resolve(strict=True))
        self.assertTrue(verified.samefile(alias))

    def test_relocated_different_executable_is_rejected(self):
        output, _, _ = self.good()
        other = self.root / "different-build.exe"
        other.write_bytes(b"DIFFERENT SYNTHETIC EXECUTABLE; NEVER EXECUTED")
        with self.assertRaises(handoff.HandoffError):
            self.verify(output, exe=other)

    def test_final_save_cannot_point_to_side_branch(self):
        output, _, report = self.good()
        report["final_checkpoint"] = next(s["save"] for s in report["stages"] if s["name"] == "enemy-feeding")
        self.change_report(output, report)
        with self.assertRaises(handoff.HandoffError): self.verify(output)

    def test_earlier_world_report_cannot_authorize_pirate_resume(self):
        self.args.checkpoint_route = self.args.checkpoint_route[:8]
        output, _, _ = self.good()
        with self.assertRaises(handoff.HandoffError): self.verify(output)

    def test_production_pinned_save_rejects_synthetic_contract_save(self):
        output, _, _ = self.good()
        with self.assertRaisesRegex(handoff.HandoffError, "byte-identical"):
            handoff.load_verified_handoff(output / "handoff.json")

    def test_path_traversal_is_rejected(self):
        output, _, report = self.good()
        for path in ["../outside.sav", str(self.seed)]:
            with self.subTest(path=path):
                with self.assertRaises(handoff.HandoffError): handoff.evidence_path(output, path)

    def test_external_symlink_is_rejected(self):
        output, _, _ = self.good()
        linked = output / "outside.sav"
        try: linked.symlink_to(self.seed)
        except (OSError, NotImplementedError): self.skipTest("Symlink creation unavailable")
        with self.assertRaises(handoff.HandoffError): handoff.evidence_path(output, "outside.sav")

    def test_verify_only_never_launches_or_creates_session(self):
        output, _, _ = self.good(); runner = mock.Mock()
        self.assertEqual(self.launch(output, runner=runner, verify_only=True), (0, None))
        runner.assert_not_called()
        self.assertFalse((self.root / "sessions").exists())

    def test_play_receives_copy_only_and_original_survives_writes(self):
        output, _, report = self.good()
        original = output / "story-09/checkpoint.sav"
        def play(command, **kwargs):
            self.assertEqual(command[1], "--play")
            self.assertNotEqual(Path(command[2]), original)
            self.assertEqual(Path(command[2]).read_bytes(), TEST_SAVE)
            Path(command[2]).write_bytes(b"P" * handoff.SRAM_BYTES)
            return subprocess.CompletedProcess(command, 0)
        code, session = self.launch(output, runner=play)
        self.assertEqual(code, 0)
        self.assertEqual(original.read_bytes(), TEST_SAVE)
        self.assertEqual((session / "play.sav").read_bytes(), b"P" * handoff.SRAM_BYTES)
        self.assertEqual(json.loads((session / "session.json").read_text())["status"], "closed")

    def test_probe_gets_new_nonexistent_output_directory(self):
        output, _, _ = self.good()
        def probe(command, **kwargs):
            self.assertEqual(command[1], "--m8-probe")
            self.assertFalse(Path(command[3]).exists())
            self.assertEqual(Path(command[2]).read_bytes(), TEST_SAVE)
            return subprocess.CompletedProcess(command, 0)
        self.assertEqual(self.launch(output, runner=probe, mode="probe")[0], 0)

    def test_each_play_session_has_an_independent_save(self):
        output, _, _ = self.good()
        runner = mock.Mock(return_value=subprocess.CompletedProcess([], 0))
        _, one = self.launch(output, runner=runner)
        _, two = self.launch(output, runner=runner)
        self.assertNotEqual(one, two)
        self.assertTrue((one / "play.sav").exists())
        self.assertTrue((two / "play.sav").exists())

    def test_runtime_failure_is_not_reported_as_success(self):
        output, _, _ = self.good()
        runner = mock.Mock(return_value=subprocess.CompletedProcess([], 90))
        code, session = self.launch(output, runner=runner)
        self.assertEqual(code, 90)
        report = json.loads((session / "session.json").read_text())
        self.assertEqual(report["status"], "runtime-failed")

    def test_launch_failure_does_not_change_original(self):
        output, _, _ = self.good()
        with self.assertRaises(OSError):
            self.launch(output, runner=mock.Mock(side_effect=OSError("denied")))
        self.assertEqual((output / "story-09/checkpoint.sav").read_bytes(), TEST_SAVE)
        session = next((self.root / "sessions").iterdir())
        self.assertEqual(json.loads((session / "session.json").read_text())["status"], "launch-failed")

    def test_invalid_manifest_never_reaches_launcher(self):
        output, _, report = self.good()
        report["status"] = "failed"; self.change_report(output, report)
        runner = mock.Mock()
        with self.assertRaises(handoff.HandoffError): self.launch(output, runner=runner)
        runner.assert_not_called()

    def test_reports_leave_no_temporary_files(self):
        output, _, _ = self.good()
        self.assertEqual(list(output.glob(".handoff-*.tmp")), [])

    def test_cli_failure_returns_nonzero_without_traceback(self):
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            code = handoff.main(["--manifest", str(self.root / "missing.json"), "--verify-only"])
        self.assertEqual(code, 2)
        self.assertIn("M8_HANDOFF_FAIL", stream.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
