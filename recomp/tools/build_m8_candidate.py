#!/usr/bin/env python3
"""Build/package a complete-AOT Windows candidate without running any tests.

Only a new workspace/output is accepted. Sources come from a pinned Git archive,
not from mutable build caches. The game executable is never launched by this tool.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import struct
import subprocess
import sys
import tarfile
import uuid
import zipfile

ROM_SHA256 = "8e38a7420ef5239c7196aa4fd4b1499e65db2823e875bbf8241bb2199e766d4e"
SOURCE_PATHS = ("recomp", "src/banks", "LICENSE-NOTICE.md")
RUNTIME_SETTING = "MultiThreaded$<$<CONFIG:Debug>:Debug>"


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def capture(command: list[str], cwd: Path) -> str:
    return subprocess.check_output(command, cwd=cwd, text=True,
                                   encoding="utf-8", errors="strict").lstrip("\ufeff").strip()


def write_json(path: Path, data: object) -> None:
    temporary = path.with_name(path.name + ".pending")
    with temporary.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(data, stream, indent=2, sort_keys=True)
        stream.write("\n")
    os.replace(temporary, path)


def run_logged(command: list[str], cwd: Path, log: Path, timeout: int) -> None:
    print(f"BUILD_STEP {log.stem} (no tests)", flush=True)
    with log.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(command) + "\n")
        stream.flush()
        result = subprocess.run(command, cwd=cwd, stdout=stream,
                                stderr=subprocess.STDOUT, timeout=timeout, check=False,
                                env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    if result.returncode:
        raise RuntimeError(f"{log.stem} failed ({result.returncode}); inspect {log}")


def unpack_sources(archive: Path, destination: Path) -> None:
    # Git archives need no network and cannot incorporate ignored saves/builds.
    destination.mkdir()
    with tarfile.open(archive, "r:") as source:
        for member in source:
            parts = PurePosixPath(member.name).parts
            if (not parts or member.name.startswith("/") or ".." in parts or
                    "\\" in member.name or any(":" in part for part in parts)):
                raise ValueError(f"Unsafe source archive path: {member.name}")
            path = destination.joinpath(*parts)
            if member.isdir():
                path.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                path.parent.mkdir(parents=True, exist_ok=True)
                incoming = source.extractfile(member)
                if incoming is None:
                    raise ValueError(f"Unreadable source archive member: {member.name}")
                with incoming, path.open("xb") as output:
                    shutil.copyfileobj(incoming, output)
            else:
                raise ValueError(f"Links/special files are not build inputs: {member.name}")


def inventory(root: Path) -> dict[str, str]:
    return {path.relative_to(root).as_posix(): digest(path)
            for path in sorted(root.rglob("*")) if path.is_file()}


def check_rom_identity(root: Path) -> None:
    rom = hashlib.sha256()
    for bank in range(256):
        path = root / "src" / "banks" / f"bank_{bank:03}.asm"
        data = bytearray()
        for line in path.read_text(encoding="utf-8").splitlines():
            match = re.match(r"\s*db\s+(.+)", line, re.IGNORECASE)
            if match:
                data.extend(int(value, 16) for value in
                            re.findall(r"\$([0-9a-fA-F]{2})(?![0-9a-fA-F])",
                                       match.group(1).split(";", 1)[0]))
        if len(data) != 16384:
            raise ValueError(f"Source bank {bank} is not exactly 16384 bytes")
        rom.update(data)
    if rom.hexdigest() != ROM_SHA256:
        raise ValueError("Source-bank ROM identity mismatch; packaging refused")


def choose_generator(cmake: str, requested: str | None, root: Path) -> str:
    capabilities = json.loads(capture([cmake, "-E", "capabilities"], root))
    names = [entry["name"] for entry in capabilities["generators"]]
    if requested:
        if requested not in names or not (requested == "Ninja" or
                                          requested.startswith("Visual Studio ")):
            raise ValueError("Select a supported Visual Studio or Ninja generator")
        return requested
    visual_studio = [name for name in names if name.startswith("Visual Studio ")]
    locator = Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")) / "Microsoft Visual Studio/Installer/vswhere.exe"
    if not locator.is_file():
        raise ValueError("Visual Studio discovery is unavailable; select --generator explicitly")
    installations = json.loads(capture([str(locator), "-products", "*", "-prerelease",
        "-requires", "Microsoft.VisualStudio.Component.VC.Tools.x86.x64", "-format", "json", "-utf8"], root))
    majors = {int(item["installationVersion"].split(".")[0]) for item in installations}
    available = [name for name in visual_studio if int(name.split()[2]) in majors]
    if not available:
        raise ValueError("No supported C++ Visual Studio installation; use --generator Ninja in an x64 developer prompt")
    return max(available, key=lambda name: int(name.split()[2]))


def check_pe_x64(path: Path) -> None:
    with path.open("rb") as stream:
        header = stream.read(64)
        if len(header) != 64 or header[:2] != b"MZ":
            raise ValueError("Build output is not a Windows executable")
        pe_offset = struct.unpack_from("<I", header, 0x3C)[0]
        if not 64 <= pe_offset <= path.stat().st_size - 6:
            raise ValueError("Invalid executable header offset")
        stream.seek(pe_offset)
        if stream.read(6) != b"PE\0\0\x64\x86":
            raise ValueError("Build output is not Windows x64 (PE machine 8664)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--generator")
    parser.add_argument("--jobs", type=int, choices=range(1, 5), default=2)
    args = parser.parse_args()
    report: dict[str, object] = {"status": "not_started", "tests": "not_run",
                                 "gameplay": "not_run", "m8_accepted": False}
    output: Path | None = None
    try:
        if os.name != "nt":
            raise ValueError("The candidate builder requires Windows x64 and the C++ build tools")
        root = Path(__file__).resolve().parents[2]
        cmake = shutil.which("cmake")
        git = shutil.which("git")
        if not cmake or not git:
            raise ValueError("CMake and Git must be available on PATH")
        commit = capture([git, "rev-parse", "HEAD"], root)
        if not re.fullmatch(r"[0-9a-f]{40}", commit):
            raise ValueError("A pinned 40-character Git commit is required")
        dirty = capture([git, "status", "--porcelain", "--untracked-files=normal", "--",
                         *SOURCE_PATHS], root)
        if dirty:
            raise ValueError("Commit or isolate source changes before building a candidate")
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        identity = f"{commit[:12]}-{stamp}-{uuid.uuid4().hex[:8]}"
        workspace = (args.workspace or root / "recomp/build/candidates" / identity).resolve()
        output = (args.output or root / "recomp/build/packages" / identity).resolve()
        if workspace == output or workspace in output.parents or output in workspace.parents:
            raise ValueError("Workspace and output must be separate, non-nested directories")
        if workspace.exists() or output.exists():
            raise ValueError("Workspace and output must both be new; nothing will be overwritten")
        workspace.mkdir(parents=True)
        output.mkdir(parents=True)
        logs = output / "build-logs"
        logs.mkdir()
        report.update(status="building", source_commit=commit, created_utc=stamp,
                      workspace=str(workspace), output=str(output))
        write_json(output / "build-report.json", report)
        archive = workspace / "source.tar"
        subprocess.run([git, "archive", "--format=tar", "-o", str(archive), commit,
                        *SOURCE_PATHS], cwd=root, check=True, timeout=120)
        source = workspace / "source"
        unpack_sources(archive, source)
        before = inventory(source)
        check_rom_identity(source)
        generator = choose_generator(cmake, args.generator, root)
        build = workspace / "native"
        configure = [cmake, "-S", str(source / "recomp/player"), "-B", str(build),
                     "-G", generator, "-DCMAKE_BUILD_TYPE=Release", "-DBUILD_TESTING=OFF",
                     "-DDWM2T_ALL_ROMX=ON", f"-DDWM2T_SOURCE_REVISION={commit}",
                     f"-DCMAKE_MSVC_RUNTIME_LIBRARY={RUNTIME_SETTING}",
                     f"-DPython3_EXECUTABLE={sys.executable}"]
        if generator.startswith("Visual Studio "):
            configure += ["-A", "x64"]
        else:
            configure += ["-DCMAKE_CXX_COMPILER=cl"]
        run_logged(configure, root, logs / "configure.log", 600)
        run_logged([cmake, "--build", str(build), "--config", "Release", "--target",
                    "DWM2tPlayer", "--parallel", str(args.jobs)], root,
                   logs / "build.log", 10800)
        executable = build / ("Release/DWM2tRecomp.exe" if generator.startswith("Visual Studio ")
                              else "DWM2tRecomp.exe")
        check_pe_x64(executable)
        dispatch = build / "generated/player_romx_dispatch.cpp"
        cases = [(int(a), int(b)) for a, b in re.findall(
            r"case (\d+): return execute_romx_bank_(\d+)\(cpu, memory\);",
            dispatch.read_text(encoding="utf-8"))]
        if cases != [(bank, bank) for bank in range(1, 256)]:
            raise ValueError("Complete 255-bank AOT registry missing; packaging refused")
        if inventory(source) != before:
            raise ValueError("Source snapshot changed during the build; packaging refused")
        package = output / "DWM2t-M8-UNTESTED"
        package.mkdir()
        shutil.copy2(executable, package / "DWM2tRecomp.exe")
        for filename in ("Play.cmd", "Launch.ps1", "README.txt"):
            shutil.copy2(source / "recomp/release" / filename, package / filename)
        shutil.copy2(source / "LICENSE-NOTICE.md", package / "LICENSE-NOTICE.md")
        write_json(package / "source-manifest.json", before)
        metadata = dict(schema=1, status="UNTESTED_CANDIDATE", tests="not_run",
                        full_game_verified=False, m8_accepted=False, source_commit=commit,
                        created_utc=stamp, rom_sha256=ROM_SHA256, fixed_bank=0,
                        romx_banks=list(range(1, 256)), generator=generator,
                        executable_target="DWM2tPlayer",
                        requested_msvc_runtime=RUNTIME_SETTING, files=inventory(package))
        write_json(package / "manifest.json", metadata)
        zip_path = output / f"DWM2t-M8-UNTESTED-{commit[:12]}.zip"
        with zipfile.ZipFile(zip_path, "x", zipfile.ZIP_DEFLATED, compresslevel=6) as zipped:
            for path in sorted(package.iterdir()):
                zipped.write(path, f"{package.name}/{path.name}")
        shutil.copy2(build / "CMakeCache.txt", logs / "CMakeCache.txt")
        shutil.copy2(dispatch, logs / "romx_dispatch.cpp")
        report.update(status="built_untested", source_archive_sha256=digest(archive),
                      executable_sha256=digest(executable), zip_sha256=digest(zip_path),
                      zip=str(zip_path), native_build=str(build), generator=generator)
        write_json(output / "build-report.json", report)
        print(f"CANDIDATE_BUILT_UNTESTED {zip_path}", flush=True)
        print("No executable, test suite or gameplay session was run. M8 acceptance is pending.")
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError,
            tarfile.TarError, KeyError) as error:
        report.update(status="build_failed", error=str(error))
        # Never overwrite an existing output directory that we did not reserve.
        if output is not None and report.get("created_utc"):
            try:
                write_json(output / "build-report.json", report)
            except OSError:
                pass
        print(f"CANDIDATE_BUILD_FAILED: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
