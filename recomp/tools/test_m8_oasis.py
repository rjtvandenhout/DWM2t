"""Revalidate original Oasis/Asiya Journal routes; not final M8 acceptance."""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import tempfile
from typing import Any

from m8_handoff import HandoffError, SCHEMA, SCOPE, record_file, verify_file, write_report


class StageFailure(RuntimeError):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code if code != 0 else 2


def run_chain(args: argparse.Namespace, *, runner: Any = subprocess.run) -> tuple[int, Path]:
    args.output.mkdir(parents=True, exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix="oasis-", dir=args.output.resolve()))
    manifest = output / "handoff.json"
    report: dict[str, Any] = {
        "schema": SCHEMA, "scope": SCOPE, "status": "running",
        "stages": [], "final_checkpoint": None,
    }
    write_report(manifest, report)
    print(f"M8_OASIS_EVIDENCE {output}", flush=True)

    def stage(name: str, flag: str, seed: Path, route: Path, destination: Path,
              save_name: str | None, *, role: str = "main") -> Path | None:
        seed_record = record_file(seed, save=True)
        route_record = record_file(route)
        entry = {"name": name, "role": role, "seed": seed_record,
                 "route": route_record, "returncode": None, "save": None}
        report["stages"].append(entry)
        write_report(manifest, report)
        command = [str(args.exe.resolve()), flag, str(seed.resolve()),
                   str(route.resolve()), str(destination)]
        result = runner(command, check=False)
        entry["returncode"] = int(result.returncode)
        # Native tests must only read their seed/fixture. Never count an
        # in-place mutation of an old checkpoint as successful new evidence.
        verify_file(seed_record, save=True)
        verify_file(route_record)
        if result.returncode != 0:
            raise StageFailure(result.returncode, f"Native stage {name} failed")
        if save_name is None:
            write_report(manifest, report)
            return None
        save = destination / save_name
        entry["save"] = record_file(save, output, save=True)
        write_report(manifest, report)
        return save

    try:
        report["executable"] = record_file(args.exe)
        seed = stage("oasis", "--m8-oasis-test", args.seed, args.route,
                     output, "oasis_original_journal.sav")
        assert seed is not None
        seed = stage("inn", "--m8-inn-test", seed, args.inn_route,
                     output / "inn", "inn_original_journal.sav")
        assert seed is not None
        for index, route in enumerate(args.checkpoint_route, start=1):
            name = f"story-{index:02}"
            seed = stage(name, "--m8-checkpoint-test", seed, route,
                         output / name, "checkpoint.sav")
            assert seed is not None
            if index == 5 and args.feeding_route:
                # Keep the feeding save off the main chain, as before.
                stage("enemy-feeding", "--m8-checkpoint-test", seed,
                      args.feeding_route, output / "enemy-feeding",
                      "checkpoint.sav", role="side-branch")
                print("M8_ENEMY_FEEDING_BRANCH_PASS original_item_consumption_and_bonus", flush=True)
            if index == 8 and args.audio_route:
                stage("hub-audio", "--m8-audio-output-test", seed,
                      args.audio_route, output / "hub-audio", None, role="side-branch")
        verify_file(report["executable"])
        report["final_checkpoint"] = record_file(seed, output, save=True)
        report["status"] = "complete"
        write_report(manifest, report)
        print(f"M8_CHECKPOINT_HANDOFF {manifest}", flush=True)
        return 0, output
    except (StageFailure, HandoffError, OSError, ValueError) as exc:
        report.update(status="failed", error=str(exc), final_checkpoint=None)
        write_report(manifest, report)
        print(f"M8_CHECKPOINT_CHAIN_FAIL {exc}", flush=True)
        return exc.code if isinstance(exc, StageFailure) else 2, output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path, required=True)
    parser.add_argument("--seed", type=Path, required=True)
    parser.add_argument("--route", type=Path, required=True)
    parser.add_argument("--inn-route", type=Path, required=True)
    parser.add_argument("--checkpoint-route", type=Path, action="append", default=[])
    parser.add_argument("--feeding-route", type=Path)
    parser.add_argument("--audio-route", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.feeding_route and len(args.checkpoint_route) < 5:
        parser.error("feeding side branch requires the five original story checkpoints")
    if args.audio_route and len(args.checkpoint_route) < 8:
        parser.error("audio side branch requires the post-Oasis home checkpoint")
    code, _ = run_chain(args)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
