"""Integrity-checked M8 checkpoint handoff; never full-game acceptance.

Only a copy of a verified original Journal is passed to the native game.
This module neither emulates the CPU nor edits cartridge/save state.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any

SRAM_BYTES = 32768
SCHEMA = "dwm2t.m8.checkpoint-handoff.v1"
SCOPE = "checkpoint-chain-only; not full M8 or whole-suite acceptance"


class HandoffError(ValueError):
    """Evidence is incomplete, inconsistent, or no longer matches its files."""


@dataclass(frozen=True)
class CheckpointSpec:
    route: str
    sha256: str


# Pinned in M8_WORKING.md at repository commit 80d37f2f51038d295ef9c5cf03545dbb0565b26e.
KIDS_CLASS = CheckpointSpec(
    "m8_kids_class_victory_p1.txt",
    "a48fb7b52d6b5063f03725d205f96964174b44afbb3600782892ba44caeaa91a",
)


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def record_file(path: Path, root: Path | None = None, *, save: bool = False) -> dict[str, Any]:
    path = path.resolve(strict=True)
    if not path.is_file():
        raise HandoffError(f"Not a regular file: {path}")
    size = path.stat().st_size
    if save and size != SRAM_BYTES:
        raise HandoffError(f"Expected {SRAM_BYTES}-byte original SRAM, found {size}: {path}")
    if root is not None:
        try:
            stored_path = path.relative_to(root.resolve(strict=True)).as_posix()
        except ValueError as exc:
            raise HandoffError("Checkpoint must remain inside its evidence directory") from exc
    else:
        stored_path = str(path)
    return {"path": stored_path, "bytes": size, "sha256": digest(path)}


def evidence_path(root: Path, stored_path: str) -> Path:
    relative = Path(stored_path)
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise HandoffError("Checkpoint path must be relative and cannot escape the evidence directory")
    path = (root / relative).resolve(strict=True)
    try:
        path.relative_to(root.resolve(strict=True))
    except ValueError as exc:
        raise HandoffError("Checkpoint symlink escapes the evidence directory") from exc
    return path


def verify_file(record: dict[str, Any], *, root: Path | None = None,
                override: Path | None = None, save: bool = False) -> Path:
    if not isinstance(record, dict) or not {"path", "bytes", "sha256"} <= record.keys():
        raise HandoffError("Incomplete file record")
    if not isinstance(record["path"], str) or not isinstance(record["sha256"], str):
        raise HandoffError("Invalid file record")
    path = override.resolve(strict=True) if override is not None else (
        evidence_path(root, record["path"]) if root is not None
        else Path(record["path"]).resolve(strict=True)
    )
    current = record_file(path, save=save)
    if current["bytes"] != record["bytes"] or current["sha256"] != record["sha256"]:
        raise HandoffError(f"File changed since verification: {path}")
    return path


def write_report(path: Path, report: dict[str, Any]) -> None:
    """Atomically replace only the report in a newly allocated evidence directory."""
    fd, temporary = tempfile.mkstemp(prefix=".handoff-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(report, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def load_verified_handoff(manifest: Path, *, exe: Path | None = None,
                          checkpoint: CheckpointSpec = KIDS_CLASS) -> tuple[Path, Path, dict[str, Any]]:
    manifest = manifest.resolve(strict=True)
    try:
        report = json.loads(manifest.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise HandoffError("Unreadable checkpoint handoff") from exc
    if not isinstance(report, dict) or report.get("schema") != SCHEMA:
        raise HandoffError("Unsupported handoff schema")
    if report.get("scope") != SCOPE or report.get("status") != "complete":
        raise HandoffError("Checkpoint chain did not complete; discovery/failure reports cannot authorize resume")
    stages = report.get("stages")
    if not isinstance(stages, list) or not stages:
        raise HandoffError("No completed native checkpoint stages")
    for stage in stages:
        if not isinstance(stage, dict) or stage.get("returncode") != 0:
            raise HandoffError("A native stage did not pass")
        if "route" not in stage or "seed" not in stage:
            raise HandoffError("Incomplete stage evidence")
        verify_file(stage["route"])
        verify_file(stage["seed"], save=True)
        if stage.get("save") is not None:
            verify_file(stage["save"], root=manifest.parent, save=True)
    main_stages = [stage for stage in stages if stage.get("role") == "main"]
    if not main_stages:
        raise HandoffError("No main-story checkpoint")
    last = main_stages[-1]
    if Path(last["route"]["path"]).name != checkpoint.route:
        raise HandoffError("Not the accepted Kids Class checkpoint; a limited-build/earlier-world report is insufficient")
    final = report.get("final_checkpoint")
    if not isinstance(final, dict) or final != last.get("save"):
        raise HandoffError("Final checkpoint is not the last passing main-story save")
    if final.get("sha256") != checkpoint.sha256:
        raise HandoffError("Final Journal is not byte-identical to the accepted Kids Class save")
    executable = verify_file(report.get("executable", {}), override=exe)
    save_path = verify_file(final, root=manifest.parent, save=True)
    return executable, save_path, report


def launch_session(manifest: Path, session_root: Path, *, exe: Path | None = None,
                   mode: str = "play", verify_only: bool = False,
                   runner: Any = subprocess.run,
                   checkpoint: CheckpointSpec = KIDS_CLASS) -> tuple[int, Path | None]:
    if mode not in {"play", "probe"}:
        raise HandoffError("Mode must be play or probe")
    executable, original, report = load_verified_handoff(manifest, exe=exe, checkpoint=checkpoint)
    print(f"M8_HANDOFF_VERIFIED checkpoint=kids-class sha256={report['final_checkpoint']['sha256']}", flush=True)
    if verify_only:
        return 0, None
    session_root.mkdir(parents=True, exist_ok=True)
    session = Path(tempfile.mkdtemp(prefix="after-kids-", dir=session_root.resolve()))
    copied_save = session / "play.sav"
    with original.open("rb") as source, copied_save.open("xb") as target:
        shutil.copyfileobj(source, target, 1024 * 1024)
    # Recheck both sides after copying; fail closed on a concurrently changed source.
    verify_file(report["final_checkpoint"], override=original, save=True)
    verify_file(report["final_checkpoint"], override=copied_save, save=True)
    verify_file(report["executable"], override=executable)
    command = [str(executable), "--play", str(copied_save)] if mode == "play" else [
        str(executable), "--m8-probe", str(copied_save), str(session / "probe")
    ]
    session_record = {
        "schema": "dwm2t.m8.resume-session.v1", "status": "ready",
        "scope": "safe resume only; no next-world or ending proof",
        "source_manifest": record_file(manifest),
        "original_save": record_file(original, save=True),
        "copied_save": record_file(copied_save, session, save=True),
        "executable": record_file(executable), "command": command,
    }
    write_report(session / "session.json", session_record)
    print(f"M8_SESSION {session}", flush=True)
    try:
        result = runner(command, check=False)
        code = int(result.returncode)
    except OSError as exc:
        session_record.update(status="launch-failed", error=str(exc))
        write_report(session / "session.json", session_record)
        raise
    verify_file(session_record["original_save"], save=True)
    session_record.update(status="closed" if code == 0 else "runtime-failed", returncode=code)
    session_record["session_save_after"] = record_file(copied_save, session, save=True)
    write_report(session / "session.json", session_record)
    return code, session


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True, help="handoff.json emitted by test_m8_oasis.py")
    parser.add_argument("--exe", type=Path, help="optional relocated, byte-identical verified executable")
    parser.add_argument("--session-root", type=Path, default=Path("recomp/build/m8-sessions"))
    parser.add_argument("--mode", choices=("play", "probe"), default="play")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        code, _ = launch_session(args.manifest, args.session_root, exe=args.exe,
                                 mode=args.mode, verify_only=args.verify_only)
        return code
    except (HandoffError, OSError, KeyError, TypeError) as exc:
        print(f"M8_HANDOFF_FAIL {exc}", flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
