"""Replay observed original story Journals and verify fresh Continue.

The manifest describes evidence already obtained through original P1 input.
It supplies assertions only; it never writes game state or interprets opcodes.
Passing these checkpoints does not certify the ending or final M8 acceptance.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import traceback

from test_m8_farm_dancer import EXE_SHA, check_file, digest
from m8_build_identity import load_identity


def bundle_hashes(data: dict) -> dict[str, str]:
    """Describe only original Journal fixtures already pinned by the manifest."""
    expected = {'initial.sav': data['seed_sha256']}
    seen = {'initial', 'seed-inputs'}
    original_names = set()
    for stage in data['stages']:
        name = stage['name']
        if (not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', name)
                or name.casefold() in seen
                or name.upper() in {'CON', 'PRN', 'AUX', 'NUL',
                                    *(f'COM{i}' for i in range(1, 10)),
                                    *(f'LPT{i}' for i in range(1, 10))}):
            raise ValueError('Unsafe or duplicate checkpoint name in Journal bundle')
        if 'seed_stage' in stage and (not isinstance(stage['seed_stage'], str)
                                      or stage['seed_stage'] not in original_names):
            raise ValueError('Journal bundle dependency must name an exact earlier checkpoint')
        seen.add(name.casefold())
        original_names.add(name)
        expected[name+'.sav'] = stage['save_sha256']
    if any(not re.fullmatch(r'[0-9a-f]{64}', str(value)) for value in expected.values()):
        raise ValueError('Journal bundle requires exact pinned SHA256 identities')
    return expected


def load_seed_bundle(bundle: Path, data: dict, destination: Path) -> dict[str, Path]:
    """Validate every tar.xz member before creating the new seed-input directory.

    These exact 32-KiB files are genuine original Journals, never RAM/SRAM
    observations. Only the manifest's pinned filenames and hashes are accepted.
    """
    if destination.exists():
        raise ValueError('Journal seed-input directory must be new')
    expected = bundle_hashes(data)
    content = {}
    with tarfile.open(bundle, 'r:xz') as archive:
        for member in archive:
            if (not member.isfile() or member.name not in expected
                    or member.name in content or member.size != 32768):
                raise ValueError('Unexpected, duplicate or non-32-KiB original Journal member')
            stream = archive.extractfile(member)
            if stream is None:
                raise ValueError('Unreadable original Journal member')
            with stream:
                saved = stream.read(32769)
            if len(saved) != 32768 or hashlib.sha256(saved).hexdigest() != expected[member.name]:
                raise ValueError('Original Journal bundle checksum differs: '+member.name)
            content[member.name] = saved
    if set(content) != set(expected):
        raise ValueError('Original Journal bundle is incomplete')
    destination.mkdir(exist_ok=False)
    result = {}
    for name, saved in content.items():
        path = destination/name
        with path.open('xb') as output:
            output.write(saved)
        result[name[:-4]] = path
    return result


def verify_ending_witnesses(route: Path, expected: dict) -> None:
    if expected.get('ending_complete') is not True:
        return
    witnesses = expected.get('completion_witnesses', {})
    if set(witnesses) != {'darck-defeated', 'credits-start', 'credits-final', 'the-end'} or 0x25 not in expected['set_flags']:
        raise ValueError('Ending checkpoint lacks the complete original ending witnesses')
    frames, screens = 0, {}
    for line in route.read_text(encoding='utf-8').splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] in ('A', 'B', 'U', 'D', 'L', 'R', 'Start', 'Select', '-'):
            frames += int(parts[1])+int(parts[2])
        elif parts[0] == 'expect_screen':
            screens.setdefault(frames, set()).add(int(parts[1], 16))
    ordered = [witnesses[key] for key in ('darck-defeated', 'credits-start', 'credits-final', 'the-end')]
    if (not all(0 < item['frame'] < expected['frames'] and
                int(item['screen'], 16) in screens.get(item['frame'], set()) for item in ordered)
            or [item['frame'] for item in ordered] != sorted(item['frame'] for item in ordered)
            or frames != expected['frames']):
        raise ValueError('Ending witnesses do not match the tested original P1 route')


def verify_name_bytes(saved: bytes, fresh: bytes, record: int, transitions: list[dict]) -> None:
    """Keep historical name checks; pin original codec padding changes exactly."""
    if len(saved) != 10 or len(fresh) != 10:
        raise ValueError('Original nickname observations must contain ten bytes')
    selected = []
    for item in transitions:
        if item.get('record') != record:
            continue
        offset = item.get('offset')
        if type(offset) is not int:
            raise ValueError('Original name transition offset must be an integer')
        if 1 <= offset <= 10:
            selected.append(item)
    if selected:
        expected = bytearray(saved)
        seen = set()
        for item in selected:
            if (set(item) != {'record', 'offset', 'before', 'after'} or
                    any(type(item[key]) is not int for key in item) or
                    item['before'] not in range(256) or item['after'] not in range(256) or
                    item['before'] == item['after'] or item['offset'] in seen):
                raise ValueError('Invalid or duplicate exact original nickname transition')
            index = item['offset']-1
            if saved[index] != item['before'] or fresh[index] != item['after']:
                raise ValueError('Original nickname transition differs from its exact pin')
            expected[index] = item['after']
            seen.add(item['offset'])
        if bytes(expected) != fresh:
            raise ValueError(f'Creature name differs after Continue: {record}')
    elif saved.split(b'\xf0', 1)[0] != fresh.split(b'\xf0', 1)[0]:
        raise ValueError(f'Creature name differs after Continue: {record}')


def verify_creatures(native: Path, seed: Path, expected: dict) -> None:
    saved = (native / 'checkpoint.sav').read_bytes()
    fresh = (native / 'fresh_continue/m8_0.sram').read_bytes()
    source = (native / 'm8_0.ram').read_bytes()
    ram = (native / 'fresh_continue/m8_0.ram').read_bytes()
    if tuple(map(len, (saved, fresh, source, ram))) != (32768, 32768, 65536, 65536):
        raise ValueError('Incomplete original Journal/Continue capture')
    party = expected['party']
    if ram[0xC6FD:0xC6FE+len(party)] != bytes((len(party), *party)):
        raise ValueError('Original active party differs after Continue')
    if [i for i in range(40) if saved[i*0xA5] in (1, 2)] != expected['owned']:
        raise ValueError('Original owned roster differs')
    initial = seed.read_bytes()
    retained = {int(old): new for old, new in expected.get('retained_records', {}).items()}
    if retained:
        initial_owned = {i for i in range(40) if initial[i*0xA5] in (1, 2)}
        parents = set(expected.get('consumed_records', expected.get('bred_parents', [])))
        if (set(retained) | parents != initial_owned or set(retained) & parents or
                len(set(retained.values())) != len(retained) or
                not set(retained.values()).issubset(expected['owned'])):
            raise ValueError('Incomplete original roster compaction witness')
        for old, new in retained.items():
            old_base, new_base = old*0xA5, new*0xA5
            # Original Continue clears stale bytes after the F0 name terminator.
            # WingSlime's genuine recruitment/Continue route exercises this.
            old_name = initial[old_base+1:old_base+11].split(b'\xf0', 1)[0]
            new_name = saved[new_base+1:new_base+11].split(b'\xf0', 1)[0]
            if (new_name != old_name or
                    saved[new_base+11:new_base+13] != initial[old_base+11:old_base+13]):
                raise ValueError(f'Previously owned name/species differs: {old} -> {new}')
    for record in expected['owned']:
        base = record * 0xA5
        if saved[base] != (2 if record in party else 1):
            raise ValueError(f'Original farm/active status differs: {record}')
        verify_name_bytes(saved[base+1:base+11], fresh[base+1:base+11], record,
                          expected.get('continue_byte_transitions', []))
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
    # Original bank 2:$7636/$76AC saves/restores CBD7 with length 0x6B.
    # Sky's bridge uses flag 0x209, beyond the earlier 64-byte comparison.
    # Keep the complete original block; the pinned native core is unchanged.
    if source[0xCBD7:0xCC42] != ram[0xCBD7:0xCC42]:
        raise ValueError('Original quest bytes differ after Continue')
    if saved[0x3DA0:0x3E0B] != ram[0xCBD7:0xCC42]:
        raise ValueError('Original Journal quest block differs after Continue')
    for name, flags in (('set_flags', True), ('clear_flags', False)):
        for flag in expected.get(name, []):
            if bool(ram[0xCBD7+flag//8] & (1 << (flag % 8))) != flags:
                raise ValueError(f'Observed quest flag differs: {flag:02x}')
    for capture in (source, ram):
        if 'arena_class' in expected and capture[0xC82C] != expected['arena_class']:
            raise ValueError('Original Arena class differs after Journal/Continue')
        if int.from_bytes(capture[0xC617:0xC61A], 'little') != expected['gold']:
            raise ValueError('Original wallet differs after Journal/Continue')
        location = [capture[a] for a in (0xFF90, 0xFF8F, 0xFF92, 0xFF8E, 0xFF91)]
        if location != expected['location']:
            raise ValueError('Original location differs after Journal/Continue')
        if 'key_entries' in expected:
            key_bytes = bytes(value for key in expected['key_entries'] for value in key)
            if capture[0xC707:0xC707+len(key_bytes)] != key_bytes:
                raise ValueError('Original Magic Key entries differ after Journal/Continue')
        if 'items' in expected:
            items = []
            for item in capture[0xC61D:0xC635]:
                if item in (0, 255):
                    break
                items.append(item)
            if items != expected['items']:
                raise ValueError('Original quest-item inventory differs after Continue')


def replay_checkpoint(expected: dict, copied: Path, native: Path,
                      command: list[str], entry: dict, timeout: int = 1200) -> Path:
    """Run the same complete original P1, Journal and persistence gate in either mode."""
    name = expected['name']
    with (native.parent/'native.log').open('xb') as log:
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT,
                                timeout=timeout, check=False)
    entry['native_returncode'] = result.returncode
    if result.returncode:
        raise RuntimeError(f'{name}: native replay exited {result.returncode}')
    saved = native/'checkpoint.sav'
    check_file(saved, expected['save_sha256'], 32768)
    log = (native.parent/'native.log').read_text(encoding='utf-8', errors='replace')
    world, rx, ry, x, y = expected['location']
    location = f'world={world} region={rx},{ry} pos={x},{y}'
    for marker in ('M8_TRACE_REPLAY_PASS', 'M8_FRESH_CONTINUE_PASS', 'M8_CHECKPOINT_PASS',
                   f'frame={expected["frames"]} mode=1:0 {location} party={len(expected["party"])}'):
        if marker not in log:
            raise ValueError(f'{name}: missing native witness: {marker}')
    verify_creatures(native, copied, expected)
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
    if expected.get('ending_complete') is True:
        entry.update(ending_completed=True,
                     completion_witnesses=expected['completion_witnesses'])
    return saved


def replay_prepared(plans: list[dict], workers: int) -> dict[str, Path]:
    """Bound concurrency, keep every result, and leave report entries in manifest order."""
    if workers not in range(1, 5):
        raise ValueError('Original checkpoint replay accepts one to four workers')
    completed, errors = {}, []

    def run(plan: dict) -> Path:
        plan['entry']['status'] = 'running'
        print('M8_STORY_STAGE_START', plan['expected']['name'], flush=True)
        return replay_checkpoint(plan['expected'], plan['copied'], plan['native'],
                                 plan['command'], plan['entry'], timeout=1800)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        # All stages start from separately validated original Journals. Start the
        # longest routes first to avoid a long training route becoming the tail.
        pending = {executor.submit(run, plan): plan for plan in
                   sorted(plans, key=lambda plan: plan['expected']['frames'], reverse=True)}
        for future in as_completed(pending):
            plan = pending[future]
            name = plan['expected']['name']
            try:
                completed[name] = future.result()
                print('M8_STORY_STAGE_PASS', name, flush=True)
            except Exception as error:
                plan['entry'].update(status='failed', error=str(error),
                                     error_type=type(error).__name__,
                                     error_traceback=traceback.format_exc())
                errors.append(f'{name}: {type(error).__name__}: {error}')
                print('M8_STORY_STAGE_FAIL', errors[-1], flush=True)
    if errors:
        raise RuntimeError('Parallel original checkpoint failures: '+'; '.join(errors))
    return completed


def audit_journal_chain(data: dict, output: Path, initial: Path,
                        completed: dict[str, Path]) -> int:
    """Bind each tested input to its newly replayed parent output, not just a golden."""
    expected_saves = {stage['name']: stage['save_sha256'] for stage in data['stages']}
    if set(completed) != set(expected_saves):
        raise ValueError('Original Journal chain has missing replayed checkpoints')
    check_file(initial, data['seed_sha256'], 32768)
    for stage in data['stages']:
        parent = stage.get('seed_stage')
        source = completed[parent] if parent else initial
        source_hash = expected_saves[parent] if parent else data['seed_sha256']
        check_file(source, source_hash, 32768)
        check_file(completed[stage['name']], stage['save_sha256'], 32768)
        check_file(output/stage['name']/'seed-copy.sav', digest(source), 32768)
    return len(data['stages'])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('exe', 'seed', 'manifest', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--wine', type=Path, help='Explicit Linux compatibility launcher')
    parser.add_argument('--build-identity', type=Path,
                        help='Isolated fresh diagnostic build identity; default preserves the historical pin')
    parser.add_argument('--workers', type=int, choices=range(1, 5), default=1,
                        help='One to four uncapped original replays; parallel mode requires --seed-bundle')
    parser.add_argument('--seed-bundle', type=Path,
                        help='Pinned authentic Journal tar.xz; all replayed parent/output links are audited')
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    report = {'status': 'running', 'platform': 'Wine on Linux' if args.wine else 'Windows',
              'executable_sha256': EXE_SHA,
              'executable_source': '697647033b4ce6b00dd8e11759cb85e1ae469a65',
              'full_game_verified': False, 'sea_world_completed': False,
              'ice_world_completed': False, 'quest_bytes': 107, 'stages': [],
              'workers': args.workers, 'seed_chain_audited': False}
    try:
        if (os.name != 'nt') != bool(args.wine):
            raise ValueError('Run on Windows, or explicitly supply --wine on Linux')
        if args.workers > 1 and args.seed_bundle is None:
            raise ValueError('Parallel original replay requires a pinned original Journal seed bundle')
        exe, initial = args.exe.resolve(strict=True), args.seed.resolve(strict=True)
        manifest = args.manifest.resolve(strict=True)
        data = json.loads(manifest.read_text(encoding='utf-8'))
        identity = load_identity(args.build_identity)
        identity.verify(exe)
        report.update(identity.report())
        check_file(initial, data['seed_sha256'], 32768)
        immutable = [(exe, identity.sha256), (initial, digest(initial)), (manifest, digest(manifest))]
        launcher = [str(args.wine.resolve(strict=True))] if args.wine else []
        completed = {}

        def runtime_path(path: Path) -> str:
            return 'Z:'+path.as_posix() if args.wine else str(path)

        if args.seed_bundle is not None:
            bundle = args.seed_bundle.resolve(strict=True)
            bundle_sha = digest(bundle)
            report.update(seed_bundle_sha256=bundle_sha)
            seeds = load_seed_bundle(bundle, data, out/'seed-inputs')
            immutable.append((bundle, bundle_sha))
            immutable.extend((path, digest(path)) for path in seeds.values())
            plans = []
            for expected in data['stages']:
                name = expected['name']
                route = (manifest.parent/expected['route']).resolve(strict=True)
                check_file(route, expected['route_sha256'])
                verify_ending_witnesses(route, expected)
                immutable.append((route, expected['route_sha256']))
                # The initial branches always use the freshly generated native
                # preparation Journal, never the bundle's redundant initial copy.
                seed = seeds[expected['seed_stage']] if 'seed_stage' in expected else initial
                stage = out/name
                stage.mkdir()
                copied = stage/'seed-copy.sav'
                shutil.copyfile(seed, copied)
                immutable.append((copied, digest(seed)))
                shutil.copyfile(route, stage/route.name)
                native = stage/'native'
                command = launcher+[str(exe), '--m8-checkpoint-test', runtime_path(copied),
                                    runtime_path(route), runtime_path(native)]
                entry = dict(stage=name, frames=expected['frames'], command=command,
                             route_sha256=expected['route_sha256'], status='pending')
                report['stages'].append(entry)
                plans.append(dict(expected=expected, copied=copied, native=native,
                                  command=command, entry=entry))
            completed = replay_prepared(plans, args.workers)

        for expected in ([] if args.seed_bundle is not None else data['stages']):
            name = expected['name']
            if Path(name).name != name or name in completed:
                raise ValueError('Checkpoint names must be unique directory names')
            route = (manifest.parent / expected['route']).resolve(strict=True)
            check_file(route, expected['route_sha256'])
            verify_ending_witnesses(route, expected)
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
            completed[name] = replay_checkpoint(expected, copied, native, command, entry)
        report.update(seed_chain_links=audit_journal_chain(data, out, initial, completed),
                      seed_chain_audited=True)
        for path, expected_hash in immutable:
            check_file(path, expected_hash)
        identity.verify(exe)
        report['status'] = 'passed'
        report['ending_completed'] = any(stage.get('ending_completed') is True for stage in report['stages'])
        report['sea_world_completed'] = any(
            {0x22, 0x7F}.issubset(stage.get('set_flags', [])) for stage in data['stages'])
        report['ice_world_completed'] = any(
            {0x23, 0x1E5}.issubset(stage.get('set_flags', [])) for stage in data['stages'])
        print(f'M8_STORY_CHECKPOINTS_PASS platform={report["platform"]} original_Journal fresh_Continue')
        return 0
    except (OSError, ValueError, RuntimeError, KeyError, subprocess.SubprocessError, tarfile.TarError) as error:
        report.update(status='failed', error=str(error))
        print('M8_STORY_CHECKPOINTS_FAIL', error)
        return 1
    finally:
        (out / 'story-checkpoints-validation.json').write_text(json.dumps(report, indent=2)+'\n',
                                                            encoding='utf-8')


if __name__ == '__main__':
    raise SystemExit(main())
