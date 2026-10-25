"""Check an intact fresh package and derive a GUI spec without changing fixtures."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

from m8_build_identity import digest
from m8_package import verify_package


def prepare(package: Path, source: str, reference: Path, output: Path) -> dict:
    if not re.fullmatch(r'[0-9a-f]{40}', source):
        raise ValueError('Expected exact source commit is required')
    metadata = verify_package(package, source)
    files = metadata['files']
    spec = json.loads(reference.read_text(encoding='utf-8'))
    spec.update(source=source, executable_sha256=files['DWM2tRecomp.exe'],
                package_manifest_sha256=digest(package/'manifest.json'),
                historical_gui_spec_sha256=digest(reference))
    for key, expected in zip(('field_reference', 'menu_reference'), spec['reference_sha256'], strict=True):
        path = (reference.parent/spec[key]).resolve(strict=True)
        if digest(path) != expected:
            raise ValueError('Historical original framebuffer reference differs')
        spec[key] = str(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(spec, indent=2)+'\n')
    return spec


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('package', 'reference', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--source', required=True)
    args = parser.parse_args()
    prepare(args.package.resolve(strict=True), args.source,
            args.reference.resolve(strict=True), args.output.resolve())
    print('M8_FRESH_PACKAGE_IDENTITY_PASS GUI_validation_not_run')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
