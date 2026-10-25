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


def package_run(root: Path, source: str, run: str, output: Path, *,
                native_retest: Path | None = None,
                validation_run_id: str | None = None) -> Path:
    if not re.fullmatch(r'[0-9a-f]{40}', source) or not run.isdigit():
        raise ValueError('Exact source and native validation run ID are required')
    if (native_retest is None) != (validation_run_id is None):
        raise ValueError('--native-retest and --validation-run-id must be supplied together')
    if output.exists():
        raise ValueError('Verified output must be a new directory')
    diagnostic = root/f'M8-fresh-diagnostic-{run}'
    production = root/f'M8-fresh-production-{run}'
    story = root/f'M8-fresh-story-{run}'
    gui = root/f'M8-fresh-production-journal-{run}'
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
    package = output/'DWM2t-M8'
    candidate.rename(package)
    temporary.rmdir()
    records = package/'validation'
    records.mkdir()
    for name, path in evidence.items():
        shutil.copyfile(path, records/name)
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
    if retest_provenance is not None:
        record.update(build_run_id=run, story_run_id=run,
                      build_run_url=f'https://github.com/rjtvandenhout/DWM2t/actions/runs/{run}',
                      story_run_url=f'https://github.com/rjtvandenhout/DWM2t/actions/runs/{run}',
                      validation_run_id=validation_run_id, native_run_id=validation_run_id,
                      native_run_url=f'https://github.com/rjtvandenhout/DWM2t/actions/runs/{validation_run_id}',
                      packaging_source_commit=retest_provenance['packaging_source_commit'],
                      native_suite_source=source, native_suite_retest=True,
                      initial_native_tests_status='unaccepted',
                      initial_native_tests_sha256=retest_provenance['original_native_tests_sha256'],
                      accepted_native_tests_sha256=retest_provenance['retest_native_tests_sha256'])
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
    args = parser.parse_args()
    print('M8_VERIFIED_PACKAGE', package_run(args.root, args.source, args.run_id, args.output,
        native_retest=args.native_retest, validation_run_id=args.validation_run_id))
