"""Download only the exact accepted diagnostic/story inputs for a supplement.

The token is read from GH_TOKEN, sent only to api.github.com, never logged or
forwarded to the signed artifact redirect. No repository/Actions writes occur.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request
import zipfile

REPO = 'rjtvandenhout/DWM2t'
BUILD_RUN = 40175408153
SOURCE = '3d573873ae8122cbb10fcd5d0f7ae7a33a7609ba'
ACCEPTED_RUN = 40183484388
ACCEPTED_TOOL_SOURCE = '8859ef67289ce90712a44b9c17174de4519a59b3'
PINS = {
    'diagnostic': {'id': 12594525715, 'name': 'M8-fresh-diagnostic-40175408153',
                   'bytes': 139241574,
                   'sha256': '9690048b14418b0ba5a944f7422f4c100eaa30eb42c3b4692b774e6ad81a5980'},
    'story': {'id': 12594545489, 'name': 'M8-fresh-story-40175408153',
              'bytes': 2625793,
              'sha256': '2734ea5d13be5ce3d938199c4cc8bb7c86604aa275154c7fd80c71aaf1706117'},
}
EXE_SHA = 'f93b7f96212559f65f05e09f8443a224bbda7d124047047fbf53510e16ae0321'
EXE_BYTES = 725575680
ENDING_SHA = '0649c4ef78867d2e55f352ddb0fea811fea6e3cf7407f8451220cc2bf01df95d'
SOURCE_ARCHIVE_SHA = 'c75ba57b296c1b2038cd5cc3789059eb4513f79831d64cfb6f4b855a22d72722'
SOURCE_MANIFEST_SHA = '462752ad7e2fa0e658486cc5524106bb1f121a353d279418dd5cfa75d230ba99'


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, url):
        return None


class GitHubReadOnly:
    def __init__(self, token: str):
        if not token:
            raise ValueError('GH_TOKEN is required for the private accepted artifacts')
        self.token = token
        self.opener = urllib.request.build_opener(NoRedirect)

    def open_api(self, suffix: str):
        request = urllib.request.Request('https://api.github.com/repos/'+REPO+'/'+suffix,
            headers={'Authorization': 'Bearer '+self.token,
                     'Accept': 'application/vnd.github+json',
                     'X-GitHub-Api-Version': '2022-11-28',
                     'User-Agent': 'DWM2t-exact-postgame-supplement'})
        return self.opener.open(request, timeout=120)

    def get(self, suffix: str):
        with self.open_api(suffix) as response:
            return json.load(response)

    def download(self, artifact_id: int, target: Path, pin: dict) -> dict:
        try:
            response = self.open_api(f'actions/artifacts/{artifact_id}/zip')
        except urllib.error.HTTPError as error:
            if error.code != 302:
                raise
            location = error.headers.get('Location', '')
            error.close()
            parsed = urllib.parse.urlsplit(location)
            if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
                raise ValueError('Expected HTTPS signed artifact redirect')
            # Deliberately start a separate unauthenticated request. Do not use
            # the authenticated Request or opener for the signed blob location.
            response = urllib.request.urlopen(location, timeout=120)
        sha, size = hashlib.sha256(), 0
        with response, target.open('xb') as destination:
            while chunk := response.read(1024*1024):
                size += len(chunk)
                if size > pin['bytes']:
                    raise ValueError('Artifact ZIP exceeds exact pinned byte size')
                sha.update(chunk)
                destination.write(chunk)
        if size != pin['bytes'] or sha.hexdigest() != pin['sha256']:
            raise ValueError('Downloaded original Actions ZIP differs from the accepted pin')
        return {'bytes': size, 'sha256': sha.hexdigest(), 'raw_zip': str(target)}


def zip_member(archive: zipfile.ZipFile, name: str, expected_sha: str | None = None,
               expected_bytes: int | None = None, target: Path | None = None) -> dict:
    if archive.namelist().count(name) != 1:
        raise ValueError('Missing or duplicate exact accepted artifact member: '+name)
    entry = archive.getinfo(name)
    if entry.is_dir() or (expected_bytes is not None and entry.file_size != expected_bytes):
        raise ValueError('Accepted artifact member size/type differs: '+name)
    sha, size = hashlib.sha256(), 0
    output = target.open('xb') if target else None
    try:
        with archive.open(entry) as stream:
            while chunk := stream.read(1024*1024):
                sha.update(chunk)
                size += len(chunk)
                if output:
                    output.write(chunk)
    finally:
        if output:
            output.close()
    if expected_sha is not None and sha.hexdigest() != expected_sha:
        raise ValueError('Accepted artifact member hash differs: '+name)
    return {'member': name, 'bytes': size, 'sha256': sha.hexdigest()}


def extract_pinned(diagnostic_zip: Path, story_zip: Path, output: Path) -> list[dict]:
    """Extract only exact named inputs; preserve raw ZIPs separately."""
    members = []
    with zipfile.ZipFile(diagnostic_zip) as archive:
        members.append(zip_member(archive, 'diagnostic-output/DWM2tRecompFull.exe',
                                 EXE_SHA, EXE_BYTES, output/'DWM2tRecompFull.exe'))
        members.append(zip_member(archive, 'diagnostic-output/build-identity.json',
                                 target=output/'build-identity.json'))
        members.append(zip_member(archive, 'diagnostic-output/source-manifest.json',
                                 SOURCE_MANIFEST_SHA))
        members.append(zip_member(archive, 'diagnostic-work/source.tar',
                                 SOURCE_ARCHIVE_SHA, 27443200))
    identity = json.loads((output/'build-identity.json').read_text(encoding='utf-8'))
    required = {'schema': 1, 'kind': 'complete_aot_diagnostic_build', 'build_testing': True,
                'source_commit': SOURCE, 'executable_sha256': EXE_SHA,
                'executable_bytes': EXE_BYTES, 'source_archive_sha256': SOURCE_ARCHIVE_SHA,
                'source_manifest_sha256': SOURCE_MANIFEST_SHA, 'fixed_bank': 0,
                'romx_banks': list(range(1, 256)),
                'rom_sha256': '8e38a7420ef5239c7196aa4fd4b1499e65db2823e875bbf8241bb2199e766d4e'}
    if any(identity.get(key) != value for key, value in required.items()):
        raise ValueError('Accepted original complete-AOT diagnostic build identity differs')
    with zipfile.ZipFile(story_zip) as archive:
        members.append(zip_member(archive, 'ending-complete/native/checkpoint.sav',
                                 ENDING_SHA, 32768, output/'ending-complete.sav'))
    return members


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ('producer-run-id', 'diagnostic-artifact-id', 'story-artifact-id'):
        parser.add_argument('--'+flag, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    report = {'schema': 1, 'status': 'running', 'repository': REPO,
              'build_run_id': str(BUILD_RUN), 'game_source_commit': SOURCE,
              'accepted_baseline_validation_run_id': str(ACCEPTED_RUN),
              'supplemental_validation_run_id': os.environ.get('GITHUB_RUN_ID'),
              'tooling_source_commit': os.environ.get('GITHUB_SHA'), 'artifacts': []}
    try:
        ids = (args.producer_run_id, args.diagnostic_artifact_id, args.story_artifact_id)
        if ids != (str(BUILD_RUN), str(PINS['diagnostic']['id']), str(PINS['story']['id'])):
            raise ValueError('Explicit producer/artifact IDs must equal the exact accepted set')
        api = GitHubReadOnly(os.environ.get('GH_TOKEN', ''))
        original = api.get(f'actions/runs/{BUILD_RUN}')
        accepted = api.get(f'actions/runs/{ACCEPTED_RUN}')
        if original['head_sha'] != SOURCE or original['status'] != 'completed':
            raise ValueError('Original build run/source differs or is incomplete')
        if (accepted['head_sha'] != ACCEPTED_TOOL_SOURCE or accepted['status'] != 'completed'
                or accepted['conclusion'] != 'success'):
            raise ValueError('Accepted baseline final validation provenance differs')
        report.update(original_build_run_conclusion=original['conclusion'],
                      accepted_baseline_tool_source=ACCEPTED_TOOL_SOURCE,
                      accepted_baseline_conclusion=accepted['conclusion'])
        jobs, page = [], 1
        while True:
            batch = api.get(f'actions/runs/{BUILD_RUN}/jobs?filter=latest&per_page=100&page={page}')['jobs']
            jobs.extend(batch)
            if len(batch) < 100:
                break
            page += 1
        report['producer_jobs'] = []
        for name in ('diagnostic', 'production', 'production-journal', 'posix-persistence'):
            matching = [job for job in jobs if job['name'] == name or job['name'].endswith('/ '+name)]
            if len(matching) != 1 or matching[0]['conclusion'] != 'success':
                raise ValueError('Exact original producer did not succeed: '+name)
            report['producer_jobs'].append({key: matching[0][key] for key in ('id', 'name', 'conclusion')})
        archives = {}
        for kind, pin in PINS.items():
            meta = api.get(f"actions/artifacts/{pin['id']}")
            if (meta['name'] != pin['name'] or meta['size_in_bytes'] != pin['bytes']
                    or meta.get('digest') != 'sha256:'+pin['sha256'] or meta['expired']
                    or meta['workflow_run']['id'] != BUILD_RUN
                    or meta['workflow_run']['head_sha'] != SOURCE):
                raise ValueError('Original artifact API metadata differs: '+kind)
            target = out/(kind+'-actions.zip')
            download = api.download(pin['id'], target, pin)
            archives[kind] = target
            report['artifacts'].append(dict(pin, kind=kind, expired=False,
                created_at=meta['created_at'], expires_at=meta['expires_at'], download=download))
        report['members'] = extract_pinned(archives['diagnostic'], archives['story'], out)
        report['status'] = 'passed'
        print('POSTGAME_ACCEPTED_INPUTS_READY exact_original_artifact_ZIPs EXE source ending_Journal')
        return 0
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as error:
        # Do not print URLs, redirects, headers, requests, or token-bearing state.
        report.update(status='failed', error_type=type(error).__name__, error=str(error))
        print('POSTGAME_ACCEPTED_INPUTS_FAIL', type(error).__name__)
        return 1
    finally:
        with (out/'accepted-input-artifacts.json').open('x', encoding='utf-8') as stream:
            json.dump(report, stream, indent=2)
            stream.write('\n')


if __name__ == '__main__':
    raise SystemExit(main())
