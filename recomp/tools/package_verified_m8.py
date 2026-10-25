"""Package the unchanged tested player only after the complete M8 gates pass.

Inputs are artifacts from one fresh validation run. No build, game-state
mutation, executable patch, or public release is performed here.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import xml.etree.ElementTree as ET
import zipfile

from m8_build_identity import digest, load_identity
from m8_package import BASE_FILES, verify_package
from test_m8_story_checkpoints import verify_ending_witnesses


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


def package_run(root: Path, source: str, run: str, output: Path) -> Path:
    if not re.fullmatch(r'[0-9a-f]{40}', source) or not run.isdigit():
        raise ValueError('Exact source and native validation run ID are required')
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
    identity.verify(one(diagnostic, 'DWM2tRecompFull.exe'))
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
    args = parser.parse_args()
    print('M8_VERIFIED_PACKAGE', package_run(args.root, args.source, args.run_id, args.output))
