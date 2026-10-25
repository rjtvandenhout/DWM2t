#!/usr/bin/env python3
"""Build a fresh, isolated full-AOT diagnostic and record its exact identity.

This builds source only. Tests and original campaign replay run separately;
neither this identity nor successful compilation constitutes M8 acceptance.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from build_m8_candidate import (ROM_SHA256, SOURCE_PATHS, RUNTIME_SETTING, capture,
                                check_pe_x64, check_rom_identity, choose_generator,
                                digest, inventory, run_logged, unpack_sources, write_json)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--jobs', type=int, choices=range(1, 5), default=2)
    parser.add_argument('--generator', help='Explicit Visual Studio or Ninja generator; default auto-detects')
    args = parser.parse_args()
    report = dict(status='not_started', tests='not_run', full_game_verified=False)
    output = None
    try:
        if os.name != 'nt':
            raise ValueError('Fresh diagnostic builds require Windows x64 build tools')
        root = Path(__file__).resolve().parents[2]
        cmake, git = shutil.which('cmake'), shutil.which('git')
        if not cmake or not git:
            raise ValueError('CMake and Git are required')
        commit = capture([git, 'rev-parse', 'HEAD'], root)
        if not re.fullmatch(r'[0-9a-f]{40}', commit):
            raise ValueError('A complete pinned source revision is required')
        if capture([git, 'status', '--porcelain', '--untracked-files=normal', '--',
                    *SOURCE_PATHS], root):
            raise ValueError('Commit or isolate source changes before building')
        workspace, output = args.workspace.resolve(), args.output.resolve()
        if (workspace == output or workspace in output.parents or output in workspace.parents
                or workspace.exists() or output.exists()):
            raise ValueError('Workspace/output must be new, separate, non-nested directories')
        workspace.mkdir(parents=True)
        output.mkdir(parents=True)
        logs = output/'build-logs'
        logs.mkdir()
        report.update(status='building', source_commit=commit)
        archive = workspace/'source.tar'
        subprocess.run([git, 'archive', '--format=tar', '-o', str(archive), commit,
                        *SOURCE_PATHS], cwd=root, check=True, timeout=120)
        source = workspace/'source'
        unpack_sources(archive, source)
        before = inventory(source)
        write_json(output/'source-manifest.json', before)
        check_rom_identity(source)
        generator = choose_generator(cmake, args.generator, root)
        native = workspace/'native'
        configure = [cmake, '-S', str(source/'recomp'), '-B', str(native), '-G', generator,
                     '-DCMAKE_BUILD_TYPE=Release', '-DDWM2T_ALL_ROMX=ON', '-DBUILD_TESTING=ON',
                     '-DDWM2T_OUTPUT_NAME=DWM2tRecompFull',
                     f'-DCMAKE_MSVC_RUNTIME_LIBRARY={RUNTIME_SETTING}',
                     f'-DPython3_EXECUTABLE={sys.executable}']
        configure += ['-A', 'x64'] if generator.startswith('Visual Studio ') else ['-DCMAKE_CXX_COMPILER=cl']
        run_logged(configure, root, logs/'configure.log', 600)
        run_logged([cmake, '--build', str(native), '--config', 'Release', '--target',
                    'DWM2tRecomp', '--parallel', str(args.jobs)], root, logs/'build.log', 10800)
        exe = native/('Release/DWM2tRecompFull.exe' if generator.startswith('Visual Studio ')
                      else 'DWM2tRecompFull.exe')
        check_pe_x64(exe)
        dispatch = native/'generated/romx_dispatch.cpp'
        cases = [(int(a), int(b)) for a, b in re.findall(
            r'case (\d+): return execute_romx_bank_(\d+)\(cpu, memory\);',
            dispatch.read_text(encoding='utf-8'))]
        if cases != [(bank, bank) for bank in range(1, 256)]:
            raise ValueError('Incomplete static ROMX registry')
        if inventory(source) != before:
            raise ValueError('Archived source changed while building')
        copied = output/'DWM2tRecompFull.exe'
        shutil.copy2(exe, copied)
        identity = dict(schema=1, kind='complete_aot_diagnostic_build',
                        source_commit=commit, executable_sha256=digest(copied),
                        executable_bytes=copied.stat().st_size, build_testing=True,
                        fixed_bank=0, romx_banks=list(range(1, 256)), rom_sha256=ROM_SHA256,
                        source_archive_sha256=digest(archive),
                        source_manifest_sha256=digest(output/'source-manifest.json'),
                        tests='not_run', full_game_verified=False)
        write_json(output/'build-identity.json', identity)
        shutil.copy2(native/'CMakeCache.txt', logs/'CMakeCache.txt')
        shutil.copy2(dispatch, logs/'romx_dispatch.cpp')
        report.update(status='built_untested', native_build=str(native),
                      source=str(source), generator=generator, **identity)
        print('M8_DIAGNOSTIC_BUILT_UNTESTED', output, flush=True)
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        report.update(status='failed', error=str(error))
        print('M8_DIAGNOSTIC_BUILD_FAIL', error)
        return 1
    finally:
        if output and output.is_dir():
            write_json(output/'build-report.json', report)


if __name__ == '__main__':
    raise SystemExit(main())
