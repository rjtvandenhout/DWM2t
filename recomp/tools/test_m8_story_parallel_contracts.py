"""Parallel orchestration contracts; synthetic fixtures never execute a game."""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from test_m8_story_checkpoints import (audit_journal_chain, bundle_hashes,
                                      load_seed_bundle, main, replay_prepared)


def sha(saved: bytes) -> str:
    return hashlib.sha256(saved).hexdigest()


class OriginalJournalContracts(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.saved = {'initial.sav': b'I'*32768, 'first.sav': b'A'*32768,
                      'second.sav': b'B'*32768}
        self.data = dict(seed_sha256=sha(self.saved['initial.sav']), stages=[
            dict(name='first', frames=20, save_sha256=sha(self.saved['first.sav'])),
            dict(name='second', frames=10, seed_stage='first',
                 save_sha256=sha(self.saved['second.sav']))])
        self.bundle = self.root/'journals.tar.xz'
        self.destination = self.root/'seed-inputs'

    def archive(self, entries=None):
        if entries is None:
            entries = list(self.saved.items())
        with tarfile.open(self.bundle, 'w:xz') as archive:
            for name, saved in entries:
                member = tarfile.TarInfo(name)
                member.size = len(saved)
                archive.addfile(member, io.BytesIO(saved))

    def refused_without_extracting(self, entries):
        self.archive(entries)
        with self.assertRaises(ValueError):
            load_seed_bundle(self.bundle, self.data, self.destination)
        self.assertFalse(self.destination.exists())

    def test_only_exact_pinned_journals_are_extracted(self):
        self.archive()
        original = self.bundle.read_bytes()
        paths = load_seed_bundle(self.bundle, self.data, self.destination)
        self.assertEqual(set(paths), {'initial', 'first', 'second'})
        self.assertEqual(paths['first'].read_bytes(), self.saved['first.sav'])
        self.assertEqual(self.bundle.read_bytes(), original)

    def test_missing_original_journal_is_refused_before_extraction(self):
        self.refused_without_extracting(list(self.saved.items())[:-1])

    def test_extra_member_is_refused_before_extraction(self):
        self.refused_without_extracting([*self.saved.items(), ('untracked.sav', b'Z'*32768)])

    def test_path_traversal_cannot_escape_new_directory(self):
        self.refused_without_extracting([*self.saved.items(), ('../outside.sav', b'Z'*32768)])
        self.assertFalse((self.root/'outside.sav').exists())

    def test_wrong_size_is_refused_before_extraction(self):
        self.refused_without_extracting([('initial.sav', b'I'*32767),
                                        *list(self.saved.items())[1:]])

    def test_changed_bytes_with_correct_size_are_refused(self):
        self.refused_without_extracting([('initial.sav', b'Z'*32768),
                                        *list(self.saved.items())[1:]])

    def test_duplicate_tar_entry_is_refused(self):
        self.refused_without_extracting([*self.saved.items(), ('first.sav', self.saved['first.sav'])])

    def test_links_are_not_journal_files(self):
        self.archive()
        with tarfile.open(self.bundle, 'w:xz') as archive:
            member = tarfile.TarInfo('initial.sav')
            member.type = tarfile.SYMTYPE
            member.linkname = '../outside.sav'
            archive.addfile(member)
        with self.assertRaises(ValueError):
            load_seed_bundle(self.bundle, self.data, self.destination)
        self.assertFalse(self.destination.exists())

    def test_existing_seed_directory_is_never_overwritten(self):
        self.archive()
        self.destination.mkdir()
        retained = self.destination/'retained.txt'
        retained.write_text('preserve')
        with self.assertRaises(ValueError):
            load_seed_bundle(self.bundle, self.data, self.destination)
        self.assertEqual(retained.read_text(), 'preserve')

    def test_future_parent_is_not_a_valid_original_chain(self):
        self.data['stages'][0]['seed_stage'] = 'second'
        with self.assertRaises(ValueError):
            bundle_hashes(self.data)

    def test_case_aliases_cannot_collide_on_windows(self):
        self.data['stages'][1]['name'] = 'FIRST'
        with self.assertRaises(ValueError):
            bundle_hashes(self.data)

    def chain(self):
        initial = self.root/'fresh-preparation.sav'
        initial.write_bytes(self.saved['initial.sav'])
        completed = {}
        for stage in self.data['stages']:
            folder = self.root/stage['name']
            (folder/'native').mkdir(parents=True)
            source = stage.get('seed_stage', 'initial')+'.sav'
            (folder/'seed-copy.sav').write_bytes(self.saved[source])
            produced = folder/'native/checkpoint.sav'
            produced.write_bytes(self.saved[stage['name']+'.sav'])
            completed[stage['name']] = produced
        return initial, completed

    def test_actual_new_parent_outputs_are_linked_to_each_input(self):
        initial, completed = self.chain()
        self.assertEqual(audit_journal_chain(self.data, self.root, initial, completed), 2)

    def test_changed_child_seed_fails_even_when_outputs_match_goldens(self):
        initial, completed = self.chain()
        (self.root/'second/seed-copy.sav').write_bytes(b'Z'*32768)
        with self.assertRaises(ValueError):
            audit_journal_chain(self.data, self.root, initial, completed)

    def test_changed_new_parent_and_child_cannot_replace_a_pinned_link(self):
        initial, completed = self.chain()
        completed['first'].write_bytes(b'Z'*32768)
        (self.root/'second/seed-copy.sav').write_bytes(b'Z'*32768)
        with self.assertRaises(ValueError):
            audit_journal_chain(self.data, self.root, initial, completed)

    def test_missing_replayed_parent_never_passes_chain_audit(self):
        initial, completed = self.chain()
        del completed['first']
        with self.assertRaises(ValueError):
            audit_journal_chain(self.data, self.root, initial, completed)

    def test_initial_branch_is_linked_to_the_fresh_preparation_seed(self):
        initial, completed = self.chain()
        (self.root/'first/seed-copy.sav').write_bytes(b'Z'*32768)
        with self.assertRaises(ValueError):
            audit_journal_chain(self.data, self.root, initial, completed)

    def main_inputs(self):
        initial = self.root/'fresh-preparation.sav'
        initial.write_bytes(self.saved['initial.sav'])
        executable = self.root/'never-executed.exe'
        executable.write_text('Synthetic orchestration fixture, not an executable')
        wine = self.root/'never-executed-wine'
        wine.touch()
        for stage in self.data['stages']:
            route = self.root/(stage['name']+'.txt')
            route.write_text('# Synthetic orchestration fixture only\n')
            stage.update(route=route.name, route_sha256=sha(route.read_bytes()))
        manifest = self.root/'manifest.json'
        manifest.write_text(json.dumps(self.data))
        output = self.root/'orchestration-output'
        arguments = ['checkpoint-test', '--exe', str(executable), '--seed', str(initial),
                     '--manifest', str(manifest), '--output', str(output), '--wine', str(wine)]
        identity = SimpleNamespace(sha256=sha(executable.read_bytes()),
                                   verify=lambda path: None,
                                   report=lambda: {'synthetic_contract_only':True})
        return arguments, output, identity

    def test_default_remains_sequential_with_the_actual_previous_output(self):
        arguments, output, identity = self.main_inputs()
        called = []
        def synthetic(expected, copied, native, command, entry, timeout=1200):
            self.assertEqual(timeout, 1200)
            self.assertEqual(copied.read_bytes(), self.saved[expected.get('seed_stage','initial')+'.sav'])
            if expected['name']=='second':
                self.assertEqual(called, ['first'])
                self.assertEqual(copied.read_bytes(), (output/'first/native/checkpoint.sav').read_bytes())
            called.append(expected['name'])
            native.mkdir()
            saved = native/'checkpoint.sav'
            saved.write_bytes(self.saved[expected['name']+'.sav'])
            entry['status'] = 'passed'
            return saved
        with patch('sys.argv', arguments), patch('test_m8_story_checkpoints.load_identity',return_value=identity), \
                patch('test_m8_story_checkpoints.replay_checkpoint',side_effect=synthetic):
            self.assertEqual(main(), 0)
        report = json.loads((output/'story-checkpoints-validation.json').read_text())
        self.assertEqual(report['workers'],1)
        self.assertTrue(report['seed_chain_audited'])
        self.assertEqual(called,['first','second'])
        self.assertNotIn('seed_bundle_sha256',report)

    def test_parallel_flag_never_passes_a_mismatched_new_parent(self):
        arguments, output, identity = self.main_inputs()
        self.archive()
        arguments += ['--workers','2','--seed-bundle',str(self.bundle)]
        def synthetic(expected, copied, native, command, entry, timeout=1800):
            native.mkdir()
            saved = native/'checkpoint.sav'
            saved.write_bytes(b'Z'*32768 if expected['name']=='first' else self.saved['second.sav'])
            entry['status'] = 'passed'
            return saved
        with patch('sys.argv', arguments), patch('test_m8_story_checkpoints.load_identity',return_value=identity), \
                patch('test_m8_story_checkpoints.replay_checkpoint',side_effect=synthetic):
            self.assertEqual(main(), 1)
        report = json.loads((output/'story-checkpoints-validation.json').read_text())
        self.assertEqual(report['status'],'failed')
        self.assertFalse(report['seed_chain_audited'])

    def test_parallel_without_bundle_never_reaches_a_native_process(self):
        arguments, output, identity = self.main_inputs()
        with patch('sys.argv', arguments+['--workers','4']), \
                patch('test_m8_story_checkpoints.subprocess.run') as native:
            self.assertEqual(main(),1)
            native.assert_not_called()
        report = json.loads((output/'story-checkpoints-validation.json').read_text())
        self.assertEqual(report['status'],'failed')
        self.assertFalse(report['seed_chain_audited'])


class BoundedReplayContracts(unittest.TestCase):
    def plans(self):
        return [dict(expected=dict(name=name, frames=frames), copied=Path(name+'.sav'),
                     native=Path(name)/'native', command=['never-executed'],
                     entry=dict(stage=name, status='pending'))
                for name, frames in [('short', 1), ('longest', 4), ('medium', 2), ('long', 3)]]

    def test_two_workers_start_longest_first_without_reordering_report(self):
        plans = self.plans()
        barrier = threading.Barrier(2, timeout=3)
        lock = threading.Lock()
        observed, active, peak = [], 0, 0
        def synthetic(expected, copied, native, command, entry, timeout):
            nonlocal active, peak
            self.assertEqual(timeout, 1800)
            with lock:
                observed.append(expected['name'])
                active += 1
                peak = max(active, peak)
            barrier.wait()
            with lock:
                active -= 1
            entry['status'] = 'passed'
            return native/'checkpoint.sav'
        with patch('test_m8_story_checkpoints.replay_checkpoint', side_effect=synthetic):
            completed = replay_prepared(plans, 2)
        self.assertEqual(peak, 2)
        self.assertEqual(set(observed[:2]), {'longest', 'long'})
        self.assertEqual([plan['entry']['stage'] for plan in plans], ['short', 'longest', 'medium', 'long'])
        self.assertEqual(set(completed), {'short', 'longest', 'medium', 'long'})

    def test_a_failure_preserves_all_other_completed_results(self):
        plans = self.plans()
        attempted = set()
        lock = threading.Lock()
        def synthetic(expected, copied, native, command, entry, timeout):
            with lock:
                attempted.add(expected['name'])
            if expected['name'] == 'longest':
                entry['native_returncode'] = 230
                raise RuntimeError('Synthetic native failure, not a game result')
            entry['status'] = 'passed'
            return native/'checkpoint.sav'
        with patch('test_m8_story_checkpoints.replay_checkpoint', side_effect=synthetic):
            with self.assertRaises(RuntimeError):
                replay_prepared(plans, 2)
        self.assertEqual(len(attempted), 4)
        self.assertEqual(plans[1]['entry']['status'], 'failed')
        self.assertEqual(plans[1]['entry']['native_returncode'], 230)
        self.assertIn('Synthetic native failure', plans[1]['entry']['error_traceback'])
        self.assertTrue(all(plan['entry']['status']=='passed' for plan in plans if plan is not plans[1]))

    def test_more_than_four_workers_is_refused_before_launch(self):
        with patch('test_m8_story_checkpoints.replay_checkpoint') as native:
            with self.assertRaises(ValueError):
                replay_prepared(self.plans(), 5)
            native.assert_not_called()


if __name__ == '__main__':
    unittest.main()
