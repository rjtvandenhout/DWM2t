"""Evidence-contract unit cases; synthetic files are never game acceptance."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from full_rom_validation import CORE_INPUTS, RUNTIME_CORE_TARGETS, RUNTIME_CORE_TESTS, verify_runtime_core


class RuntimeCoreEvidenceContracts(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = 'a'*40
        self.xml = self.root/'runtime-core-tests.xml'
        self.path = self.root/'runtime-core-validation.json'
        self.manifest = {}
        self.report = dict(schema=1, kind='full_rom_runtime_core_validation', status='passed',
                           platform='Linux', source_commit=self.source,
                           source_inventory_unchanged=True, binaries_unchanged_after_ctest=True,
                           orchestrator_inputs_match_source=True,
                           original_game_executed=False, campaign_verified=False,
                           full_rom_coverage_claimed=False,
                           configure_returncode=0, build_returncode=0, ctest_returncode=0,
                           tests=len(RUNTIME_CORE_TESTS), test_names=list(RUNTIME_CORE_TESTS),
                           input_sha256={}, lf_sha256={}, binaries={}, receipts={},
                           commands={
                               'configure': ['cmake', '-S', '/source/recomp/tests/runtime-core',
                                             '-B', '/evidence/native', '-DCMAKE_BUILD_TYPE=Release',
                                             '-DBUILD_TESTING=ON'],
                               'build': ['cmake', '--build', '/evidence/native', '--config',
                                         'Release', '--parallel', '2'],
                               'ctest': ['ctest', '--test-dir', '/evidence/native', '-C', 'Release',
                                         '--parallel', '2', '--output-on-failure', '--output-junit',
                                         '/evidence/runtime-core-tests.xml']})
        for name in sorted(CORE_INPUTS | {'recomp/include/recomp/extra.hpp'}):
            data = b'// Synthetic validator input.\n// Second line.\n'
            self.put('source-inputs/'+name, data)
            sha = hashlib.sha256(data).hexdigest()
            self.manifest[name] = sha
            self.report['input_sha256'][name] = sha
            self.report['lf_sha256'][name] = sha
        for name in RUNTIME_CORE_TARGETS:
            self.report['binaries'][name] = self.put('bin/'+name, b'synthetic evidence-contract binary\n')
        for name in RUNTIME_CORE_TESTS:
            if name in RUNTIME_CORE_TESTS[:3]:
                data = dict(schema=1, status='passed', group=name[8:-10], checks=1,
                            original_game_executed=False, original_save_loaded_or_written=False,
                            original_rom_aot_entries=0, rom_dispatch_stub_calls=0, fatal_error='',
                            cases=[dict(name='synthetic-subcase', status='passed', checks=1, error='')])
            elif name == 'FullROM_generated_aot_contracts':
                data = dict(schema=1, status='passed', checks=1, original_game_executed=False,
                            synthetic_fixture=True, sparse_generated_cases=True,
                            full_bank_coverage_claimed=False)
            else:
                data = dict(status='passed', contracts=['synthetic-renderer-contract'])
            self.report['receipts'][name] = self.put_json('evidence/'+name+'.json', data)
        self.report['generated_fixture'] = self.put_json('evidence/generated-fixture-source.json',
            dict(schema=1, synthetic_fixture=True, original_rom_read=False,
                 original_game_executed=False, sparse_generated_cases=True, emitted_case_bodies=26))
        root = ET.Element('testsuite', tests=str(len(RUNTIME_CORE_TESTS)), failures='0',
                          errors='0', skipped='0', disabled='0')
        for name in RUNTIME_CORE_TESTS:
            ET.SubElement(root, 'testcase', name=name, status='run', time='0.001')
        self.write_xml(root)

    def put(self, name, data):
        path = self.root/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return dict(path=name, bytes=len(data), sha256=hashlib.sha256(data).hexdigest())

    def put_json(self, name, data):
        return self.put(name, (json.dumps(data)+'\n').encode('utf-8'))

    def write_xml(self, root):
        ET.ElementTree(root).write(self.xml, encoding='utf-8', xml_declaration=True)
        data = self.xml.read_bytes()
        self.report.update(xml_sha256=hashlib.sha256(data).hexdigest(), xml_bytes=len(data),
                           test_names=[case.get('name') for case in root.iter('testcase')])

    def verify(self, *, manifest=True):
        self.path.write_text(json.dumps(self.report), encoding='utf-8')
        return verify_runtime_core(self.path, self.xml, self.source,
                                   source_manifest=self.manifest if manifest else None)

    def rejected(self):
        with self.assertRaises((ValueError, OSError)):
            self.verify()

    def change_receipt(self, name, change):
        path = 'evidence/'+name+'.json'
        data = json.loads((self.root/path).read_text())
        change(data)
        self.report['receipts'][name] = self.put_json(path, data)

    def test_complete_bound_evidence_is_accepted(self):
        result = self.verify()
        self.assertEqual(result['tests'], 5)
        self.assertEqual(result['binary_files_verified'], 3)
        self.assertTrue(result['source_manifest_verified'])

    def test_without_production_manifest_still_checks_actual_artifacts(self):
        result = self.verify(manifest=False)
        self.assertFalse(result['source_manifest_verified'])
        self.assertEqual(result['input_files_verified'], len(self.manifest))

    def test_windows_suffix_and_platform_are_supported(self):
        self.report['platform'] = 'Windows'
        for name in RUNTIME_CORE_TARGETS:
            old = self.root/'bin'/name
            self.report['binaries'][name] = self.put('bin/'+name+'.exe', old.read_bytes())
            old.unlink()
        self.assertEqual(self.verify()['platform'], 'Windows')

    def test_wrong_source_commit_rejected(self):
        self.report['source_commit'] = 'b'*40
        self.rejected()

    def test_unknown_platform_rejected(self):
        self.report['platform'] = 'Darwin'
        self.rejected()

    def test_self_declared_pass_cannot_hide_failed_process(self):
        self.report['ctest_returncode'] = 8
        self.rejected()

    def test_bool_returncode_is_not_integer_zero(self):
        self.report['build_returncode'] = False
        self.rejected()

    def test_all_build_processes_must_have_succeeded(self):
        self.report['configure_returncode'] = 1
        self.rejected()

    def test_empty_suite_rejected_even_with_matching_xml_hash(self):
        self.write_xml(ET.Element('testsuite', tests='5', failures='0'))
        self.rejected()

    def test_arbitrary_named_suite_rejected(self):
        root = ET.parse(self.xml).getroot()
        for index, case in enumerate(root):
            case.set('name', 'unrelated_'+str(index))
        self.write_xml(root)
        self.rejected()

    def test_duplicate_test_rejected(self):
        root = ET.parse(self.xml).getroot()
        root[-1].set('name', RUNTIME_CORE_TESTS[0])
        self.write_xml(root)
        self.rejected()

    def test_missing_fifth_generated_aot_test_rejected(self):
        root = ET.parse(self.xml).getroot()
        root.remove(root[-1])
        root.set('tests', '4')
        self.write_xml(root)
        self.rejected()

    def test_json_pass_cannot_override_failure_tag(self):
        root = ET.parse(self.xml).getroot()
        ET.SubElement(root[0], 'failure').text = 'native check failed'
        self.write_xml(root)
        self.rejected()

    def test_skipped_test_rejected(self):
        root = ET.parse(self.xml).getroot()
        ET.SubElement(root[0], 'skipped')
        self.write_xml(root)
        self.rejected()

    def test_notrun_status_rejected(self):
        root = ET.parse(self.xml).getroot()
        root[0].set('status', 'notrun')
        self.write_xml(root)
        self.rejected()

    def test_suite_error_counter_rejected_without_child_error(self):
        root = ET.parse(self.xml).getroot()
        root.set('errors', '1')
        self.write_xml(root)
        self.rejected()

    def test_nested_suite_cannot_hide_failure_counters(self):
        root = ET.parse(self.xml).getroot()
        ET.SubElement(root, 'testsuite', tests='0', failures='1')
        self.write_xml(root)
        self.rejected()

    def test_changed_xml_bytes_rejected(self):
        self.xml.write_bytes(self.xml.read_bytes()+b'\n')
        self.rejected()

    def test_ctest_selection_filter_rejected_even_if_xml_has_all_names(self):
        self.report['commands']['ctest'].extend(['-R', 'FullROM'])
        self.rejected()

    def test_list_only_ctest_command_rejected(self):
        self.report['commands']['ctest'].append('--show-only=json-v1')
        self.rejected()

    def test_wrong_parallelism_rejected(self):
        command = self.report['commands']['ctest']
        command[command.index('--parallel')+1] = '4'
        self.rejected()

    def test_wrong_standalone_source_command_rejected(self):
        self.report['commands']['configure'][2] = '/source/recomp'
        self.rejected()

    def test_missing_required_source_input_rejected(self):
        name = 'recomp/src/runtime.cpp'
        del self.report['input_sha256'][name]
        del self.report['lf_sha256'][name]
        self.rejected()

    def test_omitted_archived_header_rejected(self):
        name = 'recomp/include/recomp/extra.hpp'
        del self.report['input_sha256'][name]
        del self.report['lf_sha256'][name]
        self.rejected()

    def test_changed_copied_source_bytes_rejected(self):
        (self.root/'source-inputs/recomp/src/runtime.cpp').write_bytes(b'changed input\n')
        self.rejected()

    def test_uniform_checkout_crlf_is_bound_to_archived_lf(self):
        name = 'recomp/src/runtime.cpp'
        path = self.root/'source-inputs'/name
        data = path.read_bytes().replace(b'\n', b'\r\n')
        path.write_bytes(data)
        self.report['input_sha256'][name] = hashlib.sha256(data).hexdigest()
        self.assertTrue(self.verify()['source_manifest_verified'])

    def test_lf_host_is_bound_to_archived_uniform_crlf(self):
        name = 'recomp/src/runtime.cpp'
        data = (self.root/'source-inputs'/name).read_bytes()
        self.manifest[name] = hashlib.sha256(data.replace(b'\n', b'\r\n')).hexdigest()
        self.assertTrue(self.verify()['source_manifest_verified'])

    def test_fake_normalized_hash_cannot_cover_changed_input(self):
        name = 'recomp/src/runtime.cpp'
        data = b'changed C++\r\n'
        (self.root/'source-inputs'/name).write_bytes(data)
        self.report['input_sha256'][name] = hashlib.sha256(data).hexdigest()
        self.rejected()

    def test_mixed_line_endings_are_not_exact_checkout_conversion(self):
        name = 'recomp/src/runtime.cpp'
        path = self.root/'source-inputs'/name
        data = path.read_bytes().replace(b'\n', b'\r\n', 1)
        path.write_bytes(data)
        self.report['input_sha256'][name] = hashlib.sha256(data).hexdigest()
        self.rejected()

    def test_real_source_change_rejected_even_when_hashes_recomputed(self):
        name = 'recomp/src/runtime.cpp'
        data = b'changed C++\n'
        (self.root/'source-inputs'/name).write_bytes(data)
        self.report['input_sha256'][name] = hashlib.sha256(data).hexdigest()
        self.report['lf_sha256'][name] = hashlib.sha256(data).hexdigest()
        self.rejected()

    def test_input_path_traversal_rejected(self):
        self.report['input_sha256']['../escape'] = 'a'*64
        self.report['lf_sha256']['../escape'] = 'a'*64
        self.rejected()

    def test_changed_tested_binary_rejected(self):
        (self.root/'bin'/RUNTIME_CORE_TARGETS[0]).write_bytes(b'changed executable')
        self.rejected()

    def test_missing_binary_identity_rejected(self):
        self.report['binaries'].pop(RUNTIME_CORE_TARGETS[-1])
        self.rejected()

    def test_missing_native_receipt_rejected(self):
        self.report['receipts'].pop(RUNTIME_CORE_TESTS[0])
        self.rejected()

    def test_failed_native_subcase_rejected_with_matching_receipt_hash(self):
        self.change_receipt(RUNTIME_CORE_TESTS[0],
                            lambda data: data['cases'][0].update(status='failed', error='bad result'))
        self.rejected()

    def test_empty_native_cases_cannot_claim_passed(self):
        self.change_receipt(RUNTIME_CORE_TESTS[0], lambda data: data.update(cases=[]))
        self.rejected()

    def test_synthetic_aot_receipt_cannot_claim_original_full_game(self):
        self.change_receipt('FullROM_generated_aot_contracts',
                            lambda data: data.update(original_game_executed=True))
        self.rejected()

    def test_changed_source_during_run_rejected(self):
        self.report['source_inventory_unchanged'] = False
        self.rejected()

    def test_changed_binary_during_ctest_rejected(self):
        self.report['binaries_unchanged_after_ctest'] = False
        self.rejected()

    def test_runtime_core_does_not_certify_campaign(self):
        self.report['campaign_verified'] = True
        self.rejected()


if __name__ == '__main__':
    unittest.main()
