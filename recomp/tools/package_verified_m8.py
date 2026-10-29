"""Package the unchanged tested player only after the complete M8 gates pass.

Inputs retain their original build/story run. An optional full native-suite
rerun must bind the unchanged diagnostic to its original test sources and a
separate validation run. No build or executable patch is performed here.
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
import subprocess
import tarfile
import xml.etree.ElementTree as ET
import zipfile

from m8_build_identity import digest, load_identity
from m8_package import BASE_FILES, verify_package
from test_m8_story_checkpoints import verify_ending_witnesses


NATIVE_SUITE_TESTS = (
    'M1_decoder', 'M2_bank0_audit', 'M4_renderer', 'M5_title',
    'M6_movement', 'M6_sram', 'M6_window', 'M7_audio', 'M7_intro_p1',
    'M7_party_p1', 'M7_battle', 'M7_save_continue', 'M8_trace_contract',
    'M8_audio_selection', 'M8_audio_presentation', 'M8_audio_playback',
    'M8_audio_stream', 'M8_oasis_checkpoint',
)


def one(root: Path, pattern: str) -> Path:
    found = list(root.rglob(pattern))
    if len(found) != 1:
        raise ValueError(f'Expected one {pattern} under {root.name}, found {len(found)}')
    return found[0]


def passed_json(path: Path, source: str, executable: str) -> dict:
    report = json.loads(path.read_text(encoding='utf-8'))
    if (report.get('status') != 'passed' or report.get('platform') != 'Windows'
            or report.get('source', report.get('executable_source')) != source
            or report.get('executable_sha256') != executable):
        raise ValueError('Missing passing exact-source native Windows report: '+str(path))
    return report


def passed_ctest(path: Path, minimum: int) -> int:
    root = ET.parse(path).getroot()
    cases = list(root.iter('testcase'))
    if len(cases) < minimum or any(case.find(tag) is not None for case in cases
                                 for tag in ('failure', 'error', 'skipped')):
        raise ValueError('Missing, failed or skipped required CTest gate: '+str(path))
    for suite in root.iter('testsuite'):
        if any(int(suite.get(key, '0')) for key in ('failures', 'errors', 'skipped', 'disabled')):
            raise ValueError('Incomplete CTest suite: '+str(path))
    return len(cases)


def current_packaging_source() -> str:
    root = Path(__file__).resolve().parents[2]
    commit = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'],
                                    text=True, encoding='utf-8', timeout=30).strip()
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise ValueError('An exact packaging source commit is required')
    return commit


def native_suite_names(path: Path, *, passing: bool) -> None:
    root = ET.parse(path).getroot()
    cases = list(root.iter('testcase'))
    names = [case.get('name') for case in cases]
    if (len(names) != len(NATIVE_SUITE_TESTS) or len(set(names)) != len(names)
            or set(names) != set(NATIVE_SUITE_TESTS)):
        raise ValueError('The native suite must contain all 18 original test names exactly once')
    if passing:
        passed_ctest(path, len(NATIVE_SUITE_TESTS))
        if (root.tag != 'testsuite' or root.get('tests') != str(len(NATIVE_SUITE_TESTS))
                or any(case.get('status') != 'run' for case in cases)):
            raise ValueError('The complete native rerun did not actually run all 18 tests')


def verify_native_retest(directory: Path, source: str, build_run: str,
                         validation_run: str, diagnostic_exe: Path,
                         source_archive: Path, initial_xml: Path) -> tuple[dict, dict[str, Path]]:
    if (not re.fullmatch(r'[1-9][0-9]*', validation_run)
            or validation_run == build_run):
        raise ValueError('The native rerun needs its distinct actual validation run ID')
    provenance_path = directory/'native-retest-provenance.json'
    retest_xml = directory/'native-results.xml'
    provenance = json.loads(provenance_path.read_text(encoding='utf-8'))
    packaging_source = current_packaging_source()
    if (os.environ.get('GITHUB_SHA', packaging_source) != packaging_source
            or os.environ.get('GITHUB_RUN_ID', validation_run) != validation_run):
        raise ValueError('The native rerun must match the actual packaging workflow/run')
    source_sha = digest(source_archive)
    try:
        with tarfile.open(source_archive, 'r:') as archived:
            definitions = [member for member in archived.getmembers()
                           if member.name == 'recomp/CMakeLists.txt']
            if (archived.pax_headers.get('comment') != source or len(definitions) != 1
                    or not definitions[0].isfile()):
                raise ValueError('Original native CTest definitions are missing from the exact source archive')
            stream = archived.extractfile(definitions[0])
            if stream is None:
                raise ValueError('Original native CTest definitions cannot be read')
            with stream:
                definition_bytes = stream.read()
    except tarfile.TarError as error:
        raise ValueError('The native rerun requires the actual original source archive') from error
    definition_names = re.findall(rb'add_test\(NAME\s+([A-Za-z0-9_]+)', definition_bytes)
    if (len(definition_names) != len(NATIVE_SUITE_TESTS)
            or {name.decode('ascii') for name in definition_names} != set(NATIVE_SUITE_TESTS)):
        raise ValueError('The archived original CMake definitions do not declare the complete native suite')
    required = dict(schema=1, status='passed', platform='Windows', source_commit=source,
                    build_run_id=build_run, validation_run_id=validation_run,
                    packaging_source_commit=packaging_source,
                    diagnostic_sha256=digest(diagnostic_exe), source_archive_sha256=source_sha,
                    native_suite_source=source, native_suite_archive_sha256=source_sha,
                    native_test_definitions_sha256=hashlib.sha256(definition_bytes).hexdigest(),
                    original_native_tests_sha256=digest(initial_xml),
                    retest_native_tests_sha256=digest(retest_xml),
                    ctest_returncode=0, tests=len(NATIVE_SUITE_TESTS))
    if (any(provenance.get(key) != expected for key, expected in required.items())
            or any(type(provenance.get(key)) is not int for key in ('schema', 'ctest_returncode', 'tests'))):
        raise ValueError('Native rerun provenance does not bind the actual unchanged binary, sources, XML and runs')
    command = provenance.get('command')
    if (not isinstance(command, list) or not command
            or not all(isinstance(argument, str) and argument for argument in command)
            or command[0].replace('\\', '/').rsplit('/', 1)[-1].lower() not in ('ctest', 'ctest.exe')
            or command.count('--output-junit') != 1):
        raise ValueError('Native rerun provenance needs the actual full CTest command')
    junit_index = command.index('--output-junit') + 1
    if (junit_index >= len(command)
            or command[junit_index].replace('\\', '/').rsplit('/', 1)[-1] != 'native-results.xml'
            or any(argument in ('-R', '-E', '-I', '--rerun-failed', '--tests-from-file',
                                '--exclude-from-file', '--tests-regex', '--exclude-regex')
                   or argument.startswith(('-R', '-E', '-I', '--tests-regex=', '--exclude-regex=',
                                           '--tests-from-file=', '--exclude-from-file='))
                   for argument in command[1:])):
        raise ValueError('The native rerun must run the complete original suite without selection filters')
    native_suite_names(initial_xml, passing=False)
    native_suite_names(retest_xml, passing=True)
    return provenance, {'initial-native-tests.xml': initial_xml,
                        'native-tests.xml': retest_xml,
                        'native-retest-provenance.json': provenance_path}


FULL_ROM_HEADER = 'recomp/include/recomp/serial.hpp'
POSTGAME_MANIFEST = 'recomp/tests/m8_postgame_supplemental.json'
POSTGAME_SCOPE = 'Supplemental pinned original-P1 postgame replay and fresh Continue only'
FULL_ROM_LIMITATIONS = (
    'The supplemental checkpoints do not establish every optional postgame or catalogue reward.',
    'Rare-arrival and distribution reachability remains unverified.',
    'Finite original generator tables and pinned worlds do not establish every random seed.',
    'The Tara ROM/version has not been played or accepted; this package uses the original Cobi ROM.',
    'The two-player host is verified separately from original linked transactions; not every original link mode has been completed.',
)


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _repository_path(name: object) -> bool:
    return (isinstance(name, str) and bool(name) and '\\' not in name and ':' not in name
            and not name.startswith('/') and not any(part in ('', '.', '..') for part in name.split('/'))
            and PurePosixPath(name).as_posix() == name)


def _newline_equivalent(left: bytes, right: bytes) -> bool:
    # Permit only checkout newline conversion, never arbitrary whitespace or
    # semantically equivalent but changed JSON, routes or source files.
    return left == right or left.replace(b'\r\n', b'\n') == right.replace(b'\r\n', b'\n')


def _newline_variants(data: bytes) -> dict[str, bytes]:
    lf = data.replace(b'\r\n', b'\n')
    return {_sha_bytes(item): item for item in (data, lf, lf.replace(b'\n', b'\r\n'))}


SPLIT_GUI_SCRIPTS = (
    'recomp/tools/test_player_local_link.py',
    'recomp/tools/test_player_late_journal.py',
    'recomp/tools/test_player_package.py',
    'recomp/tools/prepare_m8_player_validation.py',
    'recomp/tools/package_verified_m8.py',
    'recomp/tools/restore_original_validation.py',
    'recomp/tools/attest_revalidated_gui.py',
    'recomp/tools/prepare_m8_native_retest.py',
    'recomp/tools/setup_windows_ci_audio.ps1',
    '.github/workflows/recomp-resume-verified.yml',
    '.github/workflows/recomp-player-validation.yml',
)
SPLIT_GUI_REPORTS = (
    'production-local-link/player-local-link.json',
    'player-package/player-package.json',
    'production-journal/player-late-journal.json',
    'production-ending-journal/player-late-journal.json',
    'production-local-link/same-file-alias.stderr.log',
    'production-local-link/competing-player2.stderr.log',
)


def committed_tooling_script_hashes(tooling_source: str) -> dict[str, str]:
    """Bind the executed checkout files to the named committed tooling source."""
    root = Path(__file__).resolve().parents[2]
    result = {}
    for name in SPLIT_GUI_SCRIPTS:
        path = root/name
        actual = path.read_bytes()
        try:
            committed = subprocess.check_output(
                ['git', '-C', str(root), 'show', tooling_source+':'+name], timeout=30)
        except (OSError, subprocess.SubprocessError) as error:
            raise ValueError('Cannot read the committed GUI tooling script: '+name) from error
        if not _newline_equivalent(actual, committed):
            raise ValueError('GUI tooling checkout differs from its committed source: '+name)
        result[name] = _sha_bytes(actual)
    return result


def verify_original_build_artifact_manifest(path: Path, source: str, build_run: str) -> dict:
    """Require the recorded successful original producers and exact artifact metadata."""
    manifest = json.loads(path.read_text(encoding='utf-8'))
    required = dict(schema=1, kind='original_build_artifacts', status='passed',
                    build_run_id=build_run, build_source_commit=source)
    if (any(manifest.get(key) != value or type(manifest.get(key)) is not type(value)
            for key, value in required.items())
            or manifest.get('run_conclusion') not in ('success', 'failure', 'cancelled')):
        raise ValueError('Original build artifact manifest has the wrong source, run or status')
    jobs = manifest.get('producer_jobs')
    if not isinstance(jobs, dict) or set(jobs) != {'diagnostic', 'production', 'posix-persistence'}:
        raise ValueError('Original successful producer jobs are incomplete')
    job_ids = []
    for job in jobs.values():
        if (not isinstance(job, dict) or type(job.get('id')) is not int or job['id'] <= 0
                or job.get('conclusion') != 'success'):
            raise ValueError('An original producer job did not succeed')
        job_ids.append(job['id'])
    if len(set(job_ids)) != len(job_ids):
        raise ValueError('Original producer jobs must be distinct')
    artifacts = manifest.get('artifacts')
    expected = {'diagnostic', 'production', 'story', 'postgame', 'posix-persistence'}
    if not isinstance(artifacts, dict) or set(artifacts) != expected:
        raise ValueError('Original build artifact metadata is incomplete')
    artifact_ids = []
    for kind, artifact in artifacts.items():
        if (not isinstance(artifact, dict) or type(artifact.get('id')) is not int
                or artifact['id'] <= 0 or type(artifact.get('size_bytes')) is not int
                or artifact['size_bytes'] <= 0
                or artifact.get('name') != f'M8-fresh-{kind}-{build_run}'
                or not isinstance(artifact.get('sha256'), str)
                or re.fullmatch(r'[0-9a-f]{64}', artifact['sha256']) is None):
            raise ValueError('Original artifact ID, name, size or ZIP digest is invalid: '+kind)
        artifact_ids.append(artifact['id'])
    if len(set(artifact_ids)) != len(artifact_ids):
        raise ValueError('Original build artifacts must be distinct')
    return manifest


def verify_split_gui_package_gate(report: dict, late_sha: str) -> None:
    """Require the actual original-seed, profile, lock, backup and launcher checks."""
    expected = {'authentic_later_journal_seed', 'windows_powershell_available',
                'first_native_window_created', 'second_native_window_created',
                'separate_profiles_run_concurrently', 'actual_duplicate_native_instance_is_refused',
                'duplicate_never_creates_game_window', 'duplicate_lock_preserves_active_save',
                'import_refuses_existing_profile_without_replacement',
                'changed_package_is_refused_before_import', 'original_journal_and_package_are_unchanged'}
    for profile in ('first', 'second'):
        expected.update(f'{profile}_'+suffix for suffix in (
            'launcher_reports_normal_exit', 'cartridge_sram_remains_exact_size',
            'session_log_created', 'session_log_has_actual_exit_status',
            'launcher_and_native_prelaunch_backups_are_recoverable'))
    checks = report.get('checks')
    if (report.get('seed_sha256') != late_sha or report.get('via_cmd') is not False
            or not isinstance(checks, list) or any(not isinstance(value, str) for value in checks)
            or not expected.issubset(checks)
            or type(report.get('duplicate_exit_code')) is not int
            or report['duplicate_exit_code'] == 0
            or report.get('duplicate_error_dialog_seen') is not True):
        raise ValueError('Separate production package gate lacks the original-seed and launcher checks')


def verify_production_journal_attestation(
        path: Path, gui: Path, *, source: str, build_run: str, validation_run: str,
        retest: dict, executable_sha: str, executable_bytes: int, source_archive: Path,
        ending: Path, ending_sha: str, late: Path, late_sha: str) -> tuple[dict, dict[str, Path]]:
    """Bind fresh production GUI gates to original bytes and a separate tooling run."""
    attestation = json.loads(path.read_text(encoding='utf-8'))
    tooling_source = current_packaging_source()
    if (retest.get('packaging_source_commit') != tooling_source
            or os.environ.get('GITHUB_SHA', tooling_source) != tooling_source
            or os.environ.get('GITHUB_RUN_ID', validation_run) != validation_run):
        raise ValueError('GUI validation must match the actual native-retest tooling run')
    if (ending.stat().st_size != 32768 or digest(ending) != ending_sha
            or late.stat().st_size != 32768 or digest(late) != late_sha):
        raise ValueError('GUI validation inputs are not the actual original story Journals')
    required = dict(schema=1, kind='production_journal_revalidation', status='passed',
                    platform='Windows', build_run_id=build_run, build_source_commit=source,
                    validation_run_id=validation_run, tooling_source_commit=tooling_source,
                    production_executable_sha256=executable_sha,
                    production_executable_bytes=executable_bytes,
                    source_archive_sha256=digest(source_archive),
                    ending_journal_sha256=ending_sha, late_journal_sha256=late_sha)
    if any(attestation.get(key) != value or type(attestation.get(key)) is not type(value)
           for key, value in required.items()):
        raise ValueError('Production Journal attestation differs from the actual build or validation run')
    original_manifest = gui/'original-artifact-manifest.json'
    if (not original_manifest.is_file()
            or attestation.get('original_artifact_manifest_sha256') != digest(original_manifest)):
        raise ValueError('Original producer/artifact metadata differs from the GUI attestation')
    verify_original_build_artifact_manifest(original_manifest, source, build_run)
    scripts = attestation.get('scripts')
    if not isinstance(scripts, dict) or scripts != committed_tooling_script_hashes(tooling_source):
        raise ValueError('GUI validation scripts differ from the actual committed tooling checkout')
    reports = attestation.get('reports')
    if not isinstance(reports, dict) or set(reports) != set(SPLIT_GUI_REPORTS):
        raise ValueError('GUI attestation must bind each original production gate report')
    for name in SPLIT_GUI_REPORTS:
        report = gui/name
        if not report.is_file() or reports[name] != digest(report):
            raise ValueError('Production GUI report differs from its attestation: '+name)
    link = json.loads((gui/SPLIT_GUI_REPORTS[0]).read_text(encoding='utf-8'))
    if (link.get('gate_script_sha256') != scripts[SPLIT_GUI_SCRIPTS[0]]
            or link.get('gui_helper_sha256') != scripts[SPLIT_GUI_SCRIPTS[1]]):
        raise ValueError('Production link report used different GUI gate or helper scripts')
    return attestation, {'production-journal-attestation.json':path,
                         'original-build-artifacts.json':original_manifest,
                         'same-file-alias-stderr.txt':gui/SPLIT_GUI_REPORTS[4],
                         'competing-player2-stderr.txt':gui/SPLIT_GUI_REPORTS[5]}


def full_rom_source_inputs(candidate: Path, archive: Path, source: str,
                           identity: dict) -> tuple[dict[str, str], dict[str, bytes]] | None:
    """Detect new sources and bind their complete inventory to the real Git tar.

    Historical packages retain their original gates. The archive is also
    inspected so removing serial.hpp from a new manifest cannot bypass them.
    Legacy synthetic package contracts intentionally have neither a JSON
    inventory nor a tar archive; they remain historical fixtures.
    """
    raw = (candidate/'source-manifest.json').read_bytes()
    try:
        inputs = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError):
        inputs = None
    manifest_new = isinstance(inputs, dict) and FULL_ROM_HEADER in inputs
    try:
        archived = tarfile.open(archive, 'r:')
    except tarfile.TarError as error:
        if manifest_new or FULL_ROM_HEADER.encode() in raw:
            raise ValueError('Full-ROM acceptance requires the actual source archive') from error
        return None
    with archived:
        members = archived.getmembers()
        archive_new = any(member.name.rstrip('/') == FULL_ROM_HEADER for member in members)
        if not manifest_new and not archive_new:
            return None
        if (not manifest_new or not isinstance(inputs, dict)
                or digest(candidate/'source-manifest.json') != identity.get('source_manifest_sha256')
                or archived.pax_headers.get('comment') != source
                or any(not _repository_path(name) or not isinstance(sha, str)
                       or re.fullmatch(r'[0-9a-f]{64}', sha) is None
                       for name, sha in inputs.items())):
            raise ValueError('Full-ROM source inventory does not identify the exact archived commit')
        files = set()
        retained = {}
        keep = {POSTGAME_MANIFEST, 'recomp/tools/test_m8_story_checkpoints.py',
                'recomp/tools/test_player_local_link.py', 'recomp/tools/test_player_late_journal.py'}
        for member in members:
            name = member.name.rstrip('/') if member.isdir() else member.name
            if not _repository_path(name) or not (member.isfile() or member.isdir()):
                raise ValueError('Unsafe full-ROM source archive member')
            if member.isdir():
                continue
            if name in files or name not in inputs:
                raise ValueError('Full-ROM archived source inventory has duplicate or unlisted files')
            files.add(name)
            stream = archived.extractfile(member)
            if stream is None:
                raise ValueError('Unreadable full-ROM source archive member: '+name)
            with stream:
                if name in keep:
                    data = stream.read()
                    actual = _sha_bytes(data)
                    retained[name] = data
                else:
                    actual = hashlib.file_digest(stream, 'sha256').hexdigest()
            if actual != inputs[name]:
                raise ValueError('Archived source bytes differ from the production inventory: '+name)
        if files != set(inputs) or not keep.issubset(retained):
            raise ValueError('Full-ROM source archive is incomplete')
        return inputs, retained


def verify_postgame_gate(directory: Path, source: str, run: str, identity: dict,
                         source_inputs: dict[str, str], archived: dict[str, bytes],
                         ending: Path, ending_sha: str, manifest_path: Path) -> tuple[dict, dict[str, Path]]:
    """Recheck actual replay inputs, owned records and all cache slots read-only."""
    from test_m8_story_checkpoints import audit_journal_chain
    from test_postgame_supplemental import (POSTGAME_STAGE_NAMES, verify_buffers,
                                           verify_replay_provenance)

    path = one(directory, 'postgame-supplemental-validation.json')
    report = passed_json(path, source, identity['executable_sha256'])
    required = dict(schema=1, diagnostic_build_mode='fresh_diagnostic', build_run_id=run,
                    supplemental_validation_run_id=run, tooling_source_commit=source,
                    scope=POSTGAME_SCOPE, seed_sha256=ending_sha,
                    executable_source=source, executable_bytes=identity['executable_bytes'],
                    source_archive_sha256=identity['source_archive_sha256'],
                    source_manifest_sha256=identity['source_manifest_sha256'],
                    build_identity_sha256=identity['build_identity_sha256'], runner_returncode=0,
                    seed_chain_links=len(POSTGAME_STAGE_NAMES), full_postgame_verified=False,
                    all_random_seeds_verified=False, new_binary_accepted=False,
                    accepted_package_changed=False)
    if (any(report.get(key) != expected for key, expected in required.items())
            or any(type(report.get(key)) is not type(required[key]) for key in required)
            or type(report.get('workers')) is not int or report['workers'] not in range(1, 5)):
        raise ValueError('Fresh exact-build supplemental postgame provenance is incomplete')
    data = archived[POSTGAME_MANIFEST]
    if (not _newline_equivalent(manifest_path.read_bytes(), data)
            or _sha_bytes(data) != source_inputs[POSTGAME_MANIFEST]
            or report.get('manifest_sha256') not in _newline_variants(data)):
        raise ValueError('Committed postgame pins differ from the actual archived source')
    runner = archived['recomp/tools/test_m8_story_checkpoints.py']
    if report.get('runner_sha256') not in _newline_variants(runner):
        raise ValueError('Postgame replay used a different source runner')
    pins = json.loads(data)
    if (not isinstance(pins, dict) or pins.get('seed_sha256') != ending_sha
            or not isinstance(pins.get('stages'), list)
            or any(not isinstance(stage, dict) for stage in pins['stages'])
            or tuple(stage.get('name') for stage in pins['stages']) != POSTGAME_STAGE_NAMES):
        raise ValueError('All seven ordered committed postgame pins are required')
    base_path = path.parent/'story-checkpoints-validation.json'
    base = json.loads(base_path.read_text(encoding='utf-8'))
    provenance = {key: identity[key] for key in ('executable_sha256', 'executable_bytes',
                                                'build_identity_sha256')}
    provenance['executable_source'] = source
    verify_replay_provenance(base, pins['stages'], provenance, 'Windows', 0)
    stages = report.get('stages')
    if not isinstance(stages, list) or len(stages) != len(POSTGAME_STAGE_NAMES):
        raise ValueError('Missing ordered postgame persistence observations')
    completed = {stage['name']: path.parent/stage['name']/'native/checkpoint.sav'
                 for stage in pins['stages']}
    links = audit_journal_chain(pins, path.parent, ending, completed)
    for expected, actual in zip(pins['stages'], stages, strict=True):
        name = expected['name']
        if (not isinstance(actual, dict) or actual.get('stage') != name
                or actual.get('save_sha256') != expected['save_sha256']
                or not _repository_path(expected.get('route'))):
            raise ValueError('Postgame stage order or actual save pin differs: '+name)
        route = path.parent/name/expected['route']
        if digest(route) != expected['route_sha256']:
            raise ValueError('Actual postgame route differs from its source pin: '+name)
        native = path.parent/name/'native'
        captures = [native/'checkpoint.sav', native/'fresh_continue/m8_0.sram',
                    native/'m8_0.ram', native/'fresh_continue/m8_0.ram']
        observations = {item.relative_to(path.parent).as_posix(): digest(item) for item in captures}
        observed = verify_buffers(*(item.read_bytes() for item in captures), expected)
        if (actual.get('observation_sha256') != observations
                or any(actual.get(key) != value for key, value in observed.items())):
            raise ValueError('Actual owned/cache/Continue observations differ from the report: '+name)
    return dict(postgame_checkpoints=len(stages), postgame_seed_chain_links=links,
                postgame_seed_chain_audited=True, postgame_owned_and_cache_verified=True,
                postgame_manifest_sha256=source_inputs[POSTGAME_MANIFEST],
                postgame_replayed_manifest_sha256=report['manifest_sha256']), {
                    'postgame-validation.json': path, 'postgame-replay.json': base_path}


def verify_local_link_gate(path: Path, source: str, executable_sha: str,
                           executable_bytes: int, ending: Path, ending_sha: str, *,
                           require_alias_rejection: bool = False) -> dict:
    """Require actual two-window production lifecycle, without a protocol claim."""
    from test_player_late_journal import verify_saved_roster

    report = passed_json(path, source, executable_sha)
    required = dict(schema=1, kind='production_local_link_gui', players=2,
                    executable_bytes=executable_bytes, input_journal_sha256=ending_sha,
                    input_journal_bytes=32768, original_p1_only=True, game_memory_edits=False,
                    serial_protocol_success_verified=False, full_game_verified=False,
                    fresh_process_reload=True, normal_shutdowns=2, shutdown_players=[2, 1],
                    input_isolation_verified=True, game_windows_per_launch=2,
                    normal_close_save_integrity_verified=True, quest_bytes=107)
    if any(report.get(key) != value or type(report.get(key)) is not type(value)
           for key, value in required.items()):
        raise ValueError('Production two-player original-P1 host lifecycle is incomplete')
    checks = report.get('checks')
    expected_checks = {'players_have_distinct_original_journal_files',
                       'genuine_original_ending_journal_is_pinned', 'original_ending_quest_flag_is_present',
                       'competing-player2_refused_for_expected_reason',
                       'peer_lock_rejection_keeps_both_original_games_running',
                       'competing_process_does_not_replace_player2_save',
                       'source_journal_and_production_executable_are_unchanged',
                       'both_games_leave_no_pending_save_temporaries'}
    for round_name, close_player in (('continue', 2), ('reload', 1)):
        expected_checks.update({round_name+'_two_distinct_windows_share_one_owned_process',
                               round_name+'_player1_inputs_did_not_continue_or_open_player2_menu',
                               round_name+'_player2_inputs_did_not_open_player1_menu',
                               round_name+'_both_original_rosters_and_quest_bytes_preserved',
                               f'{round_name}_close_player{close_player}_normally_closes_both_windows'})
        for player in (1, 2):
            expected_checks.update(f'{round_name}_player{player}_'+suffix for suffix in (
                'native_save_lock_held', 'native_save_lock_released',
                'original_ending_continue', 'original_ending_party_hud'))
    if require_alias_rejection:
        expected_checks.update({'same-file-alias_refused_for_expected_reason',
                                'same-file-alias_left_no_owned_windows',
                                'same-file-alias_owned_expected_error_dialog_observed',
                                'same-file-alias_error_dialog_close_message_delivered',
                                'same_file_rejection_preserves_both_original_copies',
                                'competing-player2_owned_expected_error_dialog_observed',
                                'competing-player2_error_dialog_close_message_delivered',
                                'competing-player2_left_no_owned_windows'})
    if (not isinstance(checks, list) or any(not isinstance(value, str) for value in checks)
            or not expected_checks.issubset(checks)):
        raise ValueError('Missing original Continue, input isolation, lock or normal-close checks')
    if require_alias_rejection:
        rejected = report.get('rejections')
        for label, reason in (('same-file-alias', 'two different save'), ('competing-player2', 'locked')):
            matches = ([item for item in rejected
                        if isinstance(item, dict) and item.get('label') == label]
                       if isinstance(rejected, list) else [])
            if len(matches) != 1:
                raise ValueError('Production rejection process evidence is incomplete: '+label)
            item = matches[0]
            dialog, attempts = item.get('dialog'), item.get('close_attempts')
            if (type(item.get('exit_code')) is not int or item['exit_code'] != 1
                    or item.get('reason') != reason or item.get('dialog_observed') is not True
                    or item.get('stderr_reason_matched') is not True
                    or item.get('error_dialog_dismissed') is not True
                    or not isinstance(dialog, dict) or dialog.get('kind') != '#32770'
                    or dialog.get('title') != 'DWM2t player'
                    or type(dialog.get('hwnd')) is not int or dialog['hwnd'] <= 0
                    or not isinstance(attempts, list) or len(attempts) != 1
                    or not isinstance(attempts[0], dict)
                    or attempts[0].get('message') != 'WM_CLOSE'
                    or attempts[0].get('hwnd') != dialog['hwnd']
                    or attempts[0].get('delivered') is not True):
                raise ValueError('Production rejection dialog or exit evidence is incomplete: '+label)
            stderr = (path.parent/(label+'.stderr.log')).read_text(encoding='utf-8', errors='replace')
            if reason not in stderr.lower():
                raise ValueError('Production rejection stderr lacks the original refusal: '+label)
    pairs = report.get('window_pairs')
    if (not isinstance(pairs, list) or len(pairs) != 2
            or [item.get('round') for item in pairs if isinstance(item, dict)] != ['continue', 'reload']
            or any(type(item.get('pid')) is not int or item['pid'] <= 0 for item in pairs)
            or pairs[0]['pid'] == pairs[1]['pid']):
        raise ValueError('Fresh reload must use a separate actual production process')
    for pair in pairs:
        windows = pair.get('windows')
        if (not isinstance(windows, list) or len(windows) != 2
                or any(not isinstance(item, dict) or item.get('pid') != pair['pid']
                       or item.get('kind') != 'DWM2tRecompWindow'
                       or type(item.get('hwnd')) is not int or item['hwnd'] <= 0 for item in windows)
                or windows[0]['hwnd'] == windows[1]['hwnd']
                or any(sum(f' - Player {player} (local link)' in str(item.get('title', ''))
                           for item in windows) != 1 for player in (1, 2))):
            raise ValueError('Two distinct original player windows are required per process')
    events = report.get('input_events')
    if (not isinstance(events, list) or not events
            or any(not isinstance(item, dict) or item.get('player') not in (1, 2)
                   or item.get('hwnd') != item.get('foreground_hwnd') for item in events)):
        raise ValueError('Actual focused input events for both original players are required')
    for pair in pairs:
        for player in (1, 2):
            window = next(item for item in pair['windows']
                          if f' - Player {player} (local link)' in item['title'])
            if not any(item['player'] == player and item.get('hwnd') == window['hwnd'] for item in events):
                raise ValueError('Both fresh-process players must receive their own focused inputs')
    initial = ending.read_bytes()
    if len(initial) != 32768 or digest(ending) != ending_sha:
        raise ValueError('Local-link input is not the actual original campaign ending')
    if report.get('original_owned_creatures') != sum(initial[i*165] in (1, 2) for i in range(40)):
        raise ValueError('Local-link report did not preserve the original owned roster')
    journals = report.get('saved_journals')
    if not isinstance(journals, dict) or set(journals) != {'continue', 'reload'}:
        raise ValueError('Both two-player normal-close rounds must retain Journal identities')
    for entries in journals.values():
        if (not isinstance(entries, list) or len(entries) != 2
                or any(not isinstance(item, dict) for item in entries)
                or [item.get('player') for item in entries] != [1, 2]
                or any(item.get('bytes') != 32768
                       or item.get('original_roster_and_107_quest_bytes_preserved') is not True
                       or re.fullmatch(r'[0-9a-f]{64}', str(item.get('sha256', ''))) is None for item in entries)):
            raise ValueError('Original two-player persistence observations are incomplete')
    saves = [one(path.parent, f'ending-player{player}.sav') for player in (1, 2)]
    if os.path.samefile(*saves):
        raise ValueError('Both production players must use separate original Journal files')
    for save, item in zip(saves, journals['reload'], strict=True):
        verify_saved_roster(initial, save.read_bytes())
        if digest(save) != item['sha256']:
            raise ValueError('Actual fresh-process production Journal differs from its report')
    return report


def verify_full_rom_gates(root: Path, source: str, run: str, executable_sha: str,
                          identity: dict, source_archive: Path, candidate: Path, *,
                          ending: Path, ending_sha: str,
                          production_journal_root: Path | None = None,
                          require_alias_rejection: bool = False) -> tuple[dict, dict[str, Path]]:
    """Conditionally extend M8 acceptance for sources with the new serial host."""
    inventory = full_rom_source_inputs(candidate, source_archive, source, identity)
    if inventory is None:
        return {}, {}
    from full_rom_validation import RUNTIME_CORE_TESTS, verify_runtime_core

    inputs, archived = inventory
    fields = {}
    evidence = {}
    counts = {}
    for label, artifact, platform in (
            ('windows', 'production', 'Windows'), ('linux', 'posix-persistence', 'Linux')):
        directory = root/f'M8-fresh-{artifact}-{run}'
        report_path = one(directory, 'runtime-core-validation.json')
        xml_path = report_path.parent/'runtime-core-tests.xml'
        report = verify_runtime_core(report_path, xml_path, source, source_manifest=inputs)
        if report['platform'] != platform or report['tests'] != len(RUNTIME_CORE_TESTS):
            raise ValueError('Runtime-core evidence must use the actual '+platform+' host')
        counts[platform] = report['tests']
        evidence[label+'-runtime-core.json'] = report_path
        evidence[label+'-runtime-core.xml'] = xml_path
    fields['hardware_contract_tests'] = counts
    fields['runtime_core_source_manifest_verified'] = True
    postgame_fields, postgame_evidence = verify_postgame_gate(
        root/f'M8-fresh-postgame-{run}', source, run, identity, inputs, archived,
        ending, ending_sha, Path(__file__).resolve().parents[1]/'tests/m8_postgame_supplemental.json')
    fields.update(postgame_fields)
    evidence.update(postgame_evidence)
    gui = (production_journal_root if production_journal_root is not None
           else root/f'M8-fresh-production-journal-{run}')
    gui_path = one(gui, 'player-local-link.json')
    verify_local_link_gate(gui_path, source, executable_sha,
                           (candidate/'DWM2tRecomp.exe').stat().st_size, ending, ending_sha,
                           require_alias_rejection=require_alias_rejection)
    evidence['production-local-link.json'] = gui_path
    fields.update(local_link_host_verified=True, original_linked_transactions_verified=False,
                  full_postgame_verified=False, all_random_seeds_verified=False,
                  tara_version_verified=False)
    # Keep raw source bytes outside the candidate until every gate passes.
    # package_run copies these together with the other evidence before cleanup.
    scratch = candidate.parent/'full-rom-evidence'
    scratch.mkdir()
    for name, data in (('full-rom-source-manifest.json', (candidate/'source-manifest.json').read_bytes()),
                       ('postgame-manifest.json', archived[POSTGAME_MANIFEST]),
                       ('postgame-replay-manifest.json', _newline_variants(archived[POSTGAME_MANIFEST])[
                           fields['postgame_replayed_manifest_sha256']])):
        path = scratch/name
        path.write_bytes(data)
        evidence[name] = path
    return fields, evidence


def package_run(root: Path, source: str, run: str, output: Path, *,
                native_retest: Path | None = None,
                validation_run_id: str | None = None,
                production_journal_root: Path | None = None,
                production_journal_attestation: Path | None = None) -> Path:
    if not re.fullmatch(r'[0-9a-f]{40}', source) or not run.isdigit():
        raise ValueError('Exact source and native validation run ID are required')
    if (native_retest is None) != (validation_run_id is None):
        raise ValueError('--native-retest and --validation-run-id must be supplied together')
    split_gui = production_journal_root is not None or production_journal_attestation is not None
    if split_gui and (production_journal_root is None or production_journal_attestation is None
                      or native_retest is None or validation_run_id is None):
        raise ValueError('Separate production Journal evidence requires its attestation and native retest/run')
    if output.exists():
        raise ValueError('Verified output must be a new directory')
    diagnostic = root/f'M8-fresh-diagnostic-{run}'
    production = root/f'M8-fresh-production-{run}'
    story = root/f'M8-fresh-story-{run}'
    original_gui = root/f'M8-fresh-production-journal-{run}'
    gui = original_gui
    if split_gui:
        gui = production_journal_root.resolve(strict=True)
        original_gui = original_gui.resolve(strict=False)
        attestation_path = production_journal_attestation.resolve(strict=True)
        if (not gui.is_dir() or gui == original_gui or original_gui in gui.parents
                or gui in original_gui.parents or original_gui in attestation_path.parents):
            raise ValueError('Separate GUI evidence must not replace or reuse the original run artifact')
    posix = root/f'M8-fresh-posix-persistence-{run}'
    identity_path = one(diagnostic, 'build-identity.json')
    identity = load_identity(identity_path)
    if identity.source != source:
        raise ValueError('Diagnostic build source differs')
    diagnostic_exe = one(diagnostic, 'DWM2tRecompFull.exe')
    identity.verify(diagnostic_exe)
    production_report = one(production, 'build-report.json')
    built = json.loads(production_report.read_text(encoding='utf-8'))
    if built.get('status') != 'built_untested' or built.get('source_commit') != source:
        raise ValueError('Independent production build is missing')
    executable = built['executable_sha256']
    archive = one(production, 'DWM2t-M8-UNTESTED-*.zip')
    if digest(archive) != built['zip_sha256']:
        raise ValueError('The actual production archive differs from its build report')
    source_archives = [one(folder, 'source.tar') for folder in (diagnostic, production)]
    source_sha = digest(source_archives[0])
    identity_data = json.loads(identity_path.read_text(encoding='utf-8'))
    if (digest(source_archives[1]) != source_sha or built['source_archive_sha256'] != source_sha
            or identity_data['source_archive_sha256'] != source_sha):
        raise ValueError('Diagnostic and production did not use identical committed sources')
    evidence = {'diagnostic-identity.json': identity_path,
                'production-build.json': production_report,
                'native-tests.xml': one(diagnostic, 'native-results.xml'),
                'windows-save-io.xml': one(production, 'save-io.xml'),
                'posix-save-io.xml': one(posix, 'save-io.xml')}
    retest_provenance = None
    if native_retest is not None:
        if split_gui:
            native_suite_names(evidence['native-tests.xml'], passing=True)
        retest_provenance, retest_evidence = verify_native_retest(
            native_retest, source, run, validation_run_id, diagnostic_exe,
            source_archives[0], evidence['native-tests.xml'])
        evidence.update(retest_evidence)
    tests = passed_ctest(evidence['native-tests.xml'], 18)
    passed_ctest(evidence['windows-save-io.xml'], 2)
    passed_ctest(evidence['posix-save-io.xml'], 2)
    for name in ('pirate', 'village', 'farm-dancer', 'party-preparation'):
        path = one(diagnostic, name+'-validation.json')
        passed_json(path, source, identity.sha256)
        evidence[name+'.json'] = path
    story_path = one(story, 'story-checkpoints-validation.json')
    campaign = passed_json(story_path, source, identity.sha256)
    manifest_path = Path(__file__).resolve().parents[1]/'tests/m8_sea_story_checkpoints.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if len(campaign['stages']) != len(manifest['stages']) or campaign.get('ending_completed') is not True:
        raise ValueError('The full original campaign and ending have not passed')
    if (campaign.get('workers', 1) not in range(1, 5)
            or campaign.get('seed_chain_audited') is not True
            or campaign.get('seed_chain_links') != len(manifest['stages'])):
        raise ValueError('The actual replayed parent/input Journal chain has not been audited')
    for actual, expected in zip(campaign['stages'], manifest['stages'], strict=True):
        route = manifest_path.parent/expected['route']
        if (actual.get('status') != 'passed' or actual.get('native_returncode') != 0
                or actual['stage'] != expected['name'] or actual['frames'] != expected['frames']
                or actual['save_sha256'] != expected['save_sha256']
                or actual['route_sha256'] != expected['route_sha256']
                or digest(route) != expected['route_sha256']):
            raise ValueError('Original campaign evidence differs: '+expected['name'])
        verify_ending_witnesses(route, expected)
    ending = manifest['stages'][-1]
    if ending.get('ending_complete') is not True or campaign['stages'][-1].get('ending_completed') is not True:
        raise ValueError('Final checkpoint is not the complete original ending')
    evidence.update({'campaign-result.json': story_path, 'campaign-manifest.json': manifest_path})
    gui_attestation = None
    if split_gui:
        with zipfile.ZipFile(archive) as zipped:
            executables = [item for item in zipped.infolist()
                           if item.filename == 'DWM2t-M8-UNTESTED/DWM2tRecomp.exe']
        if len(executables) != 1 or executables[0].is_dir() or executables[0].file_size <= 0:
            raise ValueError('The original production archive must contain exactly one player executable')
        late_stage = next(stage for stage in manifest['stages'] if stage['name'] == 'raygigas-birth')
        gui_attestation, gui_evidence = verify_production_journal_attestation(
            attestation_path, gui, source=source, build_run=run, validation_run=validation_run_id,
            retest=retest_provenance, executable_sha=executable, executable_bytes=executables[0].file_size,
            source_archive=source_archives[1],
            ending=story_path.parent/'ending-complete/native/checkpoint.sav',
            ending_sha=ending['save_sha256'],
            late=story_path.parent/'raygigas-birth/native/checkpoint.sav',
            late_sha=late_stage['save_sha256'])
        evidence.update(gui_evidence)
    for label, folder, no_arguments in [('direct-start', 'direct-start', True), ('profile-start', 'profile-start', False)]:
        path = one(production/folder, 'player-startup.json')
        report = passed_json(path, source, executable)
        if len(report['checks']) < 12 or report['no_argument_start'] is not no_arguments:
            raise ValueError('Production startup gate is incomplete')
        evidence[label+'.json'] = path
    package_path = one(gui, 'player-package.json')
    package_report = passed_json(package_path, source, executable)
    if len(package_report['checks']) < 21:
        raise ValueError('Production package checks are incomplete')
    if split_gui:
        verify_split_gui_package_gate(package_report, late_stage['save_sha256'])
    evidence['player-package.json'] = package_path
    for label, folder, seed, owned in [
            ('late-journal', 'production-journal', next(s['save_sha256'] for s in manifest['stages'] if s['name']=='raygigas-birth'), 12),
            ('ending-journal', 'production-ending-journal', ending['save_sha256'], len(ending['owned']))]:
        path = one(gui/folder, 'player-late-journal.json')
        report = passed_json(path, source, executable)
        if (report.get('input_journal_sha256') != seed or report.get('quest_bytes') != 107
                or report.get('original_owned_creatures') != owned
                or report.get('fresh_process_reload') is not True
                or report.get('normal_shutdowns') != 2 or report.get('original_p1_only') is not True):
            raise ValueError('Production original Journal/Continue gate is incomplete: '+label)
        evidence[label+'.json'] = path
    output.mkdir(parents=True)
    temporary = output/'candidate'
    temporary.mkdir()
    with zipfile.ZipFile(archive) as zipped:
        for item in zipped.infolist():
            parts = PurePosixPath(item.filename).parts
            if (not parts or parts[0] != 'DWM2t-M8-UNTESTED' or '..' in parts
                    or '\\' in item.filename or ':' in item.filename or item.filename.startswith('/')):
                raise ValueError('Unsupported production archive member')
        zipped.extractall(temporary)
    candidate = temporary/'DWM2t-M8-UNTESTED'
    metadata = verify_package(candidate, source)
    if metadata['status'] != 'UNTESTED_CANDIDATE' or metadata['files']['DWM2tRecomp.exe'] != executable:
        raise ValueError('The tested candidate identity differs')
    if package_report['package_manifest_sha256'] != digest(candidate/'manifest.json'):
        raise ValueError('Package integration tested another manifest')
    full_rom_fields, full_rom_evidence = verify_full_rom_gates(
        root, source, run, executable, dict(identity_data, build_identity_sha256=digest(identity_path)),
        source_archives[0], candidate, ending=story_path.parent/'ending-complete/native/checkpoint.sav',
        ending_sha=ending['save_sha256'], production_journal_root=gui if split_gui else None,
        require_alias_rejection=split_gui)
    if split_gui and not full_rom_fields:
        raise ValueError('Separate production GUI evidence requires the complete full-ROM gates')
    evidence.update(full_rom_evidence)
    package = output/'DWM2t-M8'
    candidate.rename(package)
    records = package/'validation'
    records.mkdir()
    for name, path in evidence.items():
        shutil.copyfile(path, records/name)
    if full_rom_fields:
        shutil.rmtree(temporary/'full-rom-evidence')
    temporary.rmdir()
    record = dict(schema=1, status='passed', full_game_verified=True, source_commit=source,
                  executable_sha256=executable, diagnostic_sha256=identity.sha256,
                  source_archive_sha256=source_sha, native_run_id=run,
                  native_run_url=f'https://github.com/rjtvandenhout/DWM2t/actions/runs/{run}',
                  campaign='Original main story through Darck, MagicPlug, complete credits and THE END',
                  story_checkpoints=len(campaign['stages']), retained_native_tests=tests,
                  story_workers=campaign.get('workers', 1), seed_chain_audited=True,
                  seed_chain_links=campaign['seed_chain_links'],
                  original_journal_bundle_sha256=campaign.get('seed_bundle_sha256'),
                  ending_journal_sha256=ending['save_sha256'],
                  limitations=['CI does not establish audible playback on the user\'s physical audio hardware.'],
                  created_utc=datetime.now(timezone.utc).isoformat(),
                  evidence={name:digest(records/name) for name in evidence})
    record.update(full_rom_fields)
    if full_rom_fields:
        record['limitations'].extend(FULL_ROM_LIMITATIONS)
    if retest_provenance is not None:
        record.update(build_run_id=run, story_run_id=run,
                      build_run_url=f'https://github.com/rjtvandenhout/DWM2t/actions/runs/{run}',
                      story_run_url=f'https://github.com/rjtvandenhout/DWM2t/actions/runs/{run}',
                      validation_run_id=validation_run_id, native_run_id=validation_run_id,
                      native_run_url=f'https://github.com/rjtvandenhout/DWM2t/actions/runs/{validation_run_id}',
                      packaging_source_commit=retest_provenance['packaging_source_commit'],
                      native_suite_source=source, native_suite_retest=True,
                      initial_native_tests_status='passed' if split_gui else 'unaccepted',
                      initial_native_tests_sha256=retest_provenance['original_native_tests_sha256'],
                      accepted_native_tests_sha256=retest_provenance['retest_native_tests_sha256'])
    if gui_attestation is not None:
        record.update(production_journal_validation_run_id=validation_run_id,
                      production_journal_validation_url=
                          f'https://github.com/rjtvandenhout/DWM2t/actions/runs/{validation_run_id}',
                      production_journal_tooling_source_commit=gui_attestation['tooling_source_commit'],
                      production_journal_attestation_sha256=digest(attestation_path),
                      original_artifact_manifest_sha256=gui_attestation['original_artifact_manifest_sha256'])
    (package/'validation.json').write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8')
    readme = (package/'README.txt').read_text(encoding='utf-8')
    start = readme.index('START\n')
    readme = ('DWM2t - Native Windows x64 player\nM8 VALIDATED MAIN CAMPAIGN\n\n'
              'This exact executable passed the original main story through the ending and\n'
              'complete credits, retained native tests, and production package/save checks.\n'
              'validation.json binds this player to its exact source and raw Windows evidence.\n'
              'It does not certify every optional route or physical audio device.\n\n'+readme[start:])
    readme = readme.replace('Keep older packages until the new candidate has been tested.', 'Keep older packages and save backups when installing an update.')
    readme = readme.replace('Filesystem/hardware failures and later-game behavior still require testing.', 'The included validation record describes the tested persistence failures and scope.')
    readme = readme.replace('All validation is pending for this candidate. No final M8 restore is asserted.', 'See validation.json and validation/ for the exact tested source and passing evidence.')
    (package/'README.txt').write_text(readme, encoding='utf-8')
    metadata.update(status='VERIFIED_M8', tests='passed', full_game_verified=True, m8_accepted=True,
                    files={name:digest(package/name) for name in (*BASE_FILES, 'validation.json')})
    (package/'manifest.json').write_text(json.dumps(metadata, indent=2)+'\n', encoding='utf-8')
    verify_package(package, source)
    zipped_path = output/f'DWM2t-M8-VERIFIED-{source[:12]}.zip'
    with zipfile.ZipFile(zipped_path, 'x', zipfile.ZIP_DEFLATED, compresslevel=6) as zipped:
        for path in sorted(package.rglob('*')):
            if path.is_file():
                zipped.write(path, path.relative_to(output).as_posix())
    (output/'verified-package.json').write_text(json.dumps(dict(record, zip_sha256=digest(zipped_path),
        manifest_sha256=digest(package/'manifest.json')), indent=2)+'\n', encoding='utf-8')
    return zipped_path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    for name in ('source', 'run-id'):
        parser.add_argument('--'+name, required=True)
    parser.add_argument('--native-retest', type=Path,
                        help='Full native-suite rerun directory; preserves the initial XML as unaccepted')
    parser.add_argument('--validation-run-id',
                        help='Actual continuation workflow run; required with --native-retest')
    parser.add_argument('--production-journal-root', type=Path,
                        help='Separate successful production GUI evidence, never the original failed artifact')
    parser.add_argument('--production-journal-attestation', type=Path,
                        help='Exact-source/tooling attestation for the separate GUI evidence')
    args = parser.parse_args()
    print('M8_VERIFIED_PACKAGE', package_run(args.root, args.source, args.run_id, args.output,
        native_retest=args.native_retest, validation_run_id=args.validation_run_id,
        production_journal_root=args.production_journal_root,
        production_journal_attestation=args.production_journal_attestation))
