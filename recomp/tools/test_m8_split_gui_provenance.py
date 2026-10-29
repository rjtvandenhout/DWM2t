"""Host contracts for separately rerun original production GUI evidence."""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import package_verified_m8 as packaging
from m8_build_identity import digest


class SplitGuiProvenanceContracts(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.gui = self.root/'new-gui-run'
        self.gui.mkdir()
        self.source, self.tooling = 'a'*40, 'b'*40
        self.build_run, self.validation_run = '123', '456'
        self.exe_sha, self.exe_bytes = 'c'*64, 123456
        self.archive = self.root/'source.tar'
        self.archive.write_bytes(b'original source archive, contract fixture')
        self.ending = self.root/'ending.sav'
        self.late = self.root/'late.sav'
        self.ending.write_bytes(b'E'*32768)
        self.late.write_bytes(b'L'*32768)
        self.ending_sha, self.late_sha = digest(self.ending), digest(self.late)
        self.script_hashes = {name:format(n+1, '064x') for n, name in
                              enumerate(packaging.SPLIT_GUI_SCRIPTS)}
        self.retest = {'packaging_source_commit':self.tooling}
        patch('package_verified_m8.current_packaging_source', return_value=self.tooling).start()
        patch('package_verified_m8.committed_tooling_script_hashes',
              return_value=self.script_hashes).start()
        patch.dict(os.environ, GITHUB_SHA=self.tooling, GITHUB_RUN_ID=self.validation_run).start()
        self.addCleanup(patch.stopall)
        self.manifest_path = self.gui/'original-artifact-manifest.json'
        jobs = {name:dict(id=n+10, conclusion='success') for n, name in enumerate(
            ('diagnostic','production','posix-persistence'))}
        artifacts = {name:dict(id=n+20, name=f'M8-fresh-{name}-{self.build_run}',
                               size_bytes=n+1, sha256=format(n+11, '064x'))
                     for n, name in enumerate(
                         ('diagnostic','production','story','postgame','posix-persistence'))}
        self.manifest = dict(schema=1, kind='original_build_artifacts', status='passed',
                             build_run_id=self.build_run, build_source_commit=self.source,
                             run_conclusion='failure', producer_jobs=jobs, artifacts=artifacts)
        self.write_manifest()
        self.reports = {}
        for index, name in enumerate(packaging.SPLIT_GUI_REPORTS):
            path = self.gui/name
            path.parent.mkdir(parents=True, exist_ok=True)
            data = {'synthetic_contract':index}
            if index == 0:
                data.update(gate_script_sha256=self.script_hashes[packaging.SPLIT_GUI_SCRIPTS[0]],
                            gui_helper_sha256=self.script_hashes[packaging.SPLIT_GUI_SCRIPTS[1]])
            path.write_text(json.dumps(data), encoding='utf-8')
            self.reports[name] = digest(path)
        self.attestation_path = self.root/'gui-attestation.json'
        self.attestation = dict(
            schema=1, kind='production_journal_revalidation', status='passed',
            platform='Windows', build_run_id=self.build_run, build_source_commit=self.source,
            validation_run_id=self.validation_run, tooling_source_commit=self.tooling,
            production_executable_sha256=self.exe_sha, production_executable_bytes=self.exe_bytes,
            source_archive_sha256=digest(self.archive), ending_journal_sha256=self.ending_sha,
            late_journal_sha256=self.late_sha,
            original_artifact_manifest_sha256=digest(self.manifest_path),
            scripts=self.script_hashes.copy(), reports=self.reports.copy())
        self.write_attestation()

    def write_manifest(self):
        self.manifest_path.write_text(json.dumps(self.manifest), encoding='utf-8')

    def write_attestation(self):
        self.attestation_path.write_text(json.dumps(self.attestation), encoding='utf-8')

    def verify(self):
        return packaging.verify_production_journal_attestation(
            self.attestation_path, self.gui, source=self.source, build_run=self.build_run,
            validation_run=self.validation_run, retest=self.retest,
            executable_sha=self.exe_sha, executable_bytes=self.exe_bytes, source_archive=self.archive,
            ending=self.ending, ending_sha=self.ending_sha,
            late=self.late, late_sha=self.late_sha)

    def test_exact_separate_evidence_is_accepted_and_retained(self):
        attestation, evidence = self.verify()
        self.assertEqual(attestation['build_run_id'], self.build_run)
        self.assertEqual(attestation['validation_run_id'], self.validation_run)
        self.assertEqual(evidence['original-build-artifacts.json'], self.manifest_path)
        self.assertEqual(evidence['production-journal-attestation.json'], self.attestation_path)

    def test_wrong_build_tooling_run_executable_or_seed_is_rejected(self):
        changes = {
            'schema':2, 'kind':'unrelated', 'status':'failed', 'platform':'Linux',
            'build_run_id':'789', 'build_source_commit':'d'*40, 'validation_run_id':'789',
            'tooling_source_commit':'d'*40, 'production_executable_sha256':'0'*64,
            'production_executable_bytes':1, 'source_archive_sha256':'0'*64,
            'ending_journal_sha256':'0'*64, 'late_journal_sha256':'0'*64,
            'original_artifact_manifest_sha256':'0'*64,
        }
        for key, value in changes.items():
            with self.subTest(field=key):
                before = self.attestation[key]
                self.attestation[key] = value
                self.write_attestation()
                with self.assertRaises(ValueError):
                    self.verify()
                self.attestation[key] = before
        self.write_attestation()

    def test_actual_windows_validation_run_must_match_native_retest(self):
        for key, value in [('GITHUB_RUN_ID','789'), ('GITHUB_SHA','d'*40)]:
            with self.subTest(key=key), patch.dict(os.environ, {key:value}):
                with self.assertRaises(ValueError):
                    self.verify()
        self.retest['packaging_source_commit'] = 'd'*40
        with self.assertRaises(ValueError):
            self.verify()

    def test_changed_report_or_tooling_script_is_rejected(self):
        self.attestation['scripts'][packaging.SPLIT_GUI_SCRIPTS[0]] = '0'*64
        self.write_attestation()
        with self.assertRaises(ValueError):
            self.verify()
        self.attestation['scripts'] = self.script_hashes.copy()
        self.write_attestation()
        link = self.gui/packaging.SPLIT_GUI_REPORTS[0]
        data = json.loads(link.read_text())
        data['gate_script_sha256'] = '0'*64
        link.write_text(json.dumps(data), encoding='utf-8')
        self.attestation['reports'][packaging.SPLIT_GUI_REPORTS[0]] = digest(link)
        self.write_attestation()
        with self.assertRaises(ValueError):
            self.verify()

    def test_missing_report_and_changed_report_bytes_are_rejected(self):
        report = self.gui/packaging.SPLIT_GUI_REPORTS[1]
        report.write_text('changed', encoding='utf-8')
        with self.assertRaises(ValueError):
            self.verify()
        report.unlink()
        with self.assertRaises(ValueError):
            self.verify()

    def test_actual_journal_and_source_archive_bytes_must_match(self):
        self.ending.write_bytes(b'X'*32768)
        self.attestation['ending_journal_sha256'] = digest(self.ending)
        self.write_attestation()
        with self.assertRaises(ValueError):
            self.verify()
        self.ending.write_bytes(b'E'*32768)
        self.attestation['ending_journal_sha256'] = self.ending_sha
        self.archive.write_bytes(b'changed archive')
        self.write_attestation()
        with self.assertRaises(ValueError):
            self.verify()

    def test_original_producer_and_artifact_metadata_cannot_be_relabelled(self):
        mutations = [
            lambda m:m.update(build_run_id='789'),
            lambda m:m['producer_jobs']['diagnostic'].update(conclusion='failure'),
            lambda m:m['producer_jobs']['production'].update(id=m['producer_jobs']['diagnostic']['id']),
            lambda m:m['artifacts']['story'].update(name='M8-fresh-story-789'),
            lambda m:m['artifacts']['story'].update(sha256='not-a-digest'),
            lambda m:m['artifacts']['postgame'].update(id=m['artifacts']['story']['id']),
            lambda m:m['artifacts'].pop('postgame'),
        ]
        original = json.loads(json.dumps(self.manifest))
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                self.manifest = json.loads(json.dumps(original))
                mutate(self.manifest)
                self.write_manifest()
                self.attestation['original_artifact_manifest_sha256'] = digest(self.manifest_path)
                self.write_attestation()
                with self.assertRaises(ValueError):
                    self.verify()

    def test_gui_options_require_both_evidence_and_full_native_retest(self):
        for options in (dict(production_journal_root=self.gui),
                        dict(production_journal_attestation=self.attestation_path),
                        dict(production_journal_root=self.gui,
                             production_journal_attestation=self.attestation_path)):
            with self.subTest(options=options):
                output = self.root/'no-release'
                with self.assertRaises(ValueError):
                    packaging.package_run(self.root, self.source, self.build_run, output, **options)
                self.assertFalse(output.exists())

    def test_split_evidence_cannot_replace_or_reuse_the_original_gui_artifact(self):
        original = self.root/f'M8-fresh-production-journal-{self.build_run}'
        original.mkdir()
        nested = original/'nested'
        nested.mkdir()
        old_attestation = original/'attestation.json'
        old_attestation.write_text('{}', encoding='utf-8')
        for gui, attestation in ((original, self.attestation_path),
                                 (nested, self.attestation_path),
                                 (self.root, self.attestation_path),
                                 (self.gui, old_attestation)):
            with self.subTest(gui=gui, attestation=attestation):
                output = self.root/'no-release'
                with self.assertRaisesRegex(ValueError, 'original run artifact'):
                    packaging.package_run(
                        self.root, self.source, self.build_run, output,
                        native_retest=self.root/'retest', validation_run_id=self.validation_run,
                        production_journal_root=gui, production_journal_attestation=attestation)
                self.assertFalse(output.exists())


class CommittedGuiScriptsContracts(unittest.TestCase):
    def test_checkout_script_must_match_its_committed_bytes(self):
        root = Path(packaging.__file__).resolve().parents[2]
        def committed(args, *, timeout):
            self.assertEqual(timeout, 30)
            return (root/args[-1].split(':', 1)[1]).read_bytes()
        with patch('package_verified_m8.subprocess.check_output', side_effect=committed):
            hashes = packaging.committed_tooling_script_hashes('a'*40)
        self.assertEqual(set(hashes), set(packaging.SPLIT_GUI_SCRIPTS))
        def wrong(args, *, timeout):
            data = committed(args, timeout=timeout)
            return data+b'changed' if args[-1].endswith('test_player_package.py') else data
        with patch('package_verified_m8.subprocess.check_output', side_effect=wrong):
            with self.assertRaises(ValueError):
                packaging.committed_tooling_script_hashes('a'*40)


if __name__ == '__main__':
    unittest.main()
