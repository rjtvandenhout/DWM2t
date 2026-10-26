"""Synthetic packaging contracts only; no fixture is executed as game evidence."""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import package_verified_m8 as packaging
from test_postgame_supplemental import POSTGAME_STAGE_NAMES, verify_buffers


def sha(data):
    return hashlib.sha256(data).hexdigest()


def put(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def write_json(path, data):
    return put(path, (json.dumps(data, indent=2)+'\n').encode())


class FullRomSourceGateContracts(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source, self.run = 'a'*40, '123'
        self.candidate = self.root/'candidate'
        self.candidate.mkdir()
        put(self.candidate/'DWM2tRecomp.exe', b'Synthetic packaging-contract bytes, never executed.')
        self.archive = self.root/'source.tar'
        self.files = {name: b'// Synthetic source-contract bytes.\n' for name in (
            packaging.FULL_ROM_HEADER, packaging.POSTGAME_MANIFEST,
            'recomp/tools/test_m8_story_checkpoints.py',
            'recomp/tools/test_player_local_link.py', 'recomp/tools/test_player_late_journal.py')}
        self.save_sources()

    def save_sources(self, *, comment=None, extra=None):
        self.inputs = {name:sha(data) for name, data in self.files.items()}
        self.manifest = write_json(self.candidate/'source-manifest.json', self.inputs)
        self.identity = dict(source_manifest_sha256=sha(self.manifest.read_bytes()))
        with tarfile.open(self.archive, 'w:', format=tarfile.PAX_FORMAT,
                          pax_headers={'comment':self.source if comment is None else comment}) as archive:
            for name, data in list(self.files.items()) + (extra or []):
                info = tarfile.TarInfo(name)
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))

    def verify(self):
        return packaging.full_rom_source_inputs(self.candidate, self.archive, self.source, self.identity)

    def test_exact_new_inventory_and_archive_are_bound(self):
        inputs, retained = self.verify()
        self.assertEqual(inputs, self.inputs)
        self.assertEqual(retained[packaging.POSTGAME_MANIFEST], self.files[packaging.POSTGAME_MANIFEST])

    def test_historical_plaintext_contract_fixture_retains_old_gates(self):
        self.manifest.write_text('Synthetic integrity fixture only: source-manifest.json')
        self.archive.write_bytes(b'Synthetic source archive, never compiled')
        self.assertIsNone(self.verify())
        fields, evidence = packaging.verify_full_rom_gates(
            self.root, self.source, self.run, 'b'*64, self.identity, self.archive,
            self.candidate, ending=self.root/'not-required.sav', ending_sha='c'*64)
        self.assertEqual((fields, evidence), ({}, {}))

    def test_historical_real_inventory_without_header_retains_old_gates(self):
        del self.files[packaging.FULL_ROM_HEADER]
        self.save_sources()
        self.assertIsNone(self.verify())

    def test_new_header_requires_readable_source_tar(self):
        self.archive.write_bytes(b'Not an actual source tar')
        with self.assertRaises(ValueError):
            self.verify()

    def test_deleting_header_from_manifest_cannot_bypass_new_gates(self):
        del self.inputs[packaging.FULL_ROM_HEADER]
        write_json(self.manifest, self.inputs)
        self.identity['source_manifest_sha256'] = sha(self.manifest.read_bytes())
        with self.assertRaises(ValueError):
            self.verify()

    def test_manifest_is_bound_to_diagnostic_identity(self):
        self.identity['source_manifest_sha256'] = '0'*64
        with self.assertRaises(ValueError):
            self.verify()

    def test_actual_archived_bytes_must_match_input_map(self):
        self.inputs[packaging.FULL_ROM_HEADER] = '0'*64
        write_json(self.manifest, self.inputs)
        self.identity['source_manifest_sha256'] = sha(self.manifest.read_bytes())
        with self.assertRaises(ValueError):
            self.verify()

    def test_actual_git_archive_commit_is_required(self):
        self.save_sources(comment='d'*40)
        with self.assertRaises(ValueError):
            self.verify()

    def test_duplicate_or_escaping_archive_members_are_refused(self):
        for name in (packaging.FULL_ROM_HEADER, '../escape.txt'):
            with self.subTest(name=name):
                self.save_sources(extra=[(name, b'bad')])
                with self.assertRaises(ValueError):
                    self.verify()

    def test_new_source_requires_windows_and_linux_contract_evidence(self):
        with self.assertRaises(ValueError):
            packaging.verify_full_rom_gates(self.root, self.source, self.run, 'b'*64,
                self.identity, self.archive, self.candidate,
                ending=self.root/'unused.sav', ending_sha='c'*64)

    def aggregate(self, *, platforms=('Windows', 'Linux')):
        reports = []
        for artifact in ('production', 'posix-persistence'):
            folder = self.root/f'M8-fresh-{artifact}-{self.run}'
            reports.append(write_json(folder/'runtime-core-validation.json', {}))
            put(folder/'runtime-core-tests.xml', b'<synthetic-contract/>')
        gui = write_json(self.root/f'M8-fresh-production-journal-{self.run}'/'player-local-link.json', {})
        with patch('full_rom_validation.verify_runtime_core', side_effect=[
                    dict(platform=value, tests=5) for value in platforms]) as runtime, \
                patch.object(packaging, 'verify_postgame_gate', return_value=(
                    dict(postgame_checkpoints=7, postgame_replayed_manifest_sha256=
                         self.inputs[packaging.POSTGAME_MANIFEST]), {'postgame-validation.json':gui})), \
                patch.object(packaging, 'verify_local_link_gate', return_value={}):
            result = packaging.verify_full_rom_gates(self.root, self.source, self.run, 'b'*64,
                self.identity, self.archive, self.candidate, ending=self.root/'unused.sav', ending_sha='c'*64)
        return result, runtime.call_args_list

    def test_both_runtime_verifiers_receive_actual_source_map_and_evidence_is_retained(self):
        (fields, evidence), calls = self.aggregate()
        self.assertEqual(fields['hardware_contract_tests'], {'Windows':5, 'Linux':5})
        self.assertEqual(fields['postgame_checkpoints'], 7)
        self.assertTrue(fields['local_link_host_verified'])
        self.assertFalse(fields['original_linked_transactions_verified'])
        self.assertEqual(len(calls), 2)
        for call in calls:
            self.assertEqual(call.kwargs['source_manifest'], self.inputs)
            self.assertEqual(call.args[2], self.source)
        for name in ('windows-runtime-core.json', 'windows-runtime-core.xml',
                     'linux-runtime-core.json', 'linux-runtime-core.xml',
                     'production-local-link.json', 'full-rom-source-manifest.json',
                     'postgame-manifest.json', 'postgame-replay-manifest.json'):
            self.assertTrue(evidence[name].is_file(), name)

    def test_linux_evidence_cannot_replace_native_windows_contracts(self):
        with self.assertRaises(ValueError):
            self.aggregate(platforms=('Linux', 'Linux'))


