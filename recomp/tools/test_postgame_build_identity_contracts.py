"""Postgame provenance contracts; synthetic executable bytes are never executed."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from m8_build_identity import ROM_SHA, load_identity
from test_postgame_supplemental import (
    BASELINE_VALIDATION_RUN_ID, BUILD_RUN_ID, ENDING_SHA, EXE_BYTES, EXE_SHA,
    POSTGAME_STAGE_NAMES, SOURCE, SOURCE_ARCHIVE_SHA, SOURCE_MANIFEST_SHA,
    digest, validate_build_identity, verify_replay_provenance,
)


class PostgameBuildIdentityContracts(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.exe = self.root/'synthetic-never-executed.exe'
        self.exe.write_bytes(b'Postgame provenance contract fixture; never execute.')
        self.path = self.root/'build-identity.json'
        self.data = dict(schema=1, kind='complete_aot_diagnostic_build',
                         build_testing=True, fixed_bank=0, romx_banks=list(range(1, 256)),
                         rom_sha256=ROM_SHA, source_commit='1'*40,
                         executable_sha256=digest(self.exe), executable_bytes=self.exe.stat().st_size,
                         source_archive_sha256='2'*64, source_manifest_sha256='3'*64)
        self.write()

    def write(self):
        self.path.write_text(json.dumps(self.data), encoding='utf-8')

    def fresh(self):
        return validate_build_identity(self.exe, self.path, fresh_build=True,
                                       build_run_id='987654321')

    def test_historical_pins_remain_exact(self):
        self.assertEqual(SOURCE, '3d573873ae8122cbb10fcd5d0f7ae7a33a7609ba')
        self.assertEqual(EXE_SHA, 'f93b7f96212559f65f05e09f8443a224bbda7d124047047fbf53510e16ae0321')
        self.assertEqual(EXE_BYTES, 725575680)
        self.assertEqual(SOURCE_ARCHIVE_SHA,
                         'c75ba57b296c1b2038cd5cc3789059eb4513f79831d64cfb6f4b855a22d72722')
        self.assertEqual(SOURCE_MANIFEST_SHA,
                         '462752ad7e2fa0e658486cc5524106bb1f121a353d279418dd5cfa75d230ba99')
        self.assertEqual(ENDING_SHA,
                         '0649c4ef78867d2e55f352ddb0fea811fea6e3cf7407f8451220cc2bf01df95d')
        self.assertEqual(BUILD_RUN_ID, '40175408153')
        self.assertEqual(BASELINE_VALIDATION_RUN_ID, '40183484388')

    def test_fresh_build_derives_actual_identity_and_preserves_baseline(self):
        before = {path: digest(path) for path in (self.exe, self.path)}
        identity, report = self.fresh()
        self.assertEqual(identity.source, self.data['source_commit'])
        self.assertEqual(report['executable_source'], self.data['source_commit'])
        self.assertEqual(report['executable_sha256'], digest(self.exe))
        self.assertEqual(report['executable_bytes'], self.exe.stat().st_size)
        self.assertEqual(report['source_archive_sha256'], self.data['source_archive_sha256'])
        self.assertEqual(report['source_manifest_sha256'], self.data['source_manifest_sha256'])
        self.assertEqual(report['build_identity_sha256'], digest(self.path))
        self.assertEqual(report['build_run_id'], '987654321')
        self.assertEqual(report['diagnostic_build_mode'], 'fresh_diagnostic')
        self.assertIs(report['new_binary_accepted'], False)
        self.assertEqual(report['accepted_baseline']['executable_source'], SOURCE)
        self.assertEqual(report['accepted_baseline']['executable_sha256'], EXE_SHA)
        self.assertEqual(report['accepted_baseline']['build_run_id'], BUILD_RUN_ID)
        self.assertEqual(before, {path: digest(path) for path in before})

    def test_fresh_build_without_workflow_id_is_not_attributed_to_historical_run(self):
        _, report = validate_build_identity(self.exe, self.path, fresh_build=True)
        self.assertIsNone(report['build_run_id'])
        self.assertEqual(report['accepted_baseline']['build_run_id'], BUILD_RUN_ID)

    def test_fresh_build_rejects_invalid_workflow_id(self):
        for run_id in ('', 'not-a-run', '1\n2', True, 123):
            with self.subTest(run_id=run_id), self.assertRaises(ValueError):
                validate_build_identity(self.exe, self.path, fresh_build=True,
                                        build_run_id=run_id)

    def test_valid_fresh_identity_requires_explicit_fresh_opt_in(self):
        with self.assertRaisesRegex(ValueError, 'unchanged accepted'):
            validate_build_identity(self.exe, self.path)

    def test_historical_metadata_does_not_bypass_actual_executable_verification(self):
        self.data.update(source_commit=SOURCE, executable_sha256=EXE_SHA,
                         executable_bytes=EXE_BYTES, source_archive_sha256=SOURCE_ARCHIVE_SHA,
                         source_manifest_sha256=SOURCE_MANIFEST_SHA)
        self.write()
        with self.assertRaisesRegex(ValueError, 'executable differs'):
            validate_build_identity(self.exe, self.path)

    def test_fresh_build_rejects_incomplete_or_wrong_identity(self):
        changes = [('schema', 2), ('kind', 'production'), ('build_testing', False),
                   ('fixed_bank', 1), ('romx_banks', list(range(1, 255))),
                   ('romx_banks', [*range(1, 255), 254]), ('rom_sha256', '0'*64),
                   ('source_commit', 'short'), ('executable_sha256', 'bad'),
                   ('source_archive_sha256', ''), ('source_manifest_sha256', None),
                   ('executable_bytes', True), ('executable_bytes', 0)]
        for key, value in changes:
            with self.subTest(key=key, value=value):
                original = self.data[key]
                self.data[key] = value
                self.write()
                with self.assertRaises(ValueError):
                    self.fresh()
                self.data[key] = original
        self.write()

    def test_fresh_build_rejects_non_object_identity(self):
        for value in ([], None, 'not metadata'):
            with self.subTest(value=value):
                self.path.write_text(json.dumps(value), encoding='utf-8')
                with self.assertRaisesRegex(ValueError, 'must be an object'):
                    self.fresh()

    def test_fresh_build_rejects_same_size_executable_hash_mismatch(self):
        original = self.exe.read_bytes()
        self.exe.write_bytes(b'!'+original[1:])
        with self.assertRaisesRegex(ValueError, 'executable differs'):
            self.fresh()

    def test_fresh_build_rejects_executable_size_mismatch(self):
        self.exe.write_bytes(self.exe.read_bytes()+b'!')
        with self.assertRaisesRegex(ValueError, 'executable differs'):
            self.fresh()

    def test_identity_cannot_change_between_metadata_read_and_shared_validation(self):
        def replace_then_load(path):
            self.data['source_archive_sha256'] = '4'*64
            self.write()
            return load_identity(path)

        with patch('test_postgame_supplemental.load_identity', side_effect=replace_then_load):
            with self.assertRaisesRegex(ValueError, 'changed while it was read'):
                self.fresh()


class PostgameReplayProvenanceContracts(unittest.TestCase):
    def setUp(self):
        self.provenance = dict(executable_source='1'*40, executable_sha256='2'*64,
                               executable_bytes=12345, build_identity_sha256='3'*64)
        self.stages = [dict(name=name, frames=index+1,
                            route_sha256=f'{index+4:064x}', save_sha256=f'{index+20:064x}')
                       for index, name in enumerate(POSTGAME_STAGE_NAMES)]
        self.base = dict(status='passed', platform='Windows', **self.provenance,
                         seed_chain_audited=True, seed_chain_links=7,
                         stages=[dict(stage=stage['name'], status='passed', native_returncode=0,
                                      frames=stage['frames'], route_sha256=stage['route_sha256'],
                                      save_sha256=stage['save_sha256']) for stage in self.stages])

    def verify(self, base=None, stages=None, returncode=0):
        verify_replay_provenance(self.base if base is None else base,
                                 self.stages if stages is None else stages,
                                 self.provenance, 'Windows', returncode)

    def test_all_seven_actual_build_results_and_parent_links_are_required(self):
        self.verify()

    def test_failed_runner_cannot_report_a_passing_postgame(self):
        for code in (1, -1, False, None):
            with self.subTest(code=code), self.assertRaises(ValueError):
                self.verify(returncode=code)

    def test_missing_or_wrong_build_and_parent_chain_provenance_is_rejected(self):
        changes = [('status', 'running'), ('platform', 'Wine on Linux'),
                   ('executable_source', SOURCE), ('executable_sha256', EXE_SHA),
                   ('executable_bytes', EXE_BYTES), ('build_identity_sha256', '4'*64),
                   ('seed_chain_audited', False), ('seed_chain_links', 6),
                   ('seed_chain_links', True), ('stages', []), ('stages', None)]
        for key, value in changes:
            with self.subTest(key=key, value=value):
                base = copy.deepcopy(self.base)
                base[key] = value
                with self.assertRaises(ValueError):
                    self.verify(base=base)

    def test_failed_or_unbound_native_stage_is_rejected(self):
        changes = [('stage', 'a-different-checkpoint'), ('status', 'failed'),
                   ('native_returncode', 1), ('native_returncode', False),
                   ('frames', 999), ('route_sha256', '0'*64), ('save_sha256', '0'*64)]
        for key, value in changes:
            with self.subTest(key=key, value=value):
                base = copy.deepcopy(self.base)
                base['stages'][3][key] = value
                with self.assertRaises(ValueError):
                    self.verify(base=base)

    def test_missing_extra_duplicate_or_reordered_stage_is_rejected(self):
        for stages in (self.stages[:-1], self.stages+[self.stages[-1]],
                       [self.stages[0]]*7, list(reversed(self.stages))):
            with self.subTest(names=[stage['name'] for stage in stages]):
                with self.assertRaises(ValueError):
                    self.verify(stages=stages)
        for actual in (self.base['stages'][:-1],
                       self.base['stages']+[self.base['stages'][-1]],
                       list(reversed(self.base['stages']))):
            base = copy.deepcopy(self.base)
            base['stages'] = actual
            with self.assertRaises(ValueError):
                self.verify(base=base)


if __name__ == '__main__':
    unittest.main()
