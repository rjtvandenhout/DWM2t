#!/usr/bin/env python3
"""Build/run independent actual-core contracts in a new evidence directory.

This deliberately does not compile or execute the original full game. The
generated-AOT target uses sparse synthetic unit fixtures and production emitters.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys

import full_rom_validation
from full_rom_validation import (
    RECEIPT_BUILD_PATHS, RUNTIME_CORE_TARGETS, collect_source_inputs, digest,
    verify_runtime_core, verify_runtime_core_xml,
)


def metadata(path: Path, output: Path) -> dict:
    return dict(path=path.relative_to(output).as_posix(), bytes=path.stat().st_size,
                sha256=digest(path))


def write_report(path: Path, report: dict) -> None:
    temporary = path.with_suffix('.json.pending')
    temporary.write_text(json.dumps(report, indent=2, sort_keys=True)+'\n', encoding='utf-8')
    os.replace(temporary, path)


def git_identity(root: Path, source: str, inputs: dict[str, str]) -> str:
    if not (root/'.git').exists():
        return 'supplied_archive_source_commit_with_recorded_actual_inputs'
    head = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'],
                                   text=True, encoding='utf-8', timeout=30).strip()
    if head != source:
        raise ValueError('The checked-out source commit differs from --source')
    tracked = subprocess.run(['git', '-C', str(root), 'ls-files', '--error-unmatch',
                              '--', *inputs], stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, timeout=30, check=False)
    diff = subprocess.run(['git', '-C', str(root), 'diff', '--quiet', source, '--', *inputs],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30, check=False)
    if tracked.returncode or diff.returncode:
        raise ValueError('Runtime-core inputs must be tracked, unchanged files of --source')
    return 'actual_git_HEAD_and_unchanged_tracked_inputs'


def run_step(command: list[str], phase: str, root: Path, output: Path,
             report: dict, timeout: int) -> None:
    report['commands'][phase] = command
    print('RUNTIME_CORE_STEP '+phase, flush=True)
    with (output/(phase+'.log')).open('xb') as stream:
        stream.write((json.dumps(command)+'\n').encode('utf-8'))
        stream.flush()
        result = subprocess.run(command, cwd=root, stdout=stream, stderr=subprocess.STDOUT,
                                env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'),
                                timeout=timeout, check=False)
    report[phase+'_returncode'] = result.returncode
    if result.returncode:
        raise RuntimeError(f'Runtime-core {phase} failed ({result.returncode}); see {phase}.log')


def copy_receipts(native: Path, output: Path, *, require_all: bool) -> dict:
    receipts = {}
    for name, relative in RECEIPT_BUILD_PATHS.items():
        original = native/relative
        if original.is_file():
            copied = output/'evidence'/(name+'.json')
            copied.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(original, copied)
            receipts[name] = metadata(copied, output)
        elif require_all:
            raise ValueError('Missing actual runtime-core test receipt: '+name)
    return receipts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source', required=True, help='Exact forty-character source commit')
    parser.add_argument('--source-root', type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    report = dict(schema=1, kind='full_rom_runtime_core_validation', status='not_started',
                  platform=platform.system(), source_commit=args.source, commands={},
                  configure_returncode=None, build_returncode=None, ctest_returncode=None,
                  original_game_executed=False, campaign_verified=False,
                  full_rom_coverage_claimed=False,
                  scope='Actual host hardware core with trapping ROM stubs, plus sparse production-emitted synthetic AOT contracts; no campaign or original full-ROM acceptance',
                  started_utc=datetime.now(timezone.utc).isoformat())
    output = None
    try:
        candidate = args.output.resolve()
        if candidate.exists():
            raise ValueError('--output must be a new directory; existing evidence is preserved')
        candidate.mkdir(parents=True)
        output = candidate
        if not re.fullmatch(r'[0-9a-f]{40}', args.source):
            raise ValueError('--source must be an exact forty-character commit')
        if report['platform'] not in ('Windows', 'Linux'):
            raise ValueError('Runtime-core validation requires an actual Windows or Linux host')
        root = args.source_root.resolve(strict=True)
        if (root == output or root.is_relative_to(output)
                or output.is_relative_to(root/'recomp/tests/runtime-core')
                or output.is_relative_to(root/'recomp/include/recomp')):
            raise ValueError('Output cannot contain or overlap runtime-core source inputs')
        before = collect_source_inputs(root)
        report.update(source_root=str(root), input_sha256=before, lf_sha256={},
                      source_identity=git_identity(root, args.source, before))
        for name, running in (
                ('recomp/tools/validate_runtime_core.py', Path(__file__).resolve()),
                ('recomp/tools/full_rom_validation.py', Path(full_rom_validation.__file__).resolve())):
            if (running.read_bytes().replace(b'\r\n', b'\n')
                    != (root/name).read_bytes().replace(b'\r\n', b'\n')):
                raise ValueError('Actual running validation tooling differs from --source-root: '+name)
        report['orchestrator_inputs_match_source'] = True
        for name, expected_sha in before.items():
            data = (root/name).read_bytes()
            if hashlib.sha256(data).hexdigest() != expected_sha:
                raise ValueError('Source changed while preserving runtime-core inputs: '+name)
            copied = output/'source-inputs'/name
            copied.parent.mkdir(parents=True, exist_ok=True)
            copied.write_bytes(data)
            report['lf_sha256'][name] = hashlib.sha256(data.replace(b'\r\n', b'\n')).hexdigest()
        cmake, ctest = shutil.which('cmake'), shutil.which('ctest')
        if not cmake or not ctest:
            raise ValueError('CMake and CTest must be installed on the actual host')
        native = output/'native'
        configure = [cmake, '-S', str(root/'recomp/tests/runtime-core'), '-B', str(native),
                     '-DCMAKE_BUILD_TYPE=Release', '-DBUILD_TESTING=ON',
                     '-DPython3_EXECUTABLE='+sys.executable]
        report['status'] = 'running'
        run_step(configure, 'configure', root, output, report, 180)
        run_step([cmake, '--build', str(native), '--config', 'Release', '--parallel', '2'],
                 'build', root, output, report, 600)
        suffix = '.exe' if report['platform'] == 'Windows' else ''
        built = {}
        report['binaries'] = {}
        for target in RUNTIME_CORE_TARGETS:
            candidates = [path for path in (native/(target+suffix), native/'Release'/(target+suffix))
                          if path.is_file()]
            if len(candidates) != 1:
                raise ValueError('Expected one actual built host executable: '+target)
            original = candidates[0]
            copied = output/'bin'/(target+suffix)
            copied.parent.mkdir(exist_ok=True)
            shutil.copyfile(original, copied)
            report['binaries'][target] = metadata(copied, output)
            built[target] = original
        xml = output/'runtime-core-tests.xml'
        command = [ctest, '--test-dir', str(native), '-C', 'Release', '--parallel', '2',
                   '--output-on-failure', '--output-junit', str(xml)]
        try:
            run_step(command, 'ctest', root, output, report, 300)
        finally:
            report['receipts'] = copy_receipts(native, output, require_all=False)
            if xml.is_file():
                report.update(xml_sha256=digest(xml), xml_bytes=xml.stat().st_size)
            fixture = native/'generated-fixtures/fixture-source.json'
            if fixture.is_file():
                copied = output/'evidence/generated-fixture-source.json'
                copied.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(fixture, copied)
                report['generated_fixture'] = metadata(copied, output)
            last_log = native/'Testing/Temporary/LastTest.log'
            if last_log.is_file():
                shutil.copyfile(last_log, output/'LastTest.log')
        names = verify_runtime_core_xml(xml)
        report.update(tests=len(names), test_names=names,
                      receipts=copy_receipts(native, output, require_all=True),
                      source_inventory_unchanged=collect_source_inputs(root) == before,
                      binaries_unchanged_after_ctest=all(
                          digest(path) == report['binaries'][name]['sha256']
                          and path.stat().st_size == report['binaries'][name]['bytes']
                          for name, path in built.items()))
        report['status'] = 'passed'
        write_report(output/'runtime-core-validation.json', report)
        verify_runtime_core(output/'runtime-core-validation.json', xml, args.source)
        print('RUNTIME_CORE_VALIDATION_PASS tests='+str(len(names))+' source='+args.source,
              flush=True)
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        report.update(status='failed', error=str(error))
        print('RUNTIME_CORE_VALIDATION_FAIL '+str(error), flush=True)
        return 1
    finally:
        if output is not None:
            report['completed_utc'] = datetime.now(timezone.utc).isoformat()
            write_report(output/'runtime-core-validation.json', report)


if __name__ == '__main__':
    raise SystemExit(main())
