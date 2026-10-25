"""Build provenance contracts only; synthetic files are never executed."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from m8_build_identity import (HISTORICAL_SHA, HISTORICAL_SOURCE, ROM_SHA,
                               digest, load_identity)
from prepare_m8_player_validation import prepare


class BuildIdentityContracts(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.exe = self.root/'synthetic-never-executed.exe'
        self.exe.write_bytes(b'Build identity contract fixture; never execute')
        self.path = self.root/'build-identity.json'
        self.data = dict(schema=1, kind='complete_aot_diagnostic_build',
                         build_testing=True, fixed_bank=0, romx_banks=list(range(1, 256)),
                         rom_sha256=ROM_SHA, source_commit='1'*40,
                         executable_sha256=digest(self.exe), executable_bytes=self.exe.stat().st_size,
                         source_archive_sha256='2'*64, source_manifest_sha256='3'*64)
        self.write()

    def write(self):
        self.path.write_text(json.dumps(self.data), encoding='utf-8')

    def test_historical_default_is_unchanged(self):
        identity = load_identity(None)
        self.assertEqual(identity.sha256, HISTORICAL_SHA)
        self.assertEqual(identity.source, HISTORICAL_SOURCE)
        self.assertEqual(identity.size, 725318144)

    def test_fresh_identity_records_actual_provenance(self):
        identity = load_identity(self.path)
        identity.verify(self.exe)
        report = identity.report()
        self.assertEqual(report['executable_source'], self.data['source_commit'])
        self.assertEqual(report['build_identity_sha256'], digest(self.path))
        self.assertNotIn('full_game_verified', report)

    def test_incomplete_or_wrong_build_is_rejected(self):
        for key, value in [('schema', 2), ('kind', 'production'), ('build_testing', False),
                           ('fixed_bank', 1), ('romx_banks', list(range(1, 255))),
                           ('rom_sha256', '0'*64), ('source_commit', 'short'),
                           ('executable_sha256', 'bad'), ('source_archive_sha256', ''),
                           ('source_manifest_sha256', None), ('executable_bytes', True),
                           ('executable_bytes', 0)]:
            with self.subTest(key=key):
                original = self.data[key]
                self.data[key] = value
                self.write()
                with self.assertRaises(ValueError):
                    load_identity(self.path)
                self.data[key] = original

    def test_same_length_executable_mutation_is_rejected(self):
        identity = load_identity(self.path)
        data = self.exe.read_bytes()
        self.exe.write_bytes(b'!'+data[1:])
        with self.assertRaises(ValueError):
            identity.verify(self.exe)

    def test_wrong_executable_length_is_rejected(self):
        identity = load_identity(self.path)
        self.exe.write_bytes(self.exe.read_bytes()+b'!')
        with self.assertRaises(ValueError):
            identity.verify(self.exe)

    def test_identity_mutation_during_run_is_rejected(self):
        identity = load_identity(self.path)
        self.data['source_commit'] = '4'*40
        self.write()
        with self.assertRaises(ValueError):
            identity.verify(self.exe)


class PackageIdentityContracts(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.package = self.root/'synthetic package'
        self.package.mkdir()
        names = ('DWM2tRecomp.exe', 'Launch.ps1', 'Play.cmd', 'README.txt',
                 'LICENSE-NOTICE.md', 'source-manifest.json')
        for name in names:
            (self.package/name).write_bytes(b'Never executed contract fixture: '+name.encode())
        metadata = dict(schema=1, status='UNTESTED_CANDIDATE', source_commit='1'*40,
                        rom_sha256=ROM_SHA, fixed_bank=0, romx_banks=list(range(1, 256)),
                        files={name: digest(self.package/name) for name in names})
        (self.package/'manifest.json').write_text(json.dumps(metadata), encoding='utf-8')
        for name in ('field', 'menu'):
            (self.root/name).write_bytes(b'Never rendered image contract fixture: '+name.encode())
        self.reference = self.root/'historical-gui.json'
        self.reference.write_text(json.dumps(dict(source='2'*40, executable_sha256='3'*64,
            seed_sha256='4'*64, field_reference='field', menu_reference='menu',
            reference_sha256=[digest(self.root/name) for name in ('field', 'menu')])), encoding='utf-8')
        self.output = self.root/'derived.json'

    def test_derivation_keeps_package_and_historical_spec_unchanged(self):
        before = {path: digest(path) for path in self.root.rglob('*') if path.is_file()}
        spec = prepare(self.package, '1'*40, self.reference, self.output)
        self.assertEqual(spec['seed_sha256'], '4'*64)
        self.assertEqual(spec['executable_sha256'], digest(self.package/'DWM2tRecomp.exe'))
        self.assertEqual(spec['source'], '1'*40)
        self.assertEqual(before, {path: digest(path) for path in before})

    def test_different_source_is_rejected_before_output(self):
        with self.assertRaises(ValueError):
            prepare(self.package, '2'*40, self.reference, self.output)
        self.assertFalse(self.output.exists())

    def test_changed_packaged_file_is_rejected_before_output(self):
        (self.package/'Play.cmd').write_bytes(b'changed')
        with self.assertRaises(ValueError):
            prepare(self.package, '1'*40, self.reference, self.output)
        self.assertFalse(self.output.exists())

    def test_derived_output_is_never_overwritten(self):
        self.output.write_bytes(b'preserve existing evidence')
        with self.assertRaises(FileExistsError):
            prepare(self.package, '1'*40, self.reference, self.output)
        self.assertEqual(self.output.read_bytes(), b'preserve existing evidence')


if __name__ == '__main__':
    unittest.main()
