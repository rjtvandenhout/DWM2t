"""Verify independent runtime-core evidence; this is not campaign acceptance."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import xml.etree.ElementTree as ET

RUNTIME_CORE_TESTS = (
    'FullROM_memory_contracts', 'FullROM_runtime_contracts',
    'FullROM_serial_contracts', 'FullROM_renderer_contracts',
    'FullROM_generated_aot_contracts',
)
RUNTIME_CORE_TARGETS = (
    'DWM2tRuntimeCoreContracts', 'DWM2tRendererContracts',
    'DWM2tGeneratedAotContracts',
)
CORE_INPUTS = frozenset({
    *('recomp/src/'+name+'.cpp' for name in ('memory', 'apu', 'runtime', 'hram_exec', 'renderer')),
    *('recomp/include/recomp/'+name+'.hpp' for name in (
        'memory', 'apu', 'runtime', 'hram_exec', 'renderer', 'cpu', 'lr35902_exec',
        'bank0', 'romx', 'serial', 'atomic_sram')),
    *('recomp/tests/runtime-core/'+name for name in (
        'CMakeLists.txt', 'runtime_core_contracts.cpp', 'stub_dispatch.cpp',
        'renderer_contracts.cpp', 'generated_aot_contracts.cpp',
        'generate_aot_contract_fixtures.py')),
    *('recomp/tools/'+name+'.py' for name in (
        'lr35902', 'recompile_bank0', 'recompile_romx_bank', 'generate_romx_dispatch',
        'validate_runtime_core', 'full_rom_validation')),
})
RECEIPT_BUILD_PATHS = {
    **{f'FullROM_{group}_contracts': f'evidence/{group}/hardware-contracts.json'
       for group in ('memory', 'runtime', 'serial')},
    'FullROM_renderer_contracts': 'renderer-evidence/renderer-contracts.json',
    'FullROM_generated_aot_contracts': 'generated-aot-evidence/generated-aot-contracts.json',
}


def digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _sha(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value) is not None


def _relative(value: object) -> str:
    if (not isinstance(value, str) or not value or '\\' in value or ':' in value
            or value.startswith('/') or '..' in value.split('/')
            or '.' in value.split('/') or PurePosixPath(value).as_posix() != value):
        raise ValueError('Evidence paths must be canonical relative repository paths')
    return value


def _optional_input(path: str) -> bool:
    return ((path.startswith('recomp/include/recomp/') and path.endswith(('.hpp', '.h')))
            or (path.startswith('recomp/tests/runtime-core/')
                and path.endswith(('.cpp', '.hpp', '.h', '.py'))))


def collect_source_inputs(root: Path) -> dict[str, str]:
    """Inventory real compilation inputs without executing or generating code."""
    paths = set(CORE_INPUTS)
    for directory in (root/'recomp/include/recomp', root/'recomp/tests/runtime-core'):
        paths.update(path.relative_to(root).as_posix() for path in directory.rglob('*')
                     if path.is_file() and _optional_input(path.relative_to(root).as_posix()))
    result = {}
    for name in sorted(paths):
        path = root/name
        if not path.is_file() or path.is_symlink():
            raise ValueError('Missing regular runtime-core source input: '+name)
        result[name] = digest(path)
    return result


def verify_runtime_core_xml(path: Path) -> list[str]:
    data = path.read_bytes()
    if (not data or len(data) > 16*1024*1024 or b'<!DOCTYPE' in data.upper()
            or b'<!ENTITY' in data.upper()):
        raise ValueError('Missing or invalid runtime-core CTest XML')
    try:
        root = ET.fromstring(data)
    except ET.ParseError as error:
        raise ValueError('Malformed runtime-core CTest XML') from error
    cases = list(root.iter('testcase'))
    names = [case.get('name') for case in cases]
    if (root.tag != 'testsuite' or root.get('tests') != str(len(RUNTIME_CORE_TESTS))
            or len(list(root.iter('testsuite'))) != 1
            or len(names) != len(RUNTIME_CORE_TESTS) or len(set(names)) != len(names)
            or set(names) != set(RUNTIME_CORE_TESTS)
            or len(root.findall('testcase')) != len(cases)
            or any(case.get('status') != 'run' for case in cases)):
        raise ValueError('All five named runtime-core tests must actually run exactly once')
    if (any(node.tag in ('failure', 'error', 'skipped') for node in root.iter())
            or any(root.get(key, '0') != '0' for key in ('failures', 'errors', 'skipped', 'disabled'))):
        raise ValueError('Failed, skipped, disabled or errored runtime-core CTest gate')
    return names


def _artifact(root: Path, name: str) -> Path:
    path = root/_relative(name)
    if (not path.is_file() or path.is_symlink()
            or not path.resolve().is_relative_to(root.resolve())):
        raise ValueError('Missing or unsafe runtime-core artifact: '+name)
    return path


def _file_metadata(root: Path, item: object, expected_path: str) -> Path:
    if (not isinstance(item, dict) or item.get('path') != expected_path
            or not _sha(item.get('sha256')) or type(item.get('bytes')) is not int
            or item['bytes'] <= 0):
        raise ValueError('Incomplete runtime-core file identity: '+expected_path)
    path = _artifact(root, expected_path)
    if path.stat().st_size != item['bytes'] or digest(path) != item['sha256']:
        raise ValueError('Runtime-core file identity differs: '+expected_path)
    return path


def _commands(report: dict) -> None:
    commands = report.get('commands')
    if not isinstance(commands, dict) or set(commands) != {'configure', 'build', 'ctest'}:
        raise ValueError('All actual configure/build/CTest commands are required')
    for phase, executable in (('configure', 'cmake'), ('build', 'cmake'), ('ctest', 'ctest')):
        command = commands[phase]
        if (not isinstance(command, list) or not command
                or any(not isinstance(value, str) or not value for value in command)
                or command[0].replace('\\', '/').rsplit('/', 1)[-1].lower()
                not in (executable, executable+'.exe')):
            raise ValueError('Invalid actual runtime-core '+phase+' command')
    configure, build, ctest = (commands[name] for name in ('configure', 'build', 'ctest'))
    if (configure.count('-S') != 1 or configure.count('-B') != 1 or build.count('--build') != 1
            or '-DCMAKE_BUILD_TYPE=Release' not in configure
            or '-DBUILD_TESTING=ON' not in configure):
        raise ValueError('The actual standalone Release runtime-core build is required')
    source = configure[configure.index('-S')+1] if configure.index('-S')+1 < len(configure) else ''
    if not source.replace('\\', '/').rstrip('/').endswith('/recomp/tests/runtime-core'):
        raise ValueError('Runtime-core configuration must use its standalone source tree')
    if (ctest.count('--parallel') != 1 or '--output-on-failure' not in ctest
            or ctest.count('--output-junit') != 1 or ctest.count('--test-dir') != 1):
        raise ValueError('The complete actual runtime-core CTest command is required')
    for flag, expected in (('--parallel', '2'), ('--output-junit', 'runtime-core-tests.xml')):
        position = ctest.index(flag)+1
        value = ctest[position] if position < len(ctest) else ''
        if flag == '--output-junit':
            value = value.replace('\\', '/').rsplit('/', 1)[-1]
        if value != expected:
            raise ValueError('Runtime-core CTest command differs at '+flag)
    def argument(command: list[str], flag: str) -> str:
        index = command.index(flag)+1
        return command[index] if index < len(command) else ''
    directories = [argument(command, flag).replace('\\', '/').rstrip('/')
                   for command, flag in ((configure, '-B'), (build, '--build'), (ctest, '--test-dir'))]
    if (not directories[0] or len(set(directories)) != 1
            or '--config' not in build or argument(build, '--config') != 'Release'):
        raise ValueError('Configure/build/CTest must use the same standalone Release build directory')
    if ctest.count('-C') != 1 or argument(ctest, '-C') != 'Release':
        raise ValueError('Runtime-core CTest must use the actual Release executables')
    forbidden = ('-R', '-E', '-I', '-L', '-LE', '--rerun-failed', '--tests-regex',
                 '--exclude-regex', '--label-regex', '--label-exclude', '--tests-information',
                 '--tests-from-file', '--exclude-from-file', '--show-only', '-N')
    if any(value in forbidden or any(value.startswith(prefix+'=') for prefix in forbidden)
           or any(value.startswith(prefix) and value != prefix for prefix in ('-R', '-E', '-I', '-L'))
           for value in ctest[1:]):
        raise ValueError('Runtime-core CTest cannot select, exclude or merely list tests')


def _receipts(root: Path, report: dict) -> None:
    receipts = report.get('receipts')
    if not isinstance(receipts, dict) or set(receipts) != set(RUNTIME_CORE_TESTS):
        raise ValueError('Actual receipts from all five runtime-core tests are required')
    for name in RUNTIME_CORE_TESTS:
        path = _file_metadata(root, receipts[name], 'evidence/'+name+'.json')
        data = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(data, dict) or data.get('status') != 'passed':
            raise ValueError('A runtime-core test receipt failed: '+name)
        if name in RUNTIME_CORE_TESTS[:3]:
            cases = data.get('cases')
            if (type(data.get('schema')) is not int or data['schema'] != 1 or data.get('group') != name[8:-10]
                    or data.get('original_game_executed') is not False
                    or data.get('original_save_loaded_or_written') is not False
                    or type(data.get('original_rom_aot_entries')) is not int
                    or data['original_rom_aot_entries'] != 0 or data.get('fatal_error') != ''
                    or type(data.get('checks')) is not int or data['checks'] <= 0
                    or not isinstance(cases, list) or not cases):
                raise ValueError('Incomplete actual hardware receipt: '+name)
            for case in cases:
                if (not isinstance(case, dict) or not isinstance(case.get('name'), str)
                        or not case['name'] or case.get('status') != 'passed'
                        or case.get('error') != '' or type(case.get('checks')) is not int
                        or case['checks'] <= 0):
                    raise ValueError('Failed or unexecuted hardware subcase: '+name)
        elif name == 'FullROM_generated_aot_contracts':
            if (type(data.get('schema')) is not int or data['schema'] != 1 or type(data.get('checks')) is not int
                    or data['checks'] <= 0 or data.get('original_game_executed') is not False
                    or data.get('synthetic_fixture') is not True
                    or data.get('sparse_generated_cases') is not True
                    or data.get('full_bank_coverage_claimed') is not False):
                raise ValueError('Incomplete sparse generated-AOT unit receipt')
        elif (not isinstance(data.get('contracts'), list) or not data['contracts']
              or any(not isinstance(item, str) or not item for item in data['contracts'])):
            raise ValueError('Incomplete renderer contract receipt')
    fixture = json.loads(_file_metadata(root, report.get('generated_fixture'),
                        'evidence/generated-fixture-source.json').read_text(encoding='utf-8'))
    if (not isinstance(fixture, dict) or type(fixture.get('schema')) is not int
            or fixture['schema'] != 1 or fixture.get('synthetic_fixture') is not True
            or fixture.get('original_rom_read') is not False
            or fixture.get('original_game_executed') is not False
            or fixture.get('sparse_generated_cases') is not True
            or type(fixture.get('emitted_case_bodies')) is not int
            or fixture['emitted_case_bodies'] <= 0):
        raise ValueError('Generated-AOT fixture provenance is missing or overclaims game coverage')


def verify_runtime_core(report_path: Path, xml_path: Path, source: str, *,
                        source_manifest: dict[str, str] | None = None) -> dict:
    """Bind actual host contracts to exact source, input bytes, binaries and XML."""
    if not isinstance(source, str) or not re.fullmatch(r'[0-9a-f]{40}', source):
        raise ValueError('An exact forty-character source commit is required')
    report_path, xml_path = Path(report_path), Path(xml_path)
    report = json.loads(report_path.read_text(encoding='utf-8'))
    if (not isinstance(report, dict) or type(report.get('schema')) is not int
            or report['schema'] != 1 or report.get('kind') != 'full_rom_runtime_core_validation'
            or report.get('status') != 'passed' or report.get('source_commit') != source
            or report.get('platform') not in ('Windows', 'Linux')
            or report.get('source_inventory_unchanged') is not True
            or report.get('binaries_unchanged_after_ctest') is not True
            or report.get('orchestrator_inputs_match_source') is not True
            or report.get('original_game_executed') is not False
            or report.get('campaign_verified') is not False
            or report.get('full_rom_coverage_claimed') is not False
            or any(type(report.get(key)) is not int or report[key] != 0
                   for key in ('configure_returncode', 'build_returncode', 'ctest_returncode'))):
        raise ValueError('A passing exact-source Windows/Linux runtime-core report is required')
    names = verify_runtime_core_xml(xml_path)
    if (not _sha(report.get('xml_sha256')) or report['xml_sha256'] != digest(xml_path)
            or type(report.get('xml_bytes')) is not int
            or report['xml_bytes'] != xml_path.stat().st_size
            or type(report.get('tests')) is not int or report['tests'] != len(RUNTIME_CORE_TESTS)
            or report.get('test_names') != names):
        raise ValueError('Runtime-core report does not bind the actual complete CTest XML')
    _commands(report)
    hashes, lf_hashes = report.get('input_sha256'), report.get('lf_sha256')
    if (not isinstance(hashes, dict) or not hashes or not isinstance(lf_hashes, dict)
            or set(hashes) != set(lf_hashes) or not CORE_INPUTS.issubset(hashes)):
        raise ValueError('Every actual core/header/test/generator input must be inventoried')
    if source_manifest is not None:
        if (not isinstance(source_manifest, dict)
                or any(not isinstance(name, str) or not _sha(value)
                       for name, value in source_manifest.items())):
            raise ValueError('The archived production source inventory must be a path/hash mapping')
        expected = CORE_INPUTS | {name for name in source_manifest
                                  if isinstance(name, str) and _optional_input(name)}
        if set(hashes) != expected:
            raise ValueError('Runtime-core input inventory omits or adds archived source inputs')
    root = report_path.parent
    for name, actual_sha in hashes.items():
        _relative(name)
        if (name not in CORE_INPUTS and not _optional_input(name)) or not _sha(actual_sha) or not _sha(lf_hashes[name]):
            raise ValueError('Invalid runtime-core input path or hash')
        data = _artifact(root, 'source-inputs/'+name).read_bytes()
        lf = data.replace(b'\r\n', b'\n')
        if hashlib.sha256(data).hexdigest() != actual_sha or hashlib.sha256(lf).hexdigest() != lf_hashes[name]:
            raise ValueError('Archived runtime-core input bytes differ: '+name)
        if source_manifest is not None:
            archived_sha = source_manifest.get(name)
            crlf = lf.replace(b'\n', b'\r\n')
            if (not _sha(archived_sha) or (actual_sha != archived_sha
                    and (data not in (lf, crlf) or archived_sha not in
                         (lf_hashes[name], hashlib.sha256(crlf).hexdigest())))):
                raise ValueError('Runtime-core input differs from archived production source: '+name)
    binaries = report.get('binaries')
    if not isinstance(binaries, dict) or set(binaries) != set(RUNTIME_CORE_TARGETS):
        raise ValueError('Actual identities of all three tested host executables are required')
    suffix = '.exe' if report['platform'] == 'Windows' else ''
    for target in RUNTIME_CORE_TARGETS:
        _file_metadata(root, binaries[target], 'bin/'+target+suffix)
    _receipts(root, report)
    return dict(report, report_sha256=digest(report_path), source_manifest_verified=source_manifest is not None,
                input_files_verified=len(hashes), binary_files_verified=len(binaries))
