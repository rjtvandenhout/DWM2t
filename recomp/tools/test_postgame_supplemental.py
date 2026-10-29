"""Replay pinned original P1 with the accepted or an explicit fresh diagnostic.

This supplemental evidence does not certify every postgame quest/random seed,
change the accepted player, rebuild game code, or provide new binary acceptance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from m8_build_identity import BuildIdentity, load_identity

SOURCE = '3d573873ae8122cbb10fcd5d0f7ae7a33a7609ba'
EXE_SHA = 'f93b7f96212559f65f05e09f8443a224bbda7d124047047fbf53510e16ae0321'
EXE_BYTES = 725575680
ENDING_SHA = '0649c4ef78867d2e55f352ddb0fea811fea6e3cf7407f8451220cc2bf01df95d'
SOURCE_ARCHIVE_SHA = 'c75ba57b296c1b2038cd5cc3789059eb4513f79831d64cfb6f4b855a22d72722'
SOURCE_MANIFEST_SHA = '462752ad7e2fa0e658486cc5524106bb1f121a353d279418dd5cfa75d230ba99'
BUILD_RUN_ID = '40175408153'
BASELINE_VALIDATION_RUN_ID = '40183484388'
POSTGAME_STAGE_NAMES = ('key-appraisal', 'quietsea-clear', 'newlywed-gift',
                        'certified-egg', 'quest-gates', 'quietsea-reload-dungeon',
                        'npc-offers')


def digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def validate_build_identity(exe: Path, path: Path, *, fresh_build: bool = False,
                            build_run_id: str | None = None) -> tuple[BuildIdentity, dict]:
    """Bind provenance to actual files; fresh builds require an explicit opt-in."""
    raw = path.read_bytes()
    data = json.loads(raw.decode('utf-8'))
    if not isinstance(data, dict):
        raise ValueError('Diagnostic build identity must be an object')
    # The shared validator checks the exact ROM, fixed bank, all 255 ROMX banks,
    # build-testing mode, source revision and all three required SHA256 fields.
    identity = load_identity(path)
    if identity.manifest_sha256 != hashlib.sha256(raw).hexdigest():
        raise ValueError('Diagnostic build identity changed while it was read')
    if not fresh_build:
        required = {'source_commit': SOURCE, 'executable_sha256': EXE_SHA,
                    'executable_bytes': EXE_BYTES, 'source_archive_sha256': SOURCE_ARCHIVE_SHA,
                    'source_manifest_sha256': SOURCE_MANIFEST_SHA}
        if any(data.get(key) != value for key, value in required.items()):
            raise ValueError('Expected unchanged accepted diagnostic/source identity differs')
    elif build_run_id is not None and (
            not isinstance(build_run_id, str) or not re.fullmatch(r'[0-9]+', build_run_id)):
        raise ValueError('Fresh build run ID must be the actual numeric workflow run ID')
    identity.verify(exe)
    provenance = identity.report()
    provenance.update(
        diagnostic_build_mode='fresh_diagnostic' if fresh_build else 'unchanged_accepted_diagnostic',
        build_run_id=build_run_id if fresh_build else BUILD_RUN_ID,
        source_archive_sha256=data['source_archive_sha256'],
        source_manifest_sha256=data['source_manifest_sha256'],
        new_binary_accepted=False,
        accepted_baseline=dict(executable_source=SOURCE, executable_sha256=EXE_SHA,
                               executable_bytes=EXE_BYTES, build_run_id=BUILD_RUN_ID,
                               source_archive_sha256=SOURCE_ARCHIVE_SHA,
                               source_manifest_sha256=SOURCE_MANIFEST_SHA,
                               validation_run_id=BASELINE_VALIDATION_RUN_ID))
    return identity, provenance


def verify_replay_provenance(base: dict, stages: list[dict], provenance: dict,
                             platform: str, returncode: int) -> None:
    """Require seven passing native checkpoints bound to the actual build/chain."""
    if (type(returncode) is not int or returncode != 0
            or not isinstance(base, dict) or base.get('status') != 'passed'
            or base.get('platform') != platform
            or any(base.get(key) != provenance[key] for key in
                   ('executable_source', 'executable_sha256', 'executable_bytes',
                    'build_identity_sha256'))
            or base.get('seed_chain_audited') is not True
            or type(base.get('seed_chain_links')) is not int
            or base['seed_chain_links'] != len(POSTGAME_STAGE_NAMES)
            or tuple(stage['name'] for stage in stages) != POSTGAME_STAGE_NAMES):
        raise ValueError('Original replay/actual-parent chain provenance is incomplete')
    actual = base.get('stages')
    if not isinstance(actual, list) or len(actual) != len(stages):
        raise ValueError('Original replay must retain every postgame checkpoint result')
    for expected, entry in zip(stages, actual, strict=True):
        if (not isinstance(entry, dict) or entry.get('stage') != expected['name']
                or entry.get('status') != 'passed'
                or type(entry.get('native_returncode')) is not int
                or entry['native_returncode'] != 0
                or any(entry.get(key) != expected[key] for key in
                       ('frames', 'route_sha256', 'save_sha256'))):
            raise ValueError('Original replay checkpoint result differs from its pinned stage')


def equal(actual: bytes, expected: bytes, label: str) -> None:
    if actual != expected:
        first = next((i for i, pair in enumerate(zip(actual, expected)) if pair[0] != pair[1]), None)
        raise ValueError(f'{label}: bytes differ (first relative offset {first})')


def verify_buffers(saved: bytes, fresh: bytes, source: bytes, ram: bytes, expected: dict) -> dict:
    """Compare observations only; never produce or modify a game input."""
    if tuple(map(len, (saved, fresh, source, ram))) != (32768, 32768, 65536, 65536):
        raise ValueError('Incomplete original Journal and fresh Continue observations')
    owned = [i for i in range(40) if saved[i*165] in (1, 2)]
    fresh_owned = [i for i in range(40) if fresh[i*165] in (1, 2)]
    if owned != expected['owned'] or fresh_owned != owned:
        raise ValueError('All-owned roster differs from the pinned observation')
    party = expected['party']
    if 'fresh_field_mode' in expected:
        equal(ram[0xC5DB:0xC5DD], bytes(expected['fresh_field_mode']),
              'fresh original field mode')
    if not 1 <= len(party) <= 3 or len(set(party)) != len(party):
        raise ValueError('Invalid expected original party')
    party_bytes = bytes((len(party), *party))
    for label, capture, offset in [('source', source, 0xC6FD), ('fresh', ram, 0xC6FD),
                                   ('Journal', saved, 0x3C00)]:
        equal(capture[offset:offset+len(party_bytes)], party_bytes, label+' complete party')
    transitions = {}
    for item in expected.get('continue_byte_transitions', []):
        if set(item) != {'record', 'offset', 'before', 'after'}:
            raise ValueError('Continue transition must specify exact record/offset/before/after')
        record, offset, before, after = (item[k] for k in ('record', 'offset', 'before', 'after'))
        if (any(type(value) is not int for value in (record, offset, before, after))
                or record not in owned or offset not in range(165)
                or before not in range(256) or after not in range(256) or before == after
                or (record, offset) in transitions):
            raise ValueError('Invalid or duplicate exact Continue byte transition')
        if saved[record*165+offset] != before or fresh[record*165+offset] != after:
            raise ValueError('Observed Continue byte transition differs from the explicit pin')
        transitions[(record, offset)] = item
    for record in owned:
        start = record*165
        if saved[start] != (2 if record in party else 1):
            raise ValueError(f'Original active/farm status differs: record {record}')
        # Every byte is checked. Explicit source-backed transitions, when the
        # manifest pins them, require both exact observed old and new values.
        for offset in range(165):
            if fresh[start+offset] != saved[start+offset] and (record, offset) not in transitions:
                raise ValueError(f'Full owned record {record} differs at offset {offset}')
    ranges = [('quest flags', 0xCBD7, 0x3DA0, 107),
              ('all Magic Key records', 0xC707, 0x3C0A, 128),
              ('all Magic Key seeds', 0xC787, 0x3C8A, 64)]
    for label, ram_start, save_start, length in ranges:
        block = saved[save_start:save_start+length]
        equal(source[ram_start:ram_start+length], block, 'source '+label)
        equal(ram[ram_start:ram_start+length], block, 'fresh '+label)
    slots = []
    for slot in range(20):
        begin = 0x4000+405*slot
        backup = 0x6000+405*slot
        record = saved[begin:begin+405]
        equal(saved[backup:backup+405], record, f'Journal working/backup cache slot {slot}')
        equal(fresh[begin:begin+405], record, f'fresh working cache slot {slot}')
        equal(fresh[backup:backup+405], record, f'fresh backup cache slot {slot}')
        slots.append({'slot': slot, 'marker': record[0],
                      'sha256': hashlib.sha256(record).hexdigest(),
                      'descriptor_sha256': hashlib.sha256(record[1:]).hexdigest(),
                      'core_flags': record[1], 'world_cleared': bool(record[1] & 0x80),
                      'area_clear_bytes': [record[1+a-0xCD07] for a in
                                           (0xCE7E, 0xCE82, 0xCE86, 0xCE8A)]})
    for item in expected.get('cache_expectations', []):
        slot = item['slot']
        if type(slot) is not int or slot not in range(20):
            raise ValueError('Invalid pinned cache slot')
        for key in ('sha256', 'descriptor_sha256', 'marker', 'world_cleared', 'area_clear_bytes'):
            if key in item and slots[slot][key] != item[key]:
                raise ValueError(f'Pinned original cache slot {slot} {key} differs')
    random_context = None
    if 'random_context' in expected:
        context = expected['random_context']
        if (not isinstance(context, list) or len(context) != 4
                or any(type(value) is not int or value not in range(256) for value in context)
                or context[0] not in range(20) or not context[2] & 0x80):
            raise ValueError('Random context must pin exact original CC42..CC45 bytes')
        for label, capture in (('source', source), ('fresh', ram)):
            equal(capture[0xCC42:0xCC46], bytes(context), label+' random context')
        descriptor = source[0xCD07:0xCE9B]
        equal(ram[0xCD07:0xCE9B], descriptor, 'complete live random-world descriptor')
        begin = 0x4000+405*context[0]
        if saved[begin] != 0x50+context[0]:
            raise ValueError('Live random-world context has no matching original cache marker')
        equal(saved[begin+1:begin+405], descriptor, 'live descriptor and saved cache descriptor')
        descriptor_sha = hashlib.sha256(descriptor).hexdigest()
        if ('random_descriptor_sha256' in expected
                and expected['random_descriptor_sha256'] != descriptor_sha):
            raise ValueError('Pinned live random-world descriptor differs')
        random_context = {'bytes': context, 'descriptor_bytes': 404,
                          'descriptor_sha256': descriptor_sha,
                          'source_fresh_and_saved_cache_equal': True}
    return {'owned_records': owned, 'owned_bytes_each': 165, 'owned_bytes_checked': len(owned)*165,
            'continue_byte_transitions': list(transitions.values()),
            'continue_byte_transition_count': len(transitions),
            'party': party, 'quest_bytes': 107, 'key_record_bytes': 128, 'key_seed_bytes': 64,
            'key_records_hex': [saved[0x3C0A+4*i:0x3C0E+4*i].hex() for i in range(32)],
            'key_seeds_hex': [saved[0x3C8A+2*i:0x3C8C+2*i].hex() for i in range(32)],
            'cache_slots': 20, 'cache_bytes_each': 405, 'cache_four_way_equal': True,
            'cache_descriptors': slots, 'random_context': random_context}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ('exe', 'seed', 'manifest', 'output', 'build-identity'):
        parser.add_argument('--'+flag, type=Path, required=True)
    parser.add_argument('--wine', type=Path)
    parser.add_argument('--workers', type=int, choices=range(1, 5), default=1)
    parser.add_argument('--seed-bundle', type=Path,
                        help='Pinned genuine original Journals for bounded parallel replay')
    parser.add_argument('--tool-source', default=os.environ.get('GITHUB_SHA'))
    parser.add_argument('--fresh-build', action='store_true',
                        help='Validate the actual fresh complete-AOT identity instead of the historical diagnostic')
    parser.add_argument('--story-runner', type=Path,
                        default=Path(__file__).with_name('test_m8_story_checkpoints.py'))
    args = parser.parse_args()
    out = args.output.resolve()
    report = {'schema': 1, 'status': 'running',
              'scope': 'Supplemental pinned original-P1 postgame replay and fresh Continue only',
              'platform': 'Wine on Linux' if args.wine else 'Windows',
              'executable_source': None if args.fresh_build else SOURCE,
              'executable_sha256': None if args.fresh_build else EXE_SHA,
              'diagnostic_build_mode': 'fresh_diagnostic' if args.fresh_build else 'unchanged_accepted_diagnostic',
              'build_run_id': os.environ.get('GITHUB_RUN_ID') if args.fresh_build else BUILD_RUN_ID,
              'accepted_baseline_validation_run_id': BASELINE_VALIDATION_RUN_ID,
              'supplemental_validation_run_id': os.environ.get('GITHUB_RUN_ID'),
              'tooling_source_commit': args.tool_source, 'full_postgame_verified': False,
              'all_random_seeds_verified': False, 'new_binary_accepted': False,
              'accepted_package_changed': False, 'stages': []}
    report['workers'] = args.workers
    may_write = False
    try:
        if out.exists():
            raise ValueError('Supplemental replay output must be a new directory')
        if (os.name != 'nt') != bool(args.wine):
            raise ValueError('Use Windows, or explicitly supply --wine on Linux')
        if args.tool_source is not None and not re.fullmatch(r'[0-9a-f]{40}', args.tool_source):
            raise ValueError('Tooling source must be an exact commit')
        if args.workers > 1 and args.seed_bundle is None:
            raise ValueError('Parallel replay requires pinned genuine original Journals')
        exe, seed, manifest, identity_path, runner = [p.resolve(strict=True) for p in
            (args.exe, args.seed, args.manifest, args.build_identity, args.story_runner)]
        data = json.loads(manifest.read_text(encoding='utf-8'))
        if (not isinstance(data, dict) or not isinstance(data.get('stages'), list)
                or any(not isinstance(stage, dict) for stage in data['stages'])
                or tuple(stage.get('name') for stage in data['stages']) != POSTGAME_STAGE_NAMES):
            raise ValueError('Supplemental manifest must retain all seven pinned original-P1 stages')
        identity, provenance = validate_build_identity(
            exe, identity_path, fresh_build=args.fresh_build,
            build_run_id=os.environ.get('GITHUB_RUN_ID'))
        report.update(provenance)
        if seed.stat().st_size != 32768 or digest(seed) != ENDING_SHA or data['seed_sha256'] != ENDING_SHA:
            raise ValueError('Initial input must be the genuine accepted ending Journal')
        immutable = {p: digest(p) for p in (exe, seed, manifest, identity_path, runner)}
        report.update(manifest_sha256=immutable[manifest], build_identity_sha256=immutable[identity_path],
                      runner_sha256=immutable[runner], seed_sha256=ENDING_SHA,
                      source_archive_sha256=provenance['source_archive_sha256'],
                      source_manifest_sha256=provenance['source_manifest_sha256'])
        command = [sys.executable, str(runner), '--exe', str(exe), '--seed', str(seed),
                   '--manifest', str(manifest), '--output', str(out),
                   '--build-identity', str(identity_path)]
        if args.wine:
            command += ['--wine', str(args.wine.resolve(strict=True))]
        command += ['--workers', str(args.workers)]
        if args.seed_bundle:
            bundle = args.seed_bundle.resolve(strict=True)
            immutable[bundle] = digest(bundle)
            report['seed_bundle_sha256'] = immutable[bundle]
            command += ['--seed-bundle', str(bundle)]
        report['command'] = command
        # The existing runner creates output exclusively, uses actual new parent
        # Saves for every child, checks hashes/P1/screens/PCM, and preserves logs.
        may_write = True
        result = subprocess.run(command, check=False)
        report['runner_returncode'] = result.returncode
        if result.returncode:
            raise ValueError(f'Original checkpoint replay failed: {result.returncode}')
        base = json.loads((out/'story-checkpoints-validation.json').read_text(encoding='utf-8'))
        verify_replay_provenance(base, data['stages'], provenance,
                                 report['platform'], result.returncode)
        report['seed_chain_links'] = base['seed_chain_links']
        for expected in data['stages']:
            native = out/expected['name']/'native'
            paths = [native/'checkpoint.sav', native/'fresh_continue/m8_0.sram',
                     native/'m8_0.ram', native/'fresh_continue/m8_0.ram']
            if digest(paths[0]) != expected['save_sha256']:
                raise ValueError('New original Journal differs from the pinned observation')
            entry = verify_buffers(*(p.read_bytes() for p in paths), expected)
            entry.update(stage=expected['name'], save_sha256=expected['save_sha256'],
                         observation_sha256={p.relative_to(out).as_posix(): digest(p) for p in paths})
            report['stages'].append(entry)
        for path, before in immutable.items():
            if digest(path) != before:
                raise ValueError('Supplemental immutable input changed: '+str(path))
        identity.verify(exe)
        report['status'] = 'passed'
        print('POSTGAME_SUPPLEMENTAL_PASS', provenance['diagnostic_build_mode'],
              'original_P1 fresh_Continue')
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        report.update(status='failed', error=str(error), error_type=type(error).__name__)
        print('POSTGAME_SUPPLEMENTAL_FAIL', error)
        return 1
    finally:
        if may_write:
            out.mkdir(parents=True, exist_ok=True)
            with (out/'postgame-supplemental-validation.json').open('x', encoding='utf-8') as stream:
                json.dump(report, stream, indent=2)
                stream.write('\n')


if __name__ == '__main__':
    raise SystemExit(main())
