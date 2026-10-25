"""Identify an isolated complete-AOT build without changing historical pins.

A build identity records provenance, not test acceptance. Callers preserve its
hash alongside the replay report and recheck both identity and executable.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re

HISTORICAL_SOURCE = '697647033b4ce6b00dd8e11759cb85e1ae469a65'
HISTORICAL_SHA = '4a12bd3197b414c888f50c606ccf3cb2ede030543f8058df83e0fcd67359e95d'
ROM_SHA = '8e38a7420ef5239c7196aa4fd4b1499e65db2823e875bbf8241bb2199e766d4e'


def digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


@dataclass(frozen=True)
class BuildIdentity:
    source: str = HISTORICAL_SOURCE
    sha256: str = HISTORICAL_SHA
    size: int = 725318144
    manifest: Path | None = None
    manifest_sha256: str | None = None

    def verify(self, exe: Path) -> None:
        if exe.stat().st_size != self.size or digest(exe) != self.sha256:
            raise ValueError('Expected complete-AOT diagnostic executable differs')
        if self.manifest and digest(self.manifest) != self.manifest_sha256:
            raise ValueError('Build identity changed during validation')

    def report(self) -> dict:
        result = dict(executable_source=self.source, executable_sha256=self.sha256,
                      executable_bytes=self.size)
        if self.manifest:
            result.update(build_identity=str(self.manifest),
                          build_identity_sha256=self.manifest_sha256)
        return result


def load_identity(path: Path | None) -> BuildIdentity:
    if path is None:
        return BuildIdentity()
    path = path.resolve(strict=True)
    before = digest(path)
    data = json.loads(path.read_text(encoding='utf-8'))
    hashes = ('executable_sha256', 'source_archive_sha256', 'source_manifest_sha256')
    if (data.get('schema') != 1 or data.get('kind') != 'complete_aot_diagnostic_build'
            or data.get('build_testing') is not True or data.get('fixed_bank') != 0
            or data.get('romx_banks') != list(range(1, 256))
            or data.get('rom_sha256') != ROM_SHA
            or not re.fullmatch(r'[0-9a-f]{40}', str(data.get('source_commit', '')))
            or any(not re.fullmatch(r'[0-9a-f]{64}', str(data.get(key, ''))) for key in hashes)
            or type(data.get('executable_bytes')) is not int
            or data['executable_bytes'] <= 0):
        raise ValueError('Incomplete complete-AOT diagnostic build identity')
    return BuildIdentity(data['source_commit'], data['executable_sha256'],
                         data['executable_bytes'], path, before)
