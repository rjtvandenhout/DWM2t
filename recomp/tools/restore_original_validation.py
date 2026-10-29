"""Restore and verify successful producers from an earlier Actions run.

This retrieves only original build/campaign artifacts. A failed GUI artifact
is deliberately not reused; the caller must run that gate again separately.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import zipfile


def api(path: str) -> dict:
    result = subprocess.run(['gh', 'api', path], check=True, capture_output=True,
                            text=True, encoding='utf-8')
    return json.loads(result.stdout)


def sha256(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--source', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    args = parser.parse_args()
    repo = os.environ.get('GITHUB_REPOSITORY', '')
    if (not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo)
            or not re.fullmatch(r'[1-9][0-9]*', args.run_id)
            or not re.fullmatch(r'[0-9a-f]{40}', args.source)):
        raise ValueError('Exact repository, original run and game source are required')
    run_path = f'repos/{repo}/actions/runs/{args.run_id}'
    run = api(run_path)
    if (str(run.get('id')) != args.run_id or run.get('head_sha') != args.source
            or run.get('status') != 'completed' or not run.get('conclusion')):
        raise ValueError('Original build run is unfinished or identifies another source')
    jobs_response = api(run_path + '/jobs?per_page=100&filter=latest')
    if jobs_response.get('total_count', 0) > len(jobs_response.get('jobs', [])):
        raise ValueError('Original job list requires pagination')
    jobs = jobs_response['jobs']
    producers = {}
    for name in ('diagnostic', 'production', 'posix-persistence'):
        matches = [job for job in jobs if job.get('name') == name
                   or str(job.get('name', '')).endswith('/ ' + name)]
        if (len(matches) != 1 or matches[0].get('conclusion') != 'success'
                or type(matches[0].get('id')) is not int or matches[0]['id'] <= 0):
            raise ValueError('Original producer is missing or did not pass: ' + name)
        producers[name] = {'id': matches[0]['id'], 'conclusion': 'success'}
    response = api(run_path + '/artifacts?per_page=100')
    if response.get('total_count', 0) > len(response.get('artifacts', [])):
        raise ValueError('Original artifact list requires pagination')
    args.output.mkdir(parents=True, exist_ok=False)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    artifacts = {}
    for kind in ('diagnostic', 'production', 'story', 'postgame', 'posix-persistence'):
        name = f'M8-fresh-{kind}-{args.run_id}'
        matching = [item for item in response['artifacts']
                    if item.get('name') == name and item.get('expired') is False]
        if len(matching) != 1:
            raise ValueError('Expected exactly one unexpired original artifact: ' + name)
        item = matching[0]
        artifact_id, size, expected = item.get('id'), item.get('size_in_bytes'), item.get('digest')
        if (type(artifact_id) is not int or artifact_id <= 0 or type(size) is not int or size <= 0
                or not isinstance(expected, str) or not re.fullmatch(r'sha256:[0-9a-f]{64}', expected)):
            raise ValueError('Original artifact lacks a verified identity: ' + name)
        archive = args.output / (name + '.zip')
        with archive.open('xb') as stream:
            subprocess.run(['gh', 'api', f'repos/{repo}/actions/artifacts/{artifact_id}/zip'],
                           stdout=stream, check=True, timeout=600)
        if archive.stat().st_size != size or 'sha256:' + sha256(archive) != expected:
            raise ValueError('Original artifact ZIP does not match GitHub digest: ' + name)
        destination = args.output / name
        destination.mkdir()
        with zipfile.ZipFile(archive) as zipped:
            names = set()
            for member in zipped.infolist():
                path = PurePosixPath(member.filename)
                mode = member.external_attr >> 16
                if (not member.filename or member.filename.startswith('/') or '\\' in member.filename
                        or ':' in member.filename or '..' in path.parts or stat.S_ISLNK(mode)
                        or member.filename in names):
                    raise ValueError('Unsafe or duplicate original artifact member: ' + member.filename)
                names.add(member.filename)
            zipped.extractall(destination)
        archive.unlink()
        artifacts[kind] = {'id': artifact_id, 'name': name, 'size_bytes': size,
                           'sha256': expected.removeprefix('sha256:')}
        print('ORIGINAL_ARTIFACT_VERIFIED', name, artifact_id, flush=True)
    manifest = {'schema': 1, 'kind': 'original_build_artifacts', 'status': 'passed',
                'build_run_id': args.run_id, 'build_source_commit': args.source,
                'run_conclusion': run['conclusion'], 'producer_jobs': producers,
                'artifacts': artifacts}
    with args.manifest.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(manifest, stream, indent=2)
        stream.write('\n')


if __name__ == '__main__':
    main()
