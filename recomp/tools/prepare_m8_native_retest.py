#!/usr/bin/env python3
"""Rerun the original complete native suite on an unchanged archived diagnostic.

Only the Windows host changes. Source/test definitions come from the actual
fresh build archive; no game recompilation or fixture changes occur here.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as ET

from build_m8_candidate import (RUNTIME_SETTING, choose_generator, inventory,
                                run_logged, unpack_sources)
from m8_build_identity import digest, load_identity


def one(root: Path, pattern: str) -> Path:
    found = list(root.rglob(pattern))
    if len(found) != 1:
        raise ValueError(f'Expected exactly one {pattern} under {root}')
    return found[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('proof-root', 'workspace', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    for name in ('build-run-id', 'source'):
        parser.add_argument('--'+name, required=True)
    args = parser.parse_args()
    report = dict(schema=1, status='not_started', platform='Windows')
    output = None
    try:
        if os.name != 'nt' or not re.fullmatch(r'[0-9a-f]{40}', args.source) or not args.build_run_id.isdigit():
            raise ValueError('A Windows host and exact original build source/run are required')
        validation_run = os.environ.get('GITHUB_RUN_ID', '')
        packaging_source = os.environ.get('GITHUB_SHA', '')
        if not validation_run.isdigit() or not re.fullmatch(r'[0-9a-f]{40}', packaging_source):
            raise ValueError('The actual continuation workflow run/source must be recorded')
        workspace, candidate_output = args.workspace.resolve(), args.output.resolve()
        if (workspace.exists() or candidate_output.exists() or workspace == candidate_output
                or workspace in candidate_output.parents or candidate_output in workspace.parents):
            raise ValueError('Retest workspace/output must be new, separate directories')
        workspace.mkdir(parents=True)
        candidate_output.mkdir(parents=True)
        output = candidate_output
        diagnostic = args.proof_root/f'M8-fresh-diagnostic-{args.build_run_id}'
        production = args.proof_root/f'M8-fresh-production-{args.build_run_id}'
        identity_path = one(diagnostic, 'build-identity.json')
        identity = load_identity(identity_path)
        exe = one(diagnostic, 'DWM2tRecompFull.exe')
        identity.verify(exe)
        if identity.source != args.source:
            raise ValueError('Archived diagnostic differs from the requested original source')
        archive = one(diagnostic, 'source.tar')
        archive_sha = digest(archive)
        identity_data = json.loads(identity_path.read_text(encoding='utf-8'))
        build = json.loads(one(production, 'build-report.json').read_text(encoding='utf-8'))
        if (identity_data['source_archive_sha256'] != archive_sha
                or digest(one(production, 'source.tar')) != archive_sha
                or build['source_commit'] != args.source or build['source_archive_sha256'] != archive_sha):
            raise ValueError('The actual independent source archives differ')
        with tarfile.open(archive) as tar:
            if tar.pax_headers.get('comment') != args.source:
                raise ValueError('The original archive commit marker differs')
        source = workspace/'source'
        unpack_sources(archive, source)
        before = inventory(source)
        source_manifest = one(diagnostic, 'source-manifest.json')
        if (digest(source_manifest) != identity_data['source_manifest_sha256']
                or before != json.loads(source_manifest.read_text(encoding='utf-8'))):
            raise ValueError('The original test/source inventory differs')
        initial_tests = one(diagnostic, 'native-results.xml')
        report.update(source_commit=args.source, build_run_id=args.build_run_id,
                      validation_run_id=validation_run, packaging_source_commit=packaging_source,
                      diagnostic_sha256=identity.sha256, source_archive_sha256=archive_sha,
                      native_suite_source=args.source, native_suite_archive_sha256=archive_sha,
                      native_test_definitions_sha256=digest(source/'recomp/CMakeLists.txt'),
                      original_native_tests_sha256=digest(initial_tests))
        cmake, ctest = shutil.which('cmake'), shutil.which('ctest')
        if not cmake or not ctest:
            raise ValueError('CMake and CTest are required to configure the original suite')
        generator = choose_generator(cmake, None, source)
        native = workspace/'native'
        configure = [cmake, '-S', str(source/'recomp'), '-B', str(native), '-G', generator,
                     '-A', 'x64', '-DCMAKE_BUILD_TYPE=Release', '-DDWM2T_ALL_ROMX=ON',
                     '-DBUILD_TESTING=ON', '-DDWM2T_OUTPUT_NAME=DWM2tRecompFull',
                     f'-DCMAKE_MSVC_RUNTIME_LIBRARY={RUNTIME_SETTING}',
                     f'-DPython3_EXECUTABLE={sys.executable}']
        run_logged(configure, source, output/'configure.log', 600)
        copied = native/'Release/DWM2tRecompFull.exe'
        copied.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(exe, copied)
        identity.verify(copied)
        description = subprocess.check_output([ctest, '--test-dir', str(native), '-C', 'Release',
                                                '--show-only=json-v1'], cwd=source)
        (output/'ctest-description.json').write_bytes(description)
        xml = output/'native-results.xml'
        command = [ctest, '--test-dir', str(native), '-C', 'Release', '--parallel', '4',
                   '--output-on-failure', '--output-junit', str(xml)]
        report.update(status='running', command=command)
        with (output/'ctest.log').open('xb') as log:
            result = subprocess.run(command, cwd=source, stdout=log, stderr=subprocess.STDOUT,
                                    timeout=1800, check=False)
        report['ctest_returncode'] = result.returncode
        last_log = native/'Testing/Temporary/LastTest.log'
        if last_log.is_file():
            shutil.copyfile(last_log, output/'LastTest.log')
        if xml.is_file():
            report['retest_native_tests_sha256'] = digest(xml)
            cases = list(ET.parse(xml).getroot().iter('testcase'))
            report['tests'] = len(cases)
            if len(cases) != 18 or any(c.get('status') != 'run' or any(c.find(t) is not None
                    for t in ('skipped', 'failure', 'error')) for c in cases):
                raise ValueError('The original full 18-test suite has missing, failed or skipped cases')
        else:
            raise ValueError('The actual native CTest XML is missing')
        if result.returncode:
            raise ValueError('The unchanged native suite failed')
        identity.verify(exe)
        identity.verify(copied)
        if inventory(source) != before or digest(archive) != archive_sha:
            raise ValueError('The original source/test definitions changed during retesting')
        report.update(status='passed', source_inventory_unchanged=True,
                      executable_unchanged=True, game_recompilation_performed=False)
        print('M8_NATIVE_RETEST_PASS tests=18 skips=0 unchanged_executable='+identity.sha256, flush=True)
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        report.update(status='failed', error=str(error))
        print('M8_NATIVE_RETEST_FAIL', error, flush=True)
        return 1
    finally:
        if output and output.is_dir():
            (output/'native-retest-provenance.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    raise SystemExit(main())
