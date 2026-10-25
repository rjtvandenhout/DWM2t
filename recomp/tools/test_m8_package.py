"""Synthetic package/evidence contracts only; no game executable is run."""
from pathlib import Path
import json
import tempfile
import unittest
import zipfile

from m8_build_identity import ROM_SHA, digest
from m8_package import BASE_FILES, verify_package
from package_verified_m8 import package_run, passed_ctest, passed_json
from test_m8_story_checkpoints import verify_ending_witnesses


class PackageContracts(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.package = self.root/'package'
        self.package.mkdir()
        self.source = '1'*40
        for name in BASE_FILES:
            (self.package/name).write_text('Synthetic integrity fixture only: '+name)
        self.metadata = dict(schema=1, status='UNTESTED_CANDIDATE', source_commit=self.source,
                             rom_sha256=ROM_SHA, fixed_bank=0, romx_banks=list(range(1, 256)),
                             full_game_verified=False, m8_accepted=False,
                             files={name:digest(self.package/name) for name in BASE_FILES})
        self.save_metadata()

    def save_metadata(self):
        (self.package/'manifest.json').write_text(json.dumps(self.metadata))

    def record(self, **changes):
        directory = self.package/'validation'
        directory.mkdir(exist_ok=True)
        evidence = directory/'synthetic.json'
        evidence.write_text('{"synthetic_fixture_only":true}')
        record = dict(schema=1, status='passed', full_game_verified=True,
                      source_commit=self.source, executable_sha256=self.metadata['files']['DWM2tRecomp.exe'],
                      evidence={'synthetic.json':digest(evidence)})
        record.update(changes)
        path = self.package/'validation.json'
        path.write_text(json.dumps(record))
        self.metadata.update(status='VERIFIED_M8', full_game_verified=True, m8_accepted=True)
        self.metadata['files']['validation.json'] = digest(path)
        self.save_metadata()

    def test_candidate_preserves_unverified_status(self):
        self.assertFalse(verify_package(self.package, self.source)['full_game_verified'])

    def test_candidate_cannot_claim_verification(self):
        self.metadata['full_game_verified'] = True
        self.save_metadata()
        with self.assertRaises(ValueError):
            verify_package(self.package, self.source)

    def test_verified_requires_validation_record(self):
        self.metadata.update(status='VERIFIED_M8', full_game_verified=True, m8_accepted=True)
        self.save_metadata()
        with self.assertRaises(ValueError):
            verify_package(self.package, self.source)

    def test_record_integrity_without_execution(self):
        self.record()
        self.assertTrue(verify_package(self.package, self.source)['full_game_verified'])

    def test_record_is_bound_to_exact_executable(self):
        self.record(executable_sha256='0'*64)
        with self.assertRaises(ValueError):
            verify_package(self.package, self.source)

    def test_changed_evidence_is_refused(self):
        self.record()
        (self.package/'validation/synthetic.json').write_text('changed')
        with self.assertRaises(ValueError):
            verify_package(self.package, self.source)

    def test_evidence_cannot_escape_package(self):
        self.record(evidence={'../outside.json':'0'*64})
        with self.assertRaises(ValueError):
            verify_package(self.package, self.source)

    def test_failed_native_report_cannot_promote(self):
        path = self.root/'failed.json'
        path.write_text(json.dumps(dict(status='failed', platform='Windows', source=self.source,
                                        executable_sha256='0'*64)))
        with self.assertRaises(ValueError):
            passed_json(path, self.source, '0'*64)

    def test_skipped_native_test_cannot_promote(self):
        path = self.root/'skipped.xml'
        path.write_text('<testsuite tests="1"><testcase><skipped/></testcase></testsuite>')
        with self.assertRaises(ValueError):
            passed_ctest(path, 1)

    def test_unasserted_ending_frame_is_refused(self):
        manifest = Path(__file__).resolve().parents[1]/'tests/m8_sea_story_checkpoints.json'
        stage = json.loads(manifest.read_text())['stages'][-1]
        self.assertTrue(stage['ending_complete'])
        stage['completion_witnesses']['the-end']['frame'] = 1
        with self.assertRaises(ValueError):
            verify_ending_witnesses(manifest.parent/stage['route'], stage)

    def test_incomplete_proof_never_creates_release(self):
        destination = self.root/'release'
        with self.assertRaises(ValueError):
            package_run(self.root, self.source, '123', destination)
        self.assertFalse(destination.exists())

    def test_packaging_preserves_exact_tested_bytes(self):
        # All reports and bytes below are temporary host-contract fixtures.
        # They are never executed or retained as gameplay evidence.
        run = '123'
        folders = {name:self.root/f'M8-fresh-{name}-{run}' for name in
                   ('diagnostic', 'production', 'story', 'production-journal', 'posix-persistence')}
        for folder in folders.values():
            folder.mkdir()
        def write(folder, name, data):
            path = folder/name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data))
            return path
        executable = digest(self.package/'DWM2tRecomp.exe')
        def report(folder, name, **fields):
            return write(folder, name, dict(status='passed', platform='Windows', source=self.source,
                                           executable_sha256=executable, **fields))
        for name in ('diagnostic', 'production'):
            (folders[name]/'source.tar').write_bytes(b'Synthetic source archive, never compiled')
        archive_sha = digest(folders['diagnostic']/'source.tar')
        (folders['diagnostic']/'DWM2tRecompFull.exe').write_bytes((self.package/'DWM2tRecomp.exe').read_bytes())
        write(folders['diagnostic'], 'build-identity.json', dict(schema=1, kind='complete_aot_diagnostic_build',
            build_testing=True, fixed_bank=0, romx_banks=list(range(1,256)), rom_sha256=ROM_SHA,
            source_commit=self.source, executable_sha256=executable,
            executable_bytes=(self.package/'DWM2tRecomp.exe').stat().st_size,
            source_archive_sha256=archive_sha, source_manifest_sha256='0'*64))
        native = folders['diagnostic']/'native-results.xml'
        native.write_text('<testsuite>'+''.join('<testcase/>' for _ in range(18))+'</testsuite>')
        for name in ('production', 'posix-persistence'):
            (folders[name]/'save-io.xml').write_text('<testsuite><testcase/><testcase/></testsuite>')
        for name in ('pirate', 'village', 'farm-dancer', 'party-preparation'):
            report(folders['diagnostic'], name+'-validation.json')
        manifest = json.loads((Path(__file__).resolve().parents[1]/'tests/m8_sea_story_checkpoints.json').read_text())
        stages = [dict(stage=s['name'], frames=s['frames'], route_sha256=s['route_sha256'],
                       save_sha256=s['save_sha256'], native_returncode=0, status='passed') for s in manifest['stages']]
        stages[-1]['ending_completed'] = True
        report(folders['story'], 'story-checkpoints-validation.json', stages=stages, ending_completed=True,
               workers=4, seed_chain_audited=True, seed_chain_links=len(stages))
        for name, no_arguments in [('direct-start', True), ('profile-start', False)]:
            report(folders['production']/name, 'player-startup.json', checks=['fixture']*12, no_argument_start=no_arguments)
        report(folders['production-journal'], 'player-package.json', checks=['fixture']*21,
               package_manifest_sha256=digest(self.package/'manifest.json'))
        for name, stage, owned in [('production-journal', next(s for s in manifest['stages'] if s['name']=='raygigas-birth'),12),
                                   ('production-ending-journal',manifest['stages'][-1],17)]:
            report(folders['production-journal']/name, 'player-late-journal.json',
                   input_journal_sha256=stage['save_sha256'], quest_bytes=107, original_owned_creatures=owned,
                   fresh_process_reload=True, normal_shutdowns=2, original_p1_only=True)
        (self.package/'README.txt').write_text('Synthetic fixture\nSTART\nOriginal controls\n')
        self.metadata['files']['README.txt'] = digest(self.package/'README.txt')
        self.save_metadata()
        report(folders['production-journal'], 'player-package.json', checks=['fixture']*21,
               package_manifest_sha256=digest(self.package/'manifest.json'))
        archive = folders['production']/'DWM2t-M8-UNTESTED-test.zip'
        with zipfile.ZipFile(archive,'w') as zipped:
            for path in self.package.iterdir():
                zipped.write(path,'DWM2t-M8-UNTESTED/'+path.name)
        write(folders['production'],'build-report.json',dict(status='built_untested',source_commit=self.source,
            executable_sha256=executable,zip_sha256=digest(archive),source_archive_sha256=archive_sha))
        output = self.root/'verified-contract-only'
        zipped = package_run(self.root,self.source,run,output)
        self.assertEqual(digest(output/'DWM2t-M8/DWM2tRecomp.exe'),executable)
        with zipfile.ZipFile(zipped) as produced:
            self.assertEqual(produced.read('DWM2t-M8/DWM2tRecomp.exe'),(self.package/'DWM2tRecomp.exe').read_bytes())


if __name__ == '__main__':
    unittest.main()
