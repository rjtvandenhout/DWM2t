"""Check complete-AOT package integrity and its external validation record."""
from __future__ import annotations

import json
from pathlib import Path
import re

from m8_build_identity import ROM_SHA, digest

BASE_FILES = ('DWM2tRecomp.exe', 'Launch.ps1', 'Play.cmd', 'README.txt',
              'LICENSE-NOTICE.md', 'source-manifest.json')


def verify_package(package: Path, source: str) -> dict:
    if not re.fullmatch(r'[0-9a-f]{40}', source):
        raise ValueError('Expected exact source commit is required')
    metadata = json.loads((package/'manifest.json').read_text(encoding='utf-8'))
    verified = metadata.get('status') == 'VERIFIED_M8'
    if (metadata.get('schema') != 1 or metadata.get('status') not in
            ('UNTESTED_CANDIDATE', 'VERIFIED_M8')
            or metadata.get('source_commit') != source or metadata.get('rom_sha256') != ROM_SHA
            or metadata.get('fixed_bank') != 0
            or metadata.get('romx_banks') != list(range(1, 256))
            or metadata.get('full_game_verified') is not verified
            or metadata.get('m8_accepted') is not verified):
        raise ValueError('Complete-AOT package metadata differs')
    required = (*BASE_FILES, 'validation.json') if verified else BASE_FILES
    files = metadata.get('files', {})
    if set(files) != set(required):
        raise ValueError('Unexpected package file inventory')
    for name in required:
        if digest(package/name) != files[name]:
            raise ValueError('Packaged file checksum differs: '+name)
    if verified:
        record = json.loads((package/'validation.json').read_text(encoding='utf-8'))
        if (record.get('schema') != 1 or record.get('status') != 'passed'
                or record.get('full_game_verified') is not True
                or record.get('source_commit') != source
                or record.get('executable_sha256') != files['DWM2tRecomp.exe']
                or not record.get('evidence')):
            raise ValueError('Verified package has no matching validation record')
        for name, expected in record['evidence'].items():
            if (not re.fullmatch(r'[A-Za-z0-9_-]+\.(?:json|xml|txt)', name)
                    or not re.fullmatch(r'[0-9a-f]{64}', str(expected))
                    or digest(package/'validation'/name) != expected):
                raise ValueError('Validation evidence differs: '+name)
    return metadata