class FreshPostgamePackageContracts(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source, self.run = 'a'*40, '123'
        self.folder = self.root/'postgame'
        self.ending = put(self.root/'ending.sav', bytes(32768))
        self.ending_sha = sha(self.ending.read_bytes())
        self.identity = dict(executable_sha256='b'*64, executable_bytes=100,
                             source_archive_sha256='c'*64, source_manifest_sha256='d'*64,
                             build_identity_sha256='e'*64)
        self.pins = dict(seed_sha256=self.ending_sha, stages=[])
        self.report = dict(schema=1, status='passed', platform='Windows',
            executable_source=self.source, diagnostic_build_mode='fresh_diagnostic',
            build_run_id=self.run, supplemental_validation_run_id=self.run,
            tooling_source_commit=self.source, scope=packaging.POSTGAME_SCOPE,
            seed_sha256=self.ending_sha, runner_returncode=0, seed_chain_links=7,
            full_postgame_verified=False, all_random_seeds_verified=False,
            new_binary_accepted=False, accepted_package_changed=False, workers=1,
            **self.identity, stages=[])
        self.base = dict(status='passed', platform='Windows', executable_source=self.source,
            seed_chain_audited=True, seed_chain_links=7, stages=[], **self.identity)
        parent = self.ending.read_bytes()
        for index, name in enumerate(POSTGAME_STAGE_NAMES):
            # Synthetic observations exercise byte contracts only. They never
            # enter a Runtime, build, save bundle or acceptance artifact.
            saved = bytearray(32768)
            saved[0] = 2
            saved[0x3C00:0x3C02] = bytes((1, 0))
            saved[0x3FFF] = index+1
            ram = bytearray(65536)
            ram[0xC6FD:0xC6FF] = bytes((1, 0))
            route = b'# Synthetic route contract; never run.\n'
            expected = dict(name=name, route=name+'.txt', route_sha256=sha(route),
                            save_sha256=sha(saved), frames=index+1, party=[0], owned=[0])
            if index:
                expected['seed_stage'] = POSTGAME_STAGE_NAMES[index-1]
            self.pins['stages'].append(expected)
            native = self.folder/name/'native'
            captures = [put(native/'checkpoint.sav', saved),
                        put(native/'fresh_continue/m8_0.sram', saved),
                        put(native/'m8_0.ram', ram), put(native/'fresh_continue/m8_0.ram', ram)]
            put(self.folder/name/'seed-copy.sav', parent)
            put(self.folder/name/expected['route'], route)
            parent = bytes(saved)
            observation = verify_buffers(saved, saved, ram, ram, expected)
            observation.update(stage=name, save_sha256=expected['save_sha256'],
                observation_sha256={p.relative_to(self.folder).as_posix():sha(p.read_bytes()) for p in captures})
            self.report['stages'].append(observation)
            self.base['stages'].append(dict(stage=name, status='passed', native_returncode=0,
                **{key:expected[key] for key in ('frames', 'route_sha256', 'save_sha256')}))
        self.manifest = write_json(self.root/'pins.json', self.pins)
        runner = b'# Synthetic runner input.\n'
        self.archived = {packaging.POSTGAME_MANIFEST:self.manifest.read_bytes(),
                         'recomp/tools/test_m8_story_checkpoints.py':runner}
        self.inputs = {packaging.POSTGAME_MANIFEST:sha(self.manifest.read_bytes())}
        self.report.update(manifest_sha256=self.inputs[packaging.POSTGAME_MANIFEST], runner_sha256=sha(runner))

    def verify(self):
        write_json(self.folder/'postgame-supplemental-validation.json', self.report)
        write_json(self.folder/'story-checkpoints-validation.json', self.base)
        return packaging.verify_postgame_gate(self.folder, self.source, self.run,
            self.identity, self.inputs, self.archived, self.ending, self.ending_sha, self.manifest)

    def test_seven_ordered_fresh_saves_and_all_owned_cache_bytes_are_reaudited(self):
        fields, evidence = self.verify()
        self.assertEqual(fields['postgame_checkpoints'], 7)
        self.assertEqual(fields['postgame_seed_chain_links'], 7)
        self.assertTrue(fields['postgame_owned_and_cache_verified'])
        self.assertEqual(len(evidence), 2)

    def test_stale_or_incomplete_fresh_provenance_is_refused(self):
        changes = dict(diagnostic_build_mode='unchanged_accepted_diagnostic', build_run_id='122',
            executable_sha256='0'*64, source_archive_sha256='0'*64, source_manifest_sha256='0'*64,
            build_identity_sha256='0'*64, tooling_source_commit='0'*40, manifest_sha256='0'*64,
            scope='All postgame verified', runner_sha256='0'*64, full_postgame_verified=True,
            all_random_seeds_verified=True, runner_returncode=False, seed_chain_links=6)
        for key, value in changes.items():
            with self.subTest(key=key):
                before = self.report[key]
                self.report[key] = value
                with self.assertRaises(ValueError):
                    self.verify()
                self.report[key] = before

    def test_reordered_persistence_stages_are_refused(self):
        self.report['stages'].reverse()
        with self.assertRaises(ValueError):
            self.verify()

    def test_actual_parent_save_copy_is_required(self):
        put(self.folder/POSTGAME_STAGE_NAMES[1]/'seed-copy.sav', bytes(32768))
        with self.assertRaises(ValueError):
            self.verify()

    def test_passing_summary_cannot_hide_changed_cache_capture(self):
        path = self.folder/POSTGAME_STAGE_NAMES[0]/'native/fresh_continue/m8_0.sram'
        data = bytearray(path.read_bytes())
        data[0x4001] = 1
        put(path, data)
        self.report['stages'][0]['observation_sha256'][path.relative_to(self.folder).as_posix()] = sha(data)
        with self.assertRaises(ValueError):
            self.verify()

    def test_passing_summary_cannot_hide_changed_owned_capture(self):
        path = self.folder/POSTGAME_STAGE_NAMES[0]/'native/fresh_continue/m8_0.sram'
        data = bytearray(path.read_bytes())
        data[100] = 1
        put(path, data)
        self.report['stages'][0]['observation_sha256'][path.relative_to(self.folder).as_posix()] = sha(data)
        with self.assertRaises(ValueError):
            self.verify()

    def test_unreported_actual_route_changes_are_refused(self):
        put(self.folder/POSTGAME_STAGE_NAMES[0]/self.pins['stages'][0]['route'], b'changed route\n')
        with self.assertRaises(ValueError):
            self.verify()

    def test_local_manifest_permits_checkout_crlf_only(self):
        self.manifest.write_bytes(self.manifest.read_bytes().replace(b'\n', b'\r\n'))
        self.report['manifest_sha256'] = sha(self.manifest.read_bytes())
        self.verify()
        self.manifest.write_bytes(self.manifest.read_bytes()+b' ')
        with self.assertRaises(ValueError):
            self.verify()

    def test_missing_original_replay_chain_audit_is_refused(self):
        self.base['seed_chain_audited'] = False
        with self.assertRaises(ValueError):
            self.verify()


class LocalLinkPackageContracts(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source, self.executable = 'a'*40, 'b'*64
        data = bytearray(32768)
        data[0] = 2
        self.ending = put(self.root/'original-ending.sav', data)
        self.seed = sha(data)
        self.path = self.root/'player-local-link.json'
        self.saves = [put(self.root/'independent'/f'ending-player{n}.sav', data) for n in (1, 2)]
        self.report = dict(schema=1, kind='production_local_link_gui', status='passed',
            source=self.source, executable_sha256=self.executable, executable_bytes=100,
            platform='Windows', players=2, input_journal_sha256=self.seed, input_journal_bytes=32768,
            original_p1_only=True, game_memory_edits=False, serial_protocol_success_verified=False,
            full_game_verified=False, fresh_process_reload=True, normal_shutdowns=2,
            shutdown_players=[2, 1], input_isolation_verified=True, game_windows_per_launch=2,
            normal_close_save_integrity_verified=True, quest_bytes=107, original_owned_creatures=1,
            window_pairs=[], input_events=[], saved_journals={}, checks=[
                'players_have_distinct_original_journal_files', 'genuine_original_ending_journal_is_pinned',
                'original_ending_quest_flag_is_present', 'competing-player2_refused_for_expected_reason',
                'peer_lock_rejection_keeps_both_original_games_running',
                'competing_process_does_not_replace_player2_save',
                'source_journal_and_production_executable_are_unchanged',
                'both_games_leave_no_pending_save_temporaries'])
        for index, (round_name, closing) in enumerate((('continue', 2), ('reload', 1))):
            pid = index+10
            windows = [dict(pid=pid, hwnd=pid*10+player, kind='DWM2tRecompWindow',
                            title=f'DWM2t - Player {player} (local link)') for player in (1, 2)]
            self.report['window_pairs'].append(dict(round=round_name, pid=pid, windows=windows))
            self.report['input_events'].extend(dict(player=n, hwnd=w['hwnd'], foreground_hwnd=w['hwnd'])
                                               for n, w in enumerate(windows, 1))
            self.report['saved_journals'][round_name] = [dict(player=n, bytes=32768, sha256=self.seed,
                original_roster_and_107_quest_bytes_preserved=True) for n in (1, 2)]
            self.report['checks'].extend((round_name+'_two_distinct_windows_share_one_owned_process',
                round_name+'_player1_inputs_did_not_continue_or_open_player2_menu',
                round_name+'_player2_inputs_did_not_open_player1_menu',
                round_name+'_both_original_rosters_and_quest_bytes_preserved',
                f'{round_name}_close_player{closing}_normally_closes_both_windows'))
            for player in (1, 2):
                self.report['checks'].extend(f'{round_name}_player{player}_'+suffix for suffix in (
                    'native_save_lock_held', 'native_save_lock_released',
                    'original_ending_continue', 'original_ending_party_hud'))

    def verify(self):
        write_json(self.path, self.report)
        return packaging.verify_local_link_gate(self.path, self.source, self.executable,
                                                100, self.ending, self.seed)

    def test_two_player_host_can_pass_without_claiming_original_link_transaction(self):
        self.assertFalse(self.verify()['serial_protocol_success_verified'])

    def test_source_platform_identity_and_lifecycle_are_strict(self):
        for key, value in dict(platform='Wine on Linux', source='0'*40,
                executable_sha256='0'*64, input_journal_sha256='0'*64,
                fresh_process_reload=False, normal_shutdowns=1,
                input_isolation_verified=False, serial_protocol_success_verified=True).items():
            with self.subTest(key=key):
                before = self.report[key]
                self.report[key] = value
                with self.assertRaises(ValueError):
                    self.verify()
                self.report[key] = before

    def test_reload_in_same_process_is_not_accepted_as_fresh(self):
        self.report['window_pairs'][1]['pid'] = self.report['window_pairs'][0]['pid']
        with self.assertRaises(ValueError):
            self.verify()

    def test_missing_lock_or_original_continue_check_is_refused(self):
        self.report['checks'].remove('reload_player2_native_save_lock_held')
        with self.assertRaises(ValueError):
            self.verify()

    def test_unfocused_or_missing_player_inputs_are_refused(self):
        self.report['input_events'][0]['foreground_hwnd'] = 0
        with self.assertRaises(ValueError):
            self.verify()

    def test_both_players_cannot_share_a_journal_inode(self):
        self.saves[1].unlink()
        os.link(self.saves[0], self.saves[1])
        with self.assertRaises(ValueError):
            self.verify()

    def test_actual_saved_bytes_are_bound_to_fresh_reload_report(self):
        data = bytearray(self.saves[1].read_bytes())
        data[-1] = 1
        put(self.saves[1], data)
        with self.assertRaises(ValueError):
            self.verify()


if __name__ == '__main__':
    unittest.main()
