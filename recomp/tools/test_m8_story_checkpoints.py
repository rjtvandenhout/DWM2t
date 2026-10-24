"""Replay observed original story Journals and verify fresh Continue.

The manifest describes evidence already obtained through original P1 input.
It supplies assertions only; it never writes game state or interprets opcodes.
Passing these checkpoints does not certify the ending or final M8 acceptance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

from test_m8_farm_dancer import EXE_SHA, check_file, digest


def verify_creatures(native: Path, seed: Path, expected: dict) -> None:
    saved = (native / 'checkpoint.sav').read_bytes()
    fresh = (native / 'fresh_continue/m8_0.sram').read_bytes()
    source = (native / 'm8_0.ram').read_bytes()
    ram = (native / 'fresh_continue/m8_0.ram').read_bytes()
    if tuple(map(len, (saved, fresh, source, ram))) != (32768, 32768, 65536, 65536):
        raise ValueError('Incomplete original Journal/Continue capture')
    party = expected['party']
    if ram[0xC6FD:0xC701] != bytes((len(party), *party)):
        raise ValueError('Original active party differs after Continue')
    if [i for i in range(40) if saved[i*0xA5] in (1, 2)] != expected['owned']:
        raise ValueError('Original owned roster differs')
    initial = seed.read_bytes()
    retained = {int(old): new for old, new in expected.get('retained_records', {}).items()}
    if retained:
        initial_owned = {i for i in range(40) if initial[i*0xA5] in (1, 2)}
        parents = set(expected['bred_parents'])
        if (set(retained) | parents != initial_owned or set(retained) & parents or
                len(set(retained.values())) != len(retained) or
                not set(retained.values()).issubset(expected['owned'])):
            raise ValueError('Incomplete original roster compaction witness')
        for old, new in retained.items():
            if saved[new*0xA5+1:new*0xA5+13] != initial[old*0xA5+1:old*0xA5+13]:
                raise ValueError(f'Previously owned name/species differs: {old} -> {new}')
    for record in expected['owned']:
        base = record * 0xA5
        if saved[base] != (2 if record in party else 1):
            raise ValueError(f'Original farm/active status differs: {record}')
        for start, end in ((0x0B, 0x0D), (0x34, 0x3C), (0x55, 0x6B),
                           *expected.get('persistent_ranges', [])):
            if saved[base+start:base+end] != fresh[base+start:base+end]:
                raise ValueError(f'Creature persistence differs: {record}, {start:02x}')
        if not retained and initial[base] in (1, 2) and record not in expected.get('bred_parents', []):
            if saved[base+11:base+13] != initial[base+11:base+13]:
                raise ValueError(f'Previously owned species differs: {record}')
    for record, species in expected.get('species', {}).items():
        base = int(record) * 0xA5
        if int.from_bytes(saved[base+11:base+13], 'little') != species:
            raise ValueError(f'Observed species differs: {record}')
    for record, skills in expected.get('learned_skills', {}).items():
        base = int(record) * 0xA5
        if list(saved[base+0x34:base+0x3C]) != skills:
            raise ValueError(f'Original learned skill list differs: {record}')
    if 'offspring' in expected:
        child = expected['offspring']
        base = child['record'] * 0xA5
        if child['record'] in retained.values() or child['record'] not in expected['owned']:
            raise ValueError('Offspring is not a new original roster entry')
        genes = saved[base+0x19:base+0x34] + saved[base+0x6B:base+0xA5]
        if (saved[base+0x6D] != child['plus'] or saved[base+0x0E] & 1 != child['gender'] or
                list(saved[base+0x34:base+0x3C]) != child['skills'] or
                hashlib.sha256(genes).hexdigest() != child['genes_sha256']):
            raise ValueError('Original offspring generation, gender, skills or genes differ')
    for record, level, hp, status in zip(party, expected['levels'], expected['hp'],
                                         expected['status'], strict=True):
        base = record * 0xA5
        if (saved[base+0x56] != level or saved[base+0x55] != status or
                int.from_bytes(saved[base+0x5B:base+0x5D], 'little') != hp):
            raise ValueError(f'Observed original creature stats differ: {record}')
    if source[0xCBD7:0xCC0F] != ram[0xCBD7:0xCC0F]:
        raise ValueError('Original quest bytes differ after Continue')
    for name, flags in (('set_flags', True), ('clear_flags', False)):
        for flag in expected.get(name, []):
            if bool(ram[0xCBD7+flag//8] & (1 << (flag % 8))) != flags:
                raise ValueError(f'Observed quest flag differs: {flag:02x}')
    for capture in (source, ram):
        if int.from_bytes(capture[0xC617:0xC61A], 'little') != expected['gold']:
            raise ValueError('Original wallet differs after Journal/Continue')
        location = [capture[a] for a in (0xFF90, 0xFF8F, 0xFF92, 0xFF8E, 0xFF91)]
        if location != expected['location']:
            raise ValueError('Original location differs after Journal/Continue')
        if 'items' in expected:
            items = []
            for item in capture[0xC61D:0xC69D]:
                if item in (0, 255):
                    break
                items.append(item)
            if items != expected['items']:
                raise ValueError('Original quest-item inventory differs after Continue')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('exe', 'seed', 'manifest', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--wine', type=Path, help='Explicit Linux compatibility launcher')
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    report = {'status': 'running', 'platform': 'Wine on Linux' if args.wine else 'Windows',
              'executable_sha256': EXE_SHA,
              'executable_source': '697647033b4ce6b00dd8e11759cb85e1ae469a65',
              'full_game_verified': False, 'sea_world_completed': False, 'stages': []}
    try:
        if (os.name != 'nt') != bool(args.wine):
            raise ValueError('Run on Windows, or explicitly supply --wine on Linux')
        exe, initial = args.exe.resolve(strict=True), args.seed.resolve(strict=True)
        manifest = args.manifest.resolve(strict=True)
        data = json.loads(manifest.read_text(encoding='utf-8'))
        check_file(exe, EXE_SHA, 725318144)
        check_file(initial, data['seed_sha256'], 32768)
        immutable = [(exe, EXE_SHA), (initial, digest(initial)), (manifest, digest(manifest))]
        launcher = [str(args.wine.resolve(strict=True))] if args.wine else []
        completed = {}

        def runtime_path(path: Path) -> str:
            return 'Z:'+path.as_posix() if args.wine else str(path)

        for expected in data['stages']:
            name = expected['name']
            if Path(name).name != name or name in completed:
                raise ValueError('Checkpoint names must be unique directory names')
            route = (manifest.parent / expected['route']).resolve(strict=True)
            check_file(route, expected['route_sha256'])
            immutable.append((route, expected['route_sha256']))
            seed = completed[expected['seed_stage']] if 'seed_stage' in expected else initial
            stage = out / name
            stage.mkdir()
            copied = stage / 'seed-copy.sav'
            shutil.copyfile(seed, copied)
            immutable.append((copied, digest(seed)))
            shutil.copyfile(route, stage / route.name)
            native = stage / 'native'
            command = launcher + [str(exe), '--m8-checkpoint-test', runtime_path(copied),
                                  runtime_path(route), runtime_path(native)]
            entry = {'stage': name, 'frames': expected['frames'], 'command': command,
                     'route_sha256': expected['route_sha256']}
            report['stages'].append(entry)
            with (stage / 'native.log').open('xb') as log:
                result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT,
                                        timeout=1200, check=False)
            entry['native_returncode'] = result.returncode
            if result.returncode:
                raise RuntimeError(f'{name}: native replay exited {result.returncode}')
            saved = native / 'checkpoint.sav'
            check_file(saved, expected['save_sha256'], 32768)
            log = (stage / 'native.log').read_text(encoding='utf-8', errors='replace')
            world, rx, ry, x, y = expected['location']
            location = f'world={world} region={rx},{ry} pos={x},{y}'
            for marker in ('M8_TRACE_REPLAY_PASS', 'M8_FRESH_CONTINUE_PASS', 'M8_CHECKPOINT_PASS',
                           f'frame={expected["frames"]} mode=1:0 {location} party=3'):
                if marker not in log:
                    raise ValueError(f'{name}: missing native witness: {marker}')
            verify_creatures(native, copied, expected)
            completed[name] = saved
            entry.update(status='passed', save_sha256=digest(saved),
                         active_party_records=expected['party'], levels=expected['levels'],
                         hp=expected['hp'], status_bytes=expected['status'], gold=expected['gold'],
                         owned=len(expected['owned']),
                         additional_persistent_creature_bytes=(32 + sum(
                             end-start for start, end in expected.get('persistent_ranges', [])))
                         * len(expected['owned']))
            if 'offspring' in expected:
                entry['offspring'] = expected['offspring']
                entry['retained_records'] = expected['retained_records']
        for path, expected_hash in immutable:
            check_file(path, expected_hash)
        report['status'] = 'passed'
        report['sea_world_completed'] = any(
            {0x22, 0x7F}.issubset(stage.get('set_flags', [])) for stage in data['stages'])
        print(f'M8_STORY_CHECKPOINTS_PASS platform={report["platform"]} original_Journal fresh_Continue')
        return 0
    except (OSError, ValueError, RuntimeError, KeyError, subprocess.SubprocessError) as error:
        report.update(status='failed', error=str(error))
        print('M8_STORY_CHECKPOINTS_FAIL', error)
        return 1
    finally:
        (out / 'story-checkpoints-validation.json').write_text(json.dumps(report, indent=2)+'\n',
                                                            encoding='utf-8')


if __name__ == '__main__':
    raise SystemExit(main())
