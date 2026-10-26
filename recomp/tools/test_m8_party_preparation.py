"""Verify original recovery, farm exchange, trading and GreatLog-key training.

These checkpoints prepare the Sea World party; they do not certify its boss or
the ending. Every input is a recorded P1 controller transition on the pinned EXE.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

from m8_build_identity import load_identity

from test_m8_farm_dancer import EXE_SHA, check_file, digest

SEED_SHA = '5632ab2d6c200ca3c93f768d8d56843f2a9c32fe4f437f9572b4ea843a86e333'
# name, argument, fixture SHA, Journal SHA, frames, levels, HP, owned count, gold, location
STAGES = (
    ('support', 'support_route',
     '70057a78eaad42f9494593950607bb3dcd273fc48db9a550220954e12df51dec',
     'c92dda4a93ca169af62704e17b33bb9aef3f75f1dc5779ed3e70a67dacf92249',
     40825, (6, 8, 5), (60, 44, 54), 8, 0, 'world=0 region=1,2 pos=64,48'),
    ('training', 'training_route',
     'f6f96a362d85ee57e509f483023ebc4022ddcedb1c3fef5abe019034c1501ef8',
     'eea6fd3aa19fc34f3bef52ea38af5e1e8fc7f19c0e0bb28e8460fc4d44225a03',
     395984, (10, 12, 12), (97, 60, 69), 9, 40, 'world=5 region=1,0 pos=80,64'),
)
PARTY = (0, 1, 4)


def validate_save(native: Path, levels: tuple[int, ...], hp: tuple[int, ...],
                  owned: int, gold: int, initial_species: list[bytes]) -> None:
    saved = (native / 'checkpoint.sav').read_bytes()
    fresh = (native / 'fresh_continue/m8_0.sram').read_bytes()
    ram = (native / 'fresh_continue/m8_0.ram').read_bytes()
    source = (native / 'm8_0.ram').read_bytes()
    if (len(saved), len(fresh), len(ram), len(source)) != (32768, 32768, 65536, 65536):
        raise ValueError('Incomplete original cartridge/Continue capture')
    if ram[0xC6FD:0xC701] != bytes((3, *PARTY)):
        raise ValueError('Original support party did not survive Continue')
    if [i for i in range(40) if saved[i*0xA5] in (1, 2)] != list(range(owned)):
        raise ValueError('Original farm roster differs')
    for record in range(owned):
        base = record * 0xA5
        if saved[base] != (2 if record in PARTY else 1):
            raise ValueError(f'Original farm/active status differs: {record}')
        # Name-cache padding may be refreshed by the original Continue routine.
        # Species, learned skills and persistent stats must remain byte-identical.
        for start, end in ((0x0B, 0x0D), (0x34, 0x3C), (0x55, 0x6B)):
            if saved[base+start:base+end] != fresh[base+start:base+end]:
                raise ValueError(f'Creature persistence differs: {record}, {start:02x}')
    for record, species in enumerate(initial_species):
        base = record * 0xA5
        if saved[base+0x0B:base+0x0D] != species:
            raise ValueError(f'Previously owned creature was replaced: {record}')
    for record, level, health in zip(PARTY, levels, hp, strict=True):
        base = record * 0xA5
        if (saved[base+0x56] != level or saved[base+0x55] & 0x80 or
                int.from_bytes(saved[base+0x5B:base+0x5D], 'little') != health):
            raise ValueError(f'Original level/living HP differs: {record}')
    for capture in (source, ram):
        if int.from_bytes(capture[0xC617:0xC61A], 'little') != gold:
            raise ValueError('Original wallet did not survive Journal/Continue')
    if source[0xCBD7:0xCC0F] != ram[0xCBD7:0xCC0F] or not ram[0xCBE4] & 0x40:
        raise ValueError('Original quest flags did not survive Continue')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('exe', 'seed', 'support-route', 'training-route', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--wine', type=Path, help='Explicit Linux compatibility launcher')
    parser.add_argument('--build-identity', type=Path,
                        help='Fresh diagnostic build identity; default preserves the historical pin')
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    report = {'status': 'running', 'platform': 'Wine on Linux' if args.wine else 'Windows',
              'executable_source': '697647033b4ce6b00dd8e11759cb85e1ae469a65',
              'full_game_verified': False, 'sea_world_completed': False, 'stages': []}
    try:
        if (os.name != 'nt') != bool(args.wine):
            raise ValueError('Use Windows directly, or explicitly supply --wine on Linux')
        exe, seed = args.exe.resolve(strict=True), args.seed.resolve(strict=True)
        identity = load_identity(args.build_identity)
        identity.verify(exe)
        report.update(identity.report())
        if args.build_identity:
            for key in ('baseline_windows_run', 'seed_windows_run'):
                if key in report:report['historical_'+key] = report.pop(key)
        check_file(seed, SEED_SHA, 32768)
        inputs = [(exe, identity.sha256), (seed, SEED_SHA)]
        initial = seed.read_bytes()
        initial_species = [initial[i*0xA5+0x0B:i*0xA5+0x0D] for i in range(7)]
        for _, argument, route_sha, *_ in STAGES:
            route = getattr(args, argument).resolve(strict=True)
            check_file(route, route_sha)
            inputs.append((route, route_sha))
        launcher = [str(args.wine.resolve(strict=True))] if args.wine else []

        def runtime_path(path: Path) -> str:
            return 'Z:'+path.as_posix() if args.wine else str(path)

        for name, argument, route_sha, save_sha, frames, levels, hp, owned, gold, location in STAGES:
            stage = out / name
            stage.mkdir()
            route = getattr(args, argument).resolve(strict=True)
            copied = stage / 'seed-copy.sav'
            shutil.copyfile(seed, copied)
            inputs.append((copied, digest(seed)))
            shutil.copyfile(route, stage / route.name)
            native = stage / 'native'
            command = launcher + [str(exe), '--m8-checkpoint-test', runtime_path(copied),
                                  runtime_path(route), runtime_path(native)]
            entry = {'stage': name, 'frames': frames, 'route_sha256': route_sha, 'command': command}
            report['stages'].append(entry)
            with (stage / 'native.log').open('xb') as log:
                result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT,
                                        timeout=1200, check=False)
            entry['native_returncode'] = result.returncode
            if result.returncode:
                raise RuntimeError(f'{name}: original replay failed: {result.returncode}')
            seed = native / 'checkpoint.sav'
            check_file(seed, save_sha, 32768)
            log = (stage / 'native.log').read_text(encoding='utf-8', errors='replace')
            for marker in ('M8_TRACE_REPLAY_PASS', 'M8_FRESH_CONTINUE_PASS', 'M8_CHECKPOINT_PASS',
                           f'frame={frames} mode=1:0 {location} party=3'):
                if marker not in log:
                    raise ValueError(f'{name}: missing native witness: {marker}')
            validate_save(native, levels, hp, owned, gold, initial_species)
            entry.update(status='passed', save_sha256=save_sha, active_party_records=PARTY,
                         levels=levels, hp=hp, gold=gold, owned=owned,
                         additional_persistent_creature_bytes=32*owned)
        for path, expected in inputs:
            check_file(path, expected)
        identity.verify(exe)
        report['status'] = 'passed'
        print(f'M8_PARTY_PREPARATION_PASS platform={report["platform"]} original_Journal fresh_Continue')
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        report.update(status='failed', error=str(error))
        print('M8_PARTY_PREPARATION_FAIL', error)
        return 1
    finally:
        (out / 'party-preparation-validation.json').write_text(json.dumps(report, indent=2)+'\n',
                                                            encoding='utf-8')


if __name__ == '__main__':
    raise SystemExit(main())
