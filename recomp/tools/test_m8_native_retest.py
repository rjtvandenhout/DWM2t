"""Synthetic continuation-proof contracts; no executable or gameplay is run."""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
import zipfile

from m8_build_identity import ROM_SHA, digest
from m8_package import BASE_FILES, verify_package
from package_verified_m8 import NATIVE_SUITE_TESTS, package_run, verify_native_retest


class NativeRetestContracts(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = '1' * 40
        self.tool_source = '2' * 40
        self.build_run = '123'
        self.validation_run = '456'
        self.addCleanup(patch.stopall)
        patch('package_verified_m8.current_packaging_source', return_value=self.tool_source).start()
        patch.dict(os.environ, GITHUB_SHA=self.tool_source,
                   GITHUB_RUN_ID=self.validation_run).start()
        self.diagnostic = self.root/'diagnostic.exe'
        self.diagnostic.write_bytes(b'SYNTHETIC DIAGNOSTIC, NEVER EXECUTED')
        self.definitions = (Path(__file__).resolve().parents[1]/'CMakeLists.txt').read_bytes()
        self.names = [name.decode('ascii') for name in
                      re.findall(rb'add_test\(NAME\s+([A-Za-z0-9_]+)', self.definitions)]
        self.assertEqual(len(self.names), 18)
        self.assertIn('M8_audio_playback', self.names)
        self.assertIn('M8_audio_stream', self.names)
        self.archive = self.root/'source.tar'
        self.write_archive()
        self.initial = self.root/'initial.xml'
        self.write_xml(self.initial, initial=True)
        self.retest = self.root/'retest'
        self.retest.mkdir()
        self.xml = self.retest/'native-results.xml'
        self.write_xml(self.xml)
        self.provenance_path = self.retest/'native-retest-provenance.json'
        self.provenance = dict(
            schema=1, status='passed', platform='Windows', source_commit=self.source,
            build_run_id=self.build_run, validation_run_id=self.validation_run,
            packaging_source_commit=self.tool_source,
            diagnostic_sha256=digest(self.diagnostic), source_archive_sha256=digest(self.archive),
            native_suite_source=self.source, native_suite_archive_sha256=digest(self.archive),
            native_test_definitions_sha256=hashlib.sha256(self.definitions).hexdigest(),
            original_native_tests_sha256=digest(self.initial),
            retest_native_tests_sha256=digest(self.xml), ctest_returncode=0, tests=18,
            command=['C:\\Program Files\\CMake\\bin\\ctest.exe', '--test-dir',
                     'D:\\a\\native', '-C', 'Release', '--parallel', '4',
                     '--output-on-failure', '--output-junit', str(self.xml)])
        self.save_provenance()

    def write_archive(self, *, source=None, definitions=None):
        data = self.definitions if definitions is None else definitions
        with tarfile.open(self.archive, 'w', format=tarfile.PAX_FORMAT,
                          pax_headers={'comment': source or self.source}) as archive:
            member = tarfile.TarInfo('recomp/CMakeLists.txt')
            member.size = len(data)
            archive.addfile(member, io.BytesIO(data))

    def write_xml(self, path, *, initial=False):
        suite = ET.Element('testsuite', tests='18', failures='0', errors='0',
                           skipped='2' if initial else '0', disabled='0')
        for name in self.names:
            skipped = initial and name in ('M8_audio_playback', 'M8_audio_stream')
            case = ET.SubElement(suite, 'testcase', name=name,
                                 status='notrun' if skipped else 'run')
            if skipped:
                ET.SubElement(case, 'skipped', message='No native render endpoint')
        ET.SubElement(suite, 'system-out').text = (
            'SYNTHETIC INITIAL UNACCEPTED' if initial else 'SYNTHETIC FULL RERUN')
        ET.indent(suite)
        path.write_bytes(ET.tostring(suite, encoding='utf-8').replace(b'\n', b'\r\n'))

    def save_provenance(self):
        self.provenance_path.write_text(json.dumps(self.provenance), encoding='utf-8')

    def refresh_xml_hash(self):
        self.provenance['retest_native_tests_sha256'] = digest(self.xml)
        self.save_provenance()

    def verify(self, *, run=None):
        return verify_native_retest(self.retest, self.source, self.build_run,
                                    run or self.validation_run, self.diagnostic,
                                    self.archive, self.initial)

    def test_all_original_tests_can_supersede_unaccepted_audio_skips(self):
        provenance, evidence = self.verify()
        self.assertEqual(provenance['tests'], 18)
        self.assertEqual(set(NATIVE_SUITE_TESTS), set(self.names))
        self.assertEqual(evidence['initial-native-tests.xml'].read_bytes(), self.initial.read_bytes())
        self.assertIn(b'<skipped', self.initial.read_bytes())
        self.assertNotIn(b'<skipped', evidence['native-tests.xml'].read_bytes())

    def test_every_identity_and_run_binding_is_checked(self):
        original = dict(self.provenance)
        substitutions = {
            'schema': 2, 'status': 'skipped', 'platform': 'Wine on Linux',
            'source_commit': '3'*40, 'build_run_id': '789', 'validation_run_id': '789',
            'packaging_source_commit': '3'*40, 'diagnostic_sha256': '0'*64,
            'source_archive_sha256': '0'*64, 'native_suite_source': '3'*40,
            'native_suite_archive_sha256': '0'*64,
            'native_test_definitions_sha256': '0'*64,
            'original_native_tests_sha256': '0'*64, 'retest_native_tests_sha256': '0'*64,
            'ctest_returncode': 77, 'tests': 17,
        }
        for key, value in substitutions.items():
            with self.subTest(field=key):
                self.provenance = dict(original, **{key: value})
                self.save_provenance()
                with self.assertRaises(ValueError):
                    self.verify()

    def test_boolean_success_is_not_a_zero_exit_code(self):
        self.provenance['ctest_returncode'] = False
        self.save_provenance()
        with self.assertRaises(ValueError):
            self.verify()

    def test_changed_actual_diagnostic_is_refused(self):
        self.diagnostic.write_bytes(b'OTHER SYNTHETIC DIAGNOSTIC')
        with self.assertRaises(ValueError):
            self.verify()

    def test_changed_raw_initial_xml_is_refused(self):
        self.initial.write_bytes(self.initial.read_bytes().replace(b'\r\n', b'\n'))
        with self.assertRaises(ValueError):
            self.verify()

    def test_changed_raw_rerun_xml_is_refused(self):
        self.xml.write_bytes(self.xml.read_bytes().replace(b'\r\n', b'\n'))
        with self.assertRaises(ValueError):
            self.verify()

    def test_missing_audio_playback_cannot_be_hidden_by_another_test(self):
        suite = ET.parse(self.xml).getroot()
        suite.find("testcase[@name='M8_audio_playback']").set('name', 'optional_unrelated_test')
        ET.ElementTree(suite).write(self.xml)
        self.refresh_xml_hash()
        with self.assertRaises(ValueError):
            self.verify()

    def test_duplicate_audio_playback_does_not_replace_audio_stream(self):
        suite = ET.parse(self.xml).getroot()
        suite.find("testcase[@name='M8_audio_stream']").set('name', 'M8_audio_playback')
        ET.ElementTree(suite).write(self.xml)
        self.refresh_xml_hash()
        with self.assertRaises(ValueError):
            self.verify()

    def test_additional_tests_cannot_disguise_a_selected_suite(self):
        suite = ET.parse(self.xml).getroot()
        ET.SubElement(suite, 'testcase', name='unrelated_extra_test', status='run')
        suite.set('tests', '19')
        ET.ElementTree(suite).write(self.xml)
        self.refresh_xml_hash()
        with self.assertRaises(ValueError):
            self.verify()

    def test_skips_errors_failures_and_notrun_status_are_refused(self):
        original = self.xml.read_bytes()
        for tag in ('skipped', 'failure', 'error', 'notrun'):
            with self.subTest(result=tag):
                self.xml.write_bytes(original)
                suite = ET.parse(self.xml).getroot()
                case = suite.find("testcase[@name='M8_audio_stream']")
                if tag == 'notrun':
                    case.set('status', 'notrun')
                else:
                    ET.SubElement(case, tag)
                ET.ElementTree(suite).write(self.xml)
                self.refresh_xml_hash()
                with self.assertRaises(ValueError):
                    self.verify()

    def test_suite_counters_cannot_contradict_the_cases(self):
        original = self.xml.read_bytes()
        for key, value in [('tests', '17'), ('skipped', '1'), ('disabled', '1'),
                           ('errors', '1'), ('failures', '1')]:
            with self.subTest(counter=key):
                self.xml.write_bytes(original)
                suite = ET.parse(self.xml).getroot()
                suite.set(key, value)
                ET.ElementTree(suite).write(self.xml)
                self.refresh_xml_hash()
                with self.assertRaises(ValueError):
                    self.verify()

    def test_source_archive_commit_marker_must_match(self):
        self.write_archive(source='3'*40)
        archive_sha = digest(self.archive)
        self.provenance.update(source_archive_sha256=archive_sha,
                               native_suite_archive_sha256=archive_sha)
        self.save_provenance()
        with self.assertRaises(ValueError):
            self.verify()

    def test_original_definitions_cannot_drop_an_output_gate(self):
        definitions = self.definitions.replace(b'add_test(NAME M8_audio_stream',
                                               b'add_test(NAME unrelated_audio_test')
        self.write_archive(definitions=definitions)
        archive_sha = digest(self.archive)
        self.provenance.update(source_archive_sha256=archive_sha,
                               native_suite_archive_sha256=archive_sha,
                               native_test_definitions_sha256=hashlib.sha256(definitions).hexdigest())
        self.save_provenance()
        with self.assertRaises(ValueError):
            self.verify()

    def test_actual_workflow_run_must_match(self):
        os.environ['GITHUB_RUN_ID'] = '789'
        with self.assertRaises(ValueError):
            self.verify()

    def test_actual_workflow_commit_must_match(self):
        os.environ['GITHUB_SHA'] = '3'*40
        with self.assertRaises(ValueError):
            self.verify()

    def test_initial_run_cannot_be_relabelled_as_the_validation_run(self):
        with self.assertRaises(ValueError):
            self.verify(run=self.build_run)

    def test_non_ctest_or_selected_commands_are_refused(self):
        command = list(self.provenance['command'])
        for changed in [['python', 'rewrite_results.py'], command+['-R', 'M8_audio'],
                        command+['--rerun-failed'], command+['--exclude-regex=M8_audio']]:
            with self.subTest(command=changed):
                self.provenance['command'] = changed
                self.save_provenance()
                with self.assertRaises(ValueError):
                    self.verify()

    def test_retest_options_must_be_paired(self):
        for options in [dict(native_retest=self.retest),
                        dict(validation_run_id=self.validation_run)]:
            with self.subTest(options=options):
                output = self.root/'incomplete-output'
                with self.assertRaises(ValueError):
                    package_run(self.root, self.source, self.build_run, output, **options)
                self.assertFalse(output.exists())

    def complete_proof(self):
        folders = {name: self.root/f'M8-fresh-{name}-{self.build_run}' for name in
                   ('diagnostic', 'production', 'story', 'production-journal', 'posix-persistence')}
        for folder in folders.values():
            folder.mkdir()
        def write(folder, name, data):
            path = folder/name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data), encoding='utf-8')
            return path
        package = self.root/'candidate'
        package.mkdir()
        for name in BASE_FILES:
            (package/name).write_bytes(('SYNTHETIC NOT EXECUTED '+name).encode())
        (package/'README.txt').write_text('SYNTHETIC\nSTART\nOriginal controls\n', encoding='utf-8')
        executable = digest(package/'DWM2tRecomp.exe')
        diagnostic_sha = digest(self.diagnostic)
        def report(folder, name, *, diagnostic=False, **fields):
            return write(folder, name, dict(status='passed', platform='Windows', source=self.source,
                         executable_sha256=diagnostic_sha if diagnostic else executable, **fields))
        metadata = dict(schema=1, status='UNTESTED_CANDIDATE', source_commit=self.source,
                        rom_sha256=ROM_SHA, fixed_bank=0, romx_banks=list(range(1, 256)),
                        full_game_verified=False, m8_accepted=False,
                        files={name: digest(package/name) for name in BASE_FILES})
        write(package, 'manifest.json', metadata)
        for name in ('diagnostic', 'production'):
            shutil.copyfile(self.archive, folders[name]/'source.tar')
        shutil.copyfile(self.diagnostic, folders['diagnostic']/'DWM2tRecompFull.exe')
        shutil.copyfile(self.initial, folders['diagnostic']/'native-results.xml')
        write(folders['diagnostic'], 'build-identity.json', dict(schema=1,
              kind='complete_aot_diagnostic_build', build_testing=True, fixed_bank=0,
              romx_banks=list(range(1, 256)), rom_sha256=ROM_SHA, source_commit=self.source,
              executable_sha256=diagnostic_sha, executable_bytes=self.diagnostic.stat().st_size,
              source_archive_sha256=digest(self.archive), source_manifest_sha256='0'*64))
        for name in ('production', 'posix-persistence'):
            (folders[name]/'save-io.xml').write_text(
                '<testsuite><testcase/><testcase/></testsuite>', encoding='utf-8')
        for name in ('pirate', 'village', 'farm-dancer', 'party-preparation'):
            report(folders['diagnostic'], name+'-validation.json', diagnostic=True)
        manifest = json.loads((Path(__file__).resolve().parents[1]/
                               'tests/m8_sea_story_checkpoints.json').read_text(encoding='utf-8'))
        stages = [dict(stage=stage['name'], frames=stage['frames'],
                       route_sha256=stage['route_sha256'], save_sha256=stage['save_sha256'],
                       native_returncode=0, status='passed') for stage in manifest['stages']]
        stages[-1]['ending_completed'] = True
        report(folders['story'], 'story-checkpoints-validation.json', diagnostic=True,
               stages=stages, ending_completed=True, workers=4,
               seed_chain_audited=True, seed_chain_links=len(stages))
        for name, default in [('direct-start', True), ('profile-start', False)]:
            report(folders['production']/name, 'player-startup.json',
                   checks=['synthetic']*12, no_argument_start=default)
        report(folders['production-journal'], 'player-package.json', checks=['synthetic']*21,
               package_manifest_sha256=digest(package/'manifest.json'))
        for name, stage, owned in [
                ('production-journal', next(s for s in manifest['stages'] if s['name']=='raygigas-birth'), 12),
                ('production-ending-journal', manifest['stages'][-1], 17)]:
            report(folders['production-journal']/name, 'player-late-journal.json',
                   input_journal_sha256=stage['save_sha256'], quest_bytes=107,
                   original_owned_creatures=owned, fresh_process_reload=True,
                   normal_shutdowns=2, original_p1_only=True)
        archive = folders['production']/'DWM2t-M8-UNTESTED-synthetic.zip'
        with zipfile.ZipFile(archive, 'w') as zipped:
            for path in package.iterdir():
                zipped.write(path, 'DWM2t-M8-UNTESTED/'+path.name)
        write(folders['production'], 'build-report.json', dict(status='built_untested',
              source_commit=self.source, executable_sha256=executable,
              zip_sha256=digest(archive), source_archive_sha256=digest(self.archive)))
        return folders, package

    def test_default_packager_still_refuses_the_original_skipped_suite(self):
        self.complete_proof()
        output = self.root/'default-output'
        with self.assertRaisesRegex(ValueError, 'skipped'):
            package_run(self.root, self.source, self.build_run, output)
        self.assertFalse(output.exists())

    def test_continuation_preserves_bytes_and_separates_all_run_identities(self):
        folders, candidate = self.complete_proof()
        original = (folders['diagnostic']/'native-results.xml').read_bytes()
        rerun = self.xml.read_bytes()
        output = self.root/'continued-output'
        archive = package_run(self.root, self.source, self.build_run, output,
                              native_retest=self.retest, validation_run_id=self.validation_run)
        package = output/'DWM2t-M8'
        verify_package(package, self.source)
        record = json.loads((package/'validation.json').read_text(encoding='utf-8'))
        self.assertEqual(record['source_commit'], self.source)
        self.assertEqual(record['packaging_source_commit'], self.tool_source)
        self.assertEqual(record['build_run_id'], self.build_run)
        self.assertEqual(record['story_run_id'], self.build_run)
        self.assertEqual(record['validation_run_id'], self.validation_run)
        self.assertEqual(record['native_run_id'], self.validation_run)
        self.assertTrue(record['native_run_url'].endswith('/'+self.validation_run))
        self.assertEqual(record['initial_native_tests_status'], 'unaccepted')
        self.assertEqual(record['retained_native_tests'], 18)
        self.assertEqual((package/'validation/initial-native-tests.xml').read_bytes(), original)
        self.assertEqual((package/'validation/native-tests.xml').read_bytes(), rerun)
        self.assertEqual((package/'validation/native-retest-provenance.json').read_bytes(),
                         self.provenance_path.read_bytes())
        self.assertEqual((folders['diagnostic']/'native-results.xml').read_bytes(), original)
        self.assertEqual(digest(package/'DWM2tRecomp.exe'), digest(candidate/'DWM2tRecomp.exe'))
        with zipfile.ZipFile(archive) as zipped:
            self.assertEqual(zipped.read('DWM2t-M8/validation/initial-native-tests.xml'), original)
            self.assertEqual(zipped.read('DWM2t-M8/validation/native-tests.xml'), rerun)
            self.assertEqual(zipped.read('DWM2t-M8/DWM2tRecomp.exe'),
                             (candidate/'DWM2tRecomp.exe').read_bytes())


if __name__ == '__main__':
    unittest.main()
