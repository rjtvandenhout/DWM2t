"""Bind fresh Windows GUI observations to an unchanged original build."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess


def digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('build-run-id', 'build-source'):
        parser.add_argument('--' + name, required=True)
    for name in ('gui-root', 'exe', 'source-archive', 'ending-seed', 'late-seed', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[2]
    validation_run = os.environ.get('GITHUB_RUN_ID', '')
    tooling = os.environ.get('GITHUB_SHA', '')
    head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=repo, check=True,
                          capture_output=True, text=True).stdout.strip()
    if (not re.fullmatch(r'[1-9][0-9]*', args.build_run_id)
            or not re.fullmatch(r'[1-9][0-9]*', validation_run)
            or validation_run == args.build_run_id
            or not re.fullmatch(r'[0-9a-f]{40}', args.build_source)
            or not re.fullmatch(r'[0-9a-f]{40}', tooling) or head != tooling
            or os.name != 'nt'):
        raise ValueError('Fresh native Windows run and exact source identities required')
    manifest = args.gui_root / 'original-artifact-manifest.json'
    original = json.loads(manifest.read_text(encoding='utf-8'))
    if (original.get('status') != 'passed' or original.get('build_run_id') != args.build_run_id
            or original.get('build_source_commit') != args.build_source):
        raise ValueError('Original artifact receipt identifies a different build')
    scripts = ('recomp/tools/test_player_local_link.py', 'recomp/tools/test_player_late_journal.py',
               'recomp/tools/test_player_package.py', 'recomp/tools/prepare_m8_player_validation.py',
               'recomp/tools/package_verified_m8.py', 'recomp/tools/restore_original_validation.py',
               'recomp/tools/attest_revalidated_gui.py', 'recomp/tools/prepare_m8_native_retest.py',
               'recomp/tools/setup_windows_ci_audio.ps1', '.github/workflows/recomp-resume-verified.yml',
               '.github/workflows/recomp-player-validation.yml')
    reports = ('production-local-link/player-local-link.json', 'player-package/player-package.json',
               'production-journal/player-late-journal.json',
               'production-ending-journal/player-late-journal.json')
    for relative in reports:
        report = json.loads((args.gui_root / relative).read_text(encoding='utf-8'))
        if (report.get('status') != 'passed' or report.get('platform') != 'Windows'
                or report.get('source') != args.build_source
                or report.get('executable_sha256') != digest(args.exe)):
            raise ValueError('Fresh GUI gate did not pass on the original player: ' + relative)
    if args.ending_seed.stat().st_size != 32768 or args.late_seed.stat().st_size != 32768:
        raise ValueError('Both original Journal seeds must be 32 KiB')
    rejection_logs = ('production-local-link/same-file-alias.stderr.log',
                      'production-local-link/competing-player2.stderr.log')
    record = {'schema': 1, 'kind': 'production_journal_revalidation', 'status': 'passed',
              'platform': 'Windows', 'build_run_id': args.build_run_id,
              'build_source_commit': args.build_source, 'validation_run_id': validation_run,
              'tooling_source_commit': tooling, 'production_executable_sha256': digest(args.exe),
              'production_executable_bytes': args.exe.stat().st_size,
              'source_archive_sha256': digest(args.source_archive),
              'ending_journal_sha256': digest(args.ending_seed),
              'late_journal_sha256': digest(args.late_seed),
              'original_artifact_manifest_sha256': digest(manifest),
              'scripts': {name: digest(repo / name) for name in scripts},
              'reports': {name: digest(args.gui_root / name) for name in (*reports, *rejection_logs)}}
    with args.output.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(record, stream, indent=2)
        stream.write('\n')
    print('PRODUCTION_GUI_ATTESTED', validation_run, tooling, flush=True)


if __name__ == '__main__':
    main()
